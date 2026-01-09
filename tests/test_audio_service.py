"""Tests for audio service."""

import pytest
from unittest.mock import patch

from backend.services.audio_service import AudioService
from backend.config.settings import Settings


def test_audio_service_singleton():
    """Test that AudioService is a singleton."""
    # Reset instance
    AudioService._instance = None

    service1 = AudioService.get_instance()
    service2 = AudioService.get_instance()
    assert service1 is service2


def test_audio_service_disabled():
    """Test audio service when disabled."""
    # Reset instance
    AudioService._instance = None

    settings = Settings()
    settings.audio_enabled = False
    service = AudioService(settings)
    health = service.health_check()

    assert health["status"] == "disabled"
    assert health["enabled"] is False


@patch("backend.services.audio_service.sd")
def test_audio_service_health_check(mock_sd):
    """Test audio service health check."""
    # Reset instance
    AudioService._instance = None

    # Mock sounddevice (matches actual API structure - no "channels" key)
    mock_device = {
        "name": "Test Device",
        "index": 0,
        "max_input_channels": 1,
        "max_output_channels": 1,
        "default_samplerate": 44100.0,
        "hostapi": 0,
    }
    mock_sd.query_devices.return_value = [mock_device]

    settings = Settings()
    settings.audio_enabled = True
    service = AudioService(settings)
    health = service.health_check()

    assert health["status"] == "healthy"
    assert health["enabled"] is True
    assert health["input_devices"] == 1
    assert health["output_devices"] == 1


def test_list_devices():
    """Test listing audio devices."""
    # Reset instance
    AudioService._instance = None

    with patch("backend.services.audio_service.sd") as mock_sd:
        # Mock sounddevice (matches actual API structure - no "channels" key)
        mock_device = {
            "name": "Test Device",
            "index": 0,
            "max_input_channels": 1,
            "max_output_channels": 1,
            "default_samplerate": 44100.0,
            "hostapi": 0,
        }
        mock_sd.query_devices.return_value = [mock_device]

        service = AudioService.get_instance()
        devices = service.list_devices()

        assert len(devices) == 1
        assert devices[0]["name"] == "Test Device"
        assert devices[0]["index"] == 0
        assert devices[0]["channels"] == 2  # Calculated from max_input_channels + max_output_channels


@patch("backend.services.audio_service.Model")
def test_initialize_wake_word_detection(mock_model_class):
    """Test wake word detection initialization."""
    # Reset instance
    AudioService._instance = None

    mock_model = mock_model_class.return_value

    settings = Settings()
    settings.audio_enabled = True
    service = AudioService(settings)

    result = service.initialize_wake_word_detection()

    assert result is True
    assert service._oww_model is not None
    mock_model_class.assert_called_once()


def test_initialize_wake_word_detection_disabled():
    """Test wake word detection initialization when audio is disabled."""
    # Reset instance
    AudioService._instance = None

    settings = Settings()
    settings.audio_enabled = False
    service = AudioService(settings)

    result = service.initialize_wake_word_detection()

    assert result is False
    assert service._oww_model is None


def test_detect_wake_word():
    """Test wake word detection."""
    import numpy as np

    # Reset instance
    AudioService._instance = None

    settings = Settings()
    settings.audio_enabled = True
    service = AudioService(settings)

    # Mock the model
    mock_model = type("MockModel", (), {})()
    mock_model.predict = lambda x: {"hey_henry": 0.75, "other_model": 0.3}
    service._oww_model = mock_model

    # Create audio frame as numpy array
    audio_frame = np.zeros(1280, dtype=np.float32)

    result = service.detect_wake_word(audio_frame)

    assert result is True


def test_detect_wake_word_not_initialized():
    """Test wake word detection when model not initialized."""
    # Reset instance
    AudioService._instance = None

    settings = Settings()
    settings.audio_enabled = True
    service = AudioService(settings)
    service._oww_model = None

    import numpy as np
    audio_frame = np.zeros(1280, dtype=np.float32)

    result = service.detect_wake_word(audio_frame)

    assert result is False


