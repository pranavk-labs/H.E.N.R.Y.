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


def offline_runtime_state(error: Any) -> dict[str, str]:
    """Return a fresh GTK runtime state for backend outages."""
    message = str(error or "").strip() or "unknown error"
    return {"state": "error", "error": f"Backend unavailable: {message}"}


def model_override(raw_value: Any) -> str | None:
    """Return a clean model override from GTK entry text."""
    value = str(raw_value or "").strip()
    return value or None


def model_entry_text(current_text: Any, runtime: dict[str, Any], *, user_edited: bool) -> str:
    """Return the model entry text after syncing with runtime status."""
    if user_edited:
        return str(current_text or "")
    return str(runtime.get("model") or "")


def model_entry_user_edited_after_action(
    action_name: str,
    response: dict[str, Any],
    *,
    was_user_edited: bool,
) -> bool:
    """Return whether GTK should keep protecting user-entered model text."""
    if response.get("error"):
        return was_user_edited
    if action_name in {"preload", "unload"}:
        return False
    return was_user_edited


def model_entry_user_edited_after_change(
    raw_value: Any,
    *,
    was_syncing: bool,
    was_user_edited: bool,
) -> bool:
    """Return model entry dirty state after a GTK text change."""
    if was_syncing:
        return was_user_edited
    return bool(str(raw_value or "").strip())


def action_feedback(action_name: str, response: dict[str, Any]) -> str:
    """Turn an action API response into concise GTK feedback."""
    action_label = _humanize(action_name)
    if response.get("error"):
        return f"{action_label}: {response['error']}"
    state = _humanize(response.get("state") or "complete")
    model = str(response.get("model") or "").strip()
    suffix = f" {model}" if model else ""
    return f"{action_label}: {state}{suffix}"


def control_state(runtime: dict[str, Any]) -> dict[str, bool]:
    """Return which runtime controls should be enabled for the current state."""
    state = str(runtime.get("state") or "unknown").lower()
    if state in {"starting", "stopping", "loading", "unloading"}:
        return {"start": False, "stop": False, "preload": False, "unload": False}
    if state == "running":
        return {"start": False, "stop": True, "preload": True, "unload": True}
    if state == "stopped":
        return {"start": True, "stop": False, "preload": True, "unload": False}
    if state == "loaded":
        return {"start": True, "stop": False, "preload": True, "unload": True}
    if state == "unloaded":
        return {"start": True, "stop": False, "preload": True, "unload": False}
    if state == "error":
        has_model = bool(str(runtime.get("model") or "").strip())
        return {"start": True, "stop": False, "preload": True, "unload": has_model}
    return {"start": False, "stop": False, "preload": False, "unload": False}


def header_state(ui_state: dict[str, Any]) -> dict[str, Any]:
    """Return GTK header navigation and concurrent-state labels."""
    view_stack = ui_state.get("view_stack") or ["idle"]
    active_states = [
        _humanize(state) for state in (ui_state.get("active_states") or []) if str(state).strip()
    ]
    return {
        "can_go_back": len(view_stack) > 1,
        "active_states_label": f"Active: {', '.join(active_states)}" if active_states else "",
    }


def status_badges(ui_state: dict[str, Any], runtime: dict[str, Any]) -> tuple[str, ...]:
    """Return compact canvas badges for current GTK context."""
    active_view = str(ui_state.get("active_view", "idle"))
    badges = [view_title(active_view)]
    runtime_state = _humanize(runtime.get("state") or "unknown")
    badges.append(f"Runtime: {runtime_state}")
    model = str(runtime.get("model") or "").strip()
    if model:
        badges.append(f"Model: {model}")
    error = str(runtime.get("error") or "").strip()
    if error:
        badges.append(f"Error: {error}")
    active_label = header_state(ui_state)["active_states_label"]
    if active_label:
        badges.append(str(active_label))
    return tuple(badges)


def runtime_status_class(runtime: dict[str, Any]) -> str:
    """Return a GTK status CSS class for runtime health."""
    state = str(runtime.get("state") or "unknown").lower()
    if state == "error" or runtime.get("error"):
        return "status-error"
    if state in {"running", "stopped", "loaded", "unloaded"}:
        return "status-ok"
    return "status-pending"


def action_status_class(response: dict[str, Any]) -> str:
    """Return a GTK status CSS class for action feedback."""
    if response.get("error"):
        return "status-error"
    return runtime_status_class(response)


def _clip_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return "." * max_chars
    return f"{text[: max_chars - 3].rstrip()}..."


def _overflow_text(text: str, max_chars: int) -> str:
    if max_chars <= 3:
        return "." * max_chars
    return f"{text[: max_chars - 3].rstrip()}..."


def compact_status_badges(badges: tuple[str, ...], *, max_chars: int) -> tuple[str, ...]:
    """Clip GTK canvas badges to a bounded single-line label."""
    char_limit = max(1, int(max_chars))
    return tuple(
        _clip_text(label, char_limit) for label in (str(badge).strip() for badge in badges) if label
    )


def wrapped_text_lines(text: Any, *, max_chars: int, max_lines: int) -> tuple[str, ...]:
    """Wrap text into a small bounded set of GTK canvas lines."""
    line_limit = max(0, int(max_lines))
    char_limit = max(1, int(max_chars))
    if line_limit == 0:
        return ()

    words = str(text or "").split()
    if not words:
        return ()

    lines: list[str] = []
    index = 0

    while index < len(words) and len(lines) < line_limit:
        current = ""
        while index < len(words):
            word = words[index]
            if not current and len(word) > char_limit:
                lines.append(_clip_text(word, char_limit))
                index += 1
                break

            candidate = word if not current else f"{current} {word}"
            if len(candidate) > char_limit:
                break
            current = candidate
            index += 1

        if current:
            lines.append(current)

    if index < len(words) and lines:
        lines[-1] = _overflow_text(lines[-1], char_limit)

    return tuple(lines)


def wrapped_detail_lines(
    detail_lines: tuple[str, ...],
    *,
    max_chars: int,
    max_lines_per_detail: int,
    max_total_lines: int,
) -> tuple[str, ...]:
    """Wrap GTK detail lines without letting a panel overflow vertically."""
    total_limit = max(0, int(max_total_lines))
    if total_limit == 0:
        return ()

    display_lines: list[str] = []
    for index, detail in enumerate(detail_lines):
        remaining_slots = total_limit - len(display_lines)
        if remaining_slots <= 0:
            break
        per_detail_limit = min(max(1, int(max_lines_per_detail)), remaining_slots)
        display_lines.extend(
            wrapped_text_lines(
                detail,
                max_chars=max_chars,
                max_lines=per_detail_limit,
            )
        )
        if len(display_lines) >= total_limit and index < len(detail_lines) - 1:
            display_lines[-1] = _overflow_text(display_lines[-1], max(1, int(max_chars)))
            break

    return tuple(display_lines)


def action_shortcuts() -> dict[str, list[str]]:
    """Return GTK app action keyboard shortcuts."""
    return {
        "back": ["Escape", "<Alt>Left"],
        "start": ["<Primary>Return"],
        "stop": ["<Primary>period"],
        "preload": ["<Primary>r"],
        "unload": ["<Primary>u"],
    }


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
        error = str(runtime.get("error") or "").strip()
        if error:
            details.append(f"Error: {error}")

    return ToolPanel(
        title=view_title(active_view),
        summary=summary,
        detail_lines=tuple(details[:3]),
        progress=progress,
    )
