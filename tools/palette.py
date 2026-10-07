#!/usr/bin/env python3
"""The one place every generator reads its colours from.

    python tools/palette.py            # print the active palette
    python tools/palette.py --list     # print all of them

Change ACTIVE, re-run the build scripts, and the whole page moves together.
Keeping this in one module is the only reason a palette swap is a one-line
edit instead of six.

Roles, not colour names, so a palette can be swapped without renaming
anything:

    bg      the panel behind framed pieces
    border  the frame around them
    head    section rules and the DOS prompt: the loudest thing on the card
    key     field labels
    value   field values, the highest-contrast text
    dim     leader dots and other furniture that should recede
    accent  numbers and anything that earns a second glance
    ink     flat art with no panel behind it (the quote, Comic Sans, Sheikah)
    snake   the contribution snake itself, against the dot grid behind it

Every role except `dim` clears 4.4:1 against both its own panel and GitHub's
page background, checked in both themes. `dim` is leader dots and rules: it is
meant to recede, and sits near 1.5:1 on purpose.

`ramp(mode, steps)` interpolates the ASCII-portrait shading from the darkest
tone to the brightest, so a new palette never has to hand-list nine hexes.
"""

from __future__ import annotations

import argparse

ACTIVE = "wordart"

PALETTES = {
    # Taken from the Welcome WordArt, so the page reads as one thing:
    # #5f24be primary, #a62cc1 secondary, #39c9fe for the numbers.
    #
    # The two purples are used as given on white. On black they measure
    # 2.4:1 and 3.7:1, under what small text needs, so dark mode lightens
    # them along their own hue rather than picking different colours.
    # #39c9fe has the opposite problem: 10.7:1 on black, 1.9:1 on white, so
    # the light theme darkens it instead.
    "wordart": {
        "dark": {
            "bg": "#06030c",
            "border": "#9869e3",
            "head": "#ba44d4",
            "key": "#9869e3",
            "value": "#f2ecff",
            "dim": "#38156f",
            "accent": "#39c9fe",
            "ink": "#9869e3",
            "snake": "#39c9fe",
            "ramp_lo": "#1c0b38",
            "ramp_hi": "#ac87e8",
        },
        "light": {
            "bg": "#ffffff",
            "border": "#5f24be",
            "head": "#a62cc1",
            "key": "#5f24be",
            "value": "#18092f",
            "dim": "#d6c3f4",
            "accent": "#016f98",
            "ink": "#5f24be",
            "snake": "#016f98",
            "ramp_lo": "#e7ddf9",
            "ramp_hi": "#3c1778",
        },
    },
    # A green phosphor CRT. The original look.
    "green": {
        "dark": {
            "bg": "#000000",
            "border": "#00ff41",
            "head": "#00ff41",
            "key": "#00ff41",
            "value": "#d6ffe0",
            "dim": "#00521a",
            "accent": "#7cffb0",
            "ink": "#00ff41",
            "snake": "#7cffb0",
            "ramp_lo": "#00330d",
            "ramp_hi": "#00ff41",
        },
        "light": {
            "bg": "#ffffff",
            "border": "#0f6b2a",
            "head": "#0f6b2a",
            "key": "#0f6b2a",
            "value": "#04240f",
            "dim": "#b7d6c0",
            "accent": "#127a45",
            "ink": "#0f6b2a",
            "snake": "#127a45",
            "ramp_lo": "#d8ece0",
            "ramp_hi": "#03551f",
        },
    },
    # Purple CRT with a magenta rule and a cyan accent: three hues doing
    # three jobs, so the eye can tell a heading from a label from a number.
    "purple": {
        "dark": {
            "bg": "#050208",
            "border": "#a970ff",
            "head": "#ff6bd6",
            "key": "#a970ff",
            "value": "#efe6ff",
            "dim": "#3d2168",
            "accent": "#5ce1e6",
            "ink": "#a970ff",
            "snake": "#5ce1e6",
            "ramp_lo": "#1e0f36",
            "ramp_hi": "#c9a4ff",
        },
        "light": {
            "bg": "#ffffff",
            "border": "#6b32b8",
            "head": "#b0208c",
            "key": "#6b32b8",
            "value": "#1c0b33",
            "dim": "#d3c2ea",
            "accent": "#0f6f86",
            "ink": "#6b32b8",
            "snake": "#0f6f86",
            "ramp_lo": "#e6dcf5",
            "ramp_hi": "#3d1470",
        },
    },
    # A monochrome amber terminal, for when the colour should stay out of
    # the way entirely.
    "amber": {
        "dark": {
            "bg": "#0a0600",
            "border": "#ffb000",
            "head": "#ffb000",
            "key": "#ffb000",
            "value": "#fff0d0",
            "dim": "#5c3d00",
            "accent": "#ffd980",
            "ink": "#ffb000",
            "snake": "#ffd980",
            "ramp_lo": "#2e1c00",
            "ramp_hi": "#ffb000",
        },
        "light": {
            "bg": "#ffffff",
            "border": "#8a5a00",
            "head": "#8a5a00",
            "key": "#8a5a00",
            "value": "#2b1c00",
            "dim": "#e0cfa8",
            "accent": "#a06a00",
            "ink": "#8a5a00",
            "snake": "#a06a00",
            "ramp_lo": "#f0e4c8",
            "ramp_hi": "#6b4400",
        },
    },
}

MODES = ("dark", "light")

# Cap height, in displayed pixels, shared by the three single-line text pieces:
# the greeting, the Comic Sans line and the Sheikah line. Each generator
# converts it to a font size through its own typeface's proportions, because
# 24px of Consolas, Comic Sans and Sheikah runes are three different point
# sizes. Measured, they had drifted to 13, 27 and 29.
TEXT_HEIGHT = 24


def theme(mode: str, palette: str | None = None) -> dict:
    return PALETTES[palette or ACTIVE][mode]


def _channels(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[index : index + 2], 16) for index in (0, 2, 4))


def mix(low: str, high: str, amount: float) -> str:
    """Blend two hex colours; amount 0 gives `low`, 1 gives `high`."""
    return "#" + "".join(
        f"{round(a + (b - a) * amount):02x}"
        for a, b in zip(_channels(low), _channels(high))
    )


def ramp(mode: str, steps: int, palette: str | None = None) -> list[str | None]:
    """Shading ramp for the ASCII portrait, darkest first.

    Index 0 is None: it belongs to the space character, which is never
    painted, so the list lines up with photo2ascii's glyph ramp.
    """
    colors = theme(mode, palette)
    low, high = colors["ramp_lo"], colors["ramp_hi"]
    return [None] + [
        mix(low, high, step / (steps - 2)) for step in range(steps - 1)
    ]


def snake_outputs() -> str:
    """The `outputs:` block for Platane/snk, one line per theme.

    The contribution snake is rendered by a GitHub Action, not by these
    scripts, so its colours would otherwise be a second place to remember to
    edit. The workflow interpolates this instead.
    """
    lines = []
    for mode, filename in (("light", "snake.svg"), ("dark", "snake-dark.svg")):
        colors = theme(mode)
        dots = [colors["bg"]] + [
            mix(colors["ramp_lo"], colors["ramp_hi"], step / 3) for step in range(4)
        ]
        lines.append(
            f"Images/{filename}?color_snake={colors['snake']}"
            f"&color_dots={','.join(dots)}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--snake", action="store_true",
                        help="print the Platane/snk outputs block and exit")
    args = parser.parse_args()

    if args.snake:
        print(snake_outputs())
        return 0

    names = PALETTES if args.list else {ACTIVE: PALETTES[ACTIVE]}
    for name in names:
        marker = "  <- ACTIVE" if name == ACTIVE else ""
        print(f"\n{name}{marker}")
        for mode in MODES:
            colors = theme(mode, name)
            joined = "  ".join(f"{role}={colors[role]}" for role in
                               ("bg", "head", "key", "value", "dim", "accent", "snake"))
            print(f"  {mode:5s} {joined}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
