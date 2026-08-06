"""Tests for GTK main window refresh behavior without loading GTK."""

from __future__ import annotations

from app.gtk_ui import face_view, main_window
from app.gtk_ui.main_window import HenryGtkWindow


class FakeLabel:
    """Small GTK label stand-in."""

    def __init__(self) -> None:
        self.text = ""
        self.tooltip_text = ""
        self.css_classes: list[str] = []

    def set_text(self, text: str) -> None:
        self.text = text

    def set_tooltip_text(self, text: str) -> None:
        self.tooltip_text = text

    def add_css_class(self, css_class: str) -> None:
        if css_class not in self.css_classes:
            self.css_classes.append(css_class)

    def remove_css_class(self, css_class: str) -> None:
        if css_class in self.css_classes:
            self.css_classes.remove(css_class)


class FakeCanvas:
    """Small GTK drawing area stand-in."""

    def __init__(self) -> None:
        self.queued = False

    def queue_draw(self) -> None:
        self.queued = True


class FakeButton:
    """Small GTK button stand-in."""

    def __init__(self) -> None:
        self.sensitive: bool | None = None
        self.tooltip_text = ""

    def set_sensitive(self, sensitive: bool) -> None:
        self.sensitive = sensitive

    def set_tooltip_text(self, text: str) -> None:
        self.tooltip_text = text


class FakeEntry:
    """Small GTK entry stand-in."""

    def __init__(self, text: str = "") -> None:
        self.text = text
        self.tooltip_text = ""
        self.css_classes: list[str] = []

    def get_text(self) -> str:
        return self.text

    def set_text(self, text: str) -> None:
        self.text = text

    def set_tooltip_text(self, text: str) -> None:
        self.tooltip_text = text

    def add_css_class(self, css_class: str) -> None:
        if css_class not in self.css_classes:
            self.css_classes.append(css_class)

    def remove_css_class(self, css_class: str) -> None:
        if css_class in self.css_classes:
            self.css_classes.remove(css_class)


class FailingClient:
    """Runtime client stand-in that simulates backend loss."""

    def get_runtime_status(self) -> dict[str, str]:
        raise ConnectionError("connection refused")


class HealthyClient:
    """Runtime client stand-in that returns connected GTK header state."""

    def __init__(self, model: str = "qwen3") -> None:
        self.model = model

    def get_runtime_status(self) -> dict[str, str]:
        return {"state": "running", "model": self.model}

    def get_ui_state(self) -> dict[str, str]:
        return {"active_view": "idle", "status_text": "Ready"}


class FakeWindow:
    """Minimal HenryGtkWindow shape for exercising refresh()."""

    def __init__(self) -> None:
        self.client = FailingClient()
        self.connection_status_label = FakeLabel()
        self.runtime_status_label = FakeLabel()
        self.view_status_label = FakeLabel()
        self.action_status_label = FakeLabel()
        self.canvas = FakeCanvas()
        self.runtime = {"state": "running", "model": "qwen3"}
        self.ui_state = {"active_view": "idle", "status_text": "Ready"}
        self._last_state_key = None
        self._last_interaction_time = 0.0
        self.synced_runtime: dict[str, str] | None = None

    def _replace_css_classes(self, widget, classes, active_class: str) -> None:
        for css_class in classes:
            widget.remove_css_class(css_class)
        widget.add_css_class(active_class)

    def _clear_css_classes(self, widget, classes) -> None:
        for css_class in classes:
            widget.remove_css_class(css_class)

    def _state_key(self, runtime, ui_state):
        return HenryGtkWindow._state_key(self, runtime, ui_state)

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
        self._model_entry_user_edited = False

    def _replace_css_classes(self, _widget, _classes, active_class: str) -> None:
        self.css_class = active_class

    def refresh(self) -> bool:
        self.refresh_called = True
        return True


class HeaderStateWindow:
    """Minimal HenryGtkWindow shape for exercising header state updates."""

    def __init__(self) -> None:
        self.active_states_label = FakeLabel()
        self._buttons = {"back": FakeButton()}

    def _replace_css_classes(self, widget, classes, active_class: str) -> None:
        for css_class in classes:
            widget.remove_css_class(css_class)
        widget.add_css_class(active_class)


class ControlStateWindow:
    """Minimal HenryGtkWindow shape for exercising runtime control updates."""

    def __init__(self) -> None:
        self._buttons = {
            "back": FakeButton(),
            "start": FakeButton(),
            "stop": FakeButton(),
            "preload": FakeButton(),
            "unload": FakeButton(),
        }


class ModelEntryWindow:
    """Minimal HenryGtkWindow shape for exercising model entry state."""

    def __init__(self, text: str = "") -> None:
        self.model_entry = FakeEntry(text)
        self._model_entry_user_edited = False
        self._syncing_model_entry = False

    def _clear_css_classes(self, widget, classes) -> None:
        for css_class in classes:
            widget.remove_css_class(css_class)

    def _apply_model_entry_state(self) -> None:
        HenryGtkWindow._apply_model_entry_state(self)


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


def test_gtk_timing_seconds_uses_configured_positive_value(monkeypatch):
    """GTK face timing env values should accept positive second counts."""
    monkeypatch.setenv("GUI_HAPPY_DURATION", "45")

    assert main_window.gtk_timing_seconds("GUI_HAPPY_DURATION", 120) == 45


def test_gtk_timing_seconds_falls_back_for_malformed_values(monkeypatch):
    """Malformed GTK face timing env values should not prevent startup."""
    monkeypatch.setenv("GUI_HAPPY_DURATION", "   ")
    monkeypatch.setenv("GUI_NEUTRAL_DURATION", "slow")
    monkeypatch.setenv("GUI_SLEEPY_DURATION", "-5")

    assert main_window.gtk_timing_seconds("GUI_HAPPY_DURATION", 120) == 120
    assert main_window.gtk_timing_seconds("GUI_NEUTRAL_DURATION", 300) == 300
    assert main_window.gtk_timing_seconds("GUI_SLEEPY_DURATION", 600) == 600


def test_refresh_syncs_model_entry_to_offline_runtime_on_backend_loss():
    """Backend loss clears stale synced model text from the GTK model entry."""
    window = FakeWindow()

    assert HenryGtkWindow.refresh(window) is True

    assert window.runtime == {
        "state": "error",
        "error": "Backend unavailable: connection refused",
    }
    assert window.runtime_status_label.text == "Runtime: Offline"
    assert (
        window.runtime_status_label.tooltip_text
        == "Runtime: Offline - Backend unavailable: connection refused"
    )
    assert window.connection_status_label.tooltip_text == (
        "Backend: unavailable - connection refused"
    )
    assert window.synced_runtime == window.runtime
    assert window.canvas.queued is True


def test_refresh_clears_stale_action_status_on_backend_loss():
    """Backend loss should not leave stale action feedback in the GTK header."""
    window = FakeWindow()
    window.action_status_label.set_text("Start: Running qwen3")
    window.action_status_label.set_tooltip_text("Start: Running qwen3")

    assert HenryGtkWindow.refresh(window) is True

    assert window.action_status_label.text == ""
    assert window.action_status_label.tooltip_text == ""


def test_refresh_clears_stale_action_status_class_on_backend_loss():
    """Backend loss should remove stale action badge styling from the header."""
    window = FakeWindow()
    window.action_status_label.add_css_class("status-ok")

    assert HenryGtkWindow.refresh(window) is True

    assert not set(window.action_status_label.css_classes).intersection(main_window.STATUS_CLASSES)


def test_refresh_sets_status_label_tooltips_to_visible_text():
    """Compact GTK header statuses should expose their full text on hover."""
    window = FakeWindow()
    window.client = HealthyClient()

    assert HenryGtkWindow.refresh(window) is True

    assert window.connection_status_label.tooltip_text == "Backend: connected"
    assert window.view_status_label.tooltip_text == "Listening"
    assert window.runtime_status_label.tooltip_text == "Runtime: Running - qwen3"


def test_refresh_runtime_tooltip_keeps_full_model_name():
    """Runtime status hover text should show full model names when labels clip them."""
    window = FakeWindow()
    window.client = HealthyClient("qwen3-extra-long-model-name")

    assert HenryGtkWindow.refresh(window) is True

    assert window.runtime_status_label.text == "Runtime: Running - qwen3-extra-lon..."
    assert (
        window.runtime_status_label.tooltip_text == "Runtime: Running - qwen3-extra-long-model-name"
    )


def test_apply_header_state_sets_active_states_tooltip():
    """Compact active-state labels should expose their full text on hover."""
    window = HeaderStateWindow()

    HenryGtkWindow._apply_header_state(
        window,
        {
            "active_view": "idle",
            "active_states": ["timer", "idea", "calendar", "todo"],
            "view_stack": ["idle", "calendar"],
        },
    )

    assert window.active_states_label.text == "Active: Timer, Idea, Calendar +1"
    assert window.active_states_label.tooltip_text == "Active: Timer, Idea, Calendar, Todo"
    assert window._buttons["back"].sensitive is True


def test_apply_header_state_clears_active_states_tooltip_when_empty():
    """Stale active-state tooltips should clear when no states are visible."""
    window = HeaderStateWindow()
    window.active_states_label.set_text("Active: timer")
    window.active_states_label.set_tooltip_text("Active: timer")

    HenryGtkWindow._apply_header_state(
        window,
        {"active_view": "idle", "active_states": [], "view_stack": ["idle"]},
    )

    assert window.active_states_label.text == ""
    assert window.active_states_label.tooltip_text == ""
    assert window._buttons["back"].sensitive is False


def test_apply_control_state_explains_disabled_runtime_controls():
    """Disabled GTK runtime controls should explain why the action is unavailable."""
    window = ControlStateWindow()

    HenryGtkWindow._apply_control_state(
        window,
        face_view.offline_runtime_state(ConnectionError("connection refused")),
    )

    assert window._buttons["start"].sensitive is False
    assert window._buttons["preload"].sensitive is False
    assert window._buttons["start"].tooltip_text == (
        "Start voice runtime unavailable: backend offline"
    )
    assert window._buttons["preload"].tooltip_text == "Preload model unavailable: backend offline"

    HenryGtkWindow._apply_control_state(window, {"state": "loading"})

    assert window._buttons["start"].tooltip_text == (
        "Start voice runtime unavailable: runtime is loading"
    )
    assert window._buttons["stop"].tooltip_text == (
        "Stop voice runtime unavailable: runtime is loading"
    )

    HenryGtkWindow._apply_control_state(window, {"state": "running"})

    assert window._buttons["start"].tooltip_text == (
        "Start voice runtime unavailable: runtime is already running"
    )
    assert window._buttons["stop"].tooltip_text == "Stop voice runtime (Ctrl+.)"


def test_model_entry_change_marks_active_override_state():
    """Typed GTK model overrides should be visually and textually inspectable."""
    window = ModelEntryWindow("custom-model")

    HenryGtkWindow._on_model_entry_changed(window, None)

    assert window._model_entry_user_edited is True
    assert window.model_entry.tooltip_text == "Model override active: custom-model"
    assert "model-entry-override" in window.model_entry.css_classes


def test_sync_model_entry_clears_stale_override_state():
    """Runtime model sync should clear stale override entry styling."""
    window = ModelEntryWindow("custom-model")
    window._model_entry_user_edited = False
    window.model_entry.set_tooltip_text("Model override active: custom-model")
    window.model_entry.add_css_class("model-entry-override")

    HenryGtkWindow._sync_model_entry(window, {"model": "qwen3"})

    assert window.model_entry.get_text() == "qwen3"
    assert window.model_entry.tooltip_text == "Model override for preload and unload"
    assert "model-entry-override" not in window.model_entry.css_classes


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


def test_state_key_normalizes_rendered_runtime_error_text():
    """Equivalent GTK runtime error labels should not reset face timing."""
    ui_state = {"active_view": "idle", "status_text": "Waiting"}

    first_key = HenryGtkWindow._state_key(
        object(),
        {"state": "error", "model": "qwen3", "error": "microphone unavailable"},
        ui_state,
    )
    second_key = HenryGtkWindow._state_key(
        object(),
        {"state": "error", "model": "qwen3", "error": " microphone unavailable "},
        ui_state,
    )

    assert first_key == second_key


def test_state_key_normalizes_rendered_active_view_names():
    """Equivalent GTK active view names should not reset face timing."""
    runtime = {"state": "running", "model": "qwen3"}

    first_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {"active_view": "idle", "status_text": "Waiting"},
    )
    second_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {"active_view": " idle ", "status_text": "Waiting"},
    )
    third_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {"active_view": " IDLE ", "status_text": "Waiting"},
    )

    assert first_key == second_key
    assert first_key == third_key


def test_state_key_normalizes_rendered_status_text():
    """Equivalent GTK status text should not reset face timing."""
    runtime = {"state": "running", "model": "qwen3"}

    first_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {"active_view": "idle", "status_text": "Ready"},
    )
    second_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {"active_view": "idle", "status_text": " Ready "},
    )

    assert first_key == second_key


def test_state_key_normalizes_rendered_tool_detail_fields():
    """Equivalent GTK tool detail labels should not reset face timing."""
    runtime = {"state": "running", "model": "qwen3"}

    first_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {
            "active_view": "todo_list",
            "status_text": "3 tasks",
            "active_todo_id": "todo:polish_gtk",
            "active_todo_title": "Polish GTK",
            "todo_filter_status": "in_progress",
            "selected_category_id": "category:ui",
            "calendar_view_mode": "week",
            "calendar_selected_date": "2026-08-06T12:00:00",
            "calendar_filter_type": "meeting",
            "active_event_id": "event:demo",
        },
    )
    second_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {
            "active_view": "todo_list",
            "status_text": "3 tasks",
            "active_todo_id": " todo:polish_gtk ",
            "active_todo_title": " Polish GTK ",
            "todo_filter_status": " in_progress ",
            "selected_category_id": " category:ui ",
            "calendar_view_mode": " week ",
            "calendar_selected_date": " 2026-08-06T12:00:00 ",
            "calendar_filter_type": " meeting ",
            "active_event_id": " event:demo ",
        },
    )

    assert first_key == second_key


def test_state_key_ignores_unrendered_todo_identifiers_when_title_is_visible():
    """Hidden todo identifiers should not reset GTK face timing."""
    runtime = {"state": "running", "model": "qwen3"}

    first_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {
            "active_view": "todo_list",
            "status_text": "3 tasks",
            "active_todo_id": "todo:polish_gtk",
            "active_todo_title": "Polish GTK",
            "todo_filter_status": "in_progress",
            "selected_category_id": "category:ui",
        },
    )
    second_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {
            "active_view": "todo_list",
            "status_text": "3 tasks",
            "active_todo_id": "todo:backend_revision_changed",
            "active_todo_title": "Polish GTK",
            "todo_filter_status": "in_progress",
            "selected_category_id": "category:ui",
        },
    )

    assert first_key == second_key


def test_state_key_normalizes_rendered_calendar_dates():
    """Equivalent GTK calendar date labels should not reset face timing."""
    runtime = {"state": "running", "model": "qwen3"}

    first_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {"active_view": "calendar", "calendar_selected_date": "2026-08-06"},
    )
    second_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {"active_view": "calendar", "calendar_selected_date": "2026-08-06T15:30:00"},
    )

    assert first_key == second_key


def test_state_key_normalizes_rendered_calendar_status_fallbacks():
    """Equivalent GTK calendar fallback summaries should not reset face timing."""
    runtime = {"state": "running", "model": "qwen3"}

    first_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {"active_view": "calendar", "calendar_view_mode": "week", "status_text": ""},
    )
    second_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {"active_view": "calendar", "calendar_view_mode": "week", "status_text": "Calendar"},
    )

    assert first_key == second_key


def test_state_key_ignores_unrendered_calendar_event_suffixes():
    """Hidden calendar event ID suffixes should not reset GTK face timing."""
    runtime = {"state": "running", "model": "qwen3"}

    first_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {
            "active_view": "calendar",
            "calendar_view_mode": "week",
            "calendar_selected_date": "2026-08-06T12:00:00",
            "calendar_filter_type": "meeting",
            "active_event_id": "event:weekly_robotics_alpha",
        },
    )
    second_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {
            "active_view": "calendar",
            "calendar_view_mode": "week",
            "calendar_selected_date": "2026-08-06T12:00:00",
            "calendar_filter_type": "meeting",
            "active_event_id": "event:weekly_robotics_beta",
        },
    )

    assert first_key == second_key


def test_state_key_normalizes_rendered_active_states():
    """Equivalent GTK active-state labels should not reset face timing."""
    runtime = {"state": "running", "model": "qwen3"}

    first_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {"active_view": "idle", "active_states": ["timer", "idea"]},
    )
    second_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {"active_view": "idle", "active_states": [" timer ", " idea "]},
    )
    blank_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {"active_view": "idle"},
    )
    malformed_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {"active_view": "idle", "active_states": "timer"},
    )

    assert first_key == second_key
    assert blank_key == malformed_key


def test_state_key_normalizes_rendered_pomodoro_timer_values():
    """Equivalent GTK Pomodoro timer labels should not reset face timing."""
    runtime = {"state": "running", "model": "qwen3"}

    first_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {
            "active_view": "pomodoro",
            "timer_state": {
                "status": "running",
                "phase": "work",
                "work_duration_minutes": 25,
                "break_duration_minutes": 5,
                "remaining_work_seconds": 600,
                "remaining_break_seconds": 300,
            },
        },
    )
    second_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {
            "active_view": "pomodoro",
            "timer_state": {
                "status": " running ",
                "phase": " work ",
                "work_duration_minutes": 25.0,
                "break_duration_minutes": 5.0,
                "remaining_work_seconds": 600.0,
                "remaining_break_seconds": 300.0,
            },
        },
    )

    assert first_key == second_key


def test_state_key_normalizes_rendered_idea_view_values():
    """Equivalent GTK idea panel labels should not reset face timing."""
    runtime = {"state": "running", "model": "qwen3"}

    first_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {
            "active_view": "ideas",
            "idea_view": {
                "is_active": True,
                "active_idea_id": "idea:polish_gtk",
            },
        },
    )
    second_key = HenryGtkWindow._state_key(
        object(),
        runtime,
        {
            "active_view": "ideas",
            "idea_view": {
                "is_active": True,
                "active_idea_id": " idea:polish_gtk ",
                "unrendered_backend_revision": "ignored",
            },
        },
    )

    assert first_key == second_key


def test_state_key_normalizes_rendered_runtime_model():
    """Equivalent GTK runtime model labels should not reset face timing."""
    ui_state = {"active_view": "idle", "status_text": "Ready"}

    first_key = HenryGtkWindow._state_key(
        object(),
        {"state": "running", "model": "qwen3"},
        ui_state,
    )
    second_key = HenryGtkWindow._state_key(
        object(),
        {"state": "running", "model": " qwen3 "},
        ui_state,
    )

    assert first_key == second_key


def test_state_key_normalizes_rendered_runtime_state():
    """Equivalent GTK runtime state labels should not reset face timing."""
    ui_state = {"active_view": "idle", "status_text": "Ready"}

    first_key = HenryGtkWindow._state_key(
        object(),
        {"state": "running", "model": "qwen3"},
        ui_state,
    )
    second_key = HenryGtkWindow._state_key(
        object(),
        {"state": " running ", "model": "qwen3"},
        ui_state,
    )

    assert first_key == second_key


def test_run_action_refreshes_after_action_exception():
    """Failed GTK actions should refresh visible runtime/backend state."""
    window = ActionFailureWindow()

    HenryGtkWindow._run_action(
        window,
        "start",
        lambda: (_ for _ in ()).throw(ConnectionError("backend unavailable")),
    )

    assert window.action_status_label.text == "Start: Backend offline"
    assert window.action_status_label.tooltip_text == "Start: Backend offline - backend unavailable"
    assert window.css_class == "status-error"
    assert window.refresh_called is True


def test_run_action_clips_long_exception_status_and_keeps_full_tooltip():
    """Long GTK action exceptions should not crowd the header but remain inspectable."""
    window = ActionFailureWindow()

    HenryGtkWindow._run_action(
        window,
        "preload",
        lambda: (_ for _ in ()).throw(
            RuntimeError("model qwen3-extra-long-model-name failed during warmup")
        ),
    )

    assert window.action_status_label.text == "Preload: model qwen3-ex..."
    assert (
        window.action_status_label.tooltip_text
        == "Preload: model qwen3-extra-long-model-name failed during warmup"
    )
    assert window.css_class == "status-error"
    assert window.refresh_called is True


def test_run_action_clips_long_error_response_and_keeps_full_tooltip():
    """Long GTK action error responses should be compact but inspectable."""
    window = ActionFailureWindow()

    HenryGtkWindow._run_action(
        window,
        "preload",
        lambda: {
            "state": "error",
            "error": "model qwen3-extra-long-model-name failed during warmup",
        },
    )

    assert window.action_status_label.text == "Preload: model qwen3-ex..."
    assert (
        window.action_status_label.tooltip_text
        == "Preload: model qwen3-extra-long-model-name failed during warmup"
    )
    assert window.css_class == "status-error"
    assert window.refresh_called is True


def test_run_action_backend_error_response_tooltip_keeps_full_detail():
    """Backend error responses should stay compact but remain inspectable."""
    window = ActionFailureWindow()

    HenryGtkWindow._run_action(
        window,
        "start",
        lambda: {"state": "error", "error": "Backend unavailable: connection refused"},
    )

    assert window.action_status_label.text == "Start: Backend offline"
    assert (
        window.action_status_label.tooltip_text == "Start: Backend unavailable: connection refused"
    )
    assert window.css_class == "status-error"
    assert window.refresh_called is True


def test_run_action_sets_action_status_tooltip_after_success():
    """Successful GTK actions should expose compact action feedback on hover."""
    window = ActionFailureWindow()

    HenryGtkWindow._run_action(
        window,
        "start",
        lambda: {"state": "running", "model": "qwen3"},
    )

    assert window.action_status_label.text == "Start: Running qwen3"
    assert window.action_status_label.tooltip_text == "Start: Running qwen3"
    assert window.css_class == "status-ok"
    assert window.refresh_called is True


def test_run_action_tooltip_keeps_full_model_name_after_success():
    """Action feedback hover text should show full model names when labels clip them."""
    window = ActionFailureWindow()

    HenryGtkWindow._run_action(
        window,
        "start",
        lambda: {"state": "running", "model": "qwen3-extra-long-model-name"},
    )

    assert window.action_status_label.text == "Start: Running qwen3-extra-lon..."
    assert window.action_status_label.tooltip_text == "Start: Running qwen3-extra-long-model-name"
    assert window.css_class == "status-ok"
    assert window.refresh_called is True


def test_draw_treats_blank_active_view_as_idle_face():
    """Blank GTK active views should draw the idle face, not an empty adaptive panel."""
    window = DrawBranchWindow("   ")

    HenryGtkWindow._draw(window, None, object(), 800, 500)

    assert window.face_calls == 1
    assert window.adaptive_calls == 0


def test_draw_normalizes_idle_active_view_casing():
    """Cased GTK idle views should draw the face, not an adaptive panel."""
    window = DrawBranchWindow(" IDLE ")

    HenryGtkWindow._draw(window, None, object(), 800, 500)

    assert window.face_calls == 1
    assert window.adaptive_calls == 0
