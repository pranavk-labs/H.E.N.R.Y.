"""Tests for the managed Ollama runtime script."""

from __future__ import annotations

from scripts.ollama_runtime import RuntimeConfig, generate_payload, runtime_config_from_env


def test_runtime_config_prefers_voice_runtime_model(monkeypatch):
    """Runtime model comes from the voice runtime env when configured."""
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.test/")
    monkeypatch.setenv("VOICE_RUNTIME_LLM_MODEL", "qwen3")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "10m")
    monkeypatch.setenv("VOICE_RUNTIME_HEARTBEAT_SECONDS", "5")

    config = runtime_config_from_env()

    assert config.ollama_base_url == "http://ollama.test"
    assert config.model == "qwen3"
    assert config.keep_alive == "10m"
    assert config.heartbeat_seconds == 5.0


def test_generate_payload_keeps_model_warm():
    """Runtime preload uses an empty non-streaming generate request."""
    config = RuntimeConfig(
        ollama_base_url="http://localhost:11434",
        model="llama3.2:3b",
        keep_alive="5m",
        heartbeat_seconds=30,
    )

    assert generate_payload(config) == {
        "model": "llama3.2:3b",
        "prompt": "",
        "stream": False,
        "keep_alive": "5m",
    }
