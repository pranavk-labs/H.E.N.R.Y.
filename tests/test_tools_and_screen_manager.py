"""Tests for tools registry and mock screen manager."""

import pytest

from backend.services import ScreenManager
from tools import ToolsRegistry


@pytest.fixture(autouse=True)
def reset_screen_manager():
    """Reset screen manager state before each test."""
    screen = ScreenManager.get_instance()
    screen.reset_to_idle()
    # Clear all active states
    screen._state.active_states.clear()
    # Clear timer state
    screen._state.timer_state.clear()
    # Clear idea state
    screen._state.idea_view.clear()
    screen._state.active_idea_id = None
    screen._state.active_idea_text = ""
    screen._state.idea_last_updated = None
    yield
    # Cleanup after test
    screen.reset_to_idle()
    screen._state.active_states.clear()


def test_tools_registry_and_screen_updates():
    """Timer and idea tools should be registered and update screen state."""
    screen = ScreenManager.get_instance()
    registry = ToolsRegistry.get_instance()
    tools = registry.list_tools()
    assert "timer" in tools
    assert "ideas" in tools

    # Use the timer tool
    timer_tool = registry.create_tool("timer")
    result = timer_tool.execute("start", work_duration_minutes=1, break_duration_minutes=1)
    session = result["session"]
    assert session["status"] == "running"

    # Check that timer updated screen state and navigation
    assert screen.state.active_view == "pomodoro"
    assert screen.state.view_stack == ["idle", "pomodoro"]
    assert "timer" in screen.state.active_states
    assert screen.state.timer_state.get("session_id") == session["id"]

    # Use the idea tool (should push ideas view on top of pomodoro)
    idea_tool = registry.create_tool("ideas")
    idea_result = idea_tool.execute("create", text="Tool test idea", tags=["tool"])
    idea = idea_result["idea"]
    assert idea["text"] == "Tool test idea"

    # After creating idea, we should be in ideas view with both timer and idea active
    assert screen.state.active_view == "ideas"
    assert screen.state.view_stack == ["idle", "pomodoro", "ideas"]
    assert "timer" in screen.state.active_states
    assert "idea" in screen.state.active_states
    assert "draft_text" in screen.state.idea_view

