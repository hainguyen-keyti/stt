"""
Unit tests for FasterWhisperEngine

Tests the faster-whisper ASR engine implementation.
"""

import pytest
from lib.engines.faster_whisper import FasterWhisperEngine, FASTER_WHISPER_AVAILABLE
from lib.engines.base import EngineInfo


class TestFasterWhisperEngine:
    """Test suite for FasterWhisperEngine"""

    def test_engine_creation(self):
        """Test that engine can be instantiated"""
        if not FASTER_WHISPER_AVAILABLE:
            pytest.skip("faster-whisper not available")

        engine = FasterWhisperEngine()
        assert engine is not None
        assert engine.model is None  # Model not loaded yet

    def test_get_info(self):
        """Test engine info retrieval"""
        if not FASTER_WHISPER_AVAILABLE:
            pytest.skip("faster-whisper not available")

        engine = FasterWhisperEngine()
        info = engine.get_info()

        assert isinstance(info, EngineInfo)
        assert info.name == "faster-whisper"
        assert info.supports_word_timestamps is True
        assert len(info.supported_models) > 0
        assert "large-v3" in info.supported_models

    @pytest.mark.slow
    def test_load_model_tiny(self):
        """Test loading tiny model (fast test)"""
        if not FASTER_WHISPER_AVAILABLE:
            pytest.skip("faster-whisper not available")

        engine = FasterWhisperEngine()
        config = {"device": "cpu", "compute_type": "int8"}

        # Load tiny model (smallest, fastest)
        engine.load_model("tiny", config)

        assert engine.model is not None
        assert engine.model_size == "tiny"

    @pytest.mark.slow
    @pytest.mark.skipif("not os.path.exists('fixtures/clean_speech.wav')")
    def test_transcribe_with_fixture(self):
        """Test transcription with actual audio file (if available)"""
        import os

        if not FASTER_WHISPER_AVAILABLE:
            pytest.skip("faster-whisper not available")

        if not os.path.exists("fixtures/clean_speech.wav"):
            pytest.skip("Test fixture clean_speech.wav not available")

        engine = FasterWhisperEngine()
        config = {"device": "cpu", "compute_type": "int8"}
        engine.load_model("tiny", config)

        # Transcribe
        transcribe_config = {
            "language": "en",
            "vad_filter": True,
            "word_timestamps": False,
        }

        result = engine.transcribe("fixtures/clean_speech.wav", transcribe_config)

        assert result is not None
        assert result.text is not None
        assert len(result.text) > 0
        assert result.language == "en"
        assert len(result.segments) > 0
        assert result.inference_time_ms > 0

    def test_transcribe_without_model_fails(self):
        """Test that transcription fails if model not loaded"""
        if not FASTER_WHISPER_AVAILABLE:
            pytest.skip("faster-whisper not available")

        engine = FasterWhisperEngine()

        with pytest.raises(Exception, match="Model not loaded"):
            engine.transcribe("fake_audio.wav", {})

    def test_transcribe_missing_file_fails(self):
        """Test that transcription fails with missing audio file"""
        if not FASTER_WHISPER_AVAILABLE:
            pytest.skip("faster-whisper not available")

        engine = FasterWhisperEngine()
        config = {"device": "cpu", "compute_type": "int8"}
        engine.load_model("tiny", config)

        with pytest.raises(FileNotFoundError):
            engine.transcribe("nonexistent_file.wav", {})
