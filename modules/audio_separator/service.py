"""
Audio Separator Service

High-level service for audio source separation and mixing.
"""

import logging
import os
import time
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from modules.audio_separator.engines.base import SeparationResult
from modules.audio_separator.mixer import AudioMixer, MixConfig
from modules.stt.utils.timing import TaskTimer, format_duration
from modules.stt.utils.gpu import get_optimal_device, is_gpu_available, get_vram_info

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("perf.SEPARATOR")

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

    def _get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """Get audio file information."""
        info = {
            "file_size_mb": 0,
            "duration_s": 0,
        }
        try:
            file_size = os.path.getsize(audio_path)
            info["file_size_mb"] = round(file_size / (1024 * 1024), 2)
        except Exception:
            pass
        return info

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
        # Initialize timer
        timer = TaskTimer("separate", module="SEPARATOR")
        timer.start()

        # Get audio info
        audio_info = self._get_audio_info(request.audio_path)
        audio_filename = Path(request.audio_path).name
        device = get_optimal_device()

        perf_logger.info(f"[SEPARATOR] ===== SEPARATION START =====")
        perf_logger.info(f"[SEPARATOR] File: {audio_filename}")
        perf_logger.info(f"[SEPARATOR] Size: {audio_info['file_size_mb']} MB")
        perf_logger.info(f"[SEPARATOR] Stems: {request.stems}")
        perf_logger.info(f"[SEPARATOR] Model: {model or 'default'}")
        perf_logger.info(f"[SEPARATOR] Device: {device}")

        try:
            # Validate input
            if not Path(request.audio_path).exists():
                perf_logger.error(f"[SEPARATOR] File not found: {request.audio_path}")
                return ServiceResult(
                    success=False,
                    error=f"Audio file not found: {request.audio_path}"
                )

            timer.mark("validation")

            # Get engine
            engine = self._get_engine(model=model)
            engine_load_time = timer.mark("engine_load")

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
            separation_time = timer.mark("separation")

            timer.stop()

            # Get VRAM usage after processing
            vram_used_mb = None
            if is_gpu_available():
                vram_info = get_vram_info()
                vram_used_mb = vram_info.get("allocated_mb")

            # Log performance summary
            perf_logger.info(f"[SEPARATOR] ===== SEPARATION COMPLETE =====")
            perf_logger.info(f"[SEPARATOR] --- TIMING BREAKDOWN ---")
            perf_logger.info(f"[SEPARATOR] Engine Load: {format_duration(engine_load_time)}")
            perf_logger.info(f"[SEPARATOR] Separation: {format_duration(separation_time)}")
            perf_logger.info(f"[SEPARATOR] Total: {format_duration(timer.total_ms)}")
            perf_logger.info(f"[SEPARATOR] --- OUTPUT ---")
            perf_logger.info(f"[SEPARATOR] Vocals: {result.vocals}")
            perf_logger.info(f"[SEPARATOR] Instrumental: {result.instrumental}")
            if vram_used_mb:
                perf_logger.info(f"[SEPARATOR] VRAM Used: {vram_used_mb:.0f} MB")
            perf_logger.info(f"[SEPARATOR] ================================")

            return ServiceResult(
                success=True,
                separation_result=result,
                processing_time_ms=timer.total_ms,
            )

        except Exception as e:
            timer.stop()
            perf_logger.error(f"[SEPARATOR] FAILED after {format_duration(timer.total_ms)}: {e}")
            logger.error(f"Separation failed: {e}", exc_info=True)
            return ServiceResult(
                success=False,
                error=str(e),
                processing_time_ms=timer.total_ms,
            )

    def remix(self, request: RemixRequest) -> ServiceResult:
        """
        Remix separated stems with volume adjustments.

        Args:
            request: RemixRequest with stem paths and volume levels

        Returns:
            ServiceResult with output path
        """
        timer = TaskTimer("remix", module="SEPARATOR")
        timer.start()

        perf_logger.info(f"[SEPARATOR] ===== REMIX START =====")
        perf_logger.info(f"[SEPARATOR] Vocal Volume: {request.vocal_volume}")
        perf_logger.info(f"[SEPARATOR] Instrumental Volume: {request.instrumental_volume}")
        perf_logger.info(f"[SEPARATOR] Output: {request.output_format}")

        try:
            mixer = self._get_mixer()
            timer.mark("mixer_init")

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
            mix_time = timer.mark("mixing")

            timer.stop()

            perf_logger.info(f"[SEPARATOR] ===== REMIX COMPLETE =====")
            perf_logger.info(f"[SEPARATOR] Mixing: {format_duration(mix_time)}")
            perf_logger.info(f"[SEPARATOR] Total: {format_duration(timer.total_ms)}")
            perf_logger.info(f"[SEPARATOR] Output: {output_path}")
            perf_logger.info(f"[SEPARATOR] ================================")

            return ServiceResult(
                success=True,
                output_path=output_path,
                processing_time_ms=timer.total_ms,
            )

        except Exception as e:
            timer.stop()
            perf_logger.error(f"[SEPARATOR] Remix FAILED after {format_duration(timer.total_ms)}: {e}")
            logger.error(f"Remix failed: {e}", exc_info=True)
            return ServiceResult(
                success=False,
                error=str(e),
                processing_time_ms=timer.total_ms,
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
        timer = TaskTimer("separate_and_remix", module="SEPARATOR")
        timer.start()

        audio_info = self._get_audio_info(audio_path)
        audio_filename = Path(audio_path).name

        perf_logger.info(f"[SEPARATOR] ===== SEPARATE & REMIX START =====")
        perf_logger.info(f"[SEPARATOR] File: {audio_filename}")
        perf_logger.info(f"[SEPARATOR] Size: {audio_info['file_size_mb']} MB")
        perf_logger.info(f"[SEPARATOR] Vocal Volume: {vocal_volume}")
        perf_logger.info(f"[SEPARATOR] Instrumental Volume: {instrumental_volume}")
        perf_logger.info(f"[SEPARATOR] Model: {model or 'default'}")

        try:
            # Step 1: Separate
            sep_request = SeparationRequest(
                audio_path=audio_path,
                stems=["vocals", "instrumental"],
                output_format="wav",  # Use WAV for intermediate
            )

            sep_result = self.separate(sep_request, model=model)
            separation_time = timer.mark("separation")

            if not sep_result.success:
                timer.stop()
                perf_logger.error(f"[SEPARATOR] Separation step failed: {sep_result.error}")
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
            remix_time = timer.mark("remix")

            if not remix_result.success:
                timer.stop()
                perf_logger.error(f"[SEPARATOR] Remix step failed: {remix_result.error}")
                return remix_result

            # Move to final output path if specified
            if output_path:
                shutil.move(remix_result.output_path, output_path)
                remix_result.output_path = output_path

            timer.stop()

            # Log final summary
            perf_logger.info(f"[SEPARATOR] ===== SEPARATE & REMIX COMPLETE =====")
            perf_logger.info(f"[SEPARATOR] --- TIMING BREAKDOWN ---")
            perf_logger.info(f"[SEPARATOR] Separation: {format_duration(separation_time)}")
            perf_logger.info(f"[SEPARATOR] Remix: {format_duration(remix_time)}")
            perf_logger.info(f"[SEPARATOR] Total: {format_duration(timer.total_ms)}")
            perf_logger.info(f"[SEPARATOR] Output: {remix_result.output_path}")
            perf_logger.info(f"[SEPARATOR] ================================")

            remix_result.processing_time_ms = timer.total_ms
            return remix_result

        except Exception as e:
            timer.stop()
            perf_logger.error(f"[SEPARATOR] FAILED after {format_duration(timer.total_ms)}: {e}")
            logger.error(f"Separate and remix failed: {e}", exc_info=True)
            return ServiceResult(
                success=False,
                error=str(e),
                processing_time_ms=timer.total_ms,
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
