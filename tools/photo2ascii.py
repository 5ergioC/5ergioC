#!/usr/bin/env python3
"""Turn a photo into the ASCII portrait used by the FACE card.

    python tools/photo2ascii.py tools/face-cut.png --width 104 --trim \
        --gamma 0.55 --sharpen

Writes two plain-text blocks, tools/portrait-dark.txt and
tools/portrait-light.txt. build_portrait.py reads the one matching the theme
and paints it with the palette, so this script only cares about shape and tone.

One plate cannot serve both themes. Ink on paper is dark, so on white the
glyphs have to land on the shadows and the page shows through as skin. Ink on
a terminal is light, so on black the glyphs have to land on the lit areas and
the panel shows through as shadow. Put either plate on the wrong background
and the portrait reads as a negative: solid where it should be empty, and so
faint it nearly vanishes. Each theme therefore gets its own, and the polarity
is not a flag anyone can set wrong.

Why the flags exist, in the order they matter for a face:

--crop      A photo of a person in a room is mostly room. At the widths a
            README can carry, anything but a tight head crop turns into noise.
--oval      Fades the corners out so the room behind the head drops out. It is
            a blunt instrument: an ellipse keeps whatever happens to fall
            inside it. Cutting the subject out properly and saving a PNG with
            an alpha channel beats it every time, and this script uses that
            alpha as the mask automatically when it finds one.
--trim      Crops to whatever the cutout actually covers, so the subject fills
            the frame instead of floating in the margin it was exported with.
--gamma     Below 1 it lifts the midtones. Flat indoor light leaves skin in
            the middle of the range, where every glyph looks the same; this
            pushes skin to the sparse end and leaves hair, eyes and mouth as
            the only dense marks.
--levels    Fewer tones than the full ramp. Ten shades of a face at this size
            read as mud.
--dither    Error diffusion, and the single thing that makes a photograph
            legible here. Straight quantisation loses every feature; diffusing
            the error trades tonal precision for apparent detail, the way a
            newspaper halftone does.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

# Dark -> light. build_portrait.py maps each glyph back to a shade, so the
# order here is the single source of truth for the whole pipeline.
RAMP = " .:-=+*#%@"

# Monospace cells are roughly twice as tall as they are wide.
CELL_ASPECT = 0.5


# Per theme: whether bright pixels become dense glyphs, and what the masked
# background turns into so that it disappears rather than filling with ink.
POLARITY = {
    "dark": {"invert": False, "matte": 0},
    "light": {"invert": True, "matte": 255},
}


def prepare(image: Image.Image, args: argparse.Namespace, matte: int) -> Image.Image:
    if args.crop:
        image = image.crop(args.crop)

    # A hand-cut PNG carries its own mask, and a designer's cutout beats any
    # ellipse this script could draw. Keep the alpha and matte the rest away.
    cutout = None
    if image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    ):
        rgba = image.convert("RGBA")
        alpha = rgba.getchannel("A")
        if alpha.getextrema()[0] < 255:
            cutout = alpha
            if args.trim:
                bounds = alpha.getbbox()
                if bounds:
                    rgba = rgba.crop(bounds)
                    cutout = alpha.crop(bounds)
        image = rgba

    image = image.convert("L")
    if cutout is not None:
        image = Image.composite(image, Image.new("L", image.size, matte), cutout)

    image = ImageOps.autocontrast(image, cutoff=1)
    if args.sharpen:
        image = image.filter(
            ImageFilter.UnsharpMask(radius=8, percent=160, threshold=2)
        )
    if args.contrast != 1.0:
        image = ImageEnhance.Contrast(image).enhance(args.contrast)
    if args.gamma != 1.0:
        image = image.point(lambda v: round(255 * (v / 255) ** args.gamma))

    if args.oval:
        mask = Image.new("L", image.size, 0)
        ImageDraw.Draw(mask).ellipse(
            (-image.width * 0.06, -image.height * 0.04,
             image.width * 1.06, image.height * 1.04),
            fill=255,
        )
        mask = mask.filter(ImageFilter.GaussianBlur(image.width * 0.09))
        image = Image.composite(image, Image.new("L", image.size, matte), mask)

    return image


def to_ascii(image: Image.Image, args: argparse.Namespace, invert: bool) -> str:
    height = max(1, round(args.width * image.height / image.width * CELL_ASPECT))
    small = image.resize((args.width, height), Image.LANCZOS)

    levels = args.levels or len(RAMP)
    grays = [round(index * 255 / (levels - 1)) for index in range(levels)]
    palette = Image.new("P", (1, 1))
    palette.putpalette(
        sum(([gray] * 3 for gray in grays), []) + [0, 0, 0] * (256 - levels)
    )
    quantized = small.convert("RGB").quantize(
        palette=palette,
        dither=Image.FLOYDSTEINBERG if args.dither else Image.NONE,
    )

    indices = list(quantized.getdata())
    step = (len(RAMP) - 1) / (levels - 1)
    rows = []
    for row in range(height):
        line = indices[row * args.width : (row + 1) * args.width]
        rows.append(
            "".join(
                RAMP[len(RAMP) - 1 - round(index * step)] if invert
                else RAMP[round(index * step)]
                for index in line
            ).rstrip()
        )
    return "\n".join(rows)


def box(text: str) -> tuple[int, int, int, int]:
    parts = tuple(int(part) for part in text.split(","))
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("crop takes four numbers: left,top,right,bottom")
    return parts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--width", type=int, default=104)
    parser.add_argument("--out", type=Path, default=Path("tools/portrait"),
                        help="stem; -dark.txt and -light.txt are appended")
    parser.add_argument("--crop", type=box, help="left,top,right,bottom in pixels")
    parser.add_argument("--levels", type=int, help=f"tones to keep (max {len(RAMP)})")
    parser.add_argument("--gamma", type=float, default=1.0)
    parser.add_argument("--contrast", type=float, default=1.0)
    parser.add_argument("--dither", action="store_true")
    parser.add_argument("--oval", action="store_true",
                        help="fade the corners into the matte")
    parser.add_argument("--trim", action="store_true",
                        help="crop to the cutout's bounds (needs an alpha channel)")
    parser.add_argument("--sharpen", action="store_true")
    args = parser.parse_args()

    if not args.image.is_file():
        print(f"error: no such image: {args.image}", file=sys.stderr)
        return 1
    if args.levels and not 2 <= args.levels <= len(RAMP):
        print(f"error: --levels must be 2..{len(RAMP)}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    for mode, how in POLARITY.items():
        plate = prepare(Image.open(args.image), args, how["matte"])
        art = to_ascii(plate, args, how["invert"])
        path = args.out.with_name(f"{args.out.name}-{mode}.txt")
        path.write_text(art + "\n", encoding="utf-8")
        rows = art.count("\n") + 1
        print(f"wrote {path}  ({args.width} cols x {rows} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
