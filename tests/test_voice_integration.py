"""Integration tests for voice pipeline (AudioService + STT + Conversation + TTS).

These tests verify the full voice pipeline works together, using mocks where needed
to avoid requiring actual hardware or LLM connections.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import numpy as np
import threading

from backend.services.audio_service import AudioService
from backend.services.stt_service import SpeechToTextService
from backend.services.tts_service import TextToSpeechService
from backend.services.conversation_service import ConversationService
from backend.config.settings import Settings


@pytest.fixture
def mock_voice_settings():
    """Create mock settings with voice enabled."""
    settings = Settings()
    settings.audio_enabled = True
    settings.wake_word = "Hey HENRY"
    settings.stt_engine = "dummy"  # Use dummy to avoid requiring Whisper in tests
    settings.tts_engine = "log"  # Use log to avoid requiring pyttsx3 in tests
    settings.ollama_base_url = "http://localhost:11434"
    return settings


def test_voice_pipeline_initialization(mock_voice_settings):
    """Test that all voice services can be initialized together."""
    # Reset instances
    AudioService._instance = None
    SpeechToTextService._instance = None
    TextToSpeechService._instance = None
    ConversationService._instance = None

    # Initialize services
    audio = AudioService.get_instance()
    stt = SpeechToTextService.get_instance()
    tts = TextToSpeechService.get_instance()
    convo = ConversationService.get_instance()

    # Verify all services exist
    assert audio is not None
    assert stt is not None
    assert tts is not None
    assert convo is not None


def test_voice_loop_defaults_to_legacy_runtime(mock_voice_settings):
    """VoiceLoop uses the legacy runtime mode by default."""
    from app.voice_loop import VoiceLoop

    mock_voice_settings.voice_runtime = "legacy"
    mock_voice_settings.voice_runtime_url = "ws://127.0.0.1:8765/v1/realtime"

    with patch("app.voice_loop.get_settings", return_value=mock_voice_settings):
        with patch("app.voice_loop.AudioService.get_instance"):
            with patch("app.voice_loop.SpeechToTextService.get_instance"):
                with patch("app.voice_loop.TextToSpeechService.get_instance"):
                    loop = VoiceLoop(api_base_url="http://127.0.0.1:8000")

    assert loop.runtime_mode == "legacy"
    assert loop.voice_runtime_url == "ws://127.0.0.1:8765/v1/realtime"


@patch("backend.services.conversation_service.OllamaClient")
def test_voice_pipeline_end_to_end(mock_ollama_client_class, mock_voice_settings):
    """Test full voice pipeline: STT → Conversation → TTS."""
    # Reset instances
    SpeechToTextService._instance = None
    TextToSpeechService._instance = None
    ConversationService._instance = None

    # Mock Ollama client
    mock_ollama = AsyncMock()
    mock_ollama.is_connected = True
    mock_ollama.generate = AsyncMock(
        return_value={"response": "I understand. Starting a Pomodoro timer."}
    )
    mock_ollama_client_class.get_instance.return_value = mock_ollama

    # Initialize services
    stt = SpeechToTextService.get_instance()
    tts = TextToSpeechService.get_instance()
    convo = ConversationService.get_instance()

    # Test STT (dummy engine returns empty string, so we'll simulate user input)
    user_text = "Start a pomodoro timer"

    # Test conversation service (handles tool intent for timer)
    with patch("backend.services.conversation_service.ToolsService") as mock_tools:
        # Mock tool execution for timer
        mock_tools.get_instance.return_value.execute_tool.return_value = {
            "session": {"id": "test-session", "status": "running"}
        }

        # Test TTS (log engine should log)
        with patch("backend.services.tts_service.logger") as mock_logger:
            result = convo.handle_utterance(user_text, user_id="test")
            response = result.get("response", "")

            # Verify TTS was called (via log mode)
            tts.speak(response)
            mock_logger.info.assert_called()

            # Verify conversation worked
            assert "response" in result
            # Intent can be "timer.start", "timer.pause", "ideas.create", or "chat"
            assert result["intent"] in ["timer.start", "timer.pause", "ideas.create", "chat"]


def test_voice_pipeline_stt_fallback():
    """Test voice pipeline handles STT failures gracefully."""
    # Reset instances
    SpeechToTextService._instance = None

    settings = Settings()
    settings.stt_engine = "none"  # Will raise on transcribe
    stt = SpeechToTextService(settings)

    # Should raise when transcribe called (caller should handle)
    with pytest.raises(RuntimeError):
        stt.transcribe(b"test audio", 16000)


def test_voice_pipeline_tts_fallback():
    """Test voice pipeline handles TTS failures gracefully."""
    # Reset instances
    TextToSpeechService._instance = None

    settings = Settings()
    settings.tts_engine = "log"  # Always works (logs)
    tts = TextToSpeechService(settings)

    # Should always work (even if just logging)
    with patch("backend.services.tts_service.logger") as mock_logger:
        tts.speak("test message")
        mock_logger.info.assert_called_once()


@patch("backend.services.conversation_service.OllamaClient")
def test_voice_pipeline_conversation_context(mock_ollama_client_class, mock_voice_settings):
    """Test voice pipeline maintains conversation context across turns."""
    # Reset instances
    ConversationService._instance = None

    # Mock Ollama
    mock_ollama = AsyncMock()
    mock_ollama.is_connected = True
    mock_ollama.generate = AsyncMock(
        return_value={"response": "Yes, I remember. We were talking about that."}
    )
    mock_ollama_client_class.get_instance.return_value = mock_ollama

    convo = ConversationService.get_instance()

    # First utterance (will go to LLM since it's not a tool intent)
    result1 = convo.handle_utterance("I'm working on a project", user_id="test")
    assert "response" in result1

    # Second utterance (should have context from first turn)
    result2 = convo.handle_utterance("What was I talking about?", user_id="test")
    assert "response" in result2

    # Verify history is maintained (should have user + assistant turns)
    history = convo.get_history("test")
    assert len(history) >= 4  # At least 2 user + 2 assistant turns


def test_voice_pipeline_settings_validation():
    """Test that voice pipeline validates settings correctly."""
    # Reset instances to ensure clean state
    AudioService._instance = None
    SpeechToTextService._instance = None
    TextToSpeechService._instance = None

    settings = Settings()

    # Test with audio disabled
    settings.audio_enabled = False
    audio = AudioService(settings)
    health = audio.health_check()
    # When audio is disabled, status should be "disabled" or enabled should be False
    assert health["status"] == "disabled" or health.get("enabled") is False

    # Test with dummy STT
    settings.stt_engine = "dummy"
    stt = SpeechToTextService(settings)
    result = stt.transcribe(b"test", 16000)
    assert result == ""  # Dummy returns empty string

    # Test with log TTS
    settings.tts_engine = "log"
    tts = TextToSpeechService(settings)
    with patch("backend.services.tts_service.logger") as mock_logger:
        tts.speak("test")
        mock_logger.info.assert_called()
