#!/usr/bin/env python3
"""Development server script for H.E.N.R.Y."""

import logging
import os
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run the development server."""
    # Get configuration from environment
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("DEBUG", "True").lower() == "true"

    logger.info(f"Starting H.E.N.R.Y. development server on {host}:{port}")
    logger.info(f"Auto-reload: {reload}")

    # Run uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host=host,
        port=port,
        reload=reload,
        reload_dirs=[str(project_root / "backend")],
        log_level="info",
    )


if __name__ == "__main__":
    main()


