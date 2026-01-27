"""Test navigation stack and concurrent state tracking."""

from __future__ import annotations

import pytest

from backend.services.screen_manager import ScreenManager


@pytest.fixture
def screen_manager():
    """Create a fresh ScreenManager instance for testing."""
    # Get singleton and reset state
    manager = ScreenManager.get_instance()
    # Reset to idle state
    manager.reset_to_idle()
    # Clear all active states
    manager._state.active_states.clear()
    # Clear timer state
    manager._state.timer_state.clear()
    # Clear idea state
    manager._state.idea_view.clear()
    manager._state.active_idea_id = None
    manager._state.active_idea_text = ""
    manager._state.idea_last_updated = None
    yield manager
    # Cleanup after test
    manager.reset_to_idle()
    manager._state.active_states.clear()


def test_navigation_stack_basic(screen_manager):
    """Test basic navigation stack operations."""
    # Start at idle
    assert screen_manager.state.active_view == "idle"
    assert screen_manager.state.view_stack == ["idle"]
    assert not screen_manager.state.can_go_back()
    
    # Push pomodoro view
    screen_manager.push_view("pomodoro")
    assert screen_manager.state.active_view == "pomodoro"
    assert screen_manager.state.view_stack == ["idle", "pomodoro"]
    assert screen_manager.state.can_go_back()
    assert screen_manager.state.previous_view == "idle"
    
    # Push ideas view
    screen_manager.push_view("ideas")
    assert screen_manager.state.active_view == "ideas"
    assert screen_manager.state.view_stack == ["idle", "pomodoro", "ideas"]
    assert screen_manager.state.previous_view == "pomodoro"
    
    # Go back to pomodoro
    success = screen_manager.go_back()
    assert success
    assert screen_manager.state.active_view == "pomodoro"
    assert screen_manager.state.view_stack == ["idle", "pomodoro"]
    
    # Go back to idle
    success = screen_manager.go_back()
    assert success
    assert screen_manager.state.active_view == "idle"
    assert screen_manager.state.view_stack == ["idle"]
    
    # Can't go back from idle
    success = screen_manager.go_back()
    assert not success
    assert screen_manager.state.active_view == "idle"


def test_navigation_stack_replace(screen_manager):
    """Test replacing current view instead of pushing."""
    screen_manager.push_view("pomodoro")
    assert screen_manager.state.view_stack == ["idle", "pomodoro"]
    
    # Replace pomodoro with ideas
    screen_manager.push_view("ideas", replace_current=True)
    assert screen_manager.state.view_stack == ["idle", "ideas"]
    assert screen_manager.state.active_view == "ideas"


def test_concurrent_states_timer_and_idea(screen_manager):
    """Test that timer and idea can be active concurrently."""
    # Start a timer
    screen_manager.update_timer(status="running", session_id="test-123")
    assert "timer" in screen_manager.state.active_states
    assert screen_manager.state.active_view == "pomodoro"
    assert screen_manager.state.view_stack == ["idle", "pomodoro"]
    
    # Activate an idea (should push ideas view on top)
    screen_manager.set_active_idea("idea-456", "Test idea")
    assert "idea" in screen_manager.state.active_states
    assert "timer" in screen_manager.state.active_states  # Timer still active
    assert screen_manager.state.active_view == "ideas"
    assert screen_manager.state.view_stack == ["idle", "pomodoro", "ideas"]
    
    # Clear idea (should pop back to pomodoro view, timer still active)
    screen_manager.clear_active_idea()
    assert "idea" not in screen_manager.state.active_states
    assert "timer" in screen_manager.state.active_states  # Timer still active
    assert screen_manager.state.active_view == "pomodoro"
    assert screen_manager.state.view_stack == ["idle", "pomodoro"]
    
    # Complete timer (should pop back to idle)
    screen_manager.update_timer(status="completed")
    assert "timer" not in screen_manager.state.active_states
    assert screen_manager.state.active_view == "idle"
    assert screen_manager.state.view_stack == ["idle"]


def test_idea_while_timer_running(screen_manager):
    """Test creating an idea while timer is running."""
    # Start timer
    screen_manager.update_timer(status="running", session_id="test-123")
    assert screen_manager.state.active_view == "pomodoro"
    
    # Start an idea (should layer on top)
    screen_manager.set_active_idea("idea-789", "Great idea during pomodoro")
    assert screen_manager.state.active_view == "ideas"
    assert screen_manager.state.view_stack == ["idle", "pomodoro", "ideas"]
    assert screen_manager.is_state_active("timer")
    assert screen_manager.is_state_active("idea")
    
    # Back button should go back to timer view
    screen_manager.go_back()
    assert screen_manager.state.active_view == "pomodoro"
    assert screen_manager.is_state_active("timer")
    assert not screen_manager.is_state_active("idea")


def test_reset_to_idle(screen_manager):
    """Test resetting navigation stack to idle."""
    # Build up a navigation stack
    screen_manager.push_view("pomodoro")
    screen_manager.push_view("ideas")
    screen_manager.add_active_state("timer")
    screen_manager.add_active_state("idea")
    
    assert len(screen_manager.state.view_stack) == 3
    assert len(screen_manager.state.active_states) == 2
    
    # Reset to idle
    screen_manager.reset_to_idle()
    assert screen_manager.state.view_stack == ["idle"]
    assert screen_manager.state.active_view == "idle"
    # Note: active_states are not cleared by reset_to_idle, only the view stack


def test_get_navigation_stack(screen_manager):
    """Test getting a copy of the navigation stack."""
    screen_manager.push_view("pomodoro")
    screen_manager.push_view("ideas")
    
    stack = screen_manager.get_navigation_stack()
    assert stack == ["idle", "pomodoro", "ideas"]
    
    # Modifying the copy shouldn't affect the original
    stack.append("test")
    assert screen_manager.state.view_stack == ["idle", "pomodoro", "ideas"]


def test_active_states_management(screen_manager):
    """Test active states management."""
    assert screen_manager.get_active_states() == []
    
    screen_manager.add_active_state("timer")
    assert screen_manager.is_state_active("timer")
    assert screen_manager.get_active_states() == ["timer"]
    
    screen_manager.add_active_state("idea")
    assert screen_manager.is_state_active("idea")
    assert set(screen_manager.get_active_states()) == {"timer", "idea"}
    
    # Adding duplicate shouldn't duplicate
    screen_manager.add_active_state("timer")
    assert screen_manager.get_active_states().count("timer") == 1
    
    screen_manager.remove_active_state("timer")
    assert not screen_manager.is_state_active("timer")
    assert screen_manager.is_state_active("idea")
    
    screen_manager.remove_active_state("idea")
    assert screen_manager.get_active_states() == []

