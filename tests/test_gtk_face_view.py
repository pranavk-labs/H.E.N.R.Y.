"""Tests for GTK adaptive face view helpers."""

from __future__ import annotations

from app.gtk_ui import face_view
from app.gtk_ui.face_view import face_geometry, sleepiness_for_elapsed, view_summary


def test_sleepiness_matches_legacy_thresholds():
    """Sleepiness follows happy, neutral, sleepy, asleep thresholds."""
    assert sleepiness_for_elapsed(10, happy_seconds=120, neutral_seconds=300, sleepy_seconds=600) == 0
    assert sleepiness_for_elapsed(150, happy_seconds=120, neutral_seconds=300, sleepy_seconds=600) == 1
    assert sleepiness_for_elapsed(450, happy_seconds=120, neutral_seconds=300, sleepy_seconds=600) == 2
    assert sleepiness_for_elapsed(700, happy_seconds=120, neutral_seconds=300, sleepy_seconds=600) == 3


def test_face_geometry_is_centered_and_responsive():
    """Face geometry centers the old eyes-and-mouth face and scales from width."""
    geometry = face_geometry(width=1000, height=600, phase=0, sleepiness_level=0)

    assert geometry.center_x == 500
    assert geometry.base_radius == 200
    assert geometry.left_eye.center_x == 420
    assert geometry.right_eye.center_x == 580
    assert geometry.left_eye.radius_x == 60
    assert geometry.mouth.width == 280


def test_view_summary_prefers_active_tool_context():
    """Adaptive view summary shows focused state instead of shell navigation."""
    assert view_summary({"active_view": "idle", "status_text": ""}, {"state": "running"}) == ""
    assert view_summary(
        {
            "active_view": "pomodoro",
            "timer_state": {
                "remaining_work_seconds": 1500,
                "remaining_break_seconds": 300,
                "phase": "work",
            },
        },
        {"state": "running"},
    ) == "Work 25:00 | Break 05:00"
    assert view_summary(
        {"active_view": "ideas", "idea_view": {"draft_text": "Ship the GTK face"}},
        {"state": "running"},
    ) == "Ship the GTK face"


def test_view_title_and_accent_make_active_context_scannable():
    """GTK active views expose concise labels and stable visual accents."""
    assert face_view.view_title("idle") == "Listening"
    assert face_view.view_title("pomodoro") == "Pomodoro"
    assert face_view.view_title("todo_list") == "Todos"
    assert face_view.view_title("unknown_tool") == "Unknown Tool"

    assert face_view.view_accent("idle") == (0.31, 0.78, 0.47)
    assert face_view.view_accent("pomodoro") == (0.95, 0.39, 0.32)


def test_runtime_summary_shows_state_and_loaded_model():
    """Runtime summary is human-readable in the header."""
    assert face_view.runtime_summary({"state": "running", "model": "qwen3"}) == "Running - qwen3"
    assert face_view.runtime_summary({"state": "stopped", "model": ""}) == "Stopped"
    assert face_view.runtime_summary({}) == "Unknown"


def test_control_state_matches_runtime_lifecycle():
    """GTK controls disable actions that do not apply to the current runtime state."""
    assert face_view.control_state({"state": "running"}) == {
        "start": False,
        "stop": True,
        "preload": True,
        "unload": True,
    }
    assert face_view.control_state({"state": "stopped"}) == {
        "start": True,
        "stop": False,
        "preload": True,
        "unload": False,
    }
    assert face_view.control_state({"state": "loading"}) == {
        "start": False,
        "stop": False,
        "preload": False,
        "unload": False,
    }


def test_header_state_exposes_back_and_active_states():
    """GTK header state makes navigation and concurrent work visible."""
    assert face_view.header_state(
        {"view_stack": ["idle", "pomodoro"], "active_states": ["timer", "idea"]}
    ) == {
        "can_go_back": True,
        "active_states_label": "Active: Timer, Idea",
    }
    assert face_view.header_state({"view_stack": ["idle"], "active_states": []}) == {
        "can_go_back": False,
        "active_states_label": "",
    }


def test_tool_panel_enriches_pomodoro_state():
    """Pomodoro view exposes phase, next break, and progress for rendering."""
    panel = face_view.tool_panel(
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
        {"state": "running"},
    )

    assert panel.title == "Pomodoro"
    assert panel.summary == "Work 10:00 | Break 05:00"
    assert panel.detail_lines == ("Running work session", "Break queued for 05:00")
    assert panel.progress == 0.6


def test_tool_panel_enriches_todo_and_calendar_filters():
    """Todo and calendar views surface filters instead of generic placeholder text."""
    todo_panel = face_view.tool_panel(
        {
            "active_view": "todo_list",
            "status_text": "3 tasks",
            "todo_filter_status": "in_progress",
            "active_todo_title": "Polish GTK",
        },
        {"state": "running"},
    )
    calendar_panel = face_view.tool_panel(
        {
            "active_view": "calendar",
            "calendar_view_mode": "week",
            "calendar_selected_date": "2026-08-05",
            "calendar_filter_type": "meeting",
        },
        {"state": "running"},
    )

    assert todo_panel.summary == "3 tasks"
    assert todo_panel.detail_lines == ("Active: Polish GTK", "Filter: In Progress")
    assert calendar_panel.summary == "Week"
    assert calendar_panel.detail_lines == ("Date: 2026-08-05", "Type: Meeting")
