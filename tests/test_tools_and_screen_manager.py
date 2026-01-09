"""Tests for tools registry and mock screen manager."""

from backend.services import ScreenManager
from tools import ToolsRegistry


def test_tools_registry_and_screen_updates():
    """Timer and idea tools should be registered and update screen state."""
    registry = ToolsRegistry.get_instance()
    tools = registry.list_tools()
    assert "timer" in tools
    assert "ideas" in tools

    # Use the timer tool
    timer_tool = registry.create_tool("timer")
    result = timer_tool.execute("start", work_duration_minutes=1, break_duration_minutes=1)
    session = result["session"]
    assert session["status"] == "running"

    screen = ScreenManager.get_instance()
    assert screen.state.active_view == "pomodoro"
    assert screen.state.timer_state.get("session_id") == session["id"]

    # Use the idea tool
    idea_tool = registry.create_tool("ideas")
    idea_result = idea_tool.execute("create", text="Tool test idea", tags=["tool"])
    idea = idea_result["idea"]
    assert idea["text"] == "Tool test idea"

    assert screen.state.active_view in {"pomodoro", "ideas"}
    assert "draft_text" in screen.state.idea_view

