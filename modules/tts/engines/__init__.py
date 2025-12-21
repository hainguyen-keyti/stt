"""
TTS Engines

Available engines:
- EdgeTTS: Microsoft Edge TTS (high quality, Vietnamese support)
- GoogleTTS: Google TTS (simple, reliable)
"""

from modules.tts.engines.base import TTSEngine, VoiceInfo
from modules.tts.engines.edge_tts import EdgeTTSEngine
from modules.tts.engines.google_tts import GoogleTTSEngine

__all__ = [
    "TTSEngine",
    "VoiceInfo",
    "EdgeTTSEngine",
    "GoogleTTSEngine",
]
