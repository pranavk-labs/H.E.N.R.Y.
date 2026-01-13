"""Tests for PersonalityService."""

from backend.services.personality_service import PersonalityService
from backend.services.knowledge_service import KnowledgeService


def test_personality_defaults_round_trip():
    service = PersonalityService.get_instance()
    profile = service.get_personality_for_user(user_id="test-user")

    # Defaults should be sensible
    assert profile.name == "default"
    assert "helpful" in profile.style
    assert profile.max_context_turns > 0


def test_personality_preferences_override():
    knowledge = KnowledgeService.get_instance()
    service = PersonalityService.get_instance()

    # Save some personality preferences
    service.save_personality_preference("user-1", "name", "playful")
    service.save_personality_preference("user-1", "style", "very witty")
    service.save_personality_preference("user-1", "max_context_turns", 3)

    profile = service.get_personality_for_user("user-1")
    assert profile.name == "playful"
    assert profile.style == "very witty"
    assert profile.max_context_turns == 3


def test_personality_builds_system_prompt():
    service = PersonalityService.get_instance()
    prompt = service.build_system_prompt(user_id="test-user")

    assert "H.E.N.R.Y." in prompt
    assert "personality style" in prompt.lower()



