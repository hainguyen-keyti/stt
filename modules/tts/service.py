"""
TTS Service

High-level service for Text-to-Speech synthesis.
Manages multiple TTS engines and provides unified API.
"""

import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any

from modules.tts.engines.base import (
    TTSEngine,
    VoiceInfo,
    VoiceGender,
    SynthesisResult,
)

logger = logging.getLogger(__name__)

# Check available engines
EDGE_TTS_AVAILABLE = False
GTTS_AVAILABLE = False

try:
    from modules.tts.engines.edge_tts import EdgeTTSEngine, EDGE_TTS_AVAILABLE as _EDGE
    EDGE_TTS_AVAILABLE = _EDGE
except ImportError:
    pass

try:
    from modules.tts.engines.google_tts import GoogleTTSEngine, GTTS_AVAILABLE as _GTTS
    GTTS_AVAILABLE = _GTTS
except ImportError:
    pass


@dataclass
class TTSRequest:
    """Request for TTS synthesis."""
    text: str
    voice_id: str = "vi-VN-HoaiMyNeural"  # Default: Edge TTS female
    pitch: int = 0                         # Semitones: -12 to +12
    speed: float = 1.0                     # Speed: 0.5 to 2.0
    output_format: str = "mp3"             # mp3, wav
    output_path: Optional[str] = None      # Auto-generate if None

    def validate(self) -> Optional[str]:
        """Validate request. Returns error message or None."""
        if not self.text or not self.text.strip():
            return "Text cannot be empty"
        if len(self.text) > 5000:
            return "Text too long (max 5000 characters)"
        if not -12 <= self.pitch <= 12:
            return "Pitch must be between -12 and +12 semitones"
        if not 0.5 <= self.speed <= 2.0:
            return "Speed must be between 0.5 and 2.0"
        if self.output_format not in ["mp3", "wav"]:
            return "Output format must be mp3 or wav"
        return None


@dataclass
class TTSResult:
    """Result from TTS synthesis."""
    success: bool
    audio_path: Optional[str] = None
    audio_data: Optional[bytes] = None
    format: str = "mp3"
    duration_ms: float = 0.0
    processing_time_ms: float = 0.0
    error: Optional[str] = None

    # Request info
    voice_id: str = ""
    voice_name: str = ""
    engine: str = ""
    text: str = ""
    pitch: int = 0
    speed: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "format": self.format,
            "duration_ms": self.duration_ms,
            "processing_time_ms": self.processing_time_ms,
            "error": self.error,
            "voice_id": self.voice_id,
            "voice_name": self.voice_name,
            "engine": self.engine,
            "pitch": self.pitch,
            "speed": self.speed,
        }


class TTSService:
    """
    Text-to-Speech Service.

    Provides unified API for TTS synthesis with:
    - Multiple engine support (Edge TTS, gTTS)
    - Voice selection
    - Pitch and speed adjustment
    """

    def __init__(self):
        self._engines: Dict[str, TTSEngine] = {}
        self._voices: Dict[str, VoiceInfo] = {}
        self._init_engines()

    def _init_engines(self):
        """Initialize available TTS engines."""
        # Try Edge TTS first (better quality)
        if EDGE_TTS_AVAILABLE:
            try:
                from modules.tts.engines.edge_tts import EdgeTTSEngine
                engine = EdgeTTSEngine()
                self._engines["edge"] = engine
                for voice in engine.list_voices():
                    self._voices[voice.id] = voice
                logger.info("Edge TTS engine initialized")
            except Exception as e:
                logger.warning(f"Failed to init Edge TTS: {e}")

        # Try gTTS
        if GTTS_AVAILABLE:
            try:
                from modules.tts.engines.google_tts import GoogleTTSEngine
                engine = GoogleTTSEngine()
                self._engines["gtts"] = engine
                for voice in engine.list_voices():
                    self._voices[voice.id] = voice
                logger.info("Google TTS engine initialized")
            except Exception as e:
                logger.warning(f"Failed to init gTTS: {e}")

        if not self._engines:
            logger.warning(
                "No TTS engines available. "
                "Install with: pip install edge-tts gTTS pydub"
            )

    def _get_engine_for_voice(self, voice_id: str) -> Optional[TTSEngine]:
        """Get the engine that provides a voice."""
        voice = self._voices.get(voice_id)
        if voice:
            return self._engines.get(voice.engine)
        return None

    async def synthesize(self, request: TTSRequest) -> TTSResult:
        """
        Synthesize text to speech.

        Args:
            request: TTSRequest with text and options

        Returns:
            TTSResult with audio data
        """
        # Validate request
        error = request.validate()
        if error:
            return TTSResult(success=False, error=error)

        # Get engine for voice
        engine = self._get_engine_for_voice(request.voice_id)
        if not engine:
            # Try default voice
            if self._engines:
                engine = list(self._engines.values())[0]
                voice_id = list(engine.list_voices())[0].id
                logger.warning(
                    f"Voice {request.voice_id} not found, using {voice_id}"
                )
                request.voice_id = voice_id
            else:
                return TTSResult(
                    success=False,
                    error="No TTS engine available"
                )

        # Get voice info
        voice = self._voices.get(request.voice_id)

        # Synthesize
        result = await engine.synthesize(
            text=request.text,
            voice_id=request.voice_id,
            output_path=request.output_path,
            pitch=request.pitch,
            speed=request.speed,
        )

        return TTSResult(
            success=result.success,
            audio_path=result.audio_path,
            audio_data=result.audio_data,
            format=result.format,
            duration_ms=result.duration_ms,
            processing_time_ms=result.processing_time_ms,
            error=result.error,
            voice_id=request.voice_id,
            voice_name=voice.name if voice else "",
            engine=engine.name,
            text=request.text,
            pitch=request.pitch,
            speed=request.speed,
        )

    def list_voices(
        self,
        language: Optional[str] = None,
        gender: Optional[VoiceGender] = None,
        engine: Optional[str] = None,
    ) -> List[VoiceInfo]:
        """
        List available voices with optional filters.

        Args:
            language: Filter by language (e.g., "vi", "vi-VN")
            gender: Filter by gender (male, female)
            engine: Filter by engine (edge, gtts)

        Returns:
            List of VoiceInfo objects
        """
        voices = list(self._voices.values())

        if language:
            lang_lower = language.lower()
            voices = [v for v in voices if lang_lower in v.language.lower()]

        if gender:
            voices = [v for v in voices if v.gender == gender]

        if engine:
            voices = [v for v in voices if v.engine == engine]

        return voices

    def get_voice(self, voice_id: str) -> Optional[VoiceInfo]:
        """Get voice info by ID."""
        return self._voices.get(voice_id)

    def list_engines(self) -> List[Dict[str, str]]:
        """List available TTS engines."""
        return [
            {"name": e.name, "display_name": e.display_name}
            for e in self._engines.values()
        ]

    def is_available(self) -> bool:
        """Check if any TTS engine is available."""
        return len(self._engines) > 0

    def cleanup(self):
        """Clean up resources."""
        for engine in self._engines.values():
            engine.cleanup()


# Global service instance
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get global TTS service instance."""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
