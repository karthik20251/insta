"""Print every item in quotes.json so the user can see what's available.

2026-06-05: migrated from old data['days'] schema to current data['items']
schema (each item = parent_law × variant_type = up to 3 variants per
parent). Output now shows item id, parent, variant, headline.
"""
import json
from pathlib import Path

data = json.loads((Path(__file__).parent.parent / "quotes.json").read_text(encoding="utf-8"))
items = data["items"]
print(f"Total items in quotes.json: {len(items)}\n")
for x in items:
    h = x.get("headline", "")
    parent = x.get("parent_law", "")
    variant = x.get("variant_type", "")
    print(f"  Item {x['item']:3d}  |  {parent:18s}  |  {variant:8s}  |  {h[:50]}")
