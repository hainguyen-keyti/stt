"""
Audio Separator API Router

API endpoints for audio source separation and remixing.
"""

import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse

from api.utils.errors import FileTooLargeError, UnsupportedAudioFormatError
from api.utils.jobs import get_job_manager, JobStatus

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Configuration
MAX_FILE_SIZE_MB = 500
SUPPORTED_FORMATS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".opus", ".webm"}

# Thread pool for background processing
executor = ThreadPoolExecutor(max_workers=2)


def process_separation_job(
    job_id: str,
    temp_file_path: str,
    original_filename: str,
    vocal_volume: float,
    instrumental_volume: float,
    output_format: str,
    model: str = None,
):
    """Process audio separation in background thread."""
    from modules.audio_separator import get_separator_service

    job_manager = get_job_manager()

    try:
        job_manager.update_job(job_id, status=JobStatus.PROCESSING, progress=10)

        service = get_separator_service()

        job_manager.update_job(job_id, progress=30)

        # Perform separation and remix
        result = service.separate_and_remix(
            audio_path=temp_file_path,
            vocal_volume=vocal_volume,
            instrumental_volume=instrumental_volume,
            output_format=output_format,
            model=model,
        )

        job_manager.update_job(job_id, progress=90)

        if not result.success:
            job_manager.update_job(
                job_id,
                status=JobStatus.FAILED,
                error=result.error,
            )
            return

        # Read output file for response
        output_filename = Path(original_filename).stem + f"_mixed.{output_format}"

        with open(result.output_path, "rb") as f:
            output_data = f.read()

        # Store result (base64 encode for JSON transport)
        import base64
        job_manager.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            result={
                "type": "audio",
                "format": output_format,
                "filename": output_filename,
                "data": base64.b64encode(output_data).decode("utf-8"),
                "size_bytes": len(output_data),
                "metadata": {
                    "processing_time_ms": result.processing_time_ms,
                    "vocal_volume": vocal_volume,
                    "instrumental_volume": instrumental_volume,
                }
            }
        )

        logger.info(f"Job {job_id} completed in {result.processing_time_ms:.1f}ms")

        # Cleanup output file
        Path(result.output_path).unlink(missing_ok=True)

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        job_manager.update_job(
            job_id,
            status=JobStatus.FAILED,
            error=str(e),
        )

    finally:
        # Cleanup temp input file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")


# Available separation models
AVAILABLE_MODELS = {
    "fast": "1_HP-UVR.pth",      # ~5-10 sec, decent quality
    "balanced": "UVR_MDXNET_Main.onnx",  # ~20 sec, good quality
    "quality": "htdemucs.yaml",   # ~2 min, highest quality
}


@router.post("/", tags=["Audio Separator"])
async def submit_separation_job(
    audio_file: UploadFile = File(..., description="Audio file to process"),
    vocal_volume: float = Form(default=1.0, description="Vocal volume (0.0-2.0)"),
    instrumental_volume: float = Form(default=1.0, description="Instrumental volume (0.0-2.0)"),
    output_format: str = Form(default="mp3", description="Output format (mp3, wav, flac)"),
    model: str = Form(default="fast", description="Separation model (fast, balanced, quality)"),
):
    """
    Submit an audio separation and remix job.

    Separates audio into vocals and instrumental, then remixes with adjusted volumes.

    **Use Cases:**
    - `vocal_volume=0.0`: Remove vocals (karaoke)
    - `vocal_volume=0.5`: Reduce vocals by 50%
    - `instrumental_volume=0.5`: Reduce instrumental by 50%
    - `vocal_volume=1.5`: Boost vocals by 50%

    **Models:**
    - `fast`: 1_HP-UVR.pth (~5-10 sec, decent quality)
    - `balanced`: UVR_MDXNET_Main.onnx (~20 sec, good quality)
    - `quality`: htdemucs.yaml (~2 min, highest quality)

    **Response:**
    ```json
    {
        "job_id": "abc12345",
        "status": "pending",
        "message": "Job submitted successfully"
    }
    ```
    """
    # Validate volumes
    if not 0.0 <= vocal_volume <= 3.0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="vocal_volume must be between 0.0 and 3.0"
        )
    if not 0.0 <= instrumental_volume <= 3.0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="instrumental_volume must be between 0.0 and 3.0"
        )

    # Validate output format
    output_format = output_format.lower()
    if output_format not in ["mp3", "wav", "flac"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="output_format must be mp3, wav, or flac"
        )

    # Validate model
    model = model.lower()
    if model not in AVAILABLE_MODELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"model must be one of: {', '.join(AVAILABLE_MODELS.keys())}"
        )
    model_filename = AVAILABLE_MODELS[model]

    # Validate file size
    file_content = await audio_file.read()
    file_size_mb = len(file_content) / (1024 * 1024)

    if file_size_mb > MAX_FILE_SIZE_MB:
        raise FileTooLargeError(file_size_mb, MAX_FILE_SIZE_MB)

    # Validate audio format
    file_extension = Path(audio_file.filename).suffix.lower()
    if file_extension not in SUPPORTED_FORMATS:
        raise UnsupportedAudioFormatError(file_extension)

    # Save to temp file
    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=file_extension, delete=False
    ) as temp_file:
        temp_file.write(file_content)
        temp_file_path = temp_file.name

    # Create job
    job_manager = get_job_manager()
    job = job_manager.create_job(format=output_format, filename=audio_file.filename)

    # Submit to thread pool
    executor.submit(
        process_separation_job,
        job.id,
        temp_file_path,
        audio_file.filename,
        vocal_volume,
        instrumental_volume,
        output_format,
        model_filename,
    )

    logger.info(f"Submitted separation job {job.id} for {audio_file.filename}")

    return JSONResponse(content={
        "job_id": job.id,
        "status": job.status.value,
        "message": "Job submitted successfully"
    })


@router.get("/jobs/{job_id}", tags=["Audio Separator"])
async def get_job_status(job_id: str):
    """
    Get the status of a separation job.

    **Response (completed):**
    ```json
    {
        "job_id": "abc12345",
        "status": "completed",
        "progress": 100,
        "result": {
            "type": "audio",
            "format": "mp3",
            "filename": "song_mixed.mp3",
            "data": "<base64-encoded-audio>",
            "size_bytes": 1234567
        }
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


@router.get("/jobs", tags=["Audio Separator"])
async def list_jobs():
    """List all separation jobs."""
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
