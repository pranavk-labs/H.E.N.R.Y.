"""Animated smiley face widget for H.E.N.R.Y. GUI."""

from __future__ import annotations

import logging
import math
import random
import sys
import time
from pathlib import Path

try:
    import tkinter as tk
except ImportError:
    tk = None

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts import colors

logger = logging.getLogger(__name__)


class SmileyFace:
    """Animated smiley face widget - just eyes and mouth."""
    
    def __init__(self, canvas: tk.Canvas, x: int, y: int, screen_width: int):
        """Initialize smiley face.

        Args:
            canvas: Canvas to draw on
            x: Center x coordinate
            y: Center y coordinate
            screen_width: Screen width for percentage-based sizing
        """
        self.canvas = canvas
        self.center_x = x
        self.center_y = y
        self.screen_width = screen_width
        # Use 40% of screen width for more reasonable, centered size
        self.size = int(screen_width * 0.4)
        self.base_radius = self.size // 2
        self.sleepiness_level = 0  # 0=happy, 1=neutral, 2=sleepy, 3=very sleepy
        self.animation_phase = 0.0
        self.vertical_offset = 0.0
        self.horizontal_offset = 0.0  # For personality - slight head tilts
        self.is_blinking = False
        self.blink_start_time = 0.0
        self.last_blink_time = time.time()
        self.blink_interval = 2.5 + (random.random() * 3.0)  # 2.5-5.5 seconds (more varied)
        self.is_listening = False  # Visual indicator when recording audio

        # Colors
        self.eye_color = colors.FACE_EYE_COLOR
        self.mouth_color = colors.FACE_MOUTH_COLOR

        logger.debug(f"SmileyFace initialized: center=({x}, {y}), size={self.size}, screen_width={screen_width}")

        # Draw initial face
        self._draw_face()
    
    def _draw_face(self) -> None:
        """Draw the smiley face (eyes and mouth only)."""
        # Clear previous drawing
        if hasattr(self, 'face_items') and self.face_items:
            for item in self.face_items:
                self.canvas.delete(item)
        self.face_items = []
        
        # Calculate current position with animation offsets (for personality)
        current_x = self.center_x + self.horizontal_offset
        current_y = self.center_y + self.vertical_offset
        
        # Calculate eye properties based on sleepiness level and listening state
        # Sleepiness: 0=happy, 1=neutral, 2=sleepy, 3=very sleepy
        if self.is_listening:
            # Listening: Wide, alert eyes
            eye_size_multiplier = 0.35  # 15% larger than normal
            eye_y_offset_multiplier = -0.18  # Slightly higher
        else:
            eye_size_multiplier = [0.3, 0.25, 0.2, 0.15][self.sleepiness_level]
            eye_y_offset_multiplier = [-0.15, -0.12, -0.1, -0.08][self.sleepiness_level]
        eye_x_offset = self.base_radius * 0.4  # Wider spacing
        eye_size = self.base_radius * eye_size_multiplier
        eye_y_offset = self.base_radius * eye_y_offset_multiplier
        
        # Line width scales with screen size
        line_width = max(4, int(self.screen_width * 0.01))

        # Smooth blink: scale eye height smoothly
        blink_scale = 1.0
        if self.is_blinking:
            blink_duration = 0.15  # 150ms total blink (matches update_animation)
            elapsed = time.time() - self.blink_start_time
            if elapsed < blink_duration:
                # Triangular wave (0->1 close, 1->0 open), smoothed
                t = elapsed / blink_duration
                triangle = 1.0 - abs(2 * t - 1.0)  # 0->1->0
                # Smoothstep for softer interpolation
                triangle = triangle * triangle * (3 - 2 * triangle)
                blink_scale = 1.0 - 0.95 * triangle  # down to 5% height when closed
            else:
                self.is_blinking = False
                blink_scale = 1.0

        # Draw eyes with smooth vertical scaling during blink
        # Left eye
        left_eye = self.canvas.create_oval(
            current_x - eye_x_offset - eye_size,
            current_y + eye_y_offset - (eye_size * blink_scale),
            current_x - eye_x_offset + eye_size,
            current_y + eye_y_offset + (eye_size * blink_scale),
            fill=self.eye_color,
            outline=""
        )
        self.face_items.append(left_eye)

        # Right eye
        right_eye = self.canvas.create_oval(
            current_x + eye_x_offset - eye_size,
            current_y + eye_y_offset - (eye_size * blink_scale),
            current_x + eye_x_offset + eye_size,
            current_y + eye_y_offset + (eye_size * blink_scale),
            fill=self.eye_color,
            outline=""
        )
        self.face_items.append(right_eye)
        
        # Draw droopy eyes if sleepy (level 2 or 3) - but not if blinking
        if self.sleepiness_level >= 2 and not self.is_blinking:
            # Draw semi-closed eyes (lines)
            droop_y = current_y + eye_y_offset + eye_size * 0.3
            droop_width = eye_size * 1.2
            left_droop = self.canvas.create_line(
                current_x - eye_x_offset - droop_width * 0.5,
                droop_y,
                current_x - eye_x_offset + droop_width * 0.5,
                droop_y,
                fill=self.eye_color,
                width=line_width
            )
            self.face_items.append(left_droop)

            right_droop = self.canvas.create_line(
                current_x + eye_x_offset - droop_width * 0.5,
                droop_y,
                current_x + eye_x_offset + droop_width * 0.5,
                droop_y,
                fill=self.eye_color,
                width=line_width
            )
            self.face_items.append(right_droop)
        
        # Draw mouth - adjust based on sleepiness
        mouth_y = current_y + self.base_radius * 0.25
        mouth_width = self.base_radius * 0.7  # Wider mouth
        mouth_height = self.base_radius * 0.3  # Taller mouth

        if self.sleepiness_level >= 3:
            # Very sleepy: neutral/frown mouth (straight line)
            mouth = self.canvas.create_line(
                current_x - mouth_width,
                mouth_y,
                current_x + mouth_width,
                mouth_y,
                fill=self.mouth_color,
                width=line_width
            )
        elif self.sleepiness_level == 2:
            # Sleepy: small smile (smaller arc)
            mouth = self.canvas.create_arc(
                current_x - mouth_width * 0.7,
                mouth_y - mouth_height * 0.3,
                current_x + mouth_width * 0.7,
                mouth_y + mouth_height * 0.3,
                start=180,
                extent=180,
                style="arc",
                outline=self.mouth_color,
                width=line_width
            )
        elif self.sleepiness_level == 1:
            # Neutral: normal smile
            mouth = self.canvas.create_arc(
                current_x - mouth_width * 0.85,
                mouth_y - mouth_height * 0.4,
                current_x + mouth_width * 0.85,
                mouth_y + mouth_height * 0.4,
                start=180,
                extent=180,
                style="arc",
                outline=self.mouth_color,
                width=line_width
            )
        else:
            # Happy: big smile
            mouth = self.canvas.create_arc(
                current_x - mouth_width,
                mouth_y - mouth_height * 0.5,
                current_x + mouth_width,
                mouth_y + mouth_height * 0.5,
                start=180,
                extent=180,
                style="arc",
                outline=self.mouth_color,
                width=line_width
            )
        self.face_items.append(mouth)
    
    def update_animation(self, phase: float, sleepiness_level: int = 0) -> None:
        """Update animation state.
        
        Args:
            phase: Animation phase (0.0 to 2*pi)
            sleepiness_level: Sleepiness level (0=happy, 1=neutral, 2=sleepy, 3=very sleepy)
        """
        needs_redraw = self.sleepiness_level != sleepiness_level
        if needs_redraw:
            logger.debug(f"Sleepiness level changed: {self.sleepiness_level} -> {sleepiness_level}")
        self.sleepiness_level = sleepiness_level
        self.animation_phase = phase
        
        # Check if it's time to blink
        current_time = time.time()
        if not self.is_blinking and (current_time - self.last_blink_time) >= self.blink_interval:
            self.is_blinking = True
            self.blink_start_time = current_time
            self.last_blink_time = current_time
            # Schedule next blink (random interval)
            self.blink_interval = 3.0 + (random.random() * 2.0)  # 3-5 seconds
        
        # Update blinking state
        if self.is_blinking:
            blink_duration = 0.15  # 150ms total blink
            if (current_time - self.blink_start_time) >= blink_duration:
                self.is_blinking = False
            # Force redraw during blink for smooth animation
            needs_redraw = True
        
        # Calculate vertical offset (sine wave for floating)
        # Amplitude decreases with sleepiness
        vertical_amplitudes = [10.0, 7.0, 4.0, 2.0]  # Happy, neutral, sleepy, very sleepy
        vertical_amplitude = vertical_amplitudes[min(sleepiness_level, 3)]
        new_vertical_offset = math.sin(phase) * vertical_amplitude

        # Calculate horizontal offset (slower sine wave for personality - subtle head sway)
        # Use a different phase for more natural movement
        horizontal_amplitudes = [5.0, 3.0, 2.0, 1.0]  # Happy is more animated
        horizontal_amplitude = horizontal_amplitudes[min(sleepiness_level, 3)]
        new_horizontal_offset = math.sin(phase * 0.7) * horizontal_amplitude  # 0.7x slower

        # Always redraw for smooth animation (optimized to only clear/redraw when needed)
        old_vertical_offset = self.vertical_offset
        old_horizontal_offset = self.horizontal_offset
        self.vertical_offset = new_vertical_offset
        self.horizontal_offset = new_horizontal_offset
        
        # Redraw if sleepiness level changed, blinking (eyes need to change shape), or no items yet
        if needs_redraw or self.is_blinking or not hasattr(self, 'face_items') or len(self.face_items) == 0:
            self._draw_face()
        else:
            # Move existing items for smoother animation when not blinking
            vertical_delta = new_vertical_offset - old_vertical_offset
            horizontal_delta = new_horizontal_offset - old_horizontal_offset
            # Only move if change is significant
            if abs(vertical_delta) > 0.1 or abs(horizontal_delta) > 0.1:
                for item in self.face_items:
                    self.canvas.move(item, horizontal_delta, vertical_delta)

    def set_listening(self, is_listening: bool) -> None:
        """Set listening state (shows wider/more alert eyes).

        Args:
            is_listening: Whether HENRY is currently listening/recording
        """
        if self.is_listening != is_listening:
            self.is_listening = is_listening
            logger.debug(f"Listening state changed: {is_listening}")
            self._draw_face()  # Immediately redraw with new eye size

