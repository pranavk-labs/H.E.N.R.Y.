"""Calendar view widget for H.E.N.R.Y. GUI."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import tkinter as tk
except ImportError:
    tk = None

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts import colors

logger = logging.getLogger(__name__)


class CalendarView:
    """Full-screen calendar view with event list and filtering."""

    def __init__(self, canvas: tk.Canvas, screen_width: int, screen_height: int):
        """Initialize calendar view.

        Args:
            canvas: Canvas to draw on
            screen_width: Screen width
            screen_height: Screen height
        """
        self.canvas = canvas
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.visible = False
        self.items: List[int] = []  # Canvas item IDs for cleanup
        self._events: List[Dict[str, Any]] = []
        self._view_mode: str = "upcoming"  # upcoming, today, week, month
        self._filter_type: Optional[str] = None
        self._scroll_offset = 0
        self._max_visible_items = 5  # Max items visible at once
        
        # Callbacks
        self._on_close_callback: Optional[Callable[[], None]] = None
        self._on_event_tap_callback: Optional[Callable[[str], None]] = None
        self._on_view_mode_change_callback: Optional[Callable[[str], None]] = None
        
        # UI sizing (responsive to screen)
        self.padding = int(screen_width * 0.025)
        self.header_height = int(screen_height * 0.10)
        self.view_bar_height = int(screen_height * 0.08)
        self.item_height = 70  # Min touch target for events
        self.title_font_size = max(20, int(screen_width * 0.025))
        self.item_font_size = max(18, int(screen_width * 0.0225))
        self.meta_font_size = max(14, int(screen_width * 0.0175))
        
        # Interaction tracking
        self._close_button_rect: Optional[tuple] = None
        self._view_mode_tab_rects: Dict[str, tuple] = {}
        self._event_item_rects: Dict[str, tuple] = {}

    def set_close_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback to invoke when close button is clicked."""
        self._on_close_callback = callback

    def set_event_tap_callback(self, callback: Callable[[str], None]) -> None:
        """Set the callback to invoke when an event is tapped."""
        self._on_event_tap_callback = callback

    def set_view_mode_change_callback(self, callback: Callable[[str], None]) -> None:
        """Set the callback to invoke when view mode changes."""
        self._on_view_mode_change_callback = callback

    def show(
        self,
        events: List[Dict[str, Any]],
        view_mode: str = "upcoming",
        filter_type: Optional[str] = None,
    ) -> None:
        """Show calendar view with events.

        Args:
            events: List of event dicts
            view_mode: View mode (upcoming, today, week, month)
            filter_type: Filter by event type
        """
        self.visible = True
        self._events = events
        self._view_mode = view_mode
        self._filter_type = filter_type
        self._scroll_offset = 0
        self._draw()

    def update_data(self, events: List[Dict[str, Any]]) -> None:
        """Update event data."""
        self._events = events
        if self.visible:
            self._draw()

    def hide(self) -> None:
        """Hide the calendar view."""
        self.visible = False
        for item in self.items:
            self.canvas.delete(item)
        self.items = []
        self._events = []
        self._scroll_offset = 0

    def _draw(self) -> None:
        """Draw the calendar view."""
        # Clear previous items
        for item in self.items:
            self.canvas.delete(item)
        self.items = []

        if not self.visible:
            return

        # Get current canvas dimensions
        current_width = self.canvas.winfo_width()
        current_height = self.canvas.winfo_height()

        # Use stored dimensions as fallback if canvas not yet rendered
        if current_width <= 1:
            current_width = self.screen_width
        if current_height <= 1:
            current_height = self.screen_height

        # Background (full canvas)
        bg = self.canvas.create_rectangle(
            0, 0, current_width, current_height,
            fill=colors.MAIN_BG,
            outline=""
        )
        self.items.append(bg)

        # Draw header
        self._draw_header(current_width)

        # Draw view mode bar
        view_bar_y = self.header_height
        self._draw_view_mode_bar(current_width, view_bar_y)

        # Draw event list
        list_y = self.header_height + self.view_bar_height
        list_height = current_height - list_y
        self._draw_event_items(current_width, list_y, list_height)

    def _draw_header(self, width: int) -> None:
        """Draw the header with title and close button."""
        # Header background
        header_bg = self.canvas.create_rectangle(
            0, 0, width, self.header_height,
            fill=colors.DIALOG_BG,
            outline=""
        )
        self.items.append(header_bg)
        
        header_line = self.canvas.create_line(
            0, self.header_height, width, self.header_height,
            fill=colors.OUTLINE_PRIMARY,
            width=2
        )
        self.items.append(header_line)

        # Title
        title = self.canvas.create_text(
            self.padding,
            self.header_height // 2,
            text="📅 Calendar",
            font=("Segoe UI", self.title_font_size, "bold"),
            fill=colors.TEXT_PRIMARY,
            anchor="w"
        )
        self.items.append(title)

        # Close button (X) in top-right corner
        close_size = int(self.header_height * 0.3)
        close_x = width - self.padding - close_size
        close_y = (self.header_height - close_size) // 2

        # Close button circle
        close_bg = self.canvas.create_oval(
            close_x, close_y, close_x + close_size, close_y + close_size,
            fill=colors.BUTTON_BG,
            outline=colors.OUTLINE_PRIMARY,
            width=2,
            tags="close_btn"
        )
        self.items.append(close_bg)

        # X symbol
        x_offset = int(close_size * 0.3)
        center_x = close_x + close_size // 2
        center_y = close_y + close_size // 2
        close_x1 = self.canvas.create_line(
            center_x - x_offset, center_y - x_offset,
            center_x + x_offset, center_y + x_offset,
            fill=colors.TEXT_PRIMARY,
            width=3,
            tags="close_btn"
        )
        close_x2 = self.canvas.create_line(
            center_x - x_offset, center_y + x_offset,
            center_x + x_offset, center_y - x_offset,
            fill=colors.TEXT_PRIMARY,
            width=3,
            tags="close_btn"
        )
        self.items.append(close_x1)
        self.items.append(close_x2)

        # Bind click event to close button
        self.canvas.tag_bind("close_btn", "<Button-1>", self._on_close_click)

        # Store close button rect for hit testing
        self._close_button_rect = (close_x, close_y, close_x + close_size, close_y + close_size)

    def _draw_view_mode_bar(self, width: int, y: int) -> None:
        """Draw the view mode bar with tabs."""
        # View mode bar background
        view_bg = self.canvas.create_rectangle(
            0, y, width, y + self.view_bar_height,
            fill=colors.DIALOG_BG,
            outline=""
        )
        self.items.append(view_bg)
        
        view_line = self.canvas.create_line(
            0, y + self.view_bar_height, width, y + self.view_bar_height,
            fill=colors.OUTLINE_PRIMARY,
            width=1
        )
        self.items.append(view_line)

        # View mode tabs
        tab_width = 100
        tab_height = 40
        tab_y = y + (self.view_bar_height - tab_height) // 2
        tab_x = self.padding

        view_modes = [
            ("upcoming", "Upcoming"),
            ("today", "Today"),
        ]

        for mode_id, mode_label in view_modes:
            if tab_x + tab_width > width - self.padding:
                break

            is_selected = self._view_mode == mode_id
            tab_color = colors.BUTTON_CONFIRM if is_selected else colors.BUTTON_BG

            tab = self.canvas.create_rectangle(
                tab_x, tab_y, tab_x + tab_width, tab_y + tab_height,
                fill=tab_color,
                outline=colors.OUTLINE_PRIMARY,
                width=2,
                tags=f"view_{mode_id}"
            )
            self.items.append(tab)

            tab_text = self.canvas.create_text(
                tab_x + tab_width // 2,
                tab_y + tab_height // 2,
                text=mode_label,
                font=("Segoe UI", self.meta_font_size),
                fill=colors.TEXT_PRIMARY,
                tags=f"view_{mode_id}"
            )
            self.items.append(tab_text)

            # Bind click event
            self.canvas.tag_bind(
                f"view_{mode_id}", 
                "<Button-1>", 
                lambda e, mid=mode_id: self._on_view_mode_click(mid)
            )
            self._view_mode_tab_rects[mode_id] = (tab_x, tab_y, tab_x + tab_width, tab_y + tab_height)

            tab_x += tab_width + 10

    def _draw_event_items(self, width: int, y: int, height: int) -> None:
        """Draw the list of event items."""
        if not self._events:
            # No events message
            no_events = self.canvas.create_text(
                width // 2,
                y + height // 2,
                text="No events scheduled",
                font=("Segoe UI", self.item_font_size),
                fill=colors.TEXT_SECONDARY
            )
            self.items.append(no_events)
            return

        # Calculate visible range based on scroll
        start_idx = max(0, self._scroll_offset)
        end_idx = min(len(self._events), start_idx + self._max_visible_items)

        # Draw visible events
        item_y = y + self.padding
        self._event_item_rects = {}

        for i in range(start_idx, end_idx):
            event = self._events[i]
            self._draw_event_item(event, width, item_y)
            item_y += self.item_height + 5

    def _draw_event_item(self, event: Dict[str, Any], width: int, y: int) -> None:
        """Draw a single event item."""
        item_width = width - (self.padding * 2)
        x1 = self.padding
        x2 = x1 + item_width
        y2 = y + self.item_height

        # Background
        event_type = event.get('event_type', 'event')
        type_colors = {
            'meeting': '#4488ff',
            'task': '#ff8844',
            'reminder': '#88ff44',
            'event': '#8844ff',
        }
        type_color = type_colors.get(event_type, '#8844ff')
        
        item_bg = self.canvas.create_rectangle(
            x1, y, x2, y2,
            fill=colors.DIALOG_BG,
            outline=colors.OUTLINE_PRIMARY,
            width=2,
            tags=f"event_{event.get('id', '')}"
        )
        self.items.append(item_bg)

        # Type indicator (colored bar on left)
        type_bar = self.canvas.create_rectangle(
            x1, y, x1 + 8, y2,
            fill=type_color,
            outline="",
            tags=f"event_{event.get('id', '')}"
        )
        self.items.append(type_bar)

        # Title
        title = event.get('title', 'Untitled Event')
        title_text = self.canvas.create_text(
            x1 + 15,
            y + 12,
            text=title[:35],
            font=("Segoe UI", self.item_font_size, "bold"),
            fill=colors.TEXT_PRIMARY,
            anchor="nw",
            tags=f"event_{event.get('id', '')}"
        )
        self.items.append(title_text)

        # Time and location row
        time_y = y + 35
        meta_x = x1 + 15

        # Start time
        start_time = event.get('start_time', '')
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                time_str = start_dt.strftime('%I:%M %p')
                date_str = start_dt.strftime('%b %d')
                
                time_text = self.canvas.create_text(
                    meta_x,
                    time_y,
                    text=f"🕒 {time_str}",
                    font=("Segoe UI", self.meta_font_size),
                    fill=colors.TEXT_SECONDARY,
                    anchor="w",
                    tags=f"event_{event.get('id', '')}"
                )
                self.items.append(time_text)
                
                # Date
                date_text = self.canvas.create_text(
                    meta_x + 100,
                    time_y,
                    text=date_str,
                    font=("Segoe UI", self.meta_font_size),
                    fill=colors.TEXT_SECONDARY,
                    anchor="w",
                    tags=f"event_{event.get('id', '')}"
                )
                self.items.append(date_text)
            except (ValueError, TypeError):
                pass

        # Location (if set)
        location = event.get('location', '')
        if location:
            location_text = self.canvas.create_text(
                x1 + 15,
                y + 52,
                text=f"📍 {location[:30]}",
                font=("Segoe UI", self.meta_font_size),
                fill=colors.TEXT_SECONDARY,
                anchor="w",
                tags=f"event_{event.get('id', '')}"
            )
            self.items.append(location_text)

        # Event type badge (on the right)
        type_labels = {
            'event': 'Event',
            'meeting': 'Meeting',
            'task': 'Task',
            'reminder': 'Reminder',
        }
        type_label = type_labels.get(event_type, event_type)
        type_text = self.canvas.create_text(
            x2 - 10,
            y + 12,
            text=type_label,
            font=("Segoe UI", self.meta_font_size),
            fill=colors.TEXT_SECONDARY,
            anchor="ne",
            tags=f"event_{event.get('id', '')}"
        )
        self.items.append(type_text)

        # Bind click event
        event_id = event.get('id', '')
        self.canvas.tag_bind(
            f"event_{event_id}", 
            "<Button-1>", 
            lambda e, eid=event_id: self._on_event_click(eid)
        )
        self._event_item_rects[event_id] = (x1, y, x2, y2)

    def _on_close_click(self, event: Any) -> None:
        """Handle close button click."""
        logger.info("Calendar view close button clicked")
        if self._on_close_callback:
            self._on_close_callback()

    def _on_view_mode_click(self, mode: str) -> None:
        """Handle view mode tab click."""
        logger.info(f"View mode clicked: {mode}")
        self._view_mode = mode
        if self._on_view_mode_change_callback:
            self._on_view_mode_change_callback(mode)

    def _on_event_click(self, event_id: str) -> None:
        """Handle event item click."""
        logger.info(f"Event clicked: {event_id}")
        if self._on_event_tap_callback:
            self._on_event_tap_callback(event_id)

    def handle_touch(self, pos: tuple[int, int]) -> bool:
        """Handle touch/click event (for compatibility).
        
        Args:
            pos: Touch position (x, y)
            
        Returns:
            True if event was handled
        """
        # tkinter handles clicks via bindings, so this is just for compatibility
        return self.visible


__all__ = ["CalendarView"]


