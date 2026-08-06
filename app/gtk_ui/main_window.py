"""GTK/libadwaita main window."""

from __future__ import annotations

import logging
import math
import os
import time
from typing import Any, Callable

from app.gtk_ui.face_view import (
    ToolPanel,
    action_exception_feedback,
    action_feedback,
    action_status_class,
    action_tooltip,
    active_states_status_class,
    compact_status_badges,
    control_state,
    face_geometry,
    header_state,
    header_view_status_class,
    header_view_title,
    model_entry_text,
    model_entry_user_edited_after_action,
    model_entry_user_edited_after_change,
    model_override,
    offline_runtime_state,
    runtime_summary,
    runtime_status_class,
    sleepiness_for_elapsed,
    status_badge_rgba,
    status_badges,
    surface_accent,
    tool_panel,
    wrapped_detail_lines,
    wrapped_text_lines,
)
from app.gtk_ui.runtime_client import RuntimeClient

logger = logging.getLogger(__name__)

STATUS_CLASSES = ("status-ok", "status-error", "status-pending", "status-neutral")


def require_gtk():
    """Load GTK dependencies only when the GTK app is launched."""
    try:
        import gi

        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw, Gdk, GLib, Gtk

        return Adw, Gdk, GLib, Gtk
    except Exception as exc:
        raise RuntimeError(
            "GTK4/libadwaita is not available. Install PyGObject, GTK4, and libadwaita."
        ) from exc


class HenryGtkWindow:
    """Main GTK window for HENRY."""

    def __init__(self, app: Any, client: RuntimeClient) -> None:
        Adw, Gdk, GLib, Gtk = require_gtk()
        self.Adw = Adw
        self.Gdk = Gdk
        self.GLib = GLib
        self.Gtk = Gtk
        self.client = client

        self.window = Adw.ApplicationWindow(application=app)
        self.window.set_title("H.E.N.R.Y.")
        self.window.set_default_size(1100, 640)

        self.view_status_label = Gtk.Label(label="Listening")
        self.view_status_label.add_css_class("view-pill")
        self.active_states_label = Gtk.Label(label="")
        self.active_states_label.add_css_class("active-states")
        self.runtime_status_label = Gtk.Label(label="Runtime: unknown")
        self.runtime_status_label.add_css_class("runtime-pill")
        self.action_status_label = Gtk.Label(label="")
        self.action_status_label.add_css_class("action-status")
        self.connection_status_label = Gtk.Label(label="Backend: checking")
        self.connection_status_label.add_css_class("connection-label")
        self.connection_status_label.add_css_class("status-pending")
        self.model_entry = Gtk.Entry()
        self.model_entry.set_placeholder_text("model")
        self.model_entry.set_tooltip_text("Model override for preload and unload")
        self.model_entry.set_width_chars(18)
        self.model_entry.add_css_class("model-entry")
        self.model_entry.connect("changed", self._on_model_entry_changed)

        self.canvas = Gtk.DrawingArea()
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
        self.canvas.set_draw_func(self._draw)

        self.runtime: dict[str, Any] = {}
        self.ui_state: dict[str, Any] = {"active_view": "idle", "status_text": ""}
        self._last_state_key: tuple[Any, ...] | None = None
        self._last_interaction_time = time.time()
        self._phase = 0.0
        self._blink_start = 0.0
        self._last_blink = time.time()
        self._blink_interval = 3.0
        self._happy_seconds = int(os.getenv("GUI_HAPPY_DURATION", "120"))
        self._neutral_seconds = int(os.getenv("GUI_NEUTRAL_DURATION", "300"))
        self._sleepy_seconds = int(os.getenv("GUI_SLEEPY_DURATION", "600"))
        self._buttons: dict[str, Any] = {}
        self._model_entry_user_edited = False
        self._syncing_model_entry = False

        self._install_css()
        self._build()
        self.refresh()
        GLib.timeout_add(33, self._animate)
        GLib.timeout_add_seconds(2, self.refresh)

    def _install_css(self) -> None:
        Gtk = self.Gtk
        Gdk = self.Gdk

        css = b"""
        window {
            background: #1a1a1a;
            color: #e0e0e0;
        }
        headerbar {
            background: #1a1a1a;
            color: #e0e0e0;
            border-bottom: 1px solid #2a2a2a;
        }
        .runtime-pill {
            color: #b0b0b0;
            font-size: 13px;
            margin-right: 8px;
        }
        .action-status {
            color: #d7d7d7;
            font-size: 13px;
            margin-right: 10px;
        }
        .view-pill {
            color: #e6e6e6;
            font-size: 13px;
            font-weight: 700;
            margin-left: 8px;
            margin-right: 8px;
        }
        .active-states {
            color: #d7d7d7;
            font-size: 13px;
            margin-right: 10px;
        }
        .connection-label {
            font-size: 13px;
            margin-right: 12px;
        }
        .model-entry {
            margin-right: 8px;
        }
        .status-ok {
            color: #50c878;
        }
        .status-error {
            color: #ff6b5f;
        }
        .status-pending {
            color: #d8b84f;
        }
        .status-neutral {
            color: #e6e6e6;
        }
        button.suggested-action {
            background: #2f7d4c;
            color: #ffffff;
        }
        """

        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _icon_button(
        self,
        icon_name: str,
        tooltip: str,
        action: Callable[[], Any],
    ) -> Any:
        button = self.Gtk.Button.new_from_icon_name(icon_name)
        button.set_tooltip_text(tooltip)
        button.connect("clicked", lambda _button: action())
        return button

    def _build(self) -> None:
        Gtk = self.Gtk
        Adw = self.Adw

        toolbar = Adw.HeaderBar()
        toolbar.set_title_widget(Adw.WindowTitle(title="H.E.N.R.Y.", subtitle=""))
        self._buttons["back"] = self._icon_button(
            "go-previous-symbolic",
            action_tooltip("back", "Go back"),
            self.go_back,
        )
        self._buttons["start"] = self._icon_button(
            "media-playback-start-symbolic",
            action_tooltip("start", "Start voice runtime"),
            self.start_runtime,
        )
        self._buttons["start"].add_css_class("suggested-action")
        self._buttons["stop"] = self._icon_button(
            "media-playback-stop-symbolic",
            action_tooltip("stop", "Stop voice runtime"),
            self.stop_runtime,
        )
        self._buttons["unload"] = self._icon_button(
            "edit-clear-symbolic",
            action_tooltip("unload", "Unload model"),
            self.unload_model,
        )
        self._buttons["preload"] = self._icon_button(
            "view-refresh-symbolic",
            action_tooltip("preload", "Preload model"),
            self.preload_model,
        )
        toolbar.pack_start(self._buttons["back"])
        toolbar.pack_start(self._buttons["start"])
        toolbar.pack_start(self._buttons["stop"])
        toolbar.pack_end(self._buttons["unload"])
        toolbar.pack_end(self._buttons["preload"])
        toolbar.pack_end(self.model_entry)
        toolbar.pack_end(self.runtime_status_label)
        toolbar.pack_end(self.action_status_label)
        toolbar.pack_end(self.connection_status_label)
        toolbar.pack_end(self.active_states_label)
        toolbar.pack_end(self.view_status_label)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(toolbar)
        root.append(self.canvas)
        self.window.set_content(root)

    def _replace_css_classes(
        self,
        widget: Any,
        classes: tuple[str, ...],
        active_class: str,
    ) -> None:
        for css_class in classes:
            widget.remove_css_class(css_class)
        widget.add_css_class(active_class)

    def _apply_control_state(self, runtime: dict[str, Any]) -> None:
        enabled = control_state(runtime)
        for name, button in self._buttons.items():
            if name == "back":
                continue
            button.set_sensitive(enabled.get(name, False))

    def _apply_header_state(self, ui_state: dict[str, Any]) -> None:
        state = header_state(ui_state)
        if "back" in self._buttons:
            self._buttons["back"].set_sensitive(bool(state["can_go_back"]))
        self.active_states_label.set_text(str(state["active_states_label"]))
        self._replace_css_classes(
            self.active_states_label,
            STATUS_CLASSES,
            active_states_status_class(ui_state),
        )

    def _on_model_entry_changed(self, _entry: Any) -> None:
        self._model_entry_user_edited = model_entry_user_edited_after_change(
            self.model_entry.get_text(),
            was_syncing=self._syncing_model_entry,
            was_user_edited=self._model_entry_user_edited,
        )

    def _sync_model_entry(self, runtime: dict[str, Any]) -> None:
        next_text = model_entry_text(
            self.model_entry.get_text(),
            runtime,
            user_edited=self._model_entry_user_edited,
        )
        if next_text == self.model_entry.get_text():
            return
        self._syncing_model_entry = True
        try:
            self.model_entry.set_text(next_text)
        finally:
            self._syncing_model_entry = False

    def _run_action(self, action_name: str, action: Callable[[], dict[str, Any]]) -> None:
        try:
            response = action()
            self._model_entry_user_edited = model_entry_user_edited_after_action(
                action_name,
                response,
                was_user_edited=self._model_entry_user_edited,
            )
            self.action_status_label.set_text(action_feedback(action_name, response))
            self._replace_css_classes(
                self.action_status_label,
                STATUS_CLASSES,
                action_status_class(response),
            )
            self.refresh()
        except Exception as exc:
            logger.error("GTK runtime action failed: %s", exc, exc_info=True)
            self.action_status_label.set_text(action_exception_feedback(action_name, exc))
            self._replace_css_classes(
                self.action_status_label,
                STATUS_CLASSES,
                "status-error",
            )
            self.refresh()

    def go_back(self) -> None:
        """Navigate back in the UI stack."""
        self._run_action("back", self.client.go_back)

    def start_runtime(self) -> None:
        """Start the voice runtime."""
        self._run_action("start", self.client.start_runtime)

    def stop_runtime(self) -> None:
        """Stop the voice runtime."""
        self._run_action("stop", self.client.stop_runtime)

    def preload_model(self) -> None:
        """Preload the configured model."""
        self._run_action("preload", lambda: self.client.preload_model(self._selected_model()))

    def unload_model(self) -> None:
        """Unload the configured model."""
        self._run_action("unload", lambda: self.client.unload_model(self._selected_model()))

    def _selected_model(self) -> str | None:
        return model_override(self.model_entry.get_text())

    def _state_key(
        self,
        runtime: dict[str, Any],
        ui_state: dict[str, Any],
    ) -> tuple[Any, ...]:
        return (
            runtime.get("state"),
            runtime.get("model"),
            runtime.get("error"),
            ui_state.get("active_view"),
            ui_state.get("status_text"),
            repr(ui_state.get("timer_state")),
            repr(ui_state.get("idea_view")),
            ui_state.get("active_todo_id"),
            ui_state.get("active_todo_title"),
            ui_state.get("todo_filter_status"),
            ui_state.get("selected_category_id"),
            ui_state.get("calendar_view_mode"),
            ui_state.get("calendar_selected_date"),
            ui_state.get("calendar_filter_type"),
            ui_state.get("active_event_id"),
            repr(ui_state.get("active_states")),
        )

    def refresh(self) -> bool:
        """Refresh runtime and UI state from the backend."""
        try:
            runtime = self.client.get_runtime_status()
            ui_state = self.client.get_ui_state()
            state_key = self._state_key(runtime, ui_state)
            if state_key != self._last_state_key:
                self._last_interaction_time = time.time()
                self._last_state_key = state_key

            self.runtime = runtime
            self.ui_state = ui_state
            self.connection_status_label.set_text("Backend: connected")
            self._replace_css_classes(
                self.connection_status_label,
                STATUS_CLASSES,
                "status-ok",
            )
            self.view_status_label.set_text(header_view_title(ui_state, runtime))
            self._replace_css_classes(
                self.view_status_label,
                STATUS_CLASSES,
                header_view_status_class(ui_state, runtime),
            )
            self.runtime_status_label.set_text(f"Runtime: {runtime_summary(runtime)}")
            self._replace_css_classes(
                self.runtime_status_label,
                STATUS_CLASSES,
                runtime_status_class(runtime),
            )
            self._sync_model_entry(runtime)
            self._apply_control_state(runtime)
            self._apply_header_state(ui_state)
        except Exception as exc:
            self.connection_status_label.set_text("Backend: unavailable")
            self._replace_css_classes(
                self.connection_status_label,
                STATUS_CLASSES,
                "status-error",
            )
            self.runtime_status_label.set_text("Runtime: error")
            self._replace_css_classes(
                self.runtime_status_label,
                STATUS_CLASSES,
                "status-error",
            )
            self.view_status_label.set_text("Offline")
            self._replace_css_classes(
                self.view_status_label,
                STATUS_CLASSES,
                "status-error",
            )
            self._apply_control_state({})
            self._apply_header_state({})
            self.runtime = offline_runtime_state(exc)
            self._sync_model_entry(self.runtime)
            self.ui_state = {
                "active_view": "idle",
                "status_text": f"Backend unavailable: {exc}",
            }
        self.canvas.queue_draw()
        return True

    def _animate(self) -> bool:
        self._phase = (self._phase + 0.045) % (math.pi * 2)
        now = time.time()
        if now - self._last_blink >= self._blink_interval:
            self._blink_start = now
            self._last_blink = now
            self._blink_interval = 3.0 + ((now * 1000) % 2000) / 1000
        self.canvas.queue_draw()
        return True

    def _blink_scale(self) -> float:
        if self._blink_start <= 0:
            return 1.0
        elapsed = time.time() - self._blink_start
        if elapsed >= 0.15:
            self._blink_start = 0
            return 1.0
        triangle = 1.0 - abs(2 * (elapsed / 0.15) - 1.0)
        smooth = triangle * triangle * (3 - 2 * triangle)
        return 1.0 - 0.95 * smooth

    def _draw(self, _area: Any, cr: Any, width: int, height: int) -> None:
        self._paint_background(cr, width, height)
        self._draw_status_badges(cr, width)
        panel = tool_panel(self.ui_state, self.runtime)
        active_view = self.ui_state.get("active_view", "idle")
        if active_view == "idle":
            self._draw_face(cr, width, height, surface_accent(self.ui_state, self.runtime))
            if panel.summary:
                summary_lines = self._draw_wrapped_centered_text(
                    cr,
                    panel.summary,
                    width / 2,
                    height * 0.82,
                    width * 0.8,
                    24,
                    2,
                )
                detail_y = height * 0.88 + max(0, summary_lines - 1) * 28
            else:
                detail_y = height * 0.9
            self._draw_detail_lines(cr, panel.detail_lines, width, detail_y, 18)
        else:
            self._draw_adaptive_view(cr, width, height, str(active_view), panel)

    def _paint_background(self, cr: Any, width: int, height: int) -> None:
        accent = surface_accent(self.ui_state, self.runtime)
        cr.set_source_rgb(0.102, 0.102, 0.102)
        cr.paint()
        cr.set_source_rgba(*accent, 0.18)
        cr.rectangle(0, 0, max(6, width * 0.01), height)
        cr.fill()
        cr.set_source_rgba(*accent, 0.08)
        cr.rectangle(0, 0, width, max(4, height * 0.012))
        cr.fill()

    def _draw_face(
        self,
        cr: Any,
        width: int,
        height: int,
        accent: tuple[float, float, float],
    ) -> None:
        elapsed = time.time() - self._last_interaction_time
        sleepiness = sleepiness_for_elapsed(
            elapsed,
            happy_seconds=self._happy_seconds,
            neutral_seconds=self._neutral_seconds,
            sleepy_seconds=self._sleepy_seconds,
        )
        geometry = face_geometry(
            width=width,
            height=height,
            phase=self._phase,
            sleepiness_level=sleepiness,
            blink_scale=self._blink_scale(),
        )

        cr.set_source_rgb(*accent)
        self._draw_eye(cr, geometry.left_eye)
        self._draw_eye(cr, geometry.right_eye)

        if sleepiness >= 2 and self._blink_start <= 0:
            cr.set_line_width(geometry.line_width)
            cr.set_line_cap(1)
            for eye in (geometry.left_eye, geometry.right_eye):
                cr.move_to(
                    eye.center_x - eye.radius_x * 0.6,
                    eye.center_y + eye.radius_y * 0.3,
                )
                cr.line_to(
                    eye.center_x + eye.radius_x * 0.6,
                    eye.center_y + eye.radius_y * 0.3,
                )
                cr.stroke()

        cr.set_line_width(geometry.line_width)
        cr.set_line_cap(1)
        mouth = geometry.mouth
        if sleepiness >= 3:
            cr.move_to(mouth.center_x - mouth.width / 2, mouth.center_y)
            cr.line_to(mouth.center_x + mouth.width / 2, mouth.center_y)
        else:
            smile_depth = [0.55, 0.42, 0.28][min(sleepiness, 2)]
            cr.move_to(mouth.center_x - mouth.width / 2, mouth.center_y)
            cr.curve_to(
                mouth.center_x - mouth.width * 0.28,
                mouth.center_y + mouth.height * smile_depth,
                mouth.center_x + mouth.width * 0.28,
                mouth.center_y + mouth.height * smile_depth,
                mouth.center_x + mouth.width / 2,
                mouth.center_y,
            )
        cr.stroke()

    def _draw_eye(self, cr: Any, eye: Any) -> None:
        cr.save()
        cr.translate(eye.center_x, eye.center_y)
        cr.scale(eye.radius_x, max(1, eye.radius_y))
        cr.arc(0, 0, 1, 0, math.pi * 2)
        cr.fill()
        cr.restore()

    def _draw_adaptive_view(
        self,
        cr: Any,
        width: int,
        height: int,
        active_view: str,
        panel: ToolPanel,
    ) -> None:
        accent = surface_accent(self.ui_state, self.runtime)
        cr.set_source_rgb(*accent)
        cr.rectangle(width * 0.18, height * 0.28, width * 0.64, 4)
        cr.fill()
        self._draw_centered_text(
            cr,
            panel.title,
            width / 2,
            height * 0.36,
            width * 0.82,
            42,
        )
        summary_lines = self._draw_wrapped_centered_text(
            cr,
            panel.summary,
            width / 2,
            height * 0.49,
            width * 0.82,
            28,
            3,
        )
        summary_bottom = height * 0.49 + max(0, summary_lines - 1) * 34
        if panel.progress is not None:
            progress_y = summary_bottom + 40
            self._draw_progress_bar(cr, width, progress_y, width * 0.56, panel.progress, accent)
            detail_y = progress_y + 64
        else:
            detail_y = summary_bottom + 58
        self._draw_detail_lines(cr, panel.detail_lines, width, detail_y, 22)

    def _draw_status_badges(self, cr: Any, width: int) -> None:
        accent = surface_accent(self.ui_state, self.runtime)
        badge_char_limit = min(44, max(12, int((width - 48) / (13 * 0.55))))
        badges = compact_status_badges(
            status_badges(self.ui_state, self.runtime),
            max_chars=badge_char_limit,
        )
        if not badges:
            return

        x = 24.0
        y = 22.0
        padding_x = 12.0
        badge_height = 28.0
        gap = 8.0
        cr.select_font_face("Sans", 0, 0)
        cr.set_font_size(13)

        for badge in badges:
            extents = cr.text_extents(badge)
            badge_width = extents.width + padding_x * 2
            if x + badge_width > width - 24 and x > 24:
                x = 24.0
                y += badge_height + gap
            cr.set_source_rgba(*status_badge_rgba(badge, accent))
            self._rounded_rect(cr, x, y, badge_width, badge_height, 8)
            cr.fill()
            cr.set_source_rgba(1, 1, 1, 0.82)
            cr.move_to(x + padding_x, y + 18)
            cr.show_text(badge)
            x += badge_width + gap

    def _draw_progress_bar(
        self,
        cr: Any,
        width: int,
        y: float,
        bar_width: float,
        progress: float,
        accent: tuple[float, float, float],
    ) -> None:
        bar_height = max(8, width * 0.012)
        x = (width - bar_width) / 2
        radius = bar_height / 2
        cr.set_source_rgba(1, 1, 1, 0.12)
        self._rounded_rect(cr, x, y, bar_width, bar_height, radius)
        cr.fill()
        cr.set_source_rgb(*accent)
        self._rounded_rect(cr, x, y, bar_width * max(0, min(progress, 1)), bar_height, radius)
        cr.fill()

    def _rounded_rect(
        self,
        cr: Any,
        x: float,
        y: float,
        width: float,
        height: float,
        radius: float,
    ) -> None:
        radius = min(radius, width / 2, height / 2)
        cr.new_sub_path()
        cr.arc(x + width - radius, y + radius, radius, -math.pi / 2, 0)
        cr.arc(x + width - radius, y + height - radius, radius, 0, math.pi / 2)
        cr.arc(x + radius, y + height - radius, radius, math.pi / 2, math.pi)
        cr.arc(x + radius, y + radius, radius, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def _draw_detail_lines(
        self,
        cr: Any,
        lines: tuple[str, ...],
        width: int,
        start_y: float,
        font_size: int,
    ) -> None:
        max_chars = max(8, int((width * 0.74) / max(font_size * 0.58, 1)))
        display_lines = wrapped_detail_lines(
            lines,
            max_chars=max_chars,
            max_lines_per_detail=2,
            max_total_lines=6,
        )
        for index, line in enumerate(display_lines):
            self._draw_centered_text(
                cr,
                line,
                width / 2,
                start_y + index * font_size * 1.55,
                width * 0.74,
                font_size,
            )

    def _draw_centered_text(
        self,
        cr: Any,
        text: str,
        x: float,
        y: float,
        max_width: float,
        font_size: int,
    ) -> None:
        if not text:
            return
        display_text = text
        cr.select_font_face("Sans", 0, 0)
        cr.set_font_size(font_size)
        extents = cr.text_extents(display_text)
        while extents.width > max_width and len(display_text) > 4:
            display_text = display_text[:-4] + "..."
            extents = cr.text_extents(display_text)
        cr.set_source_rgb(0.878, 0.878, 0.878)
        cr.move_to(x - extents.width / 2, y)
        cr.show_text(display_text)

    def _draw_wrapped_centered_text(
        self,
        cr: Any,
        text: str,
        x: float,
        y: float,
        max_width: float,
        font_size: int,
        max_lines: int,
    ) -> int:
        max_chars = max(8, int(max_width / max(font_size * 0.58, 1)))
        lines = wrapped_text_lines(text, max_chars=max_chars, max_lines=max_lines)
        for index, line in enumerate(lines):
            self._draw_centered_text(
                cr,
                line,
                x,
                y + index * font_size * 1.35,
                max_width,
                font_size,
            )
        return len(lines)

    def present(self) -> None:
        """Present the GTK window."""
        self.window.present()
