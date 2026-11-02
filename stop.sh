#!/usr/bin/env bash
# P2P Platform — Stop all services

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$ROOT_DIR/.pids"

echo "Barcha servislarni to'xtatish..."
for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    pid=$(cat "$pidfile")
    name=$(basename "$pidfile" .pid)
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null
        echo "  ✓ $name (PID $pid) to'xtatildi"
    fi
    rm -f "$pidfile"
done
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite --port=5173" 2>/dev/null || true
pkill -f "socat TCP-LISTEN:5174" 2>/dev/null || true
echo "Tayyor."
