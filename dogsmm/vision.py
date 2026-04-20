"""Shared helpers for sending images to Claude."""
from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

# Claude accepts images up to ~5MB. Resize so the long edge is at most 1568px,
# which is the recommended max for best quality-per-token.
MAX_DIM = 1568


def encode_image(path: Path) -> tuple[str, str]:
    """Return (base64_data, media_type) ready for the Anthropic messages API."""
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((MAX_DIM, MAX_DIM))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.standard_b64encode(buf.getvalue()).decode(), "image/jpeg"


def image_block(path: Path) -> dict:
    data, media_type = encode_image(path)
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }
