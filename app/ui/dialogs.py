"""Dialog widgets for H.E.N.R.Y. GUI."""

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


class ConfirmationDialog:
    """Modal-style confirmation dialog for ending timer session."""
    
    def __init__(self, canvas: tk.Canvas, x: int, y: int, screen_width: int,
                 on_confirm: Callable, on_cancel: Callable):
        """Initialize confirmation dialog.
        
        Args:
            canvas: Canvas to draw on
            x: Center x coordinate
            y: Center y coordinate
            screen_width: Screen width for responsive sizing
            on_confirm: Callback for confirm button
            on_cancel: Callback for cancel button
        """
        self.canvas = canvas
        self.center_x = x
        self.center_y = y
        self.screen_width = screen_width
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.items = []
        self.confirm_rect = None
        self.cancel_rect = None
        
        # Dialog sizing
        self.width = int(screen_width * 0.4)  # 40% of width
        self.height = int(screen_width * 0.15)  # 15% of width
        self.button_height = max(int(screen_width * 0.05), int(screen_width * 0.06))  # 6% of width, min 5% for small screens
        self.button_width = int(self.width * 0.35)
        
        self._draw()
    
    def _draw(self) -> None:
        """Draw the confirmation dialog."""
        # Clear previous items
        for item in self.items:
            self.canvas.delete(item)
        self.items = []
        
        # Dialog background (semi-transparent overlay effect)
        x1 = self.center_x - (self.width // 2)
        y1 = self.center_y - (self.height // 2)
        x2 = self.center_x + (self.width // 2)
        y2 = self.center_y + (self.height // 2)
        
        # Background rectangle with shadow for depth
        shadow_offset = 4
        shadow = self.canvas.create_rectangle(
            x1 + shadow_offset, y1 + shadow_offset,
            x2 + shadow_offset, y2 + shadow_offset,
            fill="#000000",
            outline="",
            width=0
        )
        self.items.append(shadow)

        bg = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=colors.DIALOG_BG,
            outline=colors.DIALOG_OUTLINE,
            width=4
        )
        self.items.append(bg)

        # Message text
        message_y = y1 + int(self.height * 0.35)
        font_size = max(int(self.screen_width * 0.018), int(self.screen_width * 0.025))  # 2.5% of width, min 1.8% for small screens
        message = self.canvas.create_text(
            self.center_x, message_y,
            text="End focus session?",
            font=("Arial", font_size, "bold"),
            fill=colors.DIALOG_TEXT
        )
        self.items.append(message)
        
        # Buttons
        button_y = y1 + int(self.height * 0.65)
        button_spacing = int(self.width * 0.1)
        total_button_width = (self.button_width * 2) + button_spacing
        button_start_x = self.center_x - (total_button_width // 2)
        
        # Cancel button (left)
        cancel_x1 = button_start_x
        cancel_y1 = button_y - (self.button_height // 2)
        cancel_x2 = cancel_x1 + self.button_width
        cancel_y2 = button_y + (self.button_height // 2)

        self.cancel_rect = (cancel_x1, cancel_y1, cancel_x2, cancel_y2)

        # Draw button shadow for depth
        shadow_offset = 3
        cancel_shadow = self.canvas.create_rectangle(
            cancel_x1 + shadow_offset, cancel_y1 + shadow_offset,
            cancel_x2 + shadow_offset, cancel_y2 + shadow_offset,
            fill="#000000",
            outline="",
            width=0
        )
        self.items.append(cancel_shadow)

        cancel_bg = self.canvas.create_rectangle(
            cancel_x1, cancel_y1, cancel_x2, cancel_y2,
            fill=colors.BUTTON_CANCEL,
            outline=colors.BUTTON_OUTLINE,
            width=3
        )
        self.items.append(cancel_bg)

        cancel_text = self.canvas.create_text(
            (cancel_x1 + cancel_x2) // 2, button_y,
            text="Cancel",
            font=("Arial", max(int(self.screen_width * 0.016), int(self.screen_width * 0.022)), "bold"),  # 2.2% of width, min 1.6% for small screens
            fill="white"
        )
        self.items.append(cancel_text)
        
        # Confirm button (right)
        confirm_x1 = button_start_x + self.button_width + button_spacing
        confirm_y1 = cancel_y1
        confirm_x2 = confirm_x1 + self.button_width
        confirm_y2 = cancel_y2

        self.confirm_rect = (confirm_x1, confirm_y1, confirm_x2, confirm_y2)

        # Draw button shadow for depth
        confirm_shadow = self.canvas.create_rectangle(
            confirm_x1 + shadow_offset, confirm_y1 + shadow_offset,
            confirm_x2 + shadow_offset, confirm_y2 + shadow_offset,
            fill="#000000",
            outline="",
            width=0
        )
        self.items.append(confirm_shadow)

        confirm_bg = self.canvas.create_rectangle(
            confirm_x1, confirm_y1, confirm_x2, confirm_y2,
            fill=colors.BUTTON_CONFIRM,
            outline=colors.BUTTON_OUTLINE,
            width=3
        )
        self.items.append(confirm_bg)

        confirm_text = self.canvas.create_text(
            (confirm_x1 + confirm_x2) // 2, button_y,
            text="Yes",
            font=("Arial", max(int(self.screen_width * 0.016), int(self.screen_width * 0.022)), "bold"),  # 2.2% of width, min 1.6% for small screens
            fill="white"
        )
        self.items.append(confirm_text)
    
    def handle_click(self, x: int, y: int) -> bool:
        """Handle click event. Returns True if click was handled."""
        if not self.confirm_rect or not self.cancel_rect:
            return False
        
        cx1, cy1, cx2, cy2 = self.confirm_rect
        canx1, cany1, canx2, cany2 = self.cancel_rect
        
        if cx1 <= x <= cx2 and cy1 <= y <= cy2:
            # Confirm button clicked
            self.on_confirm()
            return True
        elif canx1 <= x <= canx2 and cany1 <= y <= cany2:
            # Cancel button clicked
            self.on_cancel()
            return True
        
        return False
    
    def clear(self) -> None:
        """Clear the dialog."""
        for item in self.items:
            self.canvas.delete(item)
        self.items = []
        self.confirm_rect = None
        self.cancel_rect = None

