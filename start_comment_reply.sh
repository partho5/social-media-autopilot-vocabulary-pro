#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Facebook Comment Auto-Reply Server – Standalone startup script
# Usage:  ./start_comment_reply.sh
# Stops any running instance, then launches a fresh one in the background.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/comment_reply.pid"
LOG_FILE="$SCRIPT_DIR/logs/comment_reply.log"

cd "$SCRIPT_DIR"

# ── Stop existing instance ────────────────────────────────────────────────────
if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping existing Comment Reply server (PID $OLD_PID)…"
        kill "$OLD_PID"
        sleep 2
    fi
    rm -f "$PID_FILE"
fi

# ── Load .env ─────────────────────────────────────────────────────────────────
set -a
source "$SCRIPT_DIR/.env"
set +a

# Read port AFTER .env is loaded so FB_REPLY_PORT is available
PORT="${FB_REPLY_PORT:-8003}"

# ── Activate venv ─────────────────────────────────────────────────────────────
source "$SCRIPT_DIR/venv/bin/activate"

# ── Check dependencies ────────────────────────────────────────────────────────
if ! python -c "import flask" 2>/dev/null; then
    echo "Installing Flask dependency…"
    pip install flask -q
fi

# ── Start server ──────────────────────────────────────────────────────────────
echo "Starting FB Comment Auto-Reply server on port $PORT…"
mkdir -p "$SCRIPT_DIR/logs"

# Check if OPENAI_API_KEY is set
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "⚠️  Warning: OPENAI_API_KEY environment variable not set"
    echo "   Export it before running: export OPENAI_API_KEY=sk-..."
fi

nohup venv/bin/python -m modules.fb_comment_auto_reply \
    >> "$LOG_FILE" 2>&1 &

NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"
echo "  Server started (PID $NEW_PID). Logs: $LOG_FILE"

echo ""
echo "Health check: curl http://localhost:$PORT/health"
echo "Webhook URL:  POST http://localhost:$PORT/webhook/comment"
echo ""
echo "Example webhook call:"
echo '  curl -X POST http://localhost:8003/webhook/comment \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '"'"'{"comment_id": "123456789", "post_id": "987654321"}'"'"
