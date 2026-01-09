"""Tests for health check endpoint."""

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "H.E.N.R.Y."
    assert data["version"] == "0.1.0"
    assert data["status"] == "running"


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "neo4j" in data["services"]
    assert "ollama" in data["services"]
    assert "audio" in data["services"]


