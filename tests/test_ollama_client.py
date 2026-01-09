"""Tests for Ollama client."""

import pytest
from unittest.mock import AsyncMock, patch

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


