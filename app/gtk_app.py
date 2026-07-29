"""GTK entrypoint for HENRY."""

from __future__ import annotations

import os
from typing import Optional

from app.gtk_ui.main_window import HenryGtkWindow, require_gtk
from app.gtk_ui.runtime_client import RuntimeClient


def run_gtk_app(api_base_url: Optional[str] = None) -> int:
    """Run the GTK application."""
    Adw, _Gdk, _GLib, _Gtk = require_gtk()
    base_url = api_base_url or os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    app = Adw.Application(application_id="dev.henry.Assistant")

    def on_activate(application):
        window = HenryGtkWindow(application, RuntimeClient(base_url))
        window.present()

    app.connect("activate", on_activate)
    return app.run(None)
