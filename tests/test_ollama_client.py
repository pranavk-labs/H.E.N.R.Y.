"""Tests for Ollama client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.ollama_client import OllamaClient
from backend.config.settings import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = Settings()
    settings.ollama_base_url = "http://localhost:11434"
    return settings


@pytest.mark.asyncio
async def test_ollama_client_singleton():
    """Test that OllamaClient is a singleton."""
    # Reset instance
    OllamaClient._instance = None
    OllamaClient._client = None

    client1 = OllamaClient.get_instance()
    client2 = OllamaClient.get_instance()
    assert client1 is client2


@pytest.mark.asyncio
async def test_ollama_health_check_success():
    """Test successful health check."""
    # Reset instance
    OllamaClient._instance = None
    OllamaClient._client = None

    with patch("backend.services.ollama_client.httpx") as mock_httpx:
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_httpx.AsyncClient.return_value = mock_client

        client = OllamaClient.get_instance()
        health = await client.health_check()

        assert health["status"] == "healthy"
        assert health["connected"] is True
        mock_client.get.assert_called_once_with("/api/tags", timeout=5.0)


@pytest.mark.asyncio
async def test_ollama_health_check_failure():
    """Test failed health check."""
    # Reset instance
    OllamaClient._instance = None
    OllamaClient._client = None

    with patch("backend.services.ollama_client.httpx") as mock_httpx:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection failed"))
        mock_httpx.AsyncClient.return_value = mock_client

        client = OllamaClient.get_instance()
        health = await client.health_check()

        assert health["status"] == "unhealthy"
        assert health["connected"] is False
        assert "error" in health


@pytest.mark.asyncio
async def test_ollama_preload_model_posts_empty_generate_request(mock_settings):
    """Preloading sends an empty generation request with keep_alive."""
    client = OllamaClient(mock_settings)
    mock_http = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"done": True}
    mock_response.raise_for_status.return_value = None
    mock_http.post.return_value = mock_response
    client._get_client = AsyncMock(return_value=mock_http)

    result = await client.preload_model("qwen3", keep_alive="-1")

    assert result == {"done": True}
    mock_http.post.assert_awaited_once_with(
        "/api/generate",
        json={"model": "qwen3", "prompt": "", "keep_alive": "-1"},
    )


@pytest.mark.asyncio
async def test_ollama_unload_model_posts_keep_alive_zero(mock_settings):
    """Unloading sends an empty generation request with keep_alive=0."""
    client = OllamaClient(mock_settings)
    mock_http = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"done": True}
    mock_response.raise_for_status.return_value = None
    mock_http.post.return_value = mock_response
    client._get_client = AsyncMock(return_value=mock_http)

    result = await client.unload_model("qwen3")

    assert result == {"done": True}
    mock_http.post.assert_awaited_once_with(
        "/api/generate",
        json={"model": "qwen3", "prompt": "", "keep_alive": 0},
    )

