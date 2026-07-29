"""GTK/libadwaita main window."""

from __future__ import annotations

import logging
from typing import Any, Callable

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

        self.status_label = Gtk.Label(label="Voice runtime: unknown")
        self.status_label.add_css_class("runtime-status")
        self.footer_status_label = Gtk.Label(label="Voice runtime: unknown")
        self.transcript_label = Gtk.Label(label="")
        self.transcript_label.set_wrap(True)
        self.transcript_label.add_css_class("transcript")
        self.model_label = Gtk.Label(label="Model: unknown")
        self.connection_label = Gtk.Label(label="Backend: checking")

        self._install_css()
        self._build()
        self.refresh()
        GLib.timeout_add_seconds(2, self.refresh)

    def _install_css(self) -> None:
        Gtk = self.Gtk
        Gdk = self.Gdk

        css = b"""
        window {
            background: #101315;
            color: #f2f4f5;
        }
        .nav-rail {
            background: #171b1f;
            border-right: 1px solid #2a3137;
            padding: 10px;
        }
        .assistant-name {
            font-size: 54px;
            font-weight: 700;
            letter-spacing: 0;
        }
        .runtime-status {
            color: #87d4ff;
            font-size: 18px;
        }
        .transcript {
            color: #c8d0d5;
            font-size: 16px;
        }
        .side-panel {
            background: #171b1f;
            border-left: 1px solid #2a3137;
            padding: 16px;
        }
        .status-strip {
            background: #0c0f11;
            border-top: 1px solid #2a3137;
            padding: 8px 12px;
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
        title = Adw.WindowTitle(title="H.E.N.R.Y.", subtitle="Desk assistant")
        toolbar.set_title_widget(title)
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

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(toolbar)
        root.append(self._build_body())
        root.append(self._build_status_strip())
        self.window.set_content(root)

    def _build_body(self) -> Any:
        Gtk = self.Gtk

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        body.set_vexpand(True)
        body.append(self._build_nav())
        body.append(self._build_center())
        body.append(self._build_panel())
        return body

    def _build_nav(self) -> Any:
        Gtk = self.Gtk

        nav = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        nav.add_css_class("nav-rail")
        for label in ["Face", "Timer", "Todos", "Ideas", "Calendar"]:
            button = Gtk.Button(label=label)
            button.set_hexpand(False)
            nav.append(button)
        return nav

    def _build_center(self) -> Any:
        Gtk = self.Gtk

        center = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        center.set_hexpand(True)
        center.set_vexpand(True)
        center.set_margin_top(40)
        center.set_margin_bottom(40)
        center.set_margin_start(32)
        center.set_margin_end(32)

        assistant_name = Gtk.Label(label="H.E.N.R.Y.")
        assistant_name.add_css_class("assistant-name")
        center.append(assistant_name)
        center.append(self.status_label)
        center.append(self.transcript_label)
        return center

    def _build_panel(self) -> Any:
        Gtk = self.Gtk

        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        panel.add_css_class("side-panel")
        panel.set_size_request(280, -1)
        panel.append(Gtk.Label(label="Runtime"))
        panel.append(self.model_label)
        panel.append(Gtk.Label(label="Mode: legacy"))
        return panel

    def _build_status_strip(self) -> Any:
        Gtk = self.Gtk

        strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        strip.add_css_class("status-strip")
        strip.append(self.connection_label)
        strip.append(self.footer_status_label)
        return strip

    def _run_action(self, action: Callable[[], dict[str, Any]]) -> None:
        try:
            action()
            self.refresh()
        except Exception as exc:
            logger.error("GTK runtime action failed: %s", exc, exc_info=True)
            self.status_label.set_text(f"Voice runtime error: {exc}")

    def refresh(self) -> bool:
        """Refresh runtime and UI state from the backend."""
        try:
            runtime = self.client.get_runtime_status()
            ui_state = self.client.get_ui_state()
            runtime_state = runtime.get("state", "unknown")
            self.connection_label.set_text("Backend: connected")
            self.status_label.set_text(f"Voice runtime: {runtime_state}")
            self.footer_status_label.set_text(f"Voice runtime: {runtime_state}")
            self.model_label.set_text(f"Model: {runtime.get('model', 'unknown')}")
            self.transcript_label.set_text(str(ui_state.get("status_text", "")))
        except Exception as exc:
            self.connection_label.set_text("Backend: unavailable")
            self.status_label.set_text(f"Voice runtime error: {exc}")
            self.footer_status_label.set_text("Voice runtime: error")
        return True

    def present(self) -> None:
        """Present the GTK window."""
        self.window.present()
