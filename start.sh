#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Vocabulary Pro – VPS start/restart script
# Usage:  ./start.sh
# Stops any running instance, then launches a fresh one in the background.
# Starts both the FastAPI server (uvicorn) and the APScheduler process.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/vocab_pro.pid"
SCHED_PID_FILE="$SCRIPT_DIR/scheduler.pid"
LOG_FILE="$SCRIPT_DIR/logs/startup.log"
SCHED_LOG_FILE="$SCRIPT_DIR/logs/scheduler.log"
PORT="${PORT:-8000}"

cd "$SCRIPT_DIR"

# ── Stop existing FastAPI instance ────────────────────────────────────────────
if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping existing FastAPI process (PID $OLD_PID)…"
        kill "$OLD_PID"
        sleep 2
    fi
    rm -f "$PID_FILE"
fi

# ── Stop existing scheduler instance ─────────────────────────────────────────
if [[ -f "$SCHED_PID_FILE" ]]; then
    OLD_SCHED_PID=$(cat "$SCHED_PID_FILE")
    if kill -0 "$OLD_SCHED_PID" 2>/dev/null; then
        echo "Stopping existing scheduler process (PID $OLD_SCHED_PID)…"
        kill "$OLD_SCHED_PID"
        sleep 1
    fi
    rm -f "$SCHED_PID_FILE"
fi

# ── Activate venv ─────────────────────────────────────────────────────────────
source "$SCRIPT_DIR/venv/bin/activate"

# ── Start FastAPI server ───────────────────────────────────────────────────────
echo "Starting Vocabulary Pro (FastAPI) on port $PORT…"
mkdir -p "$SCRIPT_DIR/logs"
nohup venv/bin/python -m uvicorn main:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers 1 \
    >> "$LOG_FILE" 2>&1 &

NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"
echo "  FastAPI started (PID $NEW_PID). Logs: $LOG_FILE"

# ── Wait briefly so FastAPI is up before scheduler tries to connect ────────────
sleep 3

# ── Start scheduler ───────────────────────────────────────────────────────────
echo "Starting scheduler (Asia/Dhaka – 08:00, 12:00, 18:00, 20:00)…"
nohup venv/bin/python scheduler.py \
    >> "$SCHED_LOG_FILE" 2>&1 &

SCHED_PID=$!
echo "$SCHED_PID" > "$SCHED_PID_FILE"
echo "  Scheduler started (PID $SCHED_PID). Logs: $SCHED_LOG_FILE"

echo ""
echo "Health check: curl http://localhost:$PORT/health"
echo "Status:       curl http://localhost:$PORT/status"
