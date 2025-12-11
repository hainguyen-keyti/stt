"""
ASR Engine Base Classes and Interfaces

Defines the abstract interface that all ASR engines must implement,
along with common data structures for transcription results.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class Word(BaseModel):
    """
    Word-level timestamp and confidence.

    Used for karaoke subtitles and high-precision timing.
    """

    start: float = Field(ge=0.0, description="Word start time in seconds")
    end: float = Field(gt=0.0, description="Word end time in seconds")
    word: str = Field(min_length=1, description="The word text")
    confidence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Confidence score (0-1), if available"
    )

    @field_validator("end")
    @classmethod
    def end_after_start(cls, v, info):
        """Ensure end time is after start time"""
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("end must be greater than start")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "start": 0.0,
                "end": 0.5,
                "word": "Hello",
                "confidence": 0.98,
            }
        }
    }


class Segment(BaseModel):
    """
    Time-aligned transcript segment (sentence or phrase).

    Represents a contiguous block of text with timestamps.
    """

    start: float = Field(ge=0.0, description="Start time in seconds")
    end: float = Field(gt=0.0, description="End time in seconds (must be > start)")
    text: str = Field(min_length=1, description="Transcribed text for this segment")
    words: Optional[List[Word]] = Field(
        default=None, description="Word-level timestamps (if available)"
    )

    @field_validator("end")
    @classmethod
    def end_after_start(cls, v, info):
        """Ensure end time is after start time"""
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("end must be greater than start")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "start": 0.0,
                "end": 2.5,
                "text": "Hello world",
                "words": [
                    {"start": 0.0, "end": 0.5, "word": "Hello", "confidence": 0.98},
                    {"start": 0.5, "end": 1.0, "word": "world", "confidence": 0.97},
                ],
            }
        }
    }


class TranscriptionResult(BaseModel):
    """
    Complete transcription result from an ASR engine.

    Contains the full transcript, time-aligned segments, metadata about
    the transcription process, and performance metrics.
    """

    text: str = Field(description="Full transcription text")
    language: str = Field(description="Detected or specified language code")
    segments: List[Segment] = Field(
        description="Time-aligned segments (sentences/phrases)"
    )
    inference_time_ms: float = Field(
        description="Inference time in milliseconds", ge=0.0
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Hello world. This is a test.",
                "language": "en",
                "segments": [
                    {"start": 0.0, "end": 2.5, "text": "Hello world.", "words": None},
                    {"start": 2.5, "end": 5.0, "text": "This is a test.", "words": None},
                ],
                "inference_time_ms": 1523.5,
            }
        }
    }


class EngineInfo(BaseModel):
    """
    Information about an ASR engine's capabilities and version.
    """

    name: str = Field(description="Engine name")
    version: str = Field(description="Engine version")
    supported_models: List[str] = Field(description="Supported model sizes")
    supports_word_timestamps: bool = Field(
        description="Whether engine supports word-level timestamps"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "faster-whisper",
                "version": "1.0.0",
                "supported_models": ["tiny", "base", "small", "medium", "large", "large-v3"],
                "supports_word_timestamps": True,
            }
        }
    }


class ASREngine(ABC):
    """
    Abstract base class for ASR (Automatic Speech Recognition) engines.

    All ASR engine implementations (faster-whisper, openai-whisper)
    must inherit from this class and implement its abstract methods.

    This provides a unified interface for transcription regardless of the
    underlying engine, enabling engine selection at runtime.
    """

    @abstractmethod
    def load_model(self, model_size: str, config: dict):
        """
        Load the ASR model with specified configuration.

        Args:
            model_size: Model size identifier (e.g., "base", "large-v3")
            config: Configuration dict with engine-specific parameters
                   (device, compute_type, etc.)

        Raises:
            Exception: If model loading fails
        """
        pass

    @abstractmethod
    def transcribe(self, audio_path: str, config: dict) -> TranscriptionResult:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to audio file
            config: Transcription configuration (language, vad_filter, etc.)

        Returns:
            TranscriptionResult: Complete transcription with segments and metadata

        Raises:
            Exception: If transcription fails
        """
        pass

    @abstractmethod
    def get_info(self) -> EngineInfo:
        """
        Get information about this engine's capabilities.

        Returns:
            EngineInfo: Engine metadata and capabilities
        """
        pass
