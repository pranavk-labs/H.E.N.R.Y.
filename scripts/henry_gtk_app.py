#!/usr/bin/env python
"""Launch the GTK HENRY app."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

env_file = project_root / ".env.local"
if not env_file.exists():
    env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=False)

from app.gtk_app import run_gtk_app


if __name__ == "__main__":
    raise SystemExit(run_gtk_app())
