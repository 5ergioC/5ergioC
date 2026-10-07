#!/usr/bin/env python3
"""Render the WHOAMI card as two theme-specific SVGs.

    python tools/build_card.py

Pulls live counters from the GitHub REST API and writes
Images/whoami-dark.svg and Images/whoami-light.svg.

Everything is plain <text>/<tspan>: no <style>, no scripts, no external fonts,
so it survives GitHub's camo proxy untouched. The DOS prompt is drawn inside
the SVG rather than in a Markdown code fence, so the card carries its own
title bar instead of GitHub's code-block chrome.

Live numbers are cached in tools/stats-cache.json, so a rate-limited or
offline build still emits a card instead of failing the workflow.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palette  # noqa: E402

USER = "5ergioC"
ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "tools" / "stats-cache.json"

# Repos whose diffs are committed data or vendored bundles rather than
# authored code. Counting them turns the line total into noise:
#   Reto-Capa-de-Datos  +3,523,160 / -0        a database dump
#   5ergioC.github.io     +499,054 / -5,020    built assets committed
# Together they are 87% of every line attributed to this account. Delete a
# name from this set to count that repo again.
SKIP_LINE_COUNTS = {"Reto-Capa-de-Datos", "5ergioC.github.io"}

WIDTH = 880
PAD_X, TOP, LEAP, BOTTOM = 26, 54, 27, 32
FONT_SIZE = 17
# Every rendered line is exactly this many characters and is stretched to
# TEXT_WIDTH with textLength, so the card fills its frame identically whether
# the reader's browser picks Consolas, Menlo or DejaVu Sans Mono. Without it
# the text ran ~200px short of the right edge on the narrower fonts.
LINE_CHARS = 78
TEXT_WIDTH = WIDTH - 2 * PAD_X

# Year of birth, nothing finer. An exact date of birth is the kind of thing
# account recovery questions are made of, and this lives in a public repo.
# Storing only the year means the age ticks over on 1 January instead of on
# the real birthday, which is the point: nothing here hints at the month. The
# cost is reading a year high between New Year and the actual birthday.
BIRTH_YEAR = 2005



# --------------------------------------------------------------------------- #
# data
# --------------------------------------------------------------------------- #

def _get(path: str, retries: int = 4):
    """GET one API path. 202 means GitHub is still computing; back off and retry."""
    request = urllib.request.Request(
        f"https://api.github.com/{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{USER}-readme-card",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    for attempt in range(retries):
        with urllib.request.urlopen(request, timeout=25) as response:
            if response.status == 202:
                time.sleep(2 * (attempt + 1))
                continue
            body = response.read()
        return json.loads(body) if body.strip() else None
    return None


def fetch_line_counts(repos: list[dict]) -> tuple[int, int]:
    """Sum the user's own additions and deletions across their own repos."""
    additions = deletions = 0
    for repo in repos:
        if repo["fork"] or repo["name"] in SKIP_LINE_COUNTS:
            continue
        contributors = _get(f"repos/{repo['full_name']}/stats/contributors")
        if not isinstance(contributors, list):
            print(f"  note: no line stats for {repo['name']}")
            continue
        for contributor in contributors:
            if (contributor.get("author") or {}).get("login") != USER:
                continue
            additions += sum(week["a"] for week in contributor["weeks"])
            deletions += sum(week["d"] for week in contributor["weeks"])
    return additions, deletions


def fetch_stats() -> dict:
    """Live counters, falling back to the last good cache on any failure."""
    try:
        user = _get(f"users/{USER}")
        repos = _get(f"users/{USER}/repos?per_page=100")
        # is:public pins the count: without it the number swells or shrinks
        # with whatever private repos the current token happens to see.
        commits = _get(f"search/commits?q=author:{USER}+is:public&per_page=1")
        additions, deletions = fetch_line_counts(repos)
        stats = {
            "repos": user["public_repos"],
            "followers": user["followers"],
            "stars": sum(repo["stargazers_count"] for repo in repos),
            "commits": commits["total_count"],
            "additions": additions,
            "deletions": deletions,
            "created_at": user["created_at"],
        }
        CACHE.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
        return stats
    except (urllib.error.URLError, KeyError, TypeError, ValueError, TimeoutError) as error:
        if not CACHE.is_file():
            raise SystemExit(f"error: GitHub API failed and no cache exists: {error}")
        print(f"warning: GitHub API failed ({error}); using {CACHE.name}")
        return json.loads(CACHE.read_text(encoding="utf-8"))


def uptime() -> str:
    years = datetime.now(timezone.utc).year - BIRTH_YEAR
    return f"{years} year{'s' * (years != 1)}"


# --------------------------------------------------------------------------- #
# svg
# --------------------------------------------------------------------------- #

def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def span(text: str, fill: str) -> str:
    return f'<tspan fill="{fill}">{escape(text)}</tspan>'


def field(
    key: str, value: str, theme: dict, width: int = LINE_CHARS, accent: bool = False
) -> str:
    """`Key: ....... value`, leader dots stretched to a fixed character width."""
    label = f"{key}: "
    pad = max(1, width - len(label) - len(value) - 1)
    return (
        span(label, theme["key"])
        + span("." * pad + " ", theme["dim"])
        + span(value, theme["accent"] if accent else theme["value"])
    )


def pair(left: tuple[str, str], right: tuple[str, str], theme: dict) -> str:
    """Two fields on one line, split down the middle of the card."""
    half = (LINE_CHARS - 5) // 2
    return (
        field(left[0], left[1], theme, half, accent=True)
        + span("  |  ", theme["dim"])
        + field(right[0], right[1], theme, LINE_CHARS - 5 - half, accent=True)
    )


def rule(title: str, theme: dict) -> str:
    label = f"{title} "
    return span(label, theme["head"]) + span("-" * (LINE_CHARS - len(label)), theme["dim"])


def build(theme: dict, stats: dict) -> str:
    net = stats["additions"] - stats["deletions"]
    lines: list[str | None] = [
        rule(f"C:\\USERS\\{USER.upper()}> WHOAMI", theme),
        None,
        field("Name", "Sergio Alejandro Castano Arcila", theme),
        field("OS", "Windows 95 (emotionally)", theme),
        field("Uptime", uptime(), theme),
        field("Host", "Universidad de los Andes", theme),
        field("Kernel", "Systems Engineering student", theme),
        field("Shell", "Bogota, Colombia", theme),
        None,
        field("Languages.Programming", "Python, Java, TypeScript, JavaScript", theme),
        field("Languages.Real", "Spanish, English", theme),
        field("Interests", "Cybersecurity, Graphic design, Cryptography", theme),
        field("Hobbies", "Gaming", theme),
        None,
        rule("- Contact", theme),
        field("Web", "5ergioc.github.io", theme),
        field("LinkedIn", "in/sergio-alejandro-castano-arcila", theme),
        None,
        rule("- Diagnostics", theme),
        pair(("Repos", f"{stats['repos']:,}"), ("Stars", f"{stats['stars']:,}"), theme),
        pair(("Commits", f"{stats['commits']:,}"),
             ("Followers", f"{stats['followers']:,}"), theme),
        field(
            "Lines of Code",
            f"{net:,}  ( +{stats['additions']:,} / -{stats['deletions']:,} )",
            theme,
            accent=True,
        ),
    ]

    height = TOP + (len(lines) - 1) * LEAP + BOTTOM
    body = [
        f'<text x="{PAD_X}" y="{TOP + index * LEAP}" '
        f'textLength="{TEXT_WIDTH}" lengthAdjust="spacingAndGlyphs" '
        f'xml:space="preserve">{line}</text>'
        for index, line in enumerate(lines)
        if line is not None
    ]

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" '
        f'aria-label="{USER}: Systems Engineering student at Universidad de los Andes, '
        f'Bogota, Colombia" '
        f'font-family="Consolas, &quot;DejaVu Sans Mono&quot;, Menlo, monospace" '
        f'font-size="{FONT_SIZE}px">\n'
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" '
        f'fill="{theme["bg"]}" stroke="{theme["border"]}"/>\n'
        + "\n".join(body)
        + "\n</svg>\n"
    )


def main() -> int:
    stats = fetch_stats()
    out_dir = ROOT / "Images"
    out_dir.mkdir(exist_ok=True)
    for mode in palette.MODES:
        path = out_dir / f"whoami-{mode}.svg"
        path.write_text(build(palette.theme(mode), stats), encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}  ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
