"""Pull live performance data on recent Reels from the IG Graph API.

NOTE: This token has `instagram_basic` + `instagram_content_publish` but NOT
`instagram_manage_insights`, so the /insights endpoint returns OAuthException #10.
We fetch like_count + comments_count directly off /{media_id} instead, which is
all the API exposes without the insights scope.
"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

GRAPH = "https://graph.facebook.com/v21.0"
FIELDS = "id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count"


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
    print(f"{'date':<10}  {'kind':<6}  {'likes':>5}  {'comm':>4}  caption")
    print("-" * 78)

    total_likes = total_comments = 0
    for m in items:
        ts = m.get("timestamp", "?")[:10]
        cap = (m.get("caption", "") or "")[:55].replace("\n", " ")
        permalink = m.get("permalink", "")
        kind = m.get("media_product_type") or m.get("media_type") or "?"
        likes = m.get("like_count", 0)
        comments = m.get("comments_count", 0)
        total_likes += likes
        total_comments += comments
        print(f"{ts}  {kind:<6}  {likes:>5}  {comments:>4}  {cap}")
        if permalink:
            print(f"{'':10}  {'':6}  {'':5}  {'':4}  {permalink}")

    print("-" * 78)
    print(f"Totals across {len(items)} posts: {total_likes} likes, {total_comments} comments")
    print("\n(plays/reach/saves/shares require instagram_manage_insights — not granted on this token)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
