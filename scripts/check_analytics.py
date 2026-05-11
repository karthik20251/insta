"""Pull live performance data on recent Reels from the IG Graph API."""
import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

GRAPH = "https://graph.facebook.com/v21.0"


def main() -> int:
    user_id = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]

    # Get the 5 most recent media items
    r = requests.get(f"{GRAPH}/{user_id}/media",
                     params={"fields": "id,caption,media_type,timestamp,permalink",
                             "limit": "10", "access_token": token},
                     timeout=30)
    r.raise_for_status()
    items = r.json().get("data", [])
    print(f"Found {len(items)} recent posts.\n")

    for m in items[:5]:
        mid = m["id"]
        ts = m.get("timestamp", "?")[:10]
        cap = (m.get("caption", "") or "")[:60].replace("\n", " ")
        permalink = m.get("permalink", "")
        media_type = m.get("media_type", "?")

        # Pull insights — different metrics for REELS vs IMAGE
        if media_type == "VIDEO":
            metrics = "plays,reach,saved,shares,comments,likes,total_interactions"
        else:
            metrics = "reach,saved,shares,comments,likes,total_interactions"

        try:
            ins = requests.get(f"{GRAPH}/{mid}/insights",
                               params={"metric": metrics, "access_token": token},
                               timeout=30).json()
            data = ins.get("data", [])
            stats = {d["name"]: d["values"][0]["value"] for d in data if d.get("values")}
        except Exception as e:
            stats = {"_error": str(e)[:100]}

        print(f"{ts}  [{media_type}]  {cap}...")
        print(f"   plays={stats.get('plays', '-'):>5}  reach={stats.get('reach', '-'):>5}  "
              f"likes={stats.get('likes', '-'):>3}  comments={stats.get('comments', '-'):>3}  "
              f"saves={stats.get('saved', '-'):>3}  shares={stats.get('shares', '-'):>3}")
        if permalink:
            print(f"   {permalink}")
        if "_error" in stats:
            print(f"   ERR: {stats['_error']}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
