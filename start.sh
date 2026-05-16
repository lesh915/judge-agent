#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_PORT=${BACKEND_PORT:-19001}
FRONTEND_PORT=${FRONTEND_PORT:-29173}
LOG_DIR="$SCRIPT_DIR/.logs"

mkdir -p "$LOG_DIR"

echo "[start] Backend  → http://localhost:$BACKEND_PORT"
echo "[start] Frontend → http://localhost:$FRONTEND_PORT"

# Backend
BACKEND_PORT=$BACKEND_PORT python -m uvicorn judgeagent.backend.api:app \
  --reload --host 0.0.0.0 --port "$BACKEND_PORT" \
  > "$LOG_DIR/backend.log" 2>&1 &
echo $! > "$LOG_DIR/backend.pid"

# Frontend
cd "$SCRIPT_DIR/judgeagent/frontend/app"
npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
echo $! > "$LOG_DIR/frontend.pid"
cd "$SCRIPT_DIR"

echo "[start] PIDs saved to .logs/. Run ./stop.sh to stop."
