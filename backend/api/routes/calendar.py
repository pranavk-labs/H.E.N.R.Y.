"""Calendar and event management API endpoints.

These endpoints provide REST API access to the calendar tool for
remote access, GUI clients, and debugging. The voice pipeline can
call the calendar tool directly instead.
"""

from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.knowledge_service import KnowledgeService
from backend.services.tools_service import ToolsService


router = APIRouter(prefix="/calendar", tags=["calendar"])


# ---------------------------------------------------------------------------
# Calendar models
# ---------------------------------------------------------------------------


class EventCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    start_time: str = Field(..., description="ISO 8601 datetime string")
    end_time: Optional[str] = Field(None, description="ISO 8601 datetime string")
    description: str = Field(default="", max_length=1000)
    location: str = Field(default="", max_length=200)
    recurrence_pattern: str = Field(
        default="none",
        pattern="^(none|daily|weekly|monthly|yearly)$"
    )
    recurrence_end_date: Optional[str] = Field(None, description="ISO 8601 datetime string")
    reminder_minutes: Optional[int] = Field(None, ge=0, le=10080)
    attendees: List[str] = Field(default_factory=list)
    event_type: str = Field(
        default="event",
        pattern="^(event|meeting|task|reminder)$"
    )
    user_id: Optional[str] = None


class EventUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    start_time: Optional[str] = Field(None, description="ISO 8601 datetime string")
    end_time: Optional[str] = Field(None, description="ISO 8601 datetime string")
    description: Optional[str] = Field(None, max_length=1000)
    location: Optional[str] = Field(None, max_length=200)
    recurrence_pattern: Optional[str] = Field(
        None,
        pattern="^(none|daily|weekly|monthly|yearly)$"
    )
    recurrence_end_date: Optional[str] = Field(None, description="ISO 8601 datetime string")
    reminder_minutes: Optional[int] = Field(None, ge=0, le=10080)
    attendees: Optional[List[str]] = None
    event_type: Optional[str] = Field(
        None,
        pattern="^(event|meeting|task|reminder)$"
    )
    status: Optional[str] = Field(
        None,
        pattern="^(scheduled|cancelled|completed)$"
    )


class EventResponse(BaseModel):
    id: str
    title: str
    start_time: str
    end_time: Optional[str]
    description: str
    location: str
    recurrence_pattern: str
    recurrence_end_date: Optional[str]
    reminder_minutes: Optional[int]
    attendees: List[str]
    event_type: str
    status: str
    created_at: str
    updated_at: Optional[str]


class EventListResponse(BaseModel):
    events: List[EventResponse]
    count: int


# ---------------------------------------------------------------------------
# Event endpoints
# ---------------------------------------------------------------------------


@router.post("/events", response_model=EventResponse)
async def create_event(req: EventCreateRequest) -> Any:
    """Create a new calendar event."""
    tools_service = ToolsService.get_instance()
    try:
        result = tools_service.execute_tool(
            "calendar",
            "create",
            title=req.title,
            start_time=req.start_time,
            end_time=req.end_time,
            description=req.description,
            location=req.location,
            recurrence_pattern=req.recurrence_pattern,
            recurrence_end_date=req.recurrence_end_date,
            reminder_minutes=req.reminder_minutes,
            attendees=req.attendees,
            event_type=req.event_type,
            user_id=req.user_id,
        )
        return result["event"]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/events", response_model=EventListResponse)
async def list_events(
    status: Optional[str] = None,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Any:
    """List calendar events with optional filters."""
    tools_service = ToolsService.get_instance()
    result = tools_service.execute_tool(
        "calendar",
        "list",
        status=status,
        event_type=event_type,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )
    return result


@router.get("/events/upcoming", response_model=EventListResponse)
async def get_upcoming_events(limit: int = 10) -> Any:
    """Get upcoming events."""
    tools_service = ToolsService.get_instance()
    result = tools_service.execute_tool(
        "calendar",
        "get_upcoming",
        limit=limit,
    )
    return result


@router.get("/events/today", response_model=EventListResponse)
async def get_today_events() -> Any:
    """Get today's events."""
    tools_service = ToolsService.get_instance()
    result = tools_service.execute_tool("calendar", "get_today")
    return result


@router.get("/events/search", response_model=EventListResponse)
async def search_events(q: str) -> Any:
    """Search events by query string."""
    tools_service = ToolsService.get_instance()
    result = tools_service.execute_tool("calendar", "search", query=q)
    return result


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: str) -> Any:
    """Get a specific event by ID."""
    tools_service = ToolsService.get_instance()
    try:
        result = tools_service.execute_tool("calendar", "get", event_id=event_id)
        return result["event"]
    except KeyError:
        raise HTTPException(status_code=404, detail="Event not found")


@router.put("/events/{event_id}", response_model=EventResponse)
async def update_event(event_id: str, req: EventUpdateRequest) -> Any:
    """Update an existing event."""
    tools_service = ToolsService.get_instance()
    try:
        # Build kwargs from request, only including non-None values
        kwargs = {"event_id": event_id}
        if req.title is not None:
            kwargs["title"] = req.title
        if req.start_time is not None:
            kwargs["start_time"] = req.start_time
        if req.end_time is not None:
            kwargs["end_time"] = req.end_time
        if req.description is not None:
            kwargs["description"] = req.description
        if req.location is not None:
            kwargs["location"] = req.location
        if req.recurrence_pattern is not None:
            kwargs["recurrence_pattern"] = req.recurrence_pattern
        if req.recurrence_end_date is not None:
            kwargs["recurrence_end_date"] = req.recurrence_end_date
        if req.reminder_minutes is not None:
            kwargs["reminder_minutes"] = req.reminder_minutes
        if req.attendees is not None:
            kwargs["attendees"] = req.attendees
        if req.event_type is not None:
            kwargs["event_type"] = req.event_type
        if req.status is not None:
            kwargs["status"] = req.status

        result = tools_service.execute_tool("calendar", "update", **kwargs)
        return result["event"]
    except KeyError:
        raise HTTPException(status_code=404, detail="Event not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/events/{event_id}")
async def delete_event(event_id: str) -> Any:
    """Delete an event."""
    tools_service = ToolsService.get_instance()
    try:
        result = tools_service.execute_tool("calendar", "delete", event_id=event_id)
        return result
    except KeyError:
        raise HTTPException(status_code=404, detail="Event not found")


# ---------------------------------------------------------------------------
# Recurring event management
# ---------------------------------------------------------------------------


@router.post("/events/generate-recurring")
async def generate_recurring_events(
    user_id: Optional[str] = None,
    days_ahead: int = 30,
) -> Any:
    """Generate recurring event instances for the specified time period.

    This endpoint should be called periodically (e.g., daily) or on app startup
    to ensure recurring events have instances created ahead of time.
    """
    knowledge = KnowledgeService.get_instance()
    created_events = knowledge.check_and_create_recurring_events(
        user_id=user_id,
        days_ahead=days_ahead,
    )
    return {
        "created_events": created_events,
        "count": len(created_events),
    }
