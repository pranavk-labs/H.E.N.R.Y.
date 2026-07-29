"""GTK/libadwaita main window."""

from __future__ import annotations

import logging
import math
import os
import time
from typing import Any, Callable

from app.gtk_ui.face_view import face_geometry, sleepiness_for_elapsed, view_summary
from app.gtk_ui.runtime_client import RuntimeClient

logger = logging.getLogger(__name__)


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

        self.runtime_status_label = Gtk.Label(label="Runtime: unknown")
        self.runtime_status_label.add_css_class("runtime-pill")
        self.connection_status_label = Gtk.Label(label="Backend: checking")
        self.connection_status_label.add_css_class("connection-label")

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
        .connection-label {
            color: #50c878;
            font-size: 13px;
            margin-right: 12px;
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
        action: Callable[[], dict[str, Any]],
    ) -> Any:
        button = self.Gtk.Button.new_from_icon_name(icon_name)
        button.set_tooltip_text(tooltip)
        button.connect("clicked", lambda _button: self._run_action(action))
        return button

    def _build(self) -> None:
        Gtk = self.Gtk
        Adw = self.Adw

        toolbar = Adw.HeaderBar()
        toolbar.set_title_widget(Adw.WindowTitle(title="H.E.N.R.Y.", subtitle=""))
        toolbar.pack_start(
            self._icon_button(
                "media-playback-start-symbolic",
                "Start voice runtime",
                self.client.start_runtime,
            )
        )
        toolbar.pack_start(
            self._icon_button(
                "media-playback-stop-symbolic",
                "Stop voice runtime",
                self.client.stop_runtime,
            )
        )
        toolbar.pack_end(
            self._icon_button(
                "edit-clear-symbolic",
                "Unload model",
                self.client.unload_model,
            )
        )
        toolbar.pack_end(
            self._icon_button(
                "view-refresh-symbolic",
                "Preload model",
                self.client.preload_model,
            )
        )
        toolbar.pack_end(self.runtime_status_label)
        toolbar.pack_end(self.connection_status_label)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(toolbar)
        root.append(self.canvas)
        self.window.set_content(root)

    def _run_action(self, action: Callable[[], dict[str, Any]]) -> None:
        try:
            action()
            self.refresh()
        except Exception as exc:
            logger.error("GTK runtime action failed: %s", exc, exc_info=True)
            self.runtime_status_label.set_text(f"Runtime error: {exc}")

    def _state_key(
        self,
        runtime: dict[str, Any],
        ui_state: dict[str, Any],
    ) -> tuple[Any, ...]:
        return (
            runtime.get("state"),
            runtime.get("model"),
            ui_state.get("active_view"),
            ui_state.get("status_text"),
            repr(ui_state.get("timer_state")),
            repr(ui_state.get("idea_view")),
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
            self.runtime_status_label.set_text(
                f"Runtime: {runtime.get('state', 'unknown')}"
            )
        except Exception as exc:
            self.connection_status_label.set_text("Backend: unavailable")
            self.runtime_status_label.set_text("Runtime: error")
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
        self._paint_background(cr)
        summary = view_summary(self.ui_state, self.runtime)
        active_view = self.ui_state.get("active_view", "idle")
        if active_view == "idle":
            self._draw_face(cr, width, height)
            if summary:
                self._draw_centered_text(cr, summary, width / 2, height * 0.86, width * 0.8, 24)
        else:
            self._draw_adaptive_view(cr, width, height, str(active_view), summary)

    def _paint_background(self, cr: Any) -> None:
        cr.set_source_rgb(0.102, 0.102, 0.102)
        cr.paint()

    def _draw_face(self, cr: Any, width: int, height: int) -> None:
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

        cr.set_source_rgb(0.878, 0.878, 0.878)
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
        summary: str,
    ) -> None:
        labels = {
            "pomodoro": "Pomodoro",
            "ideas": "Idea",
            "todo_list": "Todos",
            "calendar": "Calendar",
        }
        self._draw_centered_text(
            cr,
            labels.get(active_view, active_view.replace("_", " ").title()),
            width / 2,
            height * 0.36,
            width * 0.82,
            42,
        )
        self._draw_centered_text(
            cr,
            summary,
            width / 2,
            height * 0.52,
            width * 0.82,
            28,
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

    def present(self) -> None:
        """Present the GTK window."""
        self.window.present()
