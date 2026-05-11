"""Upload a video as a YouTube Short via the Data API v3.

Reads credentials from either:
  - env vars  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN  (production / CI)
  - local file  yt_token.json                                    (local dev / backfill)
"""
from __future__ import annotations
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
ROOT = Path(__file__).parent
TOKEN_FILE = ROOT / "yt_token.json"


def get_credentials() -> Credentials:
    cid = os.environ.get("YT_CLIENT_ID")
    csec = os.environ.get("YT_CLIENT_SECRET")
    rtok = os.environ.get("YT_REFRESH_TOKEN")
    if cid and csec and rtok:
        creds = Credentials(
            None,
            refresh_token=rtok,
            client_id=cid,
            client_secret=csec,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=SCOPES,
        )
        creds.refresh(Request())
        return creds
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if not creds.valid:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        return creds
    raise RuntimeError(
        "No YouTube credentials. Set env vars YT_CLIENT_ID/SECRET/REFRESH_TOKEN "
        "or put yt_token.json at the project root."
    )


def build_youtube_metadata(day: dict) -> dict:
    """Generate Shorts-friendly title, description, and tags from a day dict."""
    title = f"{day['title']}: {day['headline']} #Shorts"
    if len(title) > 100:
        title = title[:97] + "..."

    book_lower = day["book"].lower()
    if "atomic habits" in book_lower:
        tags = ["atomic habits", "james clear", "habits", "discipline",
                "productivity", "mindset", "self improvement", "shorts"]
    elif "12 rules" in book_lower or "jordan peterson" in book_lower:
        tags = ["12 rules for life", "jordan peterson", "philosophy", "meaning",
                "responsibility", "mindset", "self improvement", "shorts"]
    else:
        tags = ["48 laws of power", "robert greene", "power", "wisdom",
                "strategy", "philosophy", "mindset", "self improvement", "shorts"]

    hook = day.get("caption_hook", "")
    description = "\n\n".join([
        hook,
        f"{day['title'].upper()}: {day['headline'].upper()}",
        day["body"],
        f"— {day['author']}, {day['book']}",
        f"Day {day.get('book_day', day['day'])} of {day.get('book_total', '?')} · {day['book']}",
        "Music: Kevin MacLeod + ccMixter artists (CC-BY)",
        "Follow @nandetroll_ on Instagram for daily posts.",
        "#Shorts #" + " #".join(t.replace(" ", "") for t in tags),
    ])
    description = description[:4900]  # YT cap is 5000

    return {"title": title, "description": description, "tags": tags}


def upload_short(video_path: Path, title: str, description: str, tags: list[str]) -> str:
    """Upload a video and return its YouTube video ID."""
    creds = get_credentials()
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags or [],
            "categoryId": "27",  # 27 = Education
        },
        "status": {
            "privacyStatus": "public",
            "madeForKids": False,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = req.next_chunk()
    return response["id"]


def short_url(video_id: str) -> str:
    return f"https://www.youtube.com/shorts/{video_id}"
