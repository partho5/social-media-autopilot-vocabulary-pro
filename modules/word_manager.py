"""
Word Manager – tracks the current position in the word list and advances it.

State is persisted in data/state.json so restarts are safe.
Atomic writes (write-then-rename) prevent corruption on crashes.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import List

from modules.config import STATE_FILE, WORDS_FILE

logger = logging.getLogger(__name__)


# ─── Word list ─────────────────────────────────────────────────────────────────

def _load_words() -> List[str]:
    """Load words from data/words.txt (one word per line, # lines are comments)."""
    if not WORDS_FILE.exists():
        raise FileNotFoundError(
            f"Word list not found at {WORDS_FILE}. "
            "Please add your IELTS/GRE word list (one word per line)."
        )
    words = []
    with open(WORDS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                words.append(stripped)
    if not words:
        raise ValueError(f"Word list at {WORDS_FILE} is empty.")
    logger.debug("Loaded %d words from word list.", len(words))
    return words


# ─── State persistence ─────────────────────────────────────────────────────────

def _load_state() -> dict:
    """Load persisted state. Returns default state if file is missing/corrupt."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("State file corrupt or unreadable (%s). Resetting to 0.", e)
    return {"current_index": 0, "total_processed": 0, "last_word": ""}


def _save_state(state: dict) -> None:
    """Atomically save state to disk (write temp + rename)."""
    dir_ = STATE_FILE.parent
    try:
        fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, STATE_FILE)
        logger.debug("State saved: index=%d word='%s'", state["current_index"], state["last_word"])
    except OSError as e:
        logger.error("Failed to save state: %s", e)
        raise


# ─── Public API ────────────────────────────────────────────────────────────────

def selectNextWord() -> str:  # noqa: N802 – name kept as specified in the spec
    """
    Return the next word from the list and advance the index.

    The selection logic is intentionally kept simple (sequential) so it can
    be replaced later with any algorithm – just change this function's body.
    The function always returns a non-empty string.
    """
    words = _load_words()
    state = _load_state()

    index = state.get("current_index", 0) % len(words)
    word = words[index]

    # Advance and wrap around
    next_index = (index + 1) % len(words)
    state["current_index"] = next_index
    state["total_processed"] = state.get("total_processed", 0) + 1
    state["last_word"] = word

    _save_state(state)
    logger.info("Selected word #%d (index %d): '%s'", state["total_processed"], index, word)
    return word


def get_status() -> dict:
    """Return current state info for health/status endpoints."""
    state = _load_state()
    try:
        words = _load_words()
        total_words = len(words)
    except Exception:
        total_words = -1
    return {
        "current_index": state.get("current_index", 0),
        "total_processed": state.get("total_processed", 0),
        "last_word": state.get("last_word", ""),
        "total_words_in_list": total_words,
    }
