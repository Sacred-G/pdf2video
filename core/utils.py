"""
Shared utilities for the PDF2Video core package.
"""

import base64
import io
import time

from openai import APITimeoutError, APIConnectionError, RateLimitError
from PIL import Image
from rich.console import Console

console = Console()


def retry_api(fn, max_retries: int = 3, backoff: float = 2.0):
    """Retry an API call with exponential backoff on transient errors."""
    for attempt in range(max_retries):
        try:
            return fn()
        except (APITimeoutError, APIConnectionError, RateLimitError) as e:
            if attempt == max_retries - 1:
                raise
            wait = backoff * (2 ** attempt)
            console.print(f"  [yellow]⚠ API error ({type(e).__name__}), retrying in {wait:.0f}s...[/]")
            time.sleep(wait)


def image_to_data_url(img: Image.Image, max_size: int = 512) -> str:
    """Resize an image and encode as a data URL for the Responses API vision input."""
    thumb = img.copy()
    thumb.thumbnail((max_size, max_size), Image.LANCZOS)
    if thumb.mode == "RGBA":
        thumb = thumb.convert("RGB")

    buf = io.BytesIO()
    thumb.save(buf, format="JPEG", quality=80)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"
