"""Keep the Drive folder stocked ~2 weeks ahead (consume-down queue).

For every queue slot in the forward window [anchor .. anchor+LEAD_DAYS),
where anchor = max(today, queue start): render the item if needed, copy it
to the dated names (YYYY-MM-DD_AM.mp4 / .txt), and upload BOTH to the shared
Drive folder. Forward-only — never resurrects an already-consumed past slot.

First run from the start date with LEAD_DAYS=14 => 28 files (2 weeks, the
1-week safety buffer). Run it weekly (you do this Sunday-ish) and it tops the
window back to ~2 weeks; idempotent, so only the new ~14 get rendered/uploaded.

  .\\.venv\\Scripts\\python.exe scripts\\stock_drive.py            # do it
  .\\.venv\\Scripts\\python.exe scripts\\stock_drive.py --dry-run  # plan only
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "output"
QUEUE = OUT / "queue.json"
LEAD_DAYS = int(os.environ.get("STOCK_LEAD_DAYS", "14"))


def main() -> int:
    dry = "--dry-run" in sys.argv
    if not QUEUE.exists():
        print("No output/queue.json — run scripts/build_queue.py first.")
        return 1
    plan = json.loads(QUEUE.read_text(encoding="utf-8"))
    queue = plan["queue"]
    start = datetime.strptime(plan["start_date"], "%Y-%m-%d").date()

    today = date.today()
    anchor = max(today, start)
    horizon = anchor + timedelta(days=LEAD_DAYS)
    window = [q for q in queue
              if anchor <= datetime.strptime(q["date"], "%Y-%m-%d").date() < horizon]

    print(f"window {anchor} .. {horizon} ({LEAD_DAYS}d) -> {len(window)} slots"
          + (" [DRY-RUN]" if dry else ""))

    if not dry:
        import gdrive
        from generate import build

    rendered = uploaded = skipped = 0
    for q in window:
        base = q["basename"]
        mp4 = OUT / f"{base}.mp4"
        txt = OUT / f"{base}.txt"

        if not dry and gdrive.exists(f"{base}.mp4"):
            skipped += 1
            continue

        if dry:
            print(f"  WOULD stock {base}  item {q['item']:>3}  "
                  f"{q['variant_type']:<8} {q['book']} · {q['parent_law']}")
            continue

        if not (mp4.exists() and txt.exists()):
            r = build(q["item"])  # renders item_NNN.* + item_NNN_post.txt
            shutil.copyfile(r["video"], mp4)
            shutil.copyfile(r["post_pack"], txt)
            rendered += 1

        gdrive.upload(mp4, mime="video/mp4")
        gdrive.upload(txt, mime="text/plain")
        uploaded += 1
        print(f"  stocked {base}  (item {q['item']})")

    if dry:
        print(f"plan: {len(window)} slots in window")
    else:
        print(f"done: {rendered} rendered, {uploaded} uploaded, "
              f"{skipped} already in Drive")
    return 0


if __name__ == "__main__":
    sys.exit(main())
