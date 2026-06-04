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

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    # force-ssl is required to call commentThreads.insert (auto-pinned
    # engagement comment after each upload). Credentials minted before this
    # was added will fail with insufficientScope — re-mint via
    # scripts/yt_auth_manual.py once and update the GH secret.
    "https://www.googleapis.com/auth/youtube.force-ssl",
]
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
    """Generate Shorts-friendly title, description, and tags from a day dict.

    Title leads with the item's TEASE — it's the scroll-stopper, and it makes
    the title unique per item (was previously "<parent_law>: <headline>" which
    meant AM and PM of the same Law produced the IDENTICAL title and broke
    per-item YT idempotency). The Law label moves into the description body."""
    from twemoji_local import strip_emoji
    tease = strip_emoji(day.get("tease", "")).strip().rstrip(" .—-:")
    if tease:
        title = f"{tease} #Shorts"
    else:
        title = f"{day.get('title','')}: {day.get('headline','')} #Shorts"
    if len(title) > 100:
        title = title[:97] + "..."

    # 2026-06-04 SMM rewrite: tags now mix author/book brand-tags (for
    # discovery via author search) with NICHE tags where small channels can
    # rank. Dropped "shorts" (redundant — already in title #Shorts), dropped
    # "self improvement"/"mindset"/"philosophy" (mega-saturated, channels
    # under 10K subs are invisible there).
    book_lower = day["book"].lower()
    if "atomic habits" in book_lower:
        tags = ["atomic habits", "james clear", "habits", "discipline",
                "daily habits", "habit building", "compound effect",
                "small habits big results", "productivity tips"]
    elif "12 rules" in book_lower or "jordan peterson" in book_lower:
        tags = ["12 rules for life", "jordan peterson", "stoicism",
                "stoic wisdom", "meaning", "responsibility", "modern stoicism",
                "wisdom for men", "life lessons"]
    else:
        tags = ["48 laws of power", "robert greene", "office politics",
                "career advice", "corporate survival", "managing up",
                "power dynamics", "workplace wisdom", "getting promoted"]

    # 2026-06-04 SMM rewrite of YT description:
    # 1) Body line moved to TOP so the first ~125 chars (what shows in YT
    #    search previews) is the actual content PUNCH, not the bookmark
    #    label "Law 1:". Previously the description led with the label,
    #    which made the preview generic and skippable.
    # 2) Removed "Follow @nandetroll_ on Instagram" CTA — triple-penalized
    #    (Follow-bait pattern + drives traffic OFF YouTube + wrong handle
    #    for YT viewers, who would search @getunwrittenrules anyway).
    # 3) Dropped uppercase headline (was reading as shouting/spam).
    # 4) Dropped empty caption_hook line that was inserting 2 blank lines
    #    at the top of every description (caption_hook field doesn't exist
    #    in quotes.json data).
    # 5) Added "From {book} by {author}" SEO line packed with searchable
    #    keywords (the YT search index loves author/book name matches).
    parts = [
        day["body"],                                            # PUNCH first (preview)
        f"From {day['book']} by {day['author']}.",              # SEO keywords
        f"{day['title']}: {day['headline']}",                   # context label
        "@getunwrittenrules — the rules nobody teaches at work.",
        f"Day {day.get('book_day', day['day'])} of {day.get('book_total', '?')} · {day['book']}",
        "Music: Kevin MacLeod + ccMixter artists (CC-BY)",      # required CC-BY attribution
        "#Shorts #" + " #".join(t.replace(" ", "") for t in tags),
    ]
    hook = day.get("caption_hook", "").strip()
    if hook:
        parts.insert(0, hook)
    description = "\n\n".join(parts)
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


def yt_has_title(target_title: str) -> tuple[bool, str]:
    """Per-item YT idempotency: True if a video with this exact title is
    already in the channel's recent uploads. Equivalent of ig_has_caption
    for YouTube — replaces the old "any post today" guard which broke
    once youtube.force-ssl unlocked the channel-uploads listing and started
    skipping PM after AM had posted. Fail-open on any error: a recoverable
    duplicate is better than a silently-missed post."""
    try:
        creds = get_credentials()
        yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
        ch = yt.channels().list(part="contentDetails", mine=True).execute()
        uploads_pl = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        pl = yt.playlistItems().list(part="snippet", playlistId=uploads_pl, maxResults=25).execute()
        target = (target_title or "").strip()[:100]
        if not target:
            return False, "YT dedupe skipped (empty target title)"
        for item in pl.get("items", []):
            if item["snippet"]["title"].strip() == target:
                return True, f"YT: this slot's item already uploaded ({target[:50]}...)"
        return False, "YT: this slot not yet uploaded — proceeding"
    except Exception as e:
        return False, f"YT dedupe unavailable (fail-open): {type(e).__name__}"


# Rotating closer lines — keep the "if you miss, you regret" pattern fresh so
# the comment doesn't read identical across 30 days of posts.
_COMMENT_CLOSERS = (
    "Most people find this channel six months too late.",
    "The ones who scroll past this usually regret it by Q2.",
    "Don't be the person learning this the week before review season.",
    "Save this for the meeting you're definitely going to have.",
    "If you're still on the fence, you're already losing ground.",
    "Every week you delay is a week the politics win.",
)


def build_yt_comment(day: dict) -> str:
    """The pinned engagement comment posted right after each upload.

    Structure: the item's own divisive question (forces a reply) -> the
    like/subscribe ask -> the rotating FOMO closer. Short on purpose; long
    pinned comments read as desperate. The 👇 is the only emoji — same as the
    caption — to keep the human voice."""
    q = (day.get("comment_q") or "").strip()
    if q.endswith("👇"):
        q = q[:-1].strip()
    closer = _COMMENT_CLOSERS[int(day.get("item", 1)) % len(_COMMENT_CLOSERS)]
    return "\n".join([
        f"{q} 👇 Drop your call in the replies.",
        "",
        "LIKE if this lands. SHARE with whoever needs the heads-up. SUBSCRIBE — daily corporate tactics decoded from the 3 books office politics actually runs on.",
        "",
        closer,
    ])


def post_comment(video_id: str, text: str) -> str:
    """Post a top-level comment on a video. Returns the comment thread id.

    Requires the credential to carry the youtube.force-ssl scope. Fails fast
    with a readable error if the scope is missing (i.e. the token hasn't
    been re-minted since the scope was added)."""
    creds = get_credentials()
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {
        "snippet": {
            "videoId": video_id,
            "topLevelComment": {"snippet": {"textOriginal": text}},
        }
    }
    resp = yt.commentThreads().insert(part="snippet", body=body).execute()
    return resp["id"]
