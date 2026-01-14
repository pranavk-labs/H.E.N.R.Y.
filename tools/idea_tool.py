"""Idea notebook tool implementation with conversation context awareness."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

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
            is_continuation: bool = kwargs.get("is_continuation", False)

            # If continuing an active idea, merge instead of creating new
            if is_continuation and self._screen.is_idea_active():
                return self._refine_active_idea(text, tags)

            idea = self._knowledge.create_idea(text=text, tags=tags, user_id=user_id)
            self._screen.set_active_idea(idea.id, idea.text)
            self._screen.update_status("Idea captured")
            return {"idea": KnowledgeService.idea_to_dict(idea), "action": "created"}

        if action == "update":
            idea_id: str | None = kwargs.get("idea_id")
            # If no idea_id provided, use the active idea
            if not idea_id:
                idea_id = self._screen.get_active_idea_id()
            if not idea_id:
                raise ValueError("No idea_id provided and no active idea to update")

            text: str | None = kwargs.get("text")
            tags: List[str] | None = kwargs.get("tags")
            idea = self._knowledge.update_idea(idea_id=idea_id, text=text, tags=tags)
            if idea is None:
                raise KeyError(f"Idea '{idea_id}' not found")
            self._screen.set_active_idea(idea.id, idea.text)
            self._screen.update_status("Idea updated")
            return {"idea": KnowledgeService.idea_to_dict(idea), "action": "updated"}

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
            # Clear active idea if we deleted it
            if self._screen.get_active_idea_id() == idea_id:
                self._screen.clear_active_idea()
            self._screen.update_status("Idea deleted")
            return {"deleted": True, "idea_id": idea_id}

        if action == "search":
            query: str = kwargs.get("query") or ""
            ideas = [KnowledgeService.idea_to_dict(i) for i in self._knowledge.search_ideas(query)]
            return {"ideas": ideas}

        if action == "close":
            # Mark the current idea discussion as complete
            self._screen.clear_active_idea()
            return {"message": "Idea session closed"}

        raise ValueError(f"Unknown idea tool action '{action}'")

    def _refine_active_idea(
        self, new_text: str, tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Merge new context into the active idea."""
        active_id = self._screen.get_active_idea_id()
        if not active_id:
            raise ValueError("No active idea to refine")

        existing = self._knowledge.get_idea(active_id)
        if not existing:
            raise KeyError(f"Active idea '{active_id}' not found")

        # Intelligent merge: if new text is comprehensive, replace; otherwise append
        merged_text = self._merge_idea_text(existing.text, new_text)
        merged_tags = list(set((existing.tags or []) + (tags or [])))

        idea = self._knowledge.update_idea(
            idea_id=active_id, text=merged_text, tags=merged_tags
        )
        if idea is None:
            raise KeyError(f"Failed to update idea '{active_id}'")

        self._screen.set_active_idea(idea.id, idea.text)
        self._screen.update_status("Idea refined")
        return {"idea": KnowledgeService.idea_to_dict(idea), "action": "refined"}

    def _merge_idea_text(self, existing: str, new: str) -> str:
        """Intelligently merge new context into existing idea text."""
        # If new text is substantially longer or comprehensive, it's likely a replacement
        if len(new) > len(existing) * 0.8:
            return new

        # If new text content is already in existing, no need to add
        if new.lower().strip() in existing.lower():
            return existing

        # Append new information
        return f"{existing} {new}"


__all__ = ["IdeaTool"]
