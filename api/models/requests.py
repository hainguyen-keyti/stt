"""
API Request Models

Pydantic models for validating incoming API requests.
"""

from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import Optional, Literal


class ASREngine(str, Enum):
    """Available ASR engines"""

    FASTER_WHISPER = "faster-whisper"
    WHISPERX = "whisperx"
    STABLE_TS = "stable-ts"


class ModelSize(str, Enum):
    """Whisper model sizes"""

    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    LARGE_V3 = "large-v3"


class ComputeType(str, Enum):
    """Quantization/compute types"""

    INT8 = "int8"
    INT8_FLOAT16 = "int8_float16"
    FLOAT16 = "float16"
    FLOAT32 = "float32"


class DemucsModel(str, Enum):
    """Demucs vocal separation models"""

    HTDEMUCS = "htdemucs"
    MDX = "mdx"
    MDX_EXTRA = "mdx_extra"


class TranscriptionRequest(BaseModel):
    """
    Request parameters for audio transcription.

    Configures ASR engine, model, preprocessing, and output options.
    """

    # ASR Configuration
    engine: ASREngine = Field(
        default=ASREngine.FASTER_WHISPER,
        description="ASR engine to use (speed vs accuracy trade-off)",
    )
    model_size: ModelSize = Field(
        default=ModelSize.LARGE_V3, description="Whisper model size"
    )
    compute_type: ComputeType = Field(
        default=ComputeType.FLOAT16,
        description="Quantization type (affects speed and VRAM)",
    )

    # Language Configuration
    language: Optional[str] = Field(
        default=None,
        description="ISO 639-1 language code (e.g., 'en', 'es') or null for auto-detect",
    )

    # Preprocessing Configuration
    use_demucs: Optional[bool | Literal["auto"]] = Field(
        default="auto",
        description="Apply Demucs vocal separation: true/false/auto (based on analysis)",
    )
    demucs_model: DemucsModel = Field(
        default=DemucsModel.MDX_EXTRA, description="Demucs model variant"
    )
    vad_filter: bool = Field(
        default=True, description="Apply voice activity detection to remove silence"
    )

    # Output Configuration
    word_timestamps: bool = Field(
        default=True, description="Include word-level timestamps"
    )
    batch_size: int = Field(
        default=16,
        ge=1,
        le=64,
        description="Batch size for inference (higher = faster but more VRAM)",
    )

    @field_validator("language")
    @classmethod
    def validate_language_code(cls, v):
        """Validate ISO 639-1 language codes"""
        if v is None:
            return v
        if len(v) != 2 or not v.isalpha():
            raise ValueError("Language must be 2-letter ISO 639-1 code (e.g., 'en')")
        return v.lower()

    model_config = {
        "json_schema_extra": {
            "example": {
                "engine": "whisperx",
                "model_size": "large-v3",
                "language": "en",
                "use_demucs": "auto",
                "word_timestamps": True,
            }
        }
    }


class SubtitleFormat(str, Enum):
    """Supported subtitle formats"""

    SRT = "srt"
    VTT = "vtt"
    ASS = "ass"
    JSON = "json"


class SubtitleRequest(TranscriptionRequest):
    """
    Extended transcription request with subtitle formatting options.

    Inherits all transcription parameters and adds format-specific configuration.
    """

    # Format Selection
    format: SubtitleFormat = Field(
        default=SubtitleFormat.SRT, description="Output subtitle format"
    )

    # Formatting Options
    word_level: bool = Field(
        default=False,
        description="One word per subtitle cue (requires word_timestamps=True)",
    )
    max_line_width: int = Field(
        default=42, ge=20, le=100, description="Maximum characters per line"
    )
    max_line_count: int = Field(
        default=2, ge=1, le=3, description="Maximum lines per subtitle cue"
    )

    # VTT-Specific
    highlight_words: bool = Field(
        default=False, description="Enable karaoke word highlighting (VTT only)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "engine": "whisperx",
                "model_size": "large-v3",
                "format": "vtt",
                "word_level": False,
                "highlight_words": True,
                "word_timestamps": True,
            }
        }
    }
