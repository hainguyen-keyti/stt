"""
Audio Separator Service

High-level service for audio source separation and mixing.
"""

import logging
import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from modules.audio_separator.engines.base import SeparationResult
from modules.audio_separator.mixer import AudioMixer, MixConfig

logger = logging.getLogger(__name__)

# Try to import available engines (prefer Demucs via audio-separator)
DEMUCS_AVAILABLE = False
SPLEETER_AVAILABLE = False

try:
    from modules.audio_separator.engines.demucs import DemucsEngine, SEPARATOR_AVAILABLE
    DEMUCS_AVAILABLE = SEPARATOR_AVAILABLE
except ImportError:
    pass

try:
    from modules.audio_separator.engines.spleeter import SpleeterEngine, SPLEETER_AVAILABLE as _SPLEETER
    SPLEETER_AVAILABLE = _SPLEETER
except ImportError:
    pass


@dataclass
class SeparationRequest:
    """Request for audio separation."""
    audio_path: str
    stems: List[str] = None  # Default: ["vocals", "instrumental"]
    engine: str = "auto"  # auto, demucs, spleeter
    output_format: str = "wav"  # wav, mp3, flac

    def __post_init__(self):
        if self.stems is None:
            self.stems = ["vocals", "instrumental"]


@dataclass
class RemixRequest:
    """Request for remixing separated audio."""
    vocals_path: Optional[str] = None
    instrumental_path: Optional[str] = None
    drums_path: Optional[str] = None
    bass_path: Optional[str] = None
    other_path: Optional[str] = None

    # Volume levels (0.0 = mute, 1.0 = original, 2.0 = double)
    vocal_volume: float = 1.0
    instrumental_volume: float = 1.0
    drums_volume: float = 1.0
    bass_volume: float = 1.0
    other_volume: float = 1.0

    # Output settings
    output_format: str = "mp3"
    output_bitrate: str = "320k"


@dataclass
class ServiceResult:
    """Result from separator service."""
    success: bool
    output_path: Optional[str] = None
    separation_result: Optional[SeparationResult] = None
    error: Optional[str] = None
    processing_time_ms: float = 0.0


class AudioSeparatorService:
    """
    Audio Separator Service.

    Provides high-level API for:
    - Audio source separation (vocals/instrumental)
    - Volume adjustment and remixing
    - Multiple output formats
    """

    def __init__(self):
        self._engine = None
        self._mixer = None
        self._temp_dirs: List[str] = []

    def _get_engine(self, model: Optional[str] = None):
        """Get or create separator engine.

        Prefers Demucs (via audio-separator) over Spleeter.

        Args:
            model: Model filename for Demucs engine. If provided, creates new engine.
        """
        # If model specified and different from current, recreate engine
        if model and self._engine is not None:
            if hasattr(self._engine, '_model_name') and self._engine._model_name != model:
                logger.info(f"Switching model from {self._engine._model_name} to {model}")
                self._engine.cleanup()
                self._engine = None

        if self._engine is None:
            if DEMUCS_AVAILABLE:
                logger.info(f"Using Demucs engine (audio-separator) with model: {model or 'default'}")
                self._engine = DemucsEngine(model_name=model)
            elif SPLEETER_AVAILABLE:
                logger.info("Using Spleeter engine")
                self._engine = SpleeterEngine()
            else:
                raise ImportError(
                    "No audio separator engine available. "
                    "Install with: pip install audio-separator[cpu]"
                )
        return self._engine

    def _get_mixer(self) -> AudioMixer:
        """Get or create audio mixer."""
        if self._mixer is None:
            self._mixer = AudioMixer()
        return self._mixer

    def separate(self, request: SeparationRequest, model: Optional[str] = None) -> ServiceResult:
        """
        Separate audio into stems.

        Args:
            request: SeparationRequest with audio path and options
            model: Model filename for separation engine

        Returns:
            ServiceResult with separation details
        """
        import time
        start_time = time.time()

        try:
            # Validate input
            if not Path(request.audio_path).exists():
                return ServiceResult(
                    success=False,
                    error=f"Audio file not found: {request.audio_path}"
                )

            # Get engine
            engine = self._get_engine(model=model)

            # Create temp output directory
            output_dir = tempfile.mkdtemp(prefix="separator_")
            self._temp_dirs.append(output_dir)

            # Perform separation
            result = engine.separate(
                audio_path=request.audio_path,
                stems=request.stems,
                output_dir=output_dir,
                config={
                    "codec": request.output_format,
                },
            )

            processing_time_ms = (time.time() - start_time) * 1000

            return ServiceResult(
                success=True,
                separation_result=result,
                processing_time_ms=processing_time_ms,
            )

        except Exception as e:
            logger.error(f"Separation failed: {e}", exc_info=True)
            return ServiceResult(
                success=False,
                error=str(e),
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def remix(self, request: RemixRequest) -> ServiceResult:
        """
        Remix separated stems with volume adjustments.

        Args:
            request: RemixRequest with stem paths and volume levels

        Returns:
            ServiceResult with output path
        """
        import time
        start_time = time.time()

        try:
            mixer = self._get_mixer()

            config = MixConfig(
                vocal_volume=request.vocal_volume,
                instrumental_volume=request.instrumental_volume,
                drums_volume=request.drums_volume,
                bass_volume=request.bass_volume,
                other_volume=request.other_volume,
                output_format=request.output_format,
                output_bitrate=request.output_bitrate,
            )

            output_path = mixer.mix_files(
                vocals_path=request.vocals_path,
                instrumental_path=request.instrumental_path,
                drums_path=request.drums_path,
                bass_path=request.bass_path,
                other_path=request.other_path,
                config=config,
            )

            processing_time_ms = (time.time() - start_time) * 1000

            return ServiceResult(
                success=True,
                output_path=output_path,
                processing_time_ms=processing_time_ms,
            )

        except Exception as e:
            logger.error(f"Remix failed: {e}", exc_info=True)
            return ServiceResult(
                success=False,
                error=str(e),
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def separate_and_remix(
        self,
        audio_path: str,
        vocal_volume: float = 1.0,
        instrumental_volume: float = 1.0,
        output_format: str = "mp3",
        output_path: Optional[str] = None,
        model: Optional[str] = None,
    ) -> ServiceResult:
        """
        Convenience method: separate audio and remix with adjusted volumes.

        This is the main use case - adjust volume of vocals or instrumental
        in a single call.

        Args:
            audio_path: Path to input audio file
            vocal_volume: Vocal volume (0.0 = mute, 1.0 = original, 2.0 = double)
            instrumental_volume: Instrumental volume
            output_format: Output format (mp3, wav, flac)
            output_path: Output file path (auto-generated if None)
            model: Model filename for separation (e.g., '1_HP-UVR.pth', 'htdemucs.yaml')

        Returns:
            ServiceResult with output path

        Example:
            # Remove vocals (karaoke)
            result = service.separate_and_remix("song.mp3", vocal_volume=0.0)

            # Reduce vocals by 50%
            result = service.separate_and_remix("song.mp3", vocal_volume=0.5)

            # Boost instrumental
            result = service.separate_and_remix("song.mp3", instrumental_volume=1.5)
        """
        import time
        start_time = time.time()

        try:
            # Step 1: Separate
            sep_request = SeparationRequest(
                audio_path=audio_path,
                stems=["vocals", "instrumental"],
                output_format="wav",  # Use WAV for intermediate
            )

            sep_result = self.separate(sep_request, model=model)

            if not sep_result.success:
                return sep_result

            # Step 2: Remix with adjusted volumes
            remix_request = RemixRequest(
                vocals_path=sep_result.separation_result.vocals,
                instrumental_path=sep_result.separation_result.instrumental,
                vocal_volume=vocal_volume,
                instrumental_volume=instrumental_volume,
                output_format=output_format,
            )

            remix_result = self.remix(remix_request)

            if not remix_result.success:
                return remix_result

            # Move to final output path if specified
            if output_path:
                shutil.move(remix_result.output_path, output_path)
                remix_result.output_path = output_path

            total_time_ms = (time.time() - start_time) * 1000
            remix_result.processing_time_ms = total_time_ms

            logger.info(
                f"Separate and remix completed in {total_time_ms:.1f}ms"
            )

            return remix_result

        except Exception as e:
            logger.error(f"Separate and remix failed: {e}", exc_info=True)
            return ServiceResult(
                success=False,
                error=str(e),
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def cleanup(self):
        """Clean up temporary files."""
        for temp_dir in self._temp_dirs:
            try:
                if Path(temp_dir).exists():
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Cleaned up: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {temp_dir}: {e}")
        self._temp_dirs.clear()

    def __del__(self):
        """Destructor - cleanup resources."""
        self.cleanup()


# Global service instance
_separator_service: Optional[AudioSeparatorService] = None


def get_separator_service() -> AudioSeparatorService:
    """Get global audio separator service instance."""
    global _separator_service
    if _separator_service is None:
        _separator_service = AudioSeparatorService()
    return _separator_service
