"""Application coordinator for H.E.N.R.Y. - combines GUI and voice loop."""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Optional

try:
    import tkinter as tk
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.gui import HenryGUI
from app.voice_loop import VoiceLoop

logger = logging.getLogger(__name__)

# Constants
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


class HenryApp:
    """Combined H.E.N.R.Y. application with GUI and voice loop."""

    def __init__(self, enable_voice: bool = True, api_base_url: Optional[str] = None) -> None:
        """Initialize combined application.

        Args:
            enable_voice: Whether to enable voice loop (default: True)
            api_base_url: API base URL (default: from environment or module constant)
        """
        self.enable_voice = enable_voice
        self.api_base_url = api_base_url or os.getenv("API_BASE_URL") or API_BASE_URL
        self.voice_loop: Optional[VoiceLoop] = None
        self.voice_thread: Optional[threading.Thread] = None
        self.gui: Optional[HenryGUI] = None
        self._shutdown_requested = False

        # Log configuration
        logger.info(f"HenryApp initialized with API_BASE_URL: {self.api_base_url}")
        logger.info(f"Voice enabled: {self.enable_voice}")

    def start(self) -> None:
        """Start the combined application."""
        logger.info("Starting H.E.N.R.Y. combined application...")
        
        # Initialize voice loop if enabled
        if self.enable_voice:
            try:
                # Create voice loop without GUI first (will set GUI reference after GUI is created)
                self.voice_loop = VoiceLoop(api_base_url=self.api_base_url)
                logger.info("Voice loop initialized")
            except Exception as e:
                logger.error(f"Failed to initialize voice loop: {e}", exc_info=True)
                self.enable_voice = False
        
        # Initialize GUI
        try:
            if not HAS_TKINTER:
                logger.error("tkinter not available. GUI cannot be started.")
                raise RuntimeError("tkinter not available")
            
            self.gui = HenryGUI(voice_loop=self.voice_loop if self.enable_voice else None, api_base_url=self.api_base_url)
            
            # Set up status callback and GUI reference for voice loop
            if self.voice_loop:
                self.voice_loop.set_status_callback(self.gui.update_voice_status)
                self.voice_loop.gui = self.gui  # Set GUI reference for transcription display
            
            logger.info("GUI initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GUI: {e}", exc_info=True)
            raise
        
        # Start voice loop in background thread if enabled
        if self.enable_voice and self.voice_loop:
            try:
                self.voice_thread = threading.Thread(
                    target=self.voice_loop.start,
                    daemon=True,
                    name="VoiceLoop"
                )
                self.voice_thread.start()
                logger.info("Voice loop thread started")
            except Exception as e:
                logger.error(f"Failed to start voice loop thread: {e}", exc_info=True)
        
        # Set up signal handlers
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Set up window close handler
        self.gui.protocol("WM_DELETE_WINDOW", self.gui.on_close)
        
        # Run GUI mainloop (blocks until window is closed)
        logger.info("Starting GUI mainloop...")
        try:
            self.gui.mainloop()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """Shutdown the application gracefully."""
        if self._shutdown_requested:
            return
        
        logger.info("Shutting down H.E.N.R.Y. application...")
        self._shutdown_requested = True
        
        # Stop voice loop
        if self.voice_loop:
            self.voice_loop.stop()
        
        # Wait for voice thread to finish
        if self.voice_thread and self.voice_thread.is_alive():
            logger.info("Waiting for voice loop thread to finish...")
            self.voice_thread.join(timeout=5.0)
            if self.voice_thread.is_alive():
                logger.warning("Voice loop thread did not finish within timeout")
        
        logger.info("Shutdown complete")

