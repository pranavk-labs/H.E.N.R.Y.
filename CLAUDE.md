# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

H.E.N.R.Y. is a personalized conversational desk assistant running on Raspberry Pi. It features graph-based knowledge, productivity tools (Pomodoro timer, idea storage), and voice interaction with personality-driven responses via local LLM (Ollama).

**Architecture**: Hub-and-spoke model where Raspberry Pi is the voice interface hub and a home server (via Tailscale VPN) handles resource-intensive services (Ollama LLM, Neo4j graph database).

## Common Commands

```bash
# Install dependencies
poetry install

# Run development server
poetry run python scripts/dev_server.py

# Run tests
pytest                                      # All tests
pytest tests/test_conversation_service.py   # Single file
pytest tests/test_api.py::test_chat -v      # Single test

# Code formatting and linting
black backend/ tests/ tools/
flake8 backend/ tests/ tools/

# Deploy to Raspberry Pi
bash scripts/deploy_to_pi.sh
```

## Architecture

### Data Flow

```
Voice Input → Wake Word Detection → STT (Whisper) → ConversationService →
OllamaClient → PersonalityService → TTS (Piper) → Audio Output
```

### Key Services (Singleton Pattern)

Services use lazy-initialized singletons accessed via `ServiceClass.get_instance()`:

- **ConversationService** (`backend/services/conversation_service.py`): Utterance handling, intent routing, conversation history
- **OllamaClient** (`backend/services/ollama_client.py`): LLM client with health checks
- **KnowledgeService** (`backend/services/knowledge_service.py`): Graph operations (ideas, preferences)
- **PersonalityService** (`backend/services/personality_service.py`): Personality trait management, response generation
- **ToolsService** (`backend/services/tools_service.py`): Tool registry and execution
- **ScreenManager** (`backend/services/screen_manager.py`): Single source of truth for UI state

### Tools Plugin System

Tools inherit from `BaseTool` in `tools/base.py` and register with `ToolsRegistry`:

```python
from tools.base import BaseTool
from tools import ToolsRegistry

class MyTool(BaseTool):
    name = "my_tool"
    def execute(self, action: str, **kwargs):
        ...

# Access via ToolsService.get_instance().get_tool("my_tool")
```

Existing tools: `TimerTool` (Pomodoro), `IdeaTool` (idea notebook)

### Async Pattern

All I/O operations are async. Services provide sync wrappers for compatibility:

```python
# Async implementation
async def _handle_utterance_async(self, text: str):
    ...

# Sync wrapper
def handle_utterance(self, text: str):
    loop = self._get_loop()
    return loop.run_until_complete(self._handle_utterance_async(text))
```

### API Routes

- `/conversation/chat` - Chat endpoint
- `/conversation/history` - Conversation history
- `/conversation/ui/state` - UI state from ScreenManager
- `/productivity/timer/*` - Timer tool endpoints
- `/productivity/ideas/*` - Ideas tool endpoints
- `/health` - Service health checks

## Configuration

Settings loaded via Pydantic from `.env.local` (development) or `.env.pi` (production):

```python
from backend.config.settings import get_settings
settings = get_settings()
```

Key environment variables:
- `APP_ENV`: "development" or "production"
- `DEBUG`: True/False
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`: Graph database connection
- `OLLAMA_BASE_URL`: LLM service URL
- `AUDIO_ENABLED`: True on Pi, False for local dev
- `WAKE_WORD`: Trigger phrase (default: "Hey HENRY")

## Constraints

- **Python version**: 3.9, 3.10, or 3.11 only (not 3.12+ due to tflite-runtime for OpenWakeWord)
- **Line length**: 100 characters (black configured)
- **Graph DB**: NetworkX + SQLite (on-Pi) or external Neo4j (optional)
- **LLM**: Ollama with quantized models (Llama 3.2 3B Q4 or Mistral 7B Q4)
