"""Mock screen manager for tools and services to update UI state.

This is intentionally lightweight: it provides an in-memory representation
of the current "screen" / view so tools can declaratively request changes
without depending on any concrete GUI implementation.

A real GUI (Phase 3+) can observe this state and render appropriate views.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScreenState:
    """Enhanced state container with navigation stack and concurrent state tracking.

    This state model supports:
    - Navigation history via a view stack
    - Concurrent states (timer + idea both active)
    - Layered views (idea overlay on top of timer view)
    """

    # Navigation stack - tracks view history for back navigation
    # Example: ["idle", "pomodoro", "ideas"] means we're in ideas view,
    # and going back would return to pomodoro, then idle
    view_stack: List[str] = field(default_factory=lambda: ["idle"])

    status_text: str = ""

    # Concurrent state tracking - these can be active simultaneously
    timer_state: Dict[str, Any] = field(default_factory=dict)
    idea_view: Dict[str, Any] = field(default_factory=dict)

    # Active idea tracking
    active_idea_id: Optional[str] = None
    active_idea_text: str = ""
    idea_last_updated: Optional[float] = None

    # Active todo tracking
    active_todo_id: Optional[str] = None
    active_todo_title: str = ""
    todo_filter_status: Optional[str] = None  # Filter: todo, in_progress, completed, etc.
    selected_category_id: Optional[str] = None  # Selected category filter

    # Active calendar tracking
    active_event_id: Optional[str] = None
    active_event_title: str = ""
    calendar_view_mode: str = "upcoming"  # upcoming, today, week, month
    calendar_selected_date: Optional[str] = None  # ISO format date string
    calendar_filter_type: Optional[str] = None  # Filter by event_type

    # Concurrent active states - tracks which features are currently running
    # Example: ["timer", "idea"] means both timer and idea are active
    active_states: List[str] = field(default_factory=list)

    @property
    def active_view(self) -> str:
        """Get the current active view (top of stack)."""
        return self.view_stack[-1] if self.view_stack else "idle"

    @property
    def previous_view(self) -> Optional[str]:
        """Get the previous view (for back navigation)."""
        return self.view_stack[-2] if len(self.view_stack) > 1 else None

    def can_go_back(self) -> bool:
        """Check if we can navigate back."""
        return len(self.view_stack) > 1


class ScreenManager:
    """Screen manager with navigation stack and concurrent state tracking."""

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
    # Navigation stack methods
    # ------------------------------------------------------------------
    def push_view(self, view_name: str, replace_current: bool = False) -> None:
        """Push a new view onto the navigation stack.

        Args:
            view_name: Name of the view to push
            replace_current: If True, replace the current view instead of pushing
        """
        current_view = self._state.active_view

        if replace_current and self._state.view_stack:
            # Replace the top of the stack
            self._state.view_stack[-1] = view_name
            logger.debug(f"Screen view replaced: {current_view} -> {view_name}")
        else:
            # Push new view onto stack
            self._state.view_stack.append(view_name)
            logger.debug(
                f"Screen view pushed: {current_view} -> {view_name} (stack depth: {len(self._state.view_stack)})"
            )

    def pop_view(self) -> Optional[str]:
        """Pop the current view from the stack and return to previous view.

        Also clears the associated active state for the view being popped.

        Returns:
            The view that was popped, or None if we're at the base view
        """
        if len(self._state.view_stack) <= 1:
            logger.debug("Cannot pop view: already at base view")
            return None

        popped = self._state.view_stack.pop()

        # Clear associated active state based on view type
        # Map view names to state names
        view_to_state = {
            "pomodoro": "timer",
            "ideas": "idea",
        }

        if popped in view_to_state:
            state_name = view_to_state[popped]
            self.remove_active_state(state_name)

            # Also clear idea-specific data if popping ideas view
            if popped == "ideas":
                self._state.active_idea_id = None
                self._state.active_idea_text = ""
                self._state.idea_last_updated = None
                self._state.idea_view["is_active"] = False

        new_view = self._state.active_view
        logger.debug(
            f"Screen view popped: {popped} -> {new_view} (stack depth: {len(self._state.view_stack)})"
        )
        return popped

    def go_back(self) -> bool:
        """Navigate back to the previous view.

        Returns:
            True if navigation occurred, False if already at base view
        """
        if not self._state.can_go_back():
            return False

        self.pop_view()
        return True

    def reset_to_idle(self) -> None:
        """Reset navigation stack to idle view."""
        self._state.view_stack = ["idle"]
        logger.debug("Screen view reset to idle")

    def get_navigation_stack(self) -> List[str]:
        """Get a copy of the current navigation stack."""
        return self._state.view_stack.copy()

    # ------------------------------------------------------------------
    # Concurrent state management
    # ------------------------------------------------------------------
    def add_active_state(self, state_name: str) -> None:
        """Mark a state as active (e.g., 'timer', 'idea').

        Args:
            state_name: Name of the state to mark as active
        """
        if state_name not in self._state.active_states:
            self._state.active_states.append(state_name)
            logger.debug(f"Active state added: {state_name} (active: {self._state.active_states})")

    def remove_active_state(self, state_name: str) -> None:
        """Remove a state from active states.

        Args:
            state_name: Name of the state to remove
        """
        if state_name in self._state.active_states:
            self._state.active_states.remove(state_name)
            logger.debug(
                f"Active state removed: {state_name} (active: {self._state.active_states})"
            )

    def is_state_active(self, state_name: str) -> bool:
        """Check if a specific state is currently active.

        Args:
            state_name: Name of the state to check

        Returns:
            True if the state is active
        """
        return state_name in self._state.active_states

    def get_active_states(self) -> List[str]:
        """Get a copy of all currently active states."""
        return self._state.active_states.copy()

    # ------------------------------------------------------------------
    # High-level helpers used by tools (backward compatible)
    # ------------------------------------------------------------------
    def set_view(self, view_name: str, **kwargs: Any) -> None:
        """Set the active view (replaces current view in stack).

        This is kept for backward compatibility but prefer push_view().
        """
        logger.debug("Screen view -> %s", view_name)
        self.push_view(view_name, replace_current=True)
        if kwargs:
            self._state.idea_view.update(kwargs)

    def update_status(self, text: str) -> None:
        """Update status text shown to the user."""
        # Only log significant status changes, not repetitive ones
        if text and text != self._state.status_text:
            logger.debug("Screen status: %s", text)
        self._state.status_text = text

    def update_timer(self, **timer_state: Any) -> None:
        """Update timer-related UI and manage timer state."""
        # Only log status changes, not countdown updates
        old_status = self._state.timer_state.get("status")
        new_status = timer_state.get("status")
        if old_status != new_status:
            logger.info("Timer status: %s -> %s", old_status or "none", new_status)

        self._state.timer_state.update(timer_state)

        # Manage active state tracking
        if new_status in ("running", "paused"):
            self.add_active_state("timer")
            # Push pomodoro view if we're currently on idle
            if self._state.active_view == "idle":
                self.push_view("pomodoro")
        elif new_status == "completed":
            self.remove_active_state("timer")
            # If we're in the pomodoro view and timer completes, pop back
            if self._state.active_view == "pomodoro":
                self.pop_view()

    def update_idea_view(self, **idea_state: Any) -> None:
        """Update the idea/notebook-related UI and manage idea state."""
        logger.debug("Screen idea view: %s", idea_state)
        self._state.idea_view.update(idea_state)

        # If an idea becomes active and we're not already in ideas view, push it
        if idea_state.get("is_active") and self._state.active_view != "ideas":
            self.add_active_state("idea")
            self.push_view("ideas")

    def set_active_idea(self, idea_id: str, text: str) -> None:
        """Set the currently active idea being discussed."""
        self._state.active_idea_id = idea_id
        self._state.active_idea_text = text
        self._state.idea_last_updated = time.time()
        self._state.idea_view.update(
            {
                "active_idea_id": idea_id,
                "draft_text": text,
                "is_active": True,
                "last_updated": self._state.idea_last_updated,
            }
        )

        # Mark idea as active and navigate to ideas view
        self.add_active_state("idea")
        if self._state.active_view != "ideas":
            self.push_view("ideas")

        logger.info("Active idea set: %s", idea_id[:8] if idea_id else "none")

    def clear_active_idea(self) -> None:
        """Clear the active idea (user moved on to a different topic)."""
        self._state.active_idea_id = None
        self._state.active_idea_text = ""
        self._state.idea_last_updated = None
        self._state.idea_view["is_active"] = False

        # Remove idea from active states
        self.remove_active_state("idea")

        # If we're in the ideas view, navigate back to previous view
        if self._state.active_view == "ideas":
            self.pop_view()

        logger.debug("Active idea cleared")

    def is_idea_active(self, timeout_seconds: float = 300) -> bool:
        """Check if an idea is actively being discussed (within timeout).

        Args:
            timeout_seconds: How long an idea stays "active" without updates (default 5 min)

        Returns:
            True if there's an active idea within the timeout window
        """
        if not self._state.active_idea_id or not self._state.idea_last_updated:
            return False
        return (time.time() - self._state.idea_last_updated) < timeout_seconds

    def get_active_idea_id(self) -> Optional[str]:
        """Get the active idea ID if one is being discussed."""
        if self.is_idea_active():
            return self._state.active_idea_id
        return None

    # ------------------------------------------------------------------
    # Todo-related methods
    # ------------------------------------------------------------------
    def show_todo_list(
        self,
        status: Optional[str] = None,
        category_id: Optional[str] = None,
    ) -> None:
        """Show the todo list view with optional filters.

        Args:
            status: Filter by status (todo, in_progress, completed, etc.)
            category_id: Filter by category ID
        """
        self._state.todo_filter_status = status
        self._state.selected_category_id = category_id

        # Navigate to todo list view
        if self._state.active_view != "todo_list":
            self.push_view("todo_list")

        logger.info("Showing todo list (status=%s, category=%s)", status, category_id)

    def set_active_todo(self, todo_id: str, title: str) -> None:
        """Set the currently active todo.

        Args:
            todo_id: The todo ID
            title: The todo title
        """
        self._state.active_todo_id = todo_id
        self._state.active_todo_title = title
        logger.info("Active todo set: %s - %s", todo_id[:8] if todo_id else "none", title)

    def clear_active_todo(self) -> None:
        """Clear the active todo."""
        self._state.active_todo_id = None
        self._state.active_todo_title = ""
        logger.debug("Active todo cleared")

    def get_active_todo_id(self) -> Optional[str]:
        """Get the active todo ID if one is set."""
        return self._state.active_todo_id

    def update_todo_list(
        self,
        status: Optional[str] = None,
        category_id: Optional[str] = None,
    ) -> None:
        """Update todo list filters.

        Args:
            status: New status filter
            category_id: New category filter
        """
        if status is not None:
            self._state.todo_filter_status = status
        if category_id is not None:
            self._state.selected_category_id = category_id
        logger.debug("Todo list filters updated (status=%s, category=%s)", status, category_id)

    def get_todo_state(self) -> Dict[str, Any]:
        """Get current todo-related state.

        Returns:
            Dict with active_todo_id, filter_status, and selected_category_id
        """
        return {
            "active_todo_id": self._state.active_todo_id,
            "active_todo_title": self._state.active_todo_title,
            "filter_status": self._state.todo_filter_status,
            "selected_category_id": self._state.selected_category_id,
        }

    # ------------------------------------------------------------------
    # Calendar-related methods
    # ------------------------------------------------------------------
    def show_calendar(
        self,
        view_mode: str = "upcoming",
        selected_date: Optional[str] = None,
        filter_type: Optional[str] = None,
    ) -> None:
        """Show the calendar view with optional configuration.

        Args:
            view_mode: Calendar view mode (upcoming, today, week, month)
            selected_date: ISO format date string for focused date
            filter_type: Filter by event type (event, meeting, task, reminder)
        """
        self._state.calendar_view_mode = view_mode
        self._state.calendar_selected_date = selected_date
        self._state.calendar_filter_type = filter_type

        # Navigate to calendar view
        if self._state.active_view != "calendar":
            self.push_view("calendar")

        logger.info(
            "Showing calendar (mode=%s, date=%s, filter=%s)",
            view_mode,
            selected_date,
            filter_type,
        )

    def set_active_event(self, event_id: str, title: str = "") -> None:
        """Set the currently active/selected event.

        Args:
            event_id: The event ID
            title: The event title
        """
        self._state.active_event_id = event_id
        self._state.active_event_title = title
        logger.info(
            "Active event set: %s - %s",
            event_id[:8] if event_id else "none",
            title,
        )

    def clear_active_event(self) -> None:
        """Clear the active event."""
        self._state.active_event_id = None
        self._state.active_event_title = ""
        logger.debug("Active event cleared")

    def get_active_event_id(self) -> Optional[str]:
        """Get the active event ID if one is set."""
        return self._state.active_event_id

    def update_calendar_view(
        self,
        view_mode: Optional[str] = None,
        selected_date: Optional[str] = None,
        filter_type: Optional[str] = None,
    ) -> None:
        """Update calendar view configuration.

        Args:
            view_mode: New view mode
            selected_date: New selected date
            filter_type: New event type filter
        """
        if view_mode is not None:
            self._state.calendar_view_mode = view_mode
        if selected_date is not None:
            self._state.calendar_selected_date = selected_date
        if filter_type is not None:
            self._state.calendar_filter_type = filter_type
        logger.debug(
            "Calendar view updated (mode=%s, date=%s, filter=%s)",
            view_mode,
            selected_date,
            filter_type,
        )

    def get_calendar_state(self) -> Dict[str, Any]:
        """Get current calendar-related state.

        Returns:
            Dict with active_event_id, view_mode, selected_date, and filter_type
        """
        return {
            "active_event_id": self._state.active_event_id,
            "active_event_title": self._state.active_event_title,
            "view_mode": self._state.calendar_view_mode,
            "selected_date": self._state.calendar_selected_date,
            "filter_type": self._state.calendar_filter_type,
        }


__all__ = ["ScreenManager", "ScreenState"]
