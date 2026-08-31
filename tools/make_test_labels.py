"""Generate synthetic label images for testing.

The brief suggests sourcing or creating test labels. These are rendered rather than
photographed, so they are the easy case - clean, straight, evenly lit. They exercise
the pipeline end to end; they do not tell you how the extractor does on a phone photo
of a curved bottle under fluorescent light.

    python tools/make_test_labels.py [output_dir]
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.verify import GOVERNMENT_WARNING

WIDTH, HEIGHT = 1000, 1400
MARGIN = 60

FONT_DIR = Path("/System/Library/Fonts/Supplemental")


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for candidate in (FONT_DIR / name, Path("/Library/Fonts") / name):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render(path: Path, brand: str, class_type: str, abv: str, net: str, warning: str | None) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)

    brand_font = _font("Arial Bold.ttf", 76)
    body_font = _font("Arial.ttf", 40)
    warning_font = _font("Arial Bold.ttf", 30)

    y = 140
    for line in _wrap(draw, brand, brand_font, WIDTH - 2 * MARGIN):
        draw.text((MARGIN, y), line, font=brand_font, fill="black")
        y += 92

    y += 40
    for line in _wrap(draw, class_type, body_font, WIDTH - 2 * MARGIN):
        draw.text((MARGIN, y), line, font=body_font, fill="black")
        y += 56

    y += 60
    draw.text((MARGIN, y), abv, font=body_font, fill="black")
    y += 70
    draw.text((MARGIN, y), net, font=body_font, fill="black")

    if warning:
        y = HEIGHT - 420
        for line in _wrap(draw, warning, warning_font, WIDTH - 2 * MARGIN):
            draw.text((MARGIN, y), line, font=warning_font, fill="black")
            y += 42

    image.save(path)
    print(f"wrote {path}")


CASES = {
    # Clean label that should pass every check.
    "compliant.png": dict(
        brand="OLD TOM DISTILLERY",
        class_type="Kentucky Straight Bourbon Whiskey",
        abv="45% Alc./Vol. (90 Proof)",
        net="750 mL",
        warning=GOVERNMENT_WARNING,
    ),
    # Jenny's catch: title case instead of all caps. Must be rejected.
    "warning_title_case.png": dict(
        brand="OLD TOM DISTILLERY",
        class_type="Kentucky Straight Bourbon Whiskey",
        abv="45% Alc./Vol. (90 Proof)",
        net="750 mL",
        warning=GOVERNMENT_WARNING.replace("GOVERNMENT WARNING:", "Government Warning:"),
    ),
    # No warning at all.
    "warning_missing.png": dict(
        brand="OLD TOM DISTILLERY",
        class_type="Kentucky Straight Bourbon Whiskey",
        abv="45% Alc./Vol. (90 Proof)",
        net="750 mL",
        warning=None,
    ),
    # ABV disagrees with the application.
    "abv_mismatch.png": dict(
        brand="OLD TOM DISTILLERY",
        class_type="Kentucky Straight Bourbon Whiskey",
        abv="40% Alc./Vol. (80 Proof)",
        net="750 mL",
        warning=GOVERNMENT_WARNING,
    ),
    # Dave's case: same brand, different casing and apostrophe.
    "brand_casing.png": dict(
        brand="STONE'S THROW",
        class_type="Straight Rye Whiskey",
        abv="45% Alc./Vol. (90 Proof)",
        net="750 mL",
        warning=GOVERNMENT_WARNING,
    ),
}


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "test_labels")
    out.mkdir(parents=True, exist_ok=True)
    for filename, spec in CASES.items():
        render(out / filename, **spec)


if __name__ == "__main__":
    main()
