"""
TTS Engine Base Classes

Abstract base class and data models for TTS engines.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class VoiceGender(str, Enum):
    """Voice gender."""
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


@dataclass
class VoiceInfo:
    """Information about a TTS voice."""
    id: str                      # Voice ID used by engine
    name: str                    # Display name
    language: str                # Language code (e.g., "vi-VN")
    gender: VoiceGender          # Male/Female/Neutral
    engine: str                  # Engine name (e.g., "edge", "gtts")
    description: str = ""        # Optional description
    sample_rate: int = 22050     # Default sample rate

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "language": self.language,
            "gender": self.gender.value,
            "engine": self.engine,
            "description": self.description,
        }


@dataclass
class SynthesisResult:
    """Result from TTS synthesis."""
    success: bool
    audio_path: Optional[str] = None
    audio_data: Optional[bytes] = None
    format: str = "mp3"
    sample_rate: int = 22050
    duration_ms: float = 0.0
    processing_time_ms: float = 0.0
    error: Optional[str] = None

    # Metadata
    voice_id: str = ""
    text: str = ""
    pitch: int = 0
    speed: float = 1.0


class TTSEngine(ABC):
    """
    Abstract base class for TTS engines.

    All TTS engines must implement:
    - synthesize(): Generate speech from text
    - list_voices(): List available voices
    - get_voice(): Get voice info by ID
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name (e.g., 'edge', 'gtts')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable engine name."""
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: Optional[str] = None,
        pitch: int = 0,
        speed: float = 1.0,
        **kwargs
    ) -> SynthesisResult:
        """
        Synthesize text to speech.

        Args:
            text: Text to synthesize
            voice_id: Voice ID to use
            output_path: Optional path to save audio (returns audio_data if None)
            pitch: Pitch adjustment in semitones (-12 to +12)
            speed: Speed multiplier (0.5 to 2.0)

        Returns:
            SynthesisResult with audio data or path
        """
        pass

    @abstractmethod
    def list_voices(self, language: Optional[str] = None) -> List[VoiceInfo]:
        """
        List available voices.

        Args:
            language: Optional language filter (e.g., "vi", "vi-VN")

        Returns:
            List of VoiceInfo objects
        """
        pass

    def get_voice(self, voice_id: str) -> Optional[VoiceInfo]:
        """
        Get voice info by ID.

        Args:
            voice_id: Voice ID to look up

        Returns:
            VoiceInfo or None if not found
        """
        for voice in self.list_voices():
            if voice.id == voice_id:
                return voice
        return None

    def cleanup(self):
        """Clean up engine resources."""
        pass
