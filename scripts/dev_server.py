#!/usr/bin/env python3
"""Development/production server script for H.E.N.R.Y.

This script runs the FastAPI backend server with proper signal handling
and graceful shutdown for production use.
"""

import logging
import os
import signal
import sys
from pathlib import Path

import uvicorn

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv

# Try to load .env.local first, fallback to .env
env_file = project_root / ".env.local"
if not env_file.exists():
    env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"Loaded environment from {env_file}")
else:
    print("Warning: No .env.local or .env file found. Using system environment variables.")

# Configure logging based on DEBUG environment variable
DEBUG_MODE = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
logger.info(f"Debug mode: {'ENABLED' if DEBUG_MODE else 'DISABLED'}")

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpcore.http11").setLevel(logging.WARNING)
logging.getLogger("httpcore.connection").setLevel(logging.WARNING)
logging.getLogger("openwakeword").setLevel(logging.WARNING)
logging.getLogger("openwakeword.model").setLevel(logging.WARNING)
logging.getLogger("openwakeword.utils").setLevel(logging.WARNING)
# Suppress uvicorn access logs for /conversation/ui/state polling endpoint
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
# Suppress Neo4j notification warnings (schema warnings about properties)
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)

# Global server instance for signal handling
_server_config = None


def signal_handler(signum, frame) -> None:
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down server...")
    sys.exit(0)


def main():
    """Run the development/production server."""
    global _server_config
    
    # Get configuration from environment
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    reload = debug  # Auto-reload only in debug mode
    
    logger.info(f"Starting H.E.N.R.Y. server on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Auto-reload: {reload}")

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Run uvicorn
        uvicorn.run(
            "backend.api.main:app",
            host=host,
            port=port,
            reload=reload,
            reload_dirs=[str(project_root / "backend")] if reload else None,
            reload_excludes=["*.git/*", "*.git", ".git/*", ".git"] if reload else None,
            log_level="info",
            access_log=False,  # Disable access logs (too noisy with polling)
        )
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
