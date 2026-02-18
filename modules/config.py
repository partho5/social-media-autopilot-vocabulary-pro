"""
Configuration module – loads and validates all environment variables.
All other modules import from here instead of reading os.environ directly.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (works regardless of CWD)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


def _require(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        raise EnvironmentError(f"Required environment variable '{key}' is missing or empty.")
    return val


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


# ─── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY: str = _require("OPENAI_API_KEY")

# ─── Anthropic (Claude) ────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = _optional("ANTHROPIC_API_KEY")

# ─── Text generation provider: "gpt" | "claude"  ← change here to switch ──────
TEXT_GENERATION_PROVIDER: str = _optional("TEXT_GENERATION_PROVIDER", "gpt").lower()

# ─── Replicate ─────────────────────────────────────────────────────────────────
REPLICATE_API_TOKEN: str = _require("REPLICATE_API_TOKEN")

# ─── Facebook ──────────────────────────────────────────────────────────────────
FB_APP_ID: str = _require("FB_APP_ID")
FB_APP_SECRET: str = _require("FB_APP_SECRET")
FB_PAGE_ID: str = _require("FB_PAGE_ID")

# ─── Paths ─────────────────────────────────────────────────────────────────────
WORDS_FILE: Path = _ROOT / "data" / "words.txt"
HASHTAGS_FILE: Path = _ROOT / "data" / "hashtags.txt"
STATE_FILE: Path = _ROOT / "data" / "state.json"
TOKEN_FILE: Path = _ROOT / "data" / "fb_tokens.json"
OUTPUT_DIR: Path = _ROOT / "output"
FONTS_DIR: Path = _ROOT / "fonts"
LOGS_DIR: Path = _ROOT / "logs"

# ─── App settings ──────────────────────────────────────────────────────────────
WEBHOOK_SECRET: str = _optional("WEBHOOK_SECRET")
LOG_LEVEL: str = _optional("LOG_LEVEL", "INFO").upper()
PORT: int = int(_optional("PORT", "8000"))

# Ensure directories exist
for _d in [OUTPUT_DIR, FONTS_DIR, LOGS_DIR, _ROOT / "data"]:
    _d.mkdir(parents=True, exist_ok=True)
