"""Tests for knowledge service backend selection."""

from backend.services.knowledge_service import KnowledgeService


def test_knowledge_service_can_force_local_fallback(monkeypatch):
    """KNOWLEDGE_BACKEND=fallback keeps unit tests off live Neo4j."""
    monkeypatch.setenv("KNOWLEDGE_BACKEND", "fallback")

    service = KnowledgeService()

    assert service._use_neo4j is False
