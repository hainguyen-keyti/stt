"""
ASR Engine implementations and interfaces.
"""

from modules.stt.engines.base import ASREngine, TranscriptionResult, Segment, Word, EngineInfo
from modules.stt.engines.factory import EngineFactory, get_engine
from modules.stt.engines.faster_whisper import FasterWhisperEngine, FASTER_WHISPER_AVAILABLE
from modules.stt.engines.openai_whisper import OpenAIWhisperEngine, OPENAI_WHISPER_AVAILABLE

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
