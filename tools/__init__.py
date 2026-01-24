"""Top-level tools package for H.E.N.R.Y.

This hosts the pluggable tools library (timer, ideas, etc.) that can be
used by the voice pipeline, GUI, or any other orchestration layer.

NOTE: Tool classes are now lazy-loaded to avoid importing heavy dependencies
(neo4j via KnowledgeService) on client devices. The registry still works
the same way but tools are registered lazily when first accessed.
"""

from typing import TYPE_CHECKING

# Base classes can be imported eagerly since they don't have heavy dependencies anymore
from tools.base import ToolsRegistry, BaseTool, ToolContext

if TYPE_CHECKING:
    from tools.timer_tool import TimerTool
    from tools.idea_tool import IdeaTool
    from tools.todo_tool import TodoTool
    from tools.calendar_tool import CalendarTool

__all__ = [
    "ToolsRegistry",
    "BaseTool",
    "ToolContext",
    "TimerTool",
    "IdeaTool",
    "TodoTool",
    "CalendarTool",
]

# Track whether tools have been registered
_tools_registered = False


def _register_tools_lazy():
    """Register built-in tools with lazy imports.

    This function imports and registers tools only when first called,
    avoiding heavy dependencies (neo4j, etc.) until actually needed.
    """
    global _tools_registered
    if _tools_registered:
        return

    from tools.timer_tool import TimerTool
    from tools.idea_tool import IdeaTool
    from tools.todo_tool import TodoTool
    from tools.calendar_tool import CalendarTool

    registry = ToolsRegistry.get_instance()
    registry.register_tool("timer", TimerTool)
    registry.register_tool("ideas", IdeaTool)
    registry.register_tool("todos", TodoTool)
    registry.register_tool("calendar", CalendarTool)

    _tools_registered = True


def __getattr__(name: str):
    """Lazy-load tool classes on first access."""
    if name == "TimerTool":
        from tools.timer_tool import TimerTool
        return TimerTool
    elif name == "IdeaTool":
        from tools.idea_tool import IdeaTool
        return IdeaTool
    elif name == "TodoTool":
        from tools.todo_tool import TodoTool
        return TodoTool
    elif name == "CalendarTool":
        from tools.calendar_tool import CalendarTool
        return CalendarTool
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
