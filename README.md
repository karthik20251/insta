# instaautomatic

A fully autonomous daily multi-platform content bot. Builds a video each day from a book quote, picks a fitting royalty-free track, publishes to **Instagram Reels + Stories + YouTube Shorts**, and emails you both URLs. Runs on GitHub Actions — no server, no maintenance.

Currently queued: **92 days** of content across 3 books → posts daily at **6:30 PM IST** (lands 6:30–7:00 PM with GitHub Actions delay) to:
- Instagram → **@nandetroll_**
- YouTube → **@nandetroll_gk**

---

## What it posts

| Days | Book | Author | Aesthetic |
|---|---|---|---|
| 1 – 49 | *The 48 Laws of Power* | Robert Greene | Dark / regal — classical paintings + cinematic dark instrumentals |
| 50 – 79 | *Atomic Habits* | James Clear | Bright / optimistic — Hokusai/Monet/Van Gogh + uplifting classical |
| 80 – 92 | *12 Rules for Life* | Jordan Peterson | Contemplative / philosophical — Friedrich/Doré + Bach/Brahms classical |

Schedule (with `START_DATE = 2026-05-09`):

- **2026-05-10** → Day 2: Law 1 *Never Outshine the Master*
- **2026-06-26** → Day 49: Law 48 *Assume Formlessness*
- **2026-06-27** → Atomic Habits Day 1
- **2026-07-26** → Atomic Habits Day 30
- **2026-07-27** → 12 Rules Day 1
- **2026-08-08** → 12 Rules Day 13 (final post)

---

## Video format (12 sec, 1080×1920, two frames)

```
Second:     0     3     6     9   9.5   12
            │─────────────────│xxxx│─────│
            │   QUOTE FRAME   │fade│ END │
            │ • law title     │ 0.5│ • COMMENT BELOW
            │ • headline      │ sec│ • Save·Share·Tag
            │ • body          │xfade • TOMORROW: next title
            │ • attribution   │    │ • » » »
            │                 │    │ • follow handle
            │ background:     │    │
            │ classical art   │    │
            │ + dark overlay  │    │
            │                 │    │
            │ music: random   │    │ music fades out
            │ track from      │    │ last 1 sec
            │ per-book pool   │    │
            └─────────────────┴────┴─────┘
```

The text block is **vertically centered** on the canvas (no empty gap). Cross-book transitions are handled automatically: Day 49 end-frame teases Atomic Habits, Day 79 teases 12 Rules, Day 92 shows "SERIES COMPLETE".

---

## Caption format

```
{caption_hook}   ← above the fold, drives engagement

{book_emoji} {TITLE} · {HEADLINE}
📖 {Author} · {Book} · Day {n}/{total}

💬 {rotating CTA}
🎵 Kevin MacLeod + ccMixter artists (CC-BY)

{30 hashtags, grouped: niche . reach . growth . engagement}
```

- **Hook** comes from `caption_hook` field in `quotes.json` — short question-led line with emoji.
- **Book emoji**: ⚔️ for 48 Laws, 🌱 for Atomic Habits, ⚖️ for 12 Rules.
- **CTA** rotates daily through a 12-item pool (Tag someone / Save / Double tap / Bookmark / etc.).
- **Hashtags**: capped at Instagram's 30/post limit. Book-specific niche + high-reach + growth-mindset + engagement.

YouTube video uses the same content but reformatted for Shorts (title ≤ 100 chars, description ≤ 5000 chars, `#Shorts` tag for discoverability).

---

## Architecture

```
              ┌──────────────────────────┐
              │  GitHub Actions cron     │
              │  · daily.yml @ 13:00 UTC │
              │  · refresh_token.yml @   │
              │    Mon 06:00 UTC         │
              └────────────┬─────────────┘
                           │
    ┌──────────────────────▼──────────────────────┐
    │  main.py                                     │
    │   • computes today's day from START_DATE     │
    │   • generate.build(day_num)                  │
    │   • upload_to_public_url() — github raw URL  │
    │   • post_reel()    → Graph API (REELS)       │
    │   • post_story()   → Graph API (STORIES)     │
    │   • upload_short() → YouTube Data API v3     │
    │   • writes day metadata to $GITHUB_OUTPUT    │
    └───────────────┬──────────────────────────────┘
                    │
        ┌───────────┼────────────┬─────────────────┐
        ▼           ▼            ▼                 ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐  ┌──────────┐
  │generate  │ │post.py   │ │post_     │  │ Email    │
  │  .py     │ │ • Reel + │ │youtube.py│  │ notif    │
  │ • two-   │ │   Story  │ │ • Shorts │  │ · OK     │
  │   frame  │ │ • hide   │ │   upload │  │ · FAIL   │
  │   video  │ │   likes  │ │ • OAuth2 │  │          │
  │ • per-   │ │ • 30     │ │   refresh│  │          │
  │   book   │ │   tags   │ │   tokens │  │          │
  │   assets │ │ • CTA    │ │          │  │          │
  └──────────┘ └──────────┘ └──────────┘  └──────────┘
```

Day → content lookup happens via [quotes.json](quotes.json), grouped by book. `load_day()` computes the per-book day index (e.g. *Atomic Habits Day 11 of 30*) and propagates `caption_hook` to caption + YouTube description builders.

---

## Files

```
├── quotes.json              # 92 days × {day, title, headline, body, caption_hook, book, author}
├── generate.py              # Pillow render → ffmpeg → 1080x1920 two-frame mp4 (book-aware assets)
├── post.py                  # IG Graph API: Reel + Story publish + caption builder + 30 hashtags
├── post_youtube.py          # YouTube Data API v3 uploader (Shorts)
├── main.py                  # daily orchestrator (IG + YT in one pass)
├── requirements.txt
│
├── .github/workflows/
│   ├── daily.yml            # 13:00 UTC = 18:30 IST — IG Reel + Story + YouTube Short
│   └── refresh_token.yml    # Mondays 06:00 UTC — refreshes long-lived IG token
│
├── backgrounds/
│   ├── 48laws/              # 6 dark classical paintings (Liberty, Saturn, Las Meninas, ...)
│   ├── atomic/              # 6 brighter landscapes (Hokusai, Monet, Van Gogh, Turner, ...)
│   └── rules/               # 3 dramatic philosophical (Friedrich, Doré, Hokusai)
│
├── music/                   # 38 royalty-free tracks total
│   ├── 48laws/              # 16: Kevin MacLeod Darkness (9) + Action Cuts (5) + ccMixter (2)
│   ├── atomic/              # 13: Famous Classics (6) + Action Cuts (4) + ccMixter (3)
│   └── rules/               # 9:  Classical Sampler (6) + ccMixter (3)
│
├── fonts/
│   ├── Cinzel.ttf
│   ├── PlayfairDisplay.ttf
│   └── PlayfairDisplay-Italic.ttf
│
├── output/                  # built videos + end-frames (auto-committed by workflow)
│   ├── day_NN.png           # main quote frame
│   ├── day_NN_end.png       # CTA + tomorrow teaser frame
│   └── day_NN.mp4           # 12-sec stitched video
│
└── scripts/
    ├── verify_token.py          # check current IG token validity + expiry
    ├── refresh_token.py         # used by refresh_token.yml workflow
    ├── yt_auth_bootstrap.py     # one-time YouTube OAuth flow (prints 3 secrets)
    ├── backfill_youtube.py      # upload arbitrary day numbers to YouTube
    ├── fetch_backgrounds.py     # downloader for 48 Laws backgrounds
    ├── fetch_book_assets.py     # downloader for atomic + rules backgrounds & music
    ├── fetch_music.py           # downloader for Kevin MacLeod Darkness album
    ├── fetch_ccmixter.py        # downloader for ccMixter tracks (uses curl)
    ├── list_ccmixter.py         # browse ccMixter tracks by tag/mood
    ├── add_caption_hooks.py     # one-time migration that injected caption_hook
    ├── audit_quotes.py          # validates quotes.json structure
    ├── list_days.py             # prints all queued days
    └── preview_end_frame.py     # generates standalone end-frame PNGs for design previews
```

Gitignored (never committed): `.env`, `client_secret*.json`, `yt_token.json`, `.venv/`.

---

## Configuration (set once)

### GitHub Secrets — repo Settings → Secrets and variables → Actions

| Name | Source | Purpose |
|---|---|---|
| `IG_USER_ID` | numeric Instagram Business Account ID | identifies which IG to post to |
| `IG_ACCESS_TOKEN` | long-lived Meta user token (60 days) | authenticates IG Graph API calls |
| `APP_SECRET` | Meta app secret | used by refresh workflow to mint new tokens |
| `GH_TOKEN` | GitHub fine-grained PAT (Secrets read+write on this repo) | lets refresh workflow update IG_ACCESS_TOKEN |
| `MAIL_USERNAME` | Gmail address that sends notifications | SMTP auth |
| `MAIL_APP_PASSWORD` | Gmail 16-char App Password | SMTP auth |
| `MAIL_TO` | comma-separated recipient emails | who gets the daily success/failure email |
| `YT_CLIENT_ID` | Google OAuth2 client ID from `client_secret.json` | YouTube API auth |
| `YT_CLIENT_SECRET` | Google OAuth2 client secret | YouTube API auth |
| `YT_REFRESH_TOKEN` | Refresh token from `yt_auth_bootstrap.py` | YouTube API auth (long-lived) |

### GitHub Variables — same page, Variables tab

| Name | Value | Purpose |
|---|---|---|
| `START_DATE` | `YYYY-MM-DD` | anchors Day 1 — bot computes `day = today − START_DATE + 1` |

### Local `.env` (only for local dry-runs, never committed)

Mirror the IG secrets above plus:
```env
UPLOAD_BACKEND=github
GITHUB_RAW_BASE=https://raw.githubusercontent.com/karthik20251/insta/master/output
```

For local YouTube uploads (backfill), `yt_token.json` at the project root is sufficient (created by `yt_auth_bootstrap.py`).

---

## YouTube setup (one-time, ~10 min)

1. Create a Google Cloud project at https://console.cloud.google.com
2. Enable **YouTube Data API v3** in the API library
3. Configure **Google Auth Platform** (the new name for OAuth Consent Screen):
   - App type: External
   - Add your Gmail as a Test User
   - Add the `.../auth/youtube.upload` scope
4. Create an **OAuth 2.0 Client ID** — type: Desktop app
5. Download the JSON, save as `client_secret.json` at project root
6. Run the bootstrap:
   ```powershell
   .\.venv\Scripts\python.exe scripts\yt_auth_bootstrap.py
   ```
7. Browser opens, you approve, PowerShell prints 3 values → add to GitHub Secrets:
   - `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`

The refresh token stays valid as long as you don't change your Google password or revoke access. Daily usage keeps it alive indefinitely.

---

## Token lifecycle (zero maintenance)

The **Meta long-lived token** expires every 60 days, but the `refresh_token.yml` workflow runs **every Monday 06:00 UTC** and exchanges the current token for a fresh one — resetting the 60-day clock. As long as that workflow keeps running, the token never expires.

The **YouTube refresh token** doesn't expire (only invalidated by password change or revoke). No maintenance.

If either refresh ever fails, you get an urgent email.

Manual annual chore (only if you set a 1-year expiry on the GitHub PAT):
- **GitHub PAT renewal** — regenerate the `GH_TOKEN` PAT. If created with "No expiration", never.

---

## Email notifications

Both workflows send Gmail (SMTP) emails via [dawidd6/action-send-mail](https://github.com/dawidd6/action-send-mail).

**Daily post success email:**
```
Subject: [OK] Day N posted — Title: Headline

Body: book + per-book day + headline + IG Media ID +
      Instagram URL + YouTube Short URL + workflow run link
```

**Daily post failure email:**
```
Subject: [FAIL] Daily post FAILED for Day N
Body: last-known day metadata + run logs + common causes
```

**Token refresh failure email:**
```
Subject: [URGENT] IG token refresh failed — daily posts will stop in <60 days
Body: run logs + common causes + fix instructions
```

---

## Operating commands

```bash
# Local dry-run (build today's video, don't post)
python main.py --dry-run

# Build a specific day for preview
python -c "from generate import build; build(50)"
start output/day_50.png

# Audit quotes.json
python scripts/audit_quotes.py

# Verify the local Meta token in .env is still valid
python scripts/verify_token.py

# Re-run YouTube bootstrap (only if token gets revoked)
python scripts/yt_auth_bootstrap.py

# Backfill specific days to YouTube (uploads existing local mp4 files)
python scripts/backfill_youtube.py 4 5 6

# Re-download backgrounds (Wikimedia)
python scripts/fetch_backgrounds.py
python scripts/fetch_book_assets.py

# Re-download music (Internet Archive + ccMixter)
python scripts/fetch_music.py
python scripts/fetch_book_assets.py
python scripts/fetch_ccmixter.py

# Preview captions for sample days
python -c "from generate import load_day; from post import build_caption; print(build_caption(load_day(50)))"
```

---

## Adding a 4th (or 5th, 6th…) book

1. Append entries to `quotes.json` `days` array, continuing from the next day number, with `"book"`, `"author"`, and `"caption_hook"` per day:
   ```json
   {
     "day": 93,
     "book": "Meditations",
     "author": "Marcus Aurelius",
     "title": "Book I",
     "headline": "...",
     "body": "...",
     "caption_hook": "What would the wise man do? 🦉 ..."
   }
   ```
2. Drop ~5–10 backgrounds into `backgrounds/<slug>/` and ~5 music tracks into `music/<slug>/`.
3. Update `generate.py::book_slug()` to map the new book name to its folder slug.
4. Update `post.py::build_caption()` to add a hashtag branch and book emoji.
5. Update `post_youtube.py::build_youtube_metadata()` to add the corresponding YouTube tags.
6. Commit and push. The bot picks up automatically on the right day.

---

## Limits and notes

- **Instagram Graph API**: 25 posts / 24h per account — way more than we need.
- **YouTube Data API v3**: 10,000 quota units/day free tier. Each upload costs ~1,600 units → we use ~16% of daily quota.
- Repo must be **public** for `raw.githubusercontent.com` URLs to be reachable by Meta's ingester.
- IG's built-in music library (Bollywood / TikTok-style trending audio) is **not** accessible via API — all music must be royalty-free files we host.
- Reels publish with `like_and_views_counts_disabled=true` so the public post hides like/view counts.
- YouTube Shorts qualify automatically: video is 1080×1920 (9:16), 12 sec (under 60 sec), and `#Shorts` is in the title.
- GitHub Actions cron is best-effort under load: scheduled runs typically fire on time but can be delayed 5–30 minutes. The 13:00 UTC schedule was chosen to land in the 6:30–7:00 PM IST evening window.
- Story cross-post and YouTube upload are best-effort: if either fails, the Reel still posts and you get a warning in the email.
- Music attribution: Kevin MacLeod tracks (incompetech.com, CC-BY 4.0), ccMixter artists (CC-BY / CC-BY-NC). Attribution included in every caption + YouTube description.

---

## Cost

**₹0.** Everything (Python, ffmpeg, GitHub Actions free tier, Meta Graph API, YouTube Data API v3 free tier, Wikimedia Commons, Internet Archive, ccMixter, Gmail SMTP) is free. Estimated usage on GitHub Actions free tier: ~60 of the 2,000 free minutes/month.
