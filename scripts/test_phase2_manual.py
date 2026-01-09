#!/usr/bin/env python3
"""Manual test script for Phase 2 features.

This script exercises all Phase 2 functionality:
- Tools registry and tool creation
- Pomodoro timer tool (start, pause, resume, complete, status)
- Idea notebook tool (create, list, get, update, search, delete)
- Screen manager state updates
- Knowledge service (preferences, ideas)

Run with: poetry run python scripts/test_phase2_manual.py
"""

import json
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services import KnowledgeService, ScreenManager
from backend.services.pomodoro_service import PomodoroService
from backend.services.idea_service import IdeaService
from tools import ToolsRegistry


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_subsection(title: str) -> None:
    """Print a formatted subsection header."""
    print(f"\n--- {title} ---")


def print_json(data: dict) -> None:
    """Pretty print JSON data."""
    print(json.dumps(data, indent=2, default=str))


def test_tools_registry():
    """Test tools registry functionality."""
    print_section("1. Tools Registry")

    registry = ToolsRegistry.get_instance()
    tools = registry.list_tools()
    print(f"Registered tools: {list(tools.keys())}")
    print(f"Tool classes: {tools}")

    assert "timer" in tools, "Timer tool should be registered"
    assert "ideas" in tools, "Ideas tool should be registered"
    print("✓ Tools registry working correctly")


def test_pomodoro_tool():
    """Test Pomodoro timer tool."""
    print_section("2. Pomodoro Timer Tool")

    registry = ToolsRegistry.get_instance()
    timer_tool = registry.create_tool("timer")
    screen = ScreenManager.get_instance()

    # Start a session
    print_subsection("Starting Pomodoro session")
    result = timer_tool.execute(
        "start", work_duration_minutes=2, break_duration_minutes=1
    )
    session = result["session"]
    session_id = session["id"]
    print(f"Session ID: {session_id}")
    print_json(session)
    print(f"Screen view: {screen.state.active_view}")
    print(f"Screen status: {screen.state.status_text}")
    print(f"Timer state: {screen.state.timer_state}")
    assert session["status"] == "running"
    assert screen.state.active_view == "pomodoro"
    print("✓ Pomodoro started successfully")

    # Get status
    print_subsection("Getting session status")
    result = timer_tool.execute("status", session_id=session_id)
    print_json(result["session"])
    print("✓ Status retrieved")

    # Pause
    print_subsection("Pausing session")
    time.sleep(0.5)  # Simulate some work time
    result = timer_tool.execute("pause", session_id=session_id)
    print_json(result["session"])
    print(f"Screen status: {screen.state.status_text}")
    assert result["session"]["status"] == "paused"
    print("✓ Session paused")

    # Resume
    print_subsection("Resuming session")
    result = timer_tool.execute("resume", session_id=session_id)
    print_json(result["session"])
    print(f"Screen status: {screen.state.status_text}")
    assert result["session"]["status"] == "running"
    print("✓ Session resumed")

    # Complete
    print_subsection("Completing session")
    time.sleep(0.5)  # Simulate more work time
    result = timer_tool.execute("complete", session_id=session_id)
    print_json(result["session"])
    print(f"Screen status: {screen.state.status_text}")
    assert result["session"]["status"] == "completed"
    assert result["session"]["completed_at"] is not None
    print("✓ Session completed")

    # Test service directly
    print_subsection("Testing PomodoroService directly")
    service = PomodoroService.get_instance()
    sessions = service.list_sessions()
    print(f"Total sessions: {len(sessions)}")
    assert len(sessions) >= 1
    print("✓ Service working correctly")


def test_idea_tool():
    """Test Idea notebook tool."""
    print_section("3. Idea Notebook Tool")

    registry = ToolsRegistry.get_instance()
    idea_tool = registry.create_tool("ideas")
    screen = ScreenManager.get_instance()

    # Create ideas
    print_subsection("Creating ideas")
    idea1_result = idea_tool.execute(
        "create",
        text="Build a voice-controlled assistant",
        tags=["project", "voice"],
    )
    idea1 = idea1_result["idea"]
    idea1_id = idea1["id"]
    print(f"Idea 1 ID: {idea1_id}")
    print_json(idea1)
    print(f"Screen view: {screen.state.active_view}")
    print(f"Screen status: {screen.state.status_text}")
    assert idea1["text"] == "Build a voice-controlled assistant"
    assert "project" in idea1["tags"]
    print("✓ Idea 1 created")

    idea2_result = idea_tool.execute(
        "create",
        text="Learn about graph databases and Neo4j",
        tags=["learning", "database"],
    )
    idea2 = idea2_result["idea"]
    idea2_id = idea2["id"]
    print(f"Idea 2 ID: {idea2_id}")
    print_json(idea2)
    print("✓ Idea 2 created")

    # List ideas
    print_subsection("Listing all ideas")
    result = idea_tool.execute("list")
    ideas = result["ideas"]
    print(f"Total ideas: {len(ideas)}")
    assert len(ideas) >= 2
    print("✓ Ideas listed")

    # Get specific idea
    print_subsection("Getting specific idea")
    result = idea_tool.execute("get", idea_id=idea1_id)
    idea = result["idea"]
    print_json(idea)
    assert idea["id"] == idea1_id
    print("✓ Idea retrieved")

    # Update idea
    print_subsection("Updating idea")
    result = idea_tool.execute(
        "update",
        idea_id=idea1_id,
        text="Build a voice-controlled assistant with personality",
        tags=["project", "voice", "personality"],
    )
    updated_idea = result["idea"]
    print_json(updated_idea)
    assert "personality" in updated_idea["text"]
    assert "personality" in updated_idea["tags"]
    print(f"Screen status: {screen.state.status_text}")
    print("✓ Idea updated")

    # Search ideas
    print_subsection("Searching ideas")
    result = idea_tool.execute("search", query="voice")
    matching_ideas = result["ideas"]
    print(f"Found {len(matching_ideas)} ideas matching 'voice'")
    assert len(matching_ideas) >= 1
    for idea in matching_ideas:
        print(f"  - {idea['text'][:50]}...")
    print("✓ Search working")

    # Delete idea
    print_subsection("Deleting idea")
    result = idea_tool.execute("delete", idea_id=idea2_id)
    print_json(result)
    assert result["deleted"] is True
    print(f"Screen status: {screen.state.status_text}")

    # Verify deletion
    try:
        idea_tool.execute("get", idea_id=idea2_id)
        assert False, "Idea should have been deleted"
    except KeyError:
        print("✓ Idea deleted successfully")

    # Test service directly
    print_subsection("Testing IdeaService directly")
    service = IdeaService.get_instance()
    all_ideas = service.list_ideas()
    print(f"Total ideas in service: {len(all_ideas)}")
    assert len(all_ideas) >= 1
    print("✓ Service working correctly")


def test_knowledge_service():
    """Test knowledge service directly."""
    print_section("4. Knowledge Service")

    knowledge = KnowledgeService.get_instance()

    # Test preferences
    print_subsection("User Preferences")
    user_id = "default_user"
    knowledge.set_preference(user_id, "theme", "dark", strength=0.9)
    knowledge.set_preference(user_id, "language", "en", strength=1.0)
    prefs = knowledge.get_preferences(user_id)
    print(f"Total preferences: {len(prefs)}")
    pref_dict = {p.key: p.value for p in prefs}
    print(f"Preferences: {pref_dict}")
    assert "theme" in pref_dict
    assert pref_dict["theme"] == "dark"
    assert pref_dict["language"] == "en"
    print("✓ Preferences working")

    # Test idea storage in knowledge graph
    print_subsection("Ideas in Knowledge Graph")
    ideas = knowledge.list_ideas()
    print(f"Total ideas in knowledge graph: {len(ideas)}")
    if ideas:
        print(f"Sample idea: {ideas[0].text[:50]}...")
    print("✓ Ideas stored in knowledge graph")


def test_screen_manager():
    """Test screen manager state."""
    print_section("5. Screen Manager State")

    screen = ScreenManager.get_instance()
    state = screen.state

    print("Current screen state:")
    print(f"  Active view: {state.active_view}")
    print(f"  Status text: {state.status_text}")
    print(f"  Timer state: {state.timer_state}")
    print(f"  Idea view: {state.idea_view}")

    # Test direct updates
    print_subsection("Direct screen updates")
    screen.set_view("custom_view", extra_data="test")
    screen.update_status("Manual test status")
    print(f"Updated view: {screen.state.active_view}")
    print(f"Updated status: {screen.state.status_text}")
    assert screen.state.active_view == "custom_view"
    print("✓ Screen manager working correctly")


def main():
    """Run all manual tests."""
    print("\n" + "=" * 70)
    print("  H.E.N.R.Y. Phase 2 Manual Test Suite")
    print("=" * 70)

    try:
        test_tools_registry()
        test_pomodoro_tool()
        test_idea_tool()
        test_knowledge_service()
        test_screen_manager()

        print_section("Test Summary")
        print("✓ All Phase 2 features tested successfully!")
        print("\nFeatures verified:")
        print("  - Tools registry and tool creation")
        print("  - Pomodoro timer (start, pause, resume, complete, status)")
        print("  - Idea notebook (create, list, get, update, search, delete)")
        print("  - Screen manager state updates")
        print("  - Knowledge service (preferences, ideas)")
        print("\nPhase 2 implementation is working correctly! 🎉")

    except Exception as e:
        print_section("Test Failed")
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

