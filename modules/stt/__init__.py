"""
Speech-to-Text Module

Core library for speech recognition and subtitle generation.
Supports multiple ASR engines (faster-whisper, openai-whisper).
"""

__version__ = "4.0.0"

from modules.stt.models import get_model_manager
from modules.stt.formatters import SRTFormatter
from modules.stt.service import (
    STTService,
    TranscriptionRequest,
    TranscriptionResult,
    get_stt_service,
)

__all__ = [
    "get_model_manager",
    "SRTFormatter",
    "STTService",
    "TranscriptionRequest",
    "TranscriptionResult",
    "get_stt_service",
]
