"""Main GUI for H.E.N.R.Y. application."""

from __future__ import annotations

import logging
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    import tkinter as tk
    from tkinter import ttk
    HAS_TKINTER = True
except ImportError:
    HAS_TKINTER = False

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.state import UIState
from app.ui import (
    CalendarView,
    ConfirmationDialog,
    IdeaNotebook,
    IdeaNotification,
    SevenSegmentDisplay,
    Sidebar,
    SmileyFace,
    TimerControls,
    TimerDisplay,
    TodoList,
)
from backend.config.settings import get_settings
from scripts import colors

# Import VoiceLoop type for type hints (circular import handling)
if sys.version_info >= (3, 8):
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from app.voice_loop import VoiceLoop
else:
    TYPE_CHECKING = False

logger = logging.getLogger(__name__)

# Constants
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
POLL_INTERVAL_SECONDS = 0.5
CONNECTION_TIMEOUT = 2.0
MAX_RETRY_DELAY = 5.0

class HenryGUI(tk.Tk):
    """Tkinter GUI for H.E.N.R.Y. that polls backend API for UI state."""

    def __init__(self, voice_loop: Optional["VoiceLoop"] = None, api_base_url: Optional[str] = None) -> None:
        """Initialize GUI.
        
        Args:
            voice_loop: Optional VoiceLoop instance for status display
            api_base_url: API base URL (default: from environment or module constant)
        """
        if not HAS_TKINTER:
            raise RuntimeError("tkinter not available. Install tkinter for GUI support.")
        
        super().__init__()
        self.title("H.E.N.R.Y.")

        # Load settings first
        self._settings = get_settings()

        # Get actual screen dimensions and use them
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        if screen_width > 0 and screen_height > 0:
            self.geometry(f"{screen_width}x{screen_height}")
        else:
            self.geometry("800x480")
        self.configure(bg=colors.MAIN_BG)

        # Enable fullscreen mode if configured (removes window decorations)
        if self._settings.fullscreen:
            self.attributes("-fullscreen", True)
            logger.info("Fullscreen mode enabled")

        self._state = UIState()
        self._api_base_url = api_base_url or os.getenv("API_BASE_URL") or API_BASE_URL
        self._client = httpx.Client(timeout=CONNECTION_TIMEOUT) if HAS_HTTPX else None
        self._running = True
        self._connected = False
        self._retry_count = 0
        self._voice_loop = voice_loop

        # Load personality timing settings
        self._happy_duration = self._settings.gui_happy_duration
        self._neutral_duration = self._settings.gui_neutral_duration
        self._sleepy_duration = self._settings.gui_sleepy_duration
        logger.info(f"GUI personality timings: Happy={self._happy_duration}s, Neutral={self._neutral_duration}s, Sleepy={self._sleepy_duration}s")
        logger.debug(f"GUI initialized: screen={screen_width}x{screen_height}, fullscreen={self._settings.fullscreen}, api_base_url={self._api_base_url}")

        self._build_layout()
        
        # Start polling thread
        thread = threading.Thread(target=self._poll_loop, daemon=True)
        thread.start()

    def _build_layout(self) -> None:
        """Build the GUI layout."""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        self.main_frame = ttk.Frame(self, padding=0)  # No padding - fill entire window
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=colors.FRAME_BG)
        style.configure("TLabel", background=colors.FRAME_BG, foreground=colors.TEXT_PRIMARY)

        # Define custom styles for status labels
        style.configure("StatusLabel.TLabel", background=colors.FRAME_BG, foreground=colors.STATUS_CONNECTED)
        style.configure("ErrorLabel.TLabel", background=colors.FRAME_BG, foreground=colors.STATUS_DISCONNECTED)

        # Content area for smiley face, timer, etc. - fill entire frame
        self.content_canvas = tk.Canvas(
            self.main_frame,
            bg=colors.CANVAS_BG,
            highlightthickness=0
        )
        self.content_canvas.grid(row=0, column=0, sticky="nsew")
        
        # Bind to canvas resize to update layout
        self.content_canvas.bind("<Configure>", self._on_canvas_configure)

        # Bind swipe gesture events for sidebar (also handles clicks)
        self.content_canvas.bind("<ButtonPress-1>", self._on_swipe_start)
        self.content_canvas.bind("<B1-Motion>", self._on_swipe_move)
        self.content_canvas.bind("<ButtonRelease-1>", self._on_swipe_end)
        
        # Initialize UI components
        self.smiley_face: Optional[SmileyFace] = None
        self.timer_display: Optional[TimerDisplay] = None
        self.timer_controls: Optional[TimerControls] = None
        self.confirmation_dialog: Optional[ConfirmationDialog] = None
        self.idea_notification: Optional[IdeaNotification] = None
        self.idea_notebook: Optional[IdeaNotebook] = None
        self.todo_list: Optional[TodoList] = None
        self.calendar_view: Optional[CalendarView] = None
        self.sidebar: Optional[Sidebar] = None
        
        # Track last interaction time for bored state
        # Initialize to current time to ensure we start in a happy state
        self._last_interaction_time = time.time()
        self._initialization_complete = False  # Track if first UI render is done
        self._last_idea_id: Optional[str] = None
        self._last_toast_idea_id: Optional[str] = None  # Track last idea shown as toast
        self._animation_job: Optional[str] = None
        self._timer_update_job: Optional[str] = None
        self._last_active_view: Optional[str] = None
        self._last_status_text: str = ""
        self._last_timer_state: Dict[str, Any] = {}
        self._last_idea_view: Dict[str, Any] = {}
        self._previous_view: Optional[str] = None
        self._swipe_animation_job: Optional[str] = None
        self._swipe_items: list = []

        # Track canvas size for resize detection
        self._last_canvas_width: int = 0
        self._last_canvas_height: int = 0
        self._animation_frame_count: int = 0  # For periodic size checks
        
        # Transcription text display
        self._transcription_text: str = ""
        self._transcription_text_id: Optional[int] = None

        # Sidebar swipe detection
        self._swipe_start_x: Optional[int] = None
        self._swipe_start_y: Optional[int] = None
        self._swipe_start_time: float = 0
        self._sidebar_visible: bool = False
        self._sidebar_animation_job: Optional[str] = None

        # Footer with connection status
        self.footer = ttk.Frame(self, padding=(16, 8))
        self.footer.grid(row=1, column=0, sticky="ew")
        self.footer.columnconfigure(0, weight=1)
        self.footer.columnconfigure(1, weight=0)
        self.footer.columnconfigure(2, weight=0)
        self.footer.columnconfigure(3, weight=0)
        style.configure("TFrame", background=colors.FOOTER_BG)
        style.configure("BackButton.TButton", background=colors.BUTTON_BG, foreground=colors.TEXT_PRIMARY)
        
        self.footer_label = ttk.Label(
            self.footer, 
            text=f"H.E.N.R.Y. - Connecting to {self._api_base_url}...",
            style="ErrorLabel.TLabel"
        )
        self.footer_label.grid(row=0, column=0, sticky="w")
        
        # Navigation breadcrumb (shows navigation stack)
        self.breadcrumb_label = ttk.Label(
            self.footer,
            text="",
            style="StatusLabel.TLabel"
        )
        self.breadcrumb_label.grid(row=0, column=1, sticky="e", padx=(16, 8))
        
        # Back button
        self.back_button = ttk.Button(
            self.footer,
            text="← Back",
            command=self._on_back_button,
            style="BackButton.TButton",
            width=8
        )
        # Initially hidden, will be shown when navigation stack has depth > 1
        
        # Voice loop status label (if voice loop is enabled)
        if self._voice_loop:
            self.voice_status_label = ttk.Label(
                self.footer,
                text="Voice: Starting...",
                style="ErrorLabel.TLabel"
            )
            self.voice_status_label.grid(row=0, column=3, sticky="e", padx=(16, 0))

    def update_voice_status(self, status: str) -> None:
        """Update voice loop status display and listening state (thread-safe)."""
        # Update smiley face listening state based on status
        is_listening = "listening" in status.lower() and "for" not in status.lower()
        if self.smiley_face:
            try:
                self.after(0, lambda: self.smiley_face.set_listening(is_listening))
            except Exception:
                pass  # GUI might be closed

        if hasattr(self, 'voice_status_label'):
            try:
                self.after(0, lambda: self.voice_status_label.config(
                    text=f"Voice: {status}",
                    style="StatusLabel.TLabel" if status.startswith("Listening") else "ErrorLabel.TLabel"
                ))
            except Exception:
                pass  # GUI might be closed
    
    def _on_back_button(self) -> None:
        """Handle back button click."""
        if not HAS_HTTPX or not self._client:
            return
        
        try:
            resp = self._client.post(f"{self._api_base_url}/conversation/ui/back", timeout=CONNECTION_TIMEOUT)
            resp.raise_for_status()
            logger.info("Back navigation triggered")
        except Exception as e:
            logger.error(f"Failed to trigger back navigation: {e}", exc_info=True)
    
    def _update_navigation_ui(self) -> None:
        """Update navigation breadcrumb and back button visibility."""
        view_stack = self._state.view_stack if self._state.view_stack else ["idle"]
        active_states = self._state.active_states if self._state.active_states else []
        
        # Show back button only if we can go back (stack depth > 1)
        can_go_back = len(view_stack) > 1
        
        if can_go_back:
            self.back_button.grid(row=0, column=2, sticky="e", padx=(8, 0))
        else:
            self.back_button.grid_remove()
        
        # Build breadcrumb text showing navigation path
        if len(view_stack) > 1:
            # Show the path: idle > pomodoro > ideas
            breadcrumb_parts = []
            for view in view_stack:
                view_name = view.capitalize()
                breadcrumb_parts.append(view_name)
            breadcrumb_text = " > ".join(breadcrumb_parts)
        else:
            breadcrumb_text = ""
        
        # Add active states indicator if any
        if active_states:
            state_text = ", ".join(s.capitalize() for s in active_states)
            if breadcrumb_text:
                breadcrumb_text += f" | Active: {state_text}"
            else:
                breadcrumb_text = f"Active: {state_text}"
        
        self.breadcrumb_label.config(text=breadcrumb_text)
    
    def display_transcription(self, text: str) -> None:
        """Display transcribed text on the GUI (thread-safe).
        
        Args:
            text: The transcribed text to display, or empty string to clear
        """
        def update_display():
            try:
                self._transcription_text = text
                self._draw_transcription_text()
            except Exception:
                pass  # GUI might be closed
        
        self.after(0, update_display)
    
    def _draw_transcription_text(self) -> None:
        """Draw the transcription text on the canvas."""
        # Remove existing transcription text
        if self._transcription_text_id is not None:
            try:
                self.content_canvas.delete(self._transcription_text_id)
            except Exception:
                pass
            self._transcription_text_id = None
        
        # Don't draw if text is empty
        if not self._transcription_text:
            return
        
        # Get canvas dimensions
        self.update_idletasks()
        canvas_width = self.content_canvas.winfo_width()
        canvas_height = self.content_canvas.winfo_height()
        
        if canvas_width <= 1:
            canvas_width = self.winfo_width() or 800
        if canvas_height <= 1:
            canvas_height = self.winfo_height() or 480
        
        # Position transcription text at bottom center, above footer
        # Use 85% from top (leaving space at bottom for footer)
        x = canvas_width // 2
        y = int(canvas_height * 0.85)
        
        # Calculate font size based on screen size (responsive)
        base_font_size = max(14, int(canvas_width * 0.02))
        font = ("Segoe UI", base_font_size)
        
        # Calculate max width for text wrapping (80% of canvas width)
        max_width = int(canvas_width * 0.8)
        
        # Draw text with word wrapping
        # Tkinter canvas text doesn't support automatic wrapping, so we'll use a simple approach
        # For longer text, we'll truncate and add ellipsis
        display_text = self._transcription_text
        if len(display_text) > 100:  # Rough character limit
            display_text = display_text[:97] + "..."
        
        try:
            self._transcription_text_id = self.content_canvas.create_text(
                x, y,
                text=display_text,
                font=font,
                fill=colors.TEXT_PRIMARY,
                anchor="center",
                width=max_width,
                justify="center"
            )
        except Exception:
            pass

    def _poll_loop(self) -> None:
        """Poll backend API in a separate thread."""
        if not HAS_HTTPX or not self._client:
            logger.warning("httpx not available, skipping API polling")
            return
        
        while self._running:
            try:
                resp = self._client.get(f"{self._api_base_url}/conversation/ui/state", timeout=CONNECTION_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()

                # Track when timer state was received for countdown calculation
                timer_state_received_at = time.time() if data.get("timer_state") else 0.0

                self._state = UIState(
                    active_view=data.get("active_view", "idle"),
                    status_text=data.get("status_text", ""),
                    timer_state=data.get("timer_state") or {},
                    idea_view=data.get("idea_view") or {},
                    timer_state_received_at=timer_state_received_at,
                    view_stack=data.get("view_stack", ["idle"]),
                    active_states=data.get("active_states", []),
                    todo_filter_status=data.get("todo_filter_status"),
                    selected_category_id=data.get("selected_category_id"),
                    active_todo_id=data.get("active_todo_id"),
                    calendar_view_mode=data.get("calendar_view_mode", "upcoming"),
                    calendar_selected_date=data.get("calendar_selected_date"),
                    calendar_filter_type=data.get("calendar_filter_type"),
                    active_event_id=data.get("active_event_id"),
                )
                
                # Connection successful
                if not self._connected:
                    self._connected = True
                    self._retry_count = 0
                    logger.info(f"Connected to API server: {self._api_base_url}")
                    self.after(0, lambda: self.footer_label.config(
                        text=f"H.E.N.R.Y. - Connected to {self._api_base_url}",
                        style="StatusLabel.TLabel"
                    ))
                
                self.after(0, self._refresh_ui)
                
            except httpx.TimeoutException:
                self._handle_connection_error(f"Connection timeout - retrying...")
            except httpx.ConnectError:
                self._handle_connection_error(f"Unable to connect to {self._api_base_url} - retrying...")
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

        # On first render, ensure we start happy by resetting interaction time
        if not self._initialization_complete:
            self._last_interaction_time = time.time()
            self._initialization_complete = True

        # Check if state changed (for interaction tracking)
        view_changed = self._state.active_view != getattr(self, '_last_active_view', None)
        status_changed = self._state.status_text != getattr(self, '_last_status_text', None)
        timer_changed = self._state.timer_state != getattr(self, '_last_timer_state', None)
        idea_changed = self._state.idea_view != getattr(self, '_last_idea_view', None)

        state_changed = view_changed or status_changed or timer_changed or idea_changed

        if state_changed:
            logger.debug(f"State changed: view={view_changed}, status={status_changed}, timer={timer_changed}, idea={idea_changed}")
            if view_changed:
                logger.debug(f"View changed: {getattr(self, '_last_active_view', None)} -> {self._state.active_view}")
            self._last_interaction_time = time.time()
            self._last_active_view = self._state.active_view
            self._last_status_text = self._state.status_text
            self._last_timer_state = self._state.timer_state.copy() if self._state.timer_state else {}
            self._last_idea_view = self._state.idea_view.copy() if self._state.idea_view else {}
        
        # Update navigation UI (breadcrumb and back button)
        self._update_navigation_ui()
        
        # Get canvas dimensions - use actual window size
        self.update_idletasks()
        canvas_width = self.content_canvas.winfo_width()
        canvas_height = self.content_canvas.winfo_height()
        
        # Default to window size if canvas not yet rendered
        if canvas_width <= 1:
            canvas_width = self.winfo_width() or 800
        if canvas_height <= 1:
            canvas_height = self.winfo_height() or 480
        
        # Use minimal padding (1% on all sides for maximum screen usage)
        padding = int(min(canvas_width, canvas_height) * 0.01)
        usable_width = canvas_width - (padding * 2)
        usable_height = canvas_height - (padding * 2)
        
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        # Only clear and redraw if view changed or timer needs update
        # Preserve confirmation dialog state before clearing
        had_confirmation_dialog = self.confirmation_dialog is not None
        if view_changed or (self._state.active_view == "pomodoro" and timer_changed):
            # Clear canvas only when view changes
            self.content_canvas.delete("all")
            self.smiley_face = None
            self.timer_display = None
            self.timer_controls = None
            # Clear confirmation dialog reference (will redraw if it was visible)
            if self.confirmation_dialog:
                self.confirmation_dialog.clear()
            # Only reset dialog on view change, preserve it on timer updates
            if view_changed:
                self.confirmation_dialog = None
                had_confirmation_dialog = False
            else:
                self.confirmation_dialog = None
            # Reset transcription text ID so it gets redrawn
            self._transcription_text_id = None
        
        # Calculate sleepiness level based on time since last interaction
        # Uses configured thresholds from settings
        time_since_interaction = time.time() - self._last_interaction_time
        if time_since_interaction < self._happy_duration:
            sleepiness_level = 0  # Happy
        elif time_since_interaction < self._neutral_duration:
            sleepiness_level = 1  # Neutral
        elif time_since_interaction < self._sleepy_duration:
            sleepiness_level = 2  # Sleepy
        else:
            sleepiness_level = 3  # Very sleepy (asleep)
        
        # Handle different views with swipe animation
        previous_view = getattr(self, '_previous_view', None)
        is_tool_view = self._state.active_view in ("pomodoro", "ideas", "todo_list", "calendar")
        was_tool_view = previous_view in ("pomodoro", "ideas", "todo_list", "calendar")
        
        # Trigger swipe animation if switching TO a tool view
        swipe_animating = False
        if view_changed and is_tool_view and not was_tool_view:
            self._animate_swipe_in(center_x, center_y, canvas_width, sleepiness_level)
            swipe_animating = True
        
        # Normal view update (runs after swipe animation starts or if no swipe needed)
        if self._state.active_view == "pomodoro" and self._state.timer_state:
            # Show timer display (unless swipe animation is handling it)
            if not swipe_animating:
                if self.timer_display is None or view_changed:
                    # Position timer at 35% from top (centered vertically in upper portion)
                    timer_y = int(canvas_height * 0.35)
                    self._show_timer_display(center_x, timer_y, canvas_width)
                else:
                    # Update timer display screen width if changed
                    if hasattr(self.timer_display, 'screen_width') and self.timer_display.screen_width != canvas_width:
                        # Recreate timer display with new screen width
                        timer_y = int(canvas_height * 0.35)
                        self.timer_display.clear()
                        self.timer_display = None
                        self._show_timer_display(center_x, timer_y, canvas_width)
                    else:
                        # Just update timer values
                        self._update_timer_display()
                
                # Show timer controls below timer display
                timer_status = self._state.timer_state.get("status", "paused")
                if self.timer_controls is None or view_changed:
                    # Position controls below timer (work timer + break timer + spacing)
                    timer_display_height = (self.timer_display.digit_height * 2) + int(canvas_width * 0.05) if self.timer_display else 200
                    controls_y = int(canvas_height * 0.35) + timer_display_height + int(canvas_width * 0.05)
                    self._show_timer_controls(center_x, controls_y, canvas_width, timer_status == "paused")
                else:
                    # Update controls state
                    self.timer_controls.set_paused(timer_status == "paused")

                # Redraw confirmation dialog if it was visible before canvas clear
                if had_confirmation_dialog and self.confirmation_dialog is None:
                    self.confirmation_dialog = ConfirmationDialog(
                        self.content_canvas, center_x, center_y, canvas_width,
                        on_confirm=self._handle_end_confirm,
                        on_cancel=self._handle_end_cancel
                    )
            # Hide smiley face
            if self.smiley_face:
                for item in getattr(self.smiley_face, 'face_items', []):
                    self.content_canvas.delete(item)
                self.smiley_face = None

            # Show toast notification for recently created ideas while timer is running
            idea_view = self._state.idea_view or {}
            idea_id = idea_view.get("active_idea_id")
            idea_text = idea_view.get("draft_text", "")
            is_active = idea_view.get("is_active", False)
            last_updated = idea_view.get("last_updated", 0)

            # Show toast if idea was created/updated within last 10 seconds
            if idea_id and is_active and idea_text and last_updated:
                time_since_update = time.time() - last_updated
                if time_since_update < 10:
                    # Show or update toast notification
                    if self.idea_notification is None:
                        self.idea_notification = IdeaNotification(
                            self.content_canvas,
                            center_x,
                            padding,
                            canvas_width
                        )
                    # Only show if this is a new idea (not already shown)
                    if not hasattr(self, '_last_toast_idea_id') or self._last_toast_idea_id != idea_id:
                        self.idea_notification.show(idea_text)
                        self._last_toast_idea_id = idea_id

            # Start timer update loop if timer is running (always check, not just if job is None)
            timer_status = self._state.timer_state.get("status", "paused")
            if timer_status == "running":
                if self._timer_update_job is None:
                    self._start_timer_update_loop()
            else:
                # Stop timer updates if not running
                if self._timer_update_job:
                    self.after_cancel(self._timer_update_job)
                    self._timer_update_job = None
        elif self._state.active_view == "ideas":
            # Show idea notebook view (persists until idea is no longer active)
            if not swipe_animating:
                idea_view = self._state.idea_view or {}
                idea_id = idea_view.get("active_idea_id")
                idea_text = idea_view.get("draft_text", "")
                is_active = idea_view.get("is_active", False)

                if idea_id and is_active and idea_text:
                    # Show or update the notebook
                    self._show_idea_notification(center_x, padding, idea_text, canvas_width)
                    self._last_idea_id = idea_id
                elif self.idea_notebook:
                    # No active idea - hide notebook
                    self.idea_notebook.hide()
            # Stop timer updates
            if self._timer_update_job:
                self.after_cancel(self._timer_update_job)
                self._timer_update_job = None
        elif self._state.active_view == "todo_list":
            # Show todo list view
            if not swipe_animating:
                self._show_todo_list(canvas_width, canvas_height)
            # Stop timer updates
            if self._timer_update_job:
                self.after_cancel(self._timer_update_job)
                self._timer_update_job = None
        elif self._state.active_view == "calendar":
            # Show calendar view
            if not swipe_animating:
                self._show_calendar(canvas_width, canvas_height)
            # Stop timer updates
            if self._timer_update_job:
                self.after_cancel(self._timer_update_job)
                self._timer_update_job = None
        else:
            # Idle view - show smiley face
            if self.smiley_face is None or view_changed:
                self._show_smiley_face(center_x, center_y, canvas_width)
            # Hide timer
            if self.timer_display:
                self.timer_display.clear()
                self.timer_display = None
            # Hide timer controls
            if self.timer_controls:
                self.timer_controls.clear()
                self.timer_controls = None
            # Hide confirmation dialog if visible
            if self.confirmation_dialog:
                self.confirmation_dialog.clear()
                self.confirmation_dialog = None
            # Hide idea notebook if visible
            if self.idea_notebook:
                self.idea_notebook.hide()
            # Hide todo list if visible
            if self.todo_list:
                self.todo_list.hide()
            # Hide calendar if visible
            if self.calendar_view:
                self.calendar_view.hide()
            # Stop timer updates
            if self._timer_update_job:
                self.after_cancel(self._timer_update_job)
                self._timer_update_job = None
        
        # Update sleepiness level for smiley face
        if self.smiley_face:
            self.smiley_face.sleepiness_level = sleepiness_level
        
        # Store previous view for next comparison
        self._previous_view = self._state.active_view
        
        # Redraw transcription text if it exists (in case canvas was cleared)
        if self._transcription_text:
            self._draw_transcription_text()
        
        # Start animation loop if not already running
        if self._animation_job is None:
            self._start_animation_loop()
    
    def _start_timer_update_loop(self) -> None:
        """Start timer update loop (updates every second when running)."""
        if not self._running:
            self._timer_update_job = None
            return
        
        # Only update if timer is active and running
        if (self._state.active_view == "pomodoro" and 
            self._state.timer_state and 
            self._state.timer_state.get("status") == "running"):
            # Update timer display
            self._update_timer_display()
            # Schedule next update
            self._timer_update_job = self.after(1000, self._start_timer_update_loop)
        else:
            # Timer stopped or paused
            self._timer_update_job = None
    
    def _update_timer_display(self) -> None:
        """Update timer display values without full UI refresh."""
        if self.timer_display is None:
            return

        timer_state = self._state.timer_state
        if not timer_state:
            return

        # Get remaining seconds from state (calculated server-side)
        remaining_work_seconds = timer_state.get("remaining_work_seconds", 0)
        remaining_break_seconds = timer_state.get("remaining_break_seconds", 0)
        phase = timer_state.get("phase", "work")
        status = timer_state.get("status", "paused")

        # If timer is running, calculate elapsed time since last state update
        if status == "running" and self._state.timer_state_received_at > 0:
            elapsed_since_update = int(time.time() - self._state.timer_state_received_at)

            # Subtract elapsed time from the appropriate counter based on phase
            if phase == "work":
                remaining_work_seconds = max(0, remaining_work_seconds - elapsed_since_update)
            elif phase == "break":
                remaining_break_seconds = max(0, remaining_break_seconds - elapsed_since_update)

        work_minutes = remaining_work_seconds // 60
        work_seconds = remaining_work_seconds % 60

        # Always show both timers (work on top, break below)
        # Break timer shows remaining time if in break phase, otherwise full duration
        break_minutes = remaining_break_seconds // 60
        break_seconds = remaining_break_seconds % 60
        self.timer_display.update_timer(
            work_minutes, work_seconds,
            break_minutes=break_minutes,
            break_seconds=break_seconds
        )
    
    def _show_smiley_face(self, x: int, y: int, screen_width: int) -> None:
        """Show smiley face at position.
        
        Args:
            x: Center x coordinate
            y: Center y coordinate
            screen_width: Screen width for responsive sizing
        """
        if self.smiley_face is None:
            self.smiley_face = SmileyFace(self.content_canvas, x, y, screen_width)
        else:
            # Update position and screen width if changed
            if self.smiley_face.screen_width != screen_width:
                self.smiley_face.screen_width = screen_width
                self.smiley_face.size = int(screen_width * 0.4)
                self.smiley_face.base_radius = self.smiley_face.size // 2
            self.smiley_face.center_x = x
            self.smiley_face.center_y = y
            # Redraw if position changed significantly
            if abs(self.smiley_face.center_x - x) > 10 or abs(self.smiley_face.center_y - y) > 10:
                self.smiley_face._draw_face()
    
    def _on_canvas_click(self, event) -> None:
        """Handle canvas click events for timer controls, confirmation dialog, and todo list."""
        x, y = event.x, event.y

        # Check sidebar first (if visible)
        if self._sidebar_visible and self.sidebar:
            if self.sidebar.handle_touch((x, y)):
                return

        # Check confirmation dialog first (if visible)
        if self.confirmation_dialog:
            if self.confirmation_dialog.handle_click(x, y):
                return
        
        # Check timer controls (if visible)
        if self.timer_controls:
            if self.timer_controls.handle_click(x, y):
                return
        
        # Check todo list (if visible)
        if self.todo_list:
            if self.todo_list.handle_touch((x, y)):
                return
        
        # Check calendar view (if visible)
        if self.calendar_view:
            if self.calendar_view.handle_touch((x, y)):
                return
        
        # Check idea notebook (if visible)
        if self.idea_notebook:
            if self.idea_notebook._on_close_click(event):
                return
    
    def _on_canvas_configure(self, event) -> None:
        """Handle canvas resize event."""
        # Only trigger UI refresh if size actually changed significantly
        new_width = event.width
        new_height = event.height

        # Check if size changed by more than a few pixels (avoid micro-adjustments)
        width_changed = abs(new_width - self._last_canvas_width) > 5
        height_changed = abs(new_height - self._last_canvas_height) > 5

        if width_changed or height_changed:
            logger.debug(f"Canvas resized: {self._last_canvas_width}x{self._last_canvas_height} -> {new_width}x{new_height}")
            self._last_canvas_width = new_width
            self._last_canvas_height = new_height

            # Trigger UI refresh to recenter and resize elements
            if self._connected:
                # Force redraw by clearing smiley face and timer
                if self.smiley_face:
                    for item in getattr(self.smiley_face, 'face_items', []):
                        self.content_canvas.delete(item)
                    self.smiley_face = None
                    logger.debug("Cleared smiley face for resize")

                if self.timer_display:
                    self.timer_display.clear()
                    self.timer_display = None
                    logger.debug("Cleared timer display for resize")
                
                if self.timer_controls:
                    self.timer_controls.clear()
                    self.timer_controls = None
                    logger.debug("Cleared timer controls for resize")

                # Refresh UI will recreate elements at new center
                self._refresh_ui()

    def _on_swipe_start(self, event) -> None:
        """Handle swipe gesture start."""
        self._swipe_start_x = event.x
        self._swipe_start_y = event.y
        self._swipe_start_time = time.time()

    def _on_swipe_move(self, event) -> None:
        """Handle swipe gesture movement."""
        # If sidebar is visible and user is dragging it, update position
        if self._sidebar_visible and self.sidebar:
            if self._swipe_start_x is not None:
                delta_x = event.x - self._swipe_start_x
                # Only allow dragging to the left (closing)
                if delta_x < 0:
                    new_offset = max(-self.sidebar.sidebar_width, int(delta_x))
                    self.sidebar.update_position(new_offset)

    def _on_swipe_end(self, event) -> None:
        """Handle swipe gesture end and regular clicks."""
        if self._swipe_start_x is None or self._swipe_start_y is None:
            return

        # Calculate swipe distance and velocity
        delta_x = event.x - self._swipe_start_x
        delta_y = event.y - self._swipe_start_y
        delta_time = time.time() - self._swipe_start_time

        # Prevent division by zero
        if delta_time < 0.01:
            delta_time = 0.01

        velocity_x = delta_x / delta_time

        # Detect right swipe from left edge (show sidebar)
        # Must start from left 20% of screen and swipe right at least 100px or 500px/s
        screen_width = self.content_canvas.winfo_width()
        if screen_width <= 1:
            screen_width = 800

        left_edge_threshold = screen_width * 0.2

        # Check if this was a swipe or just a click (small movement)
        is_swipe = abs(delta_x) > 20 or abs(delta_y) > 20 or abs(velocity_x) > 200

        if not self._sidebar_visible:
            # Check for right swipe from left edge
            if is_swipe and ((self._swipe_start_x < left_edge_threshold and
                delta_x > 100 and abs(delta_y) < 100) or velocity_x > 500):
                # Show sidebar
                logger.info(f"Right swipe detected from left edge (delta_x={delta_x:.0f}px, velocity={velocity_x:.0f}px/s)")
                self._show_sidebar()
            elif not is_swipe:
                # Regular click - handle with existing click logic
                self._on_canvas_click(event)
        else:
            # Sidebar is visible - check if we should close it
            # Close if: swiped left significantly OR clicked outside sidebar
            if is_swipe and (delta_x < -50 or velocity_x < -300):
                # Swiped left - close
                logger.info(f"Left swipe detected, closing sidebar (delta_x={delta_x:.0f}px, velocity={velocity_x:.0f}px/s)")
                self._hide_sidebar()
            elif not is_swipe and event.x > self.sidebar.sidebar_width:
                # Clicked outside sidebar - close
                logger.info("Click outside sidebar detected, closing")
                self._hide_sidebar()
            elif not is_swipe:
                # Regular click on sidebar - handle with existing click logic
                self._on_canvas_click(event)
            else:
                # Incomplete swipe - snap back to open position
                logger.debug("Incomplete swipe, snapping sidebar back to open position")
                if self.sidebar:
                    self._animate_sidebar(self.sidebar.x_offset, 0, 200)

        # Reset swipe tracking
        self._swipe_start_x = None
        self._swipe_start_y = None
        self._swipe_start_time = 0

    def _show_sidebar(self) -> None:
        """Show the sidebar with animation."""
        if self._sidebar_visible:
            return

        logger.info("Showing sidebar")
        self._sidebar_visible = True

        # Get canvas dimensions
        self.update_idletasks()
        screen_width = self.content_canvas.winfo_width()
        screen_height = self.content_canvas.winfo_height()
        if screen_width <= 1:
            screen_width = 800
        if screen_height <= 1:
            screen_height = 480

        # Create sidebar if needed
        if self.sidebar is None:
            self.sidebar = Sidebar(
                self.content_canvas,
                screen_width,
                screen_height,
                on_close=self._hide_sidebar,
                on_exit=self._on_exit_button,
                on_volume_change=self._on_volume_change,
            )

        # Fetch data for sidebar
        todos = []
        events = []
        current_volume = 0.7

        if self._client:
            try:
                # Fetch upcoming todos ordered by due date (about 10 items)
                todo_response = self._client.get(
                    f"{self._api_base_url}/api/todos",
                    params={"limit": 10}
                )
                if todo_response.status_code == 200:
                    todos_list = todo_response.json().get("todos", [])
                    # Sort by due_date (None values go to end)
                    todos = sorted(
                        todos_list,
                        key=lambda t: (t.get("due_date") is None, t.get("due_date") or "")
                    )
                    logger.info(f"Fetched {len(todos)} todos for sidebar")

                # Fetch today's events
                event_response = self._client.get(
                    f"{self._api_base_url}/calendar/events/today"
                )
                if event_response.status_code == 200:
                    events = event_response.json().get("events", [])
                    logger.info(f"Fetched {len(events)} events for sidebar")
            except Exception as e:
                logger.error(f"Failed to fetch sidebar data: {e}")

        # Show sidebar starting from off-screen left
        self.sidebar.x_offset = -self.sidebar.sidebar_width
        self.sidebar.show(todos, events)

        # Animate in from left
        self._animate_sidebar(-self.sidebar.sidebar_width, 0, 300)

    def _hide_sidebar(self) -> None:
        """Hide the sidebar with animation."""
        if not self._sidebar_visible or not self.sidebar:
            return

        logger.info("Hiding sidebar")
        self._sidebar_visible = False

        # Animate out to left
        self._animate_sidebar(self.sidebar.x_offset, -self.sidebar.sidebar_width, 300)

    def _animate_sidebar(self, start_x: int, target_x: int, duration_ms: int) -> None:
        """Animate sidebar position.

        Args:
            start_x: Starting x offset
            target_x: Target x offset
            duration_ms: Animation duration in milliseconds
        """
        if not self.sidebar:
            return

        # Cancel existing animation
        if self._sidebar_animation_job:
            self.after_cancel(self._sidebar_animation_job)

        start_time = time.time() * 1000

        def animate_frame():
            if not self.sidebar:
                self._sidebar_animation_job = None
                return

            current_time = time.time() * 1000
            elapsed = current_time - start_time

            if elapsed >= duration_ms:
                # Animation complete
                self.sidebar.update_position(target_x)

                # Clean up sidebar if it's now hidden
                if target_x <= -self.sidebar.sidebar_width:
                    self.sidebar.hide()
                    self.sidebar = None

                self._sidebar_animation_job = None
                return

            # Calculate position using ease-out curve
            t = min(1.0, elapsed / duration_ms)
            ease_t = 1 - pow(1 - t, 3)
            current_x = int(start_x + (target_x - start_x) * ease_t)

            self.sidebar.update_position(current_x)

            # Schedule next frame
            self._sidebar_animation_job = self.after(16, animate_frame)

        # Start animation
        animate_frame()

    def _on_exit_button(self) -> None:
        """Handle exit button click from sidebar."""
        logger.info("=" * 60)
        logger.info("EXIT BUTTON CLICKED - Initiating shutdown sequence")
        logger.info("=" * 60)
        self.on_close()

    def _on_volume_change(self, direction: str) -> None:
        """Handle volume change from sidebar.

        Args:
            direction: "up" or "down"
        """
        logger.info(f"Sidebar: Volume {direction} button clicked")

        # Volume change amount (5%)
        volume_step = "5%"

        try:
            # Try PulseAudio first (common on modern Linux systems)
            if direction == "up":
                cmd = ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"+{volume_step}"]
            else:
                cmd = ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"-{volume_step}"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=2.0
            )

            if result.returncode == 0:
                logger.info(f"Volume adjusted using pactl: {direction} by {volume_step}")
                return
            else:
                logger.debug(f"pactl failed (code {result.returncode}), trying amixer...")
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
            logger.debug(f"pactl not available or failed: {e}, trying amixer...")

        # Fallback to ALSA amixer (common on Raspberry Pi)
        try:
            if direction == "up":
                cmd = ["amixer", "sset", "Master", f"{volume_step}+"]
            else:
                cmd = ["amixer", "sset", "Master", f"{volume_step}-"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=2.0
            )

            if result.returncode == 0:
                logger.info(f"Volume adjusted using amixer: {direction} by {volume_step}")

                # Parse output to show current volume level
                output = result.stdout
                if "%" in output:
                    # Extract percentage from output like "[75%]"
                    import re
                    match = re.search(r'\[(\d+)%\]', output)
                    if match:
                        current_volume = match.group(1)
                        logger.info(f"Current volume: {current_volume}%")
            else:
                logger.warning(f"amixer command failed with code {result.returncode}: {result.stderr}")
        except FileNotFoundError:
            logger.error("Neither pactl nor amixer found. Volume control not available on this system.")
        except subprocess.TimeoutExpired:
            logger.error("Volume control command timed out")
        except Exception as e:
            logger.error(f"Failed to adjust volume: {e}", exc_info=True)

    def _animate_swipe_in(self, center_x: int, center_y: int, screen_width: int, sleepiness_level: int) -> None:
        """Animate swipe-in from right when switching to tool view.
        
        Args:
            center_x: Center x coordinate
            center_y: Center y coordinate
            screen_width: Screen width
            sleepiness_level: Current sleepiness level
        """
        # Cancel any existing swipe animation
        if self._swipe_animation_job:
            self.after_cancel(self._swipe_animation_job)
        
        # Clear swipe items
        for item in self._swipe_items:
            try:
                self.content_canvas.delete(item)
            except:
                pass
        self._swipe_items = []
        
        # Create the view content off-screen to the right
        start_x = screen_width + 100  # Start off-screen right
        target_x = center_x  # Target position
        
        # Get canvas dimensions for proper positioning
        self.update_idletasks()
        canvas_height = self.content_canvas.winfo_height()
        if canvas_height <= 1:
            canvas_height = self.winfo_height() or 480
        
        # Create the view based on active_view (off-screen)
        if self._state.active_view == "pomodoro" and self._state.timer_state:
            # Create timer display off-screen - use proper timer y position
            timer_y = int(canvas_height * 0.35)
            self._show_timer_display(start_x, timer_y, screen_width)
            # Collect all items for animation AFTER they're created
            if self.timer_display:
                # Force update to ensure items are created
                self._update_timer_display()
                for display in self.timer_display.work_displays + self.timer_display.break_displays:
                    self._swipe_items.extend(display.segment_items)
                self._swipe_items.extend(self.timer_display.colon_items)
                self._swipe_items.extend(self.timer_display.break_colon_items)
            
            # Also create and animate timer controls
            timer_status = self._state.timer_state.get("status", "paused")
            timer_display_height = (self.timer_display.digit_height * 2) + int(screen_width * 0.05) if self.timer_display else 200
            controls_y = int(canvas_height * 0.35) + timer_display_height + int(screen_width * 0.05)
            self._show_timer_controls(start_x, controls_y, screen_width, timer_status == "paused")
            if self.timer_controls:
                self._swipe_items.extend(self.timer_controls.items)
        elif self._state.active_view == "ideas":
            # Create idea notebook off-screen
            idea_view = self._state.idea_view or {}
            idea_id = idea_view.get("active_idea_id")
            is_active = idea_view.get("is_active", False)
            if idea_id and is_active:
                idea_text = idea_view.get("draft_text", "New idea captured")
                self._show_idea_notification(start_x, int(screen_width * 0.05), idea_text, screen_width)
                if self.idea_notebook:
                    self._swipe_items.extend(self.idea_notebook.items)
        
        # Animate swipe-in with time-based lerp for smoother animation
        animation_duration_ms = 500  # Increased duration for smoother feel (500ms)
        frame_time_ms = 8  # More frequent updates (~120 FPS target, but will adapt to actual frame rate)
        start_time = [time.time() * 1000]  # Start time in milliseconds
        last_x = [start_x]  # Last x position for delta calculation
        
        def animate_frame():
            current_time_ms = time.time() * 1000
            elapsed_ms = current_time_ms - start_time[0]
            
            if elapsed_ms >= animation_duration_ms:
                # Animation complete - ensure final position
                final_delta = target_x - last_x[0]
                if abs(final_delta) > 0.1:
                    for item in self._swipe_items:
                        try:
                            self.content_canvas.move(item, final_delta, 0)
                        except:
                            pass
                
                if self.timer_display:
                    self.timer_display.center_x = target_x
                    # Force final update
                    self._update_timer_display()
                # idea_notebook doesn't need center_x update (it's always centered)
                if self.timer_controls:
                    # Also animate controls if they exist
                    self.timer_controls.center_x = target_x
                self._swipe_animation_job = None
                return
            
            # Normalized progress (0.0 to 1.0)
            t = min(1.0, elapsed_ms / animation_duration_ms)
            
            # Smooth ease-out curve: 1 - (1-t)^3
            # This provides smooth deceleration
            ease_t = 1 - pow(1 - t, 3)
            
            # Lerp current x position
            current_x = start_x + (target_x - start_x) * ease_t
            
            # Calculate delta from last position for smooth movement
            delta_x = current_x - last_x[0]
            
            # Only move if delta is significant (reduces jitter and improves performance)
            if abs(delta_x) > 0.5:
                # Move all items smoothly
                for item in self._swipe_items:
                    try:
                        self.content_canvas.move(item, delta_x, 0)
                    except:
                        pass
                
                # Update display positions
                if self.timer_display:
                    self.timer_display.center_x = current_x
                # idea_notebook doesn't need center_x update (it's always centered)
                if self.timer_controls:
                    self.timer_controls.center_x = current_x
                
                last_x[0] = current_x
            
            # Schedule next frame - use adaptive timing
            # If we're behind, use shorter delay to catch up
            actual_frame_time = time.time() * 1000 - current_time_ms
            if actual_frame_time > frame_time_ms * 2:
                # We're running slow, use shorter delay to catch up
                next_delay = max(4, int(frame_time_ms * 0.5))
            else:
                next_delay = frame_time_ms
            
            self._swipe_animation_job = self.after(next_delay, animate_frame)
        
        # Start animation
        animate_frame()
    
    def _show_timer_display(self, x: int, y: int, screen_width: int) -> None:
        """Show timer display at position.
        
        Args:
            x: Center x coordinate
            y: Top y coordinate
            screen_width: Screen width for responsive sizing
        """
        # Always recreate if screen width changed or doesn't exist
        if (self.timer_display is None or
            (hasattr(self.timer_display, 'screen_width') and self.timer_display.screen_width != screen_width)):
            # Clear old display
            if self.timer_display:
                self.timer_display.clear()
            self.timer_display = TimerDisplay(self.content_canvas, x, y, screen_width)
        else:
            # Update position
            self.timer_display.center_x = x
            self.timer_display.start_y = y
        
        # Update timer values after creating/positioning display
        self._update_timer_display()
    
    def _show_timer_controls(self, x: int, y: int, screen_width: int, is_paused: bool) -> None:
        """Show timer controls at position.
        
        Args:
            x: Center x coordinate
            y: Top y coordinate
            screen_width: Screen width for responsive sizing
            is_paused: Whether timer is currently paused
        """
        if self.timer_controls is None or (
            hasattr(self.timer_controls, 'screen_width') and self.timer_controls.screen_width != screen_width
        ):
            # Clear old controls
            if self.timer_controls:
                self.timer_controls.clear()
            self.timer_controls = TimerControls(
                self.content_canvas, x, y, screen_width,
                on_pause_play=self._handle_pause_play,
                on_end=self._handle_end_click
            )
        else:
            # Update position and state
            self.timer_controls.center_x = x
            self.timer_controls.top_y = y
            self.timer_controls.set_paused(is_paused)
    
    def _handle_pause_play(self) -> None:
        """Handle pause/play button click."""
        timer_state = self._state.timer_state
        if not timer_state:
            return
        
        session_id = timer_state.get("session_id")
        if not session_id:
            return
        
        status = timer_state.get("status", "paused")
        api_url = f"{self._api_base_url}/productivity/pomodoro/{session_id}"
        
        try:
            if status == "running":
                # Pause the timer
                response = self._client.post(f"{api_url}/pause", timeout=CONNECTION_TIMEOUT)
                response.raise_for_status()
                logger.info("Timer paused")
            else:
                # Resume the timer
                response = self._client.post(f"{api_url}/resume", timeout=CONNECTION_TIMEOUT)
                response.raise_for_status()
                logger.info("Timer resumed")
            
            # Refresh UI state will update controls
            self._refresh_ui()
        except Exception as e:
            logger.error(f"Error toggling timer: {e}", exc_info=True)
    
    def _handle_end_click(self) -> None:
        """Handle end button click - show confirmation dialog."""
        # Show confirmation dialog
        self.update_idletasks()
        canvas_width = self.content_canvas.winfo_width()
        canvas_height = self.content_canvas.winfo_height()
        if canvas_width <= 1:
            canvas_width = self.winfo_width() or 800
        if canvas_height <= 1:
            canvas_height = self.winfo_height() or 480
        
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        if self.confirmation_dialog:
            self.confirmation_dialog.clear()
        
        self.confirmation_dialog = ConfirmationDialog(
            self.content_canvas, center_x, center_y, canvas_width,
            on_confirm=self._handle_end_confirm,
            on_cancel=self._handle_end_cancel
        )
    
    def _handle_end_confirm(self) -> None:
        """Handle confirmation to end timer session."""
        timer_state = self._state.timer_state
        if not timer_state:
            return
        
        session_id = timer_state.get("session_id")
        if not session_id:
            return
        
        api_url = f"{self._api_base_url}/productivity/pomodoro/{session_id}/stop"
        
        try:
            response = self._client.post(api_url, timeout=CONNECTION_TIMEOUT)
            response.raise_for_status()
            logger.info("Timer session ended")
            
            # Clear confirmation dialog
            if self.confirmation_dialog:
                self.confirmation_dialog.clear()
                self.confirmation_dialog = None
            
            # Reset interaction time to make Henry happy
            self._last_interaction_time = time.time()
            
            # Refresh UI - will show idle view with happy Henry
            self._refresh_ui()
        except Exception as e:
            logger.error(f"Error ending timer session: {e}", exc_info=True)
            # Clear dialog even on error
            if self.confirmation_dialog:
                self.confirmation_dialog.clear()
                self.confirmation_dialog = None
    
    def _handle_end_cancel(self) -> None:
        """Handle cancellation of end timer session."""
        if self.confirmation_dialog:
            self.confirmation_dialog.clear()
            self.confirmation_dialog = None

    def _handle_idea_close(self) -> None:
        """Handle closing the idea notebook via the close button."""
        logger.info("Closing idea via API")
        if self._client:
            try:
                response = self._client.post(
                    f"{self._api_base_url}/productivity/ideas/close",
                    timeout=5.0
                )
                if response.status_code == 200:
                    logger.info("Idea closed successfully")
                else:
                    logger.warning(f"Failed to close idea: {response.status_code}")
            except Exception as e:
                logger.error(f"Error closing idea: {e}")
        # Force a UI refresh to update the state
        self._refresh_ui()

    def _show_idea_notification(self, x: int, y: int, text: str, screen_width: int) -> None:
        """Show idea notebook view.

        Args:
            x: Center x coordinate (ignored - notebook is centered)
            y: Top y coordinate (ignored - notebook has fixed position)
            text: Idea text
            screen_width: Screen width for responsive sizing
        """
        screen_height = self.content_canvas.winfo_height()
        if screen_height <= 1:
            screen_height = 480  # Fallback

        # Use the full notebook view instead of toast notification
        # Create new notebook if none exists or dimensions changed significantly
        needs_recreate = (
            self.idea_notebook is None or
            abs(self.idea_notebook.screen_width - screen_width) > 5 or
            abs(self.idea_notebook.screen_height - screen_height) > 5
        )
        if needs_recreate:
            self.idea_notebook = IdeaNotebook(self.content_canvas, screen_width, screen_height)
            self.idea_notebook.set_close_callback(self._handle_idea_close)

        # Check if text changed - update if so
        if self.idea_notebook._current_text != text:
            idea_id = self._state.idea_view.get("active_idea_id", "")
            logger.debug(f"Idea text changed, updating notebook: old={self.idea_notebook._current_text[:50] if self.idea_notebook._current_text else 'None'}... new={text[:50]}...")
            self.idea_notebook.show(text, idea_id)
        else:
            logger.debug(f"Idea text unchanged: {text[:50]}...")

        # Keep legacy notification hidden
        if self.idea_notification:
            self.idea_notification.hide()

    def _show_todo_list(self, screen_width: int, screen_height: int) -> None:
        """Show todo list view.

        Args:
            screen_width: Screen width
            screen_height: Screen height
        """
        if self.todo_list is None:
            self.todo_list = TodoList(self.content_canvas, screen_width, screen_height)
            # Set callbacks
            self.todo_list.set_close_callback(self._on_todo_list_close)
            self.todo_list.set_filter_change_callback(self._on_todo_filter_change)
            self.todo_list.set_todo_tap_callback(self._on_todo_tap)
        
        # Fetch todos and categories from backend
        try:
            if self._client:
                # Get filter state
                filter_status = self._state.todo_filter_status
                selected_category_id = self._state.selected_category_id
                
                # Build query params
                params = {}
                if filter_status:
                    params["status"] = filter_status
                if selected_category_id:
                    params["category_id"] = selected_category_id
                
                # Fetch todos
                response = self._client.get(f"{self._api_base_url}/api/todos", params=params)
                todos_data = response.json() if response.status_code == 200 else {"todos": []}
                todos = todos_data.get("todos", [])
                
                # Fetch categories
                cat_response = self._client.get(f"{self._api_base_url}/api/categories")
                categories_data = cat_response.json() if cat_response.status_code == 200 else {"categories": []}
                categories = categories_data.get("categories", [])
                
                # Update todo list
                self.todo_list.show(
                    todos=todos,
                    categories=categories,
                    selected_category_id=selected_category_id,
                    filter_status=filter_status,
                )
        except Exception as e:
            logger.error(f"Failed to fetch todos: {e}")
            # Show empty list
            self.todo_list.show(todos=[], categories=[], selected_category_id=None, filter_status=None)

    def _on_todo_list_close(self) -> None:
        """Handle todo list close button click."""
        logger.info("Todo list closed by user")
        # Request backend to navigate back
        try:
            if self._client:
                self._client.post(f"{self._api_base_url}/conversation/ui/back")
        except Exception as e:
            logger.error(f"Failed to pop view: {e}")

    def _on_todo_filter_change(self, status: Optional[str], category_id: Optional[str]) -> None:
        """Handle todo filter change."""
        logger.info(f"Todo filter changed: status={status}, category={category_id}")
        # Update backend state
        try:
            if self._client:
                data = {}
                if status is not None:
                    data["status"] = status
                if category_id is not None:
                    data["category_id"] = category_id
                self._client.post(f"{self._api_base_url}/conversation/ui/update_todo_filters", json=data)
        except Exception as e:
            logger.error(f"Failed to update filters: {e}")

    def _on_todo_tap(self, todo_id: str) -> None:
        """Handle todo item tap."""
        logger.info(f"Todo tapped: {todo_id}")
        # TODO: Show todo detail view or edit dialog
    
    def _show_calendar(self, screen_width: int, screen_height: int) -> None:
        """Show calendar view.

        Args:
            screen_width: Screen width
            screen_height: Screen height
        """
        if self.calendar_view is None:
            self.calendar_view = CalendarView(self.content_canvas, screen_width, screen_height)
            # Set callbacks
            self.calendar_view.set_close_callback(self._on_calendar_close)
            self.calendar_view.set_view_mode_change_callback(self._on_calendar_view_mode_change)
            self.calendar_view.set_event_tap_callback(self._on_event_tap)
        
        # Fetch events from backend
        try:
            if self._client:
                # Get view mode from state
                view_mode = self._state.calendar_view_mode if hasattr(self._state, 'calendar_view_mode') else "upcoming"
                
                # Fetch events based on view mode
                if view_mode == "today":
                    response = self._client.get(f"{self._api_base_url}/calendar/events/today")
                else:  # upcoming
                    response = self._client.get(f"{self._api_base_url}/calendar/events/upcoming")
                
                events_data = response.json() if response.status_code == 200 else {"events": []}
                events = events_data.get("events", [])
                
                # Update calendar view
                self.calendar_view.show(
                    events=events,
                    view_mode=view_mode,
                    filter_type=None,
                )
        except Exception as e:
            logger.error(f"Failed to fetch calendar events: {e}")
            # Show empty calendar
            self.calendar_view.show(events=[], view_mode="upcoming", filter_type=None)

    def _on_calendar_close(self) -> None:
        """Handle calendar view close button click."""
        logger.info("Calendar closed by user")
        # Request backend to navigate back
        try:
            if self._client:
                self._client.post(f"{self._api_base_url}/conversation/ui/back")
        except Exception as e:
            logger.error(f"Failed to pop view: {e}")

    def _on_calendar_view_mode_change(self, view_mode: str) -> None:
        """Handle calendar view mode change."""
        logger.info(f"Calendar view mode changed: {view_mode}")
        # Update backend state and refresh
        try:
            if self._client:
                self._client.post(
                    f"{self._api_base_url}/conversation/ui/update_calendar_view",
                    json={"view_mode": view_mode}
                )
                # Refresh the calendar view
                canvas_width = self.content_canvas.winfo_width()
                canvas_height = self.content_canvas.winfo_height()
                if canvas_width > 1 and canvas_height > 1:
                    self._show_calendar(canvas_width, canvas_height)
        except Exception as e:
            logger.error(f"Failed to update calendar view mode: {e}")

    def _on_event_tap(self, event_id: str) -> None:
        """Handle event item tap."""
        logger.info(f"Event tapped: {event_id}")
        # TODO: Show event detail view or edit dialog
    
    def _start_animation_loop(self) -> None:
        """Start the animation loop for smiley face."""
        if not self._running:
            return

        # Periodically check canvas size (every 2 seconds = 120 frames at 60 FPS)
        self._animation_frame_count += 1
        if self._animation_frame_count % 120 == 0:
            canvas_width = self.content_canvas.winfo_width()
            canvas_height = self.content_canvas.winfo_height()

            # Check if size changed significantly (more than 5 pixels)
            if (abs(canvas_width - self._last_canvas_width) > 5 or
                abs(canvas_height - self._last_canvas_height) > 5):
                logger.debug(f"Periodic size check: canvas size changed {self._last_canvas_width}x{self._last_canvas_height} -> {canvas_width}x{canvas_height}")
                self._last_canvas_width = canvas_width
                self._last_canvas_height = canvas_height

                # Trigger recenter by clearing and forcing refresh
                if self.smiley_face:
                    for item in getattr(self.smiley_face, 'face_items', []):
                        self.content_canvas.delete(item)
                    self.smiley_face = None

                if self.timer_display:
                    self.timer_display.clear()
                    self.timer_display = None

                # Next refresh will recreate at new center
                if self._connected:
                    self._refresh_ui()

        # Calculate sleepiness level based on time since last interaction
        # Uses configured thresholds from settings
        time_since_interaction = time.time() - self._last_interaction_time
        if time_since_interaction < self._happy_duration:
            sleepiness_level = 0  # Happy
        elif time_since_interaction < self._neutral_duration:
            sleepiness_level = 1  # Neutral
        elif time_since_interaction < self._sleepy_duration:
            sleepiness_level = 2  # Sleepy
        else:
            sleepiness_level = 3  # Very sleepy (asleep)

        # Update smiley face animation if it exists
        if self.smiley_face:
            # Use current time for animation phase
            # Animation speed decreases with sleepiness
            animation_speeds = [0.6, 0.5, 0.3, 0.15]  # Happy, neutral, sleepy, very sleepy
            animation_speed = animation_speeds[min(sleepiness_level, 3)]
            phase = (time.time() * animation_speed) % (2 * math.pi)
            self.smiley_face.update_animation(phase, sleepiness_level)

        # Schedule next frame (16ms = ~60 FPS for smooth animation)
        self._animation_job = self.after(16, self._start_animation_loop)

    def on_close(self) -> None:
        """Handle window close event."""
        logger.info("=" * 60)
        logger.info("SHUTTING DOWN H.E.N.R.Y. GUI")
        logger.info("=" * 60)
        logger.info("on_close() called - initiating shutdown sequence")
        self._running = False

        # Cancel animation jobs
        logger.info("Cancelling animation jobs...")
        if self._animation_job:
            self.after_cancel(self._animation_job)
            self._animation_job = None
        if self._timer_update_job:
            self.after_cancel(self._timer_update_job)
            self._timer_update_job = None
        if self._swipe_animation_job:
            self.after_cancel(self._swipe_animation_job)
            self._swipe_animation_job = None
        if self._sidebar_animation_job:
            self.after_cancel(self._sidebar_animation_job)
            self._sidebar_animation_job = None
        logger.info("Animation jobs cancelled")

        # Stop voice loop if it exists
        if self._voice_loop:
            logger.info("Stopping voice loop...")
            self._voice_loop.stop()
            logger.info("Voice loop stopped")

        # Close HTTP client
        if self._client:
            try:
                logger.info("Closing HTTP client...")
                self._client.close()
                logger.info("HTTP client closed")
            except Exception as e:
                logger.warning(f"Error closing HTTP client: {e}")

        # Destroy window
        logger.info("Destroying GUI window...")
        self.destroy()
        logger.info("GUI SHUTDOWN COMPLETE")
        logger.info("=" * 60)

