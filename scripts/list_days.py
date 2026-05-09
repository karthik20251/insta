"""Print every day in quotes.json so the user can see all 49 are present."""
import json
from pathlib import Path

data = json.loads((Path(__file__).parent.parent / "quotes.json").read_text(encoding="utf-8"))
print(f"Total days in quotes.json: {len(data['days'])}\n")
for x in data["days"]:
    h = x["headline"]
    print(f"  Day {x['day']:2d}  |  {x['title']:18s}  |  {h[:55]}")
