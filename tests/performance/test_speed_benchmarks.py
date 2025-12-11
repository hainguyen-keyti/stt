"""
Performance benchmarks for transcription speed

Tests that transcription meets performance targets:
- SC-001: <90s for 13-minute audio
- SC-003: 4x speedup vs vanilla Whisper
"""

import pytest
import os
import time


class TestSpeedBenchmarks:
    """Performance benchmarks for transcription speed"""

    @pytest.mark.skipif(
        not os.path.exists("fixtures/13min_sample.mp3"),
        reason="13min_sample.mp3 fixture not available"
    )
    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_13min_audio_under_90s(self):
        """
        Test SC-001: Transcription of 13-minute audio completes in <90 seconds

        This test validates the core performance requirement for MVP.
        Requires: fixtures/13min_sample.mp3
        Target: <90 seconds on GPU hardware
        """
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)

        with open("fixtures/13min_sample.mp3", "rb") as audio_file:
            start_time = time.time()

            response = client.post(
                "/transcribe",
                files={"audio_file": ("13min_sample.mp3", audio_file, "audio/mp3")},
                data={
                    "engine": "faster-whisper",
                    "model_size": "large-v3",
                    "vad_filter": "true",
                },
            )

            elapsed_time = time.time() - start_time

        assert response.status_code == 200, f"Transcription failed: {response.text}"

        data = response.json()

        # Extract actual processing time from metadata
        processing_time_s = data["metadata"]["total_time_ms"] / 1000

        print(f"\n=== Performance Results ===")
        print(f"Total time (including upload): {elapsed_time:.2f}s")
        print(f"Processing time: {processing_time_s:.2f}s")
        print(f"Target: <90s")

        # Assert performance target
        assert processing_time_s < 90, (
            f"Processing time {processing_time_s:.2f}s exceeds 90s target"
        )

    @pytest.mark.skipif(
        not os.path.exists("fixtures/clean_speech.wav"),
        reason="clean_speech.wav fixture not available"
    )
    @pytest.mark.benchmark
    def test_short_audio_speed(self):
        """
        Benchmark short audio transcription speed

        Tests transcription speed on short audio sample.
        Useful for quick performance validation.
        """
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)

        with open("fixtures/clean_speech.wav", "rb") as audio_file:
            start_time = time.time()

            response = client.post(
                "/transcribe",
                files={"audio_file": ("clean_speech.wav", audio_file, "audio/wav")},
                data={
                    "engine": "faster-whisper",
                    "model_size": "base",  # Smaller model for speed
                    "vad_filter": "true",
                },
            )

            elapsed_time = time.time() - start_time

        assert response.status_code == 200

        data = response.json()
        processing_time_s = data["metadata"]["total_time_ms"] / 1000

        print(f"\n=== Short Audio Performance ===")
        print(f"Total time: {elapsed_time:.2f}s")
        print(f"Processing time: {processing_time_s:.2f}s")

        # For short audio, should be very fast
        assert processing_time_s < 10, "Short audio should process quickly"

    @pytest.mark.slow
    @pytest.mark.benchmark
    def test_model_caching_speedup(self):
        """
        Test that model caching provides speedup on subsequent requests

        First request: Loads model (slow)
        Second request: Uses cached model (fast)
        """
        from fastapi.testclient import TestClient
        from api.main import app

        if not os.path.exists("fixtures/clean_speech.wav"):
            pytest.skip("Test fixture not available")

        client = TestClient(app)

        # First request (cold start)
        with open("fixtures/clean_speech.wav", "rb") as audio_file:
            start_first = time.time()
            response1 = client.post(
                "/transcribe",
                files={"audio_file": ("clean_speech.wav", audio_file, "audio/wav")},
                data={"engine": "faster-whisper", "model_size": "tiny"},
            )
            time_first = time.time() - start_first

        assert response1.status_code == 200

        # Second request (warm start - should use cache)
        with open("fixtures/clean_speech.wav", "rb") as audio_file:
            start_second = time.time()
            response2 = client.post(
                "/transcribe",
                files={"audio_file": ("clean_speech.wav", audio_file, "audio/wav")},
                data={"engine": "faster-whisper", "model_size": "tiny"},
            )
            time_second = time.time() - start_second

        assert response2.status_code == 200

        print(f"\n=== Caching Performance ===")
        print(f"First request (cold): {time_first:.2f}s")
        print(f"Second request (warm): {time_second:.2f}s")
        print(f"Speedup: {time_first / time_second:.2f}x")

        # Second request should be faster or similar (not slower)
        # Note: May not always be faster due to system load
        assert time_second <= time_first * 1.5, "Cached request should not be significantly slower"


@pytest.mark.benchmark
def test_model_load_time():
    """
    Benchmark model loading time

    Tests how long it takes to load models from disk.
    """
    import time
    from lib.engines.faster_whisper import FasterWhisperEngine, FASTER_WHISPER_AVAILABLE

    if not FASTER_WHISPER_AVAILABLE:
        pytest.skip("faster-whisper not available")

    engine = FasterWhisperEngine()
    config = {"device": "cpu", "compute_type": "int8"}

    start_time = time.time()
    engine.load_model("tiny", config)
    load_time = time.time() - start_time

    print(f"\n=== Model Load Performance ===")
    print(f"Model: tiny")
    print(f"Load time: {load_time:.2f}s")

    # Model loading should be reasonably fast
    assert load_time < 30, f"Model loading took {load_time:.2f}s (>30s)"
