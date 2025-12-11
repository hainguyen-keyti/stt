"""
OpenAI Whisper ASR Engine (Official)

Original Whisper implementation from OpenAI.
Simple, reliable, with natural segmentation.
"""

import time
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from lib.engines.base import ASREngine, TranscriptionResult, Segment, Word, EngineInfo

logger = logging.getLogger(__name__)

# Check if OpenAI Whisper is available
try:
    import whisper
    import torch
    OPENAI_WHISPER_AVAILABLE = True
except ImportError:
    OPENAI_WHISPER_AVAILABLE = False
    logger.warning("OpenAI Whisper not available. Install with: pip install openai-whisper")


class OpenAIWhisperEngine(ASREngine):
    """
    OpenAI Whisper ASR engine (official implementation).

    Features:
    - Natural speech segmentation (VAD-based)
    - Simple and reliable
    - No complex alignment needed
    - Good balance of speed and accuracy
    """

    def __init__(self):
        if not OPENAI_WHISPER_AVAILABLE:
            raise ImportError(
                "OpenAI Whisper is not installed. "
                "Install with: pip install openai-whisper"
            )

        self.model: Optional[Any] = None
        self.model_size: Optional[str] = None
        self.device: str = "cpu"

    def load_model(self, model_size: str, config: dict):
        """
        Load OpenAI Whisper model.

        Args:
            model_size: Model size (tiny, base, small, medium, large, large-v2, large-v3)
            config: Configuration dict with:
                - device: "cpu" or "cuda"
                - download_root: Optional path for model cache
        """
        start_time = time.time()

        self.device = config.get("device", "cpu")
        download_root = config.get("download_root", None)

        logger.info(f"Loading OpenAI Whisper model: {model_size} on {self.device}")

        try:
            self.model = whisper.load_model(
                model_size,
                device=self.device,
                download_root=download_root,
            )
            self.model_size = model_size

            load_time = time.time() - start_time
            logger.info(f"OpenAI Whisper model loaded in {load_time:.2f}s")

        except Exception as e:
            logger.error(f"Failed to load OpenAI Whisper model: {e}")
            raise RuntimeError(f"Failed to load model '{model_size}': {e}")

    def transcribe(self, audio_path: str, config: dict) -> TranscriptionResult:
        """
        Transcribe audio with OpenAI Whisper.

        Args:
            audio_path: Path to audio file
            config: Transcription configuration:
                - language: Optional language code (e.g., "en", "zh")
                - word_timestamps: Enable word-level timestamps (default: False)
                - temperature: Sampling temperature (default: 0.0)
                - beam_size: Beam search size (default: 5)
                - best_of: Number of candidates (default: 5)
                - condition_on_previous_text: Use previous text as context (default: True)
                - initial_prompt: Optional text to guide transcription style/vocabulary

        Returns:
            TranscriptionResult with segments and optional word timestamps
        """
        if self.model is None:
            raise Exception("Model not loaded. Call load_model() first.")

        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Extract configuration
        language = config.get("language", None)
        word_timestamps = config.get("word_timestamps", False)
        temperature = config.get("temperature", 0.0)
        beam_size = config.get("beam_size", 5)
        best_of = config.get("best_of", 5)
        condition_on_previous_text = config.get("condition_on_previous_text", True)
        initial_prompt = config.get("initial_prompt", None)
        no_speech_threshold = config.get("no_speech_threshold", 0.6)
        compression_ratio_threshold = config.get("compression_ratio_threshold", 2.4)
        logprob_threshold = config.get("logprob_threshold", -1.0)

        logger.info(f"Transcribing: {audio_path}")
        logger.info(f"Config: language={language}, word_timestamps={word_timestamps}, initial_prompt={initial_prompt}")

        inference_start = time.time()

        try:
            # Transcribe with OpenAI Whisper
            result = self.model.transcribe(
                audio_path,
                language=language,
                word_timestamps=word_timestamps,
                temperature=temperature,
                beam_size=beam_size,
                best_of=best_of,
                condition_on_previous_text=condition_on_previous_text,
                initial_prompt=initial_prompt,
                no_speech_threshold=no_speech_threshold,
                compression_ratio_threshold=compression_ratio_threshold,
                logprob_threshold=logprob_threshold,
                verbose=False,  # Disable verbose output
            )

            inference_time_ms = (time.time() - inference_start) * 1000

            # Convert to our TranscriptionResult format
            return self._convert_result(result, inference_time_ms)

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"OpenAI Whisper transcription failed: {e}")

    def _convert_result(
        self,
        whisper_result: dict,
        inference_time_ms: float
    ) -> TranscriptionResult:
        """
        Convert OpenAI Whisper result to our TranscriptionResult format.

        Args:
            whisper_result: Raw Whisper result dict
            inference_time_ms: Inference time in milliseconds

        Returns:
            TranscriptionResult with standardized format
        """
        segments = []
        full_text_parts = []

        for seg in whisper_result.get("segments", []):
            seg_start = float(seg.get("start", 0.0))
            seg_end = float(seg.get("end", 0.0))
            seg_text = seg.get("text", "").strip()

            # Skip invalid segments
            if seg_end <= seg_start or not seg_text:
                logger.warning(f"Skipping invalid segment: start={seg_start}, end={seg_end}, text='{seg_text}'")
                continue

            # Extract word-level timestamps if available
            words = []
            if "words" in seg and seg["words"]:
                for word_data in seg["words"]:
                    word_start = float(word_data.get("start", 0.0))
                    word_end = float(word_data.get("end", 0.0))
                    word_text = word_data.get("word", "").strip()

                    # Skip invalid words
                    if word_end <= word_start or not word_text:
                        continue

                    try:
                        word = Word(
                            start=word_start,
                            end=word_end,
                            word=word_text,
                            confidence=word_data.get("probability", None),
                        )
                        words.append(word)
                    except Exception as e:
                        logger.warning(f"Failed to create Word object: {e}")
                        continue

            # Create segment
            segment = Segment(
                start=seg_start,
                end=seg_end,
                text=seg_text,
                words=words if words else None,
            )
            segments.append(segment)
            full_text_parts.append(segment.text)

        # Combine all segment text
        full_text = " ".join(full_text_parts).strip()
        detected_language = whisper_result.get("language", "unknown")

        return TranscriptionResult(
            text=full_text,
            language=detected_language,
            segments=segments,
            inference_time_ms=inference_time_ms,
        )

    def get_info(self) -> EngineInfo:
        """
        Get engine information and capabilities.

        Returns:
            EngineInfo with engine metadata
        """
        return EngineInfo(
            name="openai-whisper",
            version="20250625",
            supports_word_timestamps=True,
            supported_models=[
                "tiny",
                "base",
                "small",
                "medium",
                "large",
                "large-v2",
                "large-v3",
            ],
        )

    def unload_model(self):
        """
        Unload model from memory to free resources.
        """
        logger.info("Unloading OpenAI Whisper model")

        self.model = None

        # Clear CUDA cache if available
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            logger.info("Cleared CUDA cache")
