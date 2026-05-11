"""One-off: upload Day 2 + Day 3 (and any other specified days) to YouTube as Shorts.

Usage:
    .\\.venv\\Scripts\\python.exe scripts\\backfill_youtube.py 2 3
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from generate import load_day, OUT_DIR
from post_youtube import build_youtube_metadata, upload_short, short_url


def main() -> int:
    days = [int(d) for d in sys.argv[1:]] or [2, 3]
    print(f"Backfilling days {days} to YouTube...\n")

    for n in days:
        day = load_day(n)
        video = OUT_DIR / f"day_{n:02d}.mp4"
        if not video.exists():
            print(f"  [SKIP] Day {n}: {video} does not exist locally")
            continue

        meta = build_youtube_metadata(day)
        print(f"Day {n} - {day['title']}: {day['headline']}")
        print(f"  uploading {video.name} ({video.stat().st_size // 1024} KB)...")
        try:
            vid = upload_short(video, meta["title"], meta["description"], meta["tags"])
            print(f"  [OK] {short_url(vid)}\n")
        except Exception as e:
            print(f"  [FAIL] {e}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
