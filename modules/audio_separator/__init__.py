"""
Audio Separator Module

Separate audio into vocal and instrumental stems, with volume adjustment.
Optimized for CPU usage using Spleeter.
"""

__version__ = "1.0.0"

from modules.audio_separator.service import (
    AudioSeparatorService,
    SeparationRequest,
    RemixRequest,
    ServiceResult,
    get_separator_service,
)
from modules.audio_separator.mixer import (
    AudioMixer,
    MixConfig,
    create_mixer,
)
from modules.audio_separator.engines.base import (
    SeparatorEngine,
    SeparationResult,
    EngineInfo,
)

__all__ = [
    # Service
    "AudioSeparatorService",
    "SeparationRequest",
    "RemixRequest",
    "ServiceResult",
    "get_separator_service",
    # Mixer
    "AudioMixer",
    "MixConfig",
    "create_mixer",
    # Engine base
    "SeparatorEngine",
    "SeparationResult",
    "EngineInfo",
]
