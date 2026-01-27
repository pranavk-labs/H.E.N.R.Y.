"""Tests for ConversationService core behavior."""

from backend.services.conversation_service import ConversationService
from backend.services.tools_service import ToolsService


def test_conversation_history_and_chat_flow(monkeypatch):
    service = ConversationService.get_instance()
    service.clear_history(user_id="u1")

    # Monkeypatch Ollama client generate to avoid network
    async def fake_generate(model, prompt, system_prompt=None, stream=False, options=None):
        return {"response": "Hello from fake LLM."}

    from backend.services import ollama_client as oc_mod

    client = oc_mod.OllamaClient.get_instance()
    monkeypatch.setattr(client, "generate", fake_generate)

    result = service.handle_utterance("Hello there", user_id="u1")
    assert "response" in result
    assert result["intent"] in {"chat", "timer.start", "timer.pause", "ideas.create"}

    history = service.get_history("u1")
    assert len(history) >= 2  # user + assistant
    assert history[0].role == "user"
    assert history[1].role == "assistant"


def test_conversation_routes_basic_tool_intents(monkeypatch):
    service = ConversationService.get_instance()
    tools = ToolsService.get_instance()

    # Ensure tools are registered and available
    assert "timer" in tools.list_tools()
    assert "ideas" in tools.list_tools()

    # Patch generate so we never call real LLM in this test
    async def fake_generate(model, prompt, system_prompt=None, stream=False, options=None):
        return {"response": "Stub response"}

    from backend.services import ollama_client as oc_mod

    client = oc_mod.OllamaClient.get_instance()
    monkeypatch.setattr(client, "generate", fake_generate)

    res1 = service.handle_utterance("Start a pomodoro timer", user_id="u2")
    assert res1["intent"] in {"timer.start", "chat"}

    res2 = service.handle_utterance("Remember this idea about Phase 3 tests", user_id="u2")
    assert res2["intent"] in {"ideas.create", "chat"}



