"""
Demucs Audio Separator Engine

Audio source separation using Facebook's Demucs via audio-separator library.
Supports multiple models including UVR models.

Hardware Support:
- NVIDIA CUDA (Linux, Windows)
- Apple Silicon MPS (macOS M1/M2/M3/M4)
- AMD ROCm (Linux)
- CPU fallback (all platforms)
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
from modules.stt.utils.gpu import (
    get_optimal_device,
    get_gpu_info,
    clear_gpu_cache,
    is_gpu_available,
)

logger = logging.getLogger(__name__)

# Check if audio-separator is available
try:
    from audio_separator.separator import Separator
    SEPARATOR_AVAILABLE = True
except ImportError:
    SEPARATOR_AVAILABLE = False
    logger.warning("audio-separator not available. Install with: pip install audio-separator")


class DemucsEngine(SeparatorEngine):
    """
    Demucs-based audio source separation engine using audio-separator library.

    Features:
    - Multiple model support (Demucs, MDX, VR)
    - High quality separation
    - CPU and GPU support
    - Easy model switching

    Models:
    - htdemucs: Default Demucs model (vocals, drums, bass, other)
    - htdemucs_ft: Fine-tuned version
    - mdx_extra: High quality MDX model
    """

    # Default model - prioritize speed over quality
    # htdemucs.yaml: ~2 min (highest quality, very slow)
    # UVR_MDXNET_Main.onnx: ~20 sec (good quality)
    # 1_HP-UVR.pth: ~5-10 sec (decent quality, fastest)
    DEFAULT_MODEL = "1_HP-UVR.pth"

    def __init__(self, model_name: str = None):
        if not SEPARATOR_AVAILABLE:
            raise ImportError(
                "audio-separator is not installed. "
                "Install with: pip install audio-separator"
            )
        self._model_name = model_name or self.DEFAULT_MODEL
        self._separator = None
        self._output_dir = None

    def _get_separator(self) -> "Separator":
        """Get or create separator instance with optimal hardware detection."""
        if self._separator is None:
            # Create output directory
            self._output_dir = tempfile.mkdtemp(prefix="demucs_")

            # Auto-detect optimal device
            device = get_optimal_device()
            gpu_info = get_gpu_info()

            logger.info(f"Loading Demucs model: {self._model_name}")
            logger.info(f"Using device: {device} ({gpu_info.get('device_name', 'CPU')})")

            # Configure separator based on device
            # audio-separator uses different device names
            if device == "cuda":
                use_cpu = False
            elif device == "mps":
                # MPS support depends on audio-separator version
                # Some models may not work with MPS, fallback to CPU if needed
                use_cpu = False  # Will use MPS if available
            else:
                use_cpu = True

            self._separator = Separator(
                output_dir=self._output_dir,
                output_format="wav",
            )

            # Load model
            self._separator.load_model(model_filename=self._model_name)

        return self._separator

    def separate(
        self,
        audio_path: str,
        stems: List[str] = None,
        output_dir: Optional[str] = None,
        config: Optional[Dict] = None,
    ) -> SeparationResult:
        """
        Separate audio into stems using Demucs.

        Args:
            audio_path: Path to input audio file
            stems: List of stems to extract (default: vocals, instrumental)
            output_dir: Directory to save output files
            config: Configuration options

        Returns:
            SeparationResult with file paths
        """
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        config = config or {}
        start_time = time.time()

        if stems is None:
            stems = ["vocals", "instrumental"]

        logger.info(f"Separating {audio_path} using Demucs")
        logger.info(f"Requested stems: {stems}")

        # Get separator
        separator = self._get_separator()

        try:
            # Perform separation
            output_files = separator.separate(audio_path)

            processing_time_ms = (time.time() - start_time) * 1000

            # Build result
            result = SeparationResult(
                processing_time_ms=processing_time_ms,
            )

            # Map output files to result (add full path)
            for output_file in output_files:
                # Ensure full path
                if not os.path.isabs(output_file):
                    output_file = os.path.join(self._output_dir, output_file)

                file_lower = output_file.lower()
                if "vocal" in file_lower and "no" not in file_lower:
                    result.vocals = output_file
                elif "instrumental" in file_lower or "no_vocal" in file_lower or "accompaniment" in file_lower:
                    result.instrumental = output_file
                elif "drum" in file_lower:
                    result.drums = output_file
                elif "bass" in file_lower:
                    result.bass = output_file
                elif "other" in file_lower:
                    result.other = output_file

            # If we got 4 stems but need instrumental, combine non-vocal stems
            # Demucs outputs 4 stems: vocals, drums, bass, other
            # We need to create instrumental by combining drums + bass + other
            if result.instrumental is None and result.vocals:
                # Use 'other' as fallback for now (TODO: mix drums+bass+other)
                if result.other:
                    result.instrumental = result.other

            logger.info(f"Separation completed in {processing_time_ms:.1f}ms")
            logger.info(f"Vocals: {result.vocals}")
            logger.info(f"Instrumental: {result.instrumental}")

            return result

        except Exception as e:
            logger.error(f"Separation failed: {e}", exc_info=True)
            raise RuntimeError(f"Demucs separation failed: {e}")

    def separate_to_numpy(
        self,
        audio_path: str,
        stems: List[str] = None,
        config: Optional[Dict] = None,
    ) -> SeparationResult:
        """
        Separate audio and return numpy arrays.

        For now, this separates to files and then loads them.
        """
        import soundfile as sf

        # First separate to files
        result = self.separate(audio_path, stems, config=config)

        # Load files into numpy arrays
        if result.vocals:
            data, sr = sf.read(result.vocals)
            result.vocals_data = data
            result.sample_rate = sr

        if result.instrumental:
            data, sr = sf.read(result.instrumental)
            result.instrumental_data = data
            if result.sample_rate is None:
                result.sample_rate = sr

        return result

    def get_info(self) -> EngineInfo:
        """Get engine information."""
        return EngineInfo(
            name="demucs",
            version="4.0",
            supported_stems=["vocals", "instrumental", "drums", "bass", "other"],
            supports_gpu=True,
            default_sample_rate=44100,
        )

    def is_available(self) -> bool:
        """Check if audio-separator is available."""
        return SEPARATOR_AVAILABLE

    def cleanup(self):
        """Release resources and clear GPU memory."""
        if self._output_dir and Path(self._output_dir).exists():
            import shutil
            try:
                shutil.rmtree(self._output_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup: {e}")
        self._separator = None

        # Clear GPU cache
        clear_gpu_cache()
        logger.info("Demucs engine cleaned up")
