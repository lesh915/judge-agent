#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/.logs"

stop_pid() {
  local name=$1
  local pidfile="$LOG_DIR/$name.pid"
  if [ -f "$pidfile" ]; then
    local pid
    pid=$(cat "$pidfile")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" && echo "[stop] $name (PID $pid) stopped"
    else
      echo "[stop] $name already stopped"
    fi
    rm -f "$pidfile"
  else
    echo "[stop] $name pid file not found"
  fi
}

stop_pid backend
stop_pid frontend

# Fallback: kill by process name
pkill -f "uvicorn judgeagent" 2>/dev/null && echo "[stop] uvicorn cleaned up" || true
pkill -f "vite" 2>/dev/null && echo "[stop] vite cleaned up" || true

echo "[stop] Done."
