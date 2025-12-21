"""
Text-to-Speech (TTS) Module

Provides TTS synthesis using multiple engines:
- Edge TTS (Microsoft) - High quality, free, Vietnamese voices
- gTTS (Google) - Simple, reliable

Features:
- Multiple voice options (male/female)
- Pitch adjustment for voice customization
- Speed control
"""

__version__ = "1.0.0"

from modules.tts.service import (
    TTSService,
    TTSRequest,
    TTSResult,
    get_tts_service,
)
from modules.tts.engines.base import (
    TTSEngine,
    VoiceInfo,
)

__all__ = [
    # Service
    "TTSService",
    "TTSRequest",
    "TTSResult",
    "get_tts_service",
    # Engine base
    "TTSEngine",
    "VoiceInfo",
]
