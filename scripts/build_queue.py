"""Generate the deterministic posting queue (the consume-down plan).

CURATED 2026-06-04: dropped from 276 -> 66 items based on engagement data.
Generic motivation posts plateaued at 10-50 views/post (engagement rate ~2%,
0 organic comments across 7 days). Best performers were SPECIFIC NARRATIVE
posts on workplace/power dynamics (May 28: 182 views, May 30: 106 views).

Curation = (only viral-worthy parents) x (only narrative variants).
  Kept variants: SCENARIO, MISTAKE  (TACTIC variants dropped — too generic)
  Kept parents: 33 of 92 — listed in KEEP_* sets below

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
# TACTIC variants are dry/principle-based — dropped because SCENARIO + MISTAKE
# variants outperformed them by 3-10x in real engagement data.
VARIANTS = ("MISTAKE", "SCENARIO")
# 2026-06-04: dropped AM slot per user direction. Morning post is now manual
# (midday-image + trending audio in CapCut, uploaded by user). The automated
# pipeline ships only the evening post.
SLOTS = ("PM",)
PER_DAY = len(SLOTS)

# 2026-06-08: TIER A only mode per user direction ("Use Tier A").
# After scoring all 65 curated items on Trending + Useful, kept only the 8
# items that scored T>=5 AND U>=4. Maximum signal density per post; cycles
# every 8 days. Tradeoff: same teases repeat ~4x per month.
#
# To go back to broader curation: comment out KEEP_TIER_A_ITEMS and restore
# the KEEP_48LAWS / KEEP_ATOMIC / KEEP_RULES sets below.
# 2026-06-08 v2: MARKET-TRENDING items only (user direction "market level
# trending lines"). Researched June 2026 viral patterns in office/career
# niche: quiet firing, stealth layoffs, AI-driven cuts, PIP warnings,
# RTO-as-exit-pressure, workplace anxiety confessional. Each item was
# brand-new-written (items 277-284) to target a specific 2026 zeitgeist
# theme. Cycles every 8 days like before, but every tease now hits a
# theme with active market saturation.
KEEP_TIER_A_ITEMS = (
    277,  # Day 1: QUIET FIRING — "Three things your boss does the week before quietly pushing you out"
    278,  # Day 2: LAYOFF SIGNAL — "Her director stopped including her in decisions..."
    279,  # Day 3: PIP WARNING — "He missed one deadline. By Friday his calendar was full of check-ins"
    280,  # Day 4: AI LAYOFF — "Her job got optimized with AI in three months..."
    281,  # Day 5: STEALTH FIRING — "His projects started getting reassigned temporarily..."
    282,  # Day 6: WORKPLACE ANXIETY — "He looked unbothered in every all-hands. He was rage-applying..."
    283,  # Day 7: RTO POLITICS — "She was the only one called back to the office full-time..."
    284,  # Day 8: LAYOFF SURVIVOR — "Tech layoffs hit her team. She was the one who documented..."
)

# Tier B/C fallback sets (used only if KEEP_TIER_A_ITEMS commented out).
KEEP_48LAWS = {f"Law {n}" for n in (
    1, 3, 4, 6, 7, 11, 13, 14, 15, 16, 17, 20, 25, 27, 33, 36, 38, 45, 46, 47
)}
KEEP_ATOMIC = {
    "Identity", "Compound Effect", "The Plateau", "Habit Stacking",
    "Two-Minute Rule", "Environment", "Never Miss Twice", "Goldilocks",
}
KEEP_RULES = {f"Rule {n}" for n in (1, 2, 4, 6, 8)}


def _keep_item(it: dict) -> bool:
    """Filter an item from quotes.json. Default mode: TIER A only (8 items).
    Fallback mode: viral-worthy parent + narrative variant (65 items)."""
    if KEEP_TIER_A_ITEMS:
        return it["item"] in KEEP_TIER_A_ITEMS
    if it["variant_type"] not in VARIANTS:
        return False
    if it["book"] == "The 48 Laws of Power":
        return it["parent_law"] in KEEP_48LAWS
    if it["book"] == "Atomic Habits":
        return it["parent_law"] in KEEP_ATOMIC
    if it["book"] == "12 Rules for Life":
        return it["parent_law"] in KEEP_RULES
    return False


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
    items = [it for it in data["items"] if _keep_item(it)]
    by_key = {(it["parent_law"], it["variant_type"]): it for it in items}
    porder = parent_order(items)
    n_parents = len(porder)
    n_variants = len(VARIANTS)
    # Sanity: filtered set size depends on mode.
    if KEEP_TIER_A_ITEMS:
        assert len(items) == len(KEEP_TIER_A_ITEMS), (
            f"expected {len(KEEP_TIER_A_ITEMS)} TIER A items, got {len(items)}"
        )
    else:
        expected = (len(KEEP_48LAWS) + len(KEEP_ATOMIC) + len(KEEP_RULES)) * n_variants
        assert len(items) == expected, f"expected {expected} items after curation, got {len(items)}"

    sd = start_date()
    queue = []
    if KEEP_TIER_A_ITEMS:
        # TIER A mode: skip the (parent x variant) round-robin — Tier A items
        # don't have all (parent, variant) combinations, so the round-robin
        # would request missing combos and crash. Instead, enumerate items
        # in the explicit KEEP_TIER_A_ITEMS order so the rotation honors
        # user intent (highest-score items get the first cycle dates).
        ordered_items = [next(it for it in items if it["item"] == iid)
                         for iid in KEEP_TIER_A_ITEMS]
        for k, it in enumerate(ordered_items):
            day_idx, slot_idx = divmod(k, PER_DAY)
            d = sd + timedelta(days=day_idx)
            base = f"{d.isoformat()}_{SLOTS[slot_idx]}"
            queue.append({
                "pos": k + 1,
                "date": d.isoformat(),
                "slot": SLOTS[slot_idx],
                "basename": base,
                "item": it["item"],
                "book": it["book"],
                "parent_law": it["parent_law"],
                "variant_type": it["variant_type"],
            })
    else:
        # Curated-pool mode: round-robin interleave parents x variants so no
        # parent's variants land adjacent (max variety per week).
        for k in range(len(items)):
            variant = VARIANTS[k % n_variants]
            parent = porder[k % n_parents]
            it = by_key.get((parent, variant))
            if it is None:
                raise KeyError(f"missing quote for parent={parent!r} variant={variant!r}")
            day_idx, slot_idx = divmod(k, PER_DAY)
            d = sd + timedelta(days=day_idx)
            base = f"{d.isoformat()}_{SLOTS[slot_idx]}"
            queue.append({
                "pos": k + 1,
                "date": d.isoformat(),
                "slot": SLOTS[slot_idx],
                "basename": base,
                "item": it["item"],
                "book": it["book"],
                "parent_law": it["parent_law"],
                "variant_type": variant,
            })

    # Hard-constraint self-check: no parent's variants adjacent. (Tier A mode
    # may have adjacent same-parent items if KEEP_TIER_A_ITEMS lists them so —
    # the user-controlled order wins over the no-adjacency constraint.)
    if not KEEP_TIER_A_ITEMS:
        bad = [q["pos"] for i, q in enumerate(queue[1:], 1)
               if q["parent_law"] == queue[i - 1]["parent_law"]]
        assert not bad, f"adjacency violation at {bad[:5]}"

    OUT.write_text(json.dumps({
        "start_date": sd.isoformat(),
        "total": len(queue),
        "per_day": PER_DAY,
        "queue": queue,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    last = queue[-1]
    print(f"queue: {len(queue)} posts, {sd.isoformat()} -> {last['date']} "
          f"({len(queue)//PER_DAY} days @ {PER_DAY}/day) -> {OUT}")
    print("first 6:")
    for q in queue[:6]:
        print(f"  {q['basename']}  item {q['item']:>3}  {q['variant_type']:<8} "
              f"{q['book']}  · {q['parent_law']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
