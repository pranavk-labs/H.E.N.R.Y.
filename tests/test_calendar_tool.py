"""Tests for calendar and event management system."""

import pytest
from datetime import datetime, timezone, timedelta

from backend.services.knowledge_service import KnowledgeService
from backend.services.screen_manager import ScreenManager
from tools.base import ToolContext
from tools.calendar_tool import CalendarTool


@pytest.fixture
def knowledge_service():
    """Create a fresh knowledge service for testing."""
    service = KnowledgeService()
    yield service
    # Cleanup is automatic with in-memory graph


@pytest.fixture
def screen_manager():
    """Create a screen manager for testing."""
    # Reset singleton for clean state
    ScreenManager._instance = None
    return ScreenManager.get_instance()


@pytest.fixture
def tool_context(knowledge_service, screen_manager):
    """Create tool context."""
    return ToolContext(
        knowledge_service=knowledge_service,
        screen_manager=screen_manager,
    )


@pytest.fixture
def calendar_tool(tool_context):
    """Create calendar tool instance."""
    return CalendarTool(tool_context)


class TestCalendarTool:
    """Test CalendarTool operations."""

    def test_create_event(self, calendar_tool):
        """Test creating a simple event."""
        now = datetime.now(timezone.utc)
        start_time = (now + timedelta(hours=1)).isoformat()
        end_time = (now + timedelta(hours=2)).isoformat()

        result = calendar_tool.execute(
            "create",
            title="Team Meeting",
            start_time=start_time,
            end_time=end_time,
            description="Weekly team sync",
            location="Conference Room A",
        )

        assert result["action"] == "created"
        event = result["event"]
        assert event["title"] == "Team Meeting"
        assert event["start_time"] == start_time
        assert event["end_time"] == end_time
        assert event["description"] == "Weekly team sync"
        assert event["location"] == "Conference Room A"
        assert event["status"] == "scheduled"
        assert event["recurrence_pattern"] == "none"

    def test_create_recurring_event(self, calendar_tool):
        """Test creating a recurring event."""
        now = datetime.now(timezone.utc)
        start_time = (now + timedelta(days=1)).isoformat()
        recurrence_end = (now + timedelta(days=30)).isoformat()

        result = calendar_tool.execute(
            "create",
            title="Daily Standup",
            start_time=start_time,
            description="Daily team standup",
            recurrence_pattern="daily",
            recurrence_end_date=recurrence_end,
            reminder_minutes=15,
        )

        assert result["action"] == "created"
        event = result["event"]
        assert event["title"] == "Daily Standup"
        assert event["recurrence_pattern"] == "daily"
        assert event["recurrence_end_date"] == recurrence_end
        assert event["reminder_minutes"] == 15

    def test_create_event_with_attendees(self, calendar_tool):
        """Test creating an event with attendees."""
        now = datetime.now(timezone.utc)
        start_time = (now + timedelta(hours=2)).isoformat()

        result = calendar_tool.execute(
            "create",
            title="Client Call",
            start_time=start_time,
            attendees=["alice@example.com", "bob@example.com"],
            event_type="meeting",
        )

        event = result["event"]
        assert event["title"] == "Client Call"
        assert len(event["attendees"]) == 2
        assert "alice@example.com" in event["attendees"]
        assert "bob@example.com" in event["attendees"]
        assert event["event_type"] == "meeting"

    def test_get_event(self, calendar_tool):
        """Test retrieving an event."""
        now = datetime.now(timezone.utc)
        start_time = (now + timedelta(hours=1)).isoformat()

        create_result = calendar_tool.execute(
            "create",
            title="Test Event",
            start_time=start_time,
        )
        event_id = create_result["event"]["id"]

        result = calendar_tool.execute("get", event_id=event_id)
        event = result["event"]

        assert event["id"] == event_id
        assert event["title"] == "Test Event"

    def test_update_event(self, calendar_tool):
        """Test updating an event."""
        now = datetime.now(timezone.utc)
        start_time = (now + timedelta(hours=1)).isoformat()

        create_result = calendar_tool.execute(
            "create",
            title="Original Title",
            start_time=start_time,
        )
        event_id = create_result["event"]["id"]

        result = calendar_tool.execute(
            "update",
            event_id=event_id,
            title="Updated Title",
            description="Updated description",
            location="New Location",
        )

        assert result["action"] == "updated"
        event = result["event"]
        assert event["title"] == "Updated Title"
        assert event["description"] == "Updated description"
        assert event["location"] == "New Location"
        assert event["updated_at"] is not None

    def test_delete_event(self, calendar_tool):
        """Test deleting an event."""
        now = datetime.now(timezone.utc)
        start_time = (now + timedelta(hours=1)).isoformat()

        create_result = calendar_tool.execute(
            "create",
            title="To Delete",
            start_time=start_time,
        )
        event_id = create_result["event"]["id"]

        result = calendar_tool.execute("delete", event_id=event_id)
        assert result["deleted"] is True
        assert result["event_id"] == event_id

        # Verify event is gone
        with pytest.raises(KeyError):
            calendar_tool.execute("get", event_id=event_id)

    def test_list_events(self, calendar_tool):
        """Test listing events."""
        now = datetime.now(timezone.utc)

        # Create multiple events
        calendar_tool.execute(
            "create",
            title="Event 1",
            start_time=(now + timedelta(hours=1)).isoformat(),
            event_type="meeting",
        )
        calendar_tool.execute(
            "create",
            title="Event 2",
            start_time=(now + timedelta(hours=2)).isoformat(),
            event_type="event",
        )
        calendar_tool.execute(
            "create",
            title="Event 3",
            start_time=(now + timedelta(hours=3)).isoformat(),
            status="cancelled",
        )

        # List all events
        result = calendar_tool.execute("list")
        assert result["count"] == 3
        assert len(result["events"]) == 3

        # List by status
        result = calendar_tool.execute("list", status="scheduled")
        assert result["count"] == 2

        # List by event type
        result = calendar_tool.execute("list", event_type="meeting")
        assert result["count"] == 1
        assert result["events"][0]["title"] == "Event 1"

    def test_search_events(self, calendar_tool):
        """Test searching events."""
        now = datetime.now(timezone.utc)

        calendar_tool.execute(
            "create",
            title="Python Workshop",
            start_time=(now + timedelta(hours=1)).isoformat(),
            description="Learn Python basics",
        )
        calendar_tool.execute(
            "create",
            title="JavaScript Meetup",
            start_time=(now + timedelta(hours=2)).isoformat(),
            location="Python Building",
        )

        # Search by title
        result = calendar_tool.execute("search", query="python")
        assert result["count"] == 2  # Matches both title and location

        # Search by description
        result = calendar_tool.execute("search", query="javascript")
        assert result["count"] == 1
        assert result["events"][0]["title"] == "JavaScript Meetup"

    def test_get_upcoming_events(self, calendar_tool):
        """Test getting upcoming events."""
        now = datetime.now(timezone.utc)

        # Create past, present, and future events
        calendar_tool.execute(
            "create",
            title="Past Event",
            start_time=(now - timedelta(hours=1)).isoformat(),
        )
        calendar_tool.execute(
            "create",
            title="Future Event 1",
            start_time=(now + timedelta(hours=1)).isoformat(),
        )
        calendar_tool.execute(
            "create",
            title="Future Event 2",
            start_time=(now + timedelta(hours=2)).isoformat(),
        )

        result = calendar_tool.execute("get_upcoming", limit=10)
        # Should only include future events
        assert result["count"] == 2
        assert all("Future" in e["title"] for e in result["events"])

    def test_get_today_events(self, calendar_tool):
        """Test getting today's events."""
        now = datetime.now(timezone.utc)
        tomorrow = now + timedelta(days=1)

        # Create events for today and tomorrow
        calendar_tool.execute(
            "create",
            title="Today Event",
            start_time=now.replace(hour=14, minute=0).isoformat(),
        )
        calendar_tool.execute(
            "create",
            title="Tomorrow Event",
            start_time=tomorrow.replace(hour=10, minute=0).isoformat(),
        )

        result = calendar_tool.execute("get_today")
        # Should only include today's events
        assert result["count"] == 1
        assert result["events"][0]["title"] == "Today Event"

    def test_cancel_event(self, calendar_tool):
        """Test cancelling an event."""
        now = datetime.now(timezone.utc)
        start_time = (now + timedelta(hours=1)).isoformat()

        create_result = calendar_tool.execute(
            "create",
            title="To Cancel",
            start_time=start_time,
        )
        event_id = create_result["event"]["id"]

        result = calendar_tool.execute(
            "update",
            event_id=event_id,
            status="cancelled",
        )

        event = result["event"]
        assert event["status"] == "cancelled"

    def test_invalid_date_format(self, calendar_tool):
        """Test that invalid date formats raise errors."""
        with pytest.raises(ValueError, match="Invalid start_time format"):
            calendar_tool.execute(
                "create",
                title="Bad Date Event",
                start_time="not-a-date",
            )

    def test_screen_manager_integration(self, calendar_tool, screen_manager):
        """Test that calendar tool updates screen manager state."""
        now = datetime.now(timezone.utc)
        start_time = (now + timedelta(hours=1)).isoformat()

        calendar_tool.execute(
            "create",
            title="Test Event",
            start_time=start_time,
        )

        # Screen manager should have updated status
        assert "created" in screen_manager.state.status_text.lower()


class TestRecurringEvents:
    """Test recurring event generation."""

    def test_generate_daily_recurring_events(self, knowledge_service):
        """Test generating daily recurring event instances."""
        now = datetime.now(timezone.utc)
        start_time = (now + timedelta(hours=1)).isoformat()

        # Create a recurring event template
        event_id = knowledge_service._write_node(
            "test-recurring-daily",
            label="CalendarEvent",
            title="Daily Exercise",
            start_time=start_time,
            end_time="",
            description="Morning workout",
            location="Gym",
            recurrence_pattern="daily",
            recurrence_end_date="",
            reminder_minutes=0,
            attendees=[],
            event_type="task",
            status="scheduled",
            created_at=now.isoformat(),
        )

        # Generate instances
        created_events = knowledge_service.check_and_create_recurring_events(days_ahead=7)

        # Should create 7 daily instances (one per day for a week ahead)
        # Note: Actual count might be less if some events are in the past
        assert len(created_events) >= 5  # At least 5 instances should be created

    def test_generate_weekly_recurring_events(self, knowledge_service):
        """Test generating weekly recurring event instances."""
        now = datetime.now(timezone.utc)
        start_time = (now + timedelta(hours=1)).isoformat()

        # Create a recurring event template
        knowledge_service._write_node(
            "test-recurring-weekly",
            label="CalendarEvent",
            title="Weekly Team Meeting",
            start_time=start_time,
            end_time="",
            description="Weekly sync",
            location="",
            recurrence_pattern="weekly",
            recurrence_end_date="",
            reminder_minutes=0,
            attendees=[],
            event_type="meeting",
            status="scheduled",
            created_at=now.isoformat(),
        )

        # Generate instances
        created_events = knowledge_service.check_and_create_recurring_events(days_ahead=30)

        # Should create ~4 weekly instances for a month ahead
        assert len(created_events) >= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
