# GTK And Speech Runtime Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a modern GTK entrypoint and server-controlled speech runtime lifecycle while preserving HENRY's existing Ollama tool execution path.

**Architecture:** The backend owns voice runtime lifecycle through a focused service and API route. The GTK app is a new optional client that polls existing state and runtime endpoints. The existing Tkinter app and legacy voice loop stay available.

**Tech Stack:** Python 3.9-3.11, FastAPI, httpx, pytest, optional PyGObject GTK4/libadwaita, Ollama API, system subprocess management.

## Global Constraints

- Keep old Tkinter entrypoints working.
- Do not autostart heavy speech runtime unless explicitly configured.
- Preserve execution through `ToolsService`.
- Use `VOICE_RUNTIME=legacy` as the default.
- Use finite `OLLAMA_KEEP_ALIVE=5m` as the default.
- Use `OLLAMA_UNLOAD_ON_STOP=true` as the default.
- Support `VOICE_RUNTIME_DEVICE=cuda|cpu`.
- Add tests for settings, runtime lifecycle, API routes, and tool-call preservation.

---

## File Structure

- Modify `backend/config/settings.py`: add voice runtime and Ollama lifecycle settings.
- Modify `backend/services/ollama_client.py`: add preload/unload helpers using `keep_alive`.
- Create `backend/services/voice_runtime_service.py`: manage runtime process status, start/stop, preload/unload.
- Create `backend/api/routes/voice_runtime.py`: expose runtime controls to GTK/API clients.
- Modify `backend/api/main.py`: include runtime router.
- Create `tests/test_voice_runtime_service.py`: unit tests for runtime lifecycle with mocked subprocess/Ollama.
- Create `tests/test_voice_runtime_api.py`: route tests with service dependency patching.
- Modify `tests/test_config.py`: verify new defaults/env overrides.
- Modify `app/voice_loop.py`: branch on `VOICE_RUNTIME=hf_s2s` without breaking `legacy`.
- Create `app/gtk_app.py`: GTK app entrypoint with optional dependency checks.
- Create `app/gtk_ui/__init__.py`: GTK UI package exports.
- Create `app/gtk_ui/runtime_client.py`: sync HTTP client for runtime and UI state.
- Create `app/gtk_ui/main_window.py`: GTK/libadwaita window shell and runtime controls.
- Create `scripts/henry_gtk_app.py`: launcher.
- Create `tests/test_gtk_runtime_client.py`: test runtime client request behavior.

---

### Task 1: Runtime Settings And Ollama Lifecycle Helpers

**Files:**
- Modify: `backend/config/settings.py`
- Modify: `backend/services/ollama_client.py`
- Modify: `tests/test_config.py`
- Test: `tests/test_ollama_client.py`

**Interfaces:**
- Produces: `Settings.voice_runtime: str`
- Produces: `Settings.voice_runtime_url: str`
- Produces: `Settings.voice_runtime_command: str`
- Produces: `Settings.voice_runtime_device: str`
- Produces: `Settings.voice_runtime_auto_start: bool`
- Produces: `Settings.voice_runtime_llm_model: str`
- Produces: `Settings.ollama_keep_alive: str`
- Produces: `Settings.ollama_unload_on_stop: bool`
- Produces: `await OllamaClient.preload_model(model: str, keep_alive: str | int = "-1") -> dict`
- Produces: `await OllamaClient.unload_model(model: str) -> dict`

- [ ] **Step 1: Write failing config tests**

Add to `tests/test_config.py`:

```python
def test_voice_runtime_settings_defaults():
    settings = Settings(_env_file=None)

    assert settings.voice_runtime == "legacy"
    assert settings.voice_runtime_url == "ws://127.0.0.1:8765/v1/realtime"
    assert settings.voice_runtime_command == ""
    assert settings.voice_runtime_device == "cuda"
    assert settings.voice_runtime_auto_start is False
    assert settings.voice_runtime_llm_model == ""
    assert settings.ollama_keep_alive == "5m"
    assert settings.ollama_unload_on_stop is True
```

- [ ] **Step 2: Run config test to verify it fails**

Run: `poetry run pytest tests/test_config.py::test_voice_runtime_settings_defaults -v`

Expected: FAIL because `Settings` has no `voice_runtime` attribute.

- [ ] **Step 3: Add settings fields**

Add these fields under the Ollama and audio settings in `backend/config/settings.py`:

```python
    voice_runtime: str = Field(default="legacy", alias="VOICE_RUNTIME")
    voice_runtime_url: str = Field(
        default="ws://127.0.0.1:8765/v1/realtime", alias="VOICE_RUNTIME_URL"
    )
    voice_runtime_command: str = Field(default="", alias="VOICE_RUNTIME_COMMAND")
    voice_runtime_device: str = Field(default="cuda", alias="VOICE_RUNTIME_DEVICE")
    voice_runtime_auto_start: bool = Field(
        default=False, alias="VOICE_RUNTIME_AUTO_START"
    )
    voice_runtime_llm_model: str = Field(
        default="", alias="VOICE_RUNTIME_LLM_MODEL"
    )
    ollama_keep_alive: str = Field(default="5m", alias="OLLAMA_KEEP_ALIVE")
    ollama_unload_on_stop: bool = Field(
        default=True, alias="OLLAMA_UNLOAD_ON_STOP"
    )
```

- [ ] **Step 4: Run config test to verify it passes**

Run: `poetry run pytest tests/test_config.py::test_voice_runtime_settings_defaults -v`

Expected: PASS.

- [ ] **Step 5: Write failing Ollama lifecycle tests**

Add to `tests/test_ollama_client.py`:

```python
@pytest.mark.asyncio
async def test_ollama_preload_model_posts_empty_generate_request(mock_settings):
    client = OllamaClient(mock_settings)
    mock_http = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"done": True}
    mock_http.post.return_value = mock_response
    mock_response.raise_for_status.return_value = None
    client._get_client = AsyncMock(return_value=mock_http)

    result = await client.preload_model("qwen3", keep_alive="-1")

    assert result == {"done": True}
    mock_http.post.assert_awaited_once_with(
        "/api/generate",
        json={"model": "qwen3", "prompt": "", "keep_alive": "-1"},
    )


@pytest.mark.asyncio
async def test_ollama_unload_model_posts_keep_alive_zero(mock_settings):
    client = OllamaClient(mock_settings)
    mock_http = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"done": True}
    mock_http.post.return_value = mock_response
    mock_response.raise_for_status.return_value = None
    client._get_client = AsyncMock(return_value=mock_http)

    result = await client.unload_model("qwen3")

    assert result == {"done": True}
    mock_http.post.assert_awaited_once_with(
        "/api/generate",
        json={"model": "qwen3", "prompt": "", "keep_alive": 0},
    )
```

- [ ] **Step 6: Run Ollama lifecycle tests to verify they fail**

Run: `poetry run pytest tests/test_ollama_client.py::test_ollama_preload_model_posts_empty_generate_request tests/test_ollama_client.py::test_ollama_unload_model_posts_keep_alive_zero -v`

Expected: FAIL because `preload_model` and `unload_model` do not exist.

- [ ] **Step 7: Implement Ollama lifecycle helpers**

Add to `backend/services/ollama_client.py`:

```python
    async def preload_model(self, model: str, keep_alive: str | int = "-1") -> Dict[str, Any]:
        """Load a model into Ollama memory without generating text."""
        client = await self._get_client()
        response = await client.post(
            "/api/generate",
            json={"model": model, "prompt": "", "keep_alive": keep_alive},
        )
        response.raise_for_status()
        return response.json()

    async def unload_model(self, model: str) -> Dict[str, Any]:
        """Unload a model from Ollama memory."""
        client = await self._get_client()
        response = await client.post(
            "/api/generate",
            json={"model": model, "prompt": "", "keep_alive": 0},
        )
        response.raise_for_status()
        return response.json()
```

- [ ] **Step 8: Run task tests**

Run: `poetry run pytest tests/test_config.py tests/test_ollama_client.py -v`

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/config/settings.py backend/services/ollama_client.py tests/test_config.py tests/test_ollama_client.py
git commit -m "feat(voice): add runtime settings and ollama lifecycle controls"
```

---

### Task 2: Voice Runtime Service

**Files:**
- Create: `backend/services/voice_runtime_service.py`
- Create: `tests/test_voice_runtime_service.py`

**Interfaces:**
- Consumes: `Settings.voice_runtime_command`
- Consumes: `Settings.voice_runtime_device`
- Consumes: `Settings.voice_runtime_llm_model`
- Consumes: `Settings.ollama_keep_alive`
- Consumes: `Settings.ollama_unload_on_stop`
- Consumes: `OllamaClient.preload_model(model, keep_alive)`
- Consumes: `OllamaClient.unload_model(model)`
- Produces: `VoiceRuntimeStatus`
- Produces: `VoiceRuntimeService.status() -> dict`
- Produces: `await VoiceRuntimeService.start() -> dict`
- Produces: `await VoiceRuntimeService.stop() -> dict`
- Produces: `await VoiceRuntimeService.preload_llm(model: str | None = None) -> dict`
- Produces: `await VoiceRuntimeService.unload_llm(model: str | None = None) -> dict`

- [ ] **Step 1: Write failing service tests**

Create `tests/test_voice_runtime_service.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.config.settings import Settings
from backend.services.voice_runtime_service import VoiceRuntimeService


def make_settings(command="speech-to-speech --mode realtime"):
    settings = Settings(_env_file=None)
    settings.voice_runtime_command = command
    settings.voice_runtime_device = "cpu"
    settings.voice_runtime_llm_model = "qwen3"
    settings.ollama_keep_alive = "10m"
    settings.ollama_unload_on_stop = True
    return settings


def test_status_reports_stopped_without_process():
    service = VoiceRuntimeService(settings=make_settings(), ollama_client=MagicMock())

    assert service.status()["state"] == "stopped"


@pytest.mark.asyncio
async def test_start_launches_configured_command():
    settings = make_settings()
    process = MagicMock()
    process.poll.return_value = None

    with patch("backend.services.voice_runtime_service.subprocess.Popen", return_value=process) as popen:
        service = VoiceRuntimeService(settings=settings, ollama_client=AsyncMock())
        result = await service.start()

    assert result["state"] == "running"
    popen.assert_called_once()
    assert popen.call_args.args[0] == ["speech-to-speech", "--mode", "realtime"]


@pytest.mark.asyncio
async def test_start_without_command_returns_config_error():
    service = VoiceRuntimeService(settings=make_settings(command=""), ollama_client=AsyncMock())

    result = await service.start()

    assert result["state"] == "error"
    assert result["error"] == "VOICE_RUNTIME_COMMAND is not configured"


@pytest.mark.asyncio
async def test_stop_terminates_process_and_unloads_model():
    process = MagicMock()
    process.poll.return_value = None
    process.wait.return_value = 0
    ollama = AsyncMock()
    service = VoiceRuntimeService(settings=make_settings(), ollama_client=ollama)
    service._process = process

    result = await service.stop()

    assert result["state"] == "stopped"
    process.terminate.assert_called_once()
    ollama.unload_model.assert_awaited_once_with("qwen3")


@pytest.mark.asyncio
async def test_preload_llm_uses_keep_alive_setting():
    ollama = AsyncMock()
    ollama.preload_model.return_value = {"done": True}
    service = VoiceRuntimeService(settings=make_settings(), ollama_client=ollama)

    result = await service.preload_llm()

    assert result["state"] == "loaded"
    ollama.preload_model.assert_awaited_once_with("qwen3", keep_alive="10m")
```

- [ ] **Step 2: Run service tests to verify they fail**

Run: `poetry run pytest tests/test_voice_runtime_service.py -v`

Expected: FAIL because `backend.services.voice_runtime_service` does not exist.

- [ ] **Step 3: Implement service**

Create `backend/services/voice_runtime_service.py` with:

```python
"""Voice runtime lifecycle service."""

from __future__ import annotations

import asyncio
import logging
import shlex
import subprocess
from dataclasses import dataclass
from typing import Any, Optional

from backend.config.settings import Settings, get_settings
from backend.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


@dataclass
class VoiceRuntimeStatus:
    state: str
    pid: Optional[int] = None
    command: str = ""
    device: str = ""
    model: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
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
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _model_name(self, model: Optional[str] = None) -> str:
        return model or self.settings.voice_runtime_llm_model or "llama3.2:3b"

    def _is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def status(self) -> dict[str, Any]:
        state = "running" if self._is_running() else "stopped"
        return VoiceRuntimeStatus(
            state=state,
            pid=self._process.pid if self._is_running() and self._process else None,
            command=self.settings.voice_runtime_command,
            device=self.settings.voice_runtime_device,
            model=self._model_name(),
            error=self._last_error,
        ).to_dict()

    async def start(self) -> dict[str, Any]:
        if self._is_running():
            return self.status()
        if not self.settings.voice_runtime_command.strip():
            self._last_error = "VOICE_RUNTIME_COMMAND is not configured"
            return VoiceRuntimeStatus(
                state="error",
                command="",
                device=self.settings.voice_runtime_device,
                model=self._model_name(),
                error=self._last_error,
            ).to_dict()

        args = shlex.split(self.settings.voice_runtime_command)
        env = None
        try:
            self._process = subprocess.Popen(args, env=env)
            self._last_error = ""
            return self.status()
        except Exception as exc:
            logger.error("Failed to start voice runtime: %s", exc, exc_info=True)
            self._last_error = str(exc)
            return VoiceRuntimeStatus(
                state="error",
                command=self.settings.voice_runtime_command,
                device=self.settings.voice_runtime_device,
                model=self._model_name(),
                error=self._last_error,
            ).to_dict()

    async def stop(self) -> dict[str, Any]:
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

    async def preload_llm(self, model: Optional[str] = None) -> dict[str, Any]:
        model_name = self._model_name(model)
        result = await self.ollama.preload_model(
            model_name, keep_alive=self.settings.ollama_keep_alive
        )
        return {"state": "loaded", "model": model_name, "result": result}

    async def unload_llm(self, model: Optional[str] = None) -> dict[str, Any]:
        model_name = self._model_name(model)
        result = await self.ollama.unload_model(model_name)
        return {"state": "unloaded", "model": model_name, "result": result}


__all__ = ["VoiceRuntimeService", "VoiceRuntimeStatus"]
```

- [ ] **Step 4: Run service tests**

Run: `poetry run pytest tests/test_voice_runtime_service.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/voice_runtime_service.py tests/test_voice_runtime_service.py
git commit -m "feat(voice): add voice runtime lifecycle service"
```

---

### Task 3: Voice Runtime API Routes

**Files:**
- Create: `backend/api/routes/voice_runtime.py`
- Modify: `backend/api/main.py`
- Create: `tests/test_voice_runtime_api.py`

**Interfaces:**
- Consumes: `VoiceRuntimeService.get_instance()`
- Consumes: `VoiceRuntimeService.status()`
- Consumes: `VoiceRuntimeService.start()`
- Consumes: `VoiceRuntimeService.stop()`
- Consumes: `VoiceRuntimeService.preload_llm(model)`
- Consumes: `VoiceRuntimeService.unload_llm(model)`
- Produces: `GET /voice-runtime/status`
- Produces: `POST /voice-runtime/start`
- Produces: `POST /voice-runtime/stop`
- Produces: `POST /voice-runtime/preload`
- Produces: `POST /voice-runtime/unload`

- [ ] **Step 1: Write failing API tests**

Create `tests/test_voice_runtime_api.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from backend.api.main import app


client = TestClient(app)


def test_voice_runtime_status_route():
    service = MagicMock()
    service.status.return_value = {"state": "stopped"}

    with patch("backend.api.routes.voice_runtime.VoiceRuntimeService.get_instance", return_value=service):
        resp = client.get("/voice-runtime/status")

    assert resp.status_code == 200
    assert resp.json()["state"] == "stopped"


def test_voice_runtime_start_route():
    service = MagicMock()
    service.start = AsyncMock(return_value={"state": "running"})

    with patch("backend.api.routes.voice_runtime.VoiceRuntimeService.get_instance", return_value=service):
        resp = client.post("/voice-runtime/start")

    assert resp.status_code == 200
    assert resp.json()["state"] == "running"


def test_voice_runtime_preload_accepts_model_override():
    service = MagicMock()
    service.preload_llm = AsyncMock(return_value={"state": "loaded", "model": "qwen3"})

    with patch("backend.api.routes.voice_runtime.VoiceRuntimeService.get_instance", return_value=service):
        resp = client.post("/voice-runtime/preload", json={"model": "qwen3"})

    assert resp.status_code == 200
    assert resp.json()["model"] == "qwen3"
    service.preload_llm.assert_awaited_once_with("qwen3")
```

- [ ] **Step 2: Run API tests to verify they fail**

Run: `poetry run pytest tests/test_voice_runtime_api.py -v`

Expected: FAIL because route module does not exist or routes are not included.

- [ ] **Step 3: Implement route**

Create `backend/api/routes/voice_runtime.py`:

```python
"""Voice runtime lifecycle API routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.voice_runtime_service import VoiceRuntimeService

router = APIRouter(prefix="/voice-runtime", tags=["voice-runtime"])


class ModelRequest(BaseModel):
    model: Optional[str] = None


@router.get("/status")
async def runtime_status():
    return VoiceRuntimeService.get_instance().status()


@router.post("/start")
async def runtime_start():
    return await VoiceRuntimeService.get_instance().start()


@router.post("/stop")
async def runtime_stop():
    return await VoiceRuntimeService.get_instance().stop()


@router.post("/preload")
async def runtime_preload(payload: ModelRequest):
    return await VoiceRuntimeService.get_instance().preload_llm(payload.model)


@router.post("/unload")
async def runtime_unload(payload: ModelRequest):
    return await VoiceRuntimeService.get_instance().unload_llm(payload.model)
```

- [ ] **Step 4: Include router**

Add to `backend/api/main.py` after the STT router:

```python
from backend.api.routes import voice_runtime as voice_runtime_router

app.include_router(voice_runtime_router.router)
```

- [ ] **Step 5: Run API tests**

Run: `poetry run pytest tests/test_voice_runtime_api.py -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/api/main.py backend/api/routes/voice_runtime.py tests/test_voice_runtime_api.py
git commit -m "feat(api): expose voice runtime controls"
```

---

### Task 4: GTK Runtime Client And App Shell

**Files:**
- Create: `app/gtk_ui/__init__.py`
- Create: `app/gtk_ui/runtime_client.py`
- Create: `app/gtk_ui/main_window.py`
- Create: `app/gtk_app.py`
- Create: `scripts/henry_gtk_app.py`
- Create: `tests/test_gtk_runtime_client.py`

**Interfaces:**
- Consumes: `GET /conversation/ui/state`
- Consumes: `GET /voice-runtime/status`
- Consumes: `POST /voice-runtime/start`
- Consumes: `POST /voice-runtime/stop`
- Consumes: `POST /voice-runtime/preload`
- Consumes: `POST /voice-runtime/unload`
- Produces: `RuntimeClient.get_ui_state() -> dict`
- Produces: `RuntimeClient.get_runtime_status() -> dict`
- Produces: `RuntimeClient.start_runtime() -> dict`
- Produces: `RuntimeClient.stop_runtime() -> dict`
- Produces: `RuntimeClient.preload_model(model: str | None = None) -> dict`
- Produces: `RuntimeClient.unload_model(model: str | None = None) -> dict`
- Produces: `run_gtk_app(api_base_url: str | None = None) -> int`

- [ ] **Step 1: Write failing runtime client tests**

Create `tests/test_gtk_runtime_client.py`:

```python
from unittest.mock import MagicMock

from app.gtk_ui.runtime_client import RuntimeClient


def test_runtime_client_fetches_status():
    http = MagicMock()
    response = MagicMock()
    response.json.return_value = {"state": "stopped"}
    response.raise_for_status.return_value = None
    http.get.return_value = response
    client = RuntimeClient(api_base_url="http://testserver", http_client=http)

    assert client.get_runtime_status() == {"state": "stopped"}
    http.get.assert_called_once_with("http://testserver/voice-runtime/status")


def test_runtime_client_posts_preload_model():
    http = MagicMock()
    response = MagicMock()
    response.json.return_value = {"state": "loaded", "model": "qwen3"}
    response.raise_for_status.return_value = None
    http.post.return_value = response
    client = RuntimeClient(api_base_url="http://testserver", http_client=http)

    assert client.preload_model("qwen3")["state"] == "loaded"
    http.post.assert_called_once_with(
        "http://testserver/voice-runtime/preload", json={"model": "qwen3"}
    )
```

- [ ] **Step 2: Run client tests to verify they fail**

Run: `poetry run pytest tests/test_gtk_runtime_client.py -v`

Expected: FAIL because `app.gtk_ui.runtime_client` does not exist.

- [ ] **Step 3: Implement runtime client**

Create `app/gtk_ui/__init__.py`:

```python
"""GTK UI package for HENRY."""
```

Create `app/gtk_ui/runtime_client.py`:

```python
"""HTTP client used by the GTK app."""

from __future__ import annotations

from typing import Any, Optional

import httpx


class RuntimeClient:
    def __init__(
        self,
        api_base_url: str,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.http = http_client or httpx.Client(timeout=5.0)

    def _get(self, path: str) -> dict[str, Any]:
        response = self.http.get(f"{self.api_base_url}{path}")
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        response = self.http.post(f"{self.api_base_url}{path}", json=payload or {})
        response.raise_for_status()
        return response.json()

    def get_ui_state(self) -> dict[str, Any]:
        return self._get("/conversation/ui/state")

    def get_runtime_status(self) -> dict[str, Any]:
        return self._get("/voice-runtime/status")

    def start_runtime(self) -> dict[str, Any]:
        return self._post("/voice-runtime/start")

    def stop_runtime(self) -> dict[str, Any]:
        return self._post("/voice-runtime/stop")

    def preload_model(self, model: Optional[str] = None) -> dict[str, Any]:
        return self._post("/voice-runtime/preload", {"model": model})

    def unload_model(self, model: Optional[str] = None) -> dict[str, Any]:
        return self._post("/voice-runtime/unload", {"model": model})
```

- [ ] **Step 4: Run client tests**

Run: `poetry run pytest tests/test_gtk_runtime_client.py -v`

Expected: PASS.

- [ ] **Step 5: Implement GTK shell with optional import guard**

Create `app/gtk_ui/main_window.py`:

```python
"""GTK/libadwaita main window."""

from __future__ import annotations

import logging
from typing import Optional

from app.gtk_ui.runtime_client import RuntimeClient

logger = logging.getLogger(__name__)


def require_gtk():
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw, GLib, Gtk
        return Adw, GLib, Gtk
    except Exception as exc:
        raise RuntimeError(
            "GTK4/libadwaita is not available. Install PyGObject, GTK4, and libadwaita."
        ) from exc


class HenryGtkWindow:
    def __init__(self, app, client: RuntimeClient) -> None:
        Adw, GLib, Gtk = require_gtk()
        self.Adw = Adw
        self.GLib = GLib
        self.Gtk = Gtk
        self.client = client
        self.window = Adw.ApplicationWindow(application=app)
        self.window.set_title("H.E.N.R.Y.")
        self.window.set_default_size(1024, 600)
        self.status_label = Gtk.Label(label="Voice runtime: unknown")
        self.transcript_label = Gtk.Label(label="")
        self._build()
        self.refresh()
        GLib.timeout_add_seconds(2, self.refresh)

    def _build(self) -> None:
        Gtk = self.Gtk
        Adw = self.Adw

        toolbar = Adw.HeaderBar()
        title = Adw.WindowTitle(title="H.E.N.R.Y.", subtitle="Desk assistant")
        toolbar.set_title_widget(title)

        start_button = Gtk.Button(label="Start")
        start_button.connect("clicked", lambda _button: self._run_action(self.client.start_runtime))
        stop_button = Gtk.Button(label="Stop")
        stop_button.connect("clicked", lambda _button: self._run_action(self.client.stop_runtime))
        preload_button = Gtk.Button(label="Preload")
        preload_button.connect("clicked", lambda _button: self._run_action(self.client.preload_model))
        unload_button = Gtk.Button(label="Unload")
        unload_button.connect("clicked", lambda _button: self._run_action(self.client.unload_model))

        toolbar.pack_start(start_button)
        toolbar.pack_start(stop_button)
        toolbar.pack_end(unload_button)
        toolbar.pack_end(preload_button)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(toolbar)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        body.set_margin_top(16)
        body.set_margin_bottom(16)
        body.set_margin_start(16)
        body.set_margin_end(16)

        nav = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for label in ["Face", "Timer", "Todos", "Ideas", "Calendar"]:
            nav.append(Gtk.Button(label=label))

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        face = Gtk.Label(label="H.E.N.R.Y.")
        face.add_css_class("title-1")
        center.append(face)
        center.append(self.status_label)
        center.append(self.transcript_label)

        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        panel.append(Gtk.Label(label="Runtime"))
        panel.append(Gtk.Label(label="Controls are in the header bar."))

        body.append(nav)
        body.append(center)
        body.append(panel)
        root.append(body)
        self.window.set_content(root)

    def _run_action(self, action) -> None:
        try:
            action()
            self.refresh()
        except Exception as exc:
            self.status_label.set_text(f"Voice runtime error: {exc}")

    def refresh(self) -> bool:
        try:
            runtime = self.client.get_runtime_status()
            ui_state = self.client.get_ui_state()
            self.status_label.set_text(f"Voice runtime: {runtime.get('state', 'unknown')}")
            self.transcript_label.set_text(str(ui_state.get("status_text", "")))
        except Exception as exc:
            self.status_label.set_text(f"Backend unavailable: {exc}")
        return True

    def present(self) -> None:
        self.window.present()
```

Create `app/gtk_app.py`:

```python
"""GTK entrypoint for HENRY."""

from __future__ import annotations

import os
from typing import Optional

from app.gtk_ui.main_window import HenryGtkWindow, require_gtk
from app.gtk_ui.runtime_client import RuntimeClient


def run_gtk_app(api_base_url: Optional[str] = None) -> int:
    Adw, _GLib, _Gtk = require_gtk()
    base_url = api_base_url or os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    app = Adw.Application(application_id="dev.henry.Assistant")

    def on_activate(application):
        window = HenryGtkWindow(application, RuntimeClient(base_url))
        window.present()

    app.connect("activate", on_activate)
    return app.run(None)
```

Create `scripts/henry_gtk_app.py`:

```python
#!/usr/bin/env python
"""Launch the GTK HENRY app."""

from app.gtk_app import run_gtk_app


if __name__ == "__main__":
    raise SystemExit(run_gtk_app())
```

- [ ] **Step 6: Run GTK client tests**

Run: `poetry run pytest tests/test_gtk_runtime_client.py -v`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/gtk_app.py app/gtk_ui scripts/henry_gtk_app.py tests/test_gtk_runtime_client.py
git commit -m "feat(ui): add gtk app shell with runtime controls"
```

---

### Task 5: Voice Runtime Mode Wiring

**Files:**
- Modify: `app/voice_loop.py`
- Test: `tests/test_voice_integration.py`

**Interfaces:**
- Consumes: `Settings.voice_runtime`
- Consumes: `Settings.voice_runtime_url`
- Produces: `VoiceLoop.runtime_mode`
- Preserves: legacy `_get_user_input()` behavior when `VOICE_RUNTIME=legacy`

- [ ] **Step 1: Add failing test for default legacy mode**

Add to `tests/test_voice_integration.py`:

```python
def test_voice_loop_defaults_to_legacy_runtime(mock_voice_settings):
    from app.voice_loop import VoiceLoop

    mock_voice_settings.voice_runtime = "legacy"
    loop = VoiceLoop(api_base_url="http://127.0.0.1:8000")

    assert loop.runtime_mode == "legacy"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/test_voice_integration.py::test_voice_loop_defaults_to_legacy_runtime -v`

Expected: FAIL because `VoiceLoop.runtime_mode` does not exist.

- [ ] **Step 3: Add runtime mode field**

In `app/voice_loop.py`, inside `VoiceLoop.__init__` after `self.settings = get_settings()`:

```python
        self.runtime_mode = getattr(self.settings, "voice_runtime", "legacy")
        self.voice_runtime_url = getattr(
            self.settings, "voice_runtime_url", "ws://127.0.0.1:8765/v1/realtime"
        )
```

- [ ] **Step 4: Preserve legacy branch explicitly**

In `VoiceLoop.start`, keep existing behavior for `legacy`. If a future `hf_s2s` branch is requested before implementation, update status and fall back:

```python
        if self.runtime_mode == "hf_s2s":
            logger.warning("hf_s2s runtime mode is configured but adapter is not active; using legacy voice loop")
```

- [ ] **Step 5: Run voice integration test**

Run: `poetry run pytest tests/test_voice_integration.py::test_voice_loop_defaults_to_legacy_runtime -v`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/voice_loop.py tests/test_voice_integration.py
git commit -m "feat(voice): add selectable voice runtime mode"
```

---

### Task 6: Verification And Documentation Update

**Files:**
- Modify: `README.md`
- Modify: `docs/development-guide.md`

**Interfaces:**
- Documents: `scripts/henry_gtk_app.py`
- Documents: `/voice-runtime/*`
- Documents: `VOICE_RUNTIME_*` settings

- [ ] **Step 1: Add concise README section**

Add under the desktop/Pi usage area:

```markdown
### GTK App

The GTK app is the new desktop UI path. It keeps the older Tkinter app available while the refresh stabilizes.

Run backend:

```bash
poetry run python scripts/dev_server.py
```

Run GTK app:

```bash
API_BASE_URL=http://127.0.0.1:8000 poetry run python scripts/henry_gtk_app.py
```
```

- [ ] **Step 2: Add runtime controls docs**

Add to `docs/development-guide.md`:

```markdown
## Voice Runtime Controls

The backend exposes model/runtime controls:

- `GET /voice-runtime/status`
- `POST /voice-runtime/start`
- `POST /voice-runtime/stop`
- `POST /voice-runtime/preload`
- `POST /voice-runtime/unload`

Default mode is `VOICE_RUNTIME=legacy`.

Heavy runtime startup requires `VOICE_RUNTIME_COMMAND`; it is not started automatically unless `VOICE_RUNTIME_AUTO_START=true`.
```

- [ ] **Step 3: Run targeted tests**

Run:

```bash
poetry run pytest \
  tests/test_config.py \
  tests/test_ollama_client.py \
  tests/test_voice_runtime_service.py \
  tests/test_voice_runtime_api.py \
  tests/test_gtk_runtime_client.py \
  tests/test_voice_integration.py::test_voice_loop_defaults_to_legacy_runtime \
  -v
```

Expected: PASS.

- [ ] **Step 4: Run broader verification**

Run:

```bash
poetry run pytest -q
poetry run mypy backend app tools
poetry run flake8 backend app tools tests
```

Expected: pytest PASS. If mypy or flake8 reveal existing unrelated issues, capture exact failures in final report and do not claim they pass.

- [ ] **Step 5: Commit docs**

```bash
git add README.md docs/development-guide.md
git commit -m "docs: document gtk app and voice runtime controls"
```
