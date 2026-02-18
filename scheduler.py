"""
Scheduler – triggers the word-of-the-day workflow at fixed times (Asia/Dhaka).

Posting times (24 h, Asia/Dhaka): 08:00, 12:00, 18:00, 20:00

Runs as a separate background process started by start.sh.
It calls the FastAPI /webhook/trigger endpoint over localhost so the workflow
logic stays in one place and authentication still goes through the secret check.
"""

import logging
import logging.handlers
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── .env must be loaded before reading PORT / WEBHOOK_SECRET ──────────────────
_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env")

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# ── Settings ──────────────────────────────────────────────────────────────────
TIMEZONE = "Asia/Dhaka"
POSTING_TIMES = ["6", "8", "10", "16", "20", "23"]   # hours (24 h clock) in Asia/Dhaka

_PORT = int(os.getenv("PORT", "8002"))
_WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
_TRIGGER_URL = f"http://localhost:{_PORT}/webhook/trigger"

# ── Logging ───────────────────────────────────────────────────────────────────
_LOG_FILE = _ROOT / "logs" / "scheduler.log"
_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            _LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("scheduler")


# ── Job ───────────────────────────────────────────────────────────────────────

def _trigger_workflow() -> None:
    """Called by APScheduler at each scheduled time."""
    headers: dict[str, str] = {}
    if _WEBHOOK_SECRET:
        headers["X-Webhook-Secret"] = _WEBHOOK_SECRET

    logger.info("Firing workflow trigger → %s", _TRIGGER_URL)
    try:
        resp = requests.post(_TRIGGER_URL, headers=headers, timeout=300)
        data = resp.json()
        if resp.status_code == 200 and data.get("success"):
            logger.info(
                "Workflow OK – word=%s, post_id=%s, elapsed=%.1fs",
                data.get("word"),
                data.get("post_id"),
                data.get("elapsed_seconds", 0),
            )
        else:
            logger.error(
                "Workflow returned failure (HTTP %s): %s", resp.status_code, data
            )
    except requests.exceptions.ConnectionError:
        logger.error(
            "Could not connect to FastAPI server at %s. Is it running?", _TRIGGER_URL
        )
    except Exception as e:
        logger.exception("Unexpected error triggering workflow: %s", e)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    hour_str = ",".join(POSTING_TIMES)
    logger.info(
        "Scheduler starting – timezone=%s, posting hours=%s → %s",
        TIMEZONE,
        POSTING_TIMES,
        _TRIGGER_URL,
    )

    scheduler = BlockingScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        _trigger_workflow,
        trigger=CronTrigger(hour=hour_str, minute=0, timezone=TIMEZONE),
        id="word_of_the_day",
        name="Word-of-the-Day trigger",
        misfire_grace_time=300,  # fire up to 5 min late (e.g. if server just restarted)
        coalesce=True,           # run once even if multiple fires were missed
    )

    # Log next scheduled run times
    scheduler.start.__doc__  # trigger lazy init so get_jobs() has next_run_time
    logger.info("Scheduled at hours %s (%s). Waiting…", POSTING_TIMES, TIMEZONE)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
