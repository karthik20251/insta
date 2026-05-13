"""Daily orchestrator: figure out which day → build video → upload → post to IG."""
from __future__ import annotations
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from generate import build, total_days
from post import build_caption, post_reel, post_story
from post_youtube import build_youtube_metadata, upload_short, short_url

load_dotenv()

ROOT = Path(__file__).parent
IST = timezone(timedelta(hours=5, minutes=30))


def already_posted_today_ist() -> tuple[bool, str]:
    """Idempotency guard: True if @nandetroll_ already has a post dated today (IST).

    Prevents duplicate posts when a manual `workflow_dispatch` run overlaps with a
    delayed scheduled run. Fails open: if the check itself errors (network, API
    blip), we proceed and let the real post call surface the failure -- better to
    risk one duplicate than to silently skip a real day.
    """
    user_id = os.environ.get("IG_USER_ID")
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not user_id or not token:
        return False, "IG env vars missing — skipping idempotency check"
    try:
        r = requests.get(
            f"https://graph.facebook.com/v21.0/{user_id}/media",
            params={"fields": "id,timestamp,permalink", "limit": "1", "access_token": token},
            timeout=15,
        )
        r.raise_for_status()
        items = r.json().get("data", [])
        if not items:
            return False, "no prior posts on the account"
        latest = items[0]
        ts_str = latest.get("timestamp", "")
        if not ts_str:
            return False, f"latest post {latest.get('id')} has no timestamp"
        latest_ist = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S%z").astimezone(IST).date()
        today_ist = datetime.now(timezone.utc).astimezone(IST).date()
        if latest_ist == today_ist:
            return True, f"already posted today ({today_ist}): {latest.get('permalink') or latest.get('id')}"
        return False, f"last post {latest_ist}, today {today_ist} — proceeding"
    except Exception as e:
        return False, f"idempotency check errored, proceeding anyway: {e}"


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


def write_github_output(**kv) -> None:
    """Expose values to subsequent workflow steps via $GITHUB_OUTPUT."""
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        for k, v in kv.items():
            f.write(f"{k}={v}\n")


def main() -> int:
    day_num = current_day()
    print(f"==> Day {day_num}/{total_days()}")

    skip, reason = already_posted_today_ist()
    print(f"  [idempotency] {reason}")
    if skip:
        write_github_output(day_num=day_num, skipped="true")
        return 0

    result = build(day_num)
    day = result["day"]
    print(f"  built video: {result['video']}")

    write_github_output(
        day_num=day_num,
        title=day["title"],
        headline=day["headline"],
        book=day["book"],
        book_day=day["book_day"],
        book_total=day["book_total"],
    )

    if "--dry-run" in sys.argv:
        print("  --dry-run: skipping upload + post")
        return 0

    video_url = upload_to_public_url(result["video"])
    print(f"  public url: {video_url}")

    caption = build_caption(day)
    media_id = post_reel(video_url, caption)
    print(f"  posted reel: media_id={media_id}")
    write_github_output(media_id=media_id)

    # Cross-post to Stories — best-effort, don't fail the run if it errors
    try:
        story_id = post_story(video_url)
        print(f"  shared to story: media_id={story_id}")
        write_github_output(story_id=story_id)
    except Exception as e:
        print(f"  WARN: story share failed (non-fatal): {e}")

    # Cross-post to YouTube as a Short — also best-effort
    try:
        yt_meta = build_youtube_metadata(day)
        yt_id = upload_short(result["video"], yt_meta["title"], yt_meta["description"], yt_meta["tags"])
        yt_url = short_url(yt_id)
        print(f"  uploaded to youtube: {yt_url}")
        write_github_output(youtube_id=yt_id, youtube_url=yt_url)
    except Exception as e:
        print(f"  WARN: youtube upload failed (non-fatal): {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
