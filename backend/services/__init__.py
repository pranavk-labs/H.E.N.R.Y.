"""Core backend services package.

NOTE: This module uses lazy imports to avoid loading heavy dependencies
(neo4j, ollama) on client devices that only need lightweight services
like audio, STT, TTS.
"""

from typing import TYPE_CHECKING

# Lazy imports - only loaded when explicitly requested
# This prevents neo4j and other heavy dependencies from being imported
# when client code only needs audio/stt/tts services
if TYPE_CHECKING:
    from backend.services.knowledge_service import KnowledgeService
    from backend.services.screen_manager import ScreenManager
    from backend.services.tools_service import ToolsService

__all__ = [
    "KnowledgeService",
    "ScreenManager",
    "ToolsService",
]


def __getattr__(name: str):
    """Lazy-load services on first access."""
    if name == "KnowledgeService":
        from backend.services.knowledge_service import KnowledgeService
        return KnowledgeService
    elif name == "ScreenManager":
        from backend.services.screen_manager import ScreenManager
        return ScreenManager
    elif name == "ToolsService":
        from backend.services.tools_service import ToolsService
        return ToolsService
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


