"""Tests for GTK main window refresh behavior without loading GTK."""

from __future__ import annotations

from app.gtk_ui.main_window import HenryGtkWindow


class FakeLabel:
    """Small GTK label stand-in."""

    def __init__(self) -> None:
        self.text = ""

    def set_text(self, text: str) -> None:
        self.text = text


class FakeCanvas:
    """Small GTK drawing area stand-in."""

    def __init__(self) -> None:
        self.queued = False

    def queue_draw(self) -> None:
        self.queued = True


class FailingClient:
    """Runtime client stand-in that simulates backend loss."""

    def get_runtime_status(self) -> dict[str, str]:
        raise ConnectionError("connection refused")


class FakeWindow:
    """Minimal HenryGtkWindow shape for exercising refresh()."""

    def __init__(self) -> None:
        self.client = FailingClient()
        self.connection_status_label = FakeLabel()
        self.runtime_status_label = FakeLabel()
        self.view_status_label = FakeLabel()
        self.canvas = FakeCanvas()
        self.runtime = {"state": "running", "model": "qwen3"}
        self.ui_state = {"active_view": "idle", "status_text": "Ready"}
        self.synced_runtime: dict[str, str] | None = None

    def _replace_css_classes(self, *_args) -> None:
        return None

    def _apply_control_state(self, runtime: dict[str, str]) -> None:
        self.control_runtime = runtime

    def _apply_header_state(self, ui_state: dict[str, str]) -> None:
        self.header_ui_state = ui_state

    def _sync_model_entry(self, runtime: dict[str, str]) -> None:
        self.synced_runtime = runtime


def test_refresh_syncs_model_entry_to_offline_runtime_on_backend_loss():
    """Backend loss clears stale synced model text from the GTK model entry."""
    window = FakeWindow()

    assert HenryGtkWindow.refresh(window) is True

    assert window.runtime == {
        "state": "error",
        "error": "Backend unavailable: connection refused",
    }
    assert window.synced_runtime == window.runtime
    assert window.canvas.queued is True
