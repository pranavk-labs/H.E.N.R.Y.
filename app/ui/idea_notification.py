"""Idea notification widget for H.E.N.R.Y. GUI."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

try:
    import tkinter as tk
except ImportError:
    tk = None

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts import colors


class IdeaNotification:
    """Toast-style notification for idea creation."""
    
    def __init__(self, canvas: tk.Canvas, x: int, y: int, screen_width: int):
        """Initialize idea notification.
        
        Args:
            canvas: Canvas to draw on
            x: Center x coordinate
            y: Top y coordinate
            screen_width: Screen width for percentage-based sizing
        """
        self.canvas = canvas
        self.center_x = x
        self.top_y = y
        self.screen_width = screen_width
        # Use 37.5% of screen width for notification
        self.width = int(screen_width * 0.375)
        self.height = int(screen_width * 0.1)  # 10% of width for height
        self.items = []
        self.alpha = 0.0  # Opacity (0.0 to 1.0)
        self.visible = False
        self._fade_job: Optional[str] = None
    
    def show(self, idea_text: str) -> None:
        """Show notification with idea text.
        
        Args:
            idea_text: Text to display
        """
        self.visible = True
        self.alpha = 0.0
        self._current_text = idea_text
        self._draw(idea_text)
        self._fade_in()
    
    def _draw(self, idea_text: str) -> None:
        """Draw the notification.
        
        Args:
            idea_text: Text to display
        """
        # Clear previous items
        for item in self.items:
            self.canvas.delete(item)
        self.items = []
        
        if not self.visible:
            return
        
        # Truncate text if too long (scale with screen width)
        max_chars = max(30, int(self.screen_width * 0.05))  # ~5% of width in characters
        display_text = idea_text if len(idea_text) <= max_chars else idea_text[:max_chars-3] + "..."
        
        # Calculate position
        x1 = self.center_x - self.width // 2
        y1 = self.top_y
        x2 = self.center_x + self.width // 2
        y2 = self.top_y + self.height
        
        # Background rectangle (opacity handled by fill color)
        bg_alpha = int(240 + (255 - 240) * self.alpha)  # Fade from 240 to 255
        bg_color = f"#{bg_alpha:02x}{bg_alpha:02x}{bg_alpha:02x}"
        
        bg = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=colors.NOTIFICATION_BG,
            outline=colors.NOTIFICATION_OUTLINE,
            width=2
        )
        self.items.append(bg)

        # Lightbulb icon (simple circle) - scale with screen
        icon_size = int(self.screen_width * 0.01875)  # 1.875% of width
        icon_x = x1 + icon_size
        icon_y = y1 + self.height // 2
        icon = self.canvas.create_oval(
            icon_x - icon_size, icon_y - icon_size,
            icon_x + icon_size, icon_y + icon_size,
            fill=colors.NOTIFICATION_ICON_BG,
            outline=colors.NOTIFICATION_ICON_OUTLINE,
            width=max(1, int(self.screen_width * 0.0025))
        )
        self.items.append(icon)
        
        # Text (opacity handled by fill color)
        # Fade from medium grey to light grey
        text_value = int(colors.NOTIFICATION_TEXT_START_RGB +
                        ((colors.NOTIFICATION_TEXT_END_RGB - colors.NOTIFICATION_TEXT_START_RGB) * self.alpha))
        text_color = f"#{text_value:02x}{text_value:02x}{text_value:02x}"
        
        # Scale font size based on screen width
        font_size = max(9, int(self.screen_width * 0.01375))  # ~1.375% of width
        icon_size = int(self.screen_width * 0.01875)  # 1.875% of width
        text_x = x1 + icon_size + 10
        text_y = y1 + self.height // 2
        text_item = self.canvas.create_text(
            text_x, text_y,
            text=display_text,
            fill=text_color,
            font=("Segoe UI", font_size),
            anchor="w",
            width=self.width - icon_size - 20
        )
        self.items.append(text_item)
    
    def _fade_in(self) -> None:
        """Fade in animation."""
        if not self.visible:
            return
        
        self.alpha = min(1.0, self.alpha + 0.1)
        # Redraw with new alpha (simplified - just redraw)
        if hasattr(self, '_current_text'):
            self._draw(self._current_text)
        
        if self.alpha < 1.0:
            self._fade_job = self.canvas.after(30, self._fade_in)
        else:
            # Start auto-dismiss after 5 seconds
            self.canvas.after(5000, self._fade_out)
    
    def _fade_out(self) -> None:
        """Fade out animation."""
        if not self.visible:
            return
        
        self.alpha = max(0.0, self.alpha - 0.1)
        if hasattr(self, '_current_text'):
            self._draw(self._current_text)
        
        if self.alpha > 0.0:
            self._fade_job = self.canvas.after(30, self._fade_out)
        else:
            self.visible = False
            for item in self.items:
                self.canvas.delete(item)
            self.items = []
    
    def hide(self) -> None:
        """Hide notification immediately."""
        self.visible = False
        if self._fade_job:
            self.canvas.after_cancel(self._fade_job)
        for item in self.items:
            self.canvas.delete(item)
        self.items = []

