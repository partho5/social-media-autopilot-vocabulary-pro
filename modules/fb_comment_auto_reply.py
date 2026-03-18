"""
Facebook Comment Auto-Reply Module
Standalone webhook server that listens for Facebook comments and auto-replies using OpenAI GPT-4o mini.

No dependencies on the main project – reads tokens from data/fb_tokens.json directly.

Usage:
    python -m modules.fb_comment_auto_reply

Environment:
    OPENAI_API_KEY: Required – OpenAI API key for GPT-4o mini
    FB_WEBHOOK_SECRET: Optional – validate webhook signatures (recommended for security)
    FB_REPLY_PORT: Optional – port to run on (default: 8003)
"""

import json
import logging
import os
import hmac
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime

import requests
from openai import OpenAI

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

# Root directory (where data/fb_tokens.json lives)
_ROOT = Path(__file__).resolve().parent.parent

# Load from project's main .env file
from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")

TOKEN_FILE = _ROOT / "data" / "fb_tokens.json"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
WEBHOOK_SECRET = os.getenv("FB_WEBHOOK_SECRET") or os.getenv("FB_APP_SECRET", "")
FB_VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN", "vocab_pro_verify")
FB_REPLY_PORT = int(os.getenv("FB_REPLY_PORT", "8003"))

# ── Reply behaviour defaults (edit here to customise) ─────────────────────────
DEFAULT_SYSTEM_PROMPT = (
    "You are the admin of 'Vocabulary Pro', a Facebook page that helps people learn English vocabulary through engaging daily posts.\n\n"
    "Your goal is to reply to comments in a way that:\n"
    "1. Acknowledges what the commenter said genuinely — show you read their comment\n"
    "2. Connects their comment back to the word or topic in the post\n"
    "3. Encourages them to keep practicing vocabulary — subtly, not pushy\n"
    "4. Feels human, warm, and conversational — not robotic or salesy\n"
    "5. Keeps the reply short (2-3 sentences max)\n\n"
    "Mention and inspire practice vocabulary from 'Vocabulary Pro' app directly when feels natural.\n"
    "Reply in the same language as the commenter.\n"
    "If the reply has more than one sentence, separate sentences with a newline (\\n) where it feels natural."
)
DEFAULT_INCLUDE_PARENT = True   # include parent comment context when replying to a reply
DEFAULT_INCLUDE_POST = True     # include post content for context

# Facebook Graph API version
GRAPH_API = "https://graph.facebook.com/v21.0"

# ──────────────────────────────────────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# TOKEN MANAGEMENT
# ──────────────────────────────────────────────────────────────────────────────


def _load_fb_tokens() -> dict:
    """Load Facebook tokens from data/fb_tokens.json."""
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(f"Token file not found: {TOKEN_FILE}")

    with open(TOKEN_FILE, "r") as f:
        data = json.load(f)

    if "page_token" not in data or "token" not in data["page_token"]:
        raise ValueError("Invalid token file: missing 'page_token.token'")

    return data


def get_page_token() -> str:
    """Get the current page access token."""
    tokens = _load_fb_tokens()
    return tokens["page_token"]["token"]


def get_user_token() -> str:
    """Get the current user access token (if needed)."""
    tokens = _load_fb_tokens()
    if "user_token" not in tokens or "token" not in tokens["user_token"]:
        raise ValueError("Invalid token file: missing 'user_token.token'")
    return tokens["user_token"]["token"]


# ──────────────────────────────────────────────────────────────────────────────
# FACEBOOK API HELPERS
# ──────────────────────────────────────────────────────────────────────────────


def get_comment_details(comment_id: str, fields: str = "id,message,from,created_time") -> dict:
    """Fetch comment details from Facebook Graph API."""
    token = get_page_token()
    url = f"{GRAPH_API}/{comment_id}"
    params = {"fields": fields, "access_token": token}

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def get_post_details(post_id: str, fields: str = "id,story,message,created_time") -> dict:
    """Fetch post details from Facebook Graph API."""
    token = get_page_token()
    url = f"{GRAPH_API}/{post_id}"
    params = {"fields": fields, "access_token": token}

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def get_comment_parent(comment_id: str) -> Optional[dict]:
    """Fetch parent comment if this comment is a reply."""
    token = get_page_token()
    url = f"{GRAPH_API}/{comment_id}"
    params = {
        "fields": "id,message,from,created_time,parent",
        "access_token": token,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if "parent" not in data:
        return None

    parent_id = data["parent"]["id"]
    return get_comment_details(parent_id)


def post_comment_reply(comment_id: str, message: str) -> str:
    """Post a reply to a comment. Returns the new comment ID."""
    token = get_page_token()
    url = f"{GRAPH_API}/{comment_id}/comments"
    data = {"message": message, "access_token": token}

    response = requests.post(url, data=data)
    response.raise_for_status()
    result = response.json()

    return result.get("id", "")


# ──────────────────────────────────────────────────────────────────────────────
# OPENAI INTEGRATION
# ──────────────────────────────────────────────────────────────────────────────


def generate_reply(
    comment_text: str,
    system_prompt: str = "You are a helpful and friendly assistant. Reply briefly and naturally to comments.",
    parent_comment_text: Optional[str] = None,
    post_content: Optional[str] = None,
) -> str:
    """
    Generate a reply using OpenAI GPT-4o mini.

    Args:
        comment_text: The comment to reply to
        system_prompt: Adjustable system prompt (default: friendly assistant)
        parent_comment_text: Parent comment text (if replying to a reply)
        post_content: Post content for context (if include_post_context=True)

    Returns:
        Generated reply text
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    client = OpenAI(api_key=OPENAI_API_KEY)

    # Build context-aware messages
    messages = [{"role": "system", "content": system_prompt}]

    if post_content:
        messages.append({
            "role": "user",
            "content": f"Post context:\n{post_content}\n\n---"
        })

    if parent_comment_text:
        messages.append({
            "role": "user",
            "content": f"Parent comment:\n{parent_comment_text}\n\n---"
        })

    messages.append({
        "role": "user",
        "content": f"Comment to reply to:\n{comment_text}"
    })

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=150,
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()


# ──────────────────────────────────────────────────────────────────────────────
# WEBHOOK VALIDATION
# ──────────────────────────────────────────────────────────────────────────────


def validate_webhook_signature(request_body: bytes, signature: str) -> bool:
    """
    Validate Facebook webhook signature.

    Args:
        request_body: Raw request body bytes
        signature: X-Hub-Signature-SHA256 header value

    Returns:
        True if valid, False otherwise
    """
    if not WEBHOOK_SECRET:
        logger.warning("FB_WEBHOOK_SECRET not set – webhook validation disabled")
        return True

    expected_signature = "sha256=" + hmac.new(
        key=WEBHOOK_SECRET.encode("utf-8"),
        msg=request_body,
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected_signature)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN WEBHOOK HANDLER
# ──────────────────────────────────────────────────────────────────────────────


def handle_comment_webhook(
    event_data: dict,
    system_prompt: str = "You are a helpful and friendly assistant. Reply briefly and naturally to comments.",
    include_parent_comment: bool = True,
    include_post_context: bool = False,
) -> dict:
    """
    Handle a Facebook comment webhook event and generate/post a reply.

    Args:
        event_data: Webhook event data from Facebook (from entry.messaging[0])
        system_prompt: Adjustable LLM system prompt
        include_parent_comment: Include parent comment context if replying to a reply (default: True)
        include_post_context: Include post content context (default: False)

    Returns:
        Dictionary with status, comment_id, reply_id, reply_text, and any errors
    """
    result = {
        "status": "pending",
        "comment_id": None,
        "reply_id": None,
        "reply_text": None,
        "error": None,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        # Extract comment details from event
        if "comment_id" not in event_data:
            raise ValueError("Missing 'comment_id' in webhook data")

        comment_id = event_data["comment_id"]
        result["comment_id"] = comment_id

        logger.info(f"Processing comment: {comment_id}")

        # Use message directly from webhook payload — no extra API call needed
        comment_text = event_data.get("message", "")

        if not comment_text:
            logger.info(f"Comment {comment_id} has no text (sticker/image) – skipping")
            result["status"] = "skipped"
            return result

        logger.info(f"Comment text: {comment_text[:100]}...")

        # Optionally fetch parent comment
        parent_comment_text = None
        if include_parent_comment:
            try:
                parent = get_comment_parent(comment_id)
                if parent:
                    parent_comment_text = parent.get("message", "")
                    logger.info(f"Parent comment: {parent_comment_text[:100]}...")
            except Exception as e:
                logger.warning(f"Failed to fetch parent comment: {e}")

        # Optionally fetch post context
        post_content = None
        if include_post_context and "post_id" in event_data:
            try:
                post = get_post_details(event_data["post_id"])
                post_content = post.get("story") or post.get("message", "")
                logger.info(f"Post context: {post_content[:100]}...")
            except Exception as e:
                logger.warning(f"Failed to fetch post: {e}")

        # Generate reply using OpenAI
        reply_text = generate_reply(
            comment_text=comment_text,
            system_prompt=system_prompt,
            parent_comment_text=parent_comment_text,
            post_content=post_content,
        )

        logger.info(f"Generated reply: {reply_text[:100]}...")
        result["reply_text"] = reply_text

        # Post the reply
        reply_id = post_comment_reply(comment_id, reply_text)
        result["reply_id"] = reply_id
        result["status"] = "success"

        logger.info(f"Reply posted successfully: {reply_id}")

    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        logger.error(f"Error processing comment: {e}", exc_info=True)

    return result


# ──────────────────────────────────────────────────────────────────────────────
# FLASK SERVER (if running standalone)
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        print("Flask not installed. Install with: pip install flask")
        exit(1)

    app = Flask(__name__)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    @app.route("/webhook/comment", methods=["GET"])
    def webhook_verify():
        """Meta sends a GET to verify the webhook URL during registration."""
        verify_token = FB_VERIFY_TOKEN
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == verify_token:
            logger.info("Webhook verified by Meta")
            return challenge, 200
        else:
            logger.warning(f"Webhook verification failed – token mismatch (got: {token})")
            return "Forbidden", 403

    @app.route("/webhook/comment", methods=["POST"])
    def webhook_comment():
        """
        Facebook comment webhook endpoint.

        Expected JSON body:
        {
            "comment_id": "123456789",
            "post_id": "987654321",  // optional
            "system_prompt": "...",  // optional, uses .env.comment-reply default
            "include_parent_comment": true,  // optional, uses .env default
            "include_post_context": false  // optional, uses .env default
        }
        """
        try:
            # Validate webhook signature
            signature = request.headers.get("X-Hub-Signature-SHA256", "")
            if not validate_webhook_signature(request.data, signature):
                logger.warning("Invalid webhook signature")
                return jsonify({"error": "Invalid signature"}), 403

            data = request.get_json()
            logger.info(f"Webhook payload: {data}")

            # Parse Meta's envelope: entry[0].changes[0].value
            try:
                value = data["entry"][0]["changes"][0]["value"]
            except (KeyError, IndexError):
                logger.warning("Unexpected payload structure, skipping")
                return jsonify({"status": "skipped"}), 200

            # Only process new comments, skip edits/deletes/other events
            if value.get("verb") != "add" or value.get("item") != "comment":
                logger.info(f"Skipping non-comment event: verb={value.get('verb')} item={value.get('item')}")
                return jsonify({"status": "skipped"}), 200

            page_id = os.getenv("FB_PAGE_ID", "")

            # Skip comments made by the page itself to prevent infinite loop
            if value.get("from", {}).get("id") == page_id:
                logger.info("Skipping own comment to prevent loop")
                return jsonify({"status": "skipped – own comment"}), 200

            # Process the comment
            result = handle_comment_webhook(
                event_data=value,
                system_prompt=DEFAULT_SYSTEM_PROMPT,
                include_parent_comment=DEFAULT_INCLUDE_PARENT,
                include_post_context=DEFAULT_INCLUDE_POST,
            )

            status_code = 200 if result["status"] == "success" else 400
            return jsonify(result), status_code

        except Exception as e:
            logger.error(f"Webhook error: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    logger.info(f"Starting FB Comment Auto-Reply server on port {FB_REPLY_PORT}")
    logger.info(f"Webhook endpoint: POST http://localhost:{FB_REPLY_PORT}/webhook/comment")
    app.run(host="0.0.0.0", port=FB_REPLY_PORT, debug=False)
