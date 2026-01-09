"""Tools service providing unified access to all tools.

This service provides a single entry point for accessing tools,
making it easy for API routes and other components to interact with tools.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from tools import ToolsRegistry

logger = logging.getLogger(__name__)


class ToolsService:
    """Service for accessing and managing tools."""

    _instance: Optional["ToolsService"] = None

    def __init__(self) -> None:
        self._registry = ToolsRegistry.get_instance()

    @classmethod
    def get_instance(cls) -> "ToolsService":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def execute_tool(self, tool_name: str, action: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute a tool action.

        Args:
            tool_name: Name of the tool (e.g., "timer", "ideas")
            action: Action to execute (e.g., "start", "create")
            **kwargs: Additional arguments for the tool action

        Returns:
            Dict with tool execution result

        Raises:
            KeyError: If tool is not registered
            ValueError: If action is invalid
        """
        tool = self._registry.create_tool(tool_name)
        return tool.execute(action, **kwargs)

    def get_tool(self, tool_name: str) -> Any:
        """
        Get a tool instance.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool instance

        Raises:
            KeyError: If tool is not registered
        """
        return self._registry.create_tool(tool_name)

    def list_tools(self) -> Dict[str, str]:
        """List all available tools."""
        return self._registry.list_tools()


__all__ = ["ToolsService"]

