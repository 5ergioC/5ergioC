#!/usr/bin/env python3
"""Render the Sheikah line as two theme SVGs, with the glyphs as outlines.

    python tools/build_sheikah.py [--font tools/sheikah.ttf]

Writes Images/sheikah-dark.svg and Images/sheikah-light.svg.

Every glyph is converted to an SVG <path> here, so nothing about the result
depends on the reader having the font, and the font file never has to be
committed: point --font at wherever it lives and keep it out of the repo.

dcode.fr is not a source for this. It has no font at all: it composes the
line from one 36x36 PNG per character under /tools/sheikah/images/, so the
only thing to take from it is a screenshot.

The viewBox is measured from the real ink, not from the font's declared
ascender. Handwritten Sheikah Runes claims an ascent of 792 units while no
glyph reaches past 537, which would otherwise pad a third of the image with
nothing.
"""

from __future__ import annotations

import argparse
import sys
from statistics import median
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palette  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "Images"

# One entry per line, centred against each other. Move a word between the two
# to rebalance; a single 34-character line came out too wide for the page.
LINES = [
    "i also like",
    "cryptography and zelda",
]


PAD_X, PAD_Y = 12, 10
LINE_RATIO = 1.05  # line spacing as a fraction of the em
SPACE_RATIO = 0.30  # em width for a space the font does not define



def glyph_name(cmap: dict, char: str) -> str | None:
    """Sheikah fan fonts vary on which case they map; try the obvious ones."""
    for candidate in (char, char.upper(), char.lower()):
        name = cmap.get(ord(candidate))
        if name:
            return name
    return None


def lay_out(font: TTFont) -> tuple[list[tuple[str, float, float]], tuple[float, ...]]:
    """Place every glyph in font units, and measure the ink they cover.

    Returns the placements as (glyph name, x, baseline y) and the ink box as
    (x0, y0, x1, y1). Font units run Y-upwards, so each line sits lower than
    the one before it at a more negative baseline.
    """
    upem = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    glyphs = font.getGlyphSet()
    metrics = font["hmtx"].metrics
    space_advance = SPACE_RATIO * upem
    line_height = LINE_RATIO * upem

    missing = set()
    rows = []
    for line in LINES:
        pen_x = 0.0
        placed = []
        for char in line:
            if char == " ":
                pen_x += space_advance
                continue
            name = glyph_name(cmap, char)
            if name is None:
                missing.add(char)
                pen_x += space_advance
                continue
            placed.append((name, pen_x))
            pen_x += metrics[name][0]
        rows.append((pen_x, placed))

    if missing:
        print(f"  warning: font has no glyph for {sorted(missing)}")

    widest = max(width for width, _ in rows)
    placements = []
    box = [float("inf"), float("inf"), float("-inf"), float("-inf")]
    for index, (width, placed) in enumerate(rows):
        indent = (widest - width) / 2  # centre each line against the widest
        baseline = -index * line_height
        for name, pen_x in placed:
            bounds_pen = BoundsPen(glyphs)
            glyphs[name].draw(bounds_pen)
            x = indent + pen_x
            placements.append((name, x, baseline))
            if bounds_pen.bounds:
                x0, y0, x1, y1 = bounds_pen.bounds
                box[0] = min(box[0], x + x0)
                box[1] = min(box[1], baseline + y0)
                box[2] = max(box[2], x + x1)
                box[3] = max(box[3], baseline + y1)
    return placements, tuple(box)


def rune_height(font: TTFont) -> float:
    """Median height of a single rune, in font units, over the ones this text uses.

    Runes have no ascenders or descenders, so this is the Sheikah counterpart of
    a cap height, and what TEXT_HEIGHT is matched against. The median rather
    than the union: runes sit at slightly different heights, so the box around
    all of them is 13% taller than any one rune, and sizing to that left every
    rune about 21px next to 24px capitals.
    """
    cmap = font.getBestCmap()
    glyphs = font.getGlyphSet()
    heights = []
    for char in set("".join(LINES)) - {" "}:
        name = glyph_name(cmap, char)
        if name is None:
            continue
        pen = BoundsPen(glyphs)
        glyphs[name].draw(pen)
        if pen.bounds:
            heights.append(pen.bounds[3] - pen.bounds[1])
    return median(heights)


def build(font: TTFont, color: str) -> tuple[str, int, int]:
    glyphs = font.getGlyphSet()
    placements, (x0, y0, x1, y1) = lay_out(font)

    scale = palette.TEXT_HEIGHT / rune_height(font)
    width = round((x1 - x0) * scale) + 2 * PAD_X
    height = round((y1 - y0) * scale) + 2 * PAD_Y

    paths = []
    for name, x, baseline in placements:
        pen = SVGPathPen(glyphs)
        glyphs[name].draw(pen)
        commands = pen.getCommands()
        if commands:
            paths.append(f'<path transform="translate({x:.1f} {baseline:.1f})" d="{commands}"/>')

    # Font units put Y upwards, SVG puts it down, hence the negative scale.
    # The translate lands the ink box's top-left corner on the padding corner.
    origin_x = PAD_X - x0 * scale
    origin_y = PAD_Y + y1 * scale
    body = (
        f'<g fill="{color}" transform="translate({origin_x:.2f} {origin_y:.2f}) '
        f'scale({scale:.6f} {-scale:.6f})">\n' + "\n".join(paths) + "\n</g>"
    )
    label = " ".join(LINES)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{label}, written in the Sheikah alphabet">\n{body}\n</svg>\n'
    )
    return svg, width, height


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, default=ROOT / "tools" / "sheikah.ttf")
    args = parser.parse_args()

    if not args.font.is_file():
        raise SystemExit(
            f"error: no font at {args.font}\n"
            "Drop a Sheikah .ttf there, or pass --font with its path."
        )

    OUT_DIR.mkdir(exist_ok=True)
    for mode in palette.MODES:
        font = TTFont(args.font)  # the pens consume the glyph set, so reload
        svg, width, height = build(font, palette.theme(mode)["ink"])
        path = OUT_DIR / f"sheikah-{mode}.svg"
        path.write_text(svg, encoding="utf-8")
        print(
            f"wrote {path.relative_to(ROOT)}  "
            f"({width}x{height}, {path.stat().st_size:,} bytes)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
