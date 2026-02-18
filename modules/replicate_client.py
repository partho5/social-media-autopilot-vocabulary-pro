"""
Replicate image generation client.
Model: bytedance/sdxl-lightning-4step
Version: 5599ed30703defd1d160a25a63321b4dec97101d98b4674bcc56e41f62f35637

SDXL-Lightning produces 1024×1024 images in 4 steps (very fast).
"""

import io
import logging
import os

import replicate
from PIL import Image

from modules.config import REPLICATE_API_TOKEN

# Ensure token is in environment for the replicate client to find automatically
os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_TOKEN

logger = logging.getLogger(__name__)

# Verified full SHA256 hash for the stable 4-step version
_MODEL = "bytedance/sdxl-lightning-4step:5599ed30703defd1d160a25a63321b4dec97101d98b4674bcc56e41f62f35637"


def generate_image(prompt: str) -> Image.Image:
    """
    Generate an image via Replicate (SDXL-Lightning 4-step).

    Args:
        prompt: Image generation prompt string.

    Returns:
        PIL Image (RGB).
    Raises:
        RuntimeError on API or decoding failure.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Image generation prompt must be non-empty.")

    logger.info("Replicate image generation started. Prompt: %s...", prompt[:80])

    try:
        # replicate.run returns a list of FileOutput objects
        output = replicate.run(
            _MODEL,
            input={
                "prompt": prompt.strip(),
                "width": 1024,
                "height": 1024,
                "num_outputs": 1,
                "scheduler": "K_EULER",
                "guidance_scale": 0,  # Recommended for distilled lightning models
                "num_inference_steps": 4,
            },
        )

        if not output:
            raise RuntimeError("Replicate returned empty output.")

        # Modern replicate-python returns FileOutput objects; read() gets bytes directly
        image_data: bytes = output[0].read()

        img = Image.open(io.BytesIO(image_data)).convert("RGB")
        logger.info("Replicate image generated (%dx%d).", img.width, img.height)
        return img

    except Exception as e:
        logger.error("Replicate image generation failed: %s", e)
        raise RuntimeError(f"Image generation failed: {e}") from e