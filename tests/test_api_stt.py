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


def test_transcribe_success(client):
    """Test successful transcription via API."""
    # Create test audio (1 second of silence at 16kHz)
    audio_array = np.zeros(16000, dtype=np.int16)
    audio_bytes = audio_array.tobytes()
    audio_b64 = base64.b64encode(audio_bytes).decode()

    # Mock the STT service
    with patch.object(SpeechToTextService, 'transcribe', return_value="hello world"):
        response = client.post(
            "/stt/transcribe",
            json={"audio_data": audio_b64, "sample_rate": 16000}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "hello world"
    assert data["language"] == "en"


def test_transcribe_empty_result(client):
    """Test transcription returning empty text."""
    audio_array = np.zeros(16000, dtype=np.int16)
    audio_bytes = audio_array.tobytes()
    audio_b64 = base64.b64encode(audio_bytes).decode()

    # Mock the STT service to return empty string
    with patch.object(SpeechToTextService, 'transcribe', return_value=""):
        response = client.post(
            "/stt/transcribe",
            json={"audio_data": audio_b64, "sample_rate": 16000}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["text"] == ""
    assert data["language"] == "en"


def test_transcribe_invalid_base64(client):
    """Test transcription with invalid base64 audio."""
    response = client.post(
        "/stt/transcribe",
        json={"audio_data": "invalid-base64!!!!", "sample_rate": 16000}
    )

    assert response.status_code == 400
    assert "Invalid base64" in response.json()["detail"]


def test_transcribe_missing_audio_data(client):
    """Test transcription with missing audio_data field."""
    response = client.post(
        "/stt/transcribe",
        json={"sample_rate": 16000}
    )

    assert response.status_code == 422  # Validation error


def test_transcribe_custom_sample_rate(client):
    """Test transcription with custom sample rate."""
    audio_array = np.zeros(8000, dtype=np.int16)  # 1 second at 8kHz
    audio_bytes = audio_array.tobytes()
    audio_b64 = base64.b64encode(audio_bytes).decode()

    # Mock the STT service and verify sample rate is passed
    mock_transcribe = MagicMock(return_value="test transcription")
    with patch.object(SpeechToTextService, 'transcribe', mock_transcribe):
        response = client.post(
            "/stt/transcribe",
            json={"audio_data": audio_b64, "sample_rate": 8000}
        )

    assert response.status_code == 200
    # Verify transcribe was called with correct sample rate
    mock_transcribe.assert_called_once()
    call_args = mock_transcribe.call_args
    assert call_args[0][1] == 8000  # Second argument is sample_rate


def test_transcribe_stt_engine_not_configured(client):
    """Test transcription when STT engine is not configured."""
    audio_array = np.zeros(16000, dtype=np.int16)
    audio_bytes = audio_array.tobytes()
    audio_b64 = base64.b64encode(audio_bytes).decode()

    # Mock STT service to raise RuntimeError (engine not configured)
    with patch.object(
        SpeechToTextService,
        'transcribe',
        side_effect=RuntimeError("Speech-to-text engine 'none' is not configured")
    ):
        response = client.post(
            "/stt/transcribe",
            json={"audio_data": audio_b64, "sample_rate": 16000}
        )

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_transcribe_internal_error(client):
    """Test transcription with internal error."""
    audio_array = np.zeros(16000, dtype=np.int16)
    audio_bytes = audio_array.tobytes()
    audio_b64 = base64.b64encode(audio_bytes).decode()

    # Mock STT service to raise generic exception
    with patch.object(
        SpeechToTextService,
        'transcribe',
        side_effect=Exception("Internal transcription error")
    ):
        response = client.post(
            "/stt/transcribe",
            json={"audio_data": audio_b64, "sample_rate": 16000}
        )

    assert response.status_code == 500
    assert "Transcription failed" in response.json()["detail"]


def test_transcribe_large_audio(client):
    """Test transcription with larger audio file (30 seconds)."""
    # 30 seconds at 16kHz
    audio_array = np.zeros(16000 * 30, dtype=np.int16)
    audio_bytes = audio_array.tobytes()
    audio_b64 = base64.b64encode(audio_bytes).decode()

    with patch.object(SpeechToTextService, 'transcribe', return_value="long transcription"):
        response = client.post(
            "/stt/transcribe",
            json={"audio_data": audio_b64, "sample_rate": 16000}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "long transcription"


def test_transcribe_default_sample_rate(client):
    """Test transcription uses default sample rate when not specified."""
    audio_array = np.zeros(16000, dtype=np.int16)
    audio_bytes = audio_array.tobytes()
    audio_b64 = base64.b64encode(audio_bytes).decode()

    mock_transcribe = MagicMock(return_value="test")
    with patch.object(SpeechToTextService, 'transcribe', mock_transcribe):
        response = client.post(
            "/stt/transcribe",
            json={"audio_data": audio_b64}  # No sample_rate specified
        )

    assert response.status_code == 200
    # Should use default 16000 Hz
    call_args = mock_transcribe.call_args
    assert call_args[0][1] == 16000
