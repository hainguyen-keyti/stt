"""
Microsoft Edge TTS Engine

Uses edge-tts library for high-quality TTS synthesis.
Supports Vietnamese with male and female voices.
"""

import asyncio
import logging
import tempfile
import time
from pathlib import Path
from typing import Optional, List

from modules.tts.engines.base import (
    TTSEngine,
    VoiceInfo,
    VoiceGender,
    SynthesisResult,
)

logger = logging.getLogger(__name__)

# Check if edge-tts is available
EDGE_TTS_AVAILABLE = False
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    logger.warning("edge-tts not installed. Install with: pip install edge-tts")


# Vietnamese voices from Edge TTS
VIETNAMESE_VOICES = [
    VoiceInfo(
        id="vi-VN-HoaiMyNeural",
        name="Hoai My",
        language="vi-VN",
        gender=VoiceGender.FEMALE,
        engine="edge",
        description="Vietnamese female voice - natural and clear",
        sample_rate=24000,
    ),
    VoiceInfo(
        id="vi-VN-NamMinhNeural",
        name="Nam Minh",
        language="vi-VN",
        gender=VoiceGender.MALE,
        engine="edge",
        description="Vietnamese male voice - professional",
        sample_rate=24000,
    ),
]


class EdgeTTSEngine(TTSEngine):
    """
    Microsoft Edge TTS Engine.

    Features:
    - High quality neural voices
    - Vietnamese support (2 voices: male + female)
    - No API key required
    - Pitch adjustment via audio processing
    """

    def __init__(self):
        if not EDGE_TTS_AVAILABLE:
            raise ImportError(
                "edge-tts is not installed. Install with: pip install edge-tts"
            )
        self._voices = {v.id: v for v in VIETNAMESE_VOICES}

    @property
    def name(self) -> str:
        return "edge"

    @property
    def display_name(self) -> str:
        return "Microsoft Edge TTS"

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
        Synthesize text using Edge TTS.

        Args:
            text: Text to synthesize
            voice_id: Voice ID (e.g., "vi-VN-HoaiMyNeural")
            output_path: Path to save audio file
            pitch: Pitch adjustment in semitones (-12 to +12)
            speed: Speed multiplier (0.5 to 2.0)

        Returns:
            SynthesisResult with audio
        """
        start_time = time.time()

        try:
            # Validate voice
            if voice_id not in self._voices:
                return SynthesisResult(
                    success=False,
                    error=f"Voice not found: {voice_id}",
                    voice_id=voice_id,
                    text=text,
                )

            # Generate temp path if not provided
            if output_path is None:
                temp_file = tempfile.NamedTemporaryFile(
                    suffix=".mp3", delete=False
                )
                output_path = temp_file.name
                temp_file.close()

            # Generate audio with Edge TTS
            communicate = edge_tts.Communicate(text, voice_id)
            await communicate.save(output_path)

            # Apply pitch adjustment if needed
            if pitch != 0 or speed != 1.0:
                output_path = await self._apply_audio_effects(
                    output_path, pitch, speed
                )

            # Read audio data
            with open(output_path, "rb") as f:
                audio_data = f.read()

            processing_time_ms = (time.time() - start_time) * 1000

            return SynthesisResult(
                success=True,
                audio_path=output_path,
                audio_data=audio_data,
                format="mp3",
                sample_rate=24000,
                processing_time_ms=processing_time_ms,
                voice_id=voice_id,
                text=text,
                pitch=pitch,
                speed=speed,
            )

        except Exception as e:
            logger.error(f"Edge TTS synthesis failed: {e}", exc_info=True)
            return SynthesisResult(
                success=False,
                error=str(e),
                processing_time_ms=(time.time() - start_time) * 1000,
                voice_id=voice_id,
                text=text,
            )

    async def _apply_audio_effects(
        self, audio_path: str, pitch: int, speed: float
    ) -> str:
        """
        Apply pitch and speed adjustments using pydub.

        Args:
            audio_path: Path to audio file
            pitch: Pitch in semitones
            speed: Speed multiplier

        Returns:
            Path to processed audio file
        """
        try:
            from pydub import AudioSegment

            audio = AudioSegment.from_mp3(audio_path)

            # Apply pitch shift
            if pitch != 0:
                # Pitch shift by changing sample rate then resampling
                ratio = 2 ** (pitch / 12.0)
                new_sample_rate = int(audio.frame_rate * ratio)
                audio = audio._spawn(
                    audio.raw_data,
                    overrides={"frame_rate": new_sample_rate}
                ).set_frame_rate(audio.frame_rate)

            # Apply speed change
            if speed != 1.0:
                audio = audio.speedup(playback_speed=speed)

            # Save to new file
            output_path = audio_path.replace(".mp3", "_processed.mp3")
            audio.export(output_path, format="mp3")

            # Remove original if different
            if output_path != audio_path:
                Path(audio_path).unlink(missing_ok=True)

            return output_path

        except ImportError:
            logger.warning("pydub not installed, skipping audio effects")
            return audio_path
        except Exception as e:
            logger.warning(f"Failed to apply audio effects: {e}")
            return audio_path

    def list_voices(self, language: Optional[str] = None) -> List[VoiceInfo]:
        """List available Vietnamese voices."""
        if language is None:
            return list(self._voices.values())

        # Filter by language
        lang_lower = language.lower()
        return [
            v for v in self._voices.values()
            if lang_lower in v.language.lower()
        ]

    def get_voice(self, voice_id: str) -> Optional[VoiceInfo]:
        """Get voice by ID."""
        return self._voices.get(voice_id)
