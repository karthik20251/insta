"""Audit quotes.json for completeness and consistency."""
import json
from pathlib import Path

data = json.loads((Path(__file__).parent.parent / "quotes.json").read_text(encoding="utf-8"))
days = data["days"]
print(f"Total days: {len(days)}\n")

nums = [d["day"] for d in days]
expected = list(range(1, max(nums) + 1))
missing = set(expected) - set(nums)
duplicates = [n for n in nums if nums.count(n) > 1]
print(f"Sequence: {nums[0]} - {nums[-1]}")
print(f"Missing days: {missing if missing else 'none'}")
print(f"Duplicate days: {set(duplicates) if duplicates else 'none'}\n")

fields = ["day", "title", "headline", "body"]
issues = []
for d in days:
    for f in fields:
        if f not in d:
            issues.append(f'Day {d.get("day", "?")} missing field: {f}')
if issues:
    for i in issues:
        print("  " + i)
else:
    print("All required fields present.\n")

books = {}
for d in days:
    b = d.get("book", data["book"])
    books.setdefault(b, []).append(d["day"])
print("Days per book:")
for b, ds in books.items():
    print(f"  {b}: {len(ds)} days  (day {min(ds)} to {max(ds)})")

# Show body lengths to flag any unusually short/long ones
print("\nBody-length outliers (chars):")
lens = sorted([(len(d["body"]), d["day"], d["title"]) for d in days])
for L, day_n, title in lens[:3]:
    print(f"  shortest: Day {day_n} ({title}): {L} chars")
for L, day_n, title in lens[-3:]:
    print(f"  longest:  Day {day_n} ({title}): {L} chars")
