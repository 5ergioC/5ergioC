#!/usr/bin/env python3
"""Render the README's images side by side, dark theme against light.

    python tools/preview.py            # writes preview.html
    python tools/preview.py --open     # and opens it

GitHub picks between the two <source> elements from the reader's theme, so a
browser only ever shows one of them. This lays both out at once, at the widths
the README asks for, which is the only way to catch a piece that works in one
theme and disappears in the other.

The list of images is read out of README.md rather than kept here, so a piece
added to the page shows up in the preview without touching this file. HTML
comments are stripped first: a block commented out of the README is not part
of the page and should not be part of its preview either.

Everything is inlined as a data: URI, so the result is one self-contained file
that survives being sent somewhere else. That makes it a few MB; it is
gitignored.
"""

from __future__ import annotations

import argparse
import base64
import mimetypes
import re
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
OUT = ROOT / "preview.html"

COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
PICTURE = re.compile(r"<picture>(.*?)</picture>", re.DOTALL)
SOURCE = re.compile(r'<source[^>]*prefers-color-scheme:\s*(dark|light)[^>]*'
                    r'srcset="([^"]+)"')
IMG = re.compile(r'<img[^>]*src="([^"]+)"[^>]*>')
WIDTH = re.compile(r'width="(\d+)"')

# What GitHub paints behind the page in each theme.
PAGE = {"dark": ("#0d1117", "#30363d"), "light": ("#ffffff", "#d1d9e0")}


def data_uri(src: str) -> str | None:
    path = ROOT / src.lstrip("./")
    if not path.is_file():
        print(f"  warning: README points at a missing file: {src}")
        return None
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def pieces(markdown: str) -> list[dict]:
    """Every image the rendered page shows, in order, with its two variants."""
    found = []
    position = 0
    for block in PICTURE.finditer(markdown):
        # Any bare <img> between the previous <picture> and this one.
        for tag in IMG.finditer(markdown[position:block.start()]):
            found.append(_single(tag))
        sources = dict(SOURCE.findall(block.group(1)))
        fallback = IMG.search(block.group(1))
        found.append({
            "dark": sources.get("dark"),
            "light": sources.get("light"),
            "width": _width(fallback.group(0)) if fallback else None,
        })
        position = block.end()
    for tag in IMG.finditer(markdown[position:]):
        found.append(_single(tag))
    return [piece for piece in found if piece["dark"] and piece["light"]]


def _single(tag: re.Match) -> dict:
    src = tag.group(1)
    return {"dark": src, "light": src, "width": _width(tag.group(0))}


def _width(tag: str) -> int | None:
    match = WIDTH.search(tag)
    return int(match.group(1)) if match else None


def panel(mode: str, found: list[dict]) -> str:
    background, edge = PAGE[mode]
    rows = []
    for piece in found:
        uri = data_uri(piece[mode])
        if uri is None:
            continue
        style = f"width:{piece['width']}px" if piece["width"] else "width:auto"
        rows.append(f'<img src="{uri}" style="{style}">')
    return (
        f'<section style="background:{background};border-color:{edge}">'
        f"<h2>GITHUB {mode.upper()}</h2>" + "".join(rows) + "</section>"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open", action="store_true", help="open it when done")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    found = pieces(COMMENT.sub("", README.read_text(encoding="utf-8")))
    if not found:
        raise SystemExit("error: found no images in README.md")

    html = (
        '<meta charset="utf-8"><title>readme-lab preview</title>\n'
        "<style>\n"
        " body{margin:0;background:#161b22;font:13px system-ui;"
        "display:flex;gap:18px;padding:18px;align-items:flex-start}\n"
        " section{flex:1;min-width:0;border:1px solid;border-radius:8px;"
        "padding:26px;text-align:center}\n"
        " h2{font:11px/1 ui-monospace,monospace;color:#8b949e;"
        "letter-spacing:.12em;margin:0 0 22px}\n"
        " img{display:block;margin:0 auto 26px;max-width:100%;height:auto}\n"
        "</style>\n"
        + panel("dark", found)
        + panel("light", found)
    )
    args.out.write_text(html, encoding="utf-8")
    print(f"wrote {args.out}  ({len(found)} images, "
          f"{args.out.stat().st_size / 1e6:.1f} MB)")
    if args.open:
        webbrowser.open(args.out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
