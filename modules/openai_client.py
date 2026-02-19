"""
LLM client – handles all text generation calls.

Provider for post text is switchable via TEXT_GENERATION_PROVIDER in .env:
  TEXT_GENERATION_PROVIDER=gpt     → GPT-4o mini  (default)
  TEXT_GENERATION_PROVIDER=claude  → Claude claude-sonnet-4-5-20250929

Image prompt generation always uses GPT (no need to switch).
"""

import logging
import re
from typing import Optional

import anthropic
from openai import OpenAI, APIError, RateLimitError, APITimeoutError

from modules.config import (
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    TEXT_GENERATION_PROVIDER,
)
from modules.prompts import (
    TEXT_GENERATION_SYSTEM_PROMPT,
    TEXT_GENERATION_USER_PROMPT,
    IMAGE_PROMPT_SYSTEM_PROMPT,
    IMAGE_PROMPT_USER_PROMPT,
)

logger = logging.getLogger(__name__)

# ─── Unicode bold converter ───────────────────────────────────────────────────

def _apply_unicode_bold(text: str) -> str:
    """
    Replace **word** markers with Unicode Mathematical Bold characters.
    Only Latin A-Z, a-z and digits 0-9 have bold Unicode equivalents.
    Bengali and other scripts are left unchanged inside the markers.
    """
    _U = 0x1D400  # bold uppercase A
    _L = 0x1D41A  # bold lowercase a
    _D = 0x1D7CE  # bold digit 0

    def _to_bold(s: str) -> str:
        out = []
        for ch in s:
            if "A" <= ch <= "Z":
                out.append(chr(_U + ord(ch) - ord("A")))
            elif "a" <= ch <= "z":
                out.append(chr(_L + ord(ch) - ord("a")))
            elif "0" <= ch <= "9":
                out.append(chr(_D + ord(ch) - ord("0")))
            else:
                out.append(ch)
        return "".join(out)

    return re.sub(r"\*\*(.*?)\*\*", lambda m: _to_bold(m.group(1)), text, flags=re.DOTALL)


# ─── Lazy clients ─────────────────────────────────────────────────────────────
_openai_client: Optional[OpenAI] = None
_anthropic_client: Optional[anthropic.Anthropic] = None


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


def _get_anthropic() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set but TEXT_GENERATION_PROVIDER=claude."
            )
        _anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _anthropic_client


# ─── GPT ──────────────────────────────────────────────────────────────────────

def _call_gpt(system_prompt: str, user_prompt: str, label: str) -> str:
    client = _get_openai()
    logger.info("GPT-4o mini call: %s", label)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_prompt.strip()},
            ],
            response_format={"type": "text"},
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError(f"GPT returned empty content for '{label}'.")
        logger.debug("GPT response [%s]: %s", label, content[:200])
        return content

    except RateLimitError as e:
        raise RuntimeError(f"GPT rate limit during '{label}'.") from e
    except APITimeoutError as e:
        raise RuntimeError(f"GPT timeout during '{label}'.") from e
    except APIError as e:
        raise RuntimeError(f"GPT API error during '{label}'.") from e


# ─── Claude ───────────────────────────────────────────────────────────────────

def _call_claude(system_prompt: str, user_prompt: str, label: str) -> str:
    client = _get_anthropic()
    logger.info("Claude call: %s", label)
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            system=system_prompt.strip(),
            messages=[{"role": "user", "content": user_prompt.strip()}],
        )
        content = message.content[0].text
        if not content:
            raise RuntimeError(f"Claude returned empty content for '{label}'.")
        logger.debug("Claude response [%s]: %s", label, content[:200])
        return content

    except anthropic.RateLimitError as e:
        raise RuntimeError(f"Claude rate limit during '{label}'.") from e
    except anthropic.APITimeoutError as e:
        raise RuntimeError(f"Claude timeout during '{label}'.") from e
    except anthropic.APIError as e:
        raise RuntimeError(f"Claude API error during '{label}'.") from e


# ─── Public API ────────────────────────────────────────────────────────────────

def generate_post_text(word: str) -> str:
    """
    Generate Bengali educational post text for the given English word.
    Provider determined by TEXT_GENERATION_PROVIDER in .env (gpt | claude).
    """
    if not word or not word.strip():
        raise ValueError("'word' must be a non-empty string.")

    system = TEXT_GENERATION_SYSTEM_PROMPT
    user = TEXT_GENERATION_USER_PROMPT.format(word=word.strip())
    label = f"generate_post_text({word})"

    if TEXT_GENERATION_PROVIDER == "claude":
        raw = _call_claude(system, user, label).strip()
    else:
        raw = _call_gpt(system, user, label).strip()
    raw = re.sub(r"^#+[^\n]*\n?", "", raw, flags=re.MULTILINE)  # drop lines starting with #
    return _apply_unicode_bold(raw.strip())


def generate_image_prompt(post_text: str, word: str) -> str:
    """
    Generate an image-generation prompt from the post text and word.
    Always uses GPT-4o mini.
    """
    if not post_text or not post_text.strip():
        raise ValueError("'post_text' must be a non-empty string.")
    if not word or not word.strip():
        raise ValueError("'word' must be a non-empty string.")

    system = IMAGE_PROMPT_SYSTEM_PROMPT
    user = IMAGE_PROMPT_USER_PROMPT.format(word=word.strip(), post_text=post_text.strip())

    return _call_gpt(system, user, "generate_image_prompt").strip()