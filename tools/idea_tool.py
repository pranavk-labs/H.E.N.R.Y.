"""Idea notebook tool implementation."""

from __future__ import annotations

from typing import Any, Dict, List

from backend.services.knowledge_service import KnowledgeService
from backend.services.screen_manager import ScreenManager
from tools.base import BaseTool, ToolContext


class IdeaTool(BaseTool):
    """Tool for interacting with the virtual idea notebook."""

    name = "ideas"

    def __init__(self, context: ToolContext) -> None:
        super().__init__(context)
        self._knowledge = context.knowledge_service
        self._screen: ScreenManager = context.screen_manager

    def execute(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        action = action.lower()

        if action == "create":
            text: str = kwargs.get("text") or ""
            tags: List[str] = kwargs.get("tags") or []
            user_id: str | None = kwargs.get("user_id")
            idea = self._knowledge.create_idea(text=text, tags=tags, user_id=user_id)
            self._screen.update_idea_view(active_idea_id=idea.id, draft_text=idea.text)
            self._screen.update_status("Idea captured")
            return {"idea": KnowledgeService.idea_to_dict(idea)}

        if action == "update":
            idea_id: str = kwargs.get("idea_id")
            if not idea_id:
                raise ValueError("idea_id is required for update action")
            text: str | None = kwargs.get("text")
            tags: List[str] | None = kwargs.get("tags")
            idea = self._knowledge.update_idea(idea_id=idea_id, text=text, tags=tags)
            if idea is None:
                raise KeyError(f"Idea '{idea_id}' not found")
            self._screen.update_idea_view(active_idea_id=idea.id, draft_text=idea.text)
            self._screen.update_status("Idea updated")
            return {"idea": KnowledgeService.idea_to_dict(idea)}

        if action == "get":
            idea_id: str = kwargs.get("idea_id")
            if not idea_id:
                raise ValueError("idea_id is required for get action")
            idea = self._knowledge.get_idea(idea_id)
            if idea is None:
                raise KeyError(f"Idea '{idea_id}' not found")
            return {"idea": KnowledgeService.idea_to_dict(idea)}

        if action == "list":
            ideas = [KnowledgeService.idea_to_dict(i) for i in self._knowledge.list_ideas()]
            return {"ideas": ideas}

        if action == "delete":
            idea_id: str = kwargs.get("idea_id")
            if not idea_id:
                raise ValueError("idea_id is required for delete action")
            deleted = self._knowledge.delete_idea(idea_id)
            if not deleted:
                raise KeyError(f"Idea '{idea_id}' not found")
            self._screen.update_status("Idea deleted")
            return {"deleted": True, "idea_id": idea_id}

        if action == "search":
            query: str = kwargs.get("query") or ""
            ideas = [KnowledgeService.idea_to_dict(i) for i in self._knowledge.search_ideas(query)]
            return {"ideas": ideas}

        raise ValueError(f"Unknown idea tool action '{action}'")


__all__ = ["IdeaTool"]


