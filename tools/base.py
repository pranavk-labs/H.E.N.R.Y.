"""Base abstractions and central registry for tools.

This is the canonical place for shared tool infrastructure, so that
tools can be used from the backend, voice pipeline, or future clients.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type

from backend.services.knowledge_service import KnowledgeService
from backend.services.screen_manager import ScreenManager

logger = logging.getLogger(__name__)


@dataclass
class ToolContext:
    """Shared context injected into all tools."""

    knowledge_service: KnowledgeService
    screen_manager: ScreenManager


class BaseTool(ABC):
    """Abstract base class for all tools."""

    name: str

    def __init__(self, context: ToolContext) -> None:
        self.context = context

    @abstractmethod
    def execute(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute a tool action and return a structured result."""


class ToolsRegistry:
    """Central registry for all tools."""

    _instance: Optional["ToolsRegistry"] = None

    def __init__(self) -> None:
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._context = ToolContext(
            knowledge_service=KnowledgeService.get_instance(),
            screen_manager=ScreenManager.get_instance(),
        )

    @classmethod
    def get_instance(cls) -> "ToolsRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_tool(self, name: str, tool_cls: Type[BaseTool]) -> None:
        """Register a tool class by name."""
        logger.info("Registering tool: %s -> %s", name, tool_cls.__name__)
        self._tools[name] = tool_cls

    def create_tool(self, name: str) -> BaseTool:
        """Instantiate a tool by name."""
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered")
        return self._tools[name](self._context)

    def list_tools(self) -> Dict[str, str]:
        """Return a mapping of tool names to class names."""
        return {name: cls.__name__ for name, cls in self._tools.items()}


__all__ = ["ToolContext", "BaseTool", "ToolsRegistry"]


