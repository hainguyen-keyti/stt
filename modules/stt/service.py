"""
STT Service Layer

High-level service for speech-to-text transcription.
Encapsulates all business logic for transcription workflow.
"""

import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from modules.stt.models import get_model_manager
from modules.stt.formatters import SRTFormatter
from modules.stt.utils.gpu import get_optimal_device, get_optimal_compute_type, is_gpu_available, get_vram_info

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionRequest:
    """Request parameters for transcription."""
    audio_path: str
    output_format: str = "srt"  # srt or json
    engine: str = "faster-whisper"
    model_size: str = "large-v3"
    compute_type: Optional[str] = None

    # Transcription options
    language: Optional[str] = None
    vad_filter: bool = True
    word_timestamps: bool = True
    batch_size: int = 16
    beam_size: int = 5
    temperature: float = 0.0
    best_of: int = 5
    condition_on_previous_text: bool = True
    no_speech_threshold: float = 0.6
    compression_ratio_threshold: float = 2.4
    logprob_threshold: float = -1.0
    initial_prompt: Optional[str] = None

    # Formatter options
    word_level: bool = False
    max_line_width: int = 42
    max_line_count: int = 2
    adjust_timing: bool = False
    split_by_punctuation: bool = False


@dataclass
class TranscriptionResult:
    """Result of transcription."""
    success: bool
    output_type: str  # srt or json
    content: Optional[str] = None  # For SRT
    data: Optional[Dict[str, Any]] = None  # For JSON
    filename: Optional[str] = None
    error: Optional[str] = None

    # Metrics
    total_time_ms: float = 0.0
    inference_time_ms: float = 0.0
    preprocessing_time_ms: float = 0.0
    audio_duration_s: float = 0.0
    real_time_factor: float = 0.0
    vram_used_mb: Optional[float] = None


class STTService:
    """
    Speech-to-Text Service.

    Provides high-level API for transcription workflow:
    - Model loading and management
    - Audio transcription
    - Output formatting (SRT/JSON)
    - Metrics collection
    """

    def __init__(self):
        self.model_manager = get_model_manager()

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        """
        Transcribe audio file to subtitles.

        Args:
            request: TranscriptionRequest with all parameters

        Returns:
            TranscriptionResult with output and metrics
        """
        request_start_time = time.time()

        try:
            # Validate audio file
            if not Path(request.audio_path).exists():
                return TranscriptionResult(
                    success=False,
                    output_type=request.output_format,
                    error=f"Audio file not found: {request.audio_path}"
                )

            # Auto-detect compute type
            compute_type = request.compute_type or get_optimal_compute_type()

            # Load engine
            engine_config = {
                "device": get_optimal_device(),
                "compute_type": compute_type,
            }

            preprocessing_start = time.time()
            engine = self.model_manager.get_engine(
                request.engine,
                request.model_size,
                engine_config
            )
            preprocessing_time_ms = (time.time() - preprocessing_start) * 1000

            # Build transcription config
            transcription_config = {
                "language": request.language,
                "vad_filter": request.vad_filter,
                "word_timestamps": request.word_timestamps,
                "batch_size": request.batch_size,
                "beam_size": request.beam_size,
                "temperature": request.temperature,
                "best_of": request.best_of,
                "condition_on_previous_text": request.condition_on_previous_text,
                "no_speech_threshold": request.no_speech_threshold,
                "compression_ratio_threshold": request.compression_ratio_threshold,
                "logprob_threshold": request.logprob_threshold,
                "initial_prompt": request.initial_prompt,
            }

            # Transcribe
            inference_start = time.time()
            result = engine.transcribe(request.audio_path, transcription_config)
            inference_time_ms = (time.time() - inference_start) * 1000

            total_time_ms = (time.time() - request_start_time) * 1000

            # Calculate metrics
            audio_duration_s = result.segments[-1].end if result.segments else 0
            real_time_factor = (total_time_ms / 1000) / audio_duration_s if audio_duration_s > 0 else 0

            vram_used_mb = None
            if is_gpu_available():
                vram_info = get_vram_info()
                vram_used_mb = vram_info.get("allocated_mb")

            # Format output
            if request.output_format == "json":
                return self._format_json_result(
                    result, request,
                    total_time_ms, inference_time_ms, preprocessing_time_ms,
                    audio_duration_s, real_time_factor, vram_used_mb
                )
            else:
                return self._format_srt_result(
                    result, request,
                    total_time_ms, inference_time_ms,
                    audio_duration_s
                )

        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            return TranscriptionResult(
                success=False,
                output_type=request.output_format,
                error=str(e)
            )

    def _format_json_result(
        self, result, request: TranscriptionRequest,
        total_time_ms: float, inference_time_ms: float, preprocessing_time_ms: float,
        audio_duration_s: float, real_time_factor: float, vram_used_mb: Optional[float]
    ) -> TranscriptionResult:
        """Format transcription result as JSON."""
        words_list = []
        for segment in result.segments:
            if segment.words:
                words_list.extend([
                    {"word": w.word, "start": w.start, "end": w.end}
                    for w in segment.words
                ])

        data = {
            "text": result.text,
            "language": result.language,
            "segments": [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                    "words": [
                        {"word": w.word, "start": w.start, "end": w.end}
                        for w in seg.words
                    ] if seg.words else None
                }
                for seg in result.segments
            ],
            "words": words_list if words_list else None,
            "metadata": {
                "engine": request.engine,
                "model_size": request.model_size,
                "language": result.language,
                "preprocessing": "vad_only" if request.vad_filter else "none",
                "audio_duration_s": audio_duration_s,
                "inference_time_ms": inference_time_ms,
                "preprocessing_time_ms": preprocessing_time_ms,
                "total_time_ms": total_time_ms,
                "real_time_factor": real_time_factor,
                "vram_used_mb": vram_used_mb,
            }
        }

        return TranscriptionResult(
            success=True,
            output_type="json",
            data=data,
            total_time_ms=total_time_ms,
            inference_time_ms=inference_time_ms,
            preprocessing_time_ms=preprocessing_time_ms,
            audio_duration_s=audio_duration_s,
            real_time_factor=real_time_factor,
            vram_used_mb=vram_used_mb,
        )

    def _format_srt_result(
        self, result, request: TranscriptionRequest,
        total_time_ms: float, inference_time_ms: float,
        audio_duration_s: float
    ) -> TranscriptionResult:
        """Format transcription result as SRT."""
        formatter = SRTFormatter(
            max_line_width=request.max_line_width,
            max_line_count=request.max_line_count,
            adjust_timing=request.adjust_timing,
            split_by_punctuation=request.split_by_punctuation,
        )
        content = formatter.format(
            result.segments,
            word_level=request.word_level
        )

        # Generate filename from audio path
        audio_filename = Path(request.audio_path).stem
        srt_filename = f"{audio_filename}.srt"

        return TranscriptionResult(
            success=True,
            output_type="srt",
            content=content,
            filename=srt_filename,
            total_time_ms=total_time_ms,
            inference_time_ms=inference_time_ms,
            audio_duration_s=audio_duration_s,
        )


# Global service instance
_stt_service: Optional[STTService] = None


def get_stt_service() -> STTService:
    """Get global STT service instance."""
    global _stt_service
    if _stt_service is None:
        _stt_service = STTService()
    return _stt_service
