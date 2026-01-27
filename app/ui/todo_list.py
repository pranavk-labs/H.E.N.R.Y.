"""Todo list widget for H.E.N.R.Y. GUI."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
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


class TodoList:
    """Full-screen todo list view with filtering and interaction."""

    def __init__(self, canvas: tk.Canvas, screen_width: int, screen_height: int):
        """Initialize todo list view.

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
        self._todos: List[Dict[str, Any]] = []
        self._categories: List[Dict[str, Any]] = []
        self._selected_category_id: Optional[str] = None
        self._filter_status: Optional[str] = None
        self._scroll_offset = 0
        self._max_visible_items = 6  # Max items visible at once
        
        # Callbacks
        self._on_close_callback: Optional[Callable[[], None]] = None
        self._on_todo_tap_callback: Optional[Callable[[str], None]] = None
        self._on_filter_change_callback: Optional[Callable[[Optional[str], Optional[str]], None]] = None
        
        # UI sizing (responsive to screen)
        self.padding = int(screen_width * 0.025)
        self.header_height = int(screen_height * 0.10)
        self.filter_bar_height = int(screen_height * 0.08)
        self.item_height = 60  # Min touch target
        self.title_font_size = max(20, int(screen_width * 0.025))
        self.item_font_size = max(18, int(screen_width * 0.0225))
        self.meta_font_size = max(14, int(screen_width * 0.0175))
        
        # Interaction tracking
        self._close_button_rect: Optional[tuple] = None
        self._filter_tab_rects: Dict[str, tuple] = {}
        self._todo_item_rects: Dict[str, tuple] = {}

    def set_close_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback to invoke when close button is clicked."""
        self._on_close_callback = callback

    def set_todo_tap_callback(self, callback: Callable[[str], None]) -> None:
        """Set the callback to invoke when a todo is tapped."""
        self._on_todo_tap_callback = callback

    def set_filter_change_callback(
        self, callback: Callable[[Optional[str], Optional[str]], None]
    ) -> None:
        """Set the callback to invoke when filters change."""
        self._on_filter_change_callback = callback

    def show(
        self,
        todos: List[Dict[str, Any]],
        categories: List[Dict[str, Any]],
        selected_category_id: Optional[str] = None,
        filter_status: Optional[str] = None,
    ) -> None:
        """Show todo list with data.

        Args:
            todos: List of todo dicts
            categories: List of category dicts
            selected_category_id: Currently selected category filter
            filter_status: Currently selected status filter
        """
        self.visible = True
        self._todos = todos
        self._categories = categories
        self._selected_category_id = selected_category_id
        self._filter_status = filter_status
        self._scroll_offset = 0
        self._draw()

    def update_data(
        self,
        todos: List[Dict[str, Any]],
        categories: List[Dict[str, Any]],
    ) -> None:
        """Update todo and category data."""
        self._todos = todos
        self._categories = categories
        if self.visible:
            self._draw()

    def hide(self) -> None:
        """Hide the todo list view."""
        self.visible = False
        for item in self.items:
            self.canvas.delete(item)
        self.items = []
        self._todos = []
        self._categories = []
        self._scroll_offset = 0

    def _draw(self) -> None:
        """Draw the todo list view."""
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

        # Draw filter bar
        filter_y = self.header_height
        self._draw_filter_bar(current_width, filter_y)

        # Draw todo list
        list_y = self.header_height + self.filter_bar_height
        list_height = current_height - list_y
        self._draw_todo_items(current_width, list_y, list_height)

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
            text="Tasks",
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

    def _draw_filter_bar(self, width: int, y: int) -> None:
        """Draw the filter bar with category tabs."""
        # Filter bar background
        filter_bg = self.canvas.create_rectangle(
            0, y, width, y + self.filter_bar_height,
            fill=colors.DIALOG_BG,
            outline=""
        )
        self.items.append(filter_bg)
        
        filter_line = self.canvas.create_line(
            0, y + self.filter_bar_height, width, y + self.filter_bar_height,
            fill=colors.OUTLINE_PRIMARY,
            width=1
        )
        self.items.append(filter_line)

        # Filter tabs
        tab_width = 100
        tab_height = 40
        tab_y = y + (self.filter_bar_height - tab_height) // 2
        tab_x = self.padding

        # "All" tab
        all_selected = self._selected_category_id is None
        all_color = colors.BUTTON_CONFIRM if all_selected else colors.BUTTON_BG
        all_tab = self.canvas.create_rectangle(
            tab_x, tab_y, tab_x + tab_width, tab_y + tab_height,
            fill=all_color,
            outline=colors.OUTLINE_PRIMARY,
            width=2,
            tags="filter_all"
        )
        self.items.append(all_tab)
        
        all_text = self.canvas.create_text(
            tab_x + tab_width // 2,
            tab_y + tab_height // 2,
            text="All",
            font=("Segoe UI", self.meta_font_size),
            fill=colors.TEXT_PRIMARY,
            tags="filter_all"
        )
        self.items.append(all_text)
        
        # Bind click event
        self.canvas.tag_bind("filter_all", "<Button-1>", lambda e: self._on_filter_click('all'))
        self._filter_tab_rects['all'] = (tab_x, tab_y, tab_x + tab_width, tab_y + tab_height)

        tab_x += tab_width + 10

        # Category tabs (show first 4 categories)
        for i, category in enumerate(self._categories[:4]):
            if tab_x + tab_width > width - self.padding:
                break

            cat_id = category.get('id', '')
            cat_name = category.get('name', 'Unknown')
            cat_selected = self._selected_category_id == cat_id
            cat_color = colors.BUTTON_CONFIRM if cat_selected else colors.BUTTON_BG

            cat_tab = self.canvas.create_rectangle(
                tab_x, tab_y, tab_x + tab_width, tab_y + tab_height,
                fill=cat_color,
                outline=colors.OUTLINE_PRIMARY,
                width=2,
                tags=f"filter_{cat_id}"
            )
            self.items.append(cat_tab)

            # Category name (truncate if needed)
            cat_text = self.canvas.create_text(
                tab_x + tab_width // 2,
                tab_y + tab_height // 2,
                text=cat_name[:8],
                font=("Segoe UI", self.meta_font_size),
                fill=colors.TEXT_PRIMARY,
                tags=f"filter_{cat_id}"
            )
            self.items.append(cat_text)

            # Bind click event
            self.canvas.tag_bind(f"filter_{cat_id}", "<Button-1>", lambda e, cid=cat_id: self._on_filter_click(cid))
            self._filter_tab_rects[cat_id] = (tab_x, tab_y, tab_x + tab_width, tab_y + tab_height)

            tab_x += tab_width + 10

    def _draw_todo_items(self, width: int, y: int, height: int) -> None:
        """Draw the list of todo items."""
        if not self._todos:
            # No todos message
            no_todos = self.canvas.create_text(
                width // 2,
                y + height // 2,
                text="No tasks yet",
                font=("Segoe UI", self.item_font_size),
                fill=colors.TEXT_SECONDARY
            )
            self.items.append(no_todos)
            return

        # Calculate visible range based on scroll
        start_idx = max(0, self._scroll_offset)
        end_idx = min(len(self._todos), start_idx + self._max_visible_items)

        # Draw visible todos
        item_y = y + self.padding
        self._todo_item_rects = {}

        for i in range(start_idx, end_idx):
            todo = self._todos[i]
            self._draw_todo_item(todo, width, item_y)
            item_y += self.item_height + 5

    def _draw_todo_item(self, todo: Dict[str, Any], width: int, y: int) -> None:
        """Draw a single todo item."""
        item_width = width - (self.padding * 2)
        x1 = self.padding
        x2 = x1 + item_width
        y2 = y + self.item_height

        # Background
        bg_color = colors.DIALOG_BG
        if todo.get('status') == 'completed':
            bg_color = colors.OUTLINE_SECONDARY
        
        item_bg = self.canvas.create_rectangle(
            x1, y, x2, y2,
            fill=bg_color,
            outline=colors.OUTLINE_PRIMARY,
            width=2,
            tags=f"todo_{todo.get('id', '')}"
        )
        self.items.append(item_bg)

        # Priority indicator (colored bar on left)
        priority = todo.get('priority', 'medium')
        priority_colors_map = {
            'critical': '#ff4444',
            'high': '#ff9944',
            'medium': '#44aaff',
            'low': '#888888',
        }
        priority_color = priority_colors_map.get(priority, '#888888')
        priority_bar = self.canvas.create_rectangle(
            x1, y, x1 + 8, y2,
            fill=priority_color,
            outline="",
            tags=f"todo_{todo.get('id', '')}"
        )
        self.items.append(priority_bar)

        # Title
        title = todo.get('title', 'Untitled')
        title_color = colors.TEXT_SECONDARY if todo.get('status') == 'completed' else colors.TEXT_PRIMARY
        title_text = self.canvas.create_text(
            x1 + 15,
            y + 12,
            text=title[:40],
            font=("Segoe UI", self.item_font_size, "bold"),
            fill=title_color,
            anchor="nw",
            tags=f"todo_{todo.get('id', '')}"
        )
        self.items.append(title_text)

        # Metadata row (difficulty, due date, status)
        meta_y = y + self.item_height - 18
        meta_x = x1 + 15

        # Difficulty (stars)
        difficulty = todo.get('difficulty', 3)
        stars = '★' * difficulty + '☆' * (5 - difficulty)
        stars_text = self.canvas.create_text(
            meta_x,
            meta_y,
            text=stars,
            font=("Segoe UI", self.meta_font_size),
            fill=colors.TEXT_SECONDARY,
            anchor="w",
            tags=f"todo_{todo.get('id', '')}"
        )
        self.items.append(stars_text)

        # Due date (if set)
        due_date = todo.get('due_date')
        if due_date:
            try:
                # Parse ISO date
                due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                due_str = due_dt.strftime('%m/%d')
                # Check if overdue
                now = datetime.now(due_dt.tzinfo)
                is_overdue = due_dt < now and todo.get('status') != 'completed'
                due_color = colors.STATUS_DISCONNECTED if is_overdue else colors.TEXT_SECONDARY
                due_text = self.canvas.create_text(
                    meta_x + 80,
                    meta_y,
                    text=f"📅 {due_str}",
                    font=("Segoe UI", self.meta_font_size),
                    fill=due_color,
                    anchor="w",
                    tags=f"todo_{todo.get('id', '')}"
                )
                self.items.append(due_text)
            except (ValueError, TypeError):
                pass

        # Status badge (on the right)
        status = todo.get('status', 'todo')
        status_labels = {
            'todo': 'To Do',
            'in_progress': 'In Progress',
            'completed': '✓ Done',
            'cancelled': 'Cancelled',
        }
        status_label = status_labels.get(status, status)
        status_text = self.canvas.create_text(
            x2 - 10,
            meta_y,
            text=status_label,
            font=("Segoe UI", self.meta_font_size),
            fill=colors.TEXT_SECONDARY,
            anchor="e",
            tags=f"todo_{todo.get('id', '')}"
        )
        self.items.append(status_text)

        # Bind click event
        todo_id = todo.get('id', '')
        self.canvas.tag_bind(f"todo_{todo_id}", "<Button-1>", lambda e, tid=todo_id: self._on_todo_click(tid))
        self._todo_item_rects[todo_id] = (x1, y, x2, y2)

    def _on_close_click(self, event: Any) -> None:
        """Handle close button click."""
        logger.info("Todo list close button clicked")
        if self._on_close_callback:
            self._on_close_callback()

    def _on_filter_click(self, filter_id: str) -> None:
        """Handle filter tab click."""
        new_category = None if filter_id == 'all' else filter_id
        logger.info(f"Filter clicked: {filter_id}")
        self._selected_category_id = new_category
        if self._on_filter_change_callback:
            self._on_filter_change_callback(self._filter_status, new_category)

    def _on_todo_click(self, todo_id: str) -> None:
        """Handle todo item click."""
        logger.info(f"Todo clicked: {todo_id}")
        if self._on_todo_tap_callback:
            self._on_todo_tap_callback(todo_id)

    def handle_touch(self, pos: tuple[int, int]) -> bool:
        """Handle touch/click event (for compatibility).
        
        Args:
            pos: Touch position (x, y)
            
        Returns:
            True if event was handled
        """
        # tkinter handles clicks via bindings, so this is just for compatibility
        return self.visible


__all__ = ["TodoList"]
