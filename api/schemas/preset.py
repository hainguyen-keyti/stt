"""
Preset Schema/DTO

Defines the structure for transcription presets.
All presets must follow this schema.
"""

from typing import Optional
from pydantic import BaseModel, Field


class TranscriptionConfig(BaseModel):
    """Transcription engine configuration."""
    model_config = {"protected_namespaces": ()}

    model_size: str = Field(default="large-v3", description="Model size (tiny, base, small, medium, large-v3, turbo)")
    language: Optional[str] = Field(default=None, description="Language code (e.g., 'en', 'zh', 'vi') or None for auto-detect")
    word_timestamps: bool = Field(default=True, description="Enable word-level timestamps")
    beam_size: int = Field(default=5, ge=1, le=20, description="Beam search size")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="Sampling temperature")
    best_of: int = Field(default=5, ge=1, le=10, description="Number of candidates for beam search")
    condition_on_previous_text: bool = Field(default=True, description="Use previous text as context")
    no_speech_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="No speech detection threshold")
    compression_ratio_threshold: float = Field(default=2.4, ge=0.0, description="Compression ratio threshold")
    logprob_threshold: float = Field(default=-1.0, description="Log probability threshold")
    initial_prompt: Optional[str] = Field(default=None, description="Initial prompt for context/vocabulary guidance")
    # faster-whisper specific
    vad_filter: bool = Field(default=True, description="Enable VAD filtering (faster-whisper only)")


class FormatterConfig(BaseModel):
    """SRT formatter configuration."""
    max_line_width: int = Field(default=42, ge=10, le=100, description="Maximum characters per line")
    max_line_count: int = Field(default=2, ge=1, le=3, description="Maximum lines per subtitle")
    adjust_timing: bool = Field(default=False, description="Adjust timing based on text length")
    split_by_punctuation: bool = Field(default=False, description="Split subtitles at punctuation marks")
    word_level: bool = Field(default=False, description="One word per subtitle")


class PresetSchema(BaseModel):
    """
    Complete preset schema.

    All preset JSON files must follow this structure.
    """
    id: Optional[str] = Field(default=None, description="Preset ID (auto-generated from filename)")
    title: str = Field(..., description="Display title for the preset")
    engine: str = Field(default="faster-whisper", description="ASR engine (faster-whisper, openai-whisper)")
    description: str = Field(default="", description="Description of the preset")
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig, description="Transcription settings")
    formatter: FormatterConfig = Field(default_factory=FormatterConfig, description="Formatter settings")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Default",
                "engine": "faster-whisper",
                "description": "Default transcription settings",
                "transcription": {
                    "model_size": "large-v3",
                    "language": None,
                    "word_timestamps": True,
                    "beam_size": 5,
                    "temperature": 0.0,
                    "best_of": 5,
                    "condition_on_previous_text": True,
                    "no_speech_threshold": 0.6,
                    "compression_ratio_threshold": 2.4,
                    "logprob_threshold": -1.0,
                    "initial_prompt": None,
                    "vad_filter": True
                },
                "formatter": {
                    "max_line_width": 42,
                    "max_line_count": 2,
                    "adjust_timing": False,
                    "split_by_punctuation": False,
                    "word_level": False
                }
            }
        }


# Default preset values for reference
DEFAULT_TRANSCRIPTION = TranscriptionConfig()
DEFAULT_FORMATTER = FormatterConfig()
