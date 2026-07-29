"""Base abstractions and central registry for tools.

This is the canonical place for shared tool infrastructure, so that
tools can be used from the backend, voice pipeline, or future clients.

NOTE: Services are lazy-loaded to avoid importing heavy dependencies
(neo4j via KnowledgeService) on client devices.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.knowledge_service import KnowledgeService
    from backend.services.screen_manager import ScreenManager

logger = logging.getLogger(__name__)


@dataclass
class ToolContext:
    """Shared context injected into all tools.

    Services are loaded lazily when the context is created,
    not when this module is imported.
    """

    knowledge_service: Any  # KnowledgeService (lazy-loaded)
    screen_manager: Any  # ScreenManager (lazy-loaded)


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
        self._context: Optional[ToolContext] = None  # Lazy-loaded

    def _ensure_context(self) -> ToolContext:
        """Lazy-load the tool context with service dependencies."""
        # Import services only when first needed.
        from backend.services.knowledge_service import KnowledgeService
        from backend.services.screen_manager import ScreenManager

        knowledge_service = KnowledgeService.get_instance()
        screen_manager = ScreenManager.get_instance()

        if (
            self._context is None
            or self._context.knowledge_service is not knowledge_service
            or self._context.screen_manager is not screen_manager
        ):
            self._context = ToolContext(
                knowledge_service=knowledge_service,
                screen_manager=screen_manager,
            )
        return self._context

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
            # Trigger lazy tool registration if needed
            self._ensure_tools_registered()
            if name not in self._tools:
                raise KeyError(f"Tool '{name}' is not registered")
        context = self._ensure_context()
        return self._tools[name](context)

    def _ensure_tools_registered(self) -> None:
        """Ensure tools are registered (triggers lazy registration)."""
        if not self._tools:
            # Import and register tools lazily
            try:
                import tools
                if hasattr(tools, '_register_tools_lazy'):
                    tools._register_tools_lazy()
            except ImportError:
                logger.warning("Could not import tools package for lazy registration")

    def list_tools(self) -> Dict[str, str]:
        """Return a mapping of tool names to class names."""
        self._ensure_tools_registered()
        return {name: cls.__name__ for name, cls in self._tools.items()}


__all__ = ["ToolContext", "BaseTool", "ToolsRegistry"]
