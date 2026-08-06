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
    assert view_summary({"active_view": "idle", "status_text": ""}, {"state": "running"}) == (
        "Running"
    )
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


def test_view_summary_prefers_calendar_event_title_over_generic_status():
    """Selected calendar events should replace generic GTK calendar summary text."""
    assert (
        view_summary(
            {
                "active_view": "calendar",
                "status_text": "Calendar",
                "active_event_title": "Weekly robotics seminar",
            },
            {"state": "running"},
        )
        == "Weekly robotics seminar"
    )


def test_view_summary_prefers_selected_titles_over_generic_tool_statuses():
    """Selected Todo and Calendar items should stay visible over generic list labels."""
    assert (
        view_summary(
            {
                "active_view": "todo_list",
                "status_text": "Todo List",
                "active_todo_title": "Polish GTK selected task",
            },
            {"state": "running"},
        )
        == "Polish GTK selected task"
    )
    assert (
        view_summary(
            {
                "active_view": "calendar",
                "status_text": "Events",
                "active_event_title": "Design review",
            },
            {"state": "running"},
        )
        == "Design review"
    )


def test_view_summary_tolerates_non_mapping_idea_state():
    """Malformed idea state should not crash the GTK summary."""
    assert (
        view_summary({"active_view": "ideas", "status_text": "   ", "idea_view": "bad"}, {})
        == "Idea captured"
    )


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


def test_runtime_labels_treat_backend_outage_prefix_case_insensitively():
    """GTK outage labels should stay clean when backend error casing varies."""
    runtime = {"state": "error", "error": "backend unavailable: connection refused"}

    assert view_summary({"active_view": "idle", "status_text": "Ready"}, runtime) == (
        "Backend offline"
    )
    assert face_view.runtime_summary(runtime) == "Offline"
    assert face_view.status_badges({"active_view": "idle"}, runtime) == (
        "Offline",
        "Runtime: Offline",
        "Error: Backend offline",
    )


def test_view_summary_marks_idle_pending_runtime_state():
    """Idle GTK canvas should show runtime startup work when status text is empty."""
    assert view_summary({"active_view": "idle", "status_text": ""}, {"state": "loading"}) == (
        "Loading"
    )
    assert view_summary({"active_view": "idle", "status_text": ""}, {"state": " loading "}) == (
        "Loading"
    )
    assert view_summary({"active_view": "idle", "status_text": ""}, {"state": "starting"}) == (
        "Starting"
    )
    assert view_summary({"active_view": "idle", "status_text": "Ready"}, {"state": "loading"}) == (
        "Loading"
    )


def test_view_summary_treats_blank_active_view_as_idle():
    """Blank GTK active view should use the idle summary path."""
    assert view_summary({"active_view": "   ", "status_text": ""}, {"state": "running"}) == (
        "Running"
    )
    assert view_summary({"active_view": "   ", "status_text": ""}, {"state": "loading"}) == (
        "Loading"
    )


def test_view_summary_humanizes_unknown_view_runtime_fallback():
    """Unknown GTK views should not show raw runtime state identifiers."""
    assert (
        view_summary({"active_view": "voice_note", "status_text": "   "}, {"state": "voice-error"})
        == "Runtime: Voice Error"
    )


def test_view_title_and_accent_make_active_context_scannable():
    """GTK active views expose concise labels and stable visual accents."""
    assert face_view.view_title("idle") == "Listening"
    assert face_view.view_title("pomodoro") == "Pomodoro"
    assert face_view.view_title("todo_list") == "Todos"
    assert face_view.view_title("unknown_tool") == "Unknown Tool"
    assert face_view.view_title("voice-note") == "Voice Note"
    assert face_view.view_title("   ") == "Listening"
    assert face_view.status_badges({"active_view": "   "}, {"state": "running"}) == (
        "Listening",
        "Runtime: Running",
    )

    assert face_view.view_accent("idle") == (0.31, 0.78, 0.47)
    assert face_view.view_accent("pomodoro") == (0.95, 0.39, 0.32)
    assert face_view.view_accent(" pomodoro ") == (0.95, 0.39, 0.32)
    assert face_view.view_accent("   ") == (0.31, 0.78, 0.47)


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
    assert face_view.surface_accent({"active_view": "   "}, {"state": "running"}) == (
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
    assert face_view.surface_accent({"active_view": "idle"}, {"state": " loading "}) == (
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
    assert face_view.header_view_title({"active_view": "idle"}, {"state": " loading "}) == "Loading"
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
    assert face_view.runtime_summary({"state": "   "}) == "Unknown"
    assert face_view.status_badges({"active_view": "idle"}, {"state": "   "}) == (
        "Listening",
        "Runtime: Unknown",
    )


def test_runtime_summary_clips_long_model_names():
    """GTK runtime summary should keep long model names from crowding the header."""
    assert (
        face_view.runtime_summary({"state": "running", "model": "qwen3-extra-long-model-name"})
        == "Running - qwen3-extra-lon..."
    )
    assert (
        face_view.runtime_tooltip({"state": "running", "model": "qwen3-extra-long-model-name"})
        == "Running - qwen3-extra-long-model-name"
    )


def test_runtime_summary_labels_backend_outages_as_offline():
    """GTK runtime labels should show backend outages as offline."""
    runtime = face_view.offline_runtime_state(ConnectionError("connection refused"))

    assert face_view.runtime_summary(runtime) == "Offline"
    assert face_view.runtime_tooltip(runtime) == "Offline - Backend unavailable: connection refused"


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
    assert face_view.status_badges({"active_view": "   "}, runtime) == (
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
    assert face_view.model_entry_text("qwen3:8b", {"model": "   "}, user_edited=False) == ""
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
            "preload", {"state": "loaded", "model": "qwen3", "error": "   "}, was_user_edited=True
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


def test_model_entry_tooltip_marks_active_user_override():
    """GTK model override entry should explain when typed text is active."""
    assert face_view.model_entry_tooltip("custom-model", user_edited=True) == (
        "Model override active: custom-model"
    )
    assert face_view.model_entry_tooltip(" custom-model ", user_edited=True) == (
        "Model override active: custom-model"
    )
    assert face_view.model_entry_tooltip("qwen3", user_edited=False) == (
        "Model override for preload and unload"
    )
    assert face_view.model_entry_tooltip("   ", user_edited=True) == (
        "Model override for preload and unload"
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
            "preload",
            {
                "state": "error",
                "error": "model qwen3-extra-long-model-name failed during warmup",
            },
        )
        == "Preload: model qwen3-ex..."
    )
    assert (
        face_view.action_feedback_tooltip(
            "preload",
            {
                "state": "error",
                "error": "model qwen3-extra-long-model-name failed during warmup",
            },
        )
        == "Preload: model qwen3-extra-long-model-name failed during warmup"
    )
    assert (
        face_view.action_feedback(
            "start",
            {"state": "error", "error": "Backend unavailable: connection refused"},
        )
        == "Start: Backend offline"
    )
    assert (
        face_view.action_feedback_tooltip(
            "start",
            {"state": "error", "error": "Backend unavailable: connection refused"},
        )
        == "Start: Backend unavailable: connection refused"
    )
    assert face_view.action_feedback("stop", {"state": "error", "error": "   "}) == "Stop: Error"
    assert face_view.action_feedback("   ", {"state": "running"}) == "Action: Running"
    assert face_view.action_feedback("start", {"state": "   "}) == "Start: Complete"


def test_action_feedback_clips_long_model_names():
    """GTK action feedback should not let long model names crowd the header."""
    assert (
        face_view.action_feedback(
            "preload",
            {"state": "loaded", "model": "qwen3-extra-long-model-name"},
        )
        == "Preload: Loaded qwen3-extra-lon..."
    )
    assert (
        face_view.action_feedback_tooltip(
            "preload",
            {"state": "loaded", "model": "qwen3-extra-long-model-name"},
        )
        == "Preload: Loaded qwen3-extra-long-model-name"
    )


def test_action_exception_feedback_uses_readable_blank_fallback():
    """GTK exception feedback should not expose Python type names for blank text."""
    assert face_view.action_exception_feedback("start", "") == "Start: Error"
    assert (
        face_view.action_exception_feedback("start", ConnectionError("connection refused"))
        == "Start: Backend offline"
    )
    assert (
        face_view.action_exception_feedback_tooltip("start", ConnectionError("connection refused"))
        == "Start: Backend offline - connection refused"
    )
    assert (
        face_view.action_exception_feedback(
            "preload",
            RuntimeError("model qwen3-extra-long-model-name failed during warmup"),
        )
        == "Preload: model qwen3-ex..."
    )
    assert (
        face_view.action_exception_feedback_tooltip(
            "preload",
            RuntimeError("model qwen3-extra-long-model-name failed during warmup"),
        )
        == "Preload: model qwen3-extra-long-model-name failed during warmup"
    )


def test_action_tooltip_includes_human_keyboard_shortcuts():
    """GTK toolbar tooltips expose shortcuts without raw accelerator syntax."""
    assert face_view.action_tooltip("start", "Start voice runtime") == (
        "Start voice runtime (Ctrl+Enter)"
    )
    assert face_view.action_tooltip("back", "Go back") == "Go back (Esc, Alt+Left)"


def test_action_tooltip_humanizes_punctuation_shortcuts():
    """GTK toolbar tooltips show normal punctuation for punctuation keys."""
    assert face_view.action_tooltip("stop", "Stop voice runtime") == ("Stop voice runtime (Ctrl+.)")


def test_tool_panel_tooltip_includes_progress_percentage():
    """GTK canvas hover text should make progress bars inspectable."""
    assert (
        face_view.tool_panel_tooltip(
            face_view.ToolPanel(
                title="Pomodoro",
                summary="Work 10:00 | Break 05:00",
                detail_lines=("Running work session",),
                progress=0.6,
            )
        )
        == "Pomodoro\nWork 10:00 | Break 05:00\nRunning work session\nProgress: 60%"
    )


def test_canvas_tooltip_expands_active_state_badge_overflow():
    """GTK canvas hover text should expose active states hidden behind badge overflow."""
    tooltip = face_view.canvas_tooltip(
        {
            "active_view": "idle",
            "status_text": "Ready",
            "active_states": ["timer", "idea", "todo_list", "calendar", "voice_note"],
        },
        {"state": "running"},
    )

    assert tooltip == (
        "Listening\n"
        "Ready\n"
        "Runtime: Running\n"
        "Badges: Listening | Runtime: Running | "
        "Active: Timer, Idea, Todo List, Calendar, Voice Note"
    )


def test_canvas_tooltip_expands_idle_runtime_detail():
    """GTK canvas hover text should keep full idle runtime details inspectable."""
    tooltip = face_view.canvas_tooltip(
        {"active_view": "idle", "status_text": "Ready"},
        {"state": "running", "model": "qwen3-extra-long-model-name"},
    )

    assert tooltip == (
        "Listening\n"
        "Ready\n"
        "Runtime: Running - qwen3-extra-long-model-name\n"
        "Badges: Listening | Runtime: Running | Model: qwen3-extra-long-model-name"
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
    assert face_view.control_state({"state": " stopped "}) == {
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
    assert face_view.control_state(
        face_view.offline_runtime_state(ConnectionError("connection refused"))
    ) == {
        "start": False,
        "stop": False,
        "preload": False,
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
        "active_states_tooltip": "Active: Timer, Idea",
    }
    assert face_view.header_state({"view_stack": ["idle"], "active_states": []}) == {
        "can_go_back": False,
        "active_states_label": "",
        "active_states_tooltip": "",
    }
    assert face_view.header_state({"view_stack": ["idle"], "active_states": [None, "   "]}) == {
        "can_go_back": False,
        "active_states_label": "",
        "active_states_tooltip": "",
    }
    assert face_view.header_state(
        {
            "view_stack": ["idle"],
            "active_states": ["timer", "idea", "todo_list", "calendar", "voice_note"],
        }
    ) == {
        "can_go_back": False,
        "active_states_label": "Active: Timer, Idea, Todo List +2",
        "active_states_tooltip": "Active: Timer, Idea, Todo List, Calendar, Voice Note",
    }


def test_header_state_ignores_malformed_navigation_values():
    """Malformed GTK navigation values should not enable bogus header controls."""
    assert face_view.header_state({"view_stack": "idle", "active_states": "timer"}) == {
        "can_go_back": False,
        "active_states_label": "",
        "active_states_tooltip": "",
    }


def test_gtk_labels_humanize_hyphenated_api_values():
    """GTK labels render hyphenated API values as normal words."""
    assert face_view.header_state({"view_stack": ["idle"], "active_states": ["voice-note"]}) == {
        "can_go_back": False,
        "active_states_label": "Active: Voice Note",
        "active_states_tooltip": "Active: Voice Note",
    }
    assert face_view.tool_panel(
        {"active_view": "todo_list", "todo_filter_status": "in-progress"},
        {"state": "running"},
    ).detail_lines == ("Filter: In Progress",)


def test_header_state_deduplicates_active_state_labels():
    """Duplicate GTK active states should not waste header or badge space."""
    assert face_view.header_state(
        {"view_stack": ["idle"], "active_states": ["timer", " Timer ", "idea", "IDEA"]}
    ) == {
        "can_go_back": False,
        "active_states_label": "Active: Timer, Idea",
        "active_states_tooltip": "Active: Timer, Idea",
    }


def test_header_state_omits_current_view_from_active_states():
    """GTK active-state labels should show concurrent work, not repeat the current view."""
    ui_state = {
        "active_view": "todo_list",
        "view_stack": ["idle", "todo_list"],
        "active_states": ["todo_list", "timer"],
    }

    assert face_view.header_state(ui_state) == {
        "can_go_back": True,
        "active_states_label": "Active: Timer",
        "active_states_tooltip": "Active: Timer",
    }
    assert (
        face_view.active_states_status_class(
            {"active_view": "todo_list", "active_states": ["todo_list"]}
        )
        == "status-neutral"
    )
    assert face_view.status_badges(ui_state, {"state": "running"}) == (
        "Todos",
        "Runtime: Running",
        "Active: Timer",
    )


def test_header_state_omits_current_view_aliases_from_active_states():
    """GTK active-state labels should not repeat current tools with alternate names."""
    assert face_view.header_state(
        {
            "active_view": "pomodoro",
            "view_stack": ["idle", "pomodoro"],
            "active_states": ["timer", "calendar"],
        }
    ) == {
        "can_go_back": True,
        "active_states_label": "Active: Calendar",
        "active_states_tooltip": "Active: Calendar",
    }
    assert face_view.header_state(
        {
            "active_view": "todo_list",
            "view_stack": ["idle", "todo_list"],
            "active_states": ["todo", "timer"],
        }
    ) == {
        "can_go_back": True,
        "active_states_label": "Active: Timer",
        "active_states_tooltip": "Active: Timer",
    }


def test_header_state_omits_calendar_event_aliases_from_active_states():
    """GTK Calendar should not show its event aliases as concurrent work."""
    ui_state = {
        "active_view": "calendar",
        "view_stack": ["idle", "calendar"],
        "active_states": ["events", "timer"],
    }

    assert face_view.header_state(ui_state) == {
        "can_go_back": True,
        "active_states_label": "Active: Timer",
        "active_states_tooltip": "Active: Timer",
    }
    assert face_view.status_badges(ui_state, {"state": "running"}) == (
        "Calendar",
        "Runtime: Running",
        "Active: Timer",
    )


def test_active_states_status_class_marks_concurrent_work():
    """GTK active-states label gets emphasis only when work is active."""
    assert (
        face_view.active_states_status_class({"active_states": ["timer", "idea"]})
        == "status-pending"
    )
    assert face_view.active_states_status_class({"active_states": []}) == "status-neutral"
    assert face_view.active_states_status_class({"active_states": [None, "   "]}) == (
        "status-neutral"
    )
    assert face_view.active_states_status_class({}) == "status-neutral"
    assert face_view.active_states_status_class({"active_states": "timer"}) == "status-neutral"


def test_status_badges_summarize_current_surface_state():
    """Canvas status badges make key context visible away from the dense header."""
    assert face_view.status_badges(
        {"active_view": "pomodoro", "active_states": ["timer", "idea"]},
        {"state": "running", "model": "qwen3"},
    ) == ("Pomodoro", "Runtime: Running", "Model: qwen3", "Active: Idea")
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
    assert face_view.runtime_status_class({"state": " running "}) == "status-ok"
    assert face_view.runtime_status_class({"state": "running", "error": "   "}) == "status-ok"
    assert face_view.runtime_status_class({"state": "loaded"}) == "status-ok"
    assert face_view.runtime_status_class({"state": "loading"}) == "status-pending"
    assert face_view.runtime_status_class({"state": "error"}) == "status-error"
    assert face_view.runtime_status_class({}) == "status-pending"


def test_action_status_class_marks_response_severity():
    """GTK action feedback label mirrors success, progress, and failure."""
    assert face_view.action_status_class({"state": "running"}) == "status-ok"
    assert face_view.action_status_class({"state": "running", "error": "   "}) == "status-ok"
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


def test_compact_status_badges_collapses_overflow_badges():
    """GTK canvas badges stay in a bounded cluster on narrow windows."""
    assert face_view.compact_status_badges(
        (
            "Calendar",
            "Runtime: Running",
            "Model: qwen3",
            "Active: Timer, Idea",
            "Error: microphone unavailable",
        ),
        max_chars=24,
        max_badges=3,
    ) == ("Calendar", "Runtime: Running", "+3 more")


def test_compact_status_badges_keeps_primary_context_with_one_slot():
    """GTK canvas badges should keep the current surface visible on very narrow windows."""
    assert face_view.compact_status_badges(
        (
            "Calendar",
            "Runtime: Running",
            "Model: qwen3",
            "Active: Timer, Idea",
            "Error: microphone unavailable",
        ),
        max_chars=24,
        max_badges=1,
    ) == ("Calendar +4",)


def test_compact_status_badges_preserves_one_slot_overflow_count_when_clipped():
    """Very narrow primary overflow badges should keep the hidden badge count visible."""
    assert face_view.compact_status_badges(
        (
            "Calendar",
            "Runtime: Running",
            "Model: qwen3",
        ),
        max_chars=10,
        max_badges=1,
    ) == ("Cale... +2",)


def test_compact_status_badges_keeps_runtime_state_readable_when_clipped():
    """Very narrow runtime badges should keep the status word and tone readable."""
    offline_badge = face_view.compact_status_badges(
        ("Runtime: Offline", "Error: backend unavailable"),
        max_chars=12,
        max_badges=1,
    )[0]
    running_badge = face_view.compact_status_badges(
        ("Runtime: Running", "Model: qwen3"),
        max_chars=12,
        max_badges=1,
    )[0]

    assert offline_badge == "Offline +1"
    assert face_view.status_badge_tone(offline_badge) == "error"
    assert running_badge == "Running +1"
    assert face_view.status_badge_tone(running_badge) == "ok"


def test_compact_status_badges_keeps_active_state_readable_when_clipped():
    """Very narrow active-state badges should keep active work visible."""
    active_badge = face_view.compact_status_badges(
        ("Active: Timer, Idea", "Runtime: Running"),
        max_chars=10,
        max_badges=1,
    )[0]

    assert active_badge == "Active +1"
    assert face_view.status_badge_tone(active_badge) == "pending"


def test_compact_status_badges_keeps_model_badges_readable_when_clipped():
    """Very narrow model badges should keep the badge type visible."""
    assert face_view.compact_status_badges(
        ("Model: qwen3", "Runtime: Running"),
        max_chars=12,
        max_badges=1,
    ) == ("Model +1",)


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


def test_status_badge_tone_preserves_compacted_primary_severity():
    """Overflow badge labels should keep the severity of their primary context."""
    assert face_view.status_badge_tone("Error +4") == "error"
    assert face_view.status_badge_tone("Runtime: Offline +2") == "error"
    assert face_view.status_badge_tone("Runtime: Running +2") == "ok"
    assert face_view.status_badge_tone("Loading +3") == "pending"


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

    padded_phase_panel = face_view.tool_panel(
        {
            "active_view": "pomodoro",
            "timer_state": {
                "status": "running",
                "phase": " work ",
                "work_duration_minutes": 25,
                "break_duration_minutes": 5,
                "remaining_work_seconds": 600,
                "remaining_break_seconds": 300,
            },
        },
        {"state": "running"},
    )

    assert padded_phase_panel.detail_lines == ("Running work session", "Break queued for 05:00")
    assert padded_phase_panel.progress == 0.6

    blank_phase_panel = face_view.tool_panel(
        {
            "active_view": "pomodoro",
            "timer_state": {
                "status": "running",
                "phase": "   ",
                "work_duration_minutes": 25,
                "break_duration_minutes": 5,
                "remaining_work_seconds": 600,
                "remaining_break_seconds": 300,
            },
        },
        {"state": "running"},
    )

    assert blank_phase_panel.detail_lines == ("Running work session", "Break queued for 05:00")
    assert blank_phase_panel.progress == 0.6


def test_tool_panel_humanizes_pomodoro_break_phases():
    """Pomodoro detail text should not expose raw phase identifiers."""
    panel = face_view.tool_panel(
        {
            "active_view": "pomodoro",
            "timer_state": {
                "status": "running",
                "phase": "long_break",
                "work_duration_minutes": 25,
                "break_duration_minutes": 15,
                "remaining_work_seconds": 0,
                "remaining_break_seconds": 600,
            },
        },
        {"state": "running"},
    )

    assert panel.summary == "Long Break 10:00 | Work ready"
    assert panel.detail_lines == (
        "Running Long Break session",
        "Next work block after 10:00",
    )
    assert panel.progress == 0.333


def test_tool_panel_tolerates_blank_pomodoro_timer_numbers():
    """Blank Pomodoro timer numbers should not crash the GTK panel."""
    panel = face_view.tool_panel(
        {
            "active_view": "pomodoro",
            "timer_state": {
                "status": "running",
                "phase": "work",
                "work_duration_minutes": " ",
                "break_duration_minutes": None,
                "remaining_work_seconds": "",
                "remaining_break_seconds": " ",
            },
        },
        {"state": "running"},
    )

    assert panel.summary == "Work 00:00 | Break 00:00"
    assert panel.detail_lines == ("Running work session", "Break queued for 00:00")
    assert panel.progress is None


def test_tool_panel_omits_pomodoro_progress_when_remaining_time_is_missing():
    """Pomodoro progress should not look complete when remaining seconds are absent."""
    panel = face_view.tool_panel(
        {
            "active_view": "pomodoro",
            "timer_state": {
                "status": "running",
                "phase": "work",
                "work_duration_minutes": 25,
                "break_duration_minutes": 5,
            },
        },
        {"state": "running"},
    )

    assert panel.summary == "Work 00:00 | Break 00:00"
    assert panel.detail_lines == ("Running work session", "Break queued for 00:00")
    assert panel.progress is None


def test_tool_panel_marks_missing_pomodoro_timer_state_ready():
    """Pomodoro panel should not render zeroed timers before state arrives."""
    panel = face_view.tool_panel({"active_view": "pomodoro"}, {"state": "running"})

    assert panel.summary == "Timer ready"
    assert panel.detail_lines == ("Ready to start",)
    assert panel.progress is None


def test_view_summary_marks_malformed_pomodoro_timer_state_ready():
    """Malformed Pomodoro timer state should not render fake zeroed timers."""
    assert (
        view_summary({"active_view": "pomodoro", "timer_state": "bad"}, {"state": "running"})
        == "Timer ready"
    )


def test_tool_panel_marks_malformed_pomodoro_timer_state_ready():
    """Malformed Pomodoro timer state should render the same ready panel as missing state."""
    panel = face_view.tool_panel(
        {"active_view": "pomodoro", "timer_state": "bad"},
        {"state": "running"},
    )

    assert panel.summary == "Timer ready"
    assert panel.detail_lines == ("Ready to start",)
    assert panel.progress is None


def test_tool_panel_uses_readable_pomodoro_status_fallback():
    """Blank Pomodoro status should not render a broken detail label."""
    panel = face_view.tool_panel(
        {
            "active_view": "pomodoro",
            "timer_state": {
                "status": "   ",
                "phase": "work",
                "work_duration_minutes": 25,
                "break_duration_minutes": 5,
                "remaining_work_seconds": 600,
                "remaining_break_seconds": 300,
            },
        },
        {"state": "running"},
    )

    assert panel.detail_lines == ("Timer work session", "Break queued for 05:00")


def test_tool_panel_handles_float_pomodoro_timer_numbers():
    """Float Pomodoro timer values should render as real remaining time."""
    panel = face_view.tool_panel(
        {
            "active_view": "pomodoro",
            "timer_state": {
                "status": "running",
                "phase": "work",
                "work_duration_minutes": 25.0,
                "break_duration_minutes": 5.0,
                "remaining_work_seconds": 600.0,
                "remaining_break_seconds": 300.0,
            },
        },
        {"state": "running"},
    )

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


def test_tool_panel_labels_active_view_backend_outages_as_offline():
    """Active GTK panels should use the same offline language as the header."""
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
        face_view.offline_runtime_state(ConnectionError("connection refused")),
    )

    assert panel.detail_lines == (
        "Running work session",
        "Break queued for 05:00",
        "Runtime: Offline",
    )


def test_tool_panel_omits_duplicate_unknown_view_runtime_fallback_details():
    """Unknown GTK panels should not repeat runtime fallback text."""
    offline_panel = face_view.tool_panel(
        {"active_view": "voice_note", "status_text": "   "},
        face_view.offline_runtime_state(ConnectionError("connection refused")),
    )
    loading_panel = face_view.tool_panel(
        {"active_view": "voice_note", "status_text": "   "},
        {"state": "loading"},
    )
    error_panel = face_view.tool_panel(
        {"active_view": "voice_note", "status_text": "   "},
        {"state": "error", "error": "microphone unavailable"},
    )

    assert offline_panel.summary == "Runtime: Offline"
    assert offline_panel.detail_lines == ()
    assert loading_panel.summary == "Runtime: Loading"
    assert loading_panel.detail_lines == ()
    assert error_panel.summary == "Runtime: Error"
    assert error_panel.detail_lines == ("Runtime error: microphone unavailable",)


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
    assert panel.detail_lines == ("Runtime: Error - qwen3",)
    offline_panel = face_view.tool_panel(
        {"active_view": "idle", "status_text": "Waiting"},
        face_view.offline_runtime_state(ConnectionError("connection refused")),
    )
    assert offline_panel.summary == "Backend offline"
    assert offline_panel.detail_lines == ("Runtime: Offline",)


def test_tool_panel_shows_unknown_idle_runtime_detail():
    """Idle GTK panel should not look empty while runtime state is unknown."""
    panel = face_view.tool_panel({"active_view": "idle", "status_text": ""}, {})

    assert panel.title == "Listening"
    assert panel.summary == "Unknown"
    assert panel.detail_lines == ("Runtime: Unknown",)


def test_tool_panel_omits_duplicate_idle_error_detail():
    """Idle error panels should not repeat the headline as a detail line."""
    panel = face_view.tool_panel(
        {"active_view": "idle", "status_text": "Waiting"},
        {"state": "error", "model": "qwen3", "error": "microphone unavailable"},
    )
    offline_panel = face_view.tool_panel(
        {"active_view": "idle", "status_text": "Waiting"},
        face_view.offline_runtime_state(ConnectionError("connection refused")),
    )

    assert panel.summary == "microphone unavailable"
    assert panel.detail_lines == ("Runtime: Error - qwen3",)
    assert offline_panel.summary == "Backend offline"
    assert offline_panel.detail_lines == ("Runtime: Offline",)


def test_tool_panel_treats_blank_active_view_as_idle():
    """Blank GTK active view should render idle panel details."""
    panel = face_view.tool_panel(
        {"active_view": "   ", "status_text": "Waiting"},
        {"state": "error", "model": "qwen3", "error": "microphone unavailable"},
    )

    assert panel.title == "Listening"
    assert panel.summary == "microphone unavailable"
    assert panel.detail_lines == ("Runtime: Error - qwen3",)


def test_active_view_labels_ignore_api_casing():
    """GTK active view casing should not change user-facing labels or colors."""
    ui_state = {
        "active_view": " POMODORO ",
        "timer_state": {
            "status": "running",
            "phase": "work",
            "work_duration_minutes": 25,
            "remaining_work_seconds": 1200,
            "remaining_break_seconds": 300,
        },
    }
    runtime = {"state": "running", "model": "qwen3"}

    assert face_view.view_summary(ui_state, runtime) == "Work 20:00 | Break 05:00"
    assert face_view.header_view_title(ui_state, runtime) == "Pomodoro"
    assert face_view.surface_accent(ui_state, runtime) == (0.95, 0.39, 0.32)
    assert face_view.tool_panel(ui_state, runtime) == face_view.ToolPanel(
        title="Pomodoro",
        summary="Work 20:00 | Break 05:00",
        detail_lines=("Running work session", "Break queued for 05:00"),
        progress=0.2,
    )


def test_active_view_labels_route_hyphenated_known_tool_names():
    """GTK known tool views should tolerate hyphenated API names."""
    panel = face_view.tool_panel(
        {
            "active_view": "todo-list",
            "status_text": "Todos",
            "active_todo_title": "Polish GTK routing",
        },
        {"state": "running"},
    )

    assert (
        face_view.view_summary(
            {
                "active_view": "todo-list",
                "status_text": "Todos",
                "active_todo_title": "Polish GTK routing",
            },
            {"state": "running"},
        )
        == "Polish GTK routing"
    )
    assert face_view.header_view_title({"active_view": "todo-list"}, {"state": "running"}) == (
        "Todos"
    )
    assert face_view.status_badges({"active_view": "todo-list"}, {"state": "running"}) == (
        "Todos",
        "Runtime: Running",
    )
    assert panel == face_view.ToolPanel(
        title="Todos",
        summary="Polish GTK routing",
        detail_lines=(),
    )


def test_active_view_labels_route_compact_known_tool_aliases():
    """GTK known tool views should tolerate compact API aliases."""
    ui_state = {
        "active_view": "todo",
        "status_text": "Todos",
        "active_todo_title": "Polish GTK aliases",
    }

    assert face_view.view_summary(ui_state, {"state": "running"}) == "Polish GTK aliases"
    assert face_view.header_view_title(ui_state, {"state": "running"}) == "Todos"
    assert face_view.tool_panel(ui_state, {"state": "running"}) == face_view.ToolPanel(
        title="Todos",
        summary="Polish GTK aliases",
        detail_lines=(),
    )


def test_active_view_labels_route_timer_and_idea_aliases():
    """GTK known tool views should tolerate timer and idea API aliases."""
    timer_state = {
        "active_view": "timer",
        "timer_state": {
            "status": "running",
            "phase": "work",
            "work_duration_minutes": 25,
            "break_duration_minutes": 5,
            "remaining_work_seconds": 1200,
            "remaining_break_seconds": 300,
        },
    }
    idea_state = {
        "active_view": "idea",
        "idea_view": {"draft_text": "Polish GTK aliases"},
    }

    assert face_view.view_summary(timer_state, {"state": "running"}) == "Work 20:00 | Break 05:00"
    assert face_view.header_view_title(timer_state, {"state": "running"}) == "Pomodoro"
    assert face_view.tool_panel(idea_state, {"state": "running"}) == face_view.ToolPanel(
        title="Idea",
        summary="Polish GTK aliases",
        detail_lines=("Draft in progress",),
    )


def test_active_view_labels_route_calendar_event_aliases():
    """GTK Calendar should tolerate event-oriented API view aliases."""
    ui_state = {
        "active_view": "events",
        "status_text": "Events",
        "active_event_title": "Planning review",
    }

    assert face_view.view_summary(ui_state, {"state": "running"}) == "Planning review"
    assert face_view.header_view_title(ui_state, {"state": "running"}) == "Calendar"
    assert face_view.tool_panel(ui_state, {"state": "running"}) == face_view.ToolPanel(
        title="Calendar",
        summary="Planning review",
        detail_lines=(),
    )


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
    assert (
        face_view.tool_panel(
            {
                "active_view": "calendar",
                "active_event_id": "event:weekly_robotics_seminar_2026_01_27",
                "active_event_title": "Weekly robotics seminar",
            },
            {"state": "running"},
        ).detail_lines
        == ()
    )


def test_tool_panel_promotes_active_todo_title_to_summary():
    """Todo panel should use the active todo title as the headline when status is generic."""
    panel = face_view.tool_panel(
        {
            "active_view": "todo_list",
            "status_text": "Todos",
            "active_todo_title": "Polish GTK",
            "todo_filter_status": "in_progress",
        },
        {"state": "running"},
    )

    assert panel.summary == "Polish GTK"
    assert panel.detail_lines == ("Filter: In Progress",)


def test_tool_panel_omits_todo_id_when_active_title_is_headline():
    """Todo panel should not show a fallback ID when the title is already visible."""
    panel = face_view.tool_panel(
        {
            "active_view": "todo_list",
            "status_text": "Todos",
            "active_todo_id": "todo:polish_gtk_header",
            "active_todo_title": "Polish GTK",
            "todo_filter_status": "in_progress",
        },
        {"state": "running"},
    )

    assert panel.summary == "Polish GTK"
    assert panel.detail_lines == ("Filter: In Progress",)


def test_tool_panel_omits_duplicate_calendar_event_title_detail():
    """Calendar panel details should not repeat the event title headline."""
    panel = face_view.tool_panel(
        {
            "active_view": "calendar",
            "status_text": "Calendar",
            "calendar_selected_date": "2026-08-05",
            "active_event_title": "Weekly robotics seminar",
        },
        {"state": "running"},
    )

    assert panel.summary == "Weekly robotics seminar"
    assert panel.detail_lines == ("Date: Aug 5, 2026",)


def test_tool_panel_omits_duplicate_calendar_event_title_without_other_details():
    """Calendar panel should not repeat the event title as its only detail line."""
    panel = face_view.tool_panel(
        {
            "active_view": "calendar",
            "status_text": "Calendar",
            "active_event_title": "Weekly robotics seminar",
        },
        {"state": "running"},
    )

    assert panel.summary == "Weekly robotics seminar"
    assert panel.detail_lines == ()


def test_tool_panel_marks_active_calendar_event_ids_as_active():
    """Calendar panel should not show active event IDs under a generic headline."""
    panel = face_view.tool_panel(
        {
            "active_view": "calendar",
            "active_event_id": "event:weekly_robotics_seminar_2026_01_27",
        },
        {"state": "running"},
    )

    assert panel.summary == "Active event"
    assert panel.detail_lines == ("Event: weekly_r",)


def test_tool_panel_marks_active_idea_without_draft_as_active():
    """Ideas panel should not describe active ideas as already captured."""
    panel = face_view.tool_panel(
        {
            "active_view": "ideas",
            "idea_view": {
                "is_active": True,
                "active_idea_id": "idea:capture_voice_routine_2026_08_06",
            },
        },
        {"state": "running"},
    )

    assert panel.summary == "Active idea"
    assert panel.detail_lines == ("ID: capture_",)


def test_tool_panel_simplifies_scoped_fallback_identifiers():
    """Fallback GTK panel identifiers show the useful scoped ID segment."""
    idea_panel = face_view.tool_panel(
        {
            "active_view": "ideas",
            "idea_view": {"active_idea_id": "idea:capture_voice_routine_2026_08_06"},
        },
        {"state": "running"},
    )

    assert idea_panel.summary == "Active idea"
    assert idea_panel.detail_lines == ("ID: capture_",)
    assert face_view.tool_panel(
        {
            "active_view": "todo_list",
            "active_todo_id": "todo:book_doctor_appointment_2026_08_06",
            "selected_category_id": "category:health_admin_2026",
        },
        {"state": "running"},
    ).detail_lines == ("Active: book_doc", "Category: health_a")


def test_tool_panel_marks_idea_drafts_in_progress():
    """GTK Ideas panel should distinguish draft text from empty capture state."""
    panel = face_view.tool_panel(
        {
            "active_view": "ideas",
            "idea_view": {"draft_text": "Ship the GTK face"},
        },
        {"state": "running"},
    )

    assert panel.summary == "Ship the GTK face"
    assert panel.detail_lines == ("Draft in progress",)


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


def test_tool_panel_tolerates_non_mapping_idea_state():
    """Malformed idea state should render the Ideas fallback panel."""
    panel = face_view.tool_panel(
        {"active_view": "ideas", "status_text": "   ", "idea_view": "bad"},
        {"state": "running"},
    )

    assert panel.summary == "Idea captured"
    assert panel.detail_lines == ("Ready to capture",)


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
            "calendar_selected_date": "   ",
            "calendar_filter_type": "   ",
        },
        {"state": "running"},
    )

    assert calendar_panel.summary == "Upcoming"
    assert calendar_panel.detail_lines == ()
