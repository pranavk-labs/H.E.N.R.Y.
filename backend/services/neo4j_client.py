"""Neo4j database client with connection pooling and health checks."""

import logging
from typing import Optional

from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import ServiceUnavailable

from backend.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j client with connection management and health checks."""

    _instance: Optional["Neo4jClient"] = None
    _driver: Optional[AsyncDriver] = None

    def __init__(self, settings: Settings):
        """Initialize Neo4j client."""
        self.settings = settings
        self._connection_status: str = "disconnected"
        self._last_error: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "Neo4jClient":
        """Get or create the singleton instance."""
        if cls._instance is None:
            settings = get_settings()
            cls._instance = cls(settings)
        return cls._instance

    async def connect(self) -> None:
        """Connect to Neo4j database."""
        if self._driver is not None:
            return

        try:
            logger.info(f"Connecting to Neo4j at {self.settings.neo4j_uri}")
            self._driver = AsyncGraphDatabase.driver(
                self.settings.neo4j_uri,
                auth=(self.settings.neo4j_user, self.settings.neo4j_password),
            )
            # Verify connection
            await self._driver.verify_connectivity()
            self._connection_status = "connected"
            self._last_error = None
            logger.info("Successfully connected to Neo4j")
        except Exception as e:
            self._connection_status = "error"
            self._last_error = str(e)
            logger.error(f"Failed to connect to Neo4j: {e}")
            if self._driver:
                await self._driver.close()
                self._driver = None
            raise

    async def disconnect(self) -> None:
        """Disconnect from Neo4j database."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            self._connection_status = "disconnected"
            logger.info("Disconnected from Neo4j")

    async def health_check(self) -> dict:
        """
        Check Neo4j connection health.

        Returns:
            dict: Health status with 'status' and optional 'error' fields
        """
        if self._driver is None:
            try:
                await self.connect()
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "error": str(e),
                    "connected": False,
                }

        try:
            # Simple query to verify connection
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 as test")
                await result.single()
            self._connection_status = "connected"
            self._last_error = None
            return {
                "status": "healthy",
                "connected": True,
                "uri": self.settings.neo4j_uri,
            }
        except ServiceUnavailable as e:
            self._connection_status = "error"
            self._last_error = str(e)
            logger.warning(f"Neo4j health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False,
            }
        except Exception as e:
            self._connection_status = "error"
            self._last_error = str(e)
            logger.error(f"Neo4j health check error: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "connected": False,
            }

    @property
    def driver(self) -> Optional[AsyncDriver]:
        """Get the Neo4j driver instance."""
        return self._driver

    @property
    def is_connected(self) -> bool:
        """Check if connected to Neo4j."""
        return self._driver is not None and self._connection_status == "connected"


