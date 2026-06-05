"""Audit quotes.json for completeness and consistency.

2026-06-05: migrated from old data['days'] schema to current data['items'].
Reports item counts, missing/duplicate item ids, required-field coverage,
items-per-book + items-per-variant_type distribution, and body-length
outliers (very short bodies tend to feel under-rendered; very long ones
get truncated by the TTS word budget).
"""
import json
from pathlib import Path

data = json.loads((Path(__file__).parent.parent / "quotes.json").read_text(encoding="utf-8"))
items = data["items"]
print(f"Total items: {len(items)}\n")

nums = sorted(it["item"] for it in items)
expected = list(range(1, max(nums) + 1))
missing = set(expected) - set(nums)
duplicates = [n for n in nums if nums.count(n) > 1]
print(f"Item id range: {nums[0]} - {nums[-1]}")
print(f"Missing item ids: {missing if missing else 'none'}")
print(f"Duplicate item ids: {set(duplicates) if duplicates else 'none'}\n")

fields = ["item", "title", "headline", "body", "tease", "comment_q", "parent_law", "variant_type", "book"]
issues = []
for it in items:
    for f in fields:
        if f not in it or not str(it.get(f, "")).strip():
            issues.append(f'Item {it.get("item", "?")} missing/empty field: {f}')
if issues:
    for i in issues[:20]:
        print("  " + i)
    if len(issues) > 20:
        print(f"  ... and {len(issues) - 20} more")
else:
    print("All required fields present.\n")

books = {}
for it in items:
    b = it.get("book", "?")
    books.setdefault(b, []).append(it["item"])
print("\nItems per book:")
for b, ids in books.items():
    print(f"  {b}: {len(ids)} items  (id {min(ids)} - {max(ids)})")

variants = {}
for it in items:
    v = it.get("variant_type", "?")
    variants.setdefault(v, 0)
    variants[v] += 1
print("\nItems per variant type:")
for v, n in sorted(variants.items()):
    print(f"  {v}: {n}")

print("\nBody-length outliers (chars):")
lens = sorted([(len(it.get("body", "")), it["item"], it.get("title", "?"), it.get("variant_type", "?")) for it in items])
for L, n, title, var in lens[:3]:
    print(f"  shortest: Item {n} ({title} {var}): {L} chars")
for L, n, title, var in lens[-3:]:
    print(f"  longest:  Item {n} ({title} {var}): {L} chars")
