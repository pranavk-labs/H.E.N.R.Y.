"""Pure helpers for the GTK adaptive face view."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
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


def _timer_int(value: Any) -> int:
    try:
        number = float(str(value or "").strip() or "0")
    except (TypeError, ValueError):
        return 0
    if not math.isfinite(number):
        return 0
    return max(0, int(number))


def _dict_state(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_state(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _active_view_name(value: Any) -> str:
    return str(value or "").strip().lower() or "idle"


def _unique_labels(values: list[Any]) -> list[str]:
    labels: list[str] = []
    seen: set[str] = set()
    for value in values:
        label = _humanized_label(value)
        key = label.lower()
        if label and key not in seen:
            labels.append(label)
            seen.add(key)
    return labels


def _humanize(value: Any) -> str:
    """Convert compact API values into short labels."""
    return str(value or "").replace("_", " ").replace("-", " ").strip().title()


def _humanized_label(value: Any) -> str:
    return _humanize(value).strip()


def _action_label(value: Any) -> str:
    return _humanized_label(value) or "Action"


def _date_label(value: Any) -> str:
    raw_value = str(value or "").strip()
    date_value = raw_value[:10] if len(raw_value) >= 10 else raw_value
    try:
        parsed = date.fromisoformat(date_value)
    except ValueError:
        return raw_value
    month = parsed.strftime("%b")
    return f"{month} {parsed.day}, {parsed.year}"


def _short_identifier(value: Any) -> str:
    raw_value = str(value or "").strip()
    label = raw_value.split(":", 1)[1] if ":" in raw_value else raw_value
    return label[:8]


def _runtime_error_summary(error: Any) -> str:
    message = str(error or "").strip()
    if message.lower().startswith("backend unavailable:"):
        return "Backend offline"
    return message


def _runtime_state_label(runtime: dict[str, Any]) -> str:
    error = str(runtime.get("error") or "").strip()
    if error.lower().startswith("backend unavailable:"):
        return "Offline"
    return _humanized_label(runtime.get("state")) or "Unknown"


def view_summary(ui_state: dict[str, Any], runtime: dict[str, Any]) -> str:
    """Return the focused overlay text for the active adaptive view."""
    active_view = _active_view_name(ui_state.get("active_view"))
    status_text = str(ui_state.get("status_text") or "").strip()
    if active_view == "idle":
        error = _runtime_error_summary(runtime.get("error"))
        if error:
            return error
        state = str(runtime.get("state") or "").strip().lower()
        if not status_text and state in {"starting", "stopping", "loading", "unloading"}:
            return _humanize(state)
        return status_text

    if active_view == "pomodoro":
        raw_timer = ui_state.get("timer_state")
        if raw_timer is None:
            return "Timer ready"
        timer = _dict_state(raw_timer)
        work = _format_seconds(_timer_int(timer.get("remaining_work_seconds")))
        rest = _format_seconds(_timer_int(timer.get("remaining_break_seconds")))
        return f"Work {work} | Break {rest}"

    if active_view == "ideas":
        idea = _dict_state(ui_state.get("idea_view"))
        draft_text = str(idea.get("draft_text") or "").strip()
        if idea.get("is_active") and not draft_text and not status_text:
            return "Active idea"
        return draft_text or status_text or "Idea captured"

    if active_view == "todo_list":
        active_todo_title = str(ui_state.get("active_todo_title") or "").strip()
        if active_todo_title and (not status_text or status_text.lower() == "todos"):
            return active_todo_title
        return status_text or "Todos"

    if active_view == "calendar":
        active_event_title = str(ui_state.get("active_event_title") or "").strip()
        if active_event_title and (not status_text or status_text.lower() == "calendar"):
            return active_event_title
        return status_text or "Calendar"

    return status_text or f"Runtime {_runtime_state_label(runtime)}"


def view_title(active_view: str) -> str:
    """Return a concise human-facing title for the active GTK view."""
    view_name = _active_view_name(active_view)
    labels = {
        "idle": "Listening",
        "pomodoro": "Pomodoro",
        "ideas": "Idea",
        "todo_list": "Todos",
        "calendar": "Calendar",
    }
    return labels.get(view_name, _humanized_label(view_name))


def surface_title(ui_state: dict[str, Any], runtime: dict[str, Any]) -> str:
    """Return the current GTK canvas surface title."""
    active_view = _active_view_name(ui_state.get("active_view"))
    error = str(runtime.get("error") or "").strip()
    if active_view == "idle" and error.lower().startswith("backend unavailable:"):
        return "Offline"
    if active_view == "idle" and runtime_status_class(runtime) == "status-error":
        return "Error"
    state = str(runtime.get("state") or "").strip().lower()
    if active_view == "idle" and state in {"starting", "stopping", "loading", "unloading"}:
        return _humanize(state)
    return view_title(active_view)


def header_view_title(ui_state: dict[str, Any], runtime: dict[str, Any]) -> str:
    """Return the GTK header view label for the current surface."""
    return surface_title(ui_state, runtime)


def header_view_status_class(ui_state: dict[str, Any], runtime: dict[str, Any]) -> str:
    """Return a GTK status CSS class for the header view label."""
    title = header_view_title(ui_state, runtime)
    runtime_class = runtime_status_class(runtime)
    if title in {"Offline", "Error"} or runtime_class == "status-error":
        return "status-error"
    if runtime_class == "status-pending":
        return "status-pending"
    if title == "Listening":
        return "status-ok"
    return "status-neutral"


def view_accent(active_view: str) -> tuple[float, float, float]:
    """Return stable RGB accent colors for the active GTK view."""
    view_name = _active_view_name(active_view)
    accents = {
        "idle": (0.31, 0.78, 0.47),
        "pomodoro": (0.95, 0.39, 0.32),
        "ideas": (0.35, 0.63, 0.94),
        "todo_list": (0.91, 0.73, 0.33),
        "calendar": (0.65, 0.55, 0.95),
    }
    return accents.get(view_name, (0.72, 0.74, 0.78))


def surface_accent(ui_state: dict[str, Any], runtime: dict[str, Any]) -> tuple[float, float, float]:
    """Return the current GTK canvas accent color."""
    active_view = _active_view_name(ui_state.get("active_view"))
    if runtime_status_class(runtime) == "status-error":
        return (1.0, 0.42, 0.37)
    state = str(runtime.get("state") or "").strip().lower()
    if state in {"starting", "stopping", "loading", "unloading"}:
        return (0.85, 0.72, 0.31)
    return view_accent(active_view)


def runtime_summary(runtime: dict[str, Any]) -> str:
    """Return a compact runtime summary for the GTK header."""
    label = _runtime_state_label(runtime)
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
    return str(runtime.get("model") or "").strip()


def model_entry_user_edited_after_action(
    action_name: str,
    response: dict[str, Any],
    *,
    was_user_edited: bool,
) -> bool:
    """Return whether GTK should keep protecting user-entered model text."""
    if str(response.get("error") or "").strip():
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
    action_label = _action_label(action_name)
    if response.get("error"):
        error = _runtime_error_summary(response["error"])
        if error:
            return f"{action_label}: {error}"
    state = _humanized_label(response.get("state")) or "Complete"
    model = str(response.get("model") or "").strip()
    suffix = f" {model}" if model else ""
    return f"{action_label}: {state}{suffix}"


def action_exception_feedback(action_name: str, error: Any) -> str:
    """Turn an action exception into concise GTK feedback."""
    action_label = _action_label(action_name)
    if isinstance(error, ConnectionError):
        return f"{action_label}: Backend offline"
    fallback = error.__class__.__name__ if isinstance(error, BaseException) else "Error"
    message = str(error or "").strip() or fallback
    return f"{action_label}: {message}"


def control_state(runtime: dict[str, Any]) -> dict[str, bool]:
    """Return which runtime controls should be enabled for the current state."""
    state = str(runtime.get("state") or "unknown").strip().lower()
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
    view_stack = _list_state(ui_state.get("view_stack")) or ["idle"]
    active_states = _unique_labels(_list_state(ui_state.get("active_states")))
    visible_states = active_states[:3]
    overflow_count = len(active_states) - len(visible_states)
    active_states_label = ""
    if visible_states:
        active_states_label = f"Active: {', '.join(visible_states)}"
        if overflow_count > 0:
            active_states_label = f"{active_states_label} +{overflow_count}"
    return {
        "can_go_back": len(view_stack) > 1,
        "active_states_label": active_states_label,
    }


def active_states_status_class(ui_state: dict[str, Any]) -> str:
    """Return a GTK status CSS class for the active-states header label."""
    active_states = _unique_labels(_list_state(ui_state.get("active_states")))
    return "status-pending" if active_states else "status-neutral"


def status_badges(ui_state: dict[str, Any], runtime: dict[str, Any]) -> tuple[str, ...]:
    """Return compact canvas badges for current GTK context."""
    badges = [surface_title(ui_state, runtime)]
    runtime_state = _runtime_state_label(runtime)
    badges.append(f"Runtime: {runtime_state}")
    error = _runtime_error_summary(runtime.get("error"))
    if error:
        badges.append(f"Error: {error}")
    model = str(runtime.get("model") or "").strip()
    if model:
        badges.append(f"Model: {model}")
    active_label = header_state(ui_state)["active_states_label"]
    if active_label:
        badges.append(str(active_label))
    return tuple(badges)


def runtime_status_class(runtime: dict[str, Any]) -> str:
    """Return a GTK status CSS class for runtime health."""
    state = str(runtime.get("state") or "unknown").strip().lower()
    error = str(runtime.get("error") or "").strip()
    if state == "error" or error:
        return "status-error"
    if state in {"running", "stopped", "loaded", "unloaded"}:
        return "status-ok"
    return "status-pending"


def action_status_class(response: dict[str, Any]) -> str:
    """Return a GTK status CSS class for action feedback."""
    if str(response.get("error") or "").strip():
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


def compact_status_badges(
    badges: tuple[str, ...],
    *,
    max_chars: int,
    max_badges: int | None = None,
) -> tuple[str, ...]:
    """Clip GTK canvas badges to a bounded single-line label."""
    char_limit = max(1, int(max_chars))
    labels = [str(badge).strip() for badge in badges]
    visible_labels = [label for label in labels if label]
    if max_badges is not None:
        badge_limit = max(0, int(max_badges))
        if badge_limit == 0:
            return ()
        if len(visible_labels) > badge_limit:
            if badge_limit == 1:
                visible_labels = [f"{visible_labels[0]} +{len(visible_labels) - 1}"]
                return tuple(_clip_text(label, char_limit) for label in visible_labels)
            keep_count = max(0, badge_limit - 1)
            overflow_count = len(visible_labels) - keep_count
            visible_labels = [*visible_labels[:keep_count], f"+{overflow_count} more"]
    return tuple(_clip_text(label, char_limit) for label in visible_labels)


def status_badge_tone(label: Any) -> str:
    """Return the visual tone for one GTK canvas status badge."""
    value = str(label or "").strip()
    if value in {"Offline", "Error", "Runtime: Error", "Runtime: Offline"} or value.startswith(
        "Error:"
    ):
        return "error"
    if value.startswith("Active:"):
        return "pending"
    if value in {"Starting", "Stopping", "Loading", "Unloading"}:
        return "pending"
    if value in {
        "Runtime: Running",
        "Runtime: Stopped",
        "Runtime: Loaded",
        "Runtime: Unloaded",
    }:
        return "ok"
    if value.startswith("Runtime:"):
        return "pending"
    return "neutral"


def status_badge_rgba(
    label: Any, accent: tuple[float, float, float]
) -> tuple[float, float, float, float]:
    """Return a subtle fill color for one GTK canvas status badge."""
    tone = status_badge_tone(label)
    if tone == "error":
        return (1.0, 0.42, 0.37, 0.2)
    if tone == "ok":
        return (0.31, 0.78, 0.47, 0.18)
    if tone == "pending":
        return (0.85, 0.72, 0.31, 0.2)
    return (*accent, 0.16)


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


def _humanize_shortcut(shortcut: str) -> str:
    value = shortcut.replace("<Primary>", "Ctrl+").replace("<Alt>", "Alt+")
    value = value.replace("Escape", "Esc").replace("Return", "Enter")
    value = value.replace("period", ".")
    if value.startswith("Ctrl+") and len(value) == len("Ctrl+") + 1:
        return f"Ctrl+{value[-1].upper()}"
    if value.startswith("Alt+") and len(value) == len("Alt+") + 1:
        return f"Alt+{value[-1].upper()}"
    return value


def action_tooltip(action_name: str, label: str) -> str:
    """Return a toolbar tooltip with human-readable shortcuts."""
    shortcuts = action_shortcuts().get(action_name, [])
    if not shortcuts:
        return label
    shortcut_text = ", ".join(_humanize_shortcut(shortcut) for shortcut in shortcuts)
    return f"{label} ({shortcut_text})"


def tool_panel(ui_state: dict[str, Any], runtime: dict[str, Any]) -> ToolPanel:
    """Build the richer content model rendered by the GTK canvas."""
    active_view = _active_view_name(ui_state.get("active_view"))
    summary = view_summary(ui_state, runtime)
    details: list[str] = []
    progress: float | None = None

    if active_view == "pomodoro":
        raw_timer = ui_state.get("timer_state")
        if raw_timer is None:
            details.append("Ready to start")
        else:
            timer = _dict_state(raw_timer)
            status = _humanized_label(timer.get("status")) or "Timer"
            phase = str(timer.get("phase") or "").strip().lower() or "work"
            phase_label = phase if phase == "work" else _humanized_label(phase)
            work_remaining = _timer_int(timer.get("remaining_work_seconds"))
            break_remaining = _timer_int(timer.get("remaining_break_seconds"))
            details.append(f"{status} {phase_label} session")
            if phase == "work":
                details.append(f"Break queued for {_format_seconds(break_remaining)}")
                total = _timer_int(timer.get("work_duration_minutes")) * 60
                remaining = work_remaining
            else:
                details.append(f"Next work block after {_format_seconds(break_remaining)}")
                total = _timer_int(timer.get("break_duration_minutes")) * 60
                remaining = break_remaining
            if total > 0:
                progress = max(0.0, min(1.0, round((total - remaining) / total, 3)))

    elif active_view == "ideas":
        idea = _dict_state(ui_state.get("idea_view"))
        draft_text = str(idea.get("draft_text") or "").strip()
        if idea.get("is_active") and summary != "Active idea":
            details.append("Active idea")
        if idea.get("active_idea_id"):
            identifier = _short_identifier(idea["active_idea_id"])
            if identifier:
                details.append(f"ID: {identifier}")
        if draft_text and not details:
            details.append("Draft in progress")
        if not details:
            details.append("Ready to capture")

    elif active_view == "todo_list":
        active_title = str(ui_state.get("active_todo_title") or "").strip()
        if active_title and summary != active_title:
            details.append(f"Active: {active_title}")
        elif ui_state.get("active_todo_id"):
            identifier = _short_identifier(ui_state["active_todo_id"])
            if identifier:
                details.append(f"Active: {identifier}")
        filter_status = _humanized_label(ui_state.get("todo_filter_status"))
        if filter_status:
            details.append(f"Filter: {filter_status}")
        if ui_state.get("selected_category_id"):
            identifier = _short_identifier(ui_state["selected_category_id"])
            if identifier:
                details.append(f"Category: {identifier}")

    elif active_view == "calendar":
        mode = _humanized_label(ui_state.get("calendar_view_mode")) or "Upcoming"
        summary = summary if summary != "Calendar" else mode
        if ui_state.get("calendar_selected_date"):
            selected_date = _date_label(ui_state["calendar_selected_date"])
            if selected_date:
                details.append(f"Date: {selected_date}")
        filter_type = _humanized_label(ui_state.get("calendar_filter_type"))
        if filter_type:
            details.append(f"Type: {filter_type}")
        active_event_title = str(ui_state.get("active_event_title") or "").strip()
        if active_event_title and not (details and summary == active_event_title):
            details.append(f"Event: {active_event_title}")
        elif ui_state.get("active_event_id"):
            identifier = _short_identifier(ui_state["active_event_id"])
            if identifier:
                details.append(f"Event: {identifier}")

    elif active_view == "idle":
        if runtime:
            details.append(f"Runtime: {runtime_summary(runtime)}")
        error = _runtime_error_summary(runtime.get("error"))
        if error:
            details.append(f"Error: {error}")

    attention_detail = ""
    if active_view != "idle":
        error = _runtime_error_summary(runtime.get("error"))
        state = str(runtime.get("state") or "").strip()
        if error:
            attention_detail = f"Runtime error: {error}"
        elif state and runtime_status_class(runtime) == "status-pending":
            attention_detail = f"Runtime: {_humanize(state)}"

    if active_view != "idle" and attention_detail:
        if len(details) >= 3:
            details = [*details[:2], attention_detail]
        else:
            details.append(attention_detail)

    return ToolPanel(
        title=view_title(active_view),
        summary=summary,
        detail_lines=tuple(details[:3]),
        progress=progress,
    )
