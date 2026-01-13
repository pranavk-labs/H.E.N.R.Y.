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
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
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
                "description": "Manage idea notebook. Create, update, get, list, search, or delete ideas.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["create", "update", "get", "list", "delete", "search"],
                            "description": "The action to perform on ideas"
                        },
                        "text": {
                            "type": "string",
                            "description": "Idea text content (required for create, optional for update)"
                        },
                        "idea_id": {
                            "type": "string",
                            "description": "Idea ID (required for get, update, delete actions)"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags for the idea (optional)"
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query (required for search action)"
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
            
        Returns:
            Dict with final response from the model
        """
        # Build tool schemas
        tools = self.build_tool_schemas(tools_service)
        
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "tools": tools,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if options:
            payload["options"] = options
        
        iteration = 0
        while iteration < max_tool_iterations:
            response = await self._retry_request("POST", "/api/chat", json=payload)
            response_data = response.json()
            
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
                    # Parse arguments
                    if isinstance(function_args_str, str):
                        function_args = json.loads(function_args_str)
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
                        # Execute via tools_service
                        tool_result = tools_service.execute_tool("ideas", action, **{
                            k: v for k, v in function_args.items() if k != "action"
                        })
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


