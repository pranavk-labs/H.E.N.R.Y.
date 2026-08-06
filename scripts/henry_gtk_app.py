#!/usr/bin/env python
"""Launch the GTK HENRY app."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def configure_gtk_config_home(root: Path, environ=None) -> None:
    """Keep GTK4 from inheriting user settings that libadwaita rejects."""
    environ = environ if environ is not None else os.environ
    if environ.get("HENRY_GTK_USE_SYSTEM_CONFIG"):
        return
    environ["XDG_CONFIG_HOME"] = str(root / ".cache" / "gtk-config")


configure_gtk_config_home(project_root)

env_file = project_root / ".env.local"
if not env_file.exists():
    env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=False)

from app.gtk_app import run_gtk_app


if __name__ == "__main__":
    raise SystemExit(run_gtk_app())
