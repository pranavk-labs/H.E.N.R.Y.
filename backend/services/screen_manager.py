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
        logger.debug("Screen view -> %s", view_name)
        self._state.active_view = view_name
        if kwargs:
            self._state.idea_view.update(kwargs)

    def update_status(self, text: str) -> None:
        """Update status text shown to the user."""
        # Only log significant status changes, not repetitive ones
        if text and text != self._state.status_text:
            logger.debug("Screen status: %s", text)
        self._state.status_text = text

    def update_timer(self, **timer_state: Any) -> None:
        """Update timer-related UI."""
        # Only log status changes, not countdown updates
        old_status = self._state.timer_state.get("status")
        new_status = timer_state.get("status")
        if old_status != new_status:
            logger.info("Timer status: %s -> %s", old_status or "none", new_status)

        self._state.timer_state.update(timer_state)
        # Ensure the active view reflects that a timer is visible
        # But don't force the view if the timer is completed (we're returning to idle)
        if self._state.active_view == "idle" and timer_state.get("status") != "completed":
            self._state.active_view = "pomodoro"

    def update_idea_view(self, **idea_state: Any) -> None:
        """Update the idea/notebook-related UI."""
        logger.debug("Screen idea view: %s", idea_state)
        self._state.idea_view.update(idea_state)
        if self._state.active_view == "idle":
            self._state.active_view = "ideas"


__all__ = ["ScreenManager", "ScreenState"]


