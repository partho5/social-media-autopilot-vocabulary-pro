"""
Image processor – composites the AI-generated image onto a vertical canvas
and adds the Bengali "আজকের ওয়ার্ড: <word>" label at the top.

Canvas layout (default 1080×1350, a 4:5 Facebook-friendly ratio):
┌─────────────────────────────────────┐
│                                     │  ← top padding
│      আজকের ওয়ার্ড: WORD          │  ← Bengali label (centred)
│                                     │  ← gap
│█████████████████████████████████████│
│█                                   █│
│█      AI generated image           █│  ← full canvas width, no side margins
│█      anchored to bottom           █│
│█████████████████████████████████████│
└─────────────────────────────────────┘
"""

import logging
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

from modules.config import FONTS_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)

# ─── Canvas defaults (can be overridden via kwargs later) ─────────────────────
_CANVAS_W = 1080
_CANVAS_H = 1350
_BG_COLOR = (15, 15, 25)          # near-black dark background
_LABEL_COLOR = (255, 255, 255)     # white text
_WORD_COLOR = (255, 210, 60)       # golden accent for the English word
_PADDING = 60                      # outer padding (pixels)
_LABEL_FONT_SIZE = 52
_WORD_FONT_SIZE = 68
_IMAGE_BOTTOM_MARGIN = 0           # image touches canvas bottom edge


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load NotoSansBengali from fonts/ directory; fall back to default."""
    font_path = FONTS_DIR / "NotoSansBengali.ttf"
    if font_path.exists():
        try:
            return ImageFont.truetype(str(font_path), size)
        except Exception as e:
            logger.warning("Could not load Bengali font (%s). Using default.", e)
    return ImageFont.load_default()


def _fit_image(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Resize image to fit within (max_w, max_h) while preserving aspect ratio."""
    img.thumbnail((max_w, max_h), Image.LANCZOS)
    return img


def create_post_image(
    generated_image: Image.Image,
    word: str,
    *,
    canvas_w: int = _CANVAS_W,
    canvas_h: int = _CANVAS_H,
) -> Path:
    """
    Composite the AI image onto a vertical canvas with the Bengali word label.

    Args:
        generated_image: PIL Image from Gemini.
        word: The English vocabulary word (e.g. "Ephemeral").

    Returns:
        Path to the saved output image.
    """
    if not word:
        raise ValueError("'word' must be non-empty.")

    canvas = Image.new("RGB", (canvas_w, canvas_h), color=_BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # ── Fonts ──────────────────────────────────────────────────────────────────
    label_font = _get_font(_LABEL_FONT_SIZE)   # "আজকের ওয়ার্ড:"
    word_font = _get_font(_WORD_FONT_SIZE)     # the English word

    # ── Measure text heights ───────────────────────────────────────────────────
    def text_size(text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    label_text = "আজকের ওয়ার্ড:"
    lw, lh = text_size(label_text, label_font)
    ww, wh = text_size(word.upper(), word_font)

    total_text_h = lh + 20 + wh   # 20px gap between two text lines

    # ── Place text centred at top (with padding) ───────────────────────────────
    text_top = _PADDING

    label_x = (canvas_w - lw) // 2
    draw.text((label_x, text_top), label_text, font=label_font, fill=_LABEL_COLOR)

    word_x = (canvas_w - ww) // 2
    word_y = text_top + lh + 20
    draw.text((word_x, word_y), word.capitalize(), font=word_font, fill=_WORD_COLOR)

    # ── Place generated image below the text block ─────────────────────────────
    image_top = text_top + total_text_h + _PADDING   # gap after text block
    max_img_h = canvas_h - image_top
    max_img_w = canvas_w                              # full width, no side margins

    ai_img = _fit_image(generated_image.copy(), max_img_w, max_img_h)
    img_x = (canvas_w - ai_img.width) // 2           # centre (handles non-square images)
    img_y = canvas_h - ai_img.height                 # anchor to bottom edge

    # Ensure image doesn't overlap text
    if img_y < image_top:
        img_y = image_top

    canvas.paste(ai_img, (img_x, img_y))

    # ── Save ───────────────────────────────────────────────────────────────────
    safe_word = "".join(c for c in word if c.isalnum() or c in "-_")
    output_path = OUTPUT_DIR / f"post_{safe_word}.jpg"
    canvas.save(output_path, format="JPEG", quality=92, optimize=True)
    logger.info("Post image saved: %s (%dx%d)", output_path, canvas_w, canvas_h)
    return output_path
