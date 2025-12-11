"""
Subtitle Generation API Router

Handles async subtitle generation jobs with status tracking.
"""

import asyncio
import logging
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse

from api.utils.errors import (
    FileTooLargeError,
    UnsupportedAudioFormatError,
    AudioProcessingError,
)
from api.utils.jobs import get_job_manager, JobStatus
from lib.models import get_model_manager
from lib.utils.gpu import get_vram_info, is_gpu_available, get_optimal_device, get_optimal_compute_type
from lib.formatters import SRTFormatter

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Configuration
MAX_FILE_SIZE_MB = 500
SUPPORTED_FORMATS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".opus", ".webm"}

# Thread pool for running transcription in background
executor = ThreadPoolExecutor(max_workers=2)


def process_subtitle_job(
    job_id: str,
    temp_file_path: str,
    output_format: str,
    filename: str,
    engine: str,
    model_size: str,
    compute_type: str,
    transcription_config: dict,
    formatter_config: dict,
):
    """
    Process subtitle generation in background thread.
    Updates job status as it progresses.
    """
    job_manager = get_job_manager()
    request_start_time = time.time()

    try:
        # Update status to processing
        job_manager.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

        # Load model
        model_manager = get_model_manager()
        engine_config = {
            "device": get_optimal_device(),
            "compute_type": compute_type,
        }

        job_manager.update_job(job_id, progress=20)

        preprocessing_start = time.time()
        engine_instance = model_manager.get_engine(engine, model_size, engine_config)
        preprocessing_time_ms = (time.time() - preprocessing_start) * 1000

        job_manager.update_job(job_id, progress=30)

        # Transcribe
        inference_start = time.time()
        result = engine_instance.transcribe(temp_file_path, transcription_config)
        inference_time_ms = (time.time() - inference_start) * 1000

        job_manager.update_job(job_id, progress=80)

        total_time_ms = (time.time() - request_start_time) * 1000

        # Calculate metrics
        audio_duration_s = result.segments[-1].end if result.segments else 0
        real_time_factor = (total_time_ms / 1000) / audio_duration_s if audio_duration_s > 0 else 0

        vram_used_mb = None
        if is_gpu_available():
            vram_info = get_vram_info()
            vram_used_mb = vram_info.get("allocated_mb")

        # Format result based on output format
        if output_format == "json":
            words_list = []
            for segment in result.segments:
                if segment.words:
                    words_list.extend([
                        {"word": w.word, "start": w.start, "end": w.end}
                        for w in segment.words
                    ])

            response_data = {
                "text": result.text,
                "language": result.language,
                "segments": [
                    {
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text,
                        "words": [
                            {"word": w.word, "start": w.start, "end": w.end}
                            for w in seg.words
                        ] if seg.words else None
                    }
                    for seg in result.segments
                ],
                "words": words_list if words_list else None,
                "metadata": {
                    "engine": engine,
                    "model_size": model_size,
                    "language": result.language,
                    "preprocessing": "vad_only" if transcription_config.get("vad_filter") else "none",
                    "audio_duration_s": audio_duration_s,
                    "inference_time_ms": inference_time_ms,
                    "preprocessing_time_ms": preprocessing_time_ms,
                    "total_time_ms": total_time_ms,
                    "real_time_factor": real_time_factor,
                    "vram_used_mb": vram_used_mb,
                }
            }
            job_manager.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                result={"type": "json", "data": response_data}
            )
        else:  # SRT format
            formatter = SRTFormatter(
                max_line_width=formatter_config.get("max_line_width", 42),
                max_line_count=formatter_config.get("max_line_count", 2),
                adjust_timing=formatter_config.get("adjust_timing", False),
                split_by_punctuation=formatter_config.get("split_by_punctuation", False),
            )
            content = formatter.format(
                result.segments,
                word_level=formatter_config.get("word_level", False)
            )

            job_manager.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                result={
                    "type": "srt",
                    "content": content,
                    "filename": Path(filename).stem + ".srt",
                    "metadata": {
                        "total_time_ms": total_time_ms,
                        "inference_time_ms": inference_time_ms,
                        "audio_duration_s": audio_duration_s,
                    }
                }
            )

        logger.info(f"Job {job_id} completed in {total_time_ms:.1f}ms")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        job_manager.update_job(
            job_id,
            status=JobStatus.FAILED,
            error=str(e)
        )

    finally:
        # Cleanup temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                logger.debug(f"Cleaned up temporary file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temporary file: {e}")


@router.post("/subtitle", tags=["Subtitles"])
async def submit_subtitle_job(
    audio_file: UploadFile = File(..., description="Audio file to transcribe"),
    format: str = Form(default="srt", description="Output format (srt, json)"),
    engine: Optional[str] = Form(default="faster-whisper", description="ASR engine"),
    model_size: Optional[str] = Form(default="large-v3", description="Model size"),
    compute_type: Optional[str] = Form(default=None, description="Compute type"),
    language: Optional[str] = Form(default=None, description="Language code"),
    vad_filter: Optional[bool] = Form(default=True, description="Enable VAD"),
    word_timestamps: Optional[bool] = Form(default=True, description="Include word timestamps"),
    batch_size: Optional[int] = Form(default=16, description="Batch size"),
    beam_size: Optional[int] = Form(default=5, description="Beam size"),
    temperature: Optional[float] = Form(default=0.0, description="Temperature"),
    best_of: Optional[int] = Form(default=5, description="Best of N samples"),
    condition_on_previous_text: Optional[bool] = Form(default=True, description="Condition on previous text"),
    no_speech_threshold: Optional[float] = Form(default=0.6, description="No speech threshold"),
    compression_ratio_threshold: Optional[float] = Form(default=2.4, description="Compression ratio threshold"),
    logprob_threshold: Optional[float] = Form(default=-1.0, description="Log probability threshold"),
    initial_prompt: Optional[str] = Form(default=None, description="Initial prompt for context"),
    word_level: Optional[bool] = Form(default=False, description="One word per subtitle"),
    max_line_width: Optional[int] = Form(default=42, description="Max characters per line"),
    max_line_count: Optional[int] = Form(default=2, description="Max lines per subtitle"),
    adjust_timing: Optional[bool] = Form(default=False, description="Adjust timing for natural reading"),
    split_by_punctuation: Optional[bool] = Form(default=False, description="Split subtitles at punctuation marks"),
):
    """
    Submit a subtitle generation job.

    Returns immediately with a job_id that can be used to check status.

    **Response**:
    ```json
    {
        "job_id": "abc12345",
        "status": "pending",
        "message": "Job submitted successfully"
    }
    ```
    """
    # Validate format
    format = format.lower()
    if format not in ["srt", "json"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "invalid_format",
                "message": f"Unsupported format: {format}",
                "supported_formats": ["srt", "json"],
            },
        )

    # Validate file size
    file_content = await audio_file.read()
    file_size_mb = len(file_content) / (1024 * 1024)

    if file_size_mb > MAX_FILE_SIZE_MB:
        raise FileTooLargeError(file_size_mb, MAX_FILE_SIZE_MB)

    # Validate audio format
    file_extension = Path(audio_file.filename).suffix.lower()
    if file_extension not in SUPPORTED_FORMATS:
        raise UnsupportedAudioFormatError(file_extension)

    # Save to temporary file
    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=file_extension, delete=False
    ) as temp_file:
        temp_file.write(file_content)
        temp_file_path = temp_file.name

    # Auto-detect compute type if needed
    if compute_type is None:
        compute_type = get_optimal_compute_type()

    # Create job
    job_manager = get_job_manager()
    job = job_manager.create_job(format=format, filename=audio_file.filename)

    # Prepare configs
    transcription_config = {
        "language": language,
        "vad_filter": vad_filter,
        "word_timestamps": word_timestamps,
        "batch_size": batch_size,
        "beam_size": beam_size,
        "temperature": temperature,
        "best_of": best_of,
        "condition_on_previous_text": condition_on_previous_text,
        "no_speech_threshold": no_speech_threshold,
        "compression_ratio_threshold": compression_ratio_threshold,
        "logprob_threshold": logprob_threshold,
        "initial_prompt": initial_prompt,
    }

    formatter_config = {
        "word_level": word_level,
        "max_line_width": max_line_width,
        "max_line_count": max_line_count,
        "adjust_timing": adjust_timing,
        "split_by_punctuation": split_by_punctuation,
    }

    # Submit to thread pool
    executor.submit(
        process_subtitle_job,
        job.id,
        temp_file_path,
        format,
        audio_file.filename,
        engine,
        model_size,
        compute_type,
        transcription_config,
        formatter_config,
    )

    logger.info(f"Submitted job {job.id} for {audio_file.filename}")

    return JSONResponse(content={
        "job_id": job.id,
        "status": job.status.value,
        "message": "Job submitted successfully"
    })


@router.get("/jobs/{job_id}", tags=["Jobs"])
async def get_job_status(job_id: str):
    """
    Get the status of a subtitle generation job.

    **Response (pending/processing)**:
    ```json
    {
        "job_id": "abc12345",
        "status": "processing",
        "progress": 50
    }
    ```

    **Response (completed - SRT)**:
    ```json
    {
        "job_id": "abc12345",
        "status": "completed",
        "progress": 100,
        "result": {
            "type": "srt",
            "content": "1\\n00:00:00,000 --> ...",
            "filename": "video.srt"
        }
    }
    ```

    **Response (completed - JSON)**:
    ```json
    {
        "job_id": "abc12345",
        "status": "completed",
        "progress": 100,
        "result": {
            "type": "json",
            "data": {...}
        }
    }
    ```

    **Response (failed)**:
    ```json
    {
        "job_id": "abc12345",
        "status": "failed",
        "error": "Error message"
    }
    ```
    """
    job_manager = get_job_manager()
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "job_not_found", "message": f"Job {job_id} not found"}
        )

    response = {
        "job_id": job.id,
        "status": job.status.value,
        "progress": job.progress,
    }

    if job.status == JobStatus.COMPLETED and job.result:
        response["result"] = job.result

    if job.status == JobStatus.FAILED and job.error:
        response["error"] = job.error

    return JSONResponse(content=response)


@router.get("/jobs", tags=["Jobs"])
async def list_jobs():
    """
    List all jobs (for debugging).
    """
    job_manager = get_job_manager()
    jobs = job_manager.list_jobs()

    return JSONResponse(content={
        "jobs": [
            {
                "job_id": job.id,
                "status": job.status.value,
                "progress": job.progress,
                "format": job.format,
                "filename": job.filename,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            }
            for job in jobs.values()
        ]
    })
