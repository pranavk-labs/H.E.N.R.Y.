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


class ActionFailureWindow:
    """Minimal HenryGtkWindow shape for exercising action failure handling."""

    def __init__(self) -> None:
        self.action_status_label = FakeLabel()
        self.css_class = ""
        self.refresh_called = False

    def _replace_css_classes(self, _widget, _classes, active_class: str) -> None:
        self.css_class = active_class

    def refresh(self) -> bool:
        self.refresh_called = True
        return True


class DrawBranchWindow:
    """Minimal HenryGtkWindow shape for exercising draw branch selection."""

    def __init__(self, active_view: str) -> None:
        self.ui_state = {"active_view": active_view, "status_text": ""}
        self.runtime = {"state": "running"}
        self.face_calls = 0
        self.adaptive_calls = 0

    def _paint_background(self, *_args) -> None:
        return None

    def _draw_status_badges(self, *_args) -> None:
        return None

    def _draw_face(self, *_args) -> None:
        self.face_calls += 1

    def _draw_adaptive_view(self, *_args) -> None:
        self.adaptive_calls += 1

    def _draw_detail_lines(self, *_args) -> None:
        return None


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


def test_state_key_tracks_runtime_error_detail_changes():
    """Runtime error reason changes should count as GTK state changes."""
    ui_state = {"active_view": "idle", "status_text": "Waiting"}

    first_key = HenryGtkWindow._state_key(
        object(),
        {"state": "error", "model": "qwen3", "error": "microphone unavailable"},
        ui_state,
    )
    second_key = HenryGtkWindow._state_key(
        object(),
        {"state": "error", "model": "qwen3", "error": "ollama unavailable"},
        ui_state,
    )

    assert first_key != second_key


def test_run_action_refreshes_after_action_exception():
    """Failed GTK actions should refresh visible runtime/backend state."""
    window = ActionFailureWindow()

    HenryGtkWindow._run_action(
        window,
        "start",
        lambda: (_ for _ in ()).throw(ConnectionError("backend unavailable")),
    )

    assert window.action_status_label.text == "Start: Backend offline"
    assert window.css_class == "status-error"
    assert window.refresh_called is True


def test_draw_treats_blank_active_view_as_idle_face():
    """Blank GTK active views should draw the idle face, not an empty adaptive panel."""
    window = DrawBranchWindow("   ")

    HenryGtkWindow._draw(window, None, object(), 800, 500)

    assert window.face_calls == 1
    assert window.adaptive_calls == 0
