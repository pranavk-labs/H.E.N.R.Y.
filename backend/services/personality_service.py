"""Personality system for H.E.N.R.Y.

This module provides a lightweight but extensible personality layer that:

- Defines configurable personality traits
- Builds system prompts for the LLM
- Can read/write related preferences via the knowledge graph

It is intentionally simple for Phase 3 while leaving room for future expansion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import logging

from backend.services.knowledge_service import KnowledgeService
from backend.services.screen_manager import ScreenManager

logger = logging.getLogger(__name__)


@dataclass
class PersonalityProfile:
    """Represents a single personality configuration."""

    name: str = "default"
    style: str = "helpful, conversational, and naturally curious - asks questions when unsure"
    speaking_voice: str = "neutral"
    temperature: float = 0.7
    max_context_turns: int = 8


class PersonalityService:
    """Personality system with simple profile + preference integration."""

    _instance: Optional["PersonalityService"] = None

    def __init__(
        self,
        knowledge_service: Optional[KnowledgeService] = None,
    ) -> None:
        self._knowledge = knowledge_service or KnowledgeService.get_instance()
        self._default_profile = PersonalityProfile()

    @classmethod
    def get_instance(cls) -> "PersonalityService":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Profiles and preferences
    # ------------------------------------------------------------------
    def get_personality_for_user(self, user_id: str = "default") -> PersonalityProfile:
        """Build personality profile for a user from preferences + defaults."""
        try:
            prefs = self._knowledge.get_preferences(user_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to load preferences for personality: %s", exc)
            return self._default_profile

        profile_data: Dict[str, Any] = {}
        for pref in prefs:
            if not pref.key.startswith("personality."):
                continue
            short_key = pref.key.split("personality.", 1)[1]
            profile_data[short_key] = pref.value

        return PersonalityProfile(
            name=str(profile_data.get("name", self._default_profile.name)),
            style=str(profile_data.get("style", self._default_profile.style)),
            speaking_voice=str(
                profile_data.get("speaking_voice", self._default_profile.speaking_voice)
            ),
            temperature=float(
                profile_data.get("temperature", self._default_profile.temperature)
            ),
            max_context_turns=int(
                profile_data.get("max_context_turns", self._default_profile.max_context_turns)
            ),
        )

    def save_personality_preference(
        self,
        user_id: str,
        key: str,
        value: Any,
        strength: float = 1.0,
    ) -> None:
        """Persist a single personality-related preference."""
        full_key = f"personality.{key}"
        self._knowledge.set_preference(user_id=user_id, key=full_key, value=value, strength=strength)

    # ------------------------------------------------------------------
    # Prompt construction helpers
    # ------------------------------------------------------------------
    def build_system_prompt(
        self,
        user_id: str = "default",
        extra_instructions: Optional[str] = None,
    ) -> str:
        """Create a system prompt string that encodes the active personality."""
        profile = self.get_personality_for_user(user_id)
        lines: List[str] = [
            "You are H.E.N.R.Y., a desk-based personal productivity assistant.",
            f"Your personality style is: {profile.style}.",
            "You speak concisely, stay on task, and keep a warm, collaborative tone.",
            "You can reference the user's habits and preferences when they are relevant.",
            "",
            "CRITICAL: Never use formatting marks like asterisks, bullets, or markdown in your responses. "
            "All text you generate will be read aloud by text-to-speech, so write in plain text only. "
            "This is especially important when saving ideas - always provide clean, readable text.",
            "",
            "IMPORTANT: When using tools like ideas_tool, NEVER mention idea IDs, numbers, or technical details "
            "in your response. Simply confirm the action naturally (e.g., 'Got it' or 'I've saved that idea').",
            "",
            "IMPORTANT: If the user's request is unclear, ambiguous, or missing important details, "
            "ask a clarifying question instead of guessing or making assumptions. "
            "Be conversational and natural when asking for clarification.",
            "",
            "Examples:",
            "- If they say 'start a timer' without specifying duration, ask 'How long should I set the timer for?'",
            "- If they say 'remind me about that', ask 'What should I remind you about?'",
            "- If context is missing, politely ask for more information.",
        ]

        # Add active idea context if one is being discussed
        screen = ScreenManager.get_instance()
        if screen.is_idea_active():
            active_text = screen.state.active_idea_text
            lines.extend([
                "",
                f"ACTIVE IDEA CONTEXT: The user is currently developing an idea: \"{active_text}\"",
                "If they add more details or refine this idea, use ideas_tool with is_continuation=true to update it.",
                "If they clearly change topics, create a new idea or respond normally.",
            ])

        if extra_instructions:
            lines.append(extra_instructions.strip())

        return "\n".join(lines)

    def _strip_markdown_and_formatting(self, text: str) -> str:
        """Strip markdown formatting and clean text for TTS.
        
        Removes:
        - Bold/italic asterisks and underscores
        - Bullet points and numbered lists
        - Headers
        - Idea IDs and references
        - Extra whitespace
        """
        # Remove bold/italic asterisks: **text**, *text*, __text__, _text_
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold**
        text = re.sub(r'\*(.+?)\*', r'\1', text)  # *italic*
        text = re.sub(r'__(.+?)__', r'\1', text)  # __bold__
        text = re.sub(r'_(.+?)_', r'\1', text)  # _italic_
        
        # Remove bullet points at start of lines
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        
        # Remove numbered lists
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # Remove headers
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        
        # Remove idea ID references (e.g., "Idea idea_001" or "idea_001")
        text = re.sub(r'\b[Ii]dea\s+idea_\d+\b', 'idea', text)
        text = re.sub(r'\bidea_\d+\b', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()

    def decorate_llm_response(
        self,
        user_id: str,
        raw_text: str,
    ) -> str:
        """Apply light post-processing to an LLM response based on personality.

        For Phase 3 this is intentionally minimal; future phases can
        add more sophisticated re-writing or tagging.
        """
        profile = self.get_personality_for_user(user_id)
        text = raw_text.strip()
        if not text:
            return text

        # Strip markdown and formatting for TTS compatibility
        text = self._strip_markdown_and_formatting(text)

        # Ensure we keep responses concise and aligned with style.
        # This is heuristic and intentionally lightweight.
        if len(text.split()) > 120:
            # Rough trim with a soft ending.
            trimmed = " ".join(text.split()[:120])
            if not trimmed.endswith((".", "!", "?")):
                trimmed += "..."
            text = trimmed

        # Optionally, add a small tag only for clearly functional responses.
        if "timer" in text.lower() and "pomodoro" in profile.style.lower():
            return text + " (Let me know when you want to tweak your routine.)"

        return text


__all__ = ["PersonalityService", "PersonalityProfile"]


