"""Tests for the GTK app launcher path."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_gtk_entrypoint_import_does_not_load_legacy_gui():
    """The GTK entrypoint should import without Tkinter legacy GUI startup."""
    import app.gtk_app as gtk_app

    assert callable(gtk_app.run_gtk_app)


def test_gtk_launcher_adds_project_root_to_path(monkeypatch):
    """Running the script from scripts/ should still find the app package."""
    script_path = PROJECT_ROOT / "scripts" / "henry_gtk_app.py"
    filtered_path = [path for path in sys.path if Path(path or ".").resolve() != PROJECT_ROOT]
    monkeypatch.setattr(sys, "path", filtered_path)
    monkeypatch.setenv("HENRY_GTK_USE_SYSTEM_CONFIG", "1")

    spec = importlib.util.spec_from_file_location("henry_gtk_launcher_test", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    assert str(PROJECT_ROOT) in sys.path


def test_gtk_launcher_uses_app_local_gtk_config(monkeypatch):
    """GTK launch should not inherit unsupported libadwaita user settings."""
    script_path = PROJECT_ROOT / "scripts" / "henry_gtk_app.py"
    monkeypatch.setenv("HENRY_GTK_USE_SYSTEM_CONFIG", "1")
    spec = importlib.util.spec_from_file_location("henry_gtk_launcher_config_test", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    env = {}
    module.configure_gtk_config_home(PROJECT_ROOT, env)

    assert env["XDG_CONFIG_HOME"] == str(PROJECT_ROOT / ".cache" / "gtk-config")


def test_gtk_launcher_configures_libadwaita_color_scheme():
    """GTK startup should set libadwaita color scheme through StyleManager."""
    import app.gtk_app as gtk_app

    class FakeColorScheme:
        FORCE_DARK = "force-dark"

    class FakeStyleManager:
        default = None

        def __init__(self) -> None:
            self.color_scheme = None

        @classmethod
        def get_default(cls):
            cls.default = cls.default or cls()
            return cls.default

        def set_color_scheme(self, color_scheme):
            self.color_scheme = color_scheme

    class FakeAdw:
        ColorScheme = FakeColorScheme
        StyleManager = FakeStyleManager

    gtk_app.configure_color_scheme(FakeAdw)

    assert FakeStyleManager.default is not None
    assert FakeStyleManager.default.color_scheme == "force-dark"
