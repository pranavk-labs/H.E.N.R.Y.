"""Conversation and UI state API endpoints for Phase 3."""

from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.services.conversation_service import ConversationService, ConversationTurn
from backend.services.screen_manager import ScreenManager


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
    screen = ScreenManager.get_instance()
    state = screen.state
    return UIStateResponse(
        active_view=state.active_view,
        status_text=state.status_text,
        timer_state=state.timer_state,
        idea_view=state.idea_view,
    )



