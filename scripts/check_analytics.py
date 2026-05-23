"""Pull live performance data on recent Reels from the IG Graph API.

Requires `instagram_manage_insights` on the token (use scripts/ig_auth_insights.py
to mint one). Without that scope, per-Reel views/reach/watch-time are hidden
and only like_count / comments_count come back.
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

GRAPH = "https://graph.facebook.com/v21.0"
FIELDS = "id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count"
# Reels insight metrics (v22+ — `plays` removed, replaced by `views`).
INSIGHT_METRICS = (
    "views,reach,saved,shares,total_interactions,"
    "ig_reels_video_view_total_time,ig_reels_avg_watch_time"
)


def fetch_insights(media_id: str, token: str) -> dict:
    r = requests.get(f"{GRAPH}/{media_id}/insights",
                     params={"metric": INSIGHT_METRICS, "access_token": token}, timeout=30)
    if r.status_code != 200:
        return {}
    return {x["name"]: x["values"][0]["value"] for x in r.json().get("data", [])}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    user_id = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]

    r = requests.get(f"{GRAPH}/{user_id}/media",
                     params={"fields": FIELDS, "limit": "10", "access_token": token},
                     timeout=30)
    r.raise_for_status()
    items = r.json().get("data", [])
    print(f"Found {len(items)} recent posts.\n")
    print(f"{'date':<10}  {'views':>5}  {'reach':>5}  {'likes':>5}  {'comm':>4}  {'saved':>5}  {'share':>5}  {'avgW(s)':>7}  caption")
    print("-" * 110)

    tot = {"views": 0, "reach": 0, "likes": 0, "comments": 0, "saved": 0, "shares": 0}
    for m in items:
        ts = m.get("timestamp", "?")[:10]
        cap = (m.get("caption", "") or "")[:50].replace("\n", " ")
        permalink = m.get("permalink", "")
        likes = m.get("like_count", 0)
        comments = m.get("comments_count", 0)
        ins = fetch_insights(m["id"], token)
        views = ins.get("views", 0)
        reach = ins.get("reach", 0)
        saved = ins.get("saved", 0)
        shares = ins.get("shares", 0)
        avg_ms = ins.get("ig_reels_avg_watch_time", 0)
        avg_s = round(avg_ms / 1000, 1) if avg_ms else 0
        for k, v in (("views", views), ("reach", reach), ("likes", likes),
                     ("comments", comments), ("saved", saved), ("shares", shares)):
            tot[k] += v
        print(f"{ts}  {views:>5}  {reach:>5}  {likes:>5}  {comments:>4}  {saved:>5}  {shares:>5}  {avg_s:>7}  {cap}")
        if permalink:
            print(f"{'':10}  {'':>5}  {'':>5}  {'':>5}  {'':>4}  {'':>5}  {'':>5}  {'':>7}  {permalink}")

    print("-" * 110)
    print(f"Totals ({len(items)} posts): views={tot['views']}  reach={tot['reach']}  "
          f"likes={tot['likes']}  comm={tot['comments']}  saved={tot['saved']}  shares={tot['shares']}")
    if tot["views"]:
        eng = (tot["likes"] + tot["comments"] + tot["saved"] + tot["shares"]) / tot["views"] * 100
        print(f"Engagement rate (likes+comm+saves+shares / views): {eng:.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
