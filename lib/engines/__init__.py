"""
ASR Engine implementations and interfaces.
"""

from lib.engines.base import ASREngine, TranscriptionResult, Segment, Word, EngineInfo
from lib.engines.factory import EngineFactory, get_engine
from lib.engines.faster_whisper import FasterWhisperEngine, FASTER_WHISPER_AVAILABLE
from lib.engines.openai_whisper import OpenAIWhisperEngine, OPENAI_WHISPER_AVAILABLE

__all__ = [
    "ASREngine",
    "TranscriptionResult",
    "Segment",
    "Word",
    "EngineInfo",
    "EngineFactory",
    "get_engine",
    "FasterWhisperEngine",
    "FASTER_WHISPER_AVAILABLE",
    "OpenAIWhisperEngine",
    "OPENAI_WHISPER_AVAILABLE",
]
