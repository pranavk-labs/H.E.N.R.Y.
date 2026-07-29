"""Shared pytest configuration for isolated local and CI runs."""

import os

import pytest


os.environ.setdefault("KNOWLEDGE_BACKEND", "fallback")
os.environ.setdefault("GRAPH_FALLBACK_DB", ":memory:")
os.environ.setdefault("SKIP_NEO4J_INTEGRATION", "true")

ENV_KEYS_TO_CLEAR = (
    "VOICE_RUNTIME_COMMAND",
    "VOICE_RUNTIME_DEVICE",
    "VOICE_RUNTIME_LLM_MODEL",
    "VOICE_RUNTIME_AUTO_START",
)

for key in ENV_KEYS_TO_CLEAR:
    os.environ.pop(key, None)


@pytest.fixture(autouse=True)
def isolate_runtime_env():
    """Prevent local .env runtime settings from leaking between tests."""
    for key in ENV_KEYS_TO_CLEAR:
        os.environ.pop(key, None)
    yield
    for key in ENV_KEYS_TO_CLEAR:
        os.environ.pop(key, None)
