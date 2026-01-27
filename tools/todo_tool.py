"""Todo/Task management tool implementation with categories and relationships."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.services.knowledge_service import KnowledgeService, _utc_now_iso
from backend.services.screen_manager import ScreenManager
from tools.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


class TodoTool(BaseTool):
    """Tool for managing todos/tasks with categories, priorities, and relationships."""

    name = "todos"

    def __init__(self, context: ToolContext) -> None:
        super().__init__(context)
        self._knowledge = context.knowledge_service
        self._screen: ScreenManager = context.screen_manager

    def execute(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute a todo tool action and return a structured result."""
        action = action.lower()

        # Todo actions
        if action == "create":
            return self._create_todo(**kwargs)

        if action == "update":
            return self._update_todo(**kwargs)

        if action == "delete":
            return self._delete_todo(**kwargs)

        if action == "complete":
            return self._complete_todo(**kwargs)

        if action == "list":
            return self._list_todos(**kwargs)

        if action == "get":
            return self._get_todo(**kwargs)

        # Category actions
        if action == "create_category":
            return self._create_category(**kwargs)

        if action == "list_categories":
            return self._list_categories(**kwargs)

        if action == "update_category":
            return self._update_category(**kwargs)

        if action == "delete_category":
            return self._delete_category(**kwargs)

        # Subtask actions
        if action == "add_subtask" or action == "create_subtask":
            return self._add_subtask(**kwargs)

        if action == "get_subtasks":
            return self._get_subtasks(**kwargs)

        # Relationship actions
        if action == "link_to_idea":
            return self._link_to_idea(**kwargs)

        if action == "add_dependency":
            return self._add_dependency(**kwargs)

        # Timer integration
        if action == "start_timer":
            return self._start_timer(**kwargs)

        raise ValueError(f"Unknown todo tool action '{action}'")

    # ------------------------------------------------------------------
    # Todo operations
    # ------------------------------------------------------------------
    def _create_todo(self, **kwargs: Any) -> Dict[str, Any]:
        """Create a new todo."""
        title: str = kwargs.get("title", "")
        if not title:
            raise ValueError("title is required for create action")

        description: str = kwargs.get("description", "")
        priority: str = kwargs.get("priority", "medium")
        difficulty: int = int(kwargs.get("difficulty", 3))
        category_id: Optional[str] = kwargs.get("category_id")
        due_date: Optional[str] = kwargs.get("due_date")
        estimated_minutes: Optional[int] = kwargs.get("estimated_minutes")
        recurrence_pattern: str = kwargs.get("recurrence_pattern", "none")
        parent_todo_id: Optional[str] = kwargs.get("parent_todo_id")
        user_id: Optional[str] = kwargs.get("user_id")

        todo = self._knowledge.create_todo(
            title=title,
            description=description,
            priority=priority,
            difficulty=difficulty,
            category_id=category_id,
            due_date=due_date,
            estimated_minutes=estimated_minutes,
            recurrence_pattern=recurrence_pattern,
            parent_todo_id=parent_todo_id,
            user_id=user_id,
        )

        self._screen.set_active_todo(todo.id, todo.title)
        self._screen.update_status(f"Created: {todo.title}")

        return {
            "todo": KnowledgeService.todo_to_dict(todo),
            "action": "created",
            "message": f"Created todo: {todo.title}",
        }

    def _update_todo(self, **kwargs: Any) -> Dict[str, Any]:
        """Update an existing todo."""
        todo_id: Optional[str] = kwargs.get("todo_id")

        # If no todo_id provided, use the active todo
        if not todo_id:
            todo_id = self._screen.get_active_todo_id()
        if not todo_id:
            raise ValueError("No todo_id provided and no active todo to update")

        todo = self._knowledge.update_todo(
            todo_id=todo_id,
            title=kwargs.get("title"),
            description=kwargs.get("description"),
            status=kwargs.get("status"),
            priority=kwargs.get("priority"),
            difficulty=kwargs.get("difficulty"),
            category_id=kwargs.get("category_id"),
            due_date=kwargs.get("due_date"),
            estimated_minutes=kwargs.get("estimated_minutes"),
            recurrence_pattern=kwargs.get("recurrence_pattern"),
            completed_at=kwargs.get("completed_at"),
        )

        if todo is None:
            raise KeyError(f"Todo '{todo_id}' not found")

        self._screen.set_active_todo(todo.id, todo.title)
        self._screen.update_status(f"Updated: {todo.title}")

        return {
            "todo": KnowledgeService.todo_to_dict(todo),
            "action": "updated",
            "message": f"Updated todo: {todo.title}",
        }

    def _delete_todo(self, **kwargs: Any) -> Dict[str, Any]:
        """Delete a todo."""
        todo_id: str = kwargs.get("todo_id", "")
        if not todo_id:
            raise ValueError("todo_id is required for delete action")

        # Get todo title before deleting
        todo = self._knowledge.get_todo(todo_id)
        if not todo:
            raise KeyError(f"Todo '{todo_id}' not found")

        title = todo.title
        deleted = self._knowledge.delete_todo(todo_id)
        if not deleted:
            raise KeyError(f"Todo '{todo_id}' not found")

        # Clear active todo if we deleted it
        if self._screen.get_active_todo_id() == todo_id:
            self._screen.clear_active_todo()

        self._screen.update_status(f"Deleted: {title}")

        return {
            "deleted": True,
            "todo_id": todo_id,
            "message": f"Deleted todo: {title}",
        }

    def _complete_todo(self, **kwargs: Any) -> Dict[str, Any]:
        """Mark a todo as completed."""
        todo_id: Optional[str] = kwargs.get("todo_id")

        # If no todo_id provided, use the active todo
        if not todo_id:
            todo_id = self._screen.get_active_todo_id()
        if not todo_id:
            raise ValueError("No todo_id provided and no active todo to complete")

        todo = self._knowledge.update_todo(todo_id=todo_id, status="completed")
        if todo is None:
            raise KeyError(f"Todo '{todo_id}' not found")

        self._screen.update_status(f"Completed: {todo.title}")

        return {
            "todo": KnowledgeService.todo_to_dict(todo),
            "action": "completed",
            "message": f"Completed todo: {todo.title}",
        }

    def _get_todo(self, **kwargs: Any) -> Dict[str, Any]:
        """Get a specific todo."""
        todo_id: str = kwargs.get("todo_id", "")
        if not todo_id:
            raise ValueError("todo_id is required for get action")

        todo = self._knowledge.get_todo(todo_id)
        if todo is None:
            raise KeyError(f"Todo '{todo_id}' not found")

        return {"todo": KnowledgeService.todo_to_dict(todo)}

    def _list_todos(self, **kwargs: Any) -> Dict[str, Any]:
        """List todos with optional filtering."""
        status: Optional[str] = kwargs.get("status")
        category_id: Optional[str] = kwargs.get("category_id")
        priority: Optional[str] = kwargs.get("priority")
        parent_todo_id: Optional[str] = kwargs.get("parent_todo_id")

        todos = self._knowledge.list_todos(
            status=status,
            category_id=category_id,
            priority=priority,
            parent_todo_id=parent_todo_id,
        )

        return {
            "todos": [KnowledgeService.todo_to_dict(t) for t in todos],
            "count": len(todos),
        }

    # ------------------------------------------------------------------
    # Category operations
    # ------------------------------------------------------------------
    def _create_category(self, **kwargs: Any) -> Dict[str, Any]:
        """Create a new category."""
        name: str = kwargs.get("name", "")
        if not name:
            raise ValueError("name is required for create_category action")

        color: str = kwargs.get("color", "#808080")
        icon: str = kwargs.get("icon", "📁")

        category = self._knowledge.create_category(name=name, color=color, icon=icon)

        self._screen.update_status(f"Created category: {category.name}")

        return {
            "category": KnowledgeService.category_to_dict(category),
            "action": "created",
            "message": f"Created category: {category.name}",
        }

    def _list_categories(self, **kwargs: Any) -> Dict[str, Any]:
        """List all categories."""
        categories = self._knowledge.list_categories()

        return {
            "categories": [KnowledgeService.category_to_dict(c) for c in categories],
            "count": len(categories),
        }

    def _update_category(self, **kwargs: Any) -> Dict[str, Any]:
        """Update a category."""
        category_id: str = kwargs.get("category_id", "")
        if not category_id:
            raise ValueError("category_id is required for update_category action")

        category = self._knowledge.update_category(
            category_id=category_id,
            name=kwargs.get("name"),
            color=kwargs.get("color"),
            icon=kwargs.get("icon"),
        )

        if category is None:
            raise KeyError(f"Category '{category_id}' not found")

        self._screen.update_status(f"Updated category: {category.name}")

        return {
            "category": KnowledgeService.category_to_dict(category),
            "action": "updated",
            "message": f"Updated category: {category.name}",
        }

    def _delete_category(self, **kwargs: Any) -> Dict[str, Any]:
        """Delete a category."""
        category_id: str = kwargs.get("category_id", "")
        if not category_id:
            raise ValueError("category_id is required for delete_category action")

        # Get category name before deleting
        category = self._knowledge.get_category(category_id)
        if not category:
            raise KeyError(f"Category '{category_id}' not found")

        name = category.name
        deleted = self._knowledge.delete_category(category_id)
        if not deleted:
            raise KeyError(f"Category '{category_id}' not found")

        self._screen.update_status(f"Deleted category: {name}")

        return {
            "deleted": True,
            "category_id": category_id,
            "message": f"Deleted category: {name}",
        }

    # ------------------------------------------------------------------
    # Subtask operations
    # ------------------------------------------------------------------
    def _add_subtask(self, **kwargs: Any) -> Dict[str, Any]:
        """Add a subtask to a parent todo."""
        parent_todo_id: str = kwargs.get("parent_todo_id", "")
        if not parent_todo_id:
            raise ValueError("parent_todo_id is required for add_subtask action")

        title: str = kwargs.get("title", "")
        if not title:
            raise ValueError("title is required for add_subtask action")

        # Create the subtask
        subtask = self._knowledge.create_todo(
            title=title,
            description=kwargs.get("description", ""),
            priority=kwargs.get("priority", "medium"),
            difficulty=int(kwargs.get("difficulty", 3)),
            parent_todo_id=parent_todo_id,
            user_id=kwargs.get("user_id"),
        )

        self._screen.update_status(f"Added subtask: {subtask.title}")

        return {
            "subtask": KnowledgeService.todo_to_dict(subtask),
            "action": "created",
            "message": f"Added subtask: {subtask.title}",
        }

    def _get_subtasks(self, **kwargs: Any) -> Dict[str, Any]:
        """Get all subtasks for a parent todo."""
        parent_todo_id: str = kwargs.get("parent_todo_id", "")
        if not parent_todo_id:
            raise ValueError("parent_todo_id is required for get_subtasks action")

        subtasks = self._knowledge.get_subtasks(parent_todo_id)

        return {
            "subtasks": [KnowledgeService.todo_to_dict(t) for t in subtasks],
            "count": len(subtasks),
        }

    # ------------------------------------------------------------------
    # Relationship operations
    # ------------------------------------------------------------------
    def _link_to_idea(self, **kwargs: Any) -> Dict[str, Any]:
        """Link a todo to an idea (IMPLEMENTS relationship)."""
        todo_id: str = kwargs.get("todo_id", "")
        idea_id: str = kwargs.get("idea_id", "")

        if not todo_id:
            raise ValueError("todo_id is required for link_to_idea action")
        if not idea_id:
            raise ValueError("idea_id is required for link_to_idea action")

        success = self._knowledge.link_todo_to_idea(todo_id, idea_id)
        if not success:
            raise KeyError(f"Todo '{todo_id}' or Idea '{idea_id}' not found")

        self._screen.update_status("Linked todo to idea")

        return {
            "linked": True,
            "todo_id": todo_id,
            "idea_id": idea_id,
            "message": "Todo linked to idea",
        }

    def _add_dependency(self, **kwargs: Any) -> Dict[str, Any]:
        """Add a dependency between todos (DEPENDS_ON relationship)."""
        todo_id: str = kwargs.get("todo_id", "")
        depends_on_id: str = kwargs.get("depends_on_id", "")

        if not todo_id:
            raise ValueError("todo_id is required for add_dependency action")
        if not depends_on_id:
            raise ValueError("depends_on_id is required for add_dependency action")

        success = self._knowledge.add_todo_dependency(todo_id, depends_on_id)
        if not success:
            raise KeyError(
                f"Todo '{todo_id}' or depends-on todo '{depends_on_id}' not found"
            )

        self._screen.update_status("Added todo dependency")

        return {
            "linked": True,
            "todo_id": todo_id,
            "depends_on_id": depends_on_id,
            "message": "Todo dependency added",
        }

    # ------------------------------------------------------------------
    # Timer integration
    # ------------------------------------------------------------------
    def _start_timer(self, **kwargs: Any) -> Dict[str, Any]:
        """Start a Pomodoro timer for a specific todo."""
        todo_id: Optional[str] = kwargs.get("todo_id")

        # If no todo_id provided, use the active todo
        if not todo_id:
            todo_id = self._screen.get_active_todo_id()
        if not todo_id:
            raise ValueError("No todo_id provided and no active todo to start timer for")

        # Get the todo to display its title
        todo = self._knowledge.get_todo(todo_id)
        if not todo:
            raise KeyError(f"Todo '{todo_id}' not found")

        # Get the timer tool and start a timer
        from tools.timer_tool import TimerTool

        timer_tool = TimerTool(self.context)
        work_minutes = int(kwargs.get("work_duration_minutes", 25))
        break_minutes = int(kwargs.get("break_duration_minutes", 5))

        timer_result = timer_tool.execute(
            "start",
            work_duration_minutes=work_minutes,
            break_duration_minutes=break_minutes,
        )

        session_id = timer_result.get("session", {}).get("id")

        # Create WORKED_ON relationship between session and todo
        if session_id:
            # Store the relationship in the graph
            self._knowledge._create_relationship(
                f"pomodoro:{session_id}",
                todo_id,
                relationship_type="WORKED_ON",
                created_at=_utc_now_iso(),
            )

        self._screen.update_status(f"Started timer for: {todo.title}")

        return {
            "timer_started": True,
            "todo_id": todo_id,
            "session_id": session_id,
            "message": f"Started Pomodoro timer for: {todo.title}",
            "session": timer_result.get("session"),
        }


__all__ = ["TodoTool"]

