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
    filtered_path = [
        path
        for path in sys.path
        if Path(path or ".").resolve() != PROJECT_ROOT
    ]
    monkeypatch.setattr(sys, "path", filtered_path)

    spec = importlib.util.spec_from_file_location("henry_gtk_launcher_test", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    assert str(PROJECT_ROOT) in sys.path
