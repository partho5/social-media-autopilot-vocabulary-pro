#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Facebook Comment Auto-Reply Server – Production Startup Script
# Usage:  ./start_comment_reply_prod.sh
#
# This script:
#   1. Loads configuration from .env
#   2. Validates all required variables
#   3. Starts the server with production settings
#   4. Logs to logs/comment_reply.log
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/comment_reply.pid"
LOG_FILE="$SCRIPT_DIR/logs/comment_reply.log"
CONFIG_FILE="$SCRIPT_DIR/.env"

cd "$SCRIPT_DIR"

# ── Load configuration from main .env ─────────────────────────────────────────
echo "Loading configuration from .env…"
set -a
source "$SCRIPT_DIR/.env"
set +a

# ── Validate required variables ───────────────────────────────────────────────
echo ""
echo "Validating configuration…"

if [[ -z "${OPENAI_API_KEY:-}" ]] || [[ "$OPENAI_API_KEY" == "sk-your-actual-key-here" ]]; then
    echo "❌ Error: OPENAI_API_KEY not set or is placeholder"
    echo "   Set it in: $CONFIG_FILE"
    exit 1
fi
echo "  ✅ OPENAI_API_KEY is set"

if [[ ! -f "$SCRIPT_DIR/data/fb_tokens.json" ]]; then
    echo "❌ Error: Token file not found: $SCRIPT_DIR/data/fb_tokens.json"
    echo "   Run the main project first to initialize tokens:"
    echo "   ./start.sh"
    exit 1
fi
echo "  ✅ Token file exists"

if [[ -n "${FB_WEBHOOK_SECRET:-}" ]] && [[ "$FB_WEBHOOK_SECRET" == "your-facebook-app-secret-here" ]]; then
    echo "⚠️  Warning: FB_WEBHOOK_SECRET is placeholder (validation disabled)"
else
    echo "  ✅ Webhook security configured"
fi

# ── Stop existing instance ────────────────────────────────────────────────────
if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "  Stopping existing server (PID $OLD_PID)…"
        kill "$OLD_PID"
        sleep 2
    fi
    rm -f "$PID_FILE"
fi

# ── Activate venv ─────────────────────────────────────────────────────────────
echo "Activating virtual environment…"
source "$SCRIPT_DIR/venv/bin/activate"

# ── Check dependencies ────────────────────────────────────────────────────────
echo "Checking dependencies…"
if ! python -c "import flask" 2>/dev/null; then
    echo "  Installing Flask…"
    pip install flask -q
fi
if ! python -c "import openai" 2>/dev/null; then
    echo "  Installing OpenAI…"
    pip install openai -q
fi
if ! python -c "import requests" 2>/dev/null; then
    echo "  Installing requests…"
    pip install requests -q
fi
if ! python -c "import dotenv" 2>/dev/null; then
    echo "  Installing python-dotenv…"
    pip install python-dotenv -q
fi
echo "  ✅ All dependencies installed"

# ── Create logs directory ─────────────────────────────────────────────────────
mkdir -p "$SCRIPT_DIR/logs"

# ── Start server ──────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Starting FB Comment Auto-Reply server (Production Mode)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Port:        ${FB_REPLY_PORT:-8003}"
echo "Config:      .env (Comment reply settings)"
echo "Logs:        $LOG_FILE"
echo "PID file:    $PID_FILE"
echo ""

nohup venv/bin/python -m modules.fb_comment_auto_reply \
    >> "$LOG_FILE" 2>&1 &

NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

# Wait a moment for the server to start
sleep 2

# Check if process is still running
if ! kill -0 "$NEW_PID" 2>/dev/null; then
    echo ""
    echo "❌ Server failed to start. Check logs:"
    tail -20 "$LOG_FILE"
    exit 1
fi

echo "✅ Server started successfully (PID $NEW_PID)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ENDPOINTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
PORT="${FB_REPLY_PORT:-8003}"
echo "Health:   curl http://localhost:$PORT/health"
echo "Webhook:  POST http://localhost:$PORT/webhook/comment"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "NEXT STEPS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Test health:   curl http://localhost:$PORT/health"
echo "2. Send webhook:  See WEBHOOK_EXAMPLE below"
echo "3. Watch logs:    tail -f $LOG_FILE"
echo "4. Stop server:   kill $NEW_PID"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "WEBHOOK_EXAMPLE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo 'curl -X POST "http://localhost:'"$PORT"'/webhook/comment" \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{
    "comment_id": "YOUR_COMMENT_ID",
    "post_id": "YOUR_POST_ID"
}'"'"
echo ""
