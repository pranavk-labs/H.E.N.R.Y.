"""Tests for STT API endpoints."""

import base64
import pytest
from unittest.mock import patch, MagicMock
import numpy as np

from fastapi.testclient import TestClient
from backend.api.main import app
from backend.services.stt_service import SpeechToTextService


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_stt_service():
    """Reset STT service singleton before each test."""
    SpeechToTextService._instance = None
    yield
    SpeechToTextService._instance = None


def _audio_b64(audio_array):
    return base64.b64encode(audio_array.tobytes()).decode()


def _non_silent_audio(samples: int) -> np.ndarray:
    return np.resize(np.array([1000, -1000], dtype=np.int16), samples)


def test_transcribe_success(client):
    """Test successful transcription via API."""
    audio_b64 = _audio_b64(_non_silent_audio(16000))

    # Mock the STT service
    with patch.object(SpeechToTextService, "transcribe", return_value="hello world"):
        response = client.post(
            "/stt/transcribe", json={"audio_data": audio_b64, "sample_rate": 16000}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "hello world"
    assert data["language"] == "en"


def test_transcribe_empty_result(client):
    """Test transcription returning empty text."""
    audio_b64 = _audio_b64(_non_silent_audio(16000))

    # Mock the STT service to return empty string
    with patch.object(SpeechToTextService, "transcribe", return_value=""):
        response = client.post(
            "/stt/transcribe", json={"audio_data": audio_b64, "sample_rate": 16000}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["text"] == ""
    assert data["language"] == "en"


def test_transcribe_silent_audio_skips_stt_service(client):
    """Silent audio should return empty text without loading the STT engine."""
    audio_array = np.zeros(16000, dtype=np.int16)
    audio_b64 = _audio_b64(audio_array)

    with patch.object(SpeechToTextService, "get_instance") as mock_get_instance:
        response = client.post(
            "/stt/transcribe",
            json={"audio_data": audio_b64, "sample_rate": 16000},
        )

    assert response.status_code == 200
    assert response.json() == {"text": "", "language": "en"}
    mock_get_instance.assert_not_called()


def test_transcribe_invalid_base64(client):
    """Test transcription with invalid base64 audio."""
    response = client.post(
        "/stt/transcribe", json={"audio_data": "invalid-base64!!!!", "sample_rate": 16000}
    )

    assert response.status_code == 400
    assert "Invalid base64" in response.json()["detail"]


def test_transcribe_missing_audio_data(client):
    """Test transcription with missing audio_data field."""
    response = client.post("/stt/transcribe", json={"sample_rate": 16000})

    assert response.status_code == 422  # Validation error


def test_transcribe_custom_sample_rate(client):
    """Test transcription with custom sample rate."""
    audio_b64 = _audio_b64(_non_silent_audio(8000))

    # Mock the STT service and verify sample rate is passed
    mock_transcribe = MagicMock(return_value="test transcription")
    with patch.object(SpeechToTextService, "transcribe", mock_transcribe):
        response = client.post(
            "/stt/transcribe", json={"audio_data": audio_b64, "sample_rate": 8000}
        )

    assert response.status_code == 200
    # Verify transcribe was called with correct sample rate
    mock_transcribe.assert_called_once()
    call_args = mock_transcribe.call_args
    assert call_args[0][1] == 8000  # Second argument is sample_rate


def test_transcribe_stt_engine_not_configured(client):
    """Test transcription when STT engine is not configured."""
    audio_b64 = _audio_b64(_non_silent_audio(16000))

    # Mock STT service to raise RuntimeError (engine not configured)
    with patch.object(
        SpeechToTextService,
        "transcribe",
        side_effect=RuntimeError("Speech-to-text engine 'none' is not configured"),
    ):
        response = client.post(
            "/stt/transcribe", json={"audio_data": audio_b64, "sample_rate": 16000}
        )

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_transcribe_internal_error(client):
    """Test transcription with internal error."""
    audio_b64 = _audio_b64(_non_silent_audio(16000))

    # Mock STT service to raise generic exception
    with patch.object(
        SpeechToTextService, "transcribe", side_effect=Exception("Internal transcription error")
    ):
        response = client.post(
            "/stt/transcribe", json={"audio_data": audio_b64, "sample_rate": 16000}
        )

    assert response.status_code == 500
    assert "Transcription failed" in response.json()["detail"]


def test_transcribe_large_audio(client):
    """Test transcription with larger audio file (30 seconds)."""
    audio_b64 = _audio_b64(_non_silent_audio(16000 * 30))

    with patch.object(SpeechToTextService, "transcribe", return_value="long transcription"):
        response = client.post(
            "/stt/transcribe", json={"audio_data": audio_b64, "sample_rate": 16000}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "long transcription"


def test_transcribe_default_sample_rate(client):
    """Test transcription uses default sample rate when not specified."""
    audio_b64 = _audio_b64(_non_silent_audio(16000))

    mock_transcribe = MagicMock(return_value="test")
    with patch.object(SpeechToTextService, "transcribe", mock_transcribe):
        response = client.post(
            "/stt/transcribe", json={"audio_data": audio_b64}  # No sample_rate specified
        )

    assert response.status_code == 200
    # Should use default 16000 Hz
    call_args = mock_transcribe.call_args
    assert call_args[0][1] == 16000
