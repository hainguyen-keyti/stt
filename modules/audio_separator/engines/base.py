"""
Base Audio Separator Engine

Abstract base class for audio source separation engines.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SeparationResult:
    """Result of audio separation."""
    vocals: Optional[str] = None  # Path to vocals file
    instrumental: Optional[str] = None  # Path to instrumental file
    drums: Optional[str] = None  # Path to drums file (if 4-stem)
    bass: Optional[str] = None  # Path to bass file (if 4-stem)
    other: Optional[str] = None  # Path to other file (if 4-stem)

    # Audio data (numpy arrays) - alternative to file paths
    vocals_data: Optional["np.ndarray"] = None
    instrumental_data: Optional["np.ndarray"] = None
    drums_data: Optional["np.ndarray"] = None
    bass_data: Optional["np.ndarray"] = None
    other_data: Optional["np.ndarray"] = None

    sample_rate: int = 44100
    duration_s: float = 0.0
    processing_time_ms: float = 0.0


@dataclass
class EngineInfo:
    """Information about a separator engine."""
    name: str
    version: str
    supported_stems: List[str]
    supports_gpu: bool = False
    default_sample_rate: int = 44100


class SeparatorEngine(ABC):
    """
    Abstract base class for audio source separation engines.

    All separator engines must implement:
    - separate(): Perform source separation
    - get_info(): Return engine information
    """

    @abstractmethod
    def separate(
        self,
        audio_path: str,
        stems: List[str],
        output_dir: Optional[str] = None,
        config: Optional[Dict] = None,
    ) -> SeparationResult:
        """
        Separate audio into stems.

        Args:
            audio_path: Path to input audio file
            stems: List of stems to extract (e.g., ["vocals", "instrumental"])
            output_dir: Directory to save output files (optional)
            config: Engine-specific configuration

        Returns:
            SeparationResult with paths or audio data
        """
        pass

    @abstractmethod
    def get_info(self) -> EngineInfo:
        """
        Get engine information.

        Returns:
            EngineInfo with engine metadata
        """
        pass

    def is_available(self) -> bool:
        """Check if engine dependencies are available."""
        return True
