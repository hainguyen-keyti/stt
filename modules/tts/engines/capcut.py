"""
CapCut TTS Engine (via TTSVibes)

Uses TTSVibes API for high-quality Vietnamese TTS synthesis.
Based on CapCut's TTS technology.
"""

import base64
import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Optional, List

import requests

from modules.tts.engines.base import (
    TTSEngine,
    VoiceInfo,
    VoiceGender,
    SynthesisResult,
)

logger = logging.getLogger(__name__)

# TTSVibes API configuration
TTSVIBES_URL = "https://ttsvibes.com/?/generate"
TTSVIBES_HEADERS = {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://ttsvibes.com",
    "referer": "https://ttsvibes.com/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "x-sveltekit-action": "true",
}
TTSVIBES_COOKIES = {
    "__vdpl": "dpl_2N59RzhKZKqRw8k57sthHGRZarQd"
}

# Vietnamese voices from CapCut/TTSVibes
CAPCUT_VOICES = [
    VoiceInfo(
        id="tt-BV074_streaming",
        name="CapCut Nữ",
        language="vi-VN",
        gender=VoiceGender.FEMALE,
        engine="capcut",
        description="Vietnamese female voice - CapCut/TikTok style",
        sample_rate=24000,
    ),
    VoiceInfo(
        id="tt-BV075_streaming",
        name="CapCut Nam",
        language="vi-VN",
        gender=VoiceGender.MALE,
        engine="capcut",
        description="Vietnamese male voice - CapCut/TikTok style",
        sample_rate=24000,
    ),
]


class CapCutTTSEngine(TTSEngine):
    """
    CapCut TTS Engine via TTSVibes API.

    Features:
    - High quality Vietnamese voices (male + female)
    - TikTok/CapCut style natural voices
    - No API key required
    - Fast synthesis (~2-3 seconds per request)
    """

    def __init__(self):
        self._voices = {v.id: v for v in CAPCUT_VOICES}
        self._session = requests.Session()
        self._session.headers.update(TTSVIBES_HEADERS)
        self._session.cookies.update(TTSVIBES_COOKIES)

    @property
    def name(self) -> str:
        return "capcut"

    @property
    def display_name(self) -> str:
        return "CapCut TTS"

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
        Synthesize text using CapCut TTS via TTSVibes API.

        Args:
            text: Text to synthesize
            voice_id: Voice ID (e.g., "tt-BV074_streaming")
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

            # Make API request
            data = {
                "selectedVoiceValue": voice_id,
                "text": text
            }

            response = self._session.post(
                TTSVIBES_URL,
                data=data,
                timeout=30
            )

            if response.status_code != 200:
                return SynthesisResult(
                    success=False,
                    error=f"API error: {response.status_code} - {response.text[:200]}",
                    processing_time_ms=(time.time() - start_time) * 1000,
                    voice_id=voice_id,
                    text=text,
                )

            # Parse JSON response
            try:
                resp_json = response.json()
                if resp_json.get("type") != "success":
                    return SynthesisResult(
                        success=False,
                        error=f"API returned non-success: {resp_json.get('type')}",
                        processing_time_ms=(time.time() - start_time) * 1000,
                        voice_id=voice_id,
                        text=text,
                    )

                # Parse the nested data - it's a JSON string containing an array
                # Format: [{"message":1,"data":2}, "success message", "base64_audio_data"]
                data_str = resp_json.get("data", "")
                data_array = json.loads(data_str)

                if len(data_array) < 3:
                    return SynthesisResult(
                        success=False,
                        error="Invalid response format - missing audio data",
                        processing_time_ms=(time.time() - start_time) * 1000,
                        voice_id=voice_id,
                        text=text,
                    )

                # Audio is base64 encoded at index 2
                audio_base64 = data_array[2]
                audio_data = base64.b64decode(audio_base64)

            except (json.JSONDecodeError, KeyError, IndexError) as e:
                return SynthesisResult(
                    success=False,
                    error=f"Failed to parse API response: {str(e)}",
                    processing_time_ms=(time.time() - start_time) * 1000,
                    voice_id=voice_id,
                    text=text,
                )

            # Save audio to file
            with open(output_path, "wb") as f:
                f.write(audio_data)

            # Apply pitch/speed adjustment if needed
            if pitch != 0 or speed != 1.0:
                output_path = await self._apply_audio_effects(
                    output_path, pitch, speed
                )
                # Re-read processed audio
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

        except requests.Timeout:
            return SynthesisResult(
                success=False,
                error="Request timeout - API took too long to respond",
                processing_time_ms=(time.time() - start_time) * 1000,
                voice_id=voice_id,
                text=text,
            )
        except requests.RequestException as e:
            logger.error(f"CapCut TTS request failed: {e}", exc_info=True)
            return SynthesisResult(
                success=False,
                error=f"Request failed: {str(e)}",
                processing_time_ms=(time.time() - start_time) * 1000,
                voice_id=voice_id,
                text=text,
            )
        except Exception as e:
            logger.error(f"CapCut TTS synthesis failed: {e}", exc_info=True)
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
                # Change playback speed by modifying frame_rate
                # speed < 1.0 = slower (longer audio), speed > 1.0 = faster (shorter audio)
                # Multiply frame_rate by speed: lower rate = slower playback
                new_frame_rate = int(audio.frame_rate * speed)
                audio = audio._spawn(
                    audio.raw_data,
                    overrides={"frame_rate": new_frame_rate}
                )
                # Note: Don't resample back - keep the new frame_rate for correct playback

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

    def cleanup(self):
        """Clean up session."""
        if self._session:
            self._session.close()
