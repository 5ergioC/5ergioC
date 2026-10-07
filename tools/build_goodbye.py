#!/usr/bin/env python3
"""Composite the farewell GIF onto transparency as an APNG.

    python tools/build_goodbye.py

Writes Images/Goodbye.png from Images/Goodbye.gif.

The source has a near-white baked background that reads as a bright rectangle
in dark mode. An APNG carries a real alpha channel, so the character floats on
the page in either theme. A transparent GIF cannot: its 1-bit transparency
would leave a hard white fringe on every antialiased edge.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageSequence

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "Images" / "Goodbye.gif"
OUT = ROOT / "Images" / "Goodbye.png"

WIDTH = 300
WHITE_FLOOR = 195  # darkest channel above this counts as paper, not artwork
EDGE_GAIN = 8
# An RGBA APNG of the untouched source weighs 2.2 MB, which is not a
# reasonable thing to serve on every profile view. Halving the frames and
# quantising to a flat cartoon palette brings it under the original GIF with
# no visible loss.
FRAME_STEP = 2
PALETTE_COLORS = 32


def main() -> int:
    frames = []
    for index, frame in enumerate(ImageSequence.Iterator(Image.open(SOURCE))):
        if index % FRAME_STEP:
            continue
        rgb = frame.convert("RGB")
        if rgb.width > WIDTH:
            rgb = rgb.resize((WIDTH, round(rgb.height * WIDTH / rgb.width)), Image.LANCZOS)
        # Key on the darkest channel, not luminance: bright yellow is almost as
        # luminous as the paper background, but its blue channel is not.
        red, green, blue = rgb.split()
        darkest = ImageChops.darker(ImageChops.darker(red, green), blue)
        alpha = darkest.point(
            lambda v: 255 if v < WHITE_FLOOR else max(0, 255 - (v - WHITE_FLOOR) * EDGE_GAIN)
        )
        # Quantise after keying, so the alpha ramp keeps its full 8 bits.
        rgba = rgb.quantize(colors=PALETTE_COLORS).convert("RGBA")
        rgba.putalpha(alpha)
        frames.append(rgba)

    source = Image.open(SOURCE)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=source.info.get("duration", 80) * FRAME_STEP,
        loop=0,
        disposal=1,
        optimize=True,
    )
    print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
