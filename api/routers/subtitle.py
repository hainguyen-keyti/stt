"""
Subtitle Generation API Router

Thin API layer that delegates to STT module for business logic.
"""

import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse

from api.utils.errors import FileTooLargeError, UnsupportedAudioFormatError
from api.utils.jobs import get_job_manager, JobStatus
from modules.stt import get_stt_service, TranscriptionRequest

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
    original_filename: str,
    request: TranscriptionRequest,
):
    """
    Process subtitle generation in background thread.
    Delegates to STT service for actual processing.
    """
    job_manager = get_job_manager()

    try:
        job_manager.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

        # Get STT service and transcribe
        stt_service = get_stt_service()

        job_manager.update_job(job_id, progress=30)

        result = stt_service.transcribe(request)

        job_manager.update_job(job_id, progress=80)

        if not result.success:
            job_manager.update_job(
                job_id,
                status=JobStatus.FAILED,
                error=result.error
            )
            return

        # Build response based on output type
        if result.output_type == "json":
            job_manager.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                result={"type": "json", "data": result.data}
            )
        else:  # SRT
            # Use original filename for output
            srt_filename = Path(original_filename).stem + ".srt"
            job_manager.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                result={
                    "type": "srt",
                    "content": result.content,
                    "filename": srt_filename,
                    "metadata": {
                        "total_time_ms": result.total_time_ms,
                        "inference_time_ms": result.inference_time_ms,
                        "audio_duration_s": result.audio_duration_s,
                    }
                }
            )

        logger.info(f"Job {job_id} completed in {result.total_time_ms:.1f}ms")

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


@router.post("/", tags=["Subtitles"])
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

    # Create job
    job_manager = get_job_manager()
    job = job_manager.create_job(format=format, filename=audio_file.filename)

    # Build transcription request
    request = TranscriptionRequest(
        audio_path=temp_file_path,
        output_format=format,
        engine=engine,
        model_size=model_size,
        compute_type=compute_type,
        language=language,
        vad_filter=vad_filter,
        word_timestamps=word_timestamps,
        batch_size=batch_size,
        beam_size=beam_size,
        temperature=temperature,
        best_of=best_of,
        condition_on_previous_text=condition_on_previous_text,
        no_speech_threshold=no_speech_threshold,
        compression_ratio_threshold=compression_ratio_threshold,
        logprob_threshold=logprob_threshold,
        initial_prompt=initial_prompt,
        word_level=word_level,
        max_line_width=max_line_width,
        max_line_count=max_line_count,
        adjust_timing=adjust_timing,
        split_by_punctuation=split_by_punctuation,
    )

    # Submit to thread pool
    executor.submit(
        process_subtitle_job,
        job.id,
        temp_file_path,
        audio_file.filename,
        request,
    )

    logger.info(f"Submitted job {job.id} for {audio_file.filename}")

    return JSONResponse(content={
        "job_id": job.id,
        "status": job.status.value,
        "message": "Job submitted successfully"
    })


@router.get("/jobs/{job_id}", tags=["Jobs"])
async def get_job_status(job_id: str):
    """Get the status of a subtitle generation job."""
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
    """List all jobs (for debugging)."""
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
