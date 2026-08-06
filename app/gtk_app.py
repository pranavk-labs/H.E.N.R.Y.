"""GTK entrypoint for HENRY."""

from __future__ import annotations

import os
from typing import Any, Callable, Optional

from app.gtk_ui.face_view import action_shortcuts
from app.gtk_ui.main_window import HenryGtkWindow, require_gtk
from app.gtk_ui.runtime_client import RuntimeClient


def install_app_actions(app: Any, window: HenryGtkWindow, Gio: Any) -> None:
    """Install app-level actions and keyboard shortcuts for GTK."""
    callbacks: dict[str, Callable[[], None]] = {
        "back": window.go_back,
        "start": window.start_runtime,
        "stop": window.stop_runtime,
        "preload": window.preload_model,
        "unload": window.unload_model,
    }
    shortcuts = action_shortcuts()
    for name, callback in callbacks.items():
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", lambda _action, _parameter, cb=callback: cb())
        app.add_action(action)
        app.set_accels_for_action(f"app.{name}", shortcuts[name])


def run_gtk_app(api_base_url: Optional[str] = None) -> int:
    """Run the GTK application."""
    Adw, _Gdk, _GLib, _Gtk = require_gtk()
    from gi.repository import Gio

    base_url = api_base_url or os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    app = Adw.Application(application_id="dev.henry.Assistant")

    def on_activate(application):
        window = HenryGtkWindow(application, RuntimeClient(base_url))
        install_app_actions(application, window, Gio)
        window.present()

    app.connect("activate", on_activate)
    return app.run(None)
