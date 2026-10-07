#!/usr/bin/env python3
"""Cut the subject out of a photo, locally.

    python tools/cutout.py tools/face.jpg
    python tools/cutout.py tools/face.jpg --crop 365,105,655,480

Writes a PNG with an alpha channel next to the source (`<name>-cut.png`),
which photo2ascii.py then uses as its mask.

Runs entirely on this machine: the online background removers want the photo
uploaded to them, which is a poor trade for a picture of your own face. The
first run downloads a ~176 MB model to ~/.u2net and everything after that is
offline.

rembg is a heavy dependency (onnxruntime, numba, scikit-image) and only this
script needs it, which is why it is not imported anywhere else in tools/.

    pip install "rembg[cpu]"

--crop is applied before the cutout, in the source photo's pixels. Cropping
first is what decides how much of you ends up in the portrait: head only,
head and shoulders, or the whole pose.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

# u2net is the general model. u2net_human_seg is tuned for people, and
# isnet-general-use is sharper on hair but slower.
MODELS = ("u2net", "u2net_human_seg", "isnet-general-use")


def box(text: str) -> tuple[int, int, int, int]:
    parts = tuple(int(part) for part in text.split(","))
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("crop takes four numbers: left,top,right,bottom")
    return parts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--crop", type=box, help="left,top,right,bottom in pixels")
    parser.add_argument("--model", choices=MODELS, default="u2net")
    args = parser.parse_args()

    if not args.image.is_file():
        print(f"error: no such image: {args.image}", file=sys.stderr)
        return 1
    try:
        from rembg import new_session, remove
    except ImportError:
        print('error: rembg is not installed.  pip install "rembg[cpu]"', file=sys.stderr)
        return 1

    source = Image.open(args.image)
    if args.crop:
        source = source.crop(args.crop)

    cut = remove(source, session=new_session(args.model), post_process_mask=True)
    out = args.out or args.image.with_name(f"{args.image.stem}-cut.png")
    cut.save(out)

    bounds = cut.getchannel("A").getbbox()
    print(f"wrote {out}  ({cut.width}x{cut.height}, subject fills {bounds})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
