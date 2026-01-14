"""Conversation orchestration and simple intent routing for Phase 3.

This service sits on top of:
- Audio/voice pipeline (wake word + STT handled elsewhere)
- OllamaClient for LLM-backed responses
- PersonalityService for prompt construction
- ToolsService for simple intent-based tool calls (timer, ideas, etc.)
"""

from __future__ import annotations

import asyncio
import os
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from backend.services.knowledge_service import KnowledgeService
from backend.services.ollama_client import OllamaClient
from backend.services.personality_service import PersonalityService
from backend.services.tools_service import ToolsService

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    role: str  # "user" | "assistant"
    content: str


class ConversationService:
    """High-level conversation service with minimal context + intent routing."""

    _instance: Optional["ConversationService"] = None

    def __init__(
        self,
        knowledge_service: Optional[KnowledgeService] = None,
        personality_service: Optional[PersonalityService] = None,
        ollama_client: Optional[OllamaClient] = None,
        tools_service: Optional[ToolsService] = None,
        default_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    ) -> None:
        self._knowledge = knowledge_service or KnowledgeService.get_instance()
        self._personality = personality_service or PersonalityService.get_instance()
        self._ollama = ollama_client or OllamaClient.get_instance()
        self._tools = tools_service or ToolsService.get_instance()
        self._default_model = default_model
        self._history: Dict[str, List[ConversationTurn]] = {}

    @classmethod
    def get_instance(cls) -> "ConversationService":
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_history(self, user_id: str = "default") -> List[ConversationTurn]:
        """Return conversation history for a user."""
        return list(self._history.get(user_id, []))

    def clear_history(self, user_id: str = "default") -> None:
        """Clear conversation history for a user."""
        self._history[user_id] = []

    def handle_utterance(
        self,
        text: str,
        user_id: str = "default",
        pre_tool_speak_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for handling a single utterance.
        
        Args:
            text: User input text
            user_id: User ID
            pre_tool_speak_callback: Optional callback to speak text before tool execution
        """
        loop = self._get_loop()
        return loop.run_until_complete(self._handle_utterance_async(text=text, user_id=user_id, pre_tool_speak_callback=pre_tool_speak_callback))

    # ------------------------------------------------------------------
    # Core async implementation
    # ------------------------------------------------------------------
    async def _handle_utterance_async(
        self,
        text: str,
        user_id: str,
        pre_tool_speak_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        text = text.strip()
        if not text:
            return {"response": "I didn't catch that. Could you repeat what you said?", "intent": "empty"}

        # Handle very short or potentially unclear inputs
        if len(text.split()) <= 2:
            # Check if it's a common short command
            lowered = text.lower()
            unclear_phrases = ["that", "it", "this", "there", "one", "thing"]
            if any(phrase in lowered for phrase in unclear_phrases):
                return {
                    "response": "I'm not sure what you're referring to. Could you be more specific?",
                    "intent": "clarification_needed"
                }

        # Handle requests for repetition or clarification
        lowered = text.lower()
        repeat_phrases = ["what did you say", "what was that", "repeat", "say again", "didn't hear", "pardon"]
        if any(phrase in lowered for phrase in repeat_phrases):
            # Get last assistant message
            turns = self._history.get(user_id, [])
            last_assistant_message = None
            for turn in reversed(turns):
                if turn.role == "assistant":
                    last_assistant_message = turn.content
                    break

            if last_assistant_message:
                return {
                    "response": f"I said: {last_assistant_message}",
                    "intent": "repeat"
                }
            else:
                return {
                    "response": "I haven't said anything yet. How can I help you?",
                    "intent": "repeat"
                }

        # Append user turn
        self._append_turn(user_id, "user", text)

        # Very lightweight rules-based intent detection for Phase 3.
        intent, tool_result = await self._maybe_handle_tool_intent(user_id, text)
        if intent and tool_result is not None:
            assistant_text = tool_result.get("message") or tool_result.get("response") or ""
            if not assistant_text:
                assistant_text = "Done."
            self._append_turn(user_id, "assistant", assistant_text)
            return {
                "response": assistant_text,
                "intent": intent,
                "tool_result": tool_result,
            }

        # Otherwise, fall back to free-form LLM conversation
        system_prompt = self._personality.build_system_prompt(user_id=user_id)
        
        # Try to use tool calling if available (Ollama chat API with tools)
        try:
            # Build messages from history
            messages = []
            turns = self._history.get(user_id, [])
            for turn in turns[-20:]:  # Last 20 turns
                messages.append({
                    "role": turn.role,
                    "content": turn.content
                })
            
            # Add current user message
            messages.append({
                "role": "user",
                "content": text
            })
            
            # Use chat_with_tools for tool calling support
            # Pass through the speak callback and user_id if provided
            raw = await self._ollama.chat_with_tools(
                model=self._default_model,
                messages=messages,
                tools_service=self._tools,
                tools_callback=None,  # Use tools_service directly
                system_prompt=system_prompt,
                options=None,
                max_tool_iterations=5,
                pre_tool_speak_callback=pre_tool_speak_callback,
                user_id=user_id,
            )
            
            # Get final response text
            message = raw.get("message", {})
            llm_text = str(message.get("content", "") or "").strip()
            if not llm_text:
                llm_text = "I'm sorry, I'm having trouble processing that right now. Could you try rephrasing?"
        except Exception as e:
            logger.warning(f"Tool calling failed, falling back to generate: {e}")
            # Fallback to regular generate method
            try:
                history_text = self._build_history_text(user_id)
                full_prompt = f"{history_text}\nUser: {text}\nAssistant:"

                raw = await self._ollama.generate(
                    model=self._default_model,
                    prompt=full_prompt,
                    system_prompt=system_prompt,
                    stream=False,
                )
                llm_text = str(raw.get("response") or raw.get("message", {}).get("content") or "").strip()
                if not llm_text:
                    llm_text = "I'm sorry, I'm having trouble understanding. Could you rephrase that?"
            except Exception as fallback_error:
                logger.error(f"Complete LLM failure: {fallback_error}")
                llm_text = "I'm having connection issues right now. Could you try again in a moment?"

        final_text = self._personality.decorate_llm_response(user_id=user_id, raw_text=llm_text)
        self._append_turn(user_id, "assistant", final_text)

        return {
            "response": final_text,
            "intent": "chat",
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_loop(self) -> asyncio.AbstractEventLoop:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
            return loop
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def _append_turn(self, user_id: str, role: str, content: str) -> None:
        turns = self._history.setdefault(user_id, [])
        turns.append(ConversationTurn(role=role, content=content))
        # Bound history length using personality setting
        profile = self._personality.get_personality_for_user(user_id)
        max_turns = max(2 * profile.max_context_turns, 4)
        if len(turns) > max_turns:
            self._history[user_id] = turns[-max_turns:]

    def _build_history_text(self, user_id: str) -> str:
        """Convert recent turns into a lightweight text transcript for prompts."""
        turns = self._history.get(user_id, [])
        lines: List[str] = []
        for t in turns[-20:]:
            prefix = "User" if t.role == "user" else "Assistant"
            lines.append(f"{prefix}: {t.content}")
        return "\n".join(lines)

    def _fuzzy_match_word(self, word: str, target: str, threshold: int = 2) -> bool:
        """Check if word is similar to target using Levenshtein-like edit distance.

        Args:
            word: The word to check (e.g., "state")
            target: The target word (e.g., "start")
            threshold: Maximum edit distance allowed (default: 2)

        Returns:
            True if words are similar enough, False otherwise
        """
        if word == target:
            return True

        # Quick checks for common prefixes/suffixes
        if len(word) == len(target):
            # Count character differences
            differences = sum(1 for a, b in zip(word, target) if a != b)
            return differences <= threshold

        # Simple edit distance calculation
        m, n = len(word), len(target)
        if abs(m - n) > threshold:
            return False

        # Create matrix for edit distance
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if word[i - 1] == target[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(
                        dp[i - 1][j],      # deletion
                        dp[i][j - 1],      # insertion
                        dp[i - 1][j - 1]   # substitution
                    )

        return dp[m][n] <= threshold

    def _normalize_transcription(self, text: str) -> str:
        """Normalize common transcription errors in text.

        Args:
            text: The transcribed text (possibly with errors)

        Returns:
            Normalized text with common errors corrected
        """
        lowered = text.lower()

        # Check if this looks like a timer command
        has_timer_context = any(word in lowered for word in ["timer", "pomodoro", "focus", "session"])

        # Common transcription error mappings for timer commands
        # Only apply context-sensitive corrections when timer keywords are present
        always_correct = {
            "state": "start",      # "state your timer" -> "start your timer"
            "status": "start",     # "status timer" -> "start timer"
            "stat": "start",       # "stat timer" -> "start timer"
            "stayed": "start",     # "stayed timer" -> "start timer"
            "stir": "start",       # "stir timer" -> "start timer"
            "store": "start",      # "store timer" -> "start timer"
            "star": "start",       # "star timer" -> "start timer"
            "starting": "start",   # Normalize to base form
            "started": "start",    # Normalize to base form
            "ending": "end",       # Close enough but let's normalize
            "ended": "end",        # Normalize to base form
            "finish": "finish",    # Keep as is
            "finished": "finish",  # Normalize to base form
            "finnish": "finish",   # Common typo/transcription error
            "poles": "pause",      # "poles my timer" -> "pause my timer"
            "paws": "pause",       # "paws timer" -> "pause timer"
            "pausing": "pause",    # Normalize to base form
            "paused": "pause",     # Normalize to base form
        }

        # Only apply these if timer context is detected (avoid false positives)
        context_corrections = {
            "and": "end",          # "and my timer" -> "end my timer"
            "in": "end",           # "in my timer" -> "end my timer"
        }

        words = lowered.split()
        normalized_words = []

        for i, word in enumerate(words):
            # Check for always-correct mappings
            if word in always_correct:
                normalized_words.append(always_correct[word])
                continue

            # Check for context-sensitive corrections
            if has_timer_context and word in context_corrections:
                # Check if next word is "my", "the", "timer", etc. (likely part of command)
                next_word = words[i + 1] if i + 1 < len(words) else ""
                if next_word in ["my", "the", "timer", "pomodoro", "session", "focus"]:
                    normalized_words.append(context_corrections[word])
                    continue

            # Check for fuzzy matches with always-correct words
            found_match = False
            for error, correction in always_correct.items():
                if self._fuzzy_match_word(word, error, threshold=1):
                    normalized_words.append(correction)
                    found_match = True
                    break

            if not found_match:
                normalized_words.append(word)

        return " ".join(normalized_words)

    async def _maybe_handle_tool_intent(
        self,
        user_id: str,
        text: str,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Very small, rules-based intent router for Phase 3.

        This keeps us decoupled from the LLM for simple, reliable commands.
        """
        # Normalize transcription errors before intent detection
        normalized_text = self._normalize_transcription(text)
        if normalized_text != text.lower():
            logger.info(f"Normalized transcription: '{text}' -> '{normalized_text}'")
        lowered = normalized_text.lower()

        # Timer / Pomodoro intents
        if "pomodoro" in lowered or "timer" in lowered:
            if any(word in lowered for word in ["start", "begin", "run"]):
                result = self._tools.execute_tool("timer", "start")
                return "timer.start", {
                    "message": "Starting a 25/5 Pomodoro.",
                    "session": result.get("session"),
                }
            # Check for end/finish/complete first (more specific intent)
            if any(word in lowered for word in ["end", "finish", "complete", "done"]):
                sessions = self._tools.get_tool("timer").list_sessions()
                if not sessions:
                    return "timer.end", {"message": "You don't have an active focus session."}
                latest = sessions[-1]
                if latest.status == "completed":
                    return "timer.end", {"message": "Your focus session is already complete."}
                result = self._tools.execute_tool("timer", "stop", session_id=latest.id)
                return "timer.end", {
                    "message": "Focus session ended. Great work!",
                    "session": result.get("session"),
                }
            if any(word in lowered for word in ["pause", "hold", "stop"]):
                sessions = self._tools.get_tool("timer").list_sessions()
                if not sessions:
                    return "timer.pause", {"message": "You don't have an active Pomodoro session."}
                latest = sessions[-1]
                result = self._tools.execute_tool("timer", "pause", session_id=latest.id)
                return "timer.pause", {
                    "message": "Paused your current Pomodoro.",
                    "session": result.get("session"),
                }

        # Ideas tool intents - removed simple detection to let LLM elaborate via tool calling
        # The LLM will handle idea creation through the ideas_tool function call,
        # which allows it to elaborate on the user's input and remove formatting

        return None, None


__all__ = ["ConversationService", "ConversationTurn"]


