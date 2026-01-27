"""Timer display widget for H.E.N.R.Y. pomodoro timer."""

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

from app.ui.seven_segment import SevenSegmentDisplay
from scripts import colors


class TimerDisplay:
    """Pomodoro timer display with 8-segment displays."""
    
    def __init__(self, canvas: tk.Canvas, x: int, y: int, screen_width: int):
        """Initialize timer display.
        
        Args:
            canvas: Canvas to draw on
            x: Center x coordinate
            y: Top y coordinate
            screen_width: Screen width for percentage-based sizing
        """
        self.canvas = canvas
        self.center_x = x
        self.start_y = y
        self.screen_width = screen_width
        # Use 12% of screen width per digit (larger to fill screen)
        self.digit_width = int(screen_width * 0.12)
        self.digit_height = int(self.digit_width * 1.67)
        self.digit_spacing = int(screen_width * 0.015)  # 1.5% spacing
        self.colon_width = int(screen_width * 0.03)  # 3% for colon
        
        # Calculate total width of MM:SS display (4 digits + colon + spacing)
        # Format: MM:SS = [M][M]:[S][S]
        total_display_width = (self.digit_width * 4) + self.colon_width + (self.digit_spacing * 3)
        
        # Create displays for work timer (MM:SS) - properly centered
        work_y = y
        self.work_displays = []
        start_x = x - (total_display_width // 2)  # Start from left edge of display
        for i in range(4):  # MM:SS = 4 digits
            if i < 2:
                # Minutes digits (before colon)
                digit_x = start_x + i * (self.digit_width + self.digit_spacing)
            else:
                # Seconds digits (after colon)
                digit_x = start_x + (self.digit_width * 2) + self.digit_spacing + self.colon_width + self.digit_spacing + (i - 2) * (self.digit_width + self.digit_spacing)
            display = SevenSegmentDisplay(canvas, int(digit_x), work_y, screen_width)
            self.work_displays.append(display)
        
        # Colon between minutes and seconds - properly centered
        colon_y = work_y + self.digit_height // 2
        colon_x = start_x + (self.digit_width * 2) + self.digit_spacing + (self.colon_width // 2)
        self.colon_items = []
        
        # Create displays for break timer (MM:SS) - positioned below work timer
        break_y = y + self.digit_height + int(screen_width * 0.05)  # 5% spacing
        self.break_displays = []
        for i in range(4):
            if i < 2:
                # Minutes digits (before colon)
                digit_x = start_x + i * (self.digit_width + self.digit_spacing)
            else:
                # Seconds digits (after colon)
                digit_x = start_x + (self.digit_width * 2) + self.digit_spacing + self.colon_width + self.digit_spacing + (i - 2) * (self.digit_width + self.digit_spacing)
            display = SevenSegmentDisplay(canvas, int(digit_x), break_y, screen_width)
            self.break_displays.append(display)
        
        self.break_colon_items = []
    
    def _draw_colon(self, x: int, y: int, items_list: list) -> None:
        """Draw colon separator.
        
        Args:
            x: Center x coordinate
            y: Center y coordinate
            items_list: List to store colon items
        """
        # Clear previous colon
        for item in items_list:
            self.canvas.delete(item)
        items_list.clear()
        
        # Scale dot size and spacing based on screen width
        dot_size = max(6, int(self.screen_width * 0.01))
        dot_spacing = max(15, int(self.screen_width * 0.025))
        
        # Top dot
        top_dot = self.canvas.create_oval(
            x - dot_size, y - dot_spacing - dot_size,
            x + dot_size, y - dot_spacing + dot_size,
            fill=colors.TIMER_COLON_COLOR,
            outline=""
        )
        items_list.append(top_dot)
        
        # Bottom dot
        bottom_dot = self.canvas.create_oval(
            x - dot_size, y + dot_spacing - dot_size,
            x + dot_size, y + dot_spacing + dot_size,
            fill=colors.TIMER_COLON_COLOR,
            outline=""
        )
        items_list.append(bottom_dot)
    
    def update_timer(self, work_minutes: int, work_seconds: int, 
                     break_minutes: Optional[int] = None, break_seconds: Optional[int] = None) -> None:
        """Update timer display.
        
        Args:
            work_minutes: Work minutes remaining
            work_seconds: Work seconds remaining
            break_minutes: Break minutes (optional)
            break_seconds: Break seconds (optional)
        """
        # Calculate total width of MM:SS display for proper centering
        total_display_width = (self.digit_width * 4) + self.colon_width + (self.digit_spacing * 3)
        start_x = self.center_x - (total_display_width // 2)
        
        # Update work timer (MM:SS)
        work_mm_tens = work_minutes // 10
        work_mm_ones = work_minutes % 10
        work_ss_tens = work_seconds // 10
        work_ss_ones = work_seconds % 10
        
        # Update work digit positions and redraw
        for i, display in enumerate(self.work_displays):
            if i < 2:
                # Minutes digits (before colon)
                display.x = int(start_x + i * (self.digit_width + self.digit_spacing))
            else:
                # Seconds digits (after colon)
                display.x = int(start_x + (self.digit_width * 2) + self.digit_spacing + self.colon_width + self.digit_spacing + (i - 2) * (self.digit_width + self.digit_spacing))
            # Update digit display
            if i == 0:
                display.display_digit(work_mm_tens)
            elif i == 1:
                display.display_digit(work_mm_ones)
            elif i == 2:
                display.display_digit(work_ss_tens)
            else:
                display.display_digit(work_ss_ones)
        
        # Draw colon for work timer - properly centered
        colon_x = start_x + (self.digit_width * 2) + self.digit_spacing + (self.colon_width // 2)
        colon_y = self.start_y + self.digit_height // 2
        self._draw_colon(colon_x, colon_y, self.colon_items)
        
        # Update break timer if provided
        if break_minutes is not None and break_seconds is not None:
            break_mm_tens = break_minutes // 10
            break_mm_ones = break_minutes % 10
            break_ss_tens = break_seconds // 10
            break_ss_ones = break_seconds % 10
            
            # Update break digit positions and redraw
            break_y = self.start_y + self.digit_height + int(self.screen_width * 0.05)
            for i, display in enumerate(self.break_displays):
                if i < 2:
                    # Minutes digits (before colon)
                    display.x = int(start_x + i * (self.digit_width + self.digit_spacing))
                else:
                    # Seconds digits (after colon)
                    display.x = int(start_x + (self.digit_width * 2) + self.digit_spacing + self.colon_width + self.digit_spacing + (i - 2) * (self.digit_width + self.digit_spacing))
                display.y = break_y
                # Update digit display
                if i == 0:
                    display.display_digit(break_mm_tens)
                elif i == 1:
                    display.display_digit(break_mm_ones)
                elif i == 2:
                    display.display_digit(break_ss_tens)
                else:
                    display.display_digit(break_ss_ones)
            
            # Draw colon for break timer
            break_colon_y = break_y + self.digit_height // 2
            self._draw_colon(colon_x, break_colon_y, self.break_colon_items)
    
    def clear(self) -> None:
        """Clear the timer display."""
        for display in self.work_displays + self.break_displays:
            display.clear()
        for item in self.colon_items + self.break_colon_items:
            self.canvas.delete(item)
        self.colon_items.clear()
        self.break_colon_items.clear()

