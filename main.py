"""Daily orchestrator: figure out which day → build video → upload → post to IG."""
from __future__ import annotations
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from generate import build, corporate_caption, ordered_item, total_days
from post import post_reel, post_story
from post_youtube import build_youtube_metadata, upload_short, short_url

load_dotenv()

ROOT = Path(__file__).parent
IST = timezone(timedelta(hours=5, minutes=30))


def today_ist() -> date:
    """Single source of truth for 'today'. Everything date-related in this file
    uses IST so current_day() and the idempotency guards can never disagree on
    the date boundary (the old bug: current_day used runner-local UTC)."""
    return datetime.now(timezone.utc).astimezone(IST).date()


def ig_today_count() -> int | None:
    """Count IG posts dated today (IST). Used for SLOT-AWARE 2/day dedupe:
    the AM slot skips if >=1 today, the PM slot skips if >=2 today — so each
    slot is idempotent on re-run, max 2/day, and the 2nd post can never be
    silently eaten by an 'any post today' guard. Returns None on error
    (fail-open: a recoverable possible dup beats a silently-skipped slot)."""
    user_id = os.environ.get("IG_USER_ID")
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not user_id or not token:
        return None
    try:
        r = requests.get(
            f"https://graph.facebook.com/v21.0/{user_id}/media",
            params={"fields": "id,timestamp", "limit": "8", "access_token": token},
            timeout=15,
        )
        r.raise_for_status()
        today = today_ist()
        n = 0
        for m in r.json().get("data", []):
            ts = m.get("timestamp", "")
            if ts and datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S%z").astimezone(IST).date() == today:
                n += 1
        return n
    except Exception:
        return None


def yt_posted_today() -> tuple[bool, str]:
    """True if the YouTube channel already has a video dated today (IST).

    NOTE: listing the channel's own uploads needs a `youtube.readonly`-class
    scope. The current token is `youtube.upload` (+ `yt-analytics.readonly`
    once the re-auth lands — which is retention, NOT uploads-listing). So this
    check FAILS OPEN today: it returns False, meaning YT is always attempted.
    Worst case = the pre-existing duplicate risk on a manual re-run, never the
    dangerous mode (permanent YT loss). Activating real YT dedupe is a one-line
    follow-up: add `youtube.readonly` at the next re-auth (NOT silently expanded
    here — scope changes require explicit approval).
    """
    try:
        from post_youtube import get_credentials  # noqa: PLC0415 — optional path
        from googleapiclient.discovery import build as gbuild

        yt = gbuild("youtube", "v3", credentials=get_credentials(), cache_discovery=False)
        ch = yt.channels().list(part="contentDetails", mine=True).execute()
        uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        pl = yt.playlistItems().list(part="snippet", playlistId=uploads, maxResults=1).execute()
        items = pl.get("items", [])
        if not items:
            return False, "YT: no prior uploads (proceeding)"
        published = items[0]["snippet"]["publishedAt"]  # ISO8601 Z
        pub_ist = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc).astimezone(IST).date()
        if pub_ist == today_ist():
            return True, f"YT: already uploaded today ({today_ist()})"
        return False, f"YT: last upload {pub_ist}, today {today_ist()} (proceeding)"
    except Exception as e:
        # Expected until a youtube.readonly re-auth: fail open (YT attempted).
        return False, f"YT dedupe unavailable (fail-open, YT will be attempted): {type(e).__name__}"


def current_day() -> int:
    """Day 1 on START_DATE; clamps at total_days() (computed from quotes.json)."""
    start = os.environ.get("START_DATE")
    if not start:
        raise RuntimeError("START_DATE not set (format YYYY-MM-DD)")
    start_d = datetime.strptime(start, "%Y-%m-%d").date()
    n = (today_ist() - start_d).days + 1
    total = total_days()
    if n < 1:
        raise RuntimeError(f"Today is before START_DATE ({start_d}); nothing to post")
    if n > total:
        raise SystemExit(f"Series complete (day {n} > {total}). Nothing to post.")
    return n


def current_slot() -> int:
    """0 = AM, 1 = PM. Set by the workflow per cron (POST_SLOT env);
    manual runs default to AM."""
    return 1 if os.environ.get("POST_SLOT", "AM").strip().upper() == "PM" else 0


def current_position() -> int:
    """1-based posting position for 2/day: two slots per day. Single source
    of truth shared by the workflow's build step AND main(), so the
    committed/raw-URL video is exactly the one that gets posted."""
    pos = (current_day() - 1) * 2 + current_slot() + 1
    total = total_days()
    if pos > total:
        raise SystemExit(f"Series complete (position {pos} > {total}).")
    return pos


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
        url = f"{base}/{local_video.name}"
        # raw.githubusercontent.com CDN lags 1-5 min after a fresh push. IG
        # fetches this URL immediately; a 404 pre-propagation = failed post
        # (a known, babysat failure mode). Turn the race into a bounded wait:
        # HEAD-poll to 200, ceiling 60s, then proceed and let the post path
        # surface a real failure rather than hang. Already-propagated = first
        # HEAD is 200 -> zero added latency on the happy path.
        for attempt in range(12):
            try:
                h = requests.head(url, timeout=10, allow_redirects=True)
                if h.status_code == 200:
                    if attempt:
                        print(f"  raw URL propagated after {attempt * 5}s")
                    return url
            except requests.RequestException:
                pass
            time.sleep(5)
        print("  WARN: raw URL not confirmed 200 after 60s — proceeding anyway")
        return url

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
    pos = current_position()                       # 2/day, slot-aware
    slot = current_slot()
    day_num = ordered_item(pos)  # interleaved order: no variant trio back-to-back
    print(f"==> Position {pos}/{total_days()}  slot={'PM' if slot else 'AM'}  -> item {day_num}")

    # Slot-aware idempotency for 2/day: AM skips if >=1 post today, PM skips
    # if >=2. Each slot idempotent on re-run; max 2/day; the 2nd post can't
    # be eaten by an 'any post today' guard. Fail-open on count error.
    cnt = ig_today_count()
    if cnt is None:
        ig_skip, ig_reason = False, "IG dedupe unavailable (fail-open, proceeding)"
    else:
        ig_skip = cnt >= (slot + 1)
        ig_reason = f"IG: {cnt} post(s) today; slot {'PM' if slot else 'AM'} " \
                    f"{'already done -> skip' if ig_skip else 'proceeding'}"
    yt_skip, yt_reason = yt_posted_today()
    print(f"  [idempotency] {ig_reason}")
    print(f"  [idempotency] {yt_reason}")
    if ig_skip and yt_skip:
        print("  both platforms already have this slot — nothing to do")
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
    caption = corporate_caption(day)  # repositioned caption, same as the pack

    # Instagram (gated)
    if ig_skip:
        print(f"  [skip IG] {ig_reason}")
    else:
        media_id = post_reel(video_url, caption)
        print(f"  posted reel: media_id={media_id}")
        write_github_output(media_id=media_id)
        # Story best-effort — only when we actually posted the Reel
        try:
            story_id = post_story(video_url)
            print(f"  shared to story: media_id={story_id}")
            write_github_output(story_id=story_id)
        except Exception as e:
            print(f"  WARN: story share failed (non-fatal): {e}")

    # YouTube (gated, best-effort)
    if yt_skip:
        print(f"  [skip YT] {yt_reason}")
    else:
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
