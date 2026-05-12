# instaautomatic

A fully autonomous daily multi-platform content bot. Builds a 24-second video each day from a book quote, picks a mood-matched royalty-free track, publishes to **Instagram Reels + Stories + YouTube Shorts**, and emails you both URLs. Runs on GitHub Actions — no server, no maintenance.

Currently queued: **92 days** of content across 3 books → posts daily at **5:30 PM IST** (lands 5:30–6:00 PM with GitHub Actions delay) to:
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

## Video format (24 sec, 1080×1920, four frames)

```
Second:     0    2    6    10                 22   24
            │────│────────│──────────────────│────│
            │INTRO│ MAIN  │       EXAMPLE     │ END│
            │  ←  │  ←    │  ←                │  ← │
            │     │       │                   │    │
            │  •  │ • full│ • per-book label  │ •  │
            │head │  hdr+ │   (TODAY'S MOVE / │ COM│
            │only │  body │    THE PRACTICE / │ MENT
            │     │  + Ken│    LIVE BY THIS)  │ BELO
            │     │  Burns│ • real-life       │  W  │
            │     │  zoom │   example         │ • TOMOR
            │     │       │ • Ken Burns zoom  │  ROW
            │     │       │                   │ • follow
            │     │       │                   │      │
            └─────┴───────┴───────────────────┴─────┘
                 ⤵ 0.5-sec crossfade between every frame
```

- **Intro frame (2 sec)** — just the headline + day label. Pure hook.
- **Main frame (8 sec)** — full law/principle headline + body explanation, slow Ken Burns zoom on the background painting.
- **Example frame (12 sec)** — `TODAY'S MOVE` / `THE PRACTICE` / `LIVE BY THIS` label (per book) + a concrete real-life example of how to apply the principle.
- **End frame (2 sec)** — `COMMENT BELOW` + `TOMORROW · <next title>` + handle.

Cross-book transitions are handled automatically: Day 49 end-frame teases Atomic Habits, Day 79 teases 12 Rules, Day 92 shows "SERIES COMPLETE".

Per-book example label:
- ⚔️ 48 Laws of Power → **TODAY'S MOVE**
- 🌱 Atomic Habits → **THE PRACTICE**
- ⚖️ 12 Rules for Life → **LIVE BY THIS**

---

## Audio

- **Music**: 38 royalty-free tracks split across 3 mood-tagged pools (one per book). `pick_music()` prefers tracks tagged with the day's mood from `music_metadata.json`.
- **Loudness normalization**: every track passes through ffmpeg's `loudnorm` filter at -14 LUFS (IG/YT broadcast standard) → every post has consistent volume.
- **Fades**: 1-second audio fade-in at start, 1-second fade-out at end (sec 23–24).
- **No voice narration** (TTS was evaluated; not enabled in production).

---

## Caption format

```
{caption_hook}   ← above the fold, drives engagement

{book_emoji} {TITLE} · {HEADLINE}
📖 {Author} · {Book} · Day {n}/{total}

💬 {rotating CTA}
🎵 Kevin MacLeod + ccMixter artists (CC-BY)

{22 niche/adjacent/broader/books hashtags, grouped}
```

- **Hook** comes from `caption_hook` field in `quotes.json` — short question-led line with emoji.
- **Book emoji**: ⚔️ for 48 Laws, 🌱 for Atomic Habits, ⚖️ for 12 Rules.
- **CTA** rotates daily through a 12-item pool (Tag someone / Save / Double tap / Bookmark / etc.).
- **Hashtags**: 22 niche-focused tags per book. No engagement-bait (`#likeforlikes`, `#engagementboost`), no generic mega-tags (`#viral`, `#fyp`, `#trending`).

YouTube video uses the same content but reformatted for Shorts (title ≤ 100 chars, description ≤ 5000 chars, `#Shorts` tag).

---

## Architecture

```
              ┌──────────────────────────┐
              │  GitHub Actions cron     │
              │  · daily.yml @ 12:00 UTC │
              │  · refresh_token.yml @   │
              │    Mon 06:00 UTC         │
              └────────────┬─────────────┘
                           │
    ┌──────────────────────▼──────────────────────┐
    │  main.py                                     │
    │   • computes today's day from START_DATE     │
    │   • generate.build(day_num) — 4 frames + mp4 │
    │   • upload_to_public_url() — github raw URL  │
    │   • post_reel()    → Graph API (REELS)       │
    │   • post_story()   → Graph API (STORIES)     │
    │   • upload_short() → YouTube Data API v3     │
    │   • writes day metadata to $GITHUB_OUTPUT    │
    └───────────────┬──────────────────────────────┘
                    │
        ┌───────────┼────────────┬─────────────────┐
        ▼           ▼            ▼                 ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐    ┌──────────┐
  │generate  │ │post.py   │ │post_     │    │ Email    │
  │  .py     │ │ • Reel + │ │youtube.py│    │ notif    │
  │ • 4 PNG  │ │   Story  │ │ • Shorts │    │ · OK     │
  │   frames │ │ • hide   │ │   upload │    │ · FAIL   │
  │ • Ken    │ │   likes  │ │ • OAuth2 │    │          │
  │   Burns  │ │ • 22     │ │   refresh│    │          │
  │ • Loudn. │ │   tags   │ │   tokens │    │          │
  │ • Mood   │ │ • CTA    │ │          │    │          │
  │   music  │ │          │ │          │    │          │
  └──────────┘ └──────────┘ └──────────┘    └──────────┘
```

Day → content lookup happens via [quotes.json](quotes.json), grouped by book. `load_day()` computes the per-book day index (e.g. *Atomic Habits Day 11 of 30*) and propagates `caption_hook`, `mood`, and `example` to the renderer.

---

## Files

```
├── quotes.json              # 92 days × {day, title, headline, body, example, caption_hook, mood, book, author}
├── generate.py              # 4-frame video builder (intro/main/example/end + ffmpeg stitch)
├── post.py                  # IG Graph API: Reel + Story publish + caption builder
├── post_youtube.py          # YouTube Data API v3 uploader (Shorts)
├── main.py                  # daily orchestrator (IG + YT in one pass)
├── music_metadata.json      # track-name → mood map (for mood-matched music selection)
├── requirements.txt
│
├── .github/workflows/
│   ├── daily.yml            # 12:00 UTC = 17:30 IST — IG Reel + Story + YouTube Short
│   └── refresh_token.yml    # Mondays 06:00 UTC — refreshes long-lived IG token
│
├── backgrounds/
│   ├── 48laws/              # 6 dark classical paintings
│   ├── atomic/              # 6 brighter landscapes
│   └── rules/               # 3 dramatic philosophical
│
├── music/                   # 38 royalty-free tracks total
│   ├── 48laws/              # 16: Kevin MacLeod Darkness (9) + Action Cuts (5) + ccMixter (2)
│   ├── atomic/              # 13: Famous Classics (6) + Action Cuts (4) + ccMixter (3)
│   └── rules/               # 9:  Classical Sampler (6) + ccMixter (3)
│
├── fonts/                   # Cinzel + PlayfairDisplay (regular + italic)
│
├── output/                  # built videos + frames (auto-committed by workflow)
│
└── scripts/
    ├── verify_token.py          # check IG token validity + expiry
    ├── refresh_token.py         # used by refresh_token.yml
    ├── yt_auth_bootstrap.py     # one-time YouTube OAuth flow
    ├── backfill_youtube.py      # backfill arbitrary days to YouTube
    ├── check_analytics.py       # live IG insights via Graph API
    ├── audit_quotes.py          # validates quotes.json structure
    ├── preflight_check.py       # 33-check pre-deployment validator
    ├── list_days.py             # prints all queued days
    ├── add_caption_hooks.py     # one-time migration: caption_hook field
    ├── add_examples.py          # one-time migration: example field (92 real-life examples)
    ├── add_moods.py             # one-time migration: mood field (regal/dark/tense/etc.)
    ├── fetch_backgrounds.py     # Wikimedia downloader for 48 Laws backgrounds
    ├── fetch_book_assets.py     # Wikimedia/Archive.org downloader for atomic + rules
    ├── fetch_music.py           # Internet Archive Kevin MacLeod Darkness album
    ├── fetch_ccmixter.py        # ccMixter downloader for additional tracks
    ├── list_ccmixter.py         # browse ccMixter by mood tag
    ├── voice_samples.py         # standalone voice exploration (TTS not in production)
    ├── voice_samples_kn.py      # Kannada TTS samples
    ├── find_voice.py            # search edge-tts voice list by name
    └── preview_end_frame.py     # generate end-frame design previews
```

Gitignored (never committed): `.env`, `client_secret*.json`, `yt_token.json`, `.venv/`.

---

## Configuration (set once)

### GitHub Secrets — repo Settings → Secrets and variables → Actions

| Name | Source | Purpose |
|---|---|---|
| `IG_USER_ID` | numeric Instagram Business Account ID | identifies which IG to post to |
| `IG_ACCESS_TOKEN` | long-lived Meta user token (60 days) | authenticates IG Graph API calls |
| `APP_SECRET` | Meta app secret | refresh workflow uses to mint new tokens |
| `GH_TOKEN` | GitHub fine-grained PAT (Secrets read+write) | refresh workflow uses to update IG_ACCESS_TOKEN |
| `MAIL_USERNAME` | Gmail address that sends notifications | SMTP auth |
| `MAIL_APP_PASSWORD` | Gmail 16-char App Password | SMTP auth |
| `MAIL_TO` | comma-separated recipient emails | who gets daily success/failure email |
| `YT_CLIENT_ID` | Google OAuth2 client ID | YouTube API auth |
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
3. Configure **Google Auth Platform** (OAuth Consent Screen):
   - App type: External
   - Add your Gmail as a Test User
   - Add scope `.../auth/youtube.upload`
4. Create an **OAuth 2.0 Client ID** — type: Desktop app, download JSON
5. Save the JSON at project root as `client_secret.json`
6. Run the bootstrap:
   ```powershell
   .\.venv\Scripts\python.exe scripts\yt_auth_bootstrap.py
   ```
7. Browser opens, approve, PowerShell prints 3 values → add to GitHub Secrets

Refresh token stays valid as long as the Google password doesn't change.

---

## Token lifecycle (zero maintenance)

The **Meta long-lived token** expires every 60 days, but `refresh_token.yml` runs **every Monday 06:00 UTC** and exchanges the current token for a fresh one — resetting the 60-day clock. As long as that workflow runs, the token never expires.

The **YouTube refresh token** doesn't expire (only invalidated by password change or revoke).

If either refresh fails, an urgent email goes out.

Annual chore (only if you set a 1-year expiry on the GitHub PAT): regenerate `GH_TOKEN` once a year. If created with "No expiration", never.

---

## Email notifications

Both workflows send Gmail (SMTP) emails via [dawidd6/action-send-mail](https://github.com/dawidd6/action-send-mail).

**Daily post success:**
```
Subject: [OK] Day N posted — Title: Headline
Body: book + per-book day + headline + IG Media ID + Instagram URL +
      YouTube Short URL + workflow run link
```

**Daily post failure:**
```
Subject: [FAIL] Daily post FAILED for Day N
Body: last-known day metadata + run logs + common causes
```

**Token refresh failure:**
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
start output/day_50.mp4

# Audit quotes.json (sequence, fields, books)
python scripts/audit_quotes.py

# 33-check preflight before any major deploy
python scripts/preflight_check.py

# Verify the local Meta token is still valid
python scripts/verify_token.py

# Check live IG analytics on recent posts
python scripts/check_analytics.py

# Re-run YouTube bootstrap (only if token gets revoked)
python scripts/yt_auth_bootstrap.py

# Backfill specific days to YouTube
python scripts/backfill_youtube.py 4 5 6

# Re-download assets
python scripts/fetch_backgrounds.py
python scripts/fetch_book_assets.py
python scripts/fetch_music.py
python scripts/fetch_ccmixter.py
```

---

## Adding a 4th (or 5th, 6th…) book

1. Append entries to `quotes.json` `days` array, continuing from the next day number, with `book`, `author`, `title`, `headline`, `body`, `caption_hook`, `mood`, **and `example`** per day.
2. Drop ~5–10 backgrounds into `backgrounds/<slug>/` and ~5 music tracks into `music/<slug>/`.
3. Add mood tags for the new music tracks to `music_metadata.json`.
4. Update `generate.py::book_slug()` and `render_example_frame()` to pick the right per-book label.
5. Update `post.py::build_caption()` for the new hashtag branch + book emoji.
6. Update `post_youtube.py::build_youtube_metadata()` for the new tags.
7. Commit and push. The bot picks up automatically on the right day.

---

## Limits and notes

- **Instagram Graph API**: 25 posts / 24h per account — way more than we need.
- **YouTube Data API v3**: 10,000 quota units/day free tier. Each upload costs ~1,600 units → we use ~16% of daily quota.
- Repo must be **public** for `raw.githubusercontent.com` URLs to be reachable by Meta's ingester.
- IG's built-in music library (Bollywood / TikTok-style audio) is **not** accessible via API — all music must be royalty-free files we host.
- Reels publish with `like_and_views_counts_disabled=true` so the public post hides like/view counts.
- YouTube Shorts qualify automatically: 1080×1920, ≤60 sec, `#Shorts` in the title.
- GitHub Actions cron is best-effort; the 12:00 UTC schedule was chosen to land in the 5:30–6:00 PM IST evening window.
- Story cross-post and YouTube upload are best-effort: if either fails, the Reel still posts and you get a warning in the email.
- Music attribution: Kevin MacLeod (incompetech.com, CC-BY 4.0) + ccMixter artists (CC-BY / CC-BY-NC). Attribution in every caption + YouTube description.

---

## Cost

**₹0.** Everything (Python, ffmpeg, GitHub Actions free tier, Meta Graph API, YouTube Data API v3 free tier, Wikimedia Commons, Internet Archive, ccMixter, Gmail SMTP) is free. Estimated usage on GitHub Actions free tier: ~80 of the 2,000 free minutes/month.
