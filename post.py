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


# Rotating CTAs — variety keeps captions feeling fresh and tests which style drives engagement.
CTAS = [
    "Share your thoughts ⬇️",
    "Drop your take in the comments 👇",
    "Tag someone who needs this 🙏",
    "Save this for later 📌",
    "Which resonates? Comment below 💬",
    "Double tap if this hits 💯",
    "What would you add? 💭",
    "Send to a friend who needs it 📤",
    "Bookmark and reread tomorrow 📍",
    "Follow for daily wisdom 🌅",
    "Curious — drop a 🔥 if this rings true",
    "Your turn — share your story below 👇",
]


def build_caption(day: dict) -> str:
    book_day = day.get("book_day", day["day"])
    book_total = day.get("book_total", day.get("total_days", 92))
    book_lower = day["book"].lower()
    if "atomic habits" in book_lower:
        niche = "#atomichabits #jamesclear #habits #discipline #productivity #identity #books #booksofinstagram"
    elif "12 rules" in book_lower or "jordan peterson" in book_lower:
        niche = "#12rulesforlife #jordanpeterson #meaning #responsibility #philosophy #stoic #books #booksofinstagram"
    else:
        niche = "#48lawsofpower #robertgreene #power #wisdom #strategy #philosophy #books #booksofinstagram"

    reach = "#viral #reels #trending #fyp #explorepage #foryourpage #reachmore #getnoticed"
    growth = "#growthmindset #successmindset #keepgrowing #goalsetter #motivation #mindset #selfimprovement"
    engage = "#dailyquotes #likeforlikes #doubletap #engagementboost"
    tags = f"{niche}\n.\n{reach}\n.\n{growth}\n.\n{engage}"

    hook = day.get("caption_hook", "")
    cta = CTAS[day["day"] % len(CTAS)]

    # Book-specific leading emoji so the title line matches the book's mood
    if "atomic habits" in book_lower:
        book_emoji = "🌱"
    elif "12 rules" in book_lower or "jordan peterson" in book_lower:
        book_emoji = "⚖️"
    else:
        book_emoji = "⚔️"

    # Lean caption: hook leads, then a single-line title block, CTA, music credit, hashtags.
    # The full body text is already rendered on the video itself, so we don't repeat it here.
    parts = []
    if hook:
        parts += [hook, ""]
    parts += [
        f"{book_emoji} {day['title'].upper()} · {day['headline'].upper()}",
        f"📖 {day['author']} · {day['book']} · Day {book_day}/{book_total}",
        "",
        f"💬 {cta}",
        "🎵 Kevin MacLeod + ccMixter artists (CC-BY)",
        "",
        tags,
    ]
    return "\n".join(parts)


def _create_and_publish(media_data: dict) -> str:
    """Create a media container, wait for ingestion, publish. Returns media_id."""
    user_id = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]

    r = requests.post(f"{GRAPH}/{user_id}/media",
                      data={**media_data, "access_token": token}, timeout=60)
    r.raise_for_status()
    creation_id = r.json()["id"]

    for _ in range(30):
        s = requests.get(f"{GRAPH}/{creation_id}",
                         params={"fields": "status_code", "access_token": token},
                         timeout=30).json()
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise RuntimeError(f"IG ingestion error: {s}")
        time.sleep(10)
    else:
        raise TimeoutError("IG did not finish processing the media in time")

    r = requests.post(f"{GRAPH}/{user_id}/media_publish",
                      data={"creation_id": creation_id, "access_token": token}, timeout=60)
    r.raise_for_status()
    return r.json()["id"]


def post_reel(video_url: str, caption: str) -> str:
    return _create_and_publish({
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        # Hide like and view counts on the published Reel
        "like_and_views_counts_disabled": "true",
    })


def post_story(video_url: str) -> str:
    """Share the same video to Stories (24-hour visibility). Best-effort:
    if it fails, the Reel post is unaffected."""
    return _create_and_publish({
        "media_type": "STORIES",
        "video_url": video_url,
    })


if __name__ == "__main__":
    # smoke test
    print("post.py: import this module from main.py — do not call directly")
