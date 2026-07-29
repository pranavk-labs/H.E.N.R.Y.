"""Voice runtime lifecycle service."""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, Optional

from backend.config.settings import Settings, get_settings
from backend.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


@dataclass
class VoiceRuntimeStatus:
    """Serializable voice runtime status."""

    state: str
    pid: Optional[int] = None
    command: str = ""
    device: str = ""
    model: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return status as an API-friendly dictionary."""
        return {
            "state": self.state,
            "pid": self.pid,
            "command": self.command,
            "device": self.device,
            "model": self.model,
            "error": self.error,
        }


class VoiceRuntimeService:
    """Manage the optional server-side speech runtime process."""

    _instance: Optional["VoiceRuntimeService"] = None

    def __init__(
        self,
        settings: Optional[Settings] = None,
        ollama_client: Optional[OllamaClient] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.ollama = ollama_client or OllamaClient.get_instance()
        self._process: Optional[subprocess.Popen] = None
        self._last_error = ""

    @classmethod
    def get_instance(cls) -> "VoiceRuntimeService":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _model_name(self, model: Optional[str] = None) -> str:
        return (
            model
            or self.settings.voice_runtime_llm_model
            or os.getenv("OLLAMA_MODEL")
            or "llama3.2:3b"
        )

    def _is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def status(self) -> Dict[str, Any]:
        """Return current runtime status."""
        state = "running" if self._is_running() else "stopped"
        return VoiceRuntimeStatus(
            state=state,
            pid=self._process.pid if self._is_running() and self._process else None,
            command=self.settings.voice_runtime_command,
            device=self.settings.voice_runtime_device,
            model=self._model_name(),
            error=self._last_error,
        ).to_dict()

    async def start(self) -> Dict[str, Any]:
        """Start the configured speech runtime process."""
        if self._is_running():
            return self.status()

        command = self.settings.voice_runtime_command.strip()
        if not command:
            self._last_error = "VOICE_RUNTIME_COMMAND is not configured"
            return VoiceRuntimeStatus(
                state="error",
                command=command,
                device=self.settings.voice_runtime_device,
                model=self._model_name(),
                error=self._last_error,
            ).to_dict()

        env = os.environ.copy()
        env["VOICE_RUNTIME_DEVICE"] = self.settings.voice_runtime_device

        try:
            self._process = subprocess.Popen(shlex.split(command), env=env)
            self._last_error = ""
            return self.status()
        except Exception as exc:
            logger.error("Failed to start voice runtime: %s", exc, exc_info=True)
            self._last_error = str(exc)
            return VoiceRuntimeStatus(
                state="error",
                command=command,
                device=self.settings.voice_runtime_device,
                model=self._model_name(),
                error=self._last_error,
            ).to_dict()

    async def stop(self) -> Dict[str, Any]:
        """Stop the runtime process and optionally unload the Ollama model."""
        if self._is_running() and self._process is not None:
            self._process.terminate()
            try:
                await asyncio.to_thread(self._process.wait, timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
                await asyncio.to_thread(self._process.wait, timeout=5)

        self._process = None

        if self.settings.ollama_unload_on_stop:
            await self.unload_llm()

        self._last_error = ""
        return self.status()

    async def preload_llm(self, model: Optional[str] = None) -> Dict[str, Any]:
        """Preload the configured LLM into Ollama memory."""
        model_name = self._model_name(model)
        result = await self.ollama.preload_model(
            model_name, keep_alive=self.settings.ollama_keep_alive
        )
        return {"state": "loaded", "model": model_name, "result": result}

    async def unload_llm(self, model: Optional[str] = None) -> Dict[str, Any]:
        """Unload the configured LLM from Ollama memory."""
        model_name = self._model_name(model)
        result = await self.ollama.unload_model(model_name)
        return {"state": "unloaded", "model": model_name, "result": result}


__all__ = ["VoiceRuntimeService", "VoiceRuntimeStatus"]
