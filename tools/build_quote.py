#!/usr/bin/env python3
"""Build the closing quote as FIGlet lettering, in two theme SVGs.

    python tools/build_quote.py [--font dos_rebel]

Writes Images/quote-{dark,light}.svg.

The letters come from a real FIGlet font via pyfiglet (`pip install pyfiglet`).
An earlier version drew the text in Impact and sampled it down to a grid, and
that is what made it look wrong: at seven cells a letter, Impact's tiny
counters closed up, so g, o, a and e came out as solid lumps, and the "shadow"
was whatever sliver the offset happened to leave. A FIGlet font was drawn by
hand on the grid, with its counters held open on purpose, which is the whole
reason it reads as lettering.

Every cell is drawn as geometry, never as text. Whether U+2588 fills its
advance width, and how dense U+2591 looks, depend on the reader's font: in
GitHub's monospace the light shade is nearly as solid as the full block, which
is what flattened the original "Bye bye". Here:

  full and half blocks   solid rectangles, merged along each row
  shades (light..dark)   the same cells filled with a scanline pattern,
                         sparser for lighter shades
  box drawing            thin strokes, for fonts that outline their shadow

Cells are a whole number of pixels, twice as tall as wide like a terminal's,
so rows meet without the hairline seams fractional edges leave behind.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palette  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "Images"

LINES = [
    "In case I don't see ya...",
    "good afternoon, good evening,",
    "and good night!",
]

FONT = "dos_rebel"
MAX_WIDTH = 848  # the widest the page should carry
LINE_GAP = 1  # blank rows between figlet lines

# Solid geometry, as (x, y, w, h) fractions of a cell.
BLOCKS = {
    "█": (0, 0, 1, 1),
    "▀": (0, 0, 1, 0.5),
    "▄": (0, 0.5, 1, 0.5),
    "▌": (0, 0, 0.5, 1),
    "▐": (0.5, 0, 0.5, 1),
}
# Shades become scanline fills; the value is the pattern id.
SHADES = {"░": "light", "▒": "medium", "▓": "heavy"}
# Pixels of ink per scanline period, per shade.
SCANLINES = {"light": (1, 3), "medium": (1, 2), "heavy": (2, 3)}

# Double-line box drawing, as stroke segments in cell fractions: (x0, y0, x1, y1).
# The two rails sit at A and B; each glyph connects toward the edges it names.
A, B = 0.34, 0.66
BOX = {
    "═": [(0, A, 1, A), (0, B, 1, B)],
    "║": [(A, 0, A, 1), (B, 0, B, 1)],
    "╔": [(A, A, 1, A), (A, A, A, 1), (B, B, 1, B), (B, B, B, 1)],
    "╗": [(0, A, B, A), (B, A, B, 1), (0, B, A, B), (A, B, A, 1)],
    "╚": [(A, 0, A, B), (A, B, 1, B), (B, 0, B, A), (B, A, 1, A)],
    "╝": [(B, 0, B, B), (0, B, B, B), (A, 0, A, A), (0, A, A, A)],
}
STROKE = 0.22  # box stroke thickness, as a fraction of the cell width


def figlet_rows(font: str) -> list[str]:
    try:
        import pyfiglet
    except ImportError:
        raise SystemExit("error: pyfiglet is not installed.  pip install pyfiglet")

    rows: list[str] = []
    rendered = []
    for line in LINES:
        art = pyfiglet.figlet_format(line, font=font, width=4000).rstrip("\n").split("\n")
        # Trim blank margins figlet leaves above and below each line.
        while art and not art[0].strip():
            art.pop(0)
        while art and not art[-1].strip():
            art.pop()
        rendered.append(art)

    widest = max(len(row.rstrip()) for art in rendered for row in art)
    for index, art in enumerate(rendered):
        width = max(len(row.rstrip()) for row in art)
        indent = " " * ((widest - width) // 2)  # centre each line on the widest
        rows.extend(indent + row.rstrip() for row in art)
        if index < len(rendered) - 1:
            rows.extend([""] * LINE_GAP)
    return rows


def rect(x: float, y: float, w: float, h: float) -> str:
    return f"M{x:g} {y:g}h{w:g}v{h:g}h{-w:g}z"


def geometry(rows: list[str], cell_w: int, cell_h: int) -> tuple[str, dict[str, str]]:
    """Solid path data, plus one path's worth of data per shade."""
    solid: list[str] = []
    shaded: dict[str, list[str]] = {name: [] for name in SCANLINES}
    stroke = max(1.0, STROKE * cell_w)

    for row_index, row in enumerate(rows):
        y = row_index * cell_h
        column = 0
        while column < len(row):
            char = row[column]
            # Merge runs of the same block or shade along the row: one rect per
            # run instead of one per cell, and no seams between neighbours.
            run = 1
            while column + run < len(row) and row[column + run] == char:
                run += 1
            x = column * cell_w

            if char in BLOCKS:
                fx, fy, fw, fh = BLOCKS[char]
                if fw == 1:
                    solid.append(rect(x, y + fy * cell_h, run * cell_w, fh * cell_h))
                else:
                    for offset in range(run):
                        solid.append(rect(x + (offset + fx) * cell_w, y,
                                          fw * cell_w, cell_h))
            elif char in SHADES:
                shaded[SHADES[char]].append(rect(x, y, run * cell_w, cell_h))
            elif char in BOX:
                for offset in range(run):
                    left = x + offset * cell_w
                    for x0, y0, x1, y1 in BOX[char]:
                        sx, sy = left + x0 * cell_w, y + y0 * cell_h
                        ex, ey = left + x1 * cell_w, y + y1 * cell_h
                        if y0 == y1:  # horizontal stroke
                            solid.append(rect(sx, sy - stroke / 2, ex - sx, stroke))
                        else:  # vertical stroke
                            solid.append(rect(sx - stroke / 2, sy, stroke, ey - sy))
            column += run

    return "".join(solid), {name: "".join(parts) for name, parts in shaded.items()}


def build(color: str, rows: list[str], cell_w: int, cell_h: int) -> tuple[str, int, int]:
    columns = max(len(row) for row in rows)
    width, height = columns * cell_w, len(rows) * cell_h
    solid, shaded = geometry(rows, cell_w, cell_h)

    patterns = "".join(
        f'<pattern id="{name}" width="{cell_w}" height="{period}" '
        f'patternUnits="userSpaceOnUse">'
        f'<rect width="{cell_w}" height="{ink}" fill="{color}"/></pattern>'
        for name, (ink, period) in SCANLINES.items()
        if shaded[name]
    )
    fills = "".join(
        f'<path d="{data}" fill="url(#{name})"/>'
        for name, data in shaded.items()
        if data
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{" ".join(LINES)}" '
        f'shape-rendering="crispEdges">\n'
        + (f"<defs>{patterns}</defs>\n" if patterns else "")
        + fills
        + f'\n<path d="{solid}" fill="{color}"/>\n</svg>\n'
    )
    return svg, width, height


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", default=FONT)
    parser.add_argument("--out", default="quote", help="stem; -dark.svg and -light.svg appended")
    args = parser.parse_args()

    rows = figlet_rows(args.font)
    columns = max(len(row) for row in rows)
    # Whole pixels, so cell edges land on pixel edges.
    cell_w = max(1, MAX_WIDTH // columns)
    cell_h = cell_w * 2

    OUT_DIR.mkdir(exist_ok=True)
    for mode in palette.MODES:
        svg, width, height = build(palette.theme(mode)["ink"], rows, cell_w, cell_h)
        path = OUT_DIR / f"{args.out}-{mode}.svg"
        path.write_text(svg, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}  ({width}x{height}, "
              f"{columns} cols, cell {cell_w}x{cell_h}, {path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
