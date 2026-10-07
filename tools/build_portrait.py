#!/usr/bin/env python3
"""Render the ASCII portrait as two animated theme SVGs.

    python tools/build_portrait.py [--title "C:\\USERS\\5ERGIOC> FACE.EXE"]

Reads tools/portrait.txt (see photo2ascii.py) and writes
Images/portrait-dark.svg and Images/portrait-light.svg.

The art's type size is derived from its column count rather than fixed, so a
dithered portrait at 104 columns and a coarse one at 50 both land on the same
rendered width. The title bar keeps its own readable size: it is a caption,
not part of the picture.

The animation is SMIL only: rows fade in top to bottom like a CRT drawing a
frame, a soft scanline sweeps down forever, and the whole plate flickers
gently. GitHub's camo proxy strips scripts from SVGs but passes SMIL through,
which is how the contribution snake animates.

Motion is deliberately slow and low-contrast. Anything faster reads as a
strobe, and a README cannot honour prefers-reduced-motion: an <img> gets no
stylesheet, and GitHub removes <style> from Markdown.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palette  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PORTRAIT = ROOT / "tools" / "portrait-{mode}.txt"

# photo2ascii.RAMP, darkest glyph first. Index 0 (space) is never painted.
RAMP = " .:-=+*#%@"

TARGET_WIDTH = 600  # the SVG's own width; the README shows it 1:1
PAD_X, PAD_TOP, PAD_BOTTOM = 20, 18, 18
# Widest monospace advance as a fraction of the type size. Sizing against the
# widest fallback means the art never overflows its frame, whatever font the
# reader's browser picks.
ADVANCE_RATIO = 0.602
LINE_RATIO = 1.16

TITLE_SIZE = 13
TITLE_GAP = 26

# Per theme: whether glyphs also carry a brightness ramp, or all share one ink
# and let density alone carry the tone. On black the ramp is what models the
# face, so the features read; on white a single ink gives a firmer, crisper
# figure. Picked by eye from a side-by-side, not derived.
RAMPED = {"dark": True, "light": False}

BOOT_SECONDS = 2.2  # total, however many rows there are
# How many rows are mid-wipe at once. One would be a strict row-by-row print
# and takes too long to finish; three keeps a diagonal edge moving.
WIPE_OVERLAP = 3
SWEEP_SECONDS = 5.0
SWEEP_HEIGHT = 46
# The sweep has to stay fainter on white than it does on black.
SWEEP_OPACITY = {"dark": "0.13", "light": "0.10"}


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def span(text: str, fill: str) -> str:
    return f'<tspan fill="{fill}">{escape(text)}</tspan>'


def row_spans(line: str, shades: list[str | None]) -> str:
    """Runs of one glyph collapse into a single tspan, which keeps the file small."""
    spans, run, glyph = [], 0, None
    for char in line.rstrip() + "\0":
        if char == glyph:
            run += 1
            continue
        if glyph is not None:
            fill = shades[RAMP.index(glyph)] if glyph in RAMP else shades[-1]
            spans.append(glyph * run if fill is None else span(glyph * run, fill))
        glyph, run = char, 1
    return "".join(spans)


def build(mode: str, art: list[str], title: str) -> tuple[str, int, int]:
    theme = palette.theme(mode)
    shades = (palette.ramp(mode, len(RAMP)) if RAMPED[mode]
              else [None] + [theme["ink"]] * (len(RAMP) - 1))

    columns = max(len(line.rstrip()) for line in art)
    font_size = (TARGET_WIDTH - 2 * PAD_X) / (columns * ADVANCE_RATIO)
    cell = (TARGET_WIDTH - 2 * PAD_X) / columns
    leap = font_size * LINE_RATIO

    top = PAD_TOP + (TITLE_SIZE + TITLE_GAP if title else 0)
    height = round(top + (len(art) - 1) * leap + font_size + PAD_BOTTOM)
    stagger = BOOT_SECONDS / len(art)
    wipe = stagger * WIPE_OVERLAP
    boot = BOOT_SECONDS + wipe

    body = []
    if title:
        # The title's dashes are measured in its own type size, not the art's.
        dashes = max(0, round((TARGET_WIDTH - 2 * PAD_X) /
                              (TITLE_SIZE * ADVANCE_RATIO)) - len(title) - 1)
        body.append(
            f'<text x="{PAD_X}" y="{PAD_TOP + TITLE_SIZE}" '
            f'font-size="{TITLE_SIZE}px" xml:space="preserve">'
            + span(f"{title} ", theme["head"])
            + span("-" * dashes, theme["dim"])
            + "</text>"
        )

    clips = []
    for index, line in enumerate(art):
        spans = row_spans(line, shades)
        if not spans:
            continue
        y = top + index * leap + font_size
        # Pinning each row to its own character count makes the geometry exact
        # rather than a bet on the reader's monospace advance width.
        run = len(line.rstrip()) * cell
        # Each row wipes open left to right, the way a terminal prints it.
        # Staggering the starts turns that into one diagonal edge crossing
        # the plate, which is the whole effect.
        clips.append(
            f'<clipPath id="r{index}">'
            f'<rect x="{PAD_X}" y="{y - font_size:.1f}" width="0" '
            f'height="{leap + 2:.1f}">'
            f'<animate attributeName="width" from="0" to="{run:.1f}" '
            f'begin="{index * stagger:.2f}s" dur="{wipe:.2f}s" fill="freeze"/>'
            f"</rect></clipPath>"
        )
        body.append(
            f'<text x="{PAD_X}" y="{y:.1f}" font-size="{font_size:.2f}px" '
            f'textLength="{run:.1f}" lengthAdjust="spacingAndGlyphs" '
            f'clip-path="url(#r{index})" xml:space="preserve">{spans}</text>'
        )

    plate = (
        f'<g opacity="1">\n'
        f'<animate attributeName="opacity" values="1;0.93;1;0.97;1" '
        f'begin="{boot:.2f}s" dur="2.7s" repeatCount="indefinite"/>\n'
        + "\n".join(body)
        + "\n</g>"
    )
    sweep = (
        f'<rect x="1" y="-{SWEEP_HEIGHT}" width="{TARGET_WIDTH - 2}" '
        f'height="{SWEEP_HEIGHT}" fill="url(#sweep)">'
        f'<animate attributeName="y" from="-{SWEEP_HEIGHT}" to="{height}" '
        f'begin="{boot + 0.4:.2f}s" dur="{SWEEP_SECONDS}s" repeatCount="indefinite"/>'
        f"</rect>"
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{TARGET_WIDTH}" '
        f'height="{height}" viewBox="0 0 {TARGET_WIDTH} {height}" role="img" '
        f'aria-label="ASCII portrait of Sergio on a phosphor terminal" '
        f'font-family="Consolas, &quot;DejaVu Sans Mono&quot;, Menlo, monospace">\n'
        f"<defs>\n"
        + "\n".join(clips)
        + f'\n<linearGradient id="sweep" x1="0" y1="0" x2="0" y2="1">\n'
        f'<stop offset="0%" stop-color="{theme["border"]}" stop-opacity="0"/>\n'
        f'<stop offset="50%" stop-color="{theme["border"]}" '
        f'stop-opacity="{SWEEP_OPACITY[mode]}"/>\n'
        f'<stop offset="100%" stop-color="{theme["border"]}" stop-opacity="0"/>\n'
        f"</linearGradient>\n"
        f"</defs>\n"
        f'<rect x="0.5" y="0.5" width="{TARGET_WIDTH - 1}" height="{height - 1}" '
        f'fill="{theme["bg"]}" stroke="{theme["border"]}"/>\n'
        f"{plate}\n{sweep}\n</svg>\n"
    )
    return svg, TARGET_WIDTH, height


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", default="C:\\USERS\\5ERGIOC> FACE.EXE")
    args = parser.parse_args()

    out_dir = ROOT / "Images"
    out_dir.mkdir(exist_ok=True)
    for mode in palette.MODES:
        # Each theme has its own plate: see the polarity note in photo2ascii.
        source = PORTRAIT.with_name(PORTRAIT.name.format(mode=mode))
        if not source.is_file():
            raise SystemExit(f"error: missing {source}; run photo2ascii.py first")
        art = source.read_text(encoding="utf-8").rstrip("\n").split("\n")
        svg, width, height = build(mode, art, args.title)
        path = out_dir / f"portrait-{mode}.svg"
        path.write_text(svg, encoding="utf-8")
        print(
            f"wrote {path.relative_to(ROOT)}  "
            f"({width}x{height}, {path.stat().st_size:,} bytes)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
