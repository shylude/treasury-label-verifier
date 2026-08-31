"""Read label fields off an image.

Two backends, chosen at runtime:

* ``claude``   - a vision model call. Handles the angled/glare/low-light photos Jenny
                 described, which plain OCR reliably fails on.
* ``tesseract``- local OCR. No outbound network at all, which is the constraint Marcus
                 raised about the firewall blocking vendor ML endpoints.

The Claude backend is preferred when credentials are present and falls back to OCR
rather than failing the request, so a deployment behind a strict egress policy still
works with reduced accuracy instead of not at all.
"""

from __future__ import annotations

import base64
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MODEL = os.environ.get("LABEL_MODEL", "claude-opus-5")

# Sarah's hard number: the previous vendor pilot died at 30-40s per label because
# agents could eyeball five labels in that time. Anything past this is a failure.
LATENCY_BUDGET_SECONDS = 5.0

# Fast mode roughly halves time-to-last-token at premium pricing. Off by default so
# the demo is cheap to run; the README explains when to turn it on.
USE_FAST_MODE = os.environ.get("LABEL_FAST_MODE", "").lower() in {"1", "true", "yes"}

EXTRACTION_PROMPT = """\
You are reading a single alcohol beverage label for TTB compliance review.

Transcribe what is printed on the label. Do not correct, normalize, or tidy anything -
the review downstream depends on seeing exactly what the label says, including casing.

The government warning matters most. Transcribe it character for character, preserving
capitalization exactly as printed. If "Government Warning" appears in title case on the
label, report it in title case. If it is absent entirely, return null for that field.

Return null for any field that is not visible or not legible. Do not guess."""


class LabelText(BaseModel):
    """Fields transcribed off the label artwork."""

    # Written with typing.Optional rather than `X | None` so the model is evaluable on
    # Python 3.9, which is what several federal images still ship with.
    brand_name: Optional[str] = Field(None, description="Brand name as printed")
    class_type: Optional[str] = Field(None, description="Class/type designation, e.g. 'Kentucky Straight Bourbon Whiskey'")
    alcohol_content: Optional[str] = Field(None, description="Alcohol content as printed, e.g. '45% Alc./Vol. (90 Proof)'")
    net_contents: Optional[str] = Field(None, description="Net contents as printed, e.g. '750 mL'")
    government_warning: Optional[str] = Field(None, description="Health warning, transcribed verbatim with original casing")
    producer: Optional[str] = Field(None, description="Name and address of bottler or producer")
    country_of_origin: Optional[str] = Field(None, description="Country of origin, if stated")
    legible: bool = Field(True, description="False if the image is too dark, blurred, or angled to read confidently")


@dataclass
class Extraction:
    fields: LabelText
    backend: str
    elapsed_seconds: float

    @property
    def within_budget(self) -> bool:
        return self.elapsed_seconds <= LATENCY_BUDGET_SECONDS


def _media_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return {".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}.get(ext, "image/jpeg")


def _extract_with_claude(image_bytes: bytes, filename: str) -> LabelText:
    import anthropic

    client = anthropic.Anthropic(timeout=LATENCY_BUDGET_SECONDS * 2, max_retries=1)
    encoded = base64.standard_b64encode(image_bytes).decode("utf-8")

    request = {
        "model": MODEL,
        "max_tokens": 2048,
        # Transcription is not a reasoning-heavy task, and effort is the main lever
        # we have on latency without changing models.
        "output_config": {"effort": "low"},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64",
                                             "media_type": _media_type(filename),
                                             "data": encoded}},
                {"type": "text", "text": EXTRACTION_PROMPT},
            ],
        }],
        "output_format": LabelText,
    }

    if USE_FAST_MODE:
        response = client.beta.messages.parse(
            **request, speed="fast", betas=["fast-mode-2026-02-01"],
        )
    else:
        response = client.messages.parse(**request)

    if response.stop_reason == "refusal":
        raise RuntimeError("Model declined to process this image.")

    return response.parsed_output


_OCR_PATTERNS = {
    "alcohol_content": re.compile(r"[^\n]*\d+(?:\.\d+)?\s*%[^\n]*", re.IGNORECASE),
    "net_contents": re.compile(r"[^\n]*\d+(?:\.\d+)?\s*(?:ml|milliliters?|l|liters?)\b[^\n]*", re.IGNORECASE),
}


def _extract_with_tesseract(image_bytes: bytes) -> LabelText:
    """Best-effort local OCR. Loses on skewed or glared images - documented, not hidden."""
    import io

    import pytesseract
    from PIL import Image

    text = pytesseract.image_to_string(Image.open(io.BytesIO(image_bytes)))
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    warning = None
    lowered = text.lower()
    if "government warning" in lowered:
        start = lowered.index("government warning")
        warning = " ".join(text[start:].split())

    fields = {"government_warning": warning}
    for name, pattern in _OCR_PATTERNS.items():
        match = pattern.search(text)
        fields[name] = match.group(0).strip() if match else None

    # OCR gives no reliable structure, so the largest run of text near the top is the
    # best available guess at the brand. An agent confirms it either way.
    fields["brand_name"] = lines[0] if lines else None
    fields["legible"] = bool(lines)
    return LabelText(**fields)


def extract(image_bytes: bytes, filename: str = "label.jpg", backend: str | None = None) -> Extraction:
    """Read a label. ``backend`` forces a path; otherwise Claude is tried first."""
    chosen = backend or ("claude" if os.environ.get("ANTHROPIC_API_KEY") else "tesseract")
    started = time.perf_counter()

    if chosen == "claude":
        try:
            fields = _extract_with_claude(image_bytes, filename)
        except Exception as exc:  # noqa: BLE001 - degrade rather than fail the review
            logger.warning("Claude extraction failed (%s); falling back to local OCR.", exc)
            chosen = "tesseract-fallback"
            fields = _extract_with_tesseract(image_bytes)
    else:
        fields = _extract_with_tesseract(image_bytes)

    return Extraction(fields=fields, backend=chosen, elapsed_seconds=time.perf_counter() - started)
