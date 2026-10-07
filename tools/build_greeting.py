#!/usr/bin/env python3
"""Render the greeting as a typing terminal line, in two theme SVGs.

    python tools/build_greeting.py

Writes Images/greeting-dark.svg and Images/greeting-light.svg: a DOS prompt
that types itself out and leaves a blinking block cursor.

Both <text> elements are pinned with textLength, so the geometry is exact
whatever monospace the reader's browser picks. That matters here more than on
the card: the typing effect is a clip rectangle widening one character at a
time, and it only lands on character boundaries if the text width is known.

SMIL only, no <style> and no scripts, so GitHub's camo proxy passes it
through. Background is transparent: the line sits on the page like text
instead of arriving in a box of its own.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palette  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "Images"

PROMPT = "C:\\USERS\\5ERGIOC>"
GREETING = " hi, i'm Sergio"

# Consolas caps stand at 0.633 of the em. The other monospace fallbacks sit
# within a few percent, close enough that the greeting matches its neighbours.
CAP_RATIO = 0.633
FONT_SIZE = round(palette.TEXT_HEIGHT / CAP_RATIO)
CHAR_W = FONT_SIZE * 0.6  # the pinned advance, not a measurement of any font
PAD_X, PAD_Y = round(FONT_SIZE * 0.2), round(FONT_SIZE * 0.3)
CURSOR_W, CURSOR_H = round(FONT_SIZE * 0.52), FONT_SIZE

TYPE_SECONDS = 0.07  # per character
BLINK_SECONDS = 0.55



def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(theme: dict) -> str:
    prompt_w = round(len(PROMPT) * CHAR_W)
    greeting_w = round(len(GREETING) * CHAR_W)
    width = PAD_X * 2 + prompt_w + greeting_w + CURSOR_W
    height = PAD_Y * 2 + CURSOR_H
    baseline = PAD_Y + round(FONT_SIZE * 0.8)

    typing = len(GREETING) * TYPE_SECONDS
    # Discrete steps land the clip edge exactly on each character boundary.
    steps = ";".join(
        str(round(greeting_w * step / len(GREETING)))
        for step in range(len(GREETING) + 1)
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{escape(PROMPT + GREETING)}" '
        f'font-family="Consolas, &quot;DejaVu Sans Mono&quot;, Menlo, monospace" '
        f'font-size="{FONT_SIZE}px">\n'
        f"<defs>\n"
        f'<clipPath id="type">\n'
        f'<rect x="{PAD_X + prompt_w}" y="0" width="0" height="{height}">\n'
        f'<animate attributeName="width" values="{steps}" '
        f'dur="{typing:.2f}s" calcMode="discrete" fill="freeze"/>\n'
        f"</rect>\n"
        f"</clipPath>\n"
        f"</defs>\n"
        f'<text x="{PAD_X}" y="{baseline}" textLength="{prompt_w}" '
        f'lengthAdjust="spacingAndGlyphs" fill="{theme["key"]}" '
        f'xml:space="preserve">{escape(PROMPT)}</text>\n'
        f'<g clip-path="url(#type)">\n'
        f'<text x="{PAD_X + prompt_w}" y="{baseline}" textLength="{greeting_w}" '
        f'lengthAdjust="spacingAndGlyphs" fill="{theme["value"]}" '
        f'xml:space="preserve">{escape(GREETING)}</text>\n'
        f"</g>\n"
        f'<rect x="{PAD_X + prompt_w + greeting_w}" y="{PAD_Y}" '
        f'width="{CURSOR_W}" height="{CURSOR_H}" fill="{theme["head"]}" '
        f'opacity="0">\n'
        f'<animate attributeName="opacity" values="1;0" calcMode="discrete" '
        f'begin="{typing:.2f}s" dur="{BLINK_SECONDS * 2:.2f}s" '
        f'repeatCount="indefinite"/>\n'
        f"</rect>\n"
        f"</svg>\n"
    )


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    for mode in palette.MODES:
        path = OUT_DIR / f"greeting-{mode}.svg"
        path.write_text(build(palette.theme(mode)), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}  ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
