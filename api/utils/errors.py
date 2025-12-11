"""
Custom Exception Classes and Error Handlers

Defines application-specific exceptions and FastAPI error handlers
for consistent error responses.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger(__name__)


# Custom Exception Classes
class AudioProcessingError(Exception):
    """Raised when audio processing fails"""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ModelLoadError(Exception):
    """Raised when model loading fails"""

    def __init__(self, message: str, model_name: str = None):
        self.message = message
        self.model_name = model_name
        super().__init__(self.message)


class InsufficientVRAMError(Exception):
    """Raised when there's not enough VRAM for operation"""

    def __init__(self, required_mb: float, available_mb: float):
        self.required_mb = required_mb
        self.available_mb = available_mb
        self.message = (
            f"Insufficient VRAM: {required_mb}MB required, "
            f"{available_mb}MB available"
        )
        super().__init__(self.message)


class UnsupportedAudioFormatError(Exception):
    """Raised when audio format is not supported"""

    def __init__(self, format: str):
        self.format = format
        self.message = f"Unsupported audio format: {format}"
        super().__init__(self.message)


class FileTooLargeError(Exception):
    """Raised when uploaded file exceeds size limit"""

    def __init__(self, size_mb: float, max_size_mb: float = 500):
        self.size_mb = size_mb
        self.max_size_mb = max_size_mb
        self.message = (
            f"File size {size_mb}MB exceeds maximum {max_size_mb}MB"
        )
        super().__init__(self.message)


# Error Response Helper
def create_error_response(
    error_code: str, message: str, remediation: str = None, details: dict = None
) -> dict:
    """
    Create standardized error response.

    Args:
        error_code: Machine-readable error code
        message: Human-readable error message
        remediation: Suggested fix (optional)
        details: Additional error details (optional)

    Returns:
        Standardized error response dict
    """
    response = {"error": error_code, "message": message}

    if remediation:
        response["remediation"] = remediation

    if details:
        response["details"] = details

    return response


# FastAPI Exception Handlers
async def audio_processing_error_handler(
    request: Request, exc: AudioProcessingError
) -> JSONResponse:
    """Handle audio processing errors"""
    logger.error(f"Audio processing error: {exc.message}", extra={"details": exc.details})

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            error_code="audio_processing_error",
            message=exc.message,
            remediation="Please check the audio file format and try again",
            details=exc.details,
        ),
    )


async def model_load_error_handler(
    request: Request, exc: ModelLoadError
) -> JSONResponse:
    """Handle model loading errors"""
    logger.error(f"Model load error: {exc.message}")

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=create_error_response(
            error_code="model_load_error",
            message=exc.message,
            remediation="Model may need to be downloaded. Check logs and retry.",
            details={"model_name": exc.model_name} if exc.model_name else None,
        ),
    )


async def insufficient_vram_error_handler(
    request: Request, exc: InsufficientVRAMError
) -> JSONResponse:
    """Handle insufficient VRAM errors"""
    logger.error(f"Insufficient VRAM: {exc.message}")

    return JSONResponse(
        status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
        content=create_error_response(
            error_code="insufficient_vram",
            message=exc.message,
            remediation="Try using a smaller model size or enable CPU fallback",
            details={
                "required_mb": exc.required_mb,
                "available_mb": exc.available_mb,
            },
        ),
    )


async def unsupported_audio_format_error_handler(
    request: Request, exc: UnsupportedAudioFormatError
) -> JSONResponse:
    """Handle unsupported audio format errors"""
    logger.warning(f"Unsupported audio format: {exc.format}")

    return JSONResponse(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        content=create_error_response(
            error_code="unsupported_media_type",
            message=exc.message,
            remediation="Supported formats: MP3, WAV, M4A, FLAC. Please convert your file.",
            details={"format": exc.format},
        ),
    )


async def file_too_large_error_handler(
    request: Request, exc: FileTooLargeError
) -> JSONResponse:
    """Handle file too large errors"""
    logger.warning(f"File too large: {exc.size_mb}MB")

    return JSONResponse(
        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        content=create_error_response(
            error_code="file_too_large",
            message=exc.message,
            remediation="Please split the file or compress the audio",
            details={
                "file_size_mb": exc.size_mb,
                "max_size_mb": exc.max_size_mb,
            },
        ),
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")

    # Extract field-level errors
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({"field": field, "message": error["msg"], "type": error["type"]})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            error_code="validation_error",
            message="Request validation failed",
            remediation="Please check the request parameters and try again",
            details={"errors": errors},
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    logger.exception("Unexpected error occurred", exc_info=exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            error_code="internal_server_error",
            message="An unexpected error occurred",
            remediation="Please try again. If the problem persists, contact support.",
        ),
    )


# Register all exception handlers
def register_exception_handlers(app):
    """
    Register all custom exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(AudioProcessingError, audio_processing_error_handler)
    app.add_exception_handler(ModelLoadError, model_load_error_handler)
    app.add_exception_handler(InsufficientVRAMError, insufficient_vram_error_handler)
    app.add_exception_handler(
        UnsupportedAudioFormatError, unsupported_audio_format_error_handler
    )
    app.add_exception_handler(FileTooLargeError, file_too_large_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Exception handlers registered")
