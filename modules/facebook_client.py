"""
Facebook Graph API client with automatic token lifecycle management.

Token flow:
  1. User provides a short-lived User Access Token in .env
  2. On first run we exchange it for a Long-Lived User Token (60 days)
  3. We exchange that for a Page Access Token (never expires when derived
     from a long-lived user token + app credentials)
  4. Before every post we validate the token. If it's within the refresh
     window (or already expired) we refresh it automatically.
  5. All tokens are stored encrypted in data/fb_tokens.json.

Developer only has to provide the initial short-lived token once.
"""

import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

import requests

from modules.config import (
    FB_APP_ID,
    FB_APP_SECRET,
    FB_PAGE_ID,
    TOKEN_FILE,
)

logger = logging.getLogger(__name__)

_GRAPH = "https://graph.facebook.com/v21.0"
_TOKEN_REFRESH_DAYS_BEFORE_EXPIRY = 10  # refresh when <10 days remain

# ─── Token persistence ────────────────────────────────────────────────────────

def _load_tokens() -> dict:
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Token file unreadable (%s). Starting fresh.", e)
    return {}


def _save_tokens(tokens: dict) -> None:
    dir_ = TOKEN_FILE.parent
    fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)
    os.replace(tmp, TOKEN_FILE)
    logger.debug("Token file updated.")


# ─── Graph API helpers ────────────────────────────────────────────────────────

def _graph_get(path: str, params: dict) -> dict:
    url = f"{_GRAPH}/{path.lstrip('/')}"
    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Graph API error: {data['error']}")
    return data


def _graph_post(path: str, data: dict, files: Optional[dict] = None) -> dict:
    url = f"{_GRAPH}/{path.lstrip('/')}"
    resp = requests.post(url, data=data, files=files, timeout=60)
    result = resp.json()
    if "error" in result:
        raise RuntimeError(f"Graph API error: {result['error']}")
    return result


# ─── Token exchange ───────────────────────────────────────────────────────────

def _exchange_for_long_lived_user_token(short_token: str) -> dict:
    """Exchange a short-lived user token for a long-lived one (60 days)."""
    logger.info("Exchanging short-lived token for long-lived user token…")
    data = _graph_get("oauth/access_token", {
        "grant_type": "fb_exchange_token",
        "client_id": FB_APP_ID,
        "client_secret": FB_APP_SECRET,
        "fb_exchange_token": short_token,
    })
    expires_in = data.get("expires_in", 60 * 24 * 3600)  # default ~60 days
    return {
        "token": data["access_token"],
        "expires_at": int(time.time()) + int(expires_in),
        "type": "long_lived_user",
    }


def _get_page_access_token(long_lived_user_token: str) -> dict:
    """
    Get a Page Access Token from a long-lived user token.
    Page tokens obtained this way do NOT expire (no expiry field in response).
    """
    logger.info("Fetching Page Access Token for page %s…", FB_PAGE_ID)
    data = _graph_get(FB_PAGE_ID, {
        "fields": "access_token,name",
        "access_token": long_lived_user_token,
    })
    page_name = data.get("name", "unknown page")
    logger.info("Got page token for: %s", page_name)
    return {
        "token": data["access_token"],
        "expires_at": None,   # None = never expires
        "type": "page",
        "page_name": page_name,
    }


def _debug_token(token: str) -> dict:
    """Inspect a token via /debug_token to get expiry and validity."""
    data = _graph_get("debug_token", {
        "input_token": token,
        "access_token": f"{FB_APP_ID}|{FB_APP_SECRET}",
    })
    return data.get("data", {})


# ─── Token management public API ─────────────────────────────────────────────

def _is_token_expiring_soon(expires_at: Optional[int]) -> bool:
    if expires_at is None:
        return False  # never expires
    seconds_remaining = expires_at - time.time()
    return seconds_remaining < (_TOKEN_REFRESH_DAYS_BEFORE_EXPIRY * 24 * 3600)


def _is_token_expired(expires_at: Optional[int]) -> bool:
    if expires_at is None:
        return False
    return time.time() >= expires_at


def bootstrap_tokens(initial_short_token: str) -> dict:
    """
    Full bootstrap: short-lived → long-lived user → page access token.
    Call this on first setup or when the stored tokens are invalid.
    Saves and returns the full token store.
    """
    long_lived = _exchange_for_long_lived_user_token(initial_short_token)
    page = _get_page_access_token(long_lived["token"])

    tokens = {
        "user_token": long_lived,
        "page_token": page,
        "bootstrapped_at": int(time.time()),
    }
    _save_tokens(tokens)
    logger.info(
        "Token bootstrap complete. Page token obtained (never expires). "
        "User token expires: %s",
        time.strftime("%Y-%m-%d", time.localtime(long_lived["expires_at"])),
    )
    return tokens


def _refresh_user_token(tokens: dict) -> dict:
    """Re-exchange the stored long-lived user token for a fresh one."""
    user_token = tokens.get("user_token", {}).get("token")
    if not user_token:
        raise RuntimeError("No user token stored. Re-bootstrap required.")
    logger.info("Refreshing long-lived user token…")
    new_long_lived = _exchange_for_long_lived_user_token(user_token)
    new_page = _get_page_access_token(new_long_lived["token"])
    tokens["user_token"] = new_long_lived
    tokens["page_token"] = new_page
    tokens["last_refresh"] = int(time.time())
    _save_tokens(tokens)
    logger.info("Token refresh complete.")
    return tokens


def ensure_valid_page_token() -> str:
    """
    Return a valid page access token, refreshing if needed.
    Raises RuntimeError if tokens cannot be obtained.
    """
    tokens = _load_tokens()

    # No tokens yet – need initial short-lived token from env
    if not tokens:
        short_token = os.getenv("FB_USER_ACCESS_TOKEN", "").strip()
        if not short_token:
            raise RuntimeError(
                "No Facebook tokens stored and FB_USER_ACCESS_TOKEN env var is empty. "
                "Set it in .env and restart."
            )
        tokens = bootstrap_tokens(short_token)

    user_token_info = tokens.get("user_token", {})
    page_token_info = tokens.get("page_token", {})

    user_expires_at = user_token_info.get("expires_at")

    # Refresh if user token expired or expiring soon
    if _is_token_expired(user_expires_at) or _is_token_expiring_soon(user_expires_at):
        logger.warning("User token is expired or expiring soon. Refreshing…")
        try:
            tokens = _refresh_user_token(tokens)
            page_token_info = tokens["page_token"]
        except Exception as e:
            logger.error("Automatic token refresh failed: %s", e)
            raise RuntimeError(
                f"Token refresh failed. Manual intervention required. Error: {e}"
            ) from e

    page_token = page_token_info.get("token")
    if not page_token:
        raise RuntimeError("No page access token available. Run bootstrap.")

    return page_token


def validate_token_live(token: str) -> bool:
    """Debug-token call to confirm token is valid with Facebook servers."""
    try:
        info = _debug_token(token)
        is_valid = info.get("is_valid", False)
        if not is_valid:
            logger.warning("Token is invalid per Facebook debug_token: %s", info)
        return is_valid
    except Exception as e:
        logger.error("Token validation failed: %s", e)
        return False


# ─── Posting ─────────────────────────────────────────────────────────────────

def _load_hashtags() -> str:
    from modules.config import HASHTAGS_FILE
    if HASHTAGS_FILE.exists():
        with open(HASHTAGS_FILE, "r", encoding="utf-8") as f:
            tags = [line.strip() for line in f if line.strip()]
        return "\n\n" + " ".join(tags)
    logger.warning("Hashtags file not found at %s. Posting without hashtags.", HASHTAGS_FILE)
    return ""


def post_to_facebook(text: str, image_path: Path) -> str:
    """
    Post text + image to the Facebook Page.

    Steps:
    1. Validate/refresh page token
    2. Confirm token with FB debug_token
    3. Upload photo with caption via /PAGE_ID/photos

    Returns the Facebook post ID on success.
    """
    if not text or not text.strip():
        raise ValueError("Post text must be non-empty.")
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # ── Token ──────────────────────────────────────────────────────────────────
    page_token = ensure_valid_page_token()

    if not validate_token_live(page_token):
        raise RuntimeError("Page token is invalid. Check logs and re-bootstrap.")

    # ── Compose message ────────────────────────────────────────────────────────
    hashtags = _load_hashtags()
    full_text = f"{text.strip()}\n{hashtags}".strip()

    # ── Upload photo ───────────────────────────────────────────────────────────
    logger.info("Posting to Facebook Page %s…", FB_PAGE_ID)
    with open(image_path, "rb") as img_file:
        result = _graph_post(
            f"{FB_PAGE_ID}/photos",
            data={
                "message": full_text,
                "access_token": page_token,
            },
            files={"source": (image_path.name, img_file, "image/jpeg")},
        )

    post_id = result.get("post_id") or result.get("id", "unknown")
    logger.info("Posted successfully. Post ID: %s", post_id)
    return post_id
