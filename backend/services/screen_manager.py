"""Mock screen manager for tools and services to update UI state.

This is intentionally lightweight: it provides an in-memory representation
of the current "screen" / view so tools can declaratively request changes
without depending on any concrete GUI implementation.

A real GUI (Phase 3+) can observe this state and render appropriate views.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScreenState:
    """Simple container for current screen-related state."""

    active_view: str = "idle"
    status_text: str = ""
    timer_state: Dict[str, Any] = field(default_factory=dict)
    idea_view: Dict[str, Any] = field(default_factory=dict)


class ScreenManager:
    """Mock screen manager that tools can interact with."""

    _instance: Optional["ScreenManager"] = None

    def __init__(self) -> None:
        self._state = ScreenState()

    @classmethod
    def get_instance(cls) -> "ScreenManager":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def state(self) -> ScreenState:
        """Get current screen state."""
        return self._state

    # ------------------------------------------------------------------
    # High-level helpers used by tools
    # ------------------------------------------------------------------
    def set_view(self, view_name: str, **kwargs: Any) -> None:
        """Set the active view and optionally update arbitrary metadata."""
        logger.info("Screen view -> %s", view_name)
        self._state.active_view = view_name
        if kwargs:
            self._state.idea_view.update(kwargs)

    def update_status(self, text: str) -> None:
        """Update status text shown to the user."""
        logger.info("Screen status: %s", text)
        self._state.status_text = text

    def update_timer(self, **timer_state: Any) -> None:
        """Update timer-related UI."""
        logger.info("Screen timer state: %s", timer_state)
        self._state.timer_state.update(timer_state)
        # Ensure the active view reflects that a timer is visible
        if self._state.active_view == "idle":
            self._state.active_view = "pomodoro"

    def update_idea_view(self, **idea_state: Any) -> None:
        """Update the idea/notebook-related UI."""
        logger.info("Screen idea view: %s", idea_state)
        self._state.idea_view.update(idea_state)
        if self._state.active_view == "idle":
            self._state.active_view = "ideas"


__all__ = ["ScreenManager", "ScreenState"]


