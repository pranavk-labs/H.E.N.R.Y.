#!/usr/bin/env bash
set -euo pipefail

# Run Phase 2 focused tests (productivity API + tools/screen manager)

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

poetry run pytest \
  tests/test_productivity_api.py \
  tests/test_tools_and_screen_manager.py


