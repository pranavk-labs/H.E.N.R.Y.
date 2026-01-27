"""Seven-segment display widget for H.E.N.R.Y. timer."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Tuple

try:
    import tkinter as tk
except ImportError:
    tk = None

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts import colors


class SevenSegmentDisplay:
    """8-segment display widget (7 segments + decimal point)."""
    
    # Segment definitions: (x1, y1, x2, y2) for each segment
    # Segments are numbered: top, upper-right, lower-right, bottom, lower-left, upper-left, middle
    # Added small gaps (0.05) to prevent rounded caps from overlapping
    SEGMENTS = [
        (0.15, 0.03, 0.85, 0.03),   # Top (0)
        (0.87, 0.08, 0.87, 0.43),   # Upper-right (1)
        (0.87, 0.57, 0.87, 0.92),   # Lower-right (2)
        (0.15, 0.97, 0.85, 0.97),   # Bottom (3)
        (0.13, 0.57, 0.13, 0.92),   # Lower-left (4)
        (0.13, 0.08, 0.13, 0.43),   # Upper-left (5)
        (0.15, 0.5, 0.85, 0.5),     # Middle (6)
    ]
    
    # Digit patterns: which segments are ON for each digit 0-9
    DIGIT_PATTERNS = [
        [0, 1, 2, 3, 4, 5],      # 0
        [1, 2],                   # 1
        [0, 1, 3, 4, 6],         # 2
        [0, 1, 2, 3, 6],         # 3
        [1, 2, 5, 6],            # 4
        [0, 2, 3, 5, 6],         # 5
        [0, 2, 3, 4, 5, 6],      # 6
        [0, 1, 2],               # 7
        [0, 1, 2, 3, 4, 5, 6],   # 8
        [0, 1, 2, 3, 5, 6],      # 9
    ]
    
    def __init__(self, canvas: tk.Canvas, x: int, y: int, screen_width: int):
        """Initialize 7-segment display.
        
        Args:
            canvas: Canvas to draw on
            x: Top-left x coordinate
            y: Top-left y coordinate
            screen_width: Screen width for percentage-based sizing
        """
        self.canvas = canvas
        self.x = x
        self.y = y
        self.screen_width = screen_width
        # Use 12% of screen width per digit (larger to fill screen)
        self.width = int(screen_width * 0.12)
        # Height is 1.67x width (standard 7-segment aspect ratio)
        self.height = int(self.width * 1.67)
        self.segment_items = []
        self.on_color = colors.TIMER_DIGIT_ON  # Light grey for active segments
        self.off_color = colors.TIMER_DIGIT_OFF  # Dark grey for inactive segments
        self.segment_width = max(6, int(self.width * 0.10))  # Thicker lines for better visibility
    
    def _get_segment_coords(self, segment_idx: int) -> Tuple[int, int, int, int]:
        """Get absolute coordinates for a segment.
        
        Args:
            segment_idx: Segment index (0-6)
            
        Returns:
            (x1, y1, x2, y2) coordinates
        """
        seg = self.SEGMENTS[segment_idx]
        x1 = self.x + int(seg[0] * self.width)
        y1 = self.y + int(seg[1] * self.height)
        x2 = self.x + int(seg[2] * self.width)
        y2 = self.y + int(seg[3] * self.height)
        return (x1, y1, x2, y2)
    
    def _draw_segment(self, segment_idx: int, on: bool) -> None:
        """Draw a single segment.
        
        Args:
            segment_idx: Segment index (0-6)
            on: Whether segment should be ON
        """
        x1, y1, x2, y2 = self._get_segment_coords(segment_idx)
        color = self.on_color if on else self.off_color
        
        # Draw segment as a line
        item = self.canvas.create_line(
            x1, y1, x2, y2,
            fill=color,
            width=self.segment_width,
            capstyle="round",
            joinstyle="round"
        )
        self.segment_items.append(item)
    
    def display_digit(self, digit: int) -> None:
        """Display a single digit (0-9).
        
        Args:
            digit: Digit to display (0-9)
        """
        # Clear previous display
        for item in self.segment_items:
            self.canvas.delete(item)
        self.segment_items = []
        
        if 0 <= digit <= 9:
            pattern = self.DIGIT_PATTERNS[digit]
            for seg_idx in range(7):
                self._draw_segment(seg_idx, seg_idx in pattern)
    
    def clear(self) -> None:
        """Clear the display."""
        for item in self.segment_items:
            self.canvas.delete(item)
        self.segment_items = []

