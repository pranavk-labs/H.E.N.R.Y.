"""Pure helpers for the GTK adaptive face view."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EyeGeometry:
    """Ellipse geometry for one eye."""

    center_x: float
    center_y: float
    radius_x: float
    radius_y: float


@dataclass(frozen=True)
class MouthGeometry:
    """Arc geometry for the mouth."""

    center_x: float
    center_y: float
    width: float
    height: float


@dataclass(frozen=True)
class FaceGeometry:
    """Geometry needed to draw HENRY's legacy face."""

    center_x: float
    center_y: float
    base_radius: float
    line_width: float
    left_eye: EyeGeometry
    right_eye: EyeGeometry
    mouth: MouthGeometry


@dataclass(frozen=True)
class ToolPanel:
    """Text and progress model for one adaptive GTK tool screen."""

    title: str
    summary: str
    detail_lines: tuple[str, ...] = ()
    progress: float | None = None


def sleepiness_for_elapsed(
    elapsed_seconds: float,
    *,
    happy_seconds: int,
    neutral_seconds: int,
    sleepy_seconds: int,
) -> int:
    """Return legacy sleepiness level for time since interaction."""
    if elapsed_seconds < happy_seconds:
        return 0
    if elapsed_seconds < neutral_seconds:
        return 1
    if elapsed_seconds < sleepy_seconds:
        return 2
    return 3


def face_geometry(
    *,
    width: int,
    height: int,
    phase: float,
    sleepiness_level: int,
    blink_scale: float = 1.0,
) -> FaceGeometry:
    """Build responsive face geometry matching the old Tkinter proportions."""
    center_x = width / 2
    center_y = height / 2
    size = min(width * 0.4, height * 0.82)
    base_radius = size / 2
    level = max(0, min(sleepiness_level, 3))

    vertical_amplitude = [10.0, 7.0, 4.0, 2.0][level]
    horizontal_amplitude = [5.0, 3.0, 2.0, 1.0][level]
    current_x = center_x + math.sin(phase * 0.7) * horizontal_amplitude
    current_y = center_y + math.sin(phase) * vertical_amplitude

    eye_multiplier = [0.3, 0.25, 0.2, 0.15][level]
    eye_y_multiplier = [-0.15, -0.12, -0.1, -0.08][level]
    eye_x_offset = base_radius * 0.4
    eye_size = base_radius * eye_multiplier
    eye_y = current_y + base_radius * eye_y_multiplier
    eye_radius_y = eye_size * blink_scale

    mouth_y = current_y + base_radius * 0.25
    mouth_width = base_radius * 1.4
    mouth_height = base_radius * 0.6

    return FaceGeometry(
        center_x=center_x,
        center_y=center_y,
        base_radius=base_radius,
        line_width=max(4, width * 0.01),
        left_eye=EyeGeometry(
            center_x=current_x - eye_x_offset,
            center_y=eye_y,
            radius_x=eye_size,
            radius_y=eye_radius_y,
        ),
        right_eye=EyeGeometry(
            center_x=current_x + eye_x_offset,
            center_y=eye_y,
            radius_x=eye_size,
            radius_y=eye_radius_y,
        ),
        mouth=MouthGeometry(
            center_x=current_x,
            center_y=mouth_y,
            width=mouth_width,
            height=mouth_height,
        ),
    )


def _format_seconds(total_seconds: int) -> str:
    minutes = max(0, total_seconds) // 60
    seconds = max(0, total_seconds) % 60
    return f"{minutes:02d}:{seconds:02d}"


def _humanize(value: Any) -> str:
    """Convert compact API values into short labels."""
    return str(value or "").replace("_", " ").strip().title()


def view_summary(ui_state: dict[str, Any], runtime: dict[str, Any]) -> str:
    """Return the focused overlay text for the active adaptive view."""
    active_view = ui_state.get("active_view", "idle")
    status_text = str(ui_state.get("status_text") or "")
    if active_view == "idle":
        return status_text

    if active_view == "pomodoro":
        timer = ui_state.get("timer_state") or {}
        work = _format_seconds(int(timer.get("remaining_work_seconds", 0)))
        rest = _format_seconds(int(timer.get("remaining_break_seconds", 0)))
        return f"Work {work} | Break {rest}"

    if active_view == "ideas":
        idea = ui_state.get("idea_view") or {}
        return str(idea.get("draft_text") or status_text or "Idea captured")

    if active_view == "todo_list":
        return status_text or "Todos"

    if active_view == "calendar":
        return status_text or "Calendar"

    return status_text or f"Runtime {runtime.get('state', 'unknown')}"


def view_title(active_view: str) -> str:
    """Return a concise human-facing title for the active GTK view."""
    labels = {
        "idle": "Listening",
        "pomodoro": "Pomodoro",
        "ideas": "Idea",
        "todo_list": "Todos",
        "calendar": "Calendar",
    }
    return labels.get(active_view, active_view.replace("_", " ").title())


def view_accent(active_view: str) -> tuple[float, float, float]:
    """Return stable RGB accent colors for the active GTK view."""
    accents = {
        "idle": (0.31, 0.78, 0.47),
        "pomodoro": (0.95, 0.39, 0.32),
        "ideas": (0.35, 0.63, 0.94),
        "todo_list": (0.91, 0.73, 0.33),
        "calendar": (0.65, 0.55, 0.95),
    }
    return accents.get(active_view, (0.72, 0.74, 0.78))


def runtime_summary(runtime: dict[str, Any]) -> str:
    """Return a compact runtime summary for the GTK header."""
    state = str(runtime.get("state") or "unknown")
    label = state.replace("_", " ").title()
    model = str(runtime.get("model") or "").strip()
    if model:
        return f"{label} - {model}"
    return label


def control_state(runtime: dict[str, Any]) -> dict[str, bool]:
    """Return which runtime controls should be enabled for the current state."""
    state = str(runtime.get("state") or "unknown").lower()
    if state in {"starting", "stopping", "loading", "unloading"}:
        return {"start": False, "stop": False, "preload": False, "unload": False}
    if state == "running":
        return {"start": False, "stop": True, "preload": True, "unload": True}
    if state == "stopped":
        return {"start": True, "stop": False, "preload": True, "unload": False}
    return {"start": False, "stop": False, "preload": False, "unload": False}


def tool_panel(ui_state: dict[str, Any], runtime: dict[str, Any]) -> ToolPanel:
    """Build the richer content model rendered by the GTK canvas."""
    active_view = str(ui_state.get("active_view", "idle"))
    summary = view_summary(ui_state, runtime)
    details: list[str] = []
    progress: float | None = None

    if active_view == "pomodoro":
        timer = ui_state.get("timer_state") or {}
        status = _humanize(timer.get("status") or "timer")
        phase = str(timer.get("phase") or "work").lower()
        work_remaining = int(timer.get("remaining_work_seconds", 0))
        break_remaining = int(timer.get("remaining_break_seconds", 0))
        details.append(f"{status} {phase} session")
        if phase == "work":
            details.append(f"Break queued for {_format_seconds(break_remaining)}")
            total = int(timer.get("work_duration_minutes", 0)) * 60
            remaining = work_remaining
        else:
            details.append(f"Next work block after {_format_seconds(break_remaining)}")
            total = int(timer.get("break_duration_minutes", 0)) * 60
            remaining = break_remaining
        if total > 0:
            progress = max(0.0, min(1.0, round((total - remaining) / total, 3)))

    elif active_view == "ideas":
        idea = ui_state.get("idea_view") or {}
        if idea.get("is_active"):
            details.append("Active idea")
        if idea.get("active_idea_id"):
            details.append(f"ID: {str(idea['active_idea_id'])[:8]}")
        if not details:
            details.append("Ready to capture")

    elif active_view == "todo_list":
        active_title = str(ui_state.get("active_todo_title") or "").strip()
        if active_title:
            details.append(f"Active: {active_title}")
        elif ui_state.get("active_todo_id"):
            details.append(f"Active todo: {str(ui_state['active_todo_id'])[:8]}")
        if ui_state.get("todo_filter_status"):
            details.append(f"Filter: {_humanize(ui_state['todo_filter_status'])}")
        if ui_state.get("selected_category_id"):
            details.append(f"Category: {str(ui_state['selected_category_id'])[:8]}")

    elif active_view == "calendar":
        mode = _humanize(ui_state.get("calendar_view_mode") or "upcoming")
        summary = summary if summary != "Calendar" else mode
        if ui_state.get("calendar_selected_date"):
            details.append(f"Date: {ui_state['calendar_selected_date']}")
        if ui_state.get("calendar_filter_type"):
            details.append(f"Type: {_humanize(ui_state['calendar_filter_type'])}")
        if ui_state.get("active_event_id"):
            details.append(f"Event: {str(ui_state['active_event_id'])[:8]}")

    elif active_view == "idle":
        if runtime:
            details.append(runtime_summary(runtime))

    return ToolPanel(
        title=view_title(active_view),
        summary=summary,
        detail_lines=tuple(details[:3]),
        progress=progress,
    )
