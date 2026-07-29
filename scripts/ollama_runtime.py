#!/usr/bin/env python3
"""Managed Ollama-backed runtime process for HENRY."""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime configuration loaded from environment."""

    ollama_base_url: str
    model: str
    keep_alive: str
    heartbeat_seconds: float


def runtime_config_from_env() -> RuntimeConfig:
    """Build runtime config from environment variables."""
    return RuntimeConfig(
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
        model=(
            os.getenv("VOICE_RUNTIME_LLM_MODEL")
            or os.getenv("OLLAMA_MODEL")
            or "llama3.2:3b"
        ),
        keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "5m"),
        heartbeat_seconds=float(os.getenv("VOICE_RUNTIME_HEARTBEAT_SECONDS", "30")),
    )


def generate_payload(config: RuntimeConfig) -> dict:
    """Return the Ollama request used to keep the model warm."""
    return {
        "model": config.model,
        "prompt": "",
        "stream": False,
        "keep_alive": config.keep_alive,
    }


def preload_model(client: httpx.Client, config: RuntimeConfig) -> None:
    """Load the configured model into Ollama memory."""
    response = client.post("/api/generate", json=generate_payload(config), timeout=120.0)
    response.raise_for_status()


def health_check(client: httpx.Client) -> None:
    """Verify Ollama is reachable."""
    response = client.get("/api/tags", timeout=10.0)
    response.raise_for_status()


def main() -> int:
    """Run until terminated by the voice runtime service."""
    load_dotenv(project_root / ".env.local", override=False)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    config = runtime_config_from_env()
    stop_event = threading.Event()

    def stop(_signum, _frame) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    logger.info("Starting Ollama runtime for model %s", config.model)
    with httpx.Client(base_url=config.ollama_base_url) as client:
        health_check(client)
        preload_model(client, config)
        logger.info("Ollama runtime ready at %s", config.ollama_base_url)

        while not stop_event.wait(config.heartbeat_seconds):
            health_check(client)

    logger.info("Ollama runtime stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
