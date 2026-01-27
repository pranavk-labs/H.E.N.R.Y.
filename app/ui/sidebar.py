"""Sidebar widget for H.E.N.R.Y. GUI - shows quick glance info and controls."""

from __future__ import annotations

import logging
import sys
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


class Sidebar:
    """Left sidebar overlay - takes up ~25% of screen with todos, calendar, and controls."""

    def __init__(
        self,
        canvas: tk.Canvas,
        screen_width: int,
        screen_height: int,
        on_close: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
        on_volume_change: Optional[Callable[[float], None]] = None,
    ):
        """Initialize sidebar.

        Args:
            canvas: Canvas to draw on
            screen_width: Screen width
            screen_height: Screen height
            on_close: Callback when sidebar is closed
            on_exit: Callback when exit button is clicked
            on_volume_change: Callback when volume slider is changed
        """
        self.canvas = canvas
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.visible = False
        self.items: List[int] = []  # Canvas item IDs for cleanup

        # Callbacks
        self._on_close_callback = on_close
        self._on_exit_callback = on_exit
        self._on_volume_change_callback = on_volume_change

        # Sidebar dimensions - 25% of screen width
        self.sidebar_width = int(screen_width * 0.25)
        self.x_offset = 0  # Left edge position (for animation)

        # UI sizing
        self.padding = int(self.sidebar_width * 0.08)
        self.section_spacing = int(screen_height * 0.02)
        self.font_size_large = max(14, int(self.sidebar_width * 0.06))
        self.font_size_medium = max(12, int(self.sidebar_width * 0.05))
        self.font_size_small = max(10, int(self.sidebar_width * 0.04))

        # Section heights (3 rows)
        header_height = int(screen_height * 0.06)
        self.todo_section_height = int(screen_height * 0.35)
        self.calendar_section_height = int(screen_height * 0.35)
        self.controls_section_height = screen_height - (
            header_height + self.todo_section_height +
            self.calendar_section_height + self.section_spacing * 3
        )

        # Data
        self._todos: List[Dict[str, Any]] = []
        self._events: List[Dict[str, Any]] = []

        # Interaction tracking
        self._close_button_rect: Optional[tuple] = None
        self._exit_button_rect: Optional[tuple] = None
        self._volume_up_rect: Optional[tuple] = None
        self._volume_down_rect: Optional[tuple] = None

    def show(
        self,
        todos: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
    ) -> None:
        """Show sidebar with data.

        Args:
            todos: List of todo items (will show up to 10 ordered by due date)
            events: List of calendar events (will show first 3)
        """
        self.visible = True
        self._todos = todos[:10]  # Max 10 items
        self._events = events[:3]  # Max 3 items
        self._draw()

    def hide(self) -> None:
        """Hide the sidebar and clean up canvas items."""
        self.visible = False
        self._clear()

    def _clear(self) -> None:
        """Clear all canvas items."""
        for item in self.items:
            try:
                self.canvas.delete(item)
            except Exception:
                pass
        self.items = []
        self._close_button_rect = None
        self._exit_button_rect = None
        self._volume_up_rect = None
        self._volume_down_rect = None

    def _draw(self) -> None:
        """Draw the complete sidebar."""
        self._clear()

        # Background panel
        bg_rect = self.canvas.create_rectangle(
            self.x_offset,
            0,
            self.x_offset + self.sidebar_width,
            self.screen_height,
            fill=colors.FRAME_BG,
            outline=colors.TEXT_SECONDARY,
            width=2,
        )
        self.items.append(bg_rect)

        # Header with close button
        current_y = self._draw_header()

        # Section 1: Todo list preview
        current_y = self._draw_todo_section(current_y)

        # Section 2: Calendar preview
        current_y = self._draw_calendar_section(current_y)

        # Section 3: Controls (volume + exit)
        self._draw_controls_section(current_y)

    def _draw_header(self) -> int:
        """Draw header with close button.

        Returns:
            Y position after header
        """
        header_height = int(self.screen_height * 0.06)

        # Header background
        header_bg = self.canvas.create_rectangle(
            self.x_offset,
            0,
            self.x_offset + self.sidebar_width,
            header_height,
            fill=colors.CANVAS_BG,
            outline="",
        )
        self.items.append(header_bg)

        # Close button (X) on right side
        close_x = self.x_offset + self.sidebar_width - self.padding - 20
        close_y = header_height // 2
        close_size = 15

        close_bg = self.canvas.create_oval(
            close_x - close_size,
            close_y - close_size,
            close_x + close_size,
            close_y + close_size,
            fill=colors.BUTTON_BG,
            outline="",
        )
        self.items.append(close_bg)

        # X icon
        x_offset = 6
        x_line1 = self.canvas.create_line(
            close_x - x_offset,
            close_y - x_offset,
            close_x + x_offset,
            close_y + x_offset,
            fill=colors.TEXT_PRIMARY,
            width=2,
        )
        x_line2 = self.canvas.create_line(
            close_x - x_offset,
            close_y + x_offset,
            close_x + x_offset,
            close_y - x_offset,
            fill=colors.TEXT_PRIMARY,
            width=2,
        )
        self.items.extend([x_line1, x_line2])

        # Store close button rect for hit testing
        self._close_button_rect = (
            close_x - close_size,
            close_y - close_size,
            close_x + close_size,
            close_y + close_size,
        )

        return header_height

    def _draw_todo_section(self, start_y: int) -> int:
        """Draw todo list preview section.

        Args:
            start_y: Y position to start drawing

        Returns:
            Y position after section
        """
        section_y = start_y + self.section_spacing

        # Section header
        header = self.canvas.create_text(
            self.x_offset + self.padding,
            section_y,
            text="To-Do",
            font=("Segoe UI", self.font_size_large, "bold"),
            fill=colors.TEXT_PRIMARY,
            anchor="nw",
        )
        self.items.append(header)

        current_y = section_y + self.font_size_large + self.padding // 2

        # Draw todo items (up to 10)
        if not self._todos:
            # No todos
            no_todos = self.canvas.create_text(
                self.x_offset + self.padding,
                current_y,
                text="No tasks",
                font=("Segoe UI", self.font_size_small, "italic"),
                fill=colors.TEXT_SECONDARY,
                anchor="nw",
            )
            self.items.append(no_todos)
            current_y += self.font_size_small + self.padding
        else:
            # Calculate item height based on number of todos (fit up to 10)
            item_height = max(int(self.screen_height * 0.025), self.todo_section_height // 11)  # 2.5% of screen height min
            for todo in self._todos[:10]:
                title = todo.get("title", "Untitled")
                status = todo.get("status", "todo")
                due_date = todo.get("due_date")

                # Truncate long titles
                if len(title) > 20:
                    title = title[:17] + "..."

                # Add due date indicator if available
                if due_date:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                        date_str = dt.strftime("%m/%d")
                        title = f"{date_str} {title}"
                    except Exception:
                        pass

                # Checkbox indicator
                checkbox_x = self.x_offset + self.padding
                checkbox_y = current_y + item_height // 2
                checkbox_size = max(4, int(self.sidebar_width * 0.03))  # 3% of sidebar width, min 4px

                checkbox_color = colors.SUCCESS if status == "completed" else colors.TEXT_SECONDARY
                checkbox = self.canvas.create_rectangle(
                    checkbox_x,
                    checkbox_y - checkbox_size // 2,
                    checkbox_x + checkbox_size,
                    checkbox_y + checkbox_size // 2,
                    fill=checkbox_color,
                    outline=colors.TEXT_SECONDARY,
                    width=1,
                )
                self.items.append(checkbox)

                # Title
                text_x = checkbox_x + checkbox_size + 8
                todo_text = self.canvas.create_text(
                    text_x,
                    checkbox_y,
                    text=title,
                    font=("Segoe UI", self.font_size_small),
                    fill=colors.TEXT_SECONDARY if status == "completed" else colors.TEXT_PRIMARY,
                    anchor="w",
                )
                self.items.append(todo_text)

                current_y += item_height

        return section_y + self.todo_section_height

    def _draw_calendar_section(self, start_y: int) -> int:
        """Draw calendar preview section.

        Args:
            start_y: Y position to start drawing

        Returns:
            Y position after section
        """
        section_y = start_y + self.section_spacing

        # Section header
        header = self.canvas.create_text(
            self.x_offset + self.padding,
            section_y,
            text="Today",
            font=("Segoe UI", self.font_size_large, "bold"),
            fill=colors.TEXT_PRIMARY,
            anchor="nw",
        )
        self.items.append(header)

        current_y = section_y + self.font_size_large + self.padding // 2

        # Draw event items (max 3)
        if not self._events:
            # No events
            no_events = self.canvas.create_text(
                self.x_offset + self.padding,
                current_y,
                text="No events",
                font=("Segoe UI", self.font_size_small, "italic"),
                fill=colors.TEXT_SECONDARY,
                anchor="nw",
            )
            self.items.append(no_events)
            current_y += self.font_size_small + self.padding
        else:
            item_height = self.calendar_section_height // 4
            for event in self._events[:3]:
                title = event.get("title", "Untitled")
                start_time = event.get("start_time", "")

                # Truncate long titles
                if len(title) > 18:
                    title = title[:15] + "..."

                # Time indicator (dot)
                dot_x = self.x_offset + self.padding
                dot_y = current_y + item_height // 2
                dot_size = max(3, int(self.sidebar_width * 0.02))  # 2% of sidebar width, min 3px

                dot = self.canvas.create_oval(
                    dot_x,
                    dot_y - dot_size,
                    dot_x + dot_size * 2,
                    dot_y + dot_size,
                    fill=colors.ACCENT,
                    outline="",
                )
                self.items.append(dot)

                # Title and time
                text_x = dot_x + dot_size * 2 + 8

                # Parse time if available
                time_str = ""
                if start_time:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        time_str = dt.strftime("%I:%M %p")
                    except Exception:
                        time_str = ""

                display_text = f"{time_str} {title}" if time_str else title
                event_text = self.canvas.create_text(
                    text_x,
                    dot_y,
                    text=display_text,
                    font=("Segoe UI", self.font_size_small),
                    fill=colors.TEXT_PRIMARY,
                    anchor="w",
                )
                self.items.append(event_text)

                current_y += item_height

        return section_y + self.calendar_section_height

    def _draw_controls_section(self, start_y: int) -> None:
        """Draw controls section (volume buttons + exit).

        Args:
            start_y: Y position to start drawing
        """
        section_y = start_y + self.section_spacing

        # Three buttons in a row: Volume Down, Volume Up, Exit
        button_height = max(int(self.screen_height * 0.08), 40)  # 8% of screen height, min 40px
        button_spacing = self.padding // 2
        total_width = self.sidebar_width - (self.padding * 2)
        button_width = (total_width - (button_spacing * 2)) // 3

        button_y = self.screen_height - self.padding - button_height

        # Volume Down button (-)
        vol_down_x1 = self.x_offset + self.padding
        vol_down_x2 = vol_down_x1 + button_width

        vol_down_bg = self.canvas.create_rectangle(
            vol_down_x1,
            button_y,
            vol_down_x2,
            button_y + button_height,
            fill=colors.BUTTON_BG,
            outline="",
        )
        self.items.append(vol_down_bg)

        vol_down_text = self.canvas.create_text(
            (vol_down_x1 + vol_down_x2) // 2,
            button_y + button_height // 2,
            text="🔉",
            font=("Segoe UI", self.font_size_large * 2),
            fill=colors.TEXT_PRIMARY,
            anchor="center",
        )
        self.items.append(vol_down_text)

        self._volume_down_rect = (vol_down_x1, button_y, vol_down_x2, button_y + button_height)

        # Volume Up button (+)
        vol_up_x1 = vol_down_x2 + button_spacing
        vol_up_x2 = vol_up_x1 + button_width

        vol_up_bg = self.canvas.create_rectangle(
            vol_up_x1,
            button_y,
            vol_up_x2,
            button_y + button_height,
            fill=colors.BUTTON_BG,
            outline="",
        )
        self.items.append(vol_up_bg)

        vol_up_text = self.canvas.create_text(
            (vol_up_x1 + vol_up_x2) // 2,
            button_y + button_height // 2,
            text="🔊",
            font=("Segoe UI", self.font_size_large * 2),
            fill=colors.TEXT_PRIMARY,
            anchor="center",
        )
        self.items.append(vol_up_text)

        self._volume_up_rect = (vol_up_x1, button_y, vol_up_x2, button_y + button_height)

        # Exit button
        exit_x1 = vol_up_x2 + button_spacing
        exit_x2 = self.x_offset + self.sidebar_width - self.padding

        exit_bg = self.canvas.create_rectangle(
            exit_x1,
            button_y,
            exit_x2,
            button_y + button_height,
            fill=colors.STATUS_DISCONNECTED,
            outline="",
        )
        self.items.append(exit_bg)

        exit_text = self.canvas.create_text(
            (exit_x1 + exit_x2) // 2,
            button_y + button_height // 2,
            text="⏻",
            font=("Segoe UI", self.font_size_large * 2),
            fill=colors.TEXT_PRIMARY,
            anchor="center",
        )
        self.items.append(exit_text)

        self._exit_button_rect = (exit_x1, button_y, exit_x2, button_y + button_height)

    def handle_touch(self, pos: tuple) -> bool:
        """Handle touch/click events.

        Args:
            pos: (x, y) touch position

        Returns:
            True if event was handled
        """
        x, y = pos

        # Check close button
        if self._close_button_rect:
            x1, y1, x2, y2 = self._close_button_rect
            if x1 <= x <= x2 and y1 <= y <= y2:
                logger.info("Sidebar close button clicked")
                if self._on_close_callback:
                    self._on_close_callback()
                return True

        # Check exit button
        if self._exit_button_rect:
            x1, y1, x2, y2 = self._exit_button_rect
            if x1 <= x <= x2 and y1 <= y <= y2:
                logger.info("=" * 50)
                logger.info("EXIT BUTTON CLICKED IN SIDEBAR")
                logger.info(f"Touch coordinates: ({x}, {y})")
                logger.info(f"Button bounds: ({x1}, {y1}) to ({x2}, {y2})")
                logger.info("=" * 50)
                if self._on_exit_callback:
                    logger.info("Calling exit callback...")
                    self._on_exit_callback()
                else:
                    logger.warning("Exit callback is None!")
                return True

        # Check volume up button
        if self._volume_up_rect:
            x1, y1, x2, y2 = self._volume_up_rect
            if x1 <= x <= x2 and y1 <= y <= y2:
                logger.info("Volume UP button clicked")
                logger.debug(f"Touch coords: ({x}, {y}), Button bounds: ({x1}, {y1}) to ({x2}, {y2})")
                if self._on_volume_change_callback:
                    self._on_volume_change_callback("up")
                else:
                    logger.warning("Volume change callback is None!")
                return True

        # Check volume down button
        if self._volume_down_rect:
            x1, y1, x2, y2 = self._volume_down_rect
            if x1 <= x <= x2 and y1 <= y <= y2:
                logger.info("Volume DOWN button clicked")
                logger.debug(f"Touch coords: ({x}, {y}), Button bounds: ({x1}, {y1}) to ({x2}, {y2})")
                if self._on_volume_change_callback:
                    self._on_volume_change_callback("down")
                else:
                    logger.warning("Volume change callback is None!")
                return True

        # Check if touch is within sidebar bounds (to prevent closing on sidebar touch)
        if 0 <= x <= self.sidebar_width:
            return True

        return False

    def update_position(self, x_offset: int) -> None:
        """Update sidebar x position (for animation).

        Args:
            x_offset: New x offset (0 = fully visible, negative = hidden to left)
        """
        delta_x = x_offset - self.x_offset
        self.x_offset = x_offset

        # Move all items by delta
        for item in self.items:
            try:
                self.canvas.move(item, delta_x, 0)
            except Exception:
                pass
