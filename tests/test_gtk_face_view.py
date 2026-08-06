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


def test_view_summary_ignores_blank_tool_status_text():
    """Adaptive view summary falls back instead of rendering whitespace."""
    assert (
        view_summary(
            {"active_view": "ideas", "status_text": "   ", "idea_view": {"draft_text": "  "}},
            {"state": "running"},
        )
        == "Idea captured"
    )
    assert view_summary(
        {"active_view": "todo_list", "status_text": "   "}, {"state": "running"}
    ) == ("Todos")
    assert view_summary(
        {"active_view": "calendar", "status_text": "   "}, {"state": "running"}
    ) == ("Calendar")


def test_view_summary_prioritizes_idle_runtime_errors():
    """Idle GTK canvas should surface runtime errors over stale status text."""
    assert (
        view_summary(
            {"active_view": "idle", "status_text": "Ready"},
            {"state": "error", "error": "microphone unavailable"},
        )
        == "microphone unavailable"
    )


def test_view_summary_labels_backend_outages_as_offline():
    """Idle GTK canvas should summarize backend outages as offline."""
    assert (
        view_summary(
            {"active_view": "idle", "status_text": "Ready"},
            face_view.offline_runtime_state(ConnectionError("connection refused")),
        )
        == "Backend offline"
    )


def test_view_summary_marks_idle_pending_runtime_state():
    """Idle GTK canvas should show runtime startup work when status text is empty."""
    assert view_summary({"active_view": "idle", "status_text": ""}, {"state": "loading"}) == (
        "Loading"
    )
    assert view_summary({"active_view": "idle", "status_text": ""}, {"state": "starting"}) == (
        "Starting"
    )
    assert view_summary({"active_view": "idle", "status_text": "Ready"}, {"state": "loading"}) == (
        "Ready"
    )


def test_view_title_and_accent_make_active_context_scannable():
    """GTK active views expose concise labels and stable visual accents."""
    assert face_view.view_title("idle") == "Listening"
    assert face_view.view_title("pomodoro") == "Pomodoro"
    assert face_view.view_title("todo_list") == "Todos"
    assert face_view.view_title("unknown_tool") == "Unknown Tool"

    assert face_view.view_accent("idle") == (0.31, 0.78, 0.47)
    assert face_view.view_accent("pomodoro") == (0.95, 0.39, 0.32)


def test_surface_accent_marks_runtime_health():
    """GTK surfaces switch accents when runtime needs attention."""
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
        1.0,
        0.42,
        0.37,
    )
    assert face_view.surface_accent({"active_view": "pomodoro"}, {"state": "loading"}) == (
        0.85,
        0.72,
        0.31,
    )
    assert face_view.surface_accent({"active_view": "idle"}, {"state": "starting"}) == (
        0.85,
        0.72,
        0.31,
    )


def test_header_view_title_matches_surface_error_state():
    """GTK header view label mirrors offline and idle runtime error surfaces."""
    offline = face_view.offline_runtime_state(ConnectionError("connection refused"))

    assert face_view.header_view_title({"active_view": "idle"}, offline) == "Offline"
    assert (
        face_view.header_view_title(
            {"active_view": "idle"},
            {"state": "error", "error": "microphone unavailable"},
        )
        == "Error"
    )
    assert face_view.header_view_title({"active_view": "idle"}, {"state": "running"}) == "Listening"
    assert (
        face_view.header_view_title({"active_view": "pomodoro"}, {"state": "error"}) == "Pomodoro"
    )


def test_header_view_title_marks_idle_pending_runtime_state():
    """Idle GTK title should show runtime startup work instead of Listening."""
    assert face_view.header_view_title({"active_view": "idle"}, {"state": "loading"}) == "Loading"
    assert face_view.header_view_title({"active_view": "idle"}, {"state": "starting"}) == "Starting"
    assert face_view.status_badges({"active_view": "idle"}, {"state": "loading"}) == (
        "Loading",
        "Runtime: Loading",
    )


def test_header_view_status_class_marks_surface_severity():
    """GTK header view label uses color only when the surface state needs it."""
    offline = face_view.offline_runtime_state(ConnectionError("connection refused"))

    assert face_view.header_view_status_class({"active_view": "idle"}, offline) == "status-error"
    assert (
        face_view.header_view_status_class(
            {"active_view": "idle"},
            {"state": "error", "error": "microphone unavailable"},
        )
        == "status-error"
    )
    assert (
        face_view.header_view_status_class({"active_view": "idle"}, {"state": "running"})
        == "status-ok"
    )
    assert (
        face_view.header_view_status_class({"active_view": "pomodoro"}, {"state": "error"})
        == "status-error"
    )
    assert (
        face_view.header_view_status_class({"active_view": "pomodoro"}, {"state": "loading"})
        == "status-pending"
    )


def test_runtime_summary_shows_state_and_loaded_model():
    """Runtime summary is human-readable in the header."""
    assert face_view.runtime_summary({"state": "running", "model": "qwen3"}) == "Running - qwen3"
    assert face_view.runtime_summary({"state": "stopped", "model": ""}) == "Stopped"
    assert face_view.runtime_summary({}) == "Unknown"


def test_runtime_summary_labels_backend_outages_as_offline():
    """GTK runtime labels should show backend outages as offline."""
    runtime = face_view.offline_runtime_state(ConnectionError("connection refused"))

    assert face_view.runtime_summary(runtime) == "Offline"


def test_offline_runtime_state_clears_stale_runtime_context():
    """Backend loss gets a fresh error runtime without stale model context."""
    runtime = face_view.offline_runtime_state(ConnectionError("connection refused"))

    assert runtime == {
        "state": "error",
        "error": "Backend unavailable: connection refused",
    }
    assert face_view.status_badges({"active_view": "idle"}, runtime) == (
        "Offline",
        "Runtime: Offline",
        "Error: Backend offline",
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
    assert (
        face_view.action_feedback(
            "start",
            {"state": "error", "error": "Backend unavailable: connection refused"},
        )
        == "Start: Backend offline"
    )
    assert face_view.action_feedback("stop", {"state": "error", "error": "   "}) == "Stop: Error"
    assert face_view.action_feedback("   ", {"state": "running"}) == "Action: Running"


def test_action_tooltip_includes_human_keyboard_shortcuts():
    """GTK toolbar tooltips expose shortcuts without raw accelerator syntax."""
    assert face_view.action_tooltip("start", "Start voice runtime") == (
        "Start voice runtime (Ctrl+Enter)"
    )
    assert face_view.action_tooltip("back", "Go back") == "Go back (Esc, Alt+Left)"


def test_action_tooltip_humanizes_punctuation_shortcuts():
    """GTK toolbar tooltips show normal punctuation for punctuation keys."""
    assert face_view.action_tooltip("stop", "Stop voice runtime") == ("Stop voice runtime (Ctrl+.)")


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
    assert face_view.header_state(
        {
            "view_stack": ["idle"],
            "active_states": ["timer", "idea", "todo_list", "calendar", "voice_note"],
        }
    ) == {
        "can_go_back": False,
        "active_states_label": "Active: Timer, Idea, Todo List +2",
    }


def test_gtk_labels_humanize_hyphenated_api_values():
    """GTK labels render hyphenated API values as normal words."""
    assert face_view.header_state({"view_stack": ["idle"], "active_states": ["voice-note"]}) == {
        "can_go_back": False,
        "active_states_label": "Active: Voice Note",
    }
    assert face_view.tool_panel(
        {"active_view": "todo_list", "todo_filter_status": "in-progress"},
        {"state": "running"},
    ).detail_lines == ("Filter: In Progress",)


def test_active_states_status_class_marks_concurrent_work():
    """GTK active-states label gets emphasis only when work is active."""
    assert (
        face_view.active_states_status_class({"active_states": ["timer", "idea"]})
        == "status-pending"
    )
    assert face_view.active_states_status_class({"active_states": []}) == "status-neutral"
    assert face_view.active_states_status_class({}) == "status-neutral"


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
        "Error: microphone unavailable",
        "Model: qwen3",
    )
    assert face_view.status_badges(
        {"active_view": "todo_list"},
        {"state": "error", "model": "qwen3", "error": "microphone unavailable"},
    ) == (
        "Todos",
        "Runtime: Error",
        "Error: microphone unavailable",
        "Model: qwen3",
    )
    assert face_view.status_badges(
        {"active_view": "todo_list"},
        {
            "state": "error",
            "model": "qwen3",
            "error": "Backend unavailable: connection refused",
        },
    ) == (
        "Todos",
        "Runtime: Offline",
        "Error: Backend offline",
        "Model: qwen3",
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
    assert face_view.status_badge_tone("Runtime: Offline") == "error"
    assert face_view.status_badge_tone("Runtime: Running") == "ok"
    assert face_view.status_badge_tone("Runtime: Loading") == "pending"
    assert face_view.status_badge_tone("Loading") == "pending"
    assert face_view.status_badge_tone("Starting") == "pending"
    assert face_view.status_badge_tone("Active: Timer, Idea") == "pending"
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


def test_tool_panel_surfaces_active_view_runtime_errors():
    """Active GTK panels should include runtime errors in central detail text."""
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
        {"state": "error", "error": "microphone unavailable"},
    )

    assert panel.detail_lines == (
        "Running work session",
        "Break queued for 05:00",
        "Runtime error: microphone unavailable",
    )


def test_tool_panel_surfaces_active_view_pending_runtime_state():
    """Active GTK panels should include pending runtime state in central detail text."""
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
        {"state": "loading"},
    )

    assert panel.detail_lines == (
        "Running work session",
        "Break queued for 05:00",
        "Runtime: Loading",
    )


def test_tool_panel_prioritizes_runtime_errors_when_detail_slots_are_full():
    """Active GTK panels should not drop runtime errors when details are full."""
    panel = face_view.tool_panel(
        {
            "active_view": "todo_list",
            "status_text": "3 tasks",
            "todo_filter_status": "in_progress",
            "active_todo_title": "Polish GTK",
            "selected_category_id": "local-runtime",
        },
        {"state": "error", "error": "microphone unavailable"},
    )

    assert panel.detail_lines == (
        "Active: Polish GTK",
        "Filter: In Progress",
        "Runtime error: microphone unavailable",
    )


def test_tool_panel_surfaces_idle_runtime_error_details():
    """Idle GTK panel shows the runtime error reason, not only the error state."""
    panel = face_view.tool_panel(
        {"active_view": "idle", "status_text": "Waiting"},
        {"state": "error", "model": "qwen3", "error": "microphone unavailable"},
    )

    assert panel.summary == "microphone unavailable"
    assert panel.detail_lines == ("Runtime: Error - qwen3", "Error: microphone unavailable")
    offline_panel = face_view.tool_panel(
        {"active_view": "idle", "status_text": "Waiting"},
        face_view.offline_runtime_state(ConnectionError("connection refused")),
    )
    assert offline_panel.summary == "Backend offline"
    assert offline_panel.detail_lines == ("Runtime: Offline", "Error: Backend offline")


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
    assert face_view.tool_panel(
        {
            "active_view": "todo_list",
            "status_text": "3 tasks",
            "active_todo_id": "todo-123456789",
        },
        {"state": "running"},
    ).detail_lines == ("Active: todo-123",)
    assert calendar_panel.summary == "Week"
    assert calendar_panel.detail_lines == ("Date: Aug 5, 2026", "Type: Meeting")
    assert face_view.tool_panel(
        {
            "active_view": "calendar",
            "calendar_selected_date": "2026-08-05T15:30:00",
        },
        {"state": "running"},
    ).detail_lines == ("Date: Aug 5, 2026",)
    assert face_view.tool_panel(
        {
            "active_view": "calendar",
            "active_event_id": "event:weekly_robotics_seminar_2026_01_27",
        },
        {"state": "running"},
    ).detail_lines == ("Event: weekly_r",)


def test_tool_panel_simplifies_scoped_fallback_identifiers():
    """Fallback GTK panel identifiers show the useful scoped ID segment."""
    assert face_view.tool_panel(
        {
            "active_view": "ideas",
            "idea_view": {"active_idea_id": "idea:capture_voice_routine_2026_08_06"},
        },
        {"state": "running"},
    ).detail_lines == ("ID: capture_",)
    assert face_view.tool_panel(
        {
            "active_view": "todo_list",
            "active_todo_id": "todo:book_doctor_appointment_2026_08_06",
            "selected_category_id": "category:health_admin_2026",
        },
        {"state": "running"},
    ).detail_lines == ("Active: book_doc", "Category: health_a")


def test_tool_panel_skips_blank_fallback_identifiers():
    """Fallback GTK panel identifiers should not render empty labels."""
    assert face_view.tool_panel(
        {"active_view": "ideas", "idea_view": {"active_idea_id": "   "}},
        {"state": "running"},
    ).detail_lines == ("Ready to capture",)
    assert (
        face_view.tool_panel(
            {
                "active_view": "todo_list",
                "active_todo_id": "   ",
                "selected_category_id": "   ",
            },
            {"state": "running"},
        ).detail_lines
        == ()
    )
    assert (
        face_view.tool_panel(
            {"active_view": "calendar", "active_event_id": "   "},
            {"state": "running"},
        ).detail_lines
        == ()
    )


def test_tool_panel_skips_blank_filter_labels():
    """GTK filter labels should fall back instead of rendering blank text."""
    assert (
        face_view.tool_panel(
            {"active_view": "todo_list", "todo_filter_status": "   "},
            {"state": "running"},
        ).detail_lines
        == ()
    )
    calendar_panel = face_view.tool_panel(
        {
            "active_view": "calendar",
            "calendar_view_mode": "   ",
            "calendar_filter_type": "   ",
        },
        {"state": "running"},
    )

    assert calendar_panel.summary == "Upcoming"
    assert calendar_panel.detail_lines == ()
