"""UI state management for H.E.N.R.Y. application."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class UIState:
    """UI state data class with navigation stack support."""

    active_view: str = "idle"
    status_text: str = ""
    timer_state: Dict[str, Any] | None = None
    idea_view: Dict[str, Any] | None = None
    timer_state_received_at: float = 0.0  # Timestamp when timer state was last received

    # Navigation stack for back navigation support
    view_stack: List[str] = field(default_factory=lambda: ["idle"])

    # Concurrent active states (e.g., ["timer", "idea"])
    active_states: List[str] = field(default_factory=list)

    # Todo state
    todo_filter_status: Optional[str] = None
    selected_category_id: Optional[str] = None
    active_todo_id: Optional[str] = None

    # Calendar state
    calendar_view_mode: str = "upcoming"
    calendar_selected_date: Optional[str] = None
    calendar_filter_type: Optional[str] = None
    active_event_id: Optional[str] = None
    active_event_title: str = ""
