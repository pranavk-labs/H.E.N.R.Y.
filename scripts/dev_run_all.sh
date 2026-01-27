#!/usr/bin/env bash
set -euo pipefail

# Convenience script: start backend API and combined H.E.N.R.Y. application.
#
# Usage:
#   bash scripts/dev_run_all.sh [--separate]
#
# By default, starts:
# - FastAPI dev server (for external clients and API access)
# - Combined application (GUI + Voice Loop in one process)
#
# With --separate flag, uses the old approach:
# - FastAPI dev server
# - Separate GUI process
# - Separate voice loop process (if available)
#
# All components run on localhost and assume Poetry is installed.

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Enable debug logging for development
export DEBUG="${DEBUG:-True}"

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
API_BASE_URL="http://${API_HOST}:${API_PORT}"

USE_SEPARATE=false
if [ "${1:-}" = "--separate" ]; then
    USE_SEPARATE=true
fi

echo "Starting H.E.N.R.Y. dev stack..."
echo "Backend: ${API_BASE_URL}"

echo "-> Starting FastAPI dev server..."
poetry run python scripts/dev_server.py &
API_PID=$!

sleep 2

if [ "$USE_SEPARATE" = true ]; then
    # Old approach: separate processes
    echo "-> Starting Phase 3 GUI (henry_gui.py)..."
    API_BASE_URL="${API_BASE_URL}" poetry run python scripts/henry_gui.py &
    GUI_PID=$!
    
    sleep 1
    
    # Start voice loop if it exists
    VOICE_PID=""
    if [ -f "scripts/voice_loop.py" ]; then
        echo "-> Starting voice loop..."
        API_BASE_URL="${API_BASE_URL}" poetry run python scripts/voice_loop.py &
        VOICE_PID=$!
    else
        echo "-> Voice loop script not found, skipping..."
    fi
    
    echo ""
    echo "All components started (separate processes)."
    if [ -n "${VOICE_PID}" ]; then
        echo "PIDs: backend=${API_PID}, gui=${GUI_PID}, voice=${VOICE_PID}"
    else
        echo "PIDs: backend=${API_PID}, gui=${GUI_PID}"
    fi
    echo "Press Ctrl+C to stop all."
    
    # Set up cleanup trap
    cleanup() {
        echo "Stopping..."
        [ -n "${VOICE_PID}" ] && kill ${VOICE_PID} 2>/dev/null || true
        kill ${GUI_PID} ${API_PID} 2>/dev/null || true
        wait
    }
    trap cleanup INT TERM
    
    wait
else
    # New approach: combined application
    echo "-> Starting combined H.E.N.R.Y. application (GUI + Voice Loop)..."
    echo "   Using: henry_app.py"
    echo ""
    echo "Note: API server is running separately for external client access."
    echo "      The combined app includes GUI and voice loop in one process."
    echo ""
    
    API_BASE_URL="${API_BASE_URL}" poetry run python scripts/henry_app.py
    APP_EXIT_CODE=$?
    
    # Cleanup API server when combined app exits
    echo "Stopping API server..."
    kill ${API_PID} 2>/dev/null || true
    wait ${API_PID} 2>/dev/null || true
    
    exit ${APP_EXIT_CODE}
fi


