"""Productivity tools API endpoints (Pomodoro + Ideas).

These endpoints are thin wrappers over the underlying tools/services and
are intended primarily for remote access or debugging. Higher-level
interaction layers (e.g., voice) can call the tools directly instead.
"""

from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.knowledge_service import KnowledgeService
from backend.services.tools_service import ToolsService
from tools.timer_tool import PomodoroSession


router = APIRouter(prefix="/productivity", tags=["productivity"])


# ---------------------------------------------------------------------------
# Pomodoro models
# ---------------------------------------------------------------------------


class PomodoroStartRequest(BaseModel):
    work_duration_minutes: int = Field(default=25, ge=1, le=180)
    break_duration_minutes: int = Field(default=5, ge=1, le=60)


class PomodoroSessionResponse(BaseModel):
    id: str
    work_duration_minutes: int
    break_duration_minutes: int
    status: str
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_work_seconds: int


# ---------------------------------------------------------------------------
# Idea models
# ---------------------------------------------------------------------------


class IdeaCreateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)


class IdeaUpdateRequest(BaseModel):
    text: Optional[str] = None
    tags: Optional[List[str]] = None


class IdeaResponse(BaseModel):
    id: str
    text: str
    tags: List[str]
    created_at: str
    updated_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Pomodoro endpoints
# ---------------------------------------------------------------------------


@router.post("/pomodoro/start", response_model=PomodoroSessionResponse)
async def start_pomodoro(req: PomodoroStartRequest) -> Any:
    """Start a new Pomodoro session."""
    tools_service = ToolsService.get_instance()
    result = tools_service.execute_tool(
        "timer",
        "start",
        work_duration_minutes=req.work_duration_minutes,
        break_duration_minutes=req.break_duration_minutes,
    )
    return result["session"]


@router.post("/pomodoro/{session_id}/pause", response_model=PomodoroSessionResponse)
async def pause_pomodoro(session_id: str) -> Any:
    tools_service = ToolsService.get_instance()
    try:
        result = tools_service.execute_tool("timer", "pause", session_id=session_id)
        return result["session"]
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")


@router.post("/pomodoro/{session_id}/resume", response_model=PomodoroSessionResponse)
async def resume_pomodoro(session_id: str) -> Any:
    tools_service = ToolsService.get_instance()
    try:
        result = tools_service.execute_tool("timer", "resume", session_id=session_id)
        return result["session"]
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")


@router.post("/pomodoro/{session_id}/complete", response_model=PomodoroSessionResponse)
async def complete_pomodoro(session_id: str) -> Any:
    tools_service = ToolsService.get_instance()
    try:
        result = tools_service.execute_tool("timer", "complete", session_id=session_id)
        return result["session"]
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")


@router.post("/pomodoro/{session_id}/stop", response_model=PomodoroSessionResponse)
async def stop_pomodoro(session_id: str) -> Any:
    """Stop/end a Pomodoro session immediately."""
    tools_service = ToolsService.get_instance()
    try:
        result = tools_service.execute_tool("timer", "stop", session_id=session_id)
        return result["session"]
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("/pomodoro/{session_id}", response_model=PomodoroSessionResponse)
async def get_pomodoro(session_id: str) -> Any:
    tools_service = ToolsService.get_instance()
    try:
        timer_tool = tools_service.get_tool("timer")
        session = timer_tool.get_session(session_id)
        return session.to_dict()
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found")


@router.get("/pomodoro", response_model=list[PomodoroSessionResponse])
async def list_pomodoros() -> Any:
    tools_service = ToolsService.get_instance()
    timer_tool = tools_service.get_tool("timer")
    return [s.to_dict() for s in timer_tool.list_sessions()]


# ---------------------------------------------------------------------------
# Idea endpoints
# ---------------------------------------------------------------------------


@router.post("/ideas", response_model=IdeaResponse)
async def create_idea(req: IdeaCreateRequest) -> Any:
    knowledge = KnowledgeService.get_instance()
    idea = knowledge.create_idea(text=req.text, tags=req.tags)
    return idea.__dict__


@router.get("/ideas", response_model=list[IdeaResponse])
async def list_ideas() -> Any:
    knowledge = KnowledgeService.get_instance()
    ideas = knowledge.list_ideas()
    return [i.__dict__ for i in ideas]


@router.get("/ideas/search", response_model=list[IdeaResponse])
async def search_ideas(q: str) -> Any:
    """Naive search over idea text and tags."""
    knowledge = KnowledgeService.get_instance()
    ideas = knowledge.search_ideas(q)
    return [i.__dict__ for i in ideas]


@router.get("/ideas/{idea_id}", response_model=IdeaResponse)
async def get_idea(idea_id: str) -> Any:
    knowledge = KnowledgeService.get_instance()
    idea = knowledge.get_idea(idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea.__dict__


@router.put("/ideas/{idea_id}", response_model=IdeaResponse)
async def update_idea(idea_id: str, req: IdeaUpdateRequest) -> Any:
    knowledge = KnowledgeService.get_instance()
    idea = knowledge.update_idea(
        idea_id=idea_id,
        text=req.text,
        tags=req.tags,
    )
    if idea is None:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea.__dict__


@router.delete("/ideas/{idea_id}")
async def delete_idea(idea_id: str) -> Any:
    knowledge = KnowledgeService.get_instance()
    deleted = knowledge.delete_idea(idea_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Idea not found")
    return {"deleted": True, "idea_id": idea_id}


@router.post("/ideas/close")
async def close_idea() -> Any:
    """Close the currently active idea view without deleting the idea."""
    tools_service = ToolsService.get_instance()
    result = tools_service.execute_tool("ideas", "close")
    return result



