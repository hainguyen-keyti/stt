"""
Vivibe TTS Engine (via LucyLab API)

Uses LucyLab API for high-quality Vietnamese TTS synthesis.
Supports custom user voices from Vivibe platform.
"""

import base64
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, List, Dict

import requests

from modules.tts.engines.base import (
    TTSEngine,
    VoiceInfo,
    VoiceGender,
    SynthesisResult,
)

logger = logging.getLogger(__name__)

# Firebase configuration for token refresh
FIREBASE_API_KEY = "AIzaSyBEfuL7qePYp9WlBFPjVLXLKN5Us6rr6tg"
FIREBASE_REFRESH_URL = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"

# LucyLab API configuration
LUCYLAB_API_URL = "https://api.lucylab.io/json-rpc"
LUCYLAB_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "origin": "https://www.vivibe.app",
    "pragma": "no-cache",
    "referer": "https://www.vivibe.app/",
    "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
}

# Load token and refresh token from environment
VIVIBE_TOKEN = os.getenv("VIVIBE_TOKEN", "")
VIVIBE_REFRESH_TOKEN = os.getenv("VIVIBE_REFRESH_TOKEN", "")

# Vietnamese voices from Vivibe/LucyLab
# Voice IDs are from Vivibe platform (userVoiceId)
VIVIBE_VOICES = [
    VoiceInfo(
        id="cLZiqtzLcKYqwYrWJemAJH",
        name="Vivibe Nữ",
        language="vi-VN",
        gender=VoiceGender.FEMALE,
        engine="vivibe",
        description="Vivibe Vietnamese female voice",
        sample_rate=24000,
    ),
    VoiceInfo(
        id="6QzFMn95VAXF32Yg3HxEMj",
        name="Vivibe Nam",
        language="vi-VN",
        gender=VoiceGender.MALE,
        engine="vivibe",
        description="Vivibe Vietnamese male voice",
        sample_rate=24000,
    ),
]


class VivibeTTSEngine(TTSEngine):
    """
    Vivibe TTS Engine via LucyLab API.

    Features:
    - High quality Vietnamese voices
    - Custom user voice support
    - Fast synthesis (~0.5-2 seconds)
    - Requires authentication token
    """

    def __init__(self, token: Optional[str] = None, refresh_token: Optional[str] = None):
        """
        Initialize Vivibe TTS Engine.

        Args:
            token: Bearer token for authentication (uses VIVIBE_TOKEN from env if not provided)
            refresh_token: Refresh token for auto-renewal (uses VIVIBE_REFRESH_TOKEN from env if not provided)
        """
        self._token = token or VIVIBE_TOKEN
        self._refresh_token = refresh_token or VIVIBE_REFRESH_TOKEN
        self._token_expires_at: Optional[float] = None
        self._voices = {v.id: v for v in VIVIBE_VOICES}
        self._session = requests.Session()
        self._session.headers.update(LUCYLAB_HEADERS)

    def set_token(self, token: str):
        """Set authentication token."""
        self._token = token
        self._token_expires_at = None  # Reset expiry

    def set_refresh_token(self, refresh_token: str):
        """Set refresh token for auto-renewal."""
        self._refresh_token = refresh_token

    def _refresh_id_token(self) -> bool:
        """
        Refresh the ID token using the refresh token.

        Returns:
            True if refresh successful, False otherwise
        """
        if not self._refresh_token:
            logger.warning("No refresh token available for auto-renewal")
            return False

        try:
            response = requests.post(
                FIREBASE_REFRESH_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                self._token = result.get("id_token")
                # Update refresh token if a new one is provided
                if result.get("refresh_token"):
                    self._refresh_token = result["refresh_token"]
                # Set expiry time (token expires in 3600 seconds, refresh 5 min before)
                expires_in = int(result.get("expires_in", 3600))
                self._token_expires_at = time.time() + expires_in - 300
                logger.info("Vivibe token refreshed successfully")
                return True
            else:
                logger.error(f"Failed to refresh token: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False

    def _ensure_valid_token(self) -> bool:
        """
        Ensure we have a valid token, refreshing if needed.

        Returns:
            True if token is valid, False otherwise
        """
        # If no token at all, try to refresh
        if not self._token:
            return self._refresh_id_token()

        # If we have expiry info and token is about to expire, refresh
        if self._token_expires_at and time.time() >= self._token_expires_at:
            logger.info("Token expired or about to expire, refreshing...")
            return self._refresh_id_token()

        return True

    @property
    def name(self) -> str:
        return "vivibe"

    @property
    def display_name(self) -> str:
        return "Vivibe TTS"

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
        Synthesize text using Vivibe TTS via LucyLab API.

        Args:
            text: Text to synthesize
            voice_id: Voice ID (uses user_voice_id for API call)
            output_path: Path to save audio file
            pitch: Pitch adjustment (not supported by API, ignored)
            speed: Speed multiplier (0.5 to 2.0)

        Returns:
            SynthesisResult with audio
        """
        start_time = time.time()

        # Ensure we have a valid token
        self._ensure_valid_token()

        # Check token after potential refresh
        if not self._token:
            return SynthesisResult(
                success=False,
                error="Vivibe TTS requires authentication token. Set VIVIBE_REFRESH_TOKEN in .env for auto-renewal.",
                voice_id=voice_id,
                text=text,
            )

        try:
            # Generate temp path if not provided (API returns WAV)
            if output_path is None:
                temp_file = tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False
                )
                output_path = temp_file.name
                temp_file.close()

            # Prepare request - voice_id is already the userVoiceId from Vivibe platform
            headers = {**LUCYLAB_HEADERS, "authorization": f"Bearer {self._token}"}
            payload = {
                "method": "tts",
                "input": {
                    "text": text,
                    "userVoiceId": voice_id,
                    "speed": speed,
                    "blockVersion": 0
                }
            }

            # Make API request
            response = self._session.post(
                LUCYLAB_API_URL,
                json=payload,
                headers=headers,
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

            # Parse response
            try:
                resp_json = response.json()

                # Check for error in response
                if "error" in resp_json:
                    error_data = resp_json.get("error", {})
                    error_msg = error_data.get("message", str(error_data)) if isinstance(error_data, dict) else str(error_data)

                    # Check if token expired - try to refresh and retry once
                    if "expired" in error_msg.lower() or "token" in error_msg.lower():
                        logger.info("Token appears expired, attempting refresh...")
                        if self._refresh_id_token():
                            # Retry the request with new token
                            headers["authorization"] = f"Bearer {self._token}"
                            response = self._session.post(
                                LUCYLAB_API_URL,
                                json=payload,
                                headers=headers,
                                timeout=30
                            )
                            if response.status_code == 200:
                                resp_json = response.json()
                                if "error" not in resp_json:
                                    # Continue to process successful response
                                    pass
                                else:
                                    return SynthesisResult(
                                        success=False,
                                        error=f"API error after token refresh: {resp_json.get('error')}",
                                        processing_time_ms=(time.time() - start_time) * 1000,
                                        voice_id=voice_id,
                                        text=text,
                                    )
                            else:
                                return SynthesisResult(
                                    success=False,
                                    error=f"API error after token refresh: {response.status_code}",
                                    processing_time_ms=(time.time() - start_time) * 1000,
                                    voice_id=voice_id,
                                    text=text,
                                )
                        else:
                            return SynthesisResult(
                                success=False,
                                error=f"Token expired and refresh failed. Set VIVIBE_REFRESH_TOKEN in .env",
                                processing_time_ms=(time.time() - start_time) * 1000,
                                voice_id=voice_id,
                                text=text,
                            )
                    else:
                        return SynthesisResult(
                            success=False,
                            error=f"API error: {error_msg}",
                            processing_time_ms=(time.time() - start_time) * 1000,
                            voice_id=voice_id,
                            text=text,
                        )

                # Get audio URL from response (API returns "url" not "audioUrl")
                result = resp_json.get("result", {})
                audio_url = result.get("url") or result.get("audioUrl")

                if not audio_url:
                    return SynthesisResult(
                        success=False,
                        error="No audio URL in response",
                        processing_time_ms=(time.time() - start_time) * 1000,
                        voice_id=voice_id,
                        text=text,
                    )

                # Download audio file
                audio_response = self._session.get(audio_url, timeout=30)
                if audio_response.status_code != 200:
                    return SynthesisResult(
                        success=False,
                        error=f"Failed to download audio: {audio_response.status_code}",
                        processing_time_ms=(time.time() - start_time) * 1000,
                        voice_id=voice_id,
                        text=text,
                    )

                audio_data = audio_response.content

            except (json.JSONDecodeError, KeyError) as e:
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

            # Apply pitch adjustment if needed (using pydub)
            if pitch != 0:
                output_path = await self._apply_pitch(output_path, pitch)
                with open(output_path, "rb") as f:
                    audio_data = f.read()

            processing_time_ms = (time.time() - start_time) * 1000

            # Determine format from URL or default to wav
            audio_format = "wav"
            if audio_url and ".mp3" in audio_url:
                audio_format = "mp3"

            return SynthesisResult(
                success=True,
                audio_path=output_path,
                audio_data=audio_data,
                format=audio_format,
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
            logger.error(f"Vivibe TTS request failed: {e}", exc_info=True)
            return SynthesisResult(
                success=False,
                error=f"Request failed: {str(e)}",
                processing_time_ms=(time.time() - start_time) * 1000,
                voice_id=voice_id,
                text=text,
            )
        except Exception as e:
            logger.error(f"Vivibe TTS synthesis failed: {e}", exc_info=True)
            return SynthesisResult(
                success=False,
                error=str(e),
                processing_time_ms=(time.time() - start_time) * 1000,
                voice_id=voice_id,
                text=text,
            )

    async def _apply_pitch(self, audio_path: str, pitch: int) -> str:
        """
        Apply pitch adjustment using pydub.

        Args:
            audio_path: Path to audio file
            pitch: Pitch in semitones

        Returns:
            Path to processed audio file
        """
        try:
            from pydub import AudioSegment

            audio = AudioSegment.from_mp3(audio_path)

            # Pitch shift by changing sample rate then resampling
            ratio = 2 ** (pitch / 12.0)
            new_sample_rate = int(audio.frame_rate * ratio)
            audio = audio._spawn(
                audio.raw_data,
                overrides={"frame_rate": new_sample_rate}
            ).set_frame_rate(audio.frame_rate)

            # Save to new file
            output_path = audio_path.replace(".mp3", "_processed.mp3")
            audio.export(output_path, format="mp3")

            # Remove original if different
            if output_path != audio_path:
                Path(audio_path).unlink(missing_ok=True)

            return output_path

        except ImportError:
            logger.warning("pydub not installed, skipping pitch adjustment")
            return audio_path
        except Exception as e:
            logger.warning(f"Failed to apply pitch adjustment: {e}")
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
