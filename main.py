"""
Vocabulary Pro – FastAPI entry point.

Endpoints:
  POST /webhook/trigger          – main workflow (called by cron via curl)
  GET  /health                   – liveness check
  GET  /status                   – word tracker + last run info

Cron example (every day at 8 AM):
  0 8 * * * curl -s -X POST http://localhost:${PORT:-8002}/webhook/trigger \
             -H "X-Webhook-Secret: your_secret" >> /var/log/vocab_pro.log 2>&1
"""

import logging
import logging.handlers
import time
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse

from modules.config import LOG_LEVEL, LOGS_DIR, WEBHOOK_SECRET
from modules.word_manager import get_status, selectNextWord
from modules.openai_client import generate_image_prompt, generate_post_text
from modules.replicate_client import generate_image
from modules.image_processor import create_post_image
from modules.facebook_client import post_to_facebook

# ─── Logging ──────────────────────────────────────────────────────────────────
def _setup_logging() -> None:
    fmt = "%(asctime)s [%(levelname)s] %(name)s – %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    log_file = LOGS_DIR / "vocab_pro.log"
    rotating = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    handlers.append(rotating)

    logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format=fmt, handlers=handlers)


_setup_logging()
logger = logging.getLogger(__name__)

# ─── App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Vocabulary Pro – Facebook Autopilot",
    description="Automated word-of-the-day posting to Facebook.",
    version="1.0.0",
)


# ─── Auth helper ─────────────────────────────────────────────────────────────
def _verify_secret(secret: str) -> None:
    if WEBHOOK_SECRET and secret != WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing webhook secret.",
        )


# ─── Workflow ─────────────────────────────────────────────────────────────────
def _run_workflow() -> dict:
    """
    Execute the full word-of-the-day pipeline.
    Returns a result dict. Raises on any unrecoverable error.
    """
    start = time.time()
    steps: list[str] = []

    def log_step(msg: str) -> None:
        logger.info(msg)
        steps.append(msg)

    # Step 1 – Select next word
    log_step("Step 1: Selecting next word…")
    word = selectNextWord()
    if not word:
        raise RuntimeError("selectNextWord() returned empty string.")
    log_step(f"Step 1 done: word='{word}'")

    # Step 2 – Generate Bengali post text
    log_step("Step 2: Generating Bengali post text…")
    post_text = generate_post_text(word)
    if not post_text:
        raise RuntimeError("generate_post_text() returned empty string.")
    log_step(f"Step 2 done: {len(post_text)} chars")

    # Step 3 – Generate image prompt
    log_step("Step 3: Generating image prompt…")
    image_prompt = generate_image_prompt(post_text, word)
    if not image_prompt:
        raise RuntimeError("generate_image_prompt() returned empty string.")
    log_step(f"Step 3 done: prompt length={len(image_prompt)}")

    # Step 4 – Generate image via Gemini
    log_step("Step 4: Generating image with Gemini…")
    pil_image = generate_image(image_prompt)
    if pil_image is None:
        raise RuntimeError("generate_image() returned None.")
    log_step(f"Step 4 done: {pil_image.width}×{pil_image.height}")

    # Step 5 – Compose post image
    log_step("Step 5: Composing post image…")
    image_path: Path = create_post_image(pil_image, word)
    if not image_path.exists():
        raise RuntimeError(f"Post image not found after creation: {image_path}")
    log_step(f"Step 5 done: {image_path.name}")

    # Step 6 – Post to Facebook
    log_step("Step 6: Posting to Facebook…")
    post_id = post_to_facebook(post_text, image_path)
    log_step(f"Step 6 done: post_id={post_id}")

    elapsed = round(time.time() - start, 2)
    logger.info("Workflow complete in %.2fs. Word: '%s', FB post: %s", elapsed, word, post_id)

    return {
        "success": True,
        "word": word,
        "post_id": post_id,
        "image_file": image_path.name,
        "elapsed_seconds": elapsed,
        "steps": steps,
    }


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.post("/webhook/trigger", summary="Trigger the word-of-the-day workflow")
async def trigger(
    x_webhook_secret: str = Header(default="", alias="X-Webhook-Secret"),
) -> JSONResponse:
    _verify_secret(x_webhook_secret)
    logger.info("Webhook trigger received.")
    try:
        result = _run_workflow()
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        logger.exception("Workflow failed: %s", e)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@app.get("/health", summary="Liveness check")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/status", summary="Current word tracker state")
async def word_status() -> JSONResponse:
    try:
        info = get_status()
        return JSONResponse({"status": "ok", **info})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})


# ─── Dev runner ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    from modules.config import PORT

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
