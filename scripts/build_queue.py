"""Generate the full deterministic posting queue (the consume-down plan).

276 items -> 138 days x {AM, PM}. The order guarantees a law's
TACTIC/MISTAKE/SCENARIO never post back-to-back (they land ~92 posts /
~46 days apart) and that books + variant types stay mixed post-to-post.

This writes output/queue.json — a pure plan, no rendering. stock_drive.py
consumes it to materialize + upload the next ~2 weeks of dated files.

Run:
  .\\.venv\\Scripts\\python.exe scripts\\build_queue.py [YYYY-MM-DD]
(start date also via env QUEUE_START_DATE; default = next Monday)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
QUOTES = ROOT / "quotes.json"
OUT = ROOT / "output" / "queue.json"
VARIANTS = ("TACTIC", "MISTAKE", "SCENARIO")
SLOTS = ("AM", "PM")


def _next_monday(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)


def start_date() -> date:
    raw = (len(sys.argv) > 1 and sys.argv[1]) or os.environ.get("QUEUE_START_DATE", "")
    if raw:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    return _next_monday(date.today())


def parent_order(items: list[dict]) -> list[str]:
    """92 parents, evenly interleaved across the 3 books (largest book most
    frequent) so the feed is never 49 Laws then 30 Atomic then 13 Rules."""
    by_book: dict[str, list[str]] = {}
    for it in items:
        lst = by_book.setdefault(it["book"], [])
        if it["parent_law"] not in lst:
            lst.append(it["parent_law"])
    spread: list[tuple[float, int, str, str]] = []
    for book, parents in by_book.items():
        n = len(parents)
        for i, p in enumerate(parents):
            # fractional position in [0,1): evenly distributes each book
            spread.append(((i + 0.5) / n, -n, book, p))
    spread.sort()
    return [p for _, _, _, p in spread]


def main() -> int:
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    items = data["items"]
    # index by (parent_law, variant_type) -> item number
    by_key = {(it["parent_law"], it["variant_type"]): it for it in items}
    porder = parent_order(items)
    assert len(porder) == 92, f"expected 92 parents, got {len(porder)}"

    sd = start_date()
    queue = []
    for k in range(len(items)):
        variant = VARIANTS[k % 3]
        parent = porder[k % 92]
        it = by_key[(parent, variant)]
        day_idx, slot = divmod(k, 2)
        d = sd + timedelta(days=day_idx)
        base = f"{d.isoformat()}_{SLOTS[slot]}"
        queue.append({
            "pos": k + 1,
            "date": d.isoformat(),
            "slot": SLOTS[slot],
            "basename": base,
            "item": it["item"],
            "book": it["book"],
            "parent_law": it["parent_law"],
            "variant_type": variant,
        })

    # Hard-constraint self-check: no parent's variants adjacent.
    bad = [q["pos"] for i, q in enumerate(queue[1:], 1)
           if q["parent_law"] == queue[i - 1]["parent_law"]]
    assert not bad, f"adjacency violation at {bad[:5]}"

    OUT.write_text(json.dumps({
        "start_date": sd.isoformat(),
        "total": len(queue),
        "per_day": 2,
        "queue": queue,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    last = queue[-1]
    print(f"queue: {len(queue)} posts, {sd.isoformat()} -> {last['date']} "
          f"({len(queue)//2} days @ 2/day) -> {OUT}")
    print("first 6:")
    for q in queue[:6]:
        print(f"  {q['basename']}  item {q['item']:>3}  {q['variant_type']:<8} "
              f"{q['book']}  · {q['parent_law']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
