"""Tests for voice runtime lifecycle service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.config.settings import Settings
from backend.services.voice_runtime_service import VoiceRuntimeService


def make_settings(command: str = "speech-to-speech --mode realtime") -> Settings:
    """Create settings for voice runtime service tests."""
    settings = Settings(_env_file=None)
    settings.voice_runtime_command = command
    settings.voice_runtime_device = "cpu"
    settings.voice_runtime_llm_model = "qwen3"
    settings.ollama_keep_alive = "10m"
    settings.ollama_unload_on_stop = True
    return settings


def test_status_reports_stopped_without_process():
    """Status is stopped before any runtime process starts."""
    service = VoiceRuntimeService(settings=make_settings(), ollama_client=MagicMock())

    assert service.status()["state"] == "stopped"


@pytest.mark.asyncio
async def test_start_launches_configured_command():
    """Start launches the configured runtime command once."""
    settings = make_settings()
    process = MagicMock()
    process.poll.return_value = None

    with patch(
        "backend.services.voice_runtime_service.subprocess.Popen",
        return_value=process,
    ) as popen:
        service = VoiceRuntimeService(settings=settings, ollama_client=AsyncMock())
        result = await service.start()

    assert result["state"] == "running"
    popen.assert_called_once()
    assert popen.call_args.args[0] == ["speech-to-speech", "--mode", "realtime"]


@pytest.mark.asyncio
async def test_start_without_command_returns_config_error():
    """Start returns a clear error when no runtime command is configured."""
    service = VoiceRuntimeService(
        settings=make_settings(command=""), ollama_client=AsyncMock()
    )

    result = await service.start()

    assert result["state"] == "error"
    assert result["error"] == "VOICE_RUNTIME_COMMAND is not configured"


@pytest.mark.asyncio
async def test_stop_terminates_process_and_unloads_model():
    """Stop terminates the runtime process and unloads the configured model."""
    process = MagicMock()
    process.poll.return_value = None
    process.wait.return_value = 0
    ollama = AsyncMock()
    service = VoiceRuntimeService(settings=make_settings(), ollama_client=ollama)
    service._process = process

    result = await service.stop()

    assert result["state"] == "stopped"
    process.terminate.assert_called_once()
    ollama.unload_model.assert_awaited_once_with("qwen3")


@pytest.mark.asyncio
async def test_preload_llm_uses_keep_alive_setting():
    """Preload uses the configured model and keep_alive setting."""
    ollama = AsyncMock()
    ollama.preload_model.return_value = {"done": True}
    service = VoiceRuntimeService(settings=make_settings(), ollama_client=ollama)

    result = await service.preload_llm()

    assert result["state"] == "loaded"
    ollama.preload_model.assert_awaited_once_with("qwen3", keep_alive="10m")
