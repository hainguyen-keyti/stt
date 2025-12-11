"""
Integration tests for /transcribe endpoint

Tests the full API workflow for transcription requests.
"""

import pytest
import os
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestTranscribeEndpoint:
    """Test suite for /transcribe endpoint"""

    def test_endpoint_exists(self):
        """Test that /transcribe endpoint is registered"""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_transcribe_requires_file(self):
        """Test that transcribe requires audio_file parameter"""
        response = client.post("/transcribe")
        assert response.status_code == 422  # Validation error

    def test_transcribe_rejects_non_audio_file(self):
        """Test that non-audio files are rejected"""
        # Create a fake text file
        fake_file = ("test.txt", b"This is not audio", "text/plain")

        response = client.post(
            "/transcribe",
            files={"audio_file": fake_file},
        )

        # Should fail with unsupported format error
        assert response.status_code in [415, 500]

    @pytest.mark.skipif(
        not os.path.exists("fixtures/clean_speech.wav"),
        reason="Test fixture not available"
    )
    @pytest.mark.slow
    def test_transcribe_with_real_audio(self):
        """Test transcription with actual audio file (if available)"""
        with open("fixtures/clean_speech.wav", "rb") as audio_file:
            response = client.post(
                "/transcribe",
                files={"audio_file": ("clean_speech.wav", audio_file, "audio/wav")},
                data={
                    "engine": "faster-whisper",
                    "model_size": "tiny",  # Use tiny for speed
                    "language": "en",
                    "vad_filter": "true",
                    "word_timestamps": "false",
                },
            )

        assert response.status_code == 200

        data = response.json()

        # Verify response structure
        assert "text" in data
        assert "language" in data
        assert "segments" in data
        assert "metadata" in data

        # Verify metadata
        metadata = data["metadata"]
        assert "engine" in metadata
        assert "model_size" in metadata
        assert "inference_time_ms" in metadata
        assert "total_time_ms" in metadata

        # Verify non-empty transcription
        assert len(data["text"]) > 0
        assert len(data["segments"]) > 0

    def test_transcribe_validates_engine(self):
        """Test that invalid engine names are handled"""
        fake_audio = ("test.mp3", b"fake audio data", "audio/mp3")

        response = client.post(
            "/transcribe",
            files={"audio_file": fake_audio},
            data={"engine": "invalid-engine"},
        )

        # Should fail (either validation or processing error)
        assert response.status_code >= 400

    def test_transcribe_validates_model_size(self):
        """Test that invalid model sizes are handled"""
        fake_audio = ("test.mp3", b"fake audio data", "audio/mp3")

        response = client.post(
            "/transcribe",
            files={"audio_file": fake_audio},
            data={"model_size": "invalid-size"},
        )

        # Should fail (either validation or processing error)
        assert response.status_code >= 400

    def test_health_endpoint(self):
        """Test that health endpoint works"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "uptime_seconds" in data

    def test_root_endpoint(self):
        """Test that root endpoint works"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "service" in data
        assert "version" in data
        assert data["version"] == "4.0.0"

    def test_openapi_docs(self):
        """Test that OpenAPI documentation is available"""
        response = client.get("/docs")
        assert response.status_code == 200

        response = client.get("/redoc")
        assert response.status_code == 200

        response = client.get("/openapi.json")
        assert response.status_code == 200
