"""
faster-whisper Engine Implementation

Provides high-speed transcription using CTranslate2 optimization.
Achieves 4x speedup compared to vanilla Whisper while maintaining accuracy.
"""

import logging
import time
from typing import Optional
from pathlib import Path

from lib.engines.base import (
    ASREngine,
    TranscriptionResult,
    Segment,
    Word,
    EngineInfo,
)

logger = logging.getLogger(__name__)

# Try to import faster_whisper
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    logger.warning("faster-whisper not available - install with: pip install faster-whisper")


class FasterWhisperEngine(ASREngine):
    """
    faster-whisper implementation of ASR engine.

    Uses CTranslate2 for optimized inference with 4x speedup.
    Best for: Production speed requirements, batch processing.
    """

    def __init__(self):
        """Initialize the faster-whisper engine."""
        if not FASTER_WHISPER_AVAILABLE:
            raise ImportError("faster-whisper not installed")

        self.model: Optional[WhisperModel] = None
        self.model_size: Optional[str] = None
        self.device: str = "cpu"
        self.compute_type: str = "int8"

    def load_model(self, model_size: str, config: dict):
        """
        Load Whisper model with CTranslate2 optimization.

        Args:
            model_size: Model size (tiny, base, small, medium, large, large-v3)
            config: Configuration dict with:
                - device: "cuda" or "cpu" (default: auto-detect)
                - compute_type: "int8", "float16", "float32" (default: auto)
                - download_root: Model cache directory (optional)
                - local_files_only: Use only cached models (default: False)

        Raises:
            Exception: If model loading fails
        """
        try:
            # Extract config
            self.device = config.get("device", "cpu")
            self.compute_type = config.get("compute_type", "int8")
            download_root = config.get("download_root", None)
            local_files_only = config.get("local_files_only", False)

            logger.info(
                f"Loading faster-whisper model: {model_size}",
                extra={
                    "metadata": {
                        "model_size": model_size,
                        "device": self.device,
                        "compute_type": self.compute_type,
                    }
                },
            )

            start_time = time.time()

            # Load model with CTranslate2 optimization
            self.model = WhisperModel(
                model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root=download_root,
                local_files_only=local_files_only,
            )

            self.model_size = model_size
            load_time = (time.time() - start_time) * 1000

            logger.info(
                f"Model loaded successfully in {load_time:.1f}ms",
                extra={
                    "metadata": {
                        "model_size": model_size,
                        "load_time_ms": load_time,
                    }
                },
            )

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise Exception(f"Model loading failed: {str(e)}")

    def transcribe(self, audio_path: str, config: dict) -> TranscriptionResult:
        """
        Transcribe audio file using faster-whisper.

        Args:
            audio_path: Path to audio file
            config: Transcription configuration:
                - language: Language code (e.g., "en") or None for auto-detect
                - vad_filter: Enable VAD filtering (default: True)
                - vad_parameters: VAD configuration dict
                - word_timestamps: Enable word-level timestamps (default: False)
                - beam_size: Beam size for decoding (default: 5)
                - best_of: Number of candidates for beam search (default: 5)
                - temperature: Sampling temperature (default: 0.0)
                - initial_prompt: Optional text to guide transcription style/vocabulary

        Returns:
            TranscriptionResult: Complete transcription with segments

        Raises:
            Exception: If transcription fails
        """
        if self.model is None:
            raise Exception("Model not loaded. Call load_model() first.")

        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            # Extract config
            language = config.get("language", None)
            vad_filter = config.get("vad_filter", True)
            word_timestamps = config.get("word_timestamps", False)
            beam_size = config.get("beam_size", 5)
            best_of = config.get("best_of", 5)
            temperature = config.get("temperature", 0.0)
            vad_parameters = config.get("vad_parameters", None)
            initial_prompt = config.get("initial_prompt", None)

            logger.info(
                f"Transcribing audio: {audio_path}",
                extra={
                    "metadata": {
                        "audio_path": audio_path,
                        "language": language,
                        "vad_filter": vad_filter,
                        "word_timestamps": word_timestamps,
                        "initial_prompt": initial_prompt,
                    }
                },
            )

            start_time = time.time()

            # Transcribe with faster-whisper
            segments_generator, info = self.model.transcribe(
                audio_path,
                language=language,
                vad_filter=vad_filter,
                vad_parameters=vad_parameters,
                word_timestamps=word_timestamps,
                beam_size=beam_size,
                best_of=best_of,
                temperature=temperature,
                initial_prompt=initial_prompt,
            )

            # Convert generator to list and extract segments
            segments_list = []
            full_text_parts = []

            for segment in segments_generator:
                # Build segment text
                text = segment.text.strip()
                full_text_parts.append(text)

                # Extract word timestamps if available
                words_list = None
                if word_timestamps and hasattr(segment, "words") and segment.words:
                    words_list = []
                    for word in segment.words:
                        # Skip words with invalid timestamps (end <= start)
                        # This can happen with faster-whisper in edge cases
                        if word.end <= word.start:
                            logger.warning(
                                f"Skipping word with invalid timestamps: '{word.word}' "
                                f"(start={word.start}, end={word.end})"
                            )
                            continue
                        
                        try:
                            words_list.append(
                                Word(
                                    start=word.start,
                                    end=word.end,
                                    word=word.word.strip(),
                                    confidence=word.probability if hasattr(word, "probability") else None,
                                )
                            )
                        except Exception as e:
                            logger.warning(f"Failed to create Word object: {e}")
                            continue
                    
                    # If no valid words, set to None
                    if not words_list:
                        words_list = None


                # Create segment
                segments_list.append(
                    Segment(
                        start=segment.start,
                        end=segment.end,
                        text=text,
                        words=words_list,
                    )
                )

            inference_time_ms = (time.time() - start_time) * 1000

            # Build full transcript
            full_text = " ".join(full_text_parts)
            detected_language = info.language if hasattr(info, "language") else (language or "unknown")

            logger.info(
                f"Transcription complete in {inference_time_ms:.1f}ms",
                extra={
                    "metadata": {
                        "inference_time_ms": inference_time_ms,
                        "segment_count": len(segments_list),
                        "language": detected_language,
                    }
                },
            )

            return TranscriptionResult(
                text=full_text,
                language=detected_language,
                segments=segments_list,
                inference_time_ms=inference_time_ms,
            )

        except MemoryError as e:
            logger.error(f"Out of memory during transcription: {e}")
            raise Exception(f"Insufficient memory (OOM): {str(e)}")
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise Exception(f"Transcription failed: {str(e)}")

    def get_info(self) -> EngineInfo:
        """
        Get information about faster-whisper engine.

        Returns:
            EngineInfo: Engine capabilities and version
        """
        try:
            import faster_whisper
            version = getattr(faster_whisper, "__version__", "unknown")
        except:
            version = "unknown"

        return EngineInfo(
            name="faster-whisper",
            version=version,
            supported_models=[
                "tiny",
                "tiny.en",
                "base",
                "base.en",
                "small",
                "small.en",
                "medium",
                "medium.en",
                "large",
                "large-v1",
                "large-v2",
                "large-v3",
            ],
            supports_word_timestamps=True,
        )
