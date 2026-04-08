#!/usr/bin/env bash
# dev.sh — start backend (FastAPI :8000) and frontend (Vite :5173) for local development
# Run from the project root: ./dev.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/backend/venv"
FRONTEND="$SCRIPT_DIR/frontend"

if [ ! -f "$VENV/bin/activate" ]; then
  echo "ERROR: virtual environment not found at $VENV" >&2
  echo "  Create it with: python3 -m venv backend/venv && source backend/venv/bin/activate && pip install -r backend/requirements.txt" >&2
  exit 1
fi

if [ ! -d "$FRONTEND/node_modules" ]; then
  echo "ERROR: node_modules not found — run: cd frontend && npm install" >&2
  exit 1
fi

# Kill both child processes on exit / Ctrl-C
cleanup() {
  echo ""
  echo "Stopping..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting backend  → http://localhost:8000"
source "$VENV/bin/activate"
PYTHONPATH="$SCRIPT_DIR/backend" uvicorn backend.main:app \
  --host 127.0.0.1 --port 8000 --reload \
  --reload-dir "$SCRIPT_DIR/backend" \
  2>&1 | sed 's/^/[backend] /' &
BACKEND_PID=$!

echo "Starting frontend → http://localhost:5173"
cd "$FRONTEND"
npm run dev 2>&1 | sed 's/^/[frontend] /' &
FRONTEND_PID=$!

echo "Both processes running. Press Ctrl-C to stop."
wait "$BACKEND_PID" "$FRONTEND_PID"
