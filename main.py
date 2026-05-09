"""Daily orchestrator: figure out which day → build video → upload → post to IG."""
from __future__ import annotations
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

from generate import build, total_days
from post import build_caption, post_reel

load_dotenv()

ROOT = Path(__file__).parent


def current_day() -> int:
    """Day 1 on START_DATE; clamps at total_days() (computed from quotes.json)."""
    start = os.environ.get("START_DATE")
    if not start:
        raise RuntimeError("START_DATE not set (format YYYY-MM-DD)")
    start_d = datetime.strptime(start, "%Y-%m-%d").date()
    today = date.today()
    n = (today - start_d).days + 1
    total = total_days()
    if n < 1:
        raise RuntimeError(f"Today is before START_DATE ({start_d}); nothing to post")
    if n > total:
        raise SystemExit(f"Series complete (day {n} > {total}). Nothing to post.")
    return n


def upload_to_public_url(local_video: Path) -> str:
    """Return a publicly reachable URL for the video.

    Two free options — pick one by setting UPLOAD_BACKEND env var:
      - 'github'   : commit the file into a public GitHub repo's `output/` and use the raw URL
                     (set GITHUB_RAW_BASE, e.g. https://raw.githubusercontent.com/USER/REPO/main/output/)
      - 'transfer' : upload to https://transfer.sh (free, ephemeral, ~14-day retention)
    """
    backend = os.environ.get("UPLOAD_BACKEND", "github").lower()

    if backend == "github":
        base = os.environ.get("GITHUB_RAW_BASE", "").rstrip("/")
        if not base:
            raise RuntimeError("GITHUB_RAW_BASE not set")
        # The workflow commits the output/ folder before this runs
        return f"{base}/{local_video.name}"

    if backend == "transfer":
        import requests
        with open(local_video, "rb") as f:
            r = requests.put(f"https://transfer.sh/{local_video.name}", data=f, timeout=300)
        r.raise_for_status()
        return r.text.strip()

    raise RuntimeError(f"Unknown UPLOAD_BACKEND: {backend}")


def main() -> int:
    day_num = current_day()
    print(f"==> Day {day_num}/{total_days()}")

    result = build(day_num)
    print(f"  built video: {result['video']}")

    if "--dry-run" in sys.argv:
        print("  --dry-run: skipping upload + post")
        return 0

    video_url = upload_to_public_url(result["video"])
    print(f"  public url: {video_url}")

    caption = build_caption(result["day"])
    media_id = post_reel(video_url, caption)
    print(f"  posted: media_id={media_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
