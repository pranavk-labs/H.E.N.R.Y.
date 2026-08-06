"""HTTP client used by the GTK app."""

from __future__ import annotations

from typing import Any, Optional

import httpx


class RuntimeClient:
    """Small synchronous API client for GTK callbacks."""

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
        """Fetch HENRY's current UI state."""
        return self._get("/conversation/ui/state")

    def get_runtime_status(self) -> dict[str, Any]:
        """Fetch voice runtime status."""
        return self._get("/voice-runtime/status")

    def start_runtime(self) -> dict[str, Any]:
        """Start the configured voice runtime."""
        return self._post("/voice-runtime/start")

    def stop_runtime(self) -> dict[str, Any]:
        """Stop the configured voice runtime."""
        return self._post("/voice-runtime/stop")

    def preload_model(self, model: Optional[str] = None) -> dict[str, Any]:
        """Preload the configured or provided model."""
        return self._post("/voice-runtime/preload", {"model": model})

    def unload_model(self, model: Optional[str] = None) -> dict[str, Any]:
        """Unload the configured or provided model."""
        return self._post("/voice-runtime/unload", {"model": model})

    def go_back(self) -> dict[str, Any]:
        """Navigate back in the current UI stack."""
        return self._post("/conversation/ui/back")
