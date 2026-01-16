"""Ollama LLM service client with health checks, retry logic, and tool calling support."""

import json
import logging
import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from httpx import ConnectTimeout, PoolTimeout, ReadTimeout, RequestError

from backend.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Ollama client with connection management, health checks, and tool calling."""

    _instance: Optional["OllamaClient"] = None
    _client: Optional[httpx.AsyncClient] = None

    def __init__(self, settings: Settings):
        """Initialize Ollama client."""
        self.settings = settings
        self.base_url = settings.ollama_base_url
        self._connection_status: str = "disconnected"
        self._last_error: Optional[str] = None
        self._retry_delay: float = 1.0
        self._max_retry_delay: float = 60.0

    @classmethod
    def get_instance(cls) -> "OllamaClient":
        """Get or create the singleton instance."""
        if cls._instance is None:
            settings = get_settings()
            cls._instance = cls(settings)
        return cls._instance

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
            )
        return self._client

    async def connect(self) -> None:
        """Connect to Ollama service."""
        try:
            client = await self._get_client()
            # Verify connection by checking available models
            response = await client.get("/api/tags")
            response.raise_for_status()
            self._connection_status = "connected"
            self._last_error = None
            logger.info(f"Successfully connected to Ollama at {self.base_url}")
        except Exception as e:
            self._connection_status = "error"
            self._last_error = str(e)
            logger.error(f"Failed to connect to Ollama: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Ollama service."""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._connection_status = "disconnected"
            logger.info("Disconnected from Ollama")

    async def health_check(self) -> dict:
        """
        Check Ollama connection health.

        Returns:
            dict: Health status with 'status' and optional 'error' fields
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/tags", timeout=5.0)
            response.raise_for_status()
            self._connection_status = "connected"
            self._last_error = None
            return {
                "status": "healthy",
                "connected": True,
                "base_url": self.base_url,
            }
        except (ReadTimeout, ConnectTimeout, PoolTimeout) as e:
            self._connection_status = "error"
            self._last_error = "Connection timeout"
            logger.warning(f"Ollama health check timeout: {e}")
            return {
                "status": "unhealthy",
                "error": "Connection timeout",
                "connected": False,
            }
        except RequestError as e:
            self._connection_status = "error"
            self._last_error = str(e)
            logger.warning(f"Ollama health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False,
            }
        except Exception as e:
            self._connection_status = "error"
            self._last_error = str(e)
            logger.error(f"Ollama health check error: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False,
            }

    async def _retry_request(
        self, method: str, url: str, max_retries: int = 3, **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with exponential backoff retry logic.

        Args:
            method: HTTP method
            url: Request URL
            max_retries: Maximum number of retry attempts
            **kwargs: Additional arguments for httpx request

        Returns:
            httpx.Response: HTTP response

        Raises:
            httpx.HTTPError: If request fails after all retries
        """
        client = await self._get_client()
        delay = self._retry_delay

        for attempt in range(max_retries):
            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                # Reset delay on success
                delay = self._retry_delay
                return response
            except httpx.HTTPStatusError as e:
                # Log 500 errors with response body for debugging
                if e.response.status_code == 500:
                    error_body = e.response.text[:500] if hasattr(e.response, 'text') else str(e)
                    logger.error(f"Ollama 500 error on {method} {url}: {error_body}")
                if attempt == max_retries - 1:
                    raise
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, self._max_retry_delay)
            except httpx.RequestError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {delay}s..."
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, self._max_retry_delay)

        raise httpx.RequestError("Max retries exceeded")

    async def list_models(self) -> list[dict]:
        """
        List available Ollama models.

        Returns:
            list: List of available models
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            raise

    @property
    def is_connected(self) -> bool:
        """Check if connected to Ollama."""
        return self._connection_status == "connected"

    # ------------------------------------------------------------------
    # Text generation
    # ------------------------------------------------------------------
    async def generate(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any] | AsyncGenerator[str, None]:
        """Generate text from Ollama.

        Args:
            model: Name of the Ollama model to use.
            prompt: User prompt text.
            system_prompt: Optional system prompt / instructions.
            stream: If True, yields chunks of text from the stream.
            options: Extra model options passed to Ollama.

        Returns:
            - If stream is False: full JSON response from Ollama.
            - If stream is True: async generator yielding text chunks.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if options:
            payload["options"] = options

        async def _stream_generator() -> AsyncGenerator[str, None]:
            client = await self._get_client()
            async with client.stream("POST", "/api/generate", json=payload) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = response.json()  # type: ignore[assignment]
                    except Exception:
                        # Fallback: just yield the raw line
                        yield line
                        continue
                    text = data.get("response") or data.get("message", {}).get("content")
                    if text:
                        yield str(text)

        if stream:
            return _stream_generator()

        response = await self._retry_request("POST", "/api/generate", json=payload)
        return response.json()

    # ------------------------------------------------------------------
    # Tool calling support
    # ------------------------------------------------------------------
    def build_tool_schemas(self, tools_service: Any) -> List[Dict[str, Any]]:
        """Build JSON schema definitions for tools from ToolsService.
        
        Args:
            tools_service: ToolsService instance
            
        Returns:
            List of tool schema dictionaries in Ollama format
        """
        tools = []
        
        # Timer tool schema
        tools.append({
            "type": "function",
            "function": {
                "name": "timer_tool",
                "description": "Manage Pomodoro timer sessions. Start timers, pause, resume, complete, or check status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["start", "pause", "resume", "complete", "status", "list"],
                            "description": "The action to perform on the timer"
                        },
                        "work_duration_minutes": {
                            "type": "integer",
                            "description": "Work duration in minutes (for start action, default: 25)",
                            "default": 25
                        },
                        "break_duration_minutes": {
                            "type": "integer",
                            "description": "Break duration in minutes (for start action, default: 5)",
                            "default": 5
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Session ID (required for pause, resume, complete, status actions)"
                        }
                    },
                    "required": ["action"]
                }
            }
        })
        
        # Ideas tool schema
        tools.append({
            "type": "function",
            "function": {
                "name": "ideas_tool",
                "description": "Save and manage ideas in the notebook. Use 'create' for new ideas with is_continuation=true if refining the active idea, 'update' to modify existing ideas, 'close' when done. IMPORTANT: After calling this tool, respond naturally WITHOUT mentioning idea IDs, numbers, or technical details.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["create", "update", "get", "list", "delete", "search", "close"],
                            "description": "Action to perform. Use 'create' with is_continuation=true for active idea refinement, 'close' when user is done."
                        },
                        "text": {
                            "type": "string",
                            "description": "The idea content. RULES: (1) Expand the user's thought into a clear, complete description. (2) NEVER include meta-commentary like 'the user wants', 'this idea is about', or 'raw input'. (3) NO markdown, bullets, or formatting - plain text only. (4) Write as if explaining the idea to someone else. EXAMPLE: User says 'voice control for lights' -> Write 'A voice-controlled lighting system that allows hands-free control of room lighting through spoken commands, enabling dimming, color changes, and scheduling.'"
                        },
                        "is_continuation": {
                            "type": "boolean",
                            "description": "Set to true if user is adding details to the current active idea (refinement), false for completely new ideas"
                        },
                        "idea_id": {
                            "type": "string",
                            "description": "Idea ID (required for get, update, delete). Omit for update to use active idea."
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional tags for categorization"
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query (for search action)"
                        },
                        "is_continuation": {
                            "type": "boolean",
                            "description": "Set true when adding to or refining the current active idea rather than creating a new one"
                        }
                    },
                    "required": ["action"]
                }
            }
        })
        
        # Todos tool schema
        tools.append({
            "type": "function",
            "function": {
                "name": "todos_tool",
                "description": "Manage tasks and todos. Create tasks with priorities, categories, due dates, and track progress. Link tasks to ideas, add subtasks, and manage categories.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["create", "update", "delete", "complete", "list", "get", "create_category", "list_categories", "add_subtask", "create_subtask", "get_subtasks", "link_to_idea", "add_dependency", "start_timer"],
                            "description": "Action to perform on todos/tasks"
                        },
                        "title": {
                            "type": "string",
                            "description": "Task title (required for create, add_subtask, create_subtask)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Task description (optional)"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                            "description": "Task priority (default: medium)"
                        },
                        "difficulty": {
                            "type": "integer",
                            "description": "Task difficulty from 1-5 (default: 3)"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["todo", "in_progress", "completed", "cancelled"],
                            "description": "Task status (for update/filter)"
                        },
                        "category_id": {
                            "type": "string",
                            "description": "Category ID to assign task to or filter by"
                        },
                        "due_date": {
                            "type": "string",
                            "description": "Due date in ISO format (e.g., 2026-01-20T00:00:00Z)"
                        },
                        "estimated_minutes": {
                            "type": "integer",
                            "description": "Estimated time to complete in minutes"
                        },
                        "recurrence_pattern": {
                            "type": "string",
                            "enum": ["none", "daily", "weekly", "monthly"],
                            "description": "Recurrence pattern for recurring tasks (default: none)"
                        },
                        "todo_id": {
                            "type": "string",
                            "description": "Todo ID (required for update, delete, complete, get, etc.)"
                        },
                        "parent_todo_id": {
                            "type": "string",
                            "description": "Parent todo ID (for subtasks)"
                        },
                        "idea_id": {
                            "type": "string",
                            "description": "Idea ID to link to (for link_to_idea action)"
                        },
                        "depends_on_id": {
                            "type": "string",
                            "description": "Todo ID this task depends on (for add_dependency)"
                        },
                        "name": {
                            "type": "string",
                            "description": "Category name (for create_category)"
                        },
                        "color": {
                            "type": "string",
                            "description": "Category color hex code (for create_category, default: #808080)"
                        },
                        "icon": {
                            "type": "string",
                            "description": "Category icon emoji (for create_category, default: 📁)"
                        }
                    },
                    "required": ["action"]
                }
            }
        })
        
        return tools

    async def chat_with_tools(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools_service: Any,
        tools_callback: Any,
        system_prompt: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        max_tool_iterations: int = 5,
        pre_tool_speak_callback: Optional[callable] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Chat with Ollama using tool calling support.

        Args:
            model: Name of the Ollama model to use
            messages: List of message dictionaries with 'role' and 'content'
            tools_service: ToolsService instance for executing tools
            tools_callback: Callback function to execute tools: (tool_name, args) -> result
            system_prompt: Optional system prompt
            options: Extra model options
            max_tool_iterations: Maximum number of tool call iterations (default: 5)
            pre_tool_speak_callback: Optional callback to speak text before tool execution
            user_id: Optional user ID to pass to tools for context

        Returns:
            Dict with final response from the model
        """
        # Build tool schemas
        tools = self.build_tool_schemas(tools_service)
        
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "stream": False,  # CRITICAL: Disable streaming to get single JSON response
        }
        if system_prompt:
            payload["system"] = system_prompt
        if options:
            payload["options"] = options
        
        iteration = 0
        while iteration < max_tool_iterations:
            response = await self._retry_request("POST", "/api/chat", json=payload)

            # Parse response with robust error handling
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                # If streaming wasn't disabled properly, try to parse first line
                if "Extra data" in str(e):
                    logger.warning("Ollama returned streamed response despite stream=False. Parsing first object.")
                    response_text = response.text
                    # Get first line (first JSON object)
                    first_line = response_text.split('\n')[0]
                    try:
                        response_data = json.loads(first_line)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse Ollama response: {response_text[:200]}")
                        raise
                else:
                    logger.error(f"Failed to parse Ollama response: {response.text[:200]}")
                    raise
            
            message = response_data.get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])
            
            # If no tool calls, return the response
            if not tool_calls:
                return response_data
            
            # If there's content before tool calls, speak it first via callback
            if content and content.strip() and pre_tool_speak_callback:
                try:
                    if asyncio.iscoroutinefunction(pre_tool_speak_callback):
                        await pre_tool_speak_callback(content.strip())
                    else:
                        pre_tool_speak_callback(content.strip())
                except Exception as e:
                    logger.warning(f"Error in pre-tool speak callback: {e}")
            
            # Execute tool calls
            tool_messages = []
            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                function_name = function.get("name", "")
                function_args_str = function.get("arguments", "{}")
                
                try:
                    # Parse arguments with robust JSON extraction
                    if isinstance(function_args_str, str):
                        # Try standard parsing first
                        try:
                            function_args = json.loads(function_args_str)
                        except json.JSONDecodeError as e:
                            # If there's extra data after JSON, try to extract just the JSON part
                            if "Extra data" in str(e):
                                logger.debug(f"Extracting JSON from malformed response: {function_args_str[:100]}...")
                                # Use JSONDecoder to parse incrementally
                                decoder = json.JSONDecoder()
                                try:
                                    function_args, end_idx = decoder.raw_decode(function_args_str)
                                    extra_text = function_args_str[end_idx:].strip()
                                    if extra_text:
                                        logger.debug(f"Ignored extra text after JSON: {extra_text[:50]}...")
                                except json.JSONDecodeError:
                                    # If that fails too, try to find JSON object boundaries
                                    start_idx = function_args_str.find('{')
                                    if start_idx != -1:
                                        # Count braces to find the end of the JSON object
                                        brace_count = 0
                                        end_idx = start_idx
                                        for i in range(start_idx, len(function_args_str)):
                                            if function_args_str[i] == '{':
                                                brace_count += 1
                                            elif function_args_str[i] == '}':
                                                brace_count -= 1
                                                if brace_count == 0:
                                                    end_idx = i + 1
                                                    break
                                        json_str = function_args_str[start_idx:end_idx]
                                        function_args = json.loads(json_str)
                                        logger.debug(f"Extracted JSON via brace counting: {json_str}")
                                    else:
                                        raise
                            else:
                                raise
                    else:
                        function_args = function_args_str
                    
                    # Map Ollama function names to tool names and actions
                    tool_result = None
                    if function_name == "timer_tool":
                        action = function_args.get("action", "")
                        # Execute via tools_service
                        tool_result = tools_service.execute_tool("timer", action, **{
                            k: v for k, v in function_args.items() if k != "action"
                        })
                    elif function_name == "ideas_tool":
                        action = function_args.get("action", "")
                        # Execute via tools_service, inject user_id for context
                        tool_kwargs = {k: v for k, v in function_args.items() if k != "action"}
                        if user_id:
                            tool_kwargs["user_id"] = user_id
                        tool_result = tools_service.execute_tool("ideas", action, **tool_kwargs)
                    elif function_name == "todos_tool":
                        action = function_args.get("action", "")
                        # Execute via tools_service, inject user_id for context
                        tool_kwargs = {k: v for k, v in function_args.items() if k != "action"}
                        if user_id:
                            tool_kwargs["user_id"] = user_id
                        tool_result = tools_service.execute_tool("todos", action, **tool_kwargs)
                    else:
                        # Try callback if provided
                        if tools_callback:
                            tool_result = await tools_callback(function_name, function_args) if asyncio.iscoroutinefunction(tools_callback) else tools_callback(function_name, function_args)
                    
                    # Add tool result to messages
                    tool_messages.append({
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(tool_result) if tool_result else "{}"
                    })
                except Exception as e:
                    logger.error(f"Error executing tool {function_name}: {e}", exc_info=True)
                    tool_messages.append({
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps({"error": str(e)})
                    })
            
            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls
            })
            
            # Add tool results
            messages.extend(tool_messages)
            
            # Update payload for next iteration
            payload["messages"] = messages
            
            iteration += 1
        
        # If we hit max iterations, return the last response
        logger.warning(f"Reached max tool iterations ({max_tool_iterations})")
        return response_data if 'response_data' in locals() else {"message": {"content": "Maximum tool iterations reached"}}


