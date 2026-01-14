"""UI state management for H.E.N.R.Y. application."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class UIState:
    """UI state data class."""

    active_view: str = "idle"
    status_text: str = ""
    timer_state: Dict[str, Any] | None = None
    idea_view: Dict[str, Any] | None = None
    timer_state_received_at: float = 0.0  # Timestamp when timer state was last received

