"""Conversation and UI state API endpoints for Phase 3."""

from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.services.conversation_service import ConversationService, ConversationTurn
from backend.services.screen_manager import ScreenManager
from backend.services.tools_service import ToolsService


router = APIRouter(prefix="/conversation", tags=["conversation"])


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1)
    user_id: str = Field(default="default")


class ChatResponse(BaseModel):
    response: str
    intent: str


class TurnResponse(BaseModel):
    role: str
    content: str


class UIStateResponse(BaseModel):
    active_view: str
    status_text: str
    timer_state: dict
    idea_view: dict
    view_stack: List[str] = Field(default_factory=lambda: ["idle"])
    active_states: List[str] = Field(default_factory=list)
    # Todo state
    todo_filter_status: Optional[str] = None
    selected_category_id: Optional[str] = None
    active_todo_id: Optional[str] = None
    # Calendar state
    calendar_view_mode: str = "upcoming"
    calendar_selected_date: Optional[str] = None
    calendar_filter_type: Optional[str] = None
    active_event_id: Optional[str] = None


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> Any:
    """Handle a single conversational turn."""
    service = ConversationService.get_instance()
    result = await service._handle_utterance_async(  # type: ignore[attr-defined]
        text=req.text,
        user_id=req.user_id,
    )
    return ChatResponse(response=result["response"], intent=result.get("intent", "chat"))


@router.get("/history", response_model=List[TurnResponse])
async def history(user_id: str = "default") -> Any:
    """Return recent conversation history for a user."""
    service = ConversationService.get_instance()
    turns: List[ConversationTurn] = service.get_history(user_id=user_id)
    return [TurnResponse(role=t.role, content=t.content) for t in turns]


@router.get("/ui/state", response_model=UIStateResponse)
async def ui_state() -> Any:
    """Expose current screen/UI state for GUI client consumption."""
    # Check for timer transitions before returning state
    screen = ScreenManager.get_instance()
    state = screen.state
    
    # If there's an active timer session, check for transitions
    if state.timer_state and state.timer_state.get("session_id"):
        try:
            tools_service = ToolsService.get_instance()
            timer_tool = tools_service.get_tool("timer")
            session_id = state.timer_state.get("session_id")
            if session_id:
                # This will check and handle transitions
                timer_tool.get_session(session_id)
        except (KeyError, AttributeError):
            # Timer tool or session not found, continue without checking
            pass
    
    return UIStateResponse(
        active_view=state.active_view,
        status_text=state.status_text,
        timer_state=state.timer_state,
        idea_view=state.idea_view,
        view_stack=state.view_stack,
        active_states=state.active_states,
        todo_filter_status=state.todo_filter_status,
        selected_category_id=state.selected_category_id,
        active_todo_id=state.active_todo_id,
        calendar_view_mode=state.calendar_view_mode,
        calendar_selected_date=state.calendar_selected_date,
        calendar_filter_type=state.calendar_filter_type,
        active_event_id=state.active_event_id,
    )


@router.post("/ui/back")
async def go_back() -> Any:
    """Navigate back to the previous view."""
    screen = ScreenManager.get_instance()
    success = screen.go_back()
    return {"success": success, "current_view": screen.state.active_view}


class TodoFiltersRequest(BaseModel):
    """Request model for updating todo filters."""
    status: Optional[str] = None
    category_id: Optional[str] = None


@router.post("/ui/update_todo_filters")
async def update_todo_filters(request: TodoFiltersRequest) -> Any:
    """Update todo list filters."""
    screen = ScreenManager.get_instance()
    screen.update_todo_list(
        status=request.status,
        category_id=request.category_id,
    )
    return {"success": True, "filters": {"status": request.status, "category_id": request.category_id}}


@router.post("/ui/show_todo_list")
async def show_todo_list(status: Optional[str] = None, category_id: Optional[str] = None) -> Any:
    """Show the todo list view with optional filters."""
    screen = ScreenManager.get_instance()
    screen.show_todo_list(status=status, category_id=category_id)
    return {"success": True, "view": "todo_list"}


class CalendarViewRequest(BaseModel):
    """Request to update calendar view settings."""
    view_mode: Optional[str] = None
    selected_date: Optional[str] = None
    filter_type: Optional[str] = None


@router.post("/ui/update_calendar_view")
async def update_calendar_view(request: CalendarViewRequest) -> Any:
    """Update calendar view settings."""
    screen = ScreenManager.get_instance()
    screen.update_calendar_view(
        view_mode=request.view_mode,
        selected_date=request.selected_date,
        filter_type=request.filter_type,
    )
    return {
        "success": True,
        "calendar_state": {
            "view_mode": request.view_mode,
            "selected_date": request.selected_date,
            "filter_type": request.filter_type,
        }
    }


@router.post("/ui/show_calendar")
async def show_calendar(
    view_mode: str = "upcoming",
    selected_date: Optional[str] = None,
    filter_type: Optional[str] = None
) -> Any:
    """Show the calendar view with optional configuration."""
    screen = ScreenManager.get_instance()
    screen.show_calendar(view_mode=view_mode, selected_date=selected_date, filter_type=filter_type)
    return {"success": True, "view": "calendar"}



