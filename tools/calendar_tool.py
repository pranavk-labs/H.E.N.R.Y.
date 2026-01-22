"""Calendar and event scheduling tool with recurring event support.

This tool manages calendar events with support for:
- One-time and recurring events
- Event reminders and notifications
- Location and attendee tracking
- Integration with the knowledge graph
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services.knowledge_service import KnowledgeService
from backend.services.screen_manager import ScreenManager
from tools.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


class CalendarTool(BaseTool):
    """Tool for managing calendar events and schedules."""

    name = "calendar"

    def __init__(self, context: ToolContext) -> None:
        super().__init__(context)
        self._knowledge: KnowledgeService = context.knowledge_service
        self._screen: ScreenManager = context.screen_manager

    def execute(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute calendar operations.

        Supported actions:
        - create: Create a new event
        - update: Update an existing event
        - get: Retrieve a specific event
        - list: List events (with optional filters)
        - delete: Delete an event
        - search: Search events by query
        - get_upcoming: Get upcoming events
        - get_today: Get today's events
        """
        action = action.lower()

        if action == "create":
            return self._create_event(**kwargs)

        if action == "update":
            return self._update_event(**kwargs)

        if action == "get":
            return self._get_event(**kwargs)

        if action == "list":
            return self._list_events(**kwargs)

        if action == "delete":
            return self._delete_event(**kwargs)

        if action == "search":
            return self._search_events(**kwargs)

        if action == "get_upcoming":
            return self._get_upcoming_events(**kwargs)

        if action == "get_today":
            return self._get_today_events()

        raise ValueError(f"Unknown calendar action '{action}'")

    def _create_event(
        self,
        title: str,
        start_time: str,
        end_time: Optional[str] = None,
        description: str = "",
        location: str = "",
        recurrence_pattern: str = "none",
        recurrence_end_date: Optional[str] = None,
        reminder_minutes: Optional[int] = None,
        attendees: Optional[List[str]] = None,
        event_type: str = "event",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new calendar event.

        Args:
            title: Event title
            start_time: Start time (ISO format)
            end_time: Optional end time (ISO format)
            description: Event description
            location: Event location
            recurrence_pattern: Recurrence pattern (none, daily, weekly, monthly, yearly)
            recurrence_end_date: When recurring event stops (ISO format)
            reminder_minutes: Minutes before event to remind (15, 30, 60, etc.)
            attendees: List of attendee names/emails
            event_type: Type of event (event, meeting, task, reminder)
            user_id: Optional user ID to create relationship

        Returns:
            Dictionary with created event data
        """
        event_id = str(uuid.uuid4())
        created_at = _utc_now_iso()

        # Validate start_time format
        try:
            datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid start_time format: {start_time}. Expected ISO format.") from e

        # Validate end_time if provided
        if end_time:
            try:
                datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid end_time format: {end_time}. Expected ISO format.") from e

        # Create event node in knowledge graph
        self._knowledge._write_node(
            event_id,
            label="CalendarEvent",
            title=title,
            start_time=start_time,
            end_time=end_time or "",
            description=description,
            location=location,
            recurrence_pattern=recurrence_pattern,
            recurrence_end_date=recurrence_end_date or "",
            reminder_minutes=reminder_minutes or 0,
            attendees=attendees or [],
            event_type=event_type,
            status="scheduled",
            created_at=created_at,
        )

        # Create relationship from User to Event if user_id is provided
        if user_id:
            user_node_id = f"user:{user_id}"
            if self._knowledge._read_node(user_node_id) is None:
                self._knowledge._write_node(user_node_id, label="User", user_id=user_id)

            self._knowledge._create_relationship(
                user_node_id,
                event_id,
                relationship_type="HAS_EVENT",
                created_at=created_at,
            )
            logger.info("Created event %s for user %s", event_id, user_id)
        else:
            logger.info("Created event %s (no user relationship)", event_id)

        # Update screen state
        self._screen.update_status(f"Event created: {title}")

        event_data = self._build_event_dict(event_id)
        return {"event": event_data, "action": "created"}

    def _update_event(
        self,
        event_id: str,
        title: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        recurrence_pattern: Optional[str] = None,
        recurrence_end_date: Optional[str] = None,
        reminder_minutes: Optional[int] = None,
        attendees: Optional[List[str]] = None,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing event.

        Args:
            event_id: Event ID to update
            (other args same as create_event, all optional)
            status: Event status (scheduled, cancelled, completed)

        Returns:
            Dictionary with updated event data
        """
        # Verify event exists
        data = self._knowledge._read_node(event_id)
        if not data or data.get("label") != "CalendarEvent":
            raise KeyError(f"Event '{event_id}' not found")

        # Build updates
        updates: Dict[str, Any] = {}
        if title is not None:
            updates["title"] = title
        if start_time is not None:
            # Validate format
            try:
                datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                updates["start_time"] = start_time
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid start_time format: {start_time}") from e
        if end_time is not None:
            try:
                datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                updates["end_time"] = end_time
            except (ValueError, AttributeError) as e:
                raise ValueError(f"Invalid end_time format: {end_time}") from e
        if description is not None:
            updates["description"] = description
        if location is not None:
            updates["location"] = location
        if recurrence_pattern is not None:
            updates["recurrence_pattern"] = recurrence_pattern
        if recurrence_end_date is not None:
            updates["recurrence_end_date"] = recurrence_end_date
        if reminder_minutes is not None:
            updates["reminder_minutes"] = reminder_minutes
        if attendees is not None:
            updates["attendees"] = attendees
        if event_type is not None:
            updates["event_type"] = event_type
        if status is not None:
            updates["status"] = status

        updates["updated_at"] = _utc_now_iso()

        # Update node
        self._knowledge._update_node(event_id, **updates)
        logger.info("Updated event %s", event_id)

        # Update screen state
        self._screen.update_status("Event updated")

        event_data = self._build_event_dict(event_id)
        return {"event": event_data, "action": "updated"}

    def _get_event(self, event_id: str) -> Dict[str, Any]:
        """Get a specific event by ID.

        Args:
            event_id: Event ID

        Returns:
            Dictionary with event data
        """
        event_data = self._build_event_dict(event_id)
        if not event_data:
            raise KeyError(f"Event '{event_id}' not found")
        return {"event": event_data}

    def _list_events(
        self,
        status: Optional[str] = None,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List events with optional filters.

        Args:
            status: Filter by status (scheduled, cancelled, completed)
            event_type: Filter by event type (event, meeting, task, reminder)
            user_id: Filter by user ID
            start_date: Filter events starting on or after this date (ISO format)
            end_date: Filter events starting on or before this date (ISO format)

        Returns:
            Dictionary with list of events
        """
        # Get all calendar events
        nodes = self._knowledge._list_nodes_by_label("CalendarEvent")

        events = []
        for node_data in nodes:
            event_id = node_data.get("id", "")

            # Apply filters
            if status and node_data.get("status") != status:
                continue
            if event_type and node_data.get("event_type") != event_type:
                continue

            # Filter by date range
            if start_date or end_date:
                event_start = node_data.get("start_time", "")
                if event_start:
                    try:
                        event_start_dt = datetime.fromisoformat(event_start.replace('Z', '+00:00'))
                        if start_date:
                            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                            if event_start_dt < start_dt:
                                continue
                        if end_date:
                            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                            if event_start_dt > end_dt:
                                continue
                    except (ValueError, AttributeError):
                        # Skip events with invalid dates
                        continue

            # Filter by user
            if user_id:
                user_node_id = f"user:{user_id}"
                neighbors = self._knowledge._get_neighbors(user_node_id)
                if event_id not in neighbors:
                    continue

            event_data = self._build_event_dict(event_id, node_data)
            if event_data:
                events.append(event_data)

        # Sort by start_time
        events.sort(key=lambda e: e.get("start_time", ""))

        return {"events": events, "count": len(events)}

    def _delete_event(self, event_id: str) -> Dict[str, Any]:
        """Delete an event.

        Args:
            event_id: Event ID to delete

        Returns:
            Dictionary with deletion confirmation
        """
        deleted = self._knowledge._delete_node(event_id)
        if not deleted:
            raise KeyError(f"Event '{event_id}' not found")

        logger.info("Deleted event %s", event_id)
        self._screen.update_status("Event deleted")

        return {"deleted": True, "event_id": event_id}

    def _search_events(self, query: str) -> Dict[str, Any]:
        """Search events by query string.

        Args:
            query: Search query (searches title, description, location)

        Returns:
            Dictionary with matching events
        """
        query_lower = query.lower().strip()
        if not query_lower:
            return {"events": [], "count": 0}

        nodes = self._knowledge._list_nodes_by_label("CalendarEvent")
        matches = []

        for node_data in nodes:
            event_id = node_data.get("id", "")
            title = node_data.get("title", "").lower()
            description = node_data.get("description", "").lower()
            location = node_data.get("location", "").lower()

            # Search in title, description, and location
            if (query_lower in title or
                query_lower in description or
                query_lower in location):
                event_data = self._build_event_dict(event_id, node_data)
                if event_data:
                    matches.append(event_data)

        # Sort by start_time
        matches.sort(key=lambda e: e.get("start_time", ""))

        return {"events": matches, "count": len(matches)}

    def _get_upcoming_events(self, limit: int = 10) -> Dict[str, Any]:
        """Get upcoming events.

        Args:
            limit: Maximum number of events to return (default 10)

        Returns:
            Dictionary with upcoming events
        """
        now = datetime.now(timezone.utc)
        nodes = self._knowledge._list_nodes_by_label("CalendarEvent")

        upcoming = []
        for node_data in nodes:
            event_id = node_data.get("id", "")
            start_time = node_data.get("start_time", "")
            status = node_data.get("status", "")

            # Skip cancelled/completed events
            if status in ["cancelled", "completed"]:
                continue

            if start_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    # Only include future events
                    if start_dt > now:
                        event_data = self._build_event_dict(event_id, node_data)
                        if event_data:
                            upcoming.append(event_data)
                except (ValueError, AttributeError):
                    # Skip events with invalid dates
                    continue

        # Sort by start_time and limit
        upcoming.sort(key=lambda e: e.get("start_time", ""))
        upcoming = upcoming[:limit]

        return {"events": upcoming, "count": len(upcoming)}

    def _get_today_events(self) -> Dict[str, Any]:
        """Get today's events.

        Returns:
            Dictionary with today's events
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        nodes = self._knowledge._list_nodes_by_label("CalendarEvent")

        today_events = []
        for node_data in nodes:
            event_id = node_data.get("id", "")
            start_time = node_data.get("start_time", "")
            status = node_data.get("status", "")

            # Skip cancelled events
            if status == "cancelled":
                continue

            if start_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    # Check if event is today
                    if today_start <= start_dt <= today_end:
                        event_data = self._build_event_dict(event_id, node_data)
                        if event_data:
                            today_events.append(event_data)
                except (ValueError, AttributeError):
                    # Skip events with invalid dates
                    continue

        # Sort by start_time
        today_events.sort(key=lambda e: e.get("start_time", ""))

        return {"events": today_events, "count": len(today_events)}

    def _build_event_dict(
        self, event_id: str, node_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Build event dictionary from node data.

        Args:
            event_id: Event ID
            node_data: Optional pre-fetched node data

        Returns:
            Event dictionary or None if not found
        """
        if node_data is None:
            node_data = self._knowledge._read_node(event_id)

        if not node_data or node_data.get("label") != "CalendarEvent":
            return None

        return {
            "id": event_id,
            "title": node_data.get("title", ""),
            "start_time": node_data.get("start_time", ""),
            "end_time": node_data.get("end_time") or None,
            "description": node_data.get("description", ""),
            "location": node_data.get("location", ""),
            "recurrence_pattern": node_data.get("recurrence_pattern", "none"),
            "recurrence_end_date": node_data.get("recurrence_end_date") or None,
            "reminder_minutes": node_data.get("reminder_minutes") or None,
            "attendees": list(node_data.get("attendees", []) or []),
            "event_type": node_data.get("event_type", "event"),
            "status": node_data.get("status", "scheduled"),
            "created_at": node_data.get("created_at", ""),
            "updated_at": node_data.get("updated_at") or None,
        }


__all__ = ["CalendarTool"]
