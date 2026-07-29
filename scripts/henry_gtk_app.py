#!/usr/bin/env python
"""Launch the GTK HENRY app."""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.gtk_app import run_gtk_app


if __name__ == "__main__":
    raise SystemExit(run_gtk_app())
