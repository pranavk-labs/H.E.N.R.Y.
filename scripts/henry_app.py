#!/usr/bin/env python3
"""Combined H.E.N.R.Y. application - GUI + Voice Loop in one process.

This script combines:
- Tkinter GUI for visual feedback (main thread)
- Voice loop for wake word detection and voice interaction (background thread)

Both components communicate with the backend API server (dev_server.py),
which runs separately and serves as the interface for external clients.

Usage:
    # Start API server in one terminal
    poetry run python scripts/dev_server.py

    # Start combined app in another terminal
    poetry run python scripts/henry_app.py

    # Or use the convenience script
    poetry run bash scripts/dev_run_all.sh
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load settings (this loads .env files into os.environ)
from backend.config.settings import get_settings
get_settings()  # This must be called to load .env files!

# Print startup info to stdout before logging is configured
print("=" * 60)
print("H.E.N.R.Y. Application Starting...")
print("=" * 60)
print(f"Current directory: {os.getcwd()}")
print(f"APP_ENV from os.environ: {os.getenv('APP_ENV', '(not set)')}")
print(f"API_BASE_URL from os.environ: {os.getenv('API_BASE_URL', '(not set)')}")
print()

# Configure logging FIRST before any other imports
DEBUG_MODE = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,  # Force reconfiguration if already configured
)
logger = logging.getLogger(__name__)
logger.info(f"Debug mode: {'ENABLED' if DEBUG_MODE else 'DISABLED'}")

from app import HenryApp

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpcore.http11").setLevel(logging.WARNING)
logging.getLogger("httpcore.connection").setLevel(logging.WARNING)
logging.getLogger("openwakeword").setLevel(logging.WARNING)
logging.getLogger("openwakeword.model").setLevel(logging.WARNING)
logging.getLogger("openwakeword.utils").setLevel(logging.WARNING)
logging.getLogger("backend.services.audio_service").setLevel(logging.WARNING)
# Note: neo4j logger not configured here - neo4j should not be imported on Pi (API mode)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def main() -> None:
    """Main entry point for combined H.E.N.R.Y. application."""
    # Log environment info early
    app_env = os.getenv("APP_ENV", "development")
    api_base_url_env = os.getenv("API_BASE_URL", "")
    logger.info(f"Starting H.E.N.R.Y. application - APP_ENV={app_env}")
    if api_base_url_env:
        logger.info(f"API_BASE_URL from environment: {api_base_url_env}")
    else:
        logger.info(f"API_BASE_URL not set in environment, using default: {API_BASE_URL}")

    parser = argparse.ArgumentParser(description="H.E.N.R.Y. Combined Application (GUI + Voice Loop)")
    parser.add_argument(
        "--no-voice",
        action="store_true",
        help="Disable voice loop (GUI only mode)"
    )
    parser.add_argument(
        "--api-url",
        default=API_BASE_URL,
        help=f"API base URL (default: {API_BASE_URL})"
    )

    args = parser.parse_args()

    # Get API base URL (from args or environment or default)
    api_base_url = args.api_url
    if api_base_url != API_BASE_URL:
        os.environ["API_BASE_URL"] = api_base_url

    logger.info(f"Final API_BASE_URL to use: {api_base_url}")
    
    try:
        app = HenryApp(enable_voice=not args.no_voice, api_base_url=api_base_url)
        app.start()
    except KeyboardInterrupt:
        logger.info("Application interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

