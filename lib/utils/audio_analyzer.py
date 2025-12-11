"""
Audio Quality Analyzer

Analyzes audio files for quality metrics including SNR, music detection,
silence detection, and preprocessing recommendations.
"""

import logging
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Check if librosa is available
try:
    import librosa
    import soundfile as sf
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("Librosa not available. Install with: pip install librosa soundfile")


@dataclass
class AudioQualityMetrics:
    """Audio quality analysis results"""

    # Basic properties
    duration_s: float
    sample_rate: int
    channels: int

    # Quality metrics
    snr_db: Optional[float]  # Signal-to-Noise Ratio in dB
    rms_energy: float  # Root Mean Square energy
    silence_ratio: float  # Percentage of silence (0-1)

    # Music detection
    has_music: bool  # Whether music is detected
    music_confidence: float  # Confidence score (0-1)
    spectral_centroid_mean: float  # Hz

    # Recommendations
    preprocessing_recommended: bool
    use_demucs: bool  # Recommend vocal separation
    quality_score: float  # Overall quality (0-100)


class AudioAnalyzer:
    """
    Analyzes audio files for quality metrics and preprocessing recommendations.

    Provides:
    - SNR (Signal-to-Noise Ratio) calculation
    - Music detection using spectral features
    - Silence detection
    - RMS energy analysis
    - Automatic preprocessing recommendations
    """

    def __init__(
        self,
        silence_threshold_db: float = -40.0,
        music_threshold: float = 0.6,
        snr_threshold_db: float = 20.0,
    ):
        """
        Initialize AudioAnalyzer.

        Args:
            silence_threshold_db: Threshold for silence detection (dB)
            music_threshold: Confidence threshold for music detection (0-1)
            snr_threshold_db: Minimum acceptable SNR (dB)
        """
        if not LIBROSA_AVAILABLE:
            raise ImportError(
                "Librosa is required for audio analysis. "
                "Install with: pip install librosa soundfile"
            )

        self.silence_threshold_db = silence_threshold_db
        self.music_threshold = music_threshold
        self.snr_threshold_db = snr_threshold_db

    def analyze(self, audio_path: str) -> AudioQualityMetrics:
        """
        Perform comprehensive audio quality analysis.

        Args:
            audio_path: Path to audio file

        Returns:
            AudioQualityMetrics with analysis results
        """
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Analyzing audio: {audio_path}")

        # Load audio
        audio, sr = librosa.load(audio_path, sr=None, mono=False)

        # Convert to mono for analysis
        if audio.ndim > 1:
            audio_mono = librosa.to_mono(audio)
            channels = audio.shape[0]
        else:
            audio_mono = audio
            channels = 1

        # Calculate duration
        duration_s = len(audio_mono) / sr

        # Calculate quality metrics
        snr_db = self._calculate_snr(audio_mono)
        rms_energy = self._calculate_rms(audio_mono)
        silence_ratio = self._calculate_silence_ratio(audio_mono, sr)

        # Music detection
        has_music, music_confidence, spectral_centroid = self._detect_music(audio_mono, sr)

        # Generate recommendations
        preprocessing_recommended = False
        use_demucs = False

        # Recommend preprocessing if:
        # 1. Music is detected with high confidence
        # 2. SNR is below threshold
        if has_music and music_confidence > self.music_threshold:
            use_demucs = True
            preprocessing_recommended = True
            logger.info(f"Music detected (confidence: {music_confidence:.2f}), recommending Demucs")

        if snr_db is not None and snr_db < self.snr_threshold_db:
            preprocessing_recommended = True
            logger.info(f"Low SNR ({snr_db:.1f}dB), recommending preprocessing")

        # Calculate overall quality score (0-100)
        quality_score = self._calculate_quality_score(
            snr_db, silence_ratio, rms_energy, has_music
        )

        return AudioQualityMetrics(
            duration_s=duration_s,
            sample_rate=sr,
            channels=channels,
            snr_db=snr_db,
            rms_energy=rms_energy,
            silence_ratio=silence_ratio,
            has_music=has_music,
            music_confidence=music_confidence,
            spectral_centroid_mean=spectral_centroid,
            preprocessing_recommended=preprocessing_recommended,
            use_demucs=use_demucs,
            quality_score=quality_score,
        )

    def _calculate_snr(self, audio: np.ndarray) -> Optional[float]:
        """
        Calculate Signal-to-Noise Ratio (SNR) in dB.

        Uses simple percentile-based estimation:
        - Signal: 90th percentile of energy
        - Noise: 10th percentile of energy

        Args:
            audio: Audio samples

        Returns:
            SNR in dB, or None if cannot be calculated
        """
        try:
            # Calculate frame energy
            frame_length = 2048
            hop_length = 512

            # RMS energy per frame
            rms = librosa.feature.rms(
                y=audio,
                frame_length=frame_length,
                hop_length=hop_length
            )[0]

            # Estimate signal and noise levels
            signal_level = np.percentile(rms, 90)
            noise_level = np.percentile(rms, 10)

            # Avoid division by zero
            if noise_level < 1e-10:
                return None

            # Calculate SNR in dB
            snr_linear = signal_level / noise_level
            snr_db = 20 * np.log10(snr_linear)

            return float(snr_db)

        except Exception as e:
            logger.warning(f"Failed to calculate SNR: {e}")
            return None

    def _calculate_rms(self, audio: np.ndarray) -> float:
        """
        Calculate Root Mean Square (RMS) energy.

        Args:
            audio: Audio samples

        Returns:
            RMS energy value
        """
        rms = librosa.feature.rms(y=audio)[0]
        return float(np.mean(rms))

    def _calculate_silence_ratio(self, audio: np.ndarray, sr: int) -> float:
        """
        Calculate ratio of silence in audio.

        Args:
            audio: Audio samples
            sr: Sample rate

        Returns:
            Silence ratio (0-1)
        """
        # Convert threshold from dB to amplitude
        ref_amplitude = np.max(np.abs(audio))
        if ref_amplitude < 1e-10:
            return 1.0  # All silence

        threshold_amplitude = ref_amplitude * (10 ** (self.silence_threshold_db / 20))

        # Detect non-silent intervals
        intervals = librosa.effects.split(
            audio,
            top_db=abs(self.silence_threshold_db),
            frame_length=2048,
            hop_length=512
        )

        # Calculate silence ratio
        if len(intervals) == 0:
            return 1.0  # All silence

        total_samples = len(audio)
        non_silent_samples = sum(end - start for start, end in intervals)
        silence_ratio = 1.0 - (non_silent_samples / total_samples)

        return float(max(0.0, min(1.0, silence_ratio)))

    def _detect_music(self, audio: np.ndarray, sr: int) -> Tuple[bool, float, float]:
        """
        Detect presence of music using spectral features.

        Uses spectral centroid and spectral rolloff to distinguish
        speech from music. Music typically has:
        - Higher spectral centroid variation
        - Broader frequency range
        - More harmonic structure

        Args:
            audio: Audio samples
            sr: Sample rate

        Returns:
            Tuple of (has_music, confidence, spectral_centroid_mean)
        """
        try:
            # Extract spectral features
            spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)[0]
            spectral_bandwidth = librosa.feature.spectral_bandwidth(y=audio, sr=sr)[0]

            # Calculate statistics
            centroid_mean = np.mean(spectral_centroid)
            centroid_std = np.std(spectral_centroid)
            rolloff_mean = np.mean(spectral_rolloff)
            bandwidth_mean = np.mean(spectral_bandwidth)

            # Music detection heuristics
            # Music typically has:
            # 1. Higher spectral centroid (>2000 Hz for music vs <1500 Hz for speech)
            # 2. Higher variation in spectral features
            # 3. Broader bandwidth

            music_score = 0.0

            # Check centroid (speech: 500-1500 Hz, music: 1500-4000 Hz)
            if centroid_mean > 2000:
                music_score += 0.4
            elif centroid_mean > 1500:
                music_score += 0.2

            # Check variation (music has more variation)
            if centroid_std > 500:
                music_score += 0.3
            elif centroid_std > 300:
                music_score += 0.15

            # Check bandwidth (music has broader spectrum)
            if bandwidth_mean > 1500:
                music_score += 0.3
            elif bandwidth_mean > 1000:
                music_score += 0.15

            # Normalize confidence to 0-1
            confidence = min(1.0, music_score)

            # Determine if music is present
            has_music = confidence > self.music_threshold

            return has_music, confidence, float(centroid_mean)

        except Exception as e:
            logger.warning(f"Music detection failed: {e}")
            return False, 0.0, 0.0

    def _calculate_quality_score(
        self,
        snr_db: Optional[float],
        silence_ratio: float,
        rms_energy: float,
        has_music: bool
    ) -> float:
        """
        Calculate overall audio quality score (0-100).

        Args:
            snr_db: Signal-to-Noise Ratio
            silence_ratio: Ratio of silence
            rms_energy: RMS energy
            has_music: Whether music is detected

        Returns:
            Quality score (0-100)
        """
        score = 100.0

        # Penalize low SNR
        if snr_db is not None:
            if snr_db < 10:
                score -= 40
            elif snr_db < 20:
                score -= 20
            elif snr_db < 30:
                score -= 10

        # Penalize high silence ratio
        if silence_ratio > 0.5:
            score -= 20
        elif silence_ratio > 0.3:
            score -= 10

        # Penalize very low energy
        if rms_energy < 0.01:
            score -= 20
        elif rms_energy < 0.05:
            score -= 10

        # Slight penalty for music (needs preprocessing)
        if has_music:
            score -= 5

        return max(0.0, min(100.0, score))
