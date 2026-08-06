"""Tests for GTK adaptive face view helpers."""

from __future__ import annotations

from app.gtk_ui import face_view
from app.gtk_ui.face_view import face_geometry, sleepiness_for_elapsed, view_summary


def test_sleepiness_matches_legacy_thresholds():
    """Sleepiness follows happy, neutral, sleepy, asleep thresholds."""
    assert (
        sleepiness_for_elapsed(10, happy_seconds=120, neutral_seconds=300, sleepy_seconds=600) == 0
    )
    assert (
        sleepiness_for_elapsed(150, happy_seconds=120, neutral_seconds=300, sleepy_seconds=600) == 1
    )
    assert (
        sleepiness_for_elapsed(450, happy_seconds=120, neutral_seconds=300, sleepy_seconds=600) == 2
    )
    assert (
        sleepiness_for_elapsed(700, happy_seconds=120, neutral_seconds=300, sleepy_seconds=600) == 3
    )


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
    assert (
        view_summary(
            {
                "active_view": "pomodoro",
                "timer_state": {
                    "remaining_work_seconds": 1500,
                    "remaining_break_seconds": 300,
                    "phase": "work",
                },
            },
            {"state": "running"},
        )
        == "Work 25:00 | Break 05:00"
    )
    assert (
        view_summary(
            {"active_view": "ideas", "idea_view": {"draft_text": "Ship the GTK face"}},
            {"state": "running"},
        )
        == "Ship the GTK face"
    )


def test_view_title_and_accent_make_active_context_scannable():
    """GTK active views expose concise labels and stable visual accents."""
    assert face_view.view_title("idle") == "Listening"
    assert face_view.view_title("pomodoro") == "Pomodoro"
    assert face_view.view_title("todo_list") == "Todos"
    assert face_view.view_title("unknown_tool") == "Unknown Tool"

    assert face_view.view_accent("idle") == (0.31, 0.78, 0.47)
    assert face_view.view_accent("pomodoro") == (0.95, 0.39, 0.32)


def test_surface_accent_marks_idle_runtime_errors():
    """Idle GTK face switches to an error accent when runtime is unhealthy."""
    offline = face_view.offline_runtime_state(ConnectionError("connection refused"))

    assert face_view.surface_accent({"active_view": "idle"}, offline) == (1.0, 0.42, 0.37)
    assert face_view.surface_accent(
        {"active_view": "idle"},
        {"state": "error", "error": "microphone unavailable"},
    ) == (1.0, 0.42, 0.37)
    assert face_view.surface_accent({"active_view": "idle"}, {"state": "running"}) == (
        0.31,
        0.78,
        0.47,
    )
    assert face_view.surface_accent({"active_view": "pomodoro"}, {"state": "error"}) == (
        0.95,
        0.39,
        0.32,
    )


def test_runtime_summary_shows_state_and_loaded_model():
    """Runtime summary is human-readable in the header."""
    assert face_view.runtime_summary({"state": "running", "model": "qwen3"}) == "Running - qwen3"
    assert face_view.runtime_summary({"state": "stopped", "model": ""}) == "Stopped"
    assert face_view.runtime_summary({}) == "Unknown"


def test_offline_runtime_state_clears_stale_runtime_context():
    """Backend loss gets a fresh error runtime without stale model context."""
    runtime = face_view.offline_runtime_state(ConnectionError("connection refused"))

    assert runtime == {
        "state": "error",
        "error": "Backend unavailable: connection refused",
    }
    assert face_view.status_badges({"active_view": "idle"}, runtime) == (
        "Offline",
        "Runtime: Error",
        "Error: Backend unavailable: connection refused",
    )


def test_offline_runtime_state_handles_blank_errors():
    """Offline runtime state still gives GTK a useful error label."""
    assert face_view.offline_runtime_state("") == {
        "state": "error",
        "error": "Backend unavailable: unknown error",
    }


def test_model_override_trims_blank_input():
    """GTK model entry sends a model only when the user typed a value."""
    assert face_view.model_override(" qwen3:8b ") == "qwen3:8b"
    assert face_view.model_override("   ") is None
    assert face_view.model_override(None) is None


def test_model_entry_text_syncs_runtime_model_until_user_edits():
    """GTK model entry mirrors runtime model until the user types an override."""
    assert face_view.model_entry_text("", {"model": "qwen3:8b"}, user_edited=False) == "qwen3:8b"
    assert face_view.model_entry_text("custom", {"model": "qwen3:8b"}, user_edited=True) == "custom"
    assert face_view.model_entry_text("", {}, user_edited=False) == ""


def test_model_entry_text_clears_when_runtime_model_unloads():
    """GTK model entry drops stale synced model text after unload."""
    assert face_view.model_entry_text("qwen3:8b", {"model": ""}, user_edited=False) == ""
    assert face_view.model_entry_text("qwen3:8b", {}, user_edited=False) == ""


def test_model_entry_user_edited_resets_after_successful_model_actions():
    """GTK model entry resumes runtime sync after preload or unload succeeds."""
    assert (
        face_view.model_entry_user_edited_after_action(
            "preload", {"state": "loaded", "model": "qwen3"}, was_user_edited=True
        )
        is False
    )
    assert (
        face_view.model_entry_user_edited_after_action(
            "unload", {"state": "unloaded", "model": "qwen3"}, was_user_edited=True
        )
        is False
    )
    assert (
        face_view.model_entry_user_edited_after_action(
            "preload", {"error": "no model"}, was_user_edited=True
        )
        is True
    )
    assert (
        face_view.model_entry_user_edited_after_action(
            "start", {"state": "running"}, was_user_edited=True
        )
        is True
    )


def test_model_entry_user_edited_tracks_manual_text_changes():
    """GTK model entry returns to runtime sync when the override is cleared."""
    assert (
        face_view.model_entry_user_edited_after_change(
            "custom-model", was_syncing=False, was_user_edited=False
        )
        is True
    )
    assert (
        face_view.model_entry_user_edited_after_change(
            "   ", was_syncing=False, was_user_edited=True
        )
        is False
    )
    assert (
        face_view.model_entry_user_edited_after_change(
            "qwen3", was_syncing=True, was_user_edited=False
        )
        is False
    )


def test_action_feedback_prefers_response_state_and_model():
    """GTK action feedback turns API results into short human-facing messages."""
    assert (
        face_view.action_feedback("preload", {"state": "loaded", "model": "qwen3"})
        == "Preload: Loaded qwen3"
    )
    assert (
        face_view.action_feedback("start", {"state": "running", "model": "qwen3"})
        == "Start: Running qwen3"
    )
    assert (
        face_view.action_feedback("stop", {"state": "error", "error": "no command"})
        == "Stop: no command"
    )


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
    assert face_view.control_state({"state": "loaded"}) == {
        "start": True,
        "stop": False,
        "preload": True,
        "unload": True,
    }
    assert face_view.control_state({"state": "unloaded"}) == {
        "start": True,
        "stop": False,
        "preload": True,
        "unload": False,
    }
    assert face_view.control_state({"state": "error", "model": "qwen3"}) == {
        "start": True,
        "stop": False,
        "preload": True,
        "unload": True,
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


def test_status_badges_summarize_current_surface_state():
    """Canvas status badges make key context visible away from the dense header."""
    assert face_view.status_badges(
        {"active_view": "pomodoro", "active_states": ["timer", "idea"]},
        {"state": "running", "model": "qwen3"},
    ) == ("Pomodoro", "Runtime: Running", "Model: qwen3", "Active: Timer, Idea")
    assert face_view.status_badges({"active_view": "idle"}, {"state": "stopped"}) == (
        "Listening",
        "Runtime: Stopped",
    )


def test_status_badges_include_runtime_error_reason():
    """Canvas badges surface runtime errors even outside the idle panel."""
    assert face_view.status_badges(
        {"active_view": "idle"},
        {"state": "error", "model": "qwen3", "error": "microphone unavailable"},
    ) == (
        "Error",
        "Runtime: Error",
        "Model: qwen3",
        "Error: microphone unavailable",
    )
    assert face_view.status_badges(
        {"active_view": "todo_list"},
        {"state": "error", "model": "qwen3", "error": "microphone unavailable"},
    ) == (
        "Todos",
        "Runtime: Error",
        "Model: qwen3",
        "Error: microphone unavailable",
    )


def test_runtime_status_class_marks_state_severity():
    """GTK header runtime label gets a scannable status color."""
    assert face_view.runtime_status_class({"state": "running"}) == "status-ok"
    assert face_view.runtime_status_class({"state": "loaded"}) == "status-ok"
    assert face_view.runtime_status_class({"state": "loading"}) == "status-pending"
    assert face_view.runtime_status_class({"state": "error"}) == "status-error"
    assert face_view.runtime_status_class({}) == "status-pending"


def test_action_status_class_marks_response_severity():
    """GTK action feedback label mirrors success, progress, and failure."""
    assert face_view.action_status_class({"state": "running"}) == "status-ok"
    assert face_view.action_status_class({"state": "loading"}) == "status-pending"
    assert face_view.action_status_class({"error": "no microphone"}) == "status-error"


def test_compact_status_badges_clips_long_badges():
    """GTK canvas badges stay bounded when model names are long."""
    assert face_view.compact_status_badges(
        (
            "Listening",
            "Runtime: Running",
            "Model: qwen3-extra-long-model-name",
        ),
        max_chars=18,
    ) == ("Listening", "Runtime: Running", "Model: qwen3-ex...")


def test_compact_status_badges_omits_blank_badges():
    """GTK canvas badges skip empty labels instead of drawing empty pills."""
    assert face_view.compact_status_badges(
        ("Listening", "", "  ", "Runtime: Running"),
        max_chars=24,
    ) == ("Listening", "Runtime: Running")


def test_status_badge_tone_marks_important_states():
    """GTK canvas badges use tones that make state severity scannable."""
    assert face_view.status_badge_tone("Offline") == "error"
    assert face_view.status_badge_tone("Error") == "error"
    assert face_view.status_badge_tone("Error: microphone unavailable") == "error"
    assert face_view.status_badge_tone("Runtime: Error") == "error"
    assert face_view.status_badge_tone("Runtime: Running") == "ok"
    assert face_view.status_badge_tone("Runtime: Loading") == "pending"
    assert face_view.status_badge_tone("Pomodoro") == "neutral"


def test_status_badge_rgba_uses_subtle_tinted_fills():
    """GTK canvas badges keep contrast while carrying status color."""
    assert face_view.status_badge_rgba("Runtime: Running", (0.1, 0.2, 0.3)) == (
        0.31,
        0.78,
        0.47,
        0.18,
    )
    assert face_view.status_badge_rgba("Offline", (0.1, 0.2, 0.3)) == (
        1.0,
        0.42,
        0.37,
        0.2,
    )
    assert face_view.status_badge_rgba("Pomodoro", (0.1, 0.2, 0.3)) == (
        0.1,
        0.2,
        0.3,
        0.16,
    )


def test_wrapped_text_lines_wraps_words_with_overflow_marker():
    """Long GTK summaries wrap into bounded canvas lines."""
    assert face_view.wrapped_text_lines(
        "Ship the GTK face with clearer panel summaries",
        max_chars=16,
        max_lines=3,
    ) == ("Ship the GTK", "face with", "clearer panel...")


def test_wrapped_text_lines_clips_single_long_words():
    """Long unbroken GTK text is clipped instead of overflowing the canvas."""
    assert face_view.wrapped_text_lines(
        "supercalifragilistic",
        max_chars=10,
        max_lines=2,
    ) == ("superca...",)


def test_wrapped_text_lines_preserves_short_text():
    """Short GTK text remains a single readable line."""
    assert face_view.wrapped_text_lines(
        "Ready to capture",
        max_chars=24,
        max_lines=2,
    ) == ("Ready to capture",)


def test_wrapped_detail_lines_wraps_long_details_with_total_limit():
    """Long GTK detail labels wrap while keeping the panel bounded."""
    assert face_view.wrapped_detail_lines(
        (
            "Active: Polish the GTK experience with wrapped detail rendering",
            "Filter: In Progress",
        ),
        max_chars=24,
        max_lines_per_detail=2,
        max_total_lines=4,
    ) == (
        "Active: Polish the GTK",
        "experience with wrapp...",
        "Filter: In Progress",
    )


def test_wrapped_detail_lines_marks_omitted_details():
    """GTK detail wrapping shows when lower-priority details were omitted."""
    assert face_view.wrapped_detail_lines(
        (
            "Active: Build voice controls",
            "Filter: In Progress",
            "Category: local-runtime",
        ),
        max_chars=24,
        max_lines_per_detail=1,
        max_total_lines=2,
    ) == ("Active: Build voice...", "Filter: In Progress...")


def test_action_shortcuts_are_stable_and_discoverable():
    """GTK app actions expose predictable keyboard accelerators."""
    assert face_view.action_shortcuts() == {
        "back": ["Escape", "<Alt>Left"],
        "start": ["<Primary>Return"],
        "stop": ["<Primary>period"],
        "preload": ["<Primary>r"],
        "unload": ["<Primary>u"],
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


def test_tool_panel_surfaces_idle_runtime_error_details():
    """Idle GTK panel shows the runtime error reason, not only the error state."""
    panel = face_view.tool_panel(
        {"active_view": "idle", "status_text": "Waiting"},
        {"state": "error", "model": "qwen3", "error": "microphone unavailable"},
    )

    assert panel.summary == "Waiting"
    assert panel.detail_lines == ("Error - qwen3", "Error: microphone unavailable")


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
