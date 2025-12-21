"""
Spleeter Audio Separator Engine

Fast audio source separation using Deezer's Spleeter.
Optimized for CPU usage - ideal for servers without GPU.
"""

import logging
import time
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from modules.audio_separator.engines.base import (
    SeparatorEngine,
    SeparationResult,
    EngineInfo,
)

logger = logging.getLogger(__name__)

# Check if Spleeter is available
try:
    from spleeter.separator import Separator
    from spleeter.audio.adapter import AudioAdapter
    SPLEETER_AVAILABLE = True
except ImportError:
    SPLEETER_AVAILABLE = False
    logger.warning("Spleeter not available. Install with: pip install spleeter")


class SpleeterEngine(SeparatorEngine):
    """
    Spleeter-based audio source separation engine.

    Features:
    - Fast CPU processing (~30-60s for 4-minute song)
    - Low memory footprint with proper configuration
    - 2-stem (vocals/accompaniment) or 4-stem separation
    - Pre-trained models auto-downloaded on first use

    Models:
    - spleeter:2stems - Vocals + Accompaniment
    - spleeter:4stems - Vocals + Drums + Bass + Other
    - spleeter:5stems - Vocals + Drums + Bass + Piano + Other
    """

    # Model configurations
    MODELS = {
        "2stems": "spleeter:2stems",
        "4stems": "spleeter:4stems",
        "5stems": "spleeter:5stems",
    }

    def __init__(self):
        if not SPLEETER_AVAILABLE:
            raise ImportError(
                "Spleeter is not installed. "
                "Install with: pip install spleeter"
            )
        self._separators: Dict[str, Separator] = {}
        self._audio_adapter = None

    def _get_separator(self, model: str = "2stems") -> "Separator":
        """Get or create separator instance for model."""
        if model not in self._separators:
            model_name = self.MODELS.get(model, self.MODELS["2stems"])
            logger.info(f"Loading Spleeter model: {model_name}")
            self._separators[model] = Separator(model_name)
        return self._separators[model]

    def _get_audio_adapter(self) -> "AudioAdapter":
        """Get audio adapter for loading/saving audio."""
        if self._audio_adapter is None:
            self._audio_adapter = AudioAdapter.default()
        return self._audio_adapter

    def separate(
        self,
        audio_path: str,
        stems: List[str] = None,
        output_dir: Optional[str] = None,
        config: Optional[Dict] = None,
    ) -> SeparationResult:
        """
        Separate audio into stems using Spleeter.

        Args:
            audio_path: Path to input audio file
            stems: List of stems to extract. Options:
                   - ["vocals", "instrumental"] (2stems)
                   - ["vocals", "drums", "bass", "other"] (4stems)
            output_dir: Directory to save output files
            config: Configuration options:
                   - model: "2stems", "4stems", or "5stems"
                   - bitrate: Output bitrate (e.g., "320k")
                   - codec: Output codec (e.g., "mp3", "wav")
                   - duration: Max duration to process (seconds)

        Returns:
            SeparationResult with file paths and/or audio data
        """
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        config = config or {}
        start_time = time.time()

        # Determine model based on stems requested
        if stems is None:
            stems = ["vocals", "instrumental"]

        if set(stems) <= {"vocals", "instrumental", "accompaniment"}:
            model = config.get("model", "2stems")
        else:
            model = config.get("model", "4stems")

        logger.info(f"Separating {audio_path} using model {model}")
        logger.info(f"Requested stems: {stems}")

        # Get separator
        separator = self._get_separator(model)

        # Create output directory
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="spleeter_")
        else:
            os.makedirs(output_dir, exist_ok=True)

        # Configure output
        codec = config.get("codec", "wav")
        bitrate = config.get("bitrate", "320k")

        try:
            # Perform separation
            separator.separate_to_file(
                audio_path,
                output_dir,
                codec=codec,
                bitrate=bitrate,
                duration=config.get("duration"),
            )

            processing_time_ms = (time.time() - start_time) * 1000

            # Build result
            result = SeparationResult(
                processing_time_ms=processing_time_ms,
            )

            # Find output files
            audio_name = Path(audio_path).stem
            output_subdir = Path(output_dir) / audio_name

            # Map stem names to file paths
            stem_mapping = {
                "vocals": "vocals",
                "instrumental": "accompaniment",
                "accompaniment": "accompaniment",
                "drums": "drums",
                "bass": "bass",
                "other": "other",
                "piano": "piano",
            }

            for stem in stems:
                spleeter_stem = stem_mapping.get(stem, stem)
                stem_file = output_subdir / f"{spleeter_stem}.{codec}"

                if stem_file.exists():
                    if stem in ["vocals"]:
                        result.vocals = str(stem_file)
                    elif stem in ["instrumental", "accompaniment"]:
                        result.instrumental = str(stem_file)
                    elif stem == "drums":
                        result.drums = str(stem_file)
                    elif stem == "bass":
                        result.bass = str(stem_file)
                    elif stem == "other":
                        result.other = str(stem_file)

            # Get audio info
            audio_adapter = self._get_audio_adapter()
            waveform, sample_rate = audio_adapter.load(
                audio_path,
                sample_rate=44100,
            )
            result.sample_rate = sample_rate
            result.duration_s = len(waveform) / sample_rate

            logger.info(
                f"Separation completed in {processing_time_ms:.1f}ms "
                f"({result.duration_s:.1f}s audio)"
            )

            return result

        except Exception as e:
            logger.error(f"Separation failed: {e}", exc_info=True)
            raise RuntimeError(f"Spleeter separation failed: {e}")

    def separate_to_numpy(
        self,
        audio_path: str,
        stems: List[str] = None,
        config: Optional[Dict] = None,
    ) -> SeparationResult:
        """
        Separate audio and return numpy arrays instead of files.

        Useful for further processing without disk I/O.

        Args:
            audio_path: Path to input audio file
            stems: List of stems to extract
            config: Configuration options

        Returns:
            SeparationResult with numpy arrays in *_data fields
        """
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        config = config or {}
        start_time = time.time()

        # Determine model
        if stems is None:
            stems = ["vocals", "instrumental"]

        if set(stems) <= {"vocals", "instrumental", "accompaniment"}:
            model = config.get("model", "2stems")
        else:
            model = config.get("model", "4stems")

        logger.info(f"Separating {audio_path} to numpy arrays using model {model}")

        # Get separator
        separator = self._get_separator(model)

        # Load audio
        audio_adapter = self._get_audio_adapter()
        waveform, sample_rate = audio_adapter.load(
            audio_path,
            sample_rate=44100,
        )

        try:
            # Perform separation (returns dict of numpy arrays)
            prediction = separator.separate(waveform)

            processing_time_ms = (time.time() - start_time) * 1000

            # Build result
            result = SeparationResult(
                sample_rate=sample_rate,
                duration_s=len(waveform) / sample_rate,
                processing_time_ms=processing_time_ms,
            )

            # Map predictions to result fields
            if "vocals" in prediction:
                result.vocals_data = prediction["vocals"]
            if "accompaniment" in prediction:
                result.instrumental_data = prediction["accompaniment"]
            if "drums" in prediction:
                result.drums_data = prediction["drums"]
            if "bass" in prediction:
                result.bass_data = prediction["bass"]
            if "other" in prediction:
                result.other_data = prediction["other"]

            logger.info(
                f"Separation to numpy completed in {processing_time_ms:.1f}ms"
            )

            return result

        except Exception as e:
            logger.error(f"Separation failed: {e}", exc_info=True)
            raise RuntimeError(f"Spleeter separation failed: {e}")

    def get_info(self) -> EngineInfo:
        """Get engine information."""
        return EngineInfo(
            name="spleeter",
            version="2.4",
            supported_stems=["vocals", "instrumental", "drums", "bass", "other", "piano"],
            supports_gpu=False,  # We use CPU-optimized config
            default_sample_rate=44100,
        )

    def is_available(self) -> bool:
        """Check if Spleeter is available."""
        return SPLEETER_AVAILABLE

    def cleanup(self):
        """Release resources."""
        for separator in self._separators.values():
            try:
                # Spleeter doesn't have explicit cleanup, but we clear references
                pass
            except Exception:
                pass
        self._separators.clear()
        logger.info("Spleeter engine cleaned up")
