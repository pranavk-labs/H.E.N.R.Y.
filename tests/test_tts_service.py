"""Tests for text-to-speech (TTS) service."""

import pytest
from unittest.mock import patch, MagicMock
import builtins

from backend.services.tts_service import TextToSpeechService
from backend.config.settings import Settings

# Save original import to avoid recursion
_original_import = builtins.__import__


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = Settings()
    settings.tts_engine = "log"
    settings.tts_rate = 175
    settings.tts_volume = 1.0
    return settings


def test_tts_service_singleton():
    """Test that TextToSpeechService is a singleton."""
    # Reset instance
    TextToSpeechService._instance = None

    service1 = TextToSpeechService.get_instance()
    service2 = TextToSpeechService.get_instance()
    assert service1 is service2


def test_tts_service_log_engine():
    """Test TTS service with 'log' engine just logs text."""
    # Reset instance
    TextToSpeechService._instance = None

    settings = Settings()
    settings.tts_engine = "log"
    service = TextToSpeechService(settings)

    with patch("backend.services.tts_service.logger") as mock_logger:
        service.speak("Hello, world!")

        mock_logger.info.assert_called_once()
        # Check that it was called with format string and text
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "TTS(log): %s"
        assert call_args[0][1] == "Hello, world!"


def test_tts_service_log_engine_empty_text():
    """Test TTS service with 'log' engine ignores empty text."""
    # Reset instance
    TextToSpeechService._instance = None

    settings = Settings()
    settings.tts_engine = "log"
    service = TextToSpeechService(settings)

    with patch("backend.services.tts_service.logger") as mock_logger:
        service.speak("")
        service.speak("   ")

        # Should not log empty strings
        mock_logger.info.assert_not_called()


@patch("builtins.__import__")
def test_tts_service_pyttsx3_engine_success(mock_import):
    """Test TTS service with pyttsx3 engine successfully speaks."""
    # Reset instance
    TextToSpeechService._instance = None

    # Mock pyttsx3
    mock_engine = MagicMock()
    mock_voice = MagicMock()
    mock_voice.id = "test_voice"
    mock_engine.getProperty.return_value = [mock_voice]
    mock_pyttsx3_module = MagicMock()
    mock_pyttsx3_module.init.return_value = mock_engine
    
    def import_side_effect(name, *args, **kwargs):
        if name == "pyttsx3":
            return mock_pyttsx3_module
        return _original_import(name, *args, **kwargs)
    
    mock_import.side_effect = import_side_effect

    settings = Settings()
    settings.tts_engine = "pyttsx3"
    settings.tts_rate = 175
    settings.tts_volume = 1.0
    service = TextToSpeechService(settings)

    # Verify engine was initialized
    assert service._pyttsx3 is not None
    mock_pyttsx3_module.init.assert_called_once()
    mock_engine.setProperty.assert_any_call("voice", "test_voice")
    mock_engine.setProperty.assert_any_call("rate", 175)
    mock_engine.setProperty.assert_any_call("volume", 1.0)

    # Test speaking
    service.speak("Hello, world!")

    mock_engine.say.assert_called_once_with("Hello, world!")
    mock_engine.runAndWait.assert_called_once()


@patch("builtins.__import__")
def test_tts_service_pyttsx3_custom_settings(mock_import):
    """Test TTS service with pyttsx3 uses custom rate and volume."""
    # Reset instance
    TextToSpeechService._instance = None

    mock_engine = MagicMock()
    mock_engine.getProperty.return_value = []
    mock_pyttsx3_module = MagicMock()
    mock_pyttsx3_module.init.return_value = mock_engine
    
    def import_side_effect(name, *args, **kwargs):
        if name == "pyttsx3":
            return mock_pyttsx3_module
        return _original_import(name, *args, **kwargs)
    
    mock_import.side_effect = import_side_effect

    settings = Settings()
    settings.tts_engine = "pyttsx3"
    settings.tts_rate = 200
    settings.tts_volume = 0.8
    service = TextToSpeechService(settings)

    # Verify custom settings were applied
    mock_engine.setProperty.assert_any_call("rate", 200)
    mock_engine.setProperty.assert_any_call("volume", 0.8)


@patch("builtins.__import__")
def test_tts_service_pyttsx3_import_error(mock_import):
    """Test TTS service falls back to 'log' when pyttsx3 import fails."""
    # Reset instance
    TextToSpeechService._instance = None

    def import_side_effect(name, *args, **kwargs):
        if name == "pyttsx3":
            raise ImportError("No module named 'pyttsx3'")
        return _original_import(name, *args, **kwargs)
    
    mock_import.side_effect = import_side_effect

    settings = Settings()
    settings.tts_engine = "pyttsx3"
    service = TextToSpeechService(settings)

    # Should fall back to 'log'
    assert service.engine_name == "log"
    assert service._pyttsx3 is None

    # Should log instead of speak
    with patch("backend.services.tts_service.logger") as mock_logger:
        service.speak("test")
        mock_logger.info.assert_called_once()


@patch("builtins.__import__")
def test_tts_service_pyttsx3_init_error(mock_import):
    """Test TTS service falls back to 'log' when pyttsx3 init fails."""
    # Reset instance
    TextToSpeechService._instance = None

    mock_pyttsx3_module = MagicMock()
    mock_pyttsx3_module.init.side_effect = Exception("Init failed")
    
    def import_side_effect(name, *args, **kwargs):
        if name == "pyttsx3":
            return mock_pyttsx3_module
        return _original_import(name, *args, **kwargs)
    
    mock_import.side_effect = import_side_effect

    settings = Settings()
    settings.tts_engine = "pyttsx3"
    service = TextToSpeechService(settings)

    # Should fall back to 'log'
    assert service.engine_name == "log"
    assert service._pyttsx3 is None


@patch("builtins.__import__")
def test_tts_service_pyttsx3_speak_error(mock_import):
    """Test TTS service handles pyttsx3 speak errors gracefully."""
    # Reset instance
    TextToSpeechService._instance = None

    mock_engine = MagicMock()
    mock_engine.getProperty.return_value = []
    mock_engine.say.side_effect = Exception("Speak failed")
    mock_pyttsx3_module = MagicMock()
    mock_pyttsx3_module.init.return_value = mock_engine
    
    def import_side_effect(name, *args, **kwargs):
        if name == "pyttsx3":
            return mock_pyttsx3_module
        return _original_import(name, *args, **kwargs)
    
    mock_import.side_effect = import_side_effect

    settings = Settings()
    settings.tts_engine = "pyttsx3"
    service = TextToSpeechService(settings)

    # Should fall back to logging on error
    with patch("backend.services.tts_service.logger") as mock_logger:
        service.speak("test")
        mock_logger.error.assert_called_once()
        mock_logger.info.assert_called_once()  # Fallback log


@patch("builtins.__import__")
def test_tts_service_pyttsx3_empty_text(mock_import):
    """Test TTS service with pyttsx3 ignores empty text."""
    # Reset instance
    TextToSpeechService._instance = None

    mock_engine = MagicMock()
    mock_engine.getProperty.return_value = []
    mock_pyttsx3_module = MagicMock()
    mock_pyttsx3_module.init.return_value = mock_engine
    
    def import_side_effect(name, *args, **kwargs):
        if name == "pyttsx3":
            return mock_pyttsx3_module
        return _original_import(name, *args, **kwargs)
    
    mock_import.side_effect = import_side_effect

    settings = Settings()
    settings.tts_engine = "pyttsx3"
    service = TextToSpeechService(settings)

    service.speak("")
    service.speak("   ")

    # Should not call say for empty strings
    mock_engine.say.assert_not_called()


@patch("builtins.__import__")
def test_tts_service_pyttsx3_no_voices(mock_import):
    """Test TTS service with pyttsx3 handles no voices gracefully."""
    # Reset instance
    TextToSpeechService._instance = None

    mock_engine = MagicMock()
    mock_engine.getProperty.return_value = []  # No voices
    mock_pyttsx3_module = MagicMock()
    mock_pyttsx3_module.init.return_value = mock_engine
    
    def import_side_effect(name, *args, **kwargs):
        if name == "pyttsx3":
            return mock_pyttsx3_module
        return _original_import(name, *args, **kwargs)
    
    mock_import.side_effect = import_side_effect

    settings = Settings()
    settings.tts_engine = "pyttsx3"
    service = TextToSpeechService(settings)

    # Should still work without voices
    assert service._pyttsx3 is not None
    service.speak("test")
    mock_engine.say.assert_called_once()

