"""Tests for GTK adaptive face view helpers."""

from __future__ import annotations

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
