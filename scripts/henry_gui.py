#!/usr/bin/env python3
"""Minimal Phase 3 GUI for H.E.N.R.Y.

This is a lightweight tkinter-based GUI that:
- Polls the backend `/conversation/ui/state` endpoint
- Displays the current active view, status text, timer, and idea state
- Shows connection status and handles errors gracefully

It is intentionally simple and designed to run full-screen on a Pi display.
Production-ready with proper error handling and retry logic.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict

import httpx
import tkinter as tk
from tkinter import ttk

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
POLL_INTERVAL_SECONDS = 0.5
CONNECTION_TIMEOUT = 2.0
MAX_RETRY_DELAY = 5.0


@dataclass
class UIState:
    active_view: str = "idle"
    status_text: str = ""
    timer_state: Dict[str, Any] | None = None
    idea_view: Dict[str, Any] | None = None


class HenryGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("H.E.N.R.Y.")
        self.geometry("800x480")
        self.configure(bg="#101018")

        self._state = UIState()
        self._client = httpx.Client(timeout=CONNECTION_TIMEOUT)
        self._running = True
        self._connected = False
        self._retry_count = 0

        self._build_layout()
        
        # Start polling thread
        thread = threading.Thread(target=self._poll_loop, daemon=True)
        thread.start()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        self.main_frame = ttk.Frame(self, padding=16)
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#101018")
        style.configure("TLabel", background="#101018", foreground="#f0f0f5")
        
        # Define custom styles for status labels
        style.configure("StatusLabel.TLabel", background="#101018", foreground="#90ee90")  # Connected
        style.configure("ErrorLabel.TLabel", background="#101018", foreground="#ff6b6b")  # Disconnected

        self.active_view_label = ttk.Label(
            self.main_frame, text="View: idle", font=("Segoe UI", 18, "bold")
        )
        self.active_view_label.grid(row=0, column=0, sticky="w")

        self.status_label = ttk.Label(
            self.main_frame, text="", font=("Segoe UI", 14), wraplength=760
        )
        self.status_label.grid(row=1, column=0, sticky="w", pady=(8, 16))

        self.details_label = ttk.Label(
            self.main_frame, text="", font=("Consolas", 11), justify="left"
        )
        self.details_label.grid(row=2, column=0, sticky="nsew")

        # Footer with connection status
        self.footer = ttk.Frame(self, padding=(16, 8))
        self.footer.grid(row=1, column=0, sticky="ew")
        self.footer.columnconfigure(0, weight=1)
        self.footer_label = ttk.Label(
            self.footer, 
            text=f"H.E.N.R.Y. GUI - Connecting to {API_BASE_URL}...",
            style="ErrorLabel.TLabel"
        )
        self.footer_label.grid(row=0, column=0, sticky="w")

    # ------------------------------------------------------------------
    # Backend polling
    # ------------------------------------------------------------------
    def _poll_loop(self) -> None:
        """Poll backend API in a separate thread."""
        while self._running:
            try:
                resp = self._client.get(f"{API_BASE_URL}/conversation/ui/state", timeout=CONNECTION_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                
                self._state = UIState(
                    active_view=data.get("active_view", "idle"),
                    status_text=data.get("status_text", ""),
                    timer_state=data.get("timer_state") or {},
                    idea_view=data.get("idea_view") or {},
                )
                
                # Connection successful
                if not self._connected:
                    self._connected = True
                    self._retry_count = 0
                    self.after(0, lambda: self.footer_label.config(
                        text=f"H.E.N.R.Y. GUI - Connected to {API_BASE_URL}",
                        style="StatusLabel.TLabel"
                    ))
                
                self.after(0, self._refresh_ui)
                
            except httpx.TimeoutException:
                self._handle_connection_error(f"Connection timeout - retrying...")
            except httpx.ConnectError:
                self._handle_connection_error(f"Unable to connect to {API_BASE_URL} - retrying...")
            except httpx.HTTPStatusError as e:
                self._handle_connection_error(f"API error {e.response.status_code} - retrying...")
            except Exception as e:
                logger.error(f"Unexpected error in poll loop: {e}", exc_info=True)
                self._handle_connection_error(f"Unexpected error - retrying...")
            
            # Exponential backoff on retries
            if not self._connected:
                delay = min(POLL_INTERVAL_SECONDS * (2 ** min(self._retry_count, 3)), MAX_RETRY_DELAY)
                time.sleep(delay)
            else:
                time.sleep(POLL_INTERVAL_SECONDS)

    def _handle_connection_error(self, message: str) -> None:
        """Handle connection errors with exponential backoff."""
        self._connected = False
        self._retry_count += 1
        
        def update_ui():
            self.footer_label.config(
                text=f"{message} (attempt {self._retry_count})",
                style="ErrorLabel.TLabel"
            )
        
        self.after(0, update_ui)
        logger.warning(message)

    def _refresh_ui(self) -> None:
        """Refresh UI elements with current state."""
        if not self._connected:
            return
            
        self.active_view_label.config(text=f"View: {self._state.active_view}")
        self.status_label.config(text=self._state.status_text or "Waiting for commands...")

        details: Dict[str, Any] = {
            "timer": self._state.timer_state or {},
            "ideas": self._state.idea_view or {},
        }
        pretty = json.dumps(details, indent=2, ensure_ascii=False)
        self.details_label.config(text=pretty)

    def on_close(self) -> None:
        """Handle window close event."""
        self._running = False
        try:
            self._client.close()
        except Exception:
            pass
        finally:
            self.destroy()


def main() -> None:
    """Main entry point for GUI."""
    try:
        app = HenryGUI()
        app.protocol("WM_DELETE_WINDOW", app.on_close)
        app.mainloop()
    except KeyboardInterrupt:
        logger.info("GUI interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in GUI: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
