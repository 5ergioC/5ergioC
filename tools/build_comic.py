#!/usr/bin/env python3
"""Render the Comic Sans interjection as baked dark/light PNGs.

    python tools/build_comic.py

GitHub strips <style> and inline CSS from Markdown, so a custom typeface can
only reach the reader as an image. Rendering it here (rather than shipping a
webfont) also means the result does not depend on the visitor having Comic
Sans installed.

The background is transparent so the line sits on the page as text rather
than as a panel; the two themes differ only in ink colour.

Supersampled 3x and downscaled, so the edges stay smooth at README width.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palette  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "Images"

# Cryptography and Zelda moved to the Sheikah line below this one.
TEXT = "I like cybersecurity and graphic design"
SCALE = 3
FONT_SIZE = 46
PAD_X, PAD_Y = 34, 22

# Comic Sans ships with Windows and macOS; the fallbacks keep a CI build honest.
FONT_CANDIDATES = [
    "C:/Windows/Fonts/comicbd.ttf",
    "C:/Windows/Fonts/comic.ttf",
    "/System/Library/Fonts/Supplemental/Comic Sans MS Bold.ttf",
    "/usr/share/fonts/truetype/comic-neue/ComicNeue-Bold.ttf",
]



def load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    raise SystemExit(
        "error: no Comic Sans found. Install it or add a path to FONT_CANDIDATES."
    )


def render(foreground: str, shadow: str) -> Image.Image:
    font = load_font(FONT_SIZE * SCALE)
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    left, top, right, bottom = probe.textbbox((0, 0), TEXT, font=font)
    cap_top, cap_bottom = probe.textbbox((0, 0), "H", font=font)[1::2]

    width = right - left + 2 * PAD_X * SCALE
    height = bottom - top + 2 * PAD_Y * SCALE
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    origin = (PAD_X * SCALE - left, PAD_Y * SCALE - top)
    offset = 3 * SCALE
    draw.text((origin[0] + offset, origin[1] + offset), TEXT, font=font, fill=shadow)
    draw.text(origin, TEXT, font=font, fill=foreground)

    # Shrink until a capital stands TEXT_HEIGHT tall, so this line matches the
    # greeting and the Sheikah runes. The README shows the PNG at this exact
    # width; resampling it again would only soften the edges.
    shrink = palette.TEXT_HEIGHT / (cap_bottom - cap_top)
    return canvas.resize((round(width * shrink), round(height * shrink)), Image.LANCZOS)


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    for mode in palette.MODES:
        theme = palette.theme(mode)
        path = OUT_DIR / f"interests-{mode}.png"
        render(theme["ink"], theme["dim"]).save(path, optimize=True)
        print(f"wrote {path.relative_to(ROOT)}  ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
