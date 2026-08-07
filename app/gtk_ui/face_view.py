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


def _has_timer_value(value: Any) -> bool:
    try:
        number = float(str(value or "").strip())
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def _timer_display(value: Any) -> str:
    if not _has_timer_value(value):
        return "ready"
    return _format_seconds(_timer_int(value))


def _dict_state(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_state(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _active_view_name(value: Any) -> str:
    view_name = str(value or "").strip().lower() or "idle"
    aliases = {
        "event": "calendar",
        "events": "calendar",
        "idea": "ideas",
        "tasks": "todo_list",
        "timer": "pomodoro",
        "todo": "todo_list",
        "todo list": "todo_list",
        "todo-list": "todo_list",
        "todos": "todo_list",
        "voice": "voice_note",
        "voice note": "voice_note",
        "voice-note": "voice_note",
    }
    return aliases.get(view_name, view_name)


def active_view_name(value: Any) -> str:
    """Return the canonical GTK view name for raw API state."""
    return _active_view_name(value)


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


def _current_view_active_state_labels(active_view: Any) -> set[str]:
    view_name = _active_view_name(active_view)
    aliases = {
        "calendar": ("event", "events"),
        "pomodoro": ("timer",),
        "ideas": ("idea",),
        "todo_list": ("todo", "todos", "tasks"),
        "voice_note": ("voice",),
    }
    labels = {
        view_title(view_name).lower(),
        _humanized_label(view_name).lower(),
        *(_humanized_label(alias).lower() for alias in aliases.get(view_name, ())),
    }
    return {label for label in labels if label}


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


def _label_has_error(value: Any) -> bool:
    label = _humanized_label(value)
    return label == "Error" or label.endswith(" Error") or " Error," in label


def _runtime_state_label(runtime: dict[str, Any]) -> str:
    error = str(runtime.get("error") or "").strip()
    if error.lower().startswith("backend unavailable:"):
        return "Offline"
    return _humanized_label(runtime.get("state")) or "Unknown"


def _is_generic_status(status_text: str, generic_labels: set[str]) -> bool:
    label = _humanized_label(status_text).lower()
    return label in generic_labels


def view_summary(ui_state: dict[str, Any], runtime: dict[str, Any]) -> str:
    """Return the focused overlay text for the active adaptive view."""
    active_view = _active_view_name(ui_state.get("active_view"))
    status_text = str(ui_state.get("status_text") or "").strip()
    if active_view == "idle":
        error = _runtime_error_summary(runtime.get("error"))
        if error:
            return error
        state = str(runtime.get("state") or "").strip().lower()
        if state in {"starting", "stopping", "loading", "unloading"} and (
            not status_text or _is_generic_status(status_text, {"idle", "listening", "ready"})
        ):
            return _humanize(state)
        return status_text or _runtime_state_label(runtime)

    if active_view == "pomodoro":
        raw_timer = ui_state.get("timer_state")
        if not isinstance(raw_timer, dict):
            return "Timer ready"
        timer = _dict_state(raw_timer)
        phase = str(timer.get("phase") or "").strip().lower() or "work"
        work = _timer_display(timer.get("remaining_work_seconds"))
        rest = _timer_display(timer.get("remaining_break_seconds"))
        if phase != "work":
            phase_label = _humanized_label(phase) or "Break"
            return f"{phase_label} {rest} | Work ready"
        return f"Work {work} | Break {rest}"

    if active_view == "ideas":
        idea = _dict_state(ui_state.get("idea_view"))
        draft_text = str(idea.get("draft_text") or "").strip()
        active_idea_id = str(idea.get("active_idea_id") or "").strip()
        if (
            (idea.get("is_active") or active_idea_id)
            and not draft_text
            and (
                not status_text
                or _is_generic_status(status_text, {"idea", "idea captured", "ideas"})
            )
        ):
            return "Active idea"
        return draft_text or status_text or "Idea captured"

    if active_view == "todo_list":
        active_todo_title = str(ui_state.get("active_todo_title") or "").strip()
        if active_todo_title and (
            not status_text
            or _is_generic_status(
                status_text,
                {"to do", "todo", "todo list", "todos", "task", "task list", "tasks"},
            )
        ):
            return active_todo_title
        active_todo_id = str(ui_state.get("active_todo_id") or "").strip()
        if active_todo_id and (
            not status_text
            or _is_generic_status(
                status_text,
                {"to do", "todo", "todo list", "todos", "task", "task list", "tasks"},
            )
        ):
            return "Active todo"
        return status_text or "Todos"

    if active_view == "calendar":
        active_event_title = str(ui_state.get("active_event_title") or "").strip()
        if active_event_title and (
            not status_text
            or _is_generic_status(
                status_text,
                {"calendar", "calendar events", "event", "events", "upcoming", "upcoming events"},
            )
        ):
            return active_event_title
        active_event_id = str(ui_state.get("active_event_id") or "").strip()
        if active_event_id and (
            not status_text
            or _is_generic_status(
                status_text,
                {"calendar", "calendar events", "event", "events", "upcoming", "upcoming events"},
            )
        ):
            return "Active event"
        return status_text or "Calendar"

    if active_view == "voice_note":
        if status_text and not _is_generic_status(status_text, {"voice note", "voice", "ready"}):
            return status_text
        return "Voice note ready"

    return status_text or f"Runtime: {_runtime_state_label(runtime)}"


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
        "voice_note": (0.3, 0.78, 0.82),
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
        return f"{label} - {_clip_text(model, 18)}"
    return label


def runtime_tooltip(runtime: dict[str, Any]) -> str:
    """Return full runtime detail for GTK header hover text."""
    label = _runtime_state_label(runtime)
    error = str(runtime.get("error") or "").strip()
    if error:
        return f"{label} - {error}"
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


def model_entry_tooltip(raw_value: Any, *, user_edited: bool) -> str:
    """Return hover text for the GTK model override entry."""
    value = str(raw_value or "").strip()
    if user_edited and value:
        return f"Model override active: {value}"
    return "Model override for preload and unload"


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
            return f"{action_label}: {_clip_text(error, 17)}"
    state = _humanized_label(response.get("state")) or "Complete"
    model = str(response.get("model") or "").strip()
    suffix = f" {_clip_text(model, 18)}" if model else ""
    return f"{action_label}: {state}{suffix}"


def action_feedback_tooltip(action_name: str, response: dict[str, Any]) -> str:
    """Turn an action API response into full GTK hover feedback."""
    action_label = _action_label(action_name)
    if response.get("error"):
        error = str(response["error"] or "").strip()
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
    return f"{action_label}: {_clip_text(message, 17)}"


def action_exception_feedback_tooltip(action_name: str, error: Any) -> str:
    """Turn an action exception into full GTK hover feedback."""
    action_label = _action_label(action_name)
    if isinstance(error, ConnectionError):
        message = str(error or "").strip()
        suffix = f" - {message}" if message else ""
        return f"{action_label}: Backend offline{suffix}"
    fallback = error.__class__.__name__ if isinstance(error, BaseException) else "Error"
    message = str(error or "").strip() or fallback
    return f"{action_label}: {message}"


def control_state(runtime: dict[str, Any]) -> dict[str, bool]:
    """Return which runtime controls should be enabled for the current state."""
    state = str(runtime.get("state") or "unknown").strip().lower()
    error = str(runtime.get("error") or "").strip().lower()
    if error.startswith("backend unavailable:"):
        return {"start": False, "stop": False, "preload": False, "unload": False}
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
    if runtime_status_class(runtime) == "status-error":
        has_model = bool(str(runtime.get("model") or "").strip())
        return {"start": True, "stop": False, "preload": True, "unload": has_model}
    return {"start": False, "stop": False, "preload": False, "unload": False}


def header_state(ui_state: dict[str, Any]) -> dict[str, Any]:
    """Return GTK header navigation and concurrent-state labels."""
    view_stack = _list_state(ui_state.get("view_stack")) or ["idle"]
    current_view_labels = _current_view_active_state_labels(ui_state.get("active_view"))
    active_states = [
        label
        for label in _unique_labels(_list_state(ui_state.get("active_states")))
        if label.lower() not in current_view_labels
    ]
    visible_states = active_states[:3]
    overflow_count = len(active_states) - len(visible_states)
    active_states_label = ""
    active_states_tooltip = ""
    if visible_states:
        active_states_label = f"Active: {', '.join(visible_states)}"
        active_states_tooltip = f"Active: {', '.join(active_states)}"
        if overflow_count > 0:
            active_states_label = f"{active_states_label} +{overflow_count}"
    return {
        "can_go_back": len(view_stack) > 1,
        "active_states_label": active_states_label,
        "active_states_tooltip": active_states_tooltip,
    }


def active_states_status_class(ui_state: dict[str, Any]) -> str:
    """Return a GTK status CSS class for the active-states header label."""
    current_view_labels = _current_view_active_state_labels(ui_state.get("active_view"))
    active_states = [
        label
        for label in _unique_labels(_list_state(ui_state.get("active_states")))
        if label.lower() not in current_view_labels
    ]
    if any(_label_has_error(label) for label in active_states):
        return "status-error"
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


def status_badge_tooltip_labels(
    ui_state: dict[str, Any], runtime: dict[str, Any]
) -> tuple[str, ...]:
    """Return full badge labels for GTK canvas hover text."""
    labels = list(status_badges(ui_state, runtime))
    active_state = header_state(ui_state)
    active_label = str(active_state["active_states_label"])
    active_tooltip = str(active_state["active_states_tooltip"])
    if active_label and active_tooltip and active_label in labels:
        labels[labels.index(active_label)] = active_tooltip
    return tuple(labels)


def runtime_status_class(runtime: dict[str, Any]) -> str:
    """Return a GTK status CSS class for runtime health."""
    state = str(runtime.get("state") or "unknown").strip().lower()
    error = str(runtime.get("error") or "").strip()
    if state == "error" or state.endswith("-error") or error:
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


def _overflow_primary_label(primary: str) -> str:
    if primary.startswith("Runtime:"):
        runtime_label = primary.split(":", 1)[1].strip()
        if runtime_label.endswith("Error"):
            return "Error"
        if runtime_label:
            return runtime_label
    if primary.startswith("Error:"):
        return "Error"
    if primary.startswith("Active:"):
        if _label_has_error(primary.split(":", 1)[1]):
            return "Error"
        return "Active"
    if primary.startswith("Model:"):
        return "Model"
    return primary


def _primary_overflow_badge(primary: str, overflow_count: int, max_chars: int) -> str:
    primary = _overflow_primary_label(primary)
    suffix = f" +{overflow_count}"
    if len(primary) + len(suffix) <= max_chars:
        return f"{primary}{suffix}"
    if max_chars <= len(suffix):
        return _clip_text(suffix.strip(), max_chars)
    primary_limit = max_chars - len(suffix)
    return f"{_clip_text(primary, primary_limit)}{suffix}"


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
                return (
                    _primary_overflow_badge(
                        visible_labels[0],
                        len(visible_labels) - 1,
                        char_limit,
                    ),
                )
            keep_count = max(0, badge_limit - 1)
            overflow_count = len(visible_labels) - keep_count
            visible_labels = [*visible_labels[:keep_count], f"+{overflow_count} more"]
    return tuple(_clip_text(label, char_limit) for label in visible_labels)


def status_badge_tone(label: Any) -> str:
    """Return the visual tone for one GTK canvas status badge."""
    value = str(label or "").strip()
    primary_value, overflow_suffix = value.rsplit(" +", 1) if " +" in value else (value, "")
    if overflow_suffix.isdigit():
        value = primary_value
    if (
        value in {"Offline", "Error", "Runtime: Error", "Runtime: Offline"}
        or value.startswith("Error:")
        or (value.startswith("Runtime:") and value.endswith("Error"))
        or (value.startswith("Active:") and _label_has_error(value.split(":", 1)[1]))
    ):
        return "error"
    if value == "Active" or value.startswith("Active:"):
        return "pending"
    if value in {
        "Listening",
        "Loading",
        "Paused",
        "Pausing",
        "Ready",
        "Resuming",
        "Starting",
        "Stopping",
        "Unknown",
        "Unloading",
        "Voice Error",
    }:
        return "pending"
    if value in {
        "Running",
        "Stopped",
        "Loaded",
        "Unloaded",
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


def control_tooltip(
    action_name: str,
    label: str,
    runtime: dict[str, Any],
    *,
    enabled: bool,
) -> str:
    """Return a runtime control tooltip that explains disabled actions."""
    if enabled:
        return action_tooltip(action_name, label)

    state = str(runtime.get("state") or "unknown").strip().lower() or "unknown"
    error = str(runtime.get("error") or "").strip().lower()
    if error.startswith("backend unavailable:"):
        reason = "backend offline"
    elif state in {"starting", "stopping", "loading", "unloading"}:
        reason = f"runtime is {_humanize(state).lower()}"
    elif action_name == "start" and state == "running":
        reason = "runtime is already running"
    elif action_name == "stop":
        reason = "runtime is not running"
    elif action_name == "unload":
        reason = "no model loaded"
    else:
        reason = f"runtime state is {_humanize(state).lower()}"
    return f"{label} unavailable: {reason}"


def tool_panel_tooltip(panel: ToolPanel) -> str:
    """Return full hover text for the central GTK canvas panel."""
    lines = [panel.title, panel.summary, *panel.detail_lines]
    if panel.progress is not None:
        progress = max(0.0, min(1.0, panel.progress))
        lines.append(f"Progress: {round(progress * 100)}%")
    return "\n".join(line for line in lines if str(line).strip())


def canvas_tooltip(ui_state: dict[str, Any], runtime: dict[str, Any]) -> str:
    """Return full hover text for the GTK canvas, including clipped badge context."""
    panel = tool_panel(ui_state, runtime)
    if _active_view_name(ui_state.get("active_view")) == "idle":
        panel = ToolPanel(
            title=panel.title,
            summary=panel.summary,
            detail_lines=tuple(
                f"Runtime: {runtime_tooltip(runtime)}" if line.startswith("Runtime:") else line
                for line in panel.detail_lines
            ),
            progress=panel.progress,
        )
    lines = [tool_panel_tooltip(panel)]
    badges = status_badge_tooltip_labels(ui_state, runtime)
    if badges:
        lines.append(f"Badges: {' | '.join(badges)}")
    return "\n".join(line for line in lines if str(line).strip())


def tool_panel(ui_state: dict[str, Any], runtime: dict[str, Any]) -> ToolPanel:
    """Build the richer content model rendered by the GTK canvas."""
    active_view = _active_view_name(ui_state.get("active_view"))
    summary = view_summary(ui_state, runtime)
    details: list[str] = []
    progress: float | None = None

    if active_view == "pomodoro":
        raw_timer = ui_state.get("timer_state")
        if not isinstance(raw_timer, dict):
            details.append("Ready to start")
        else:
            timer = _dict_state(raw_timer)
            status = _humanized_label(timer.get("status")) or "Timer"
            phase = str(timer.get("phase") or "").strip().lower() or "work"
            phase_label = phase if phase == "work" else _humanized_label(phase)
            raw_work_remaining = timer.get("remaining_work_seconds")
            raw_break_remaining = timer.get("remaining_break_seconds")
            work_remaining = _timer_int(raw_work_remaining)
            break_remaining = _timer_int(raw_break_remaining)
            details.append(f"{status} {phase_label} session")
            if phase == "work":
                if _has_timer_value(raw_break_remaining):
                    details.append(f"Break queued for {_format_seconds(break_remaining)}")
                else:
                    details.append("Break ready")
                total = _timer_int(timer.get("work_duration_minutes")) * 60
                remaining = work_remaining
                has_remaining = _has_timer_value(raw_work_remaining)
            else:
                if _has_timer_value(raw_break_remaining):
                    details.append(f"Next work block after {_format_seconds(break_remaining)}")
                else:
                    details.append("Next work block ready")
                total = _timer_int(timer.get("break_duration_minutes")) * 60
                remaining = break_remaining
                has_remaining = _has_timer_value(raw_break_remaining)
            if total > 0 and has_remaining:
                progress = max(0.0, min(1.0, round((total - remaining) / total, 3)))

    elif active_view == "ideas":
        idea = _dict_state(ui_state.get("idea_view"))
        draft_text = str(idea.get("draft_text") or "").strip()
        if idea.get("is_active") and summary != "Active idea":
            details.append("Active idea")
        if draft_text:
            details.append("Draft in progress")
        if idea.get("active_idea_id"):
            identifier = _short_identifier(idea["active_idea_id"])
            if identifier:
                details.append(f"ID: {identifier}")
        if not details:
            details.append("Ready to capture")

    elif active_view == "todo_list":
        active_title = str(ui_state.get("active_todo_title") or "").strip()
        if active_title and summary != active_title:
            details.append(f"Active: {active_title}")
        elif not active_title and ui_state.get("active_todo_id"):
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
        active_todo_id = str(ui_state.get("active_todo_id") or "").strip()
        if not details and not active_title and not active_todo_id:
            details.append("Ready to plan")

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
        if active_event_title and summary != active_event_title:
            details.append(f"Event: {active_event_title}")
        elif not active_event_title and ui_state.get("active_event_id"):
            identifier = _short_identifier(ui_state["active_event_id"])
            if identifier:
                details.append(f"Event: {identifier}")
        active_event_id = str(ui_state.get("active_event_id") or "").strip()
        if not details and not active_event_title and not active_event_id:
            details.append("Ready to schedule")

    elif active_view == "voice_note":
        if summary == "Voice note ready":
            details.append("Ready to listen")

    elif active_view == "idle":
        details.append(f"Runtime: {runtime_summary(runtime)}")
        error = _runtime_error_summary(runtime.get("error"))
        if error and error != summary:
            details.append(f"Error: {error}")

    attention_detail = ""
    if active_view != "idle":
        error = _runtime_error_summary(runtime.get("error"))
        state = str(runtime.get("state") or "").strip()
        if error:
            attention_detail = (
                "Runtime: Offline" if error == "Backend offline" else f"Runtime error: {error}"
            )
        elif state and runtime_status_class(runtime) == "status-error":
            attention_detail = f"Runtime error: {_humanize(state)}"
        elif state and runtime_status_class(runtime) == "status-pending":
            attention_detail = f"Runtime: {_humanize(state)}"

    if active_view != "idle" and attention_detail and attention_detail != summary:
        if len(details) >= 3:
            details = [*details[:2], attention_detail]
        else:
            details.append(attention_detail)

    panel_title = (
        surface_title(ui_state, runtime) if active_view == "idle" else view_title(active_view)
    )

    return ToolPanel(
        title=panel_title,
        summary=summary,
        detail_lines=tuple(details[:3]),
        progress=progress,
    )
