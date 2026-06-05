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

from generate import build, corporate_caption, load_day, scheduled_item
from post import post_reel  # post_story intentionally not imported (manual Stories)
from post_youtube import build_youtube_metadata, upload_short, short_url, post_comment, build_yt_comment, yt_has_title

load_dotenv()

ROOT = Path(__file__).parent
IST = timezone(timedelta(hours=5, minutes=30))


def today_ist() -> date:
    """Single source of truth for 'today'. Everything date-related in this file
    uses IST so current_day() and the idempotency guards can never disagree on
    the date boundary (the old bug: current_day used runner-local UTC)."""
    return datetime.now(timezone.utc).astimezone(IST).date()


def ig_has_caption(first_line: str) -> bool | None:
    """PER-ITEM IG dedupe (replaces the broken count-based guard).

    Skip IG only if a recent IG post's caption already STARTS WITH this
    item's `tease` (the first line of corporate_caption, unique per item).
    Order-independent: PM landing before AM under cron drift can no longer
    cannibalize AM's IG post (the bug: YT got AM's item, IG didn't, because
    '>=1 post today' suppressed it). Each slot reaches IG with its OWN item;
    a true re-run of the same item correctly skips. None on error
    (fail-open: a recoverable dup beats a silently-missed post)."""
    user_id = os.environ.get("IG_USER_ID")
    token = os.environ.get("IG_ACCESS_TOKEN")
    if not user_id or not token:
        return None
    target = (first_line or "").strip()
    if not target:
        return None
    try:
        r = requests.get(
            f"https://graph.facebook.com/v21.0/{user_id}/media",
            params={"fields": "caption", "limit": "25", "access_token": token},
            timeout=15,
        )
        r.raise_for_status()
        for m in r.json().get("data", []):
            cap = (m.get("caption") or "").strip()
            if cap and cap.split("\n", 1)[0].strip() == target:
                return True
        return False
    except Exception:
        return None


# yt_posted_today() was REMOVED. It checked "any upload today" which broke
# the moment force-ssl unlocked the channels.list call: once AM uploaded, PM
# was permanently skipped for the rest of the day. Replaced with the per-item
# yt_has_title() in post_youtube.py — matches the IG per-item dedupe pattern.


def current_day() -> int:
    """Day number since START_DATE (1-based). PERPETUAL: there is no end /
    'series complete' stop. scheduled_item() now indexes into the CURATED
    queue.json (66 items, narrative variants only, viral-worthy parents
    only) and cycles perpetually past its end — nothing is ever dropped or
    deleted, posting continues forever.

    Note: scheduled_item internally uses queue.json's own start_date as the
    anchor (NOT this function's START_DATE) — different epochs, both work."""
    start = os.environ.get("START_DATE")
    if not start:
        raise RuntimeError("START_DATE not set (format YYYY-MM-DD)")
    start_d = datetime.strptime(start, "%Y-%m-%d").date()
    n = (today_ist() - start_d).days + 1
    if n < 1:
        raise RuntimeError(f"Today is before START_DATE ({start_d}); nothing to post")
    return n  # no upper bound — never stops


def current_slot() -> int:
    """0 = AM, 1 = PM. Set by the workflow per cron (POST_SLOT env);
    manual runs default to AM."""
    return 1 if os.environ.get("POST_SLOT", "AM").strip().upper() == "PM" else 0


# 2026-06-05: removed current_position(). It computed a 1-based posting
# position assuming 2/day cadence: (day-1)*2 + slot + 1. After the cadence
# shift to 1/day (commit 5e4a46c) the math is wrong; after scheduled_item
# was rewritten to use queue.json (commit 764be62) the function had no
# remaining callers either way — verified by grep. Removed.


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
        # NOTE: do NOT `import requests` here — a function-local import makes
        # `requests` local to this whole function and breaks the github
        # branch's requests.head with UnboundLocalError. Use the module import.
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
    day = current_day()
    slot = current_slot()                          # 0=AM technique-y, 1=PM book/story
    day_num = scheduled_item(day, slot)
    print(f"==> Day {day}  slot={'PM (book/story)' if slot else 'AM (technique)'}  -> item {day_num}")

    # Slot-aware idempotency for 2/day: AM skips if >=1 post today, PM skips
    # if >=2. Each slot idempotent on re-run; max 2/day; the 2nd post can't
    # be eaten by an 'any post today' guard. Fail-open on count error.
    _item = load_day(day_num)
    _has = ig_has_caption(_item.get("tease", ""))
    if _has is None:
        ig_skip, ig_reason = False, "IG dedupe unavailable (fail-open, proceeding)"
    else:
        ig_skip = _has
        ig_reason = ("IG: this exact item already on IG -> skip" if _has
                     else "IG: item not yet on IG -> proceeding")
    # Per-item YT dedupe: build the expected title for THIS slot's item and
    # check if it's already on the channel (new title format = tease + #Shorts,
    # so unique per item). Mirrors ig_has_caption's per-item pattern.
    _yt_target_title = build_youtube_metadata(_item)["title"]
    yt_skip, yt_reason = yt_has_title(_yt_target_title)
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
        item=day["item"],
        variant=day["variant_type"],
        slot=("PM (book/story)" if slot else "AM (technique)"),
        parent=day["parent_law"],
        book=day["book"],
        tease=day["tease"],
    )

    if "--dry-run" in sys.argv:
        print("  --dry-run: skipping upload + post")
        return 0

    video_url = upload_to_public_url(result["video"])
    print(f"  public url: {video_url}")
    caption = corporate_caption(day)  # repositioned caption, same as the pack

    # IG auto-post is back ON by default (2026-05-30). It was disabled after
    # the 05-23 Meta throttle (containers POSTing 200 but never FINISHED), but
    # that's a week stale now and the reliability patch since (raw-URL HEAD-
    # poll, per-platform idempotency) addresses the retry storm that caused
    # the throttle. The first cron after this change is the real test.
    # Kill switch: set repo variable IG_AUTOPOST_ENABLED=false in GitHub
    # (Settings -> Variables) to disable IG auto-post without a code change —
    # workflow falls back to emailing the manual pack.
    ig_autopost = os.environ.get("IG_AUTOPOST_ENABLED", "true").strip().lower() == "true"
    if not ig_autopost and not ig_skip:
        ig_skip = True
        ig_reason = "IG auto-post disabled via IG_AUTOPOST_ENABLED=false — see email pack"

    # Instagram + YouTube run INDEPENDENTLY: an IG flake used to bail the whole
    # script and silently skip YT too. Each platform's failure is captured and
    # re-raised AFTER both attempts, so one good post still goes out.
    failures: list[str] = []
    yt_url = None

    if ig_skip:
        print(f"  [skip IG] {ig_reason}")
    else:
        try:
            media_id = post_reel(video_url, caption)
            print(f"  posted reel: media_id={media_id}")
            write_github_output(media_id=media_id)
        except Exception as e:
            print(f"  ERROR: IG post failed: {type(e).__name__}: {e}")
            failures.append(f"IG: {type(e).__name__}: {e}")

    if yt_skip:
        print(f"  [skip YT] {yt_reason}")
    else:
        try:
            yt_meta = build_youtube_metadata(day)
            yt_id = upload_short(result["video"], yt_meta["title"], yt_meta["description"], yt_meta["tags"])
            yt_url = short_url(yt_id)
            print(f"  uploaded to youtube: {yt_url}")
            write_github_output(youtube_id=yt_id, youtube_url=yt_url)
            # Engagement comment — best-effort, NEVER fails the post. If the
            # token doesn't have force-ssl yet (one-off re-auth required after
            # this feature shipped), the upload still counts; just log and move
            # on. Same pattern as the YouTube best-effort block already used.
            try:
                comment_text = build_yt_comment(day)
                comment_id = post_comment(yt_id, comment_text)
                print(f"  posted yt comment: {comment_id}")
                write_github_output(youtube_comment_id=comment_id)
            except Exception as ce:
                print(f"  WARN: yt comment failed (non-fatal): {type(ce).__name__}: {ce}")
        except Exception as e:
            print(f"  ERROR: YT upload failed: {type(e).__name__}: {e}")
            failures.append(f"YT: {type(e).__name__}: {e}")

    # Always emit the manual-post pack — the success-email step ships this to
    # the owner's phone (paste-ready caption + comment_q + raw URL + video).
    # When IG auto is re-enabled this pack still ships harmlessly as a backup.
    pack_lines = [
        f"ITEM #{day['item']}  ·  {day['variant_type']}  ·  {day['parent_law']}  ·  {day['book']}",
        "",
        f"TEASE:  {day['tease']}",
        "",
        "------------ CAPTION (copy everything below this line) ------------",
        caption,
        "------------ END CAPTION ------------",
        "",
        "------------ PIN AS FIRST COMMENT ------------",
        day.get("comment_q", ""),
        "------------ END PIN ------------",
        "",
        f"Video URL:     {video_url}",
        f"Video file:    {result['video'].name} (attached to this email)",
        f"YouTube:       {yt_url or 'not uploaded this run'}",
        "",
        "INSTRUCTIONS (30 sec):",
        "  1. Save the attached video to your phone Camera Roll",
        "  2. Open Instagram -> Reels -> Add from gallery",
        "  3. Pick a TRENDING sound in-app (3-5x more reach than a muted post)",
        "  4. Paste the caption above",
        "  5. Post -> then add the PIN text as the first comment and pin it",
    ]
    pack_path = ROOT / "output" / "post_pack_email.txt"
    # Trailing newline matters: the daily.yml step reads this file into a
    # $GITHUB_OUTPUT heredoc. Without a final \n the cat output runs straight
    # into the closing delimiter token and GHA fails with "Matching delimiter
    # not found". The YAML now also writes its own \n before the delimiter
    # for belt-and-suspenders, but writing it here keeps the file readable.
    pack_path.write_text("\n".join(pack_lines) + "\n", encoding="utf-8")
    write_github_output(post_pack_path=str(pack_path.relative_to(ROOT)),
                        video_file_relpath=str(result["video"].relative_to(ROOT)))

    if failures:
        raise SystemExit("Post failures: " + " | ".join(failures))
    return 0


if __name__ == "__main__":
    sys.exit(main())
