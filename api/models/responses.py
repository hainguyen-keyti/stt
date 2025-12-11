"""
API Response Models

Pydantic models for API responses including transcription results,
health status, metrics, and subtitle files.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

# Import base models from lib
from lib.engines.base import Segment, Word


class PreprocessStrategy(str, Enum):
    """Preprocessing strategy recommendations"""

    USE_DEMUCS = "use_demucs"
    VAD_ONLY = "vad_only"
    SKIP_PREPROCESSING = "skip_preprocessing"


class AudioAnalysis(BaseModel):
    """
    Audio analysis results and preprocessing recommendation.

    Provides insights into audio characteristics and suggests
    optimal preprocessing strategy.
    """

    # Basic Properties
    duration_s: float = Field(description="Audio duration in seconds")
    sample_rate: int = Field(description="Audio sample rate in Hz")
    channels: int = Field(description="Number of audio channels")

    # Quality Metrics
    snr_db: Optional[float] = Field(
        default=None, description="Signal-to-noise ratio in decibels"
    )
    rms_energy: float = Field(description="Root mean square energy")
    silence_ratio: float = Field(
        ge=0.0, le=1.0, description="Ratio of silence to total duration (0-1)"
    )

    # Music Detection
    has_music: bool = Field(description="Whether music/instrumentation detected")
    music_confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence score for music detection (0-1)"
    )
    spectral_centroid_mean: float = Field(
        description="Mean spectral centroid frequency in Hz"
    )

    # Recommendations
    preprocessing_recommended: bool = Field(
        description="Whether any preprocessing is recommended"
    )
    use_demucs: bool = Field(
        description="Whether vocal separation (Demucs) is recommended"
    )
    quality_score: float = Field(
        ge=0.0, le=100.0, description="Overall audio quality score (0-100)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "duration_s": 13.5,
                "sample_rate": 44100,
                "channels": 2,
                "snr_db": 18.5,
                "rms_energy": 0.12,
                "silence_ratio": 0.15,
                "has_music": True,
                "music_confidence": 0.85,
                "spectral_centroid_mean": 2450.0,
                "preprocessing_recommended": True,
                "use_demucs": True,
                "quality_score": 75.0,
            }
        }
    }


class TranscriptionMetadata(BaseModel):
    """
    Metadata about the transcription process.

    Includes performance metrics and processing information.
    """

    engine: str = Field(description="ASR engine used")
    model_size: str = Field(description="Model size used")
    language: str = Field(description="Detected or specified language")
    preprocessing: str = Field(
        description="Preprocessing applied (e.g., 'demucs_mdx_extra', 'vad_only', 'none')"
    )

    # Performance Metrics
    audio_duration_s: float = Field(description="Audio duration in seconds")
    inference_time_ms: float = Field(description="Inference time in milliseconds")
    preprocessing_time_ms: float = Field(
        description="Preprocessing time in milliseconds"
    )
    total_time_ms: float = Field(description="Total processing time")
    real_time_factor: float = Field(
        description="Ratio of processing time to audio duration (<1 is faster than real-time)"
    )

    # Resource Usage
    vram_used_mb: Optional[float] = Field(
        default=None, description="VRAM used in MB"
    )


class Transcription(BaseModel):
    """
    Complete transcription result with metadata.
    """

    # Transcript Content
    text: str = Field(description="Full transcription text")
    language: str = Field(description="Detected or specified language code")
    segments: List[Segment] = Field(
        description="Time-aligned segments (sentences/phrases)"
    )
    words: Optional[List[Word]] = Field(
        default=None, description="Word-level timestamps (if word_timestamps=True)"
    )

    # Metadata
    metadata: TranscriptionMetadata = Field(
        description="Processing metadata and performance metrics"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Hello world. This is a test.",
                "language": "en",
                "segments": [
                    {"start": 0.0, "end": 2.5, "text": "Hello world.", "words": None}
                ],
                "words": None,
                "metadata": {
                    "engine": "faster-whisper",
                    "model_size": "large-v3",
                    "language": "en",
                    "preprocessing": "vad_only",
                    "audio_duration_s": 5.0,
                    "inference_time_ms": 1523.5,
                    "preprocessing_time_ms": 100.0,
                    "total_time_ms": 1623.5,
                    "real_time_factor": 0.32,
                    "vram_used_mb": 4500.0,
                },
            }
        }
    }


class SubtitleFile(BaseModel):
    """
    Formatted subtitle file output.
    """

    # Content
    content: str = Field(
        description="Subtitle file content (formatted according to format)"
    )
    format: str = Field(description="Subtitle format (srt, vtt, ass, json)")
    encoding: str = Field(default="utf-8", description="Character encoding")

    # Validation
    is_valid: bool = Field(description="Whether subtitle file passes format validation")
    validation_errors: Optional[List[str]] = Field(
        default=None, description="Validation errors if any"
    )

    # Metadata (from transcription)
    metadata: TranscriptionMetadata = Field(description="Processing metadata")


class HealthStatus(str, Enum):
    """Service health status levels"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class LoadedModel(BaseModel):
    """Information about a loaded model"""

    engine: str = Field(description="Engine name")
    model_size: str = Field(description="Model size")
    vram_mb: float = Field(description="VRAM used by this model in MB")


class Health(BaseModel):
    """
    Service health information.

    Provides current service status, GPU availability, and loaded models.
    """

    status: HealthStatus = Field(description="Overall health status")
    gpu_available: bool = Field(description="Whether GPU is available")
    gpu_name: Optional[str] = Field(default=None, description="GPU device name")
    vram_total_mb: Optional[float] = Field(default=None, description="Total VRAM in MB")
    vram_used_mb: Optional[float] = Field(default=None, description="Used VRAM in MB")
    vram_usage_percent: Optional[float] = Field(
        default=None, description="VRAM usage percentage"
    )
    loaded_models: List[LoadedModel] = Field(
        default_factory=list, description="Currently loaded models"
    )
    uptime_seconds: float = Field(description="Service uptime in seconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "gpu_available": True,
                "gpu_name": "NVIDIA RTX 4090",
                "vram_total_mb": 24564.0,
                "vram_used_mb": 6234.0,
                "vram_usage_percent": 25.4,
                "loaded_models": [],
                "uptime_seconds": 3600.0,
            }
        }
    }


class Metrics(BaseModel):
    """
    Service performance metrics.

    Provides request statistics, latency percentiles, and resource utilization.
    """

    # Request Statistics
    requests_total: int = Field(description="Total requests processed")
    requests_last_hour: int = Field(description="Requests in last hour")
    requests_per_minute: float = Field(description="Current request rate")

    # Latency Statistics
    avg_inference_time_ms: float = Field(description="Average inference time")
    p50_inference_time_ms: float = Field(description="50th percentile inference time")
    p95_inference_time_ms: float = Field(description="95th percentile inference time")
    p99_inference_time_ms: float = Field(description="99th percentile inference time")

    # Resource Utilization
    gpu_utilization_percent: Optional[float] = Field(
        default=None, description="Current GPU utilization percentage"
    )
    vram_usage_percent: Optional[float] = Field(
        default=None, description="Current VRAM usage percentage"
    )

    # Cache Statistics
    cache_hit_rate: float = Field(
        ge=0.0, le=1.0, description="Model cache hit rate (0-1)"
    )

    # Error Statistics
    error_rate: float = Field(
        ge=0.0, le=1.0, description="Error rate (errors / total requests)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "requests_total": 1523,
                "requests_last_hour": 45,
                "requests_per_minute": 0.75,
                "avg_inference_time_ms": 2156.3,
                "p50_inference_time_ms": 1800.0,
                "p95_inference_time_ms": 4200.0,
                "p99_inference_time_ms": 8500.0,
                "gpu_utilization_percent": 72.5,
                "vram_usage_percent": 45.2,
                "cache_hit_rate": 0.67,
                "error_rate": 0.02,
            }
        }
    }
