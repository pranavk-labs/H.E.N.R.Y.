"""Top-level tools package for H.E.N.R.Y.

This hosts the pluggable tools library (timer, ideas, etc.) that can be
used by the voice pipeline, GUI, or any other orchestration layer.
"""

from tools.base import ToolsRegistry, BaseTool, ToolContext
from tools.timer_tool import TimerTool
from tools.idea_tool import IdeaTool

__all__ = [
    "ToolsRegistry",
    "BaseTool",
    "ToolContext",
    "TimerTool",
    "IdeaTool",
]

# Register built-in tools with the central registry on import.
_registry = ToolsRegistry.get_instance()
_registry.register_tool("timer", TimerTool)
_registry.register_tool("ideas", IdeaTool)


