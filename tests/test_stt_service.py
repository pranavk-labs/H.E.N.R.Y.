"""Tests for speech-to-text (STT) service."""

import pytest
from unittest.mock import patch, MagicMock
import numpy as np
import builtins

from backend.services.stt_service import SpeechToTextService
from backend.config.settings import Settings

# Save original import to avoid recursion
_original_import = builtins.__import__


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = Settings()
    settings.stt_engine = "none"
    settings.whisper_model_size = "small"
    return settings


def test_stt_service_singleton():
    """Test that SpeechToTextService is a singleton."""
    # Reset instance
    SpeechToTextService._instance = None

    service1 = SpeechToTextService.get_instance()
    service2 = SpeechToTextService.get_instance()
    assert service1 is service2


def test_stt_service_none_engine():
    """Test STT service with 'none' engine raises when transcribe called."""
    # Reset instance
    SpeechToTextService._instance = None

    settings = Settings()
    settings.stt_engine = "none"
    service = SpeechToTextService(settings)

    with pytest.raises(RuntimeError, match="Speech-to-text engine.*not configured"):
        service.transcribe(b"test audio", 16000)


def test_stt_service_dummy_engine():
    """Test STT service with 'dummy' engine returns empty string."""
    # Reset instance
    SpeechToTextService._instance = None

    settings = Settings()
    settings.stt_engine = "dummy"
    service = SpeechToTextService(settings)

    result = service.transcribe(b"test audio", 16000)
    assert result == ""


@patch("builtins.__import__")
def test_stt_service_whisper_engine_success(mock_import):
    """Test STT service with OpenAI Whisper engine successfully transcribes."""
    # Reset instance
    SpeechToTextService._instance = None

    # Mock OpenAI Whisper module and model
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "hello world"}
    mock_load_model = MagicMock(return_value=mock_model)
    mock_whisper_module = MagicMock()
    mock_whisper_module.load_model = mock_load_model

    def import_side_effect(name, *args, **kwargs):
        if name == "whisper":
            return mock_whisper_module
        return _original_import(name, *args, **kwargs)

    mock_import.side_effect = import_side_effect

    settings = Settings()
    settings.stt_engine = "whisper"
    settings.whisper_model_size = "small"
    service = SpeechToTextService(settings)

    # Verify model was loaded
    assert service._whisper_model is not None
    mock_load_model.assert_called_once_with("small")

    # Test transcription
    audio_bytes = np.zeros(16000, dtype=np.int16).tobytes()  # 1 second at 16kHz
    result = service.transcribe(audio_bytes, 16000)

    assert result == "hello world"
    mock_model.transcribe.assert_called_once()
    # Verify fp16=False for CPU compatibility
    call_kwargs = mock_model.transcribe.call_args[1]
    assert call_kwargs.get("fp16") is False


@patch("builtins.__import__")
def test_stt_service_whisper_engine_custom_model_size(mock_import):
    """Test STT service with OpenAI Whisper loads custom model size."""
    # Reset instance
    SpeechToTextService._instance = None

    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "test"}
    mock_load_model = MagicMock(return_value=mock_model)
    mock_whisper_module = MagicMock()
    mock_whisper_module.load_model = mock_load_model

    def import_side_effect(name, *args, **kwargs):
        if name == "whisper":
            return mock_whisper_module
        return _original_import(name, *args, **kwargs)

    mock_import.side_effect = import_side_effect

    settings = Settings()
    settings.stt_engine = "whisper"
    settings.whisper_model_size = "base"
    service = SpeechToTextService(settings)

    mock_load_model.assert_called_once_with("base")


@patch("builtins.__import__")
def test_stt_service_whisper_import_error(mock_import):
    """Test STT service falls back to 'none' when OpenAI Whisper import fails."""
    # Reset instance
    SpeechToTextService._instance = None

    def import_side_effect(name, *args, **kwargs):
        if name == "whisper":
            raise ImportError("No module named 'whisper'")
        return _original_import(name, *args, **kwargs)

    mock_import.side_effect = import_side_effect

    settings = Settings()
    settings.stt_engine = "whisper"
    service = SpeechToTextService(settings)

    # Should fall back to 'none'
    assert service.engine == "none"
    assert service._whisper_model is None

    # Should raise when transcribe called
    with pytest.raises(RuntimeError):
        service.transcribe(b"test", 16000)


@patch("builtins.__import__")
def test_stt_service_whisper_load_error(mock_import):
    """Test STT service handles OpenAI Whisper model load errors gracefully."""
    # Reset instance
    SpeechToTextService._instance = None

    mock_load_model = MagicMock(side_effect=Exception("Model load failed"))
    mock_whisper_module = MagicMock()
    mock_whisper_module.load_model = mock_load_model

    def import_side_effect(name, *args, **kwargs):
        if name == "whisper":
            return mock_whisper_module
        return _original_import(name, *args, **kwargs)

    mock_import.side_effect = import_side_effect

    settings = Settings()
    settings.stt_engine = "whisper"
    service = SpeechToTextService(settings)

    # Should fall back to 'none'
    assert service.engine == "none"
    assert service._whisper_model is None


@patch("builtins.__import__")
def test_stt_service_whisper_transcribe_error(mock_import):
    """Test STT service handles OpenAI Whisper transcription errors gracefully."""
    # Reset instance
    SpeechToTextService._instance = None

    mock_model = MagicMock()
    mock_model.transcribe.side_effect = Exception("Transcription failed")
    mock_load_model = MagicMock(return_value=mock_model)
    mock_whisper_module = MagicMock()
    mock_whisper_module.load_model = mock_load_model

    def import_side_effect(name, *args, **kwargs):
        if name == "whisper":
            return mock_whisper_module
        return _original_import(name, *args, **kwargs)

    mock_import.side_effect = import_side_effect

    settings = Settings()
    settings.stt_engine = "whisper"
    service = SpeechToTextService(settings)

    # Transcription should return empty string on error
    result = service.transcribe(b"test audio", 16000)
    assert result == ""


@patch("builtins.__import__")
def test_stt_service_whisper_audio_format_conversion(mock_import):
    """Test STT service converts audio format correctly for OpenAI Whisper."""
    # Reset instance
    SpeechToTextService._instance = None

    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "converted"}
    mock_load_model = MagicMock(return_value=mock_model)
    mock_whisper_module = MagicMock()
    mock_whisper_module.load_model = mock_load_model

    def import_side_effect(name, *args, **kwargs):
        if name == "whisper":
            return mock_whisper_module
        return _original_import(name, *args, **kwargs)

    mock_import.side_effect = import_side_effect

    settings = Settings()
    settings.stt_engine = "whisper"
    settings.whisper_model_size = "small"
    service = SpeechToTextService(settings)

    # Create int16 audio bytes (typical microphone format)
    audio_int16 = np.array([1000, -1000, 2000, -2000], dtype=np.int16)
    audio_bytes = audio_int16.tobytes()

    result = service.transcribe(audio_bytes, 16000)

    assert result == "converted"
    # Verify transcribe was called with float32 array
    call_args = mock_model.transcribe.call_args
    audio_array = call_args[0][0]
    assert audio_array.dtype == np.float32
    assert len(audio_array) == 4


def test_stt_service_unknown_engine():
    """Test STT service with unknown engine raises."""
    # Reset instance
    SpeechToTextService._instance = None

    settings = Settings()
    settings.stt_engine = "unknown_engine"
    service = SpeechToTextService(settings)

    with pytest.raises(RuntimeError, match="Speech-to-text engine.*not configured"):
        service.transcribe(b"test", 16000)
