# H.E.N.R.Y. Tools Library

This directory contains the **tools library** - pluggable, reusable components that provide specific functionality (e.g., Pomodoro timer, idea notebook).

## Architecture

**Tools vs Services:**
- **Tools** (`/tools`) - High-level, user-facing functionality that can be invoked by voice commands, API, or GUI
- **Services** (`/backend/services`) - Lower-level infrastructure (database clients, knowledge service, screen manager)

Tools use services to accomplish their work, but tools are the primary interface for user interactions.

## Structure

```
tools/
├── __init__.py          # Public API - exports ToolsRegistry, BaseTool, TimerTool, IdeaTool
├── base.py              # BaseTool abstract class, ToolsRegistry, ToolContext
├── timer_tool.py        # Pomodoro timer tool
└── idea_tool.py         # Idea notebook tool
```

## Usage

### Importing Tools

```python
from tools import ToolsRegistry, TimerTool, IdeaTool

# Get the registry
registry = ToolsRegistry.get_instance()

# List available tools
tools = registry.list_tools()  # {'timer': 'TimerTool', 'ideas': 'IdeaTool'}

# Create and use a tool
timer = registry.create_tool("timer")
result = timer.execute("start", work_duration_minutes=25, break_duration_minutes=5)
```

### Creating New Tools

1. Create a new file in `/tools` (e.g., `my_tool.py`)
2. Inherit from `BaseTool`:

```python
from tools.base import BaseTool, ToolContext
from typing import Any, Dict

class MyTool(BaseTool):
    name = "my_tool"
    
    def __init__(self, context: ToolContext):
        super().__init__(context)
        # Access services via context
        self._knowledge = context.knowledge_service
        self._screen = context.screen_manager
    
    def execute(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        if action == "do_something":
            # Your tool logic here
            self._screen.update_status("Tool executed")
            return {"result": "success"}
        raise ValueError(f"Unknown action: {action}")
```

3. Register it in `tools/__init__.py`:

```python
from tools.my_tool import MyTool

_registry.register_tool("my_tool", MyTool)
```

## Tool Interface

All tools must:
- Inherit from `BaseTool`
- Set a `name` class attribute
- Implement `execute(action: str, **kwargs) -> Dict[str, Any]`
- Use `ToolContext` to access services (knowledge, screen manager)

## Available Tools

- **timer** (`TimerTool`) - Pomodoro timer functionality
- **ideas** (`IdeaTool`) - Idea notebook management

## Integration Points

Tools are used by:
- **Voice pipeline** (Phase 3) - Voice commands invoke tools
- **API endpoints** (`/backend/api/routes/productivity.py`) - HTTP wrappers around tools
- **GUI** (Phase 3+) - Direct tool invocation for UI interactions

