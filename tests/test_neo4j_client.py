"""Tests for Neo4j client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.neo4j_client import Neo4jClient
from backend.config.settings import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = Settings()
    settings.neo4j_uri = "bolt://localhost:7687"
    settings.neo4j_user = "neo4j"
    settings.neo4j_password = "test"
    return settings


@pytest.mark.asyncio
async def test_neo4j_client_singleton():
    """Test that Neo4jClient is a singleton."""
    # Reset instance
    Neo4jClient._instance = None
    Neo4jClient._driver = None

    client1 = Neo4jClient.get_instance()
    client2 = Neo4jClient.get_instance()
    assert client1 is client2


@pytest.mark.asyncio
async def test_neo4j_health_check_unconnected():
    """Test health check when not connected."""
    # Reset instance
    Neo4jClient._instance = None
    Neo4jClient._driver = None

    with patch("backend.services.neo4j_client.AsyncGraphDatabase") as mock_db:
        mock_driver = AsyncMock()
        mock_db.driver.return_value = mock_driver
        mock_driver.verify_connectivity.side_effect = Exception("Connection failed")

        client = Neo4jClient.get_instance()
        health = await client.health_check()

        assert health["status"] == "unhealthy"
        assert health["connected"] is False
        assert "error" in health


@pytest.mark.asyncio
async def test_neo4j_health_check_connected():
    """Test health check when connected."""
    # Reset instance
    Neo4jClient._instance = None
    Neo4jClient._driver = None

    with patch("backend.services.neo4j_client.AsyncGraphDatabase") as mock_db:
        mock_driver = AsyncMock()
        mock_db.driver.return_value = mock_driver
        mock_driver.verify_connectivity = AsyncMock()

        # Mock session as async context manager
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.single = AsyncMock(return_value={"test": 1})
        mock_session.run = AsyncMock(return_value=mock_result)
        
        # Create a proper async context manager mock
        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        mock_driver.session = MagicMock(return_value=mock_session_context)

        client = Neo4jClient.get_instance()
        health = await client.health_check()

        assert health["status"] == "healthy"
        assert health["connected"] is True


