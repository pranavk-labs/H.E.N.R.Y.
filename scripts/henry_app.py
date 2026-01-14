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

from app import HenryApp

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
logging.getLogger("backend.services.audio_service").setLevel(logging.WARNING)
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def main() -> None:
    """Main entry point for combined H.E.N.R.Y. application."""
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

