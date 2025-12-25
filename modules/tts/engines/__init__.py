"""
TTS Engines

Available engines:
- EdgeTTS: Microsoft Edge TTS (high quality, Vietnamese support)
- GoogleTTS: Google TTS (simple, reliable)
- CapCutTTS: CapCut/TikTok style voices
- VivibeTTS: Vivibe platform voices (requires token)
"""

from modules.tts.engines.base import TTSEngine, VoiceInfo
from modules.tts.engines.edge_tts import EdgeTTSEngine
from modules.tts.engines.google_tts import GoogleTTSEngine
from modules.tts.engines.capcut import CapCutTTSEngine
from modules.tts.engines.vivibe import VivibeTTSEngine

__all__ = [
    "TTSEngine",
    "VoiceInfo",
    "EdgeTTSEngine",
    "GoogleTTSEngine",
    "CapCutTTSEngine",
    "VivibeTTSEngine",
]
