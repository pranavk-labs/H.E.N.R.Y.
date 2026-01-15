"""UI state management for H.E.N.R.Y. application."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


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

