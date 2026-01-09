"""Ollama LLM service client with health checks and retry logic."""

import asyncio
import logging
from typing import Optional

import httpx
from httpx import ConnectTimeout, PoolTimeout, ReadTimeout, RequestError

from backend.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Ollama client with connection management and health checks."""

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


