"""Timer controls widget for H.E.N.R.Y. pomodoro timer."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

try:
    import tkinter as tk
except ImportError:
    tk = None

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts import colors


class TimerControls:
    """Touch-friendly controls for timer (pause/play and end buttons)."""
    
    def __init__(self, canvas: tk.Canvas, x: int, y: int, screen_width: int, 
                 on_pause_play: Callable, on_end: Callable):
        """Initialize timer controls.
        
        Args:
            canvas: Canvas to draw on
            x: Center x coordinate
            y: Top y coordinate
            screen_width: Screen width for responsive sizing
            on_pause_play: Callback for pause/play button click
            on_end: Callback for end button click
        """
        self.canvas = canvas
        self.center_x = x
        self.top_y = y
        self.screen_width = screen_width
        self.on_pause_play = on_pause_play
        self.on_end = on_end
        self.items = []
        self.pause_play_rect = None
        self.end_rect = None
        self.is_paused = False
        
        # Button sizing - touch-friendly
        self.button_height = max(60, int(screen_width * 0.08))  # 8% of width, min 60px
        self.button_width = int(screen_width * 0.15)  # 15% of width
        self.button_spacing = int(screen_width * 0.03)  # 3% spacing
        
        self._draw()
    
    def _draw(self) -> None:
        """Draw the control buttons."""
        # Clear previous items
        for item in self.items:
            self.canvas.delete(item)
        self.items = []
        
        # Calculate button positions (centered horizontally)
        total_width = (self.button_width * 2) + self.button_spacing
        start_x = self.center_x - (total_width // 2)
        
        # Pause/Play button (left)
        pause_play_x1 = start_x
        pause_play_y1 = self.top_y
        pause_play_x2 = start_x + self.button_width
        pause_play_y2 = self.top_y + self.button_height

        self.pause_play_rect = (pause_play_x1, pause_play_y1, pause_play_x2, pause_play_y2)

        # Draw button shadow for depth
        shadow_offset = 3
        pause_play_shadow = self.canvas.create_rectangle(
            pause_play_x1 + shadow_offset, pause_play_y1 + shadow_offset,
            pause_play_x2 + shadow_offset, pause_play_y2 + shadow_offset,
            fill="#000000",
            outline="",
            width=0
        )
        self.items.append(pause_play_shadow)

        # Draw button background
        bg_color = colors.BUTTON_PAUSE if not self.is_paused else colors.BUTTON_PLAY
        pause_play_bg = self.canvas.create_rectangle(
            pause_play_x1, pause_play_y1, pause_play_x2, pause_play_y2,
            fill=bg_color,
            outline=colors.BUTTON_OUTLINE,
            width=3
        )
        self.items.append(pause_play_bg)

        # Draw pause/play icon (simple text for now)
        icon_text = "⏸" if not self.is_paused else "▶"
        font_size = max(20, int(self.screen_width * 0.03))
        pause_play_text = self.canvas.create_text(
            (pause_play_x1 + pause_play_x2) // 2,
            (pause_play_y1 + pause_play_y2) // 2,
            text=icon_text,
            font=("Arial", font_size, "bold"),
            fill="white"
        )
        self.items.append(pause_play_text)
        
        # End button (right)
        end_x1 = start_x + self.button_width + self.button_spacing
        end_y1 = self.top_y
        end_x2 = end_x1 + self.button_width
        end_y2 = self.top_y + self.button_height

        self.end_rect = (end_x1, end_y1, end_x2, end_y2)

        # Draw button shadow for depth
        end_shadow = self.canvas.create_rectangle(
            end_x1 + shadow_offset, end_y1 + shadow_offset,
            end_x2 + shadow_offset, end_y2 + shadow_offset,
            fill="#000000",
            outline="",
            width=0
        )
        self.items.append(end_shadow)

        # Draw button background
        end_bg = self.canvas.create_rectangle(
            end_x1, end_y1, end_x2, end_y2,
            fill=colors.BUTTON_END,
            outline=colors.BUTTON_OUTLINE,
            width=3
        )
        self.items.append(end_bg)

        # Draw end icon/text
        end_text = self.canvas.create_text(
            (end_x1 + end_x2) // 2,
            (end_y1 + end_y2) // 2,
            text="End",
            font=("Arial", max(16, int(self.screen_width * 0.025)), "bold"),
            fill="white"
        )
        self.items.append(end_text)
    
    def handle_click(self, x: int, y: int) -> bool:
        """Handle click event. Returns True if click was handled."""
        if not self.pause_play_rect or not self.end_rect:
            return False
        
        px1, py1, px2, py2 = self.pause_play_rect
        ex1, ey1, ex2, ey2 = self.end_rect
        
        if px1 <= x <= px2 and py1 <= y <= py2:
            # Pause/Play button clicked
            self.on_pause_play()
            return True
        elif ex1 <= x <= ex2 and ey1 <= y <= ey2:
            # End button clicked
            self.on_end()
            return True
        
        return False
    
    def set_paused(self, is_paused: bool) -> None:
        """Update paused state and redraw."""
        if self.is_paused != is_paused:
            self.is_paused = is_paused
            self._draw()
    
    def clear(self) -> None:
        """Clear the controls."""
        for item in self.items:
            self.canvas.delete(item)
        self.items = []
        self.pause_play_rect = None
        self.end_rect = None

