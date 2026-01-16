"""Todo/task management API routes."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services.knowledge_service import KnowledgeService
from backend.services.screen_manager import ScreenManager
from tools.todo_tool import TodoTool
from tools.base import ToolContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["todos"])

# Initialize services
_knowledge_service = KnowledgeService.get_instance()
_screen_manager = ScreenManager.get_instance()
_tool_context = ToolContext(
    knowledge_service=_knowledge_service,
    screen_manager=_screen_manager,
)
_todo_tool = TodoTool(_tool_context)


# Request/Response Models
class CreateTodoRequest(BaseModel):
    """Request model for creating a todo."""

    title: str
    description: str = ""
    priority: str = Field("medium", pattern="^(low|medium|high|critical)$")
    difficulty: int = Field(3, ge=1, le=5)
    category_id: Optional[str] = None
    due_date: Optional[str] = None
    estimated_minutes: Optional[int] = None
    recurrence_pattern: str = Field("none", pattern="^(none|daily|weekly|monthly)$")
    parent_todo_id: Optional[str] = None
    user_id: Optional[str] = None


class UpdateTodoRequest(BaseModel):
    """Request model for updating a todo."""

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|completed|cancelled)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|critical)$")
    difficulty: Optional[int] = Field(None, ge=1, le=5)
    category_id: Optional[str] = None
    due_date: Optional[str] = None
    estimated_minutes: Optional[int] = None
    recurrence_pattern: Optional[str] = Field(None, pattern="^(none|daily|weekly|monthly)$")


class CreateCategoryRequest(BaseModel):
    """Request model for creating a category."""

    name: str
    color: str = "#808080"
    icon: str = "📁"


class UpdateCategoryRequest(BaseModel):
    """Request model for updating a category."""

    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


# Todo routes
@router.get("/todos")
def list_todos(
    status: Optional[str] = Query(None, pattern="^(todo|in_progress|completed|cancelled)$"),
    category_id: Optional[str] = None,
    priority: Optional[str] = Query(None, pattern="^(low|medium|high|critical)$"),
    parent_todo_id: Optional[str] = None,
):
    """List todos with optional filtering."""
    try:
        result = _todo_tool.execute(
            "list",
            status=status,
            category_id=category_id,
            priority=priority,
            parent_todo_id=parent_todo_id,
        )
        return result
    except Exception as e:
        logger.error(f"Error listing todos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/todos")
def create_todo(request: CreateTodoRequest):
    """Create a new todo."""
    try:
        result = _todo_tool.execute(
            "create",
            title=request.title,
            description=request.description,
            priority=request.priority,
            difficulty=request.difficulty,
            category_id=request.category_id,
            due_date=request.due_date,
            estimated_minutes=request.estimated_minutes,
            recurrence_pattern=request.recurrence_pattern,
            parent_todo_id=request.parent_todo_id,
            user_id=request.user_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating todo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/todos/{todo_id}")
def get_todo(todo_id: str):
    """Get a specific todo by ID."""
    try:
        result = _todo_tool.execute("get", todo_id=todo_id)
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting todo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/todos/{todo_id}")
def update_todo(todo_id: str, request: UpdateTodoRequest):
    """Update an existing todo."""
    try:
        # Build update kwargs
        kwargs = {"todo_id": todo_id}
        if request.title is not None:
            kwargs["title"] = request.title
        if request.description is not None:
            kwargs["description"] = request.description
        if request.status is not None:
            kwargs["status"] = request.status
        if request.priority is not None:
            kwargs["priority"] = request.priority
        if request.difficulty is not None:
            kwargs["difficulty"] = request.difficulty
        if request.category_id is not None:
            kwargs["category_id"] = request.category_id
        if request.due_date is not None:
            kwargs["due_date"] = request.due_date
        if request.estimated_minutes is not None:
            kwargs["estimated_minutes"] = request.estimated_minutes
        if request.recurrence_pattern is not None:
            kwargs["recurrence_pattern"] = request.recurrence_pattern

        result = _todo_tool.execute("update", **kwargs)
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating todo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/todos/{todo_id}")
def delete_todo(todo_id: str):
    """Delete a todo."""
    try:
        result = _todo_tool.execute("delete", todo_id=todo_id)
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting todo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/todos/{todo_id}/complete")
def complete_todo(todo_id: str):
    """Mark a todo as completed."""
    try:
        result = _todo_tool.execute("complete", todo_id=todo_id)
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error completing todo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Category routes
@router.get("/categories")
def list_categories():
    """List all categories."""
    try:
        result = _todo_tool.execute("list_categories")
        return result
    except Exception as e:
        logger.error(f"Error listing categories: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/categories")
def create_category(request: CreateCategoryRequest):
    """Create a new category."""
    try:
        result = _todo_tool.execute(
            "create_category",
            name=request.name,
            color=request.color,
            icon=request.icon,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating category: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/categories/{category_id}")
def update_category(category_id: str, request: UpdateCategoryRequest):
    """Update an existing category."""
    try:
        kwargs = {"category_id": category_id}
        if request.name is not None:
            kwargs["name"] = request.name
        if request.color is not None:
            kwargs["color"] = request.color
        if request.icon is not None:
            kwargs["icon"] = request.icon

        result = _todo_tool.execute("update_category", **kwargs)
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating category: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/categories/{category_id}")
def delete_category(category_id: str):
    """Delete a category."""
    try:
        result = _todo_tool.execute("delete_category", category_id=category_id)
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting category: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Subtask routes
@router.post("/todos/{parent_id}/subtasks")
def add_subtask(parent_id: str, request: CreateTodoRequest):
    """Add a subtask to a parent todo."""
    try:
        result = _todo_tool.execute(
            "add_subtask",
            parent_todo_id=parent_id,
            title=request.title,
            description=request.description,
            priority=request.priority,
            difficulty=request.difficulty,
            user_id=request.user_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding subtask: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/todos/{parent_id}/subtasks")
def get_subtasks(parent_id: str):
    """Get all subtasks for a parent todo."""
    try:
        result = _todo_tool.execute("get_subtasks", parent_todo_id=parent_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting subtasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Relationship routes
@router.post("/todos/{todo_id}/link-idea")
def link_todo_to_idea(todo_id: str, idea_id: str = Query(...)):
    """Link a todo to an idea."""
    try:
        result = _todo_tool.execute("link_to_idea", todo_id=todo_id, idea_id=idea_id)
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error linking todo to idea: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/todos/{todo_id}/add-dependency")
def add_todo_dependency(todo_id: str, depends_on_id: str = Query(...)):
    """Add a dependency between todos."""
    try:
        result = _todo_tool.execute(
            "add_dependency", todo_id=todo_id, depends_on_id=depends_on_id
        )
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding todo dependency: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Timer integration
@router.post("/todos/{todo_id}/start-timer")
def start_timer_for_todo(
    todo_id: str,
    work_duration_minutes: int = Query(25, ge=1, le=120),
    break_duration_minutes: int = Query(5, ge=1, le=60),
):
    """Start a Pomodoro timer for a specific todo."""
    try:
        result = _todo_tool.execute(
            "start_timer",
            todo_id=todo_id,
            work_duration_minutes=work_duration_minutes,
            break_duration_minutes=break_duration_minutes,
        )
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting timer for todo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]

