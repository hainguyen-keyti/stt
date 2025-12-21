"""
Audio Mixer

Mix separated stems back together with volume adjustments.
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional, Union
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

# Check for audio I/O libraries
try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    logger.warning("soundfile not available. Install with: pip install soundfile")

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logger.warning("pydub not available. Install with: pip install pydub")


@dataclass
class MixConfig:
    """Configuration for audio mixing."""
    vocal_volume: float = 1.0  # 0.0 = mute, 1.0 = original, 2.0 = double
    instrumental_volume: float = 1.0
    drums_volume: float = 1.0
    bass_volume: float = 1.0
    other_volume: float = 1.0

    # Output settings
    output_format: str = "mp3"  # mp3, wav, flac
    output_bitrate: str = "320k"
    sample_rate: int = 44100


class AudioMixer:
    """
    Mix audio stems with volume adjustments.

    Supports:
    - Volume adjustment for each stem (0.0 to 2.0+)
    - Multiple output formats (mp3, wav, flac)
    - Both file-based and numpy array mixing
    """

    def __init__(self):
        if not SOUNDFILE_AVAILABLE:
            raise ImportError(
                "soundfile is required for AudioMixer. "
                "Install with: pip install soundfile"
            )

    def mix_files(
        self,
        vocals_path: Optional[str] = None,
        instrumental_path: Optional[str] = None,
        drums_path: Optional[str] = None,
        bass_path: Optional[str] = None,
        other_path: Optional[str] = None,
        config: Optional[MixConfig] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Mix audio files with volume adjustments.

        Args:
            vocals_path: Path to vocals audio file
            instrumental_path: Path to instrumental audio file
            drums_path: Path to drums audio file
            bass_path: Path to bass audio file
            other_path: Path to other audio file
            config: Mix configuration with volume levels
            output_path: Output file path (auto-generated if None)

        Returns:
            Path to mixed audio file
        """
        config = config or MixConfig()

        # Load and adjust each stem
        mixed = None
        sample_rate = config.sample_rate

        stems = [
            (vocals_path, config.vocal_volume),
            (instrumental_path, config.instrumental_volume),
            (drums_path, config.drums_volume),
            (bass_path, config.bass_volume),
            (other_path, config.other_volume),
        ]

        for path, volume in stems:
            if path and Path(path).exists() and volume > 0:
                data, sr = sf.read(path)
                sample_rate = sr

                # Apply volume
                data = data * volume

                # Mix
                if mixed is None:
                    mixed = data
                else:
                    # Ensure same length
                    if len(data) > len(mixed):
                        mixed = np.pad(mixed, ((0, len(data) - len(mixed)), (0, 0)))
                    elif len(data) < len(mixed):
                        data = np.pad(data, ((0, len(mixed) - len(data)), (0, 0)))
                    mixed = mixed + data

        if mixed is None:
            raise ValueError("No valid audio files provided for mixing")

        # Normalize to prevent clipping
        max_val = np.max(np.abs(mixed))
        if max_val > 1.0:
            mixed = mixed / max_val
            logger.info(f"Audio normalized (peak was {max_val:.2f})")

        # Generate output path if not provided
        if output_path is None:
            suffix = f".{config.output_format}"
            output_path = tempfile.mktemp(suffix=suffix, prefix="mixed_")

        # Save output
        self._save_audio(mixed, sample_rate, output_path, config)

        logger.info(f"Mixed audio saved to: {output_path}")
        return output_path

    def mix_arrays(
        self,
        vocals_data: Optional[np.ndarray] = None,
        instrumental_data: Optional[np.ndarray] = None,
        drums_data: Optional[np.ndarray] = None,
        bass_data: Optional[np.ndarray] = None,
        other_data: Optional[np.ndarray] = None,
        config: Optional[MixConfig] = None,
    ) -> np.ndarray:
        """
        Mix numpy arrays with volume adjustments.

        Args:
            vocals_data: Vocals audio as numpy array
            instrumental_data: Instrumental audio as numpy array
            drums_data: Drums audio as numpy array
            bass_data: Bass audio as numpy array
            other_data: Other audio as numpy array
            config: Mix configuration with volume levels

        Returns:
            Mixed audio as numpy array
        """
        config = config or MixConfig()

        mixed = None

        stems = [
            (vocals_data, config.vocal_volume),
            (instrumental_data, config.instrumental_volume),
            (drums_data, config.drums_volume),
            (bass_data, config.bass_volume),
            (other_data, config.other_volume),
        ]

        for data, volume in stems:
            if data is not None and volume > 0:
                adjusted = data * volume

                if mixed is None:
                    mixed = adjusted
                else:
                    # Ensure same length
                    if len(adjusted) > len(mixed):
                        if mixed.ndim == 1:
                            mixed = np.pad(mixed, (0, len(adjusted) - len(mixed)))
                        else:
                            mixed = np.pad(mixed, ((0, len(adjusted) - len(mixed)), (0, 0)))
                    elif len(adjusted) < len(mixed):
                        if adjusted.ndim == 1:
                            adjusted = np.pad(adjusted, (0, len(mixed) - len(adjusted)))
                        else:
                            adjusted = np.pad(adjusted, ((0, len(mixed) - len(adjusted)), (0, 0)))
                    mixed = mixed + adjusted

        if mixed is None:
            raise ValueError("No valid audio data provided for mixing")

        # Normalize to prevent clipping
        max_val = np.max(np.abs(mixed))
        if max_val > 1.0:
            mixed = mixed / max_val

        return mixed

    def adjust_volume(
        self,
        audio_path: str,
        volume: float,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Adjust volume of a single audio file.

        Args:
            audio_path: Path to input audio file
            volume: Volume multiplier (0.0 to 2.0+)
            output_path: Output file path

        Returns:
            Path to adjusted audio file
        """
        data, sample_rate = sf.read(audio_path)
        adjusted = data * volume

        # Normalize if needed
        max_val = np.max(np.abs(adjusted))
        if max_val > 1.0:
            adjusted = adjusted / max_val

        if output_path is None:
            suffix = Path(audio_path).suffix
            output_path = tempfile.mktemp(suffix=suffix, prefix="adjusted_")

        sf.write(output_path, adjusted, sample_rate)
        return output_path

    def _save_audio(
        self,
        data: np.ndarray,
        sample_rate: int,
        output_path: str,
        config: MixConfig,
    ):
        """Save audio data to file with specified format."""
        output_format = config.output_format.lower()

        if output_format == "wav":
            sf.write(output_path, data, sample_rate)

        elif output_format in ["mp3", "flac", "ogg"]:
            if not PYDUB_AVAILABLE:
                # Fallback to WAV if pydub not available
                logger.warning(
                    f"pydub not available, saving as WAV instead of {output_format}"
                )
                wav_path = output_path.rsplit(".", 1)[0] + ".wav"
                sf.write(wav_path, data, sample_rate)
                return

            # Save as temporary WAV first
            temp_wav = tempfile.mktemp(suffix=".wav")
            sf.write(temp_wav, data, sample_rate)

            # Convert using pydub
            audio = AudioSegment.from_wav(temp_wav)

            if output_format == "mp3":
                audio.export(
                    output_path,
                    format="mp3",
                    bitrate=config.output_bitrate,
                )
            elif output_format == "flac":
                audio.export(output_path, format="flac")
            elif output_format == "ogg":
                audio.export(output_path, format="ogg")

            # Cleanup temp file
            Path(temp_wav).unlink(missing_ok=True)

        else:
            # Default to WAV
            sf.write(output_path, data, sample_rate)


def create_mixer() -> AudioMixer:
    """Create an AudioMixer instance."""
    return AudioMixer()
