"""Idea notebook widget for H.E.N.R.Y. GUI."""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Any, Callable, List, Optional

try:
    import tkinter as tk
except ImportError:
    tk = None

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts import colors

logger = logging.getLogger(__name__)


class IdeaNotebook:
    """Full-screen notebook view for ideas that persists until dismissed."""

    def __init__(self, canvas: tk.Canvas, screen_width: int, screen_height: int):
        """Initialize notebook view.

        Args:
            canvas: Canvas to draw on
            screen_width: Screen width
            screen_height: Screen height
        """
        self.canvas = canvas
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.items: List[int] = []
        self.visible = False
        self._current_text = ""
        self._current_id = ""
        self._on_close_callback: Optional[Callable[[], None]] = None
        self._close_button_id: Optional[int] = None

        # Sizing (responsive to screen)
        self.notebook_width = int(screen_width * 0.9)
        self.notebook_height = int(screen_height * 0.65)
        self.padding = int(screen_width * 0.04)
        self.title_font_size = max(16, int(screen_width * 0.022))
        self.body_font_size = max(12, int(screen_width * 0.016))

    def set_close_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback to invoke when close button is clicked."""
        self._on_close_callback = callback

    def _strip_markdown(self, text: str) -> str:
        """Strip markdown formatting from text for clean display."""
        # Remove bold/italic asterisks: **text**, *text*, __text__, _text_
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # **bold**
        text = re.sub(r'\*(.+?)\*', r'\1', text)  # *italic*
        text = re.sub(r'__(.+?)__', r'\1', text)  # __bold__
        text = re.sub(r'_(.+?)_', r'\1', text)  # _italic_
        # Remove bullet points at start of lines
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        # Remove numbered lists
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        # Remove headers
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        return text.strip()

    def show(self, idea_text: str, idea_id: str = "") -> None:
        """Show notebook with idea text.

        Args:
            idea_text: The idea content to display
            idea_id: Optional idea ID
        """
        self.visible = True
        self._current_text = idea_text
        self._current_id = idea_id
        self._draw()

    def update_text(self, new_text: str) -> None:
        """Update displayed text (for live updates during refinement)."""
        if new_text != self._current_text:
            self._current_text = new_text
            self._draw()

    def _draw(self) -> None:
        """Draw the notebook view."""
        # Clear previous items
        for item in self.items:
            self.canvas.delete(item)
        self.items = []

        if not self.visible:
            return

        # Get current canvas dimensions for proper centering and scaling
        current_width = self.canvas.winfo_width()
        current_height = self.canvas.winfo_height()

        # Use stored dimensions as fallback if canvas not yet rendered
        if current_width <= 1:
            current_width = self.screen_width
        if current_height <= 1:
            current_height = self.screen_height

        # Recalculate sizing based on current dimensions
        notebook_width = int(current_width * 0.9)
        notebook_height = int(current_height * 0.65)
        self.padding = int(current_width * 0.04)
        self.title_font_size = max(16, int(current_width * 0.022))
        self.body_font_size = max(12, int(current_width * 0.016))

        center_x = current_width // 2
        x1 = center_x - notebook_width // 2
        y1 = int(current_height * 0.12)
        x2 = center_x + notebook_width // 2
        y2 = y1 + notebook_height

        # Shadow for depth
        shadow = self.canvas.create_rectangle(
            x1 + 4, y1 + 4, x2 + 4, y2 + 4,
            fill=colors.NOTEBOOK_SHADOW,
            outline=""
        )
        self.items.append(shadow)

        # Main notebook background
        bg = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=colors.NOTEBOOK_BG,
            outline=colors.NOTEBOOK_BORDER,
            width=2
        )
        self.items.append(bg)

        # Lightbulb icon
        icon_size = int(current_width * 0.015)
        icon_x = x1 + self.padding + icon_size
        icon_y = y1 + self.padding + icon_size
        icon = self.canvas.create_oval(
            icon_x - icon_size, icon_y - icon_size,
            icon_x + icon_size, icon_y + icon_size,
            fill=colors.NOTEBOOK_ICON,
            outline=colors.NOTIFICATION_ICON_OUTLINE,
            width=max(1, int(current_width * 0.002))
        )
        self.items.append(icon)

        # Title
        title_x = icon_x + icon_size + 10
        title_y = icon_y
        title = self.canvas.create_text(
            title_x, title_y,
            text="Idea Notebook",
            font=("Segoe UI", self.title_font_size, "bold"),
            fill=colors.NOTEBOOK_TITLE,
            anchor="w"
        )
        self.items.append(title)

        # Close button (X) in top-right corner
        close_btn_size = int(current_width * 0.02)
        close_x = x2 - self.padding - close_btn_size
        close_y = y1 + self.padding + close_btn_size

        # Close button background circle
        close_bg = self.canvas.create_oval(
            close_x - close_btn_size, close_y - close_btn_size,
            close_x + close_btn_size, close_y + close_btn_size,
            fill=colors.NOTEBOOK_BG,
            outline=colors.NOTEBOOK_BORDER,
            width=1,
            tags="close_btn"
        )
        self.items.append(close_bg)

        # X symbol
        x_offset = int(close_btn_size * 0.6)
        close_x1 = self.canvas.create_line(
            close_x - x_offset, close_y - x_offset,
            close_x + x_offset, close_y + x_offset,
            fill=colors.NOTEBOOK_HINT,
            width=2,
            tags="close_btn"
        )
        close_x2 = self.canvas.create_line(
            close_x - x_offset, close_y + x_offset,
            close_x + x_offset, close_y - x_offset,
            fill=colors.NOTEBOOK_HINT,
            width=2,
            tags="close_btn"
        )
        self.items.append(close_x1)
        self.items.append(close_x2)

        # Bind click event to close button
        self.canvas.tag_bind("close_btn", "<Button-1>", self._on_close_click)

        # Divider line
        divider_y = y1 + self.padding + icon_size * 2 + 10
        divider = self.canvas.create_line(
            x1 + self.padding, divider_y,
            x2 - self.padding, divider_y,
            fill=colors.NOTEBOOK_DIVIDER,
            width=1
        )
        self.items.append(divider)

        # Idea text (word-wrapped, full text - no truncation)
        text_y = divider_y + 15
        text_width = notebook_width - (self.padding * 2)

        # Strip markdown formatting for clean display
        display_text = self._strip_markdown(self._current_text)

        text_item = self.canvas.create_text(
            center_x, text_y,
            text=display_text,
            font=("Segoe UI", self.body_font_size),
            fill=colors.NOTEBOOK_TEXT,
            anchor="n",
            width=text_width,
            justify="left"
        )
        self.items.append(text_item)

        # Hint text at bottom
        hint_y = y2 - self.padding
        hint = self.canvas.create_text(
            center_x, hint_y,
            text="Speak to refine, or tap X to close",
            font=("Segoe UI", int(self.body_font_size * 0.85), "italic"),
            fill=colors.NOTEBOOK_HINT,
            anchor="s"
        )
        self.items.append(hint)

    def hide(self) -> None:
        """Hide the notebook view."""
        self.visible = False
        for item in self.items:
            self.canvas.delete(item)
        self.items = []

    def clear(self) -> None:
        """Alias for hide."""
        self.hide()

    def _on_close_click(self, event: Any) -> None:
        """Handle close button click."""
        logger.info("Idea notebook close button clicked")
        self.hide()
        if self._on_close_callback:
            self._on_close_callback()

