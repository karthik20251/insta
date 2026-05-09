"""Post a Reel to Instagram via the Graph API.

Requires:
- IG_USER_ID            — Instagram Business Account ID
- IG_ACCESS_TOKEN       — long-lived user access token
- PUBLIC_VIDEO_URL      — a publicly reachable URL to the .mp4 (Graph API needs a URL, not a file)

Caption is built from the day entry.
"""
from __future__ import annotations
import os
import time
import requests

GRAPH = "https://graph.facebook.com/v21.0"


def build_caption(day: dict) -> str:
    parts = [
        day["headline"],
        "",
        day["body"],
        "",
        f"— {day['author']}, {day['book']}",
        "",
        f"Day {day['day']} of 49 · The 48 Laws of Power series",
        "",
        "Music: Kevin MacLeod (incompetech.com), CC-BY 4.0",
        "",
        "#48lawsofpower #robertgreene #power #wisdom #mindset #selfimprovement #strategy #philosophy #books #dailyquotes",
    ]
    return "\n".join(parts)


def post_reel(video_url: str, caption: str) -> str:
    user_id = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]

    # 1. Create container
    r = requests.post(
        f"{GRAPH}/{user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": token,
        },
        timeout=60,
    )
    r.raise_for_status()
    creation_id = r.json()["id"]

    # 2. Wait for IG to ingest the video
    for _ in range(30):
        s = requests.get(
            f"{GRAPH}/{creation_id}",
            params={"fields": "status_code", "access_token": token},
            timeout=30,
        ).json()
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise RuntimeError(f"IG ingestion error: {s}")
        time.sleep(10)
    else:
        raise TimeoutError("IG did not finish processing the video in time")

    # 3. Publish
    r = requests.post(
        f"{GRAPH}/{user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["id"]


if __name__ == "__main__":
    # smoke test
    print("post.py: import this module from main.py — do not call directly")
