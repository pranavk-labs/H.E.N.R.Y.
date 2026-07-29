"""Tests for voice runtime API routes."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_voice_runtime_status_route():
    """Status route returns service status."""
    service = MagicMock()
    service.status.return_value = {"state": "stopped"}

    with patch(
        "backend.api.routes.voice_runtime.VoiceRuntimeService.get_instance",
        return_value=service,
    ):
        resp = client.get("/voice-runtime/status")

    assert resp.status_code == 200
    assert resp.json()["state"] == "stopped"


def test_voice_runtime_start_route():
    """Start route returns service start result."""
    service = MagicMock()
    service.start = AsyncMock(return_value={"state": "running"})

    with patch(
        "backend.api.routes.voice_runtime.VoiceRuntimeService.get_instance",
        return_value=service,
    ):
        resp = client.post("/voice-runtime/start")

    assert resp.status_code == 200
    assert resp.json()["state"] == "running"


def test_voice_runtime_preload_accepts_model_override():
    """Preload route passes optional model override to the service."""
    service = MagicMock()
    service.preload_llm = AsyncMock(return_value={"state": "loaded", "model": "qwen3"})

    with patch(
        "backend.api.routes.voice_runtime.VoiceRuntimeService.get_instance",
        return_value=service,
    ):
        resp = client.post("/voice-runtime/preload", json={"model": "qwen3"})

    assert resp.status_code == 200
    assert resp.json()["model"] == "qwen3"
    service.preload_llm.assert_awaited_once_with("qwen3")
