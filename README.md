# instaautomatic

A fully autonomous daily Instagram Reel bot. Builds a video each day from a book quote, picks a fitting royalty-free track, posts it via the Instagram Graph API, cross-shares to Stories, and emails you the result. Runs on GitHub Actions — no server, no maintenance.

Currently queued: **92 days** of content across 3 books → posts daily at **6:30 PM IST** (lands 6:30–7:00 PM with GitHub Actions delay) to **@nandetroll_**.

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
- **CTA** rotates daily through a 12-item pool (Tag someone / Save / Double tap / Bookmark / Send to a friend / etc.).
- **Hashtags**: capped at Instagram's 30/post limit. Book-specific niche tags + high-reach + growth-mindset + engagement.

The full body text is rendered on the video itself, not duplicated in the caption (keeps the caption scannable on mobile).

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
    │   • post_reel()  → Graph API (REELS)         │
    │   • post_story() → Graph API (STORIES)       │
    │   • writes day metadata to $GITHUB_OUTPUT    │
    └───────────────┬──────────────────────────────┘
                    │
        ┌───────────┴────────────┐
        │                        │
        ▼                        ▼
  ┌──────────────┐      ┌──────────────────┐
  │ generate.py  │      │ post.py          │
  │ • PIL render │      │ • Graph API call │
  │ • ffmpeg mp4 │      │ • Reel + Story   │
  │ • per-book   │      │ • hide likes     │
  │   assets     │      │ • 30 hashtags    │
  └──────────────┘      └──────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  Email notification   │
        │  · success: post info │
        │  · failure: run logs  │
        └───────────────────────┘
```

Day → content lookup happens via [quotes.json](quotes.json), grouped by book. `load_day()` computes the per-book day index (e.g. *Atomic Habits Day 11 of 30*) and propagates a `caption_hook` to `build_caption()`.

---

## Files

```
├── quotes.json              # 92 days × {day, title, headline, body, caption_hook, book, author}
├── generate.py              # Pillow render → ffmpeg → 1080x1920 mp4 (book-aware assets)
├── post.py                  # IG Graph API: Reel + Story publish + caption builder
├── main.py                  # daily orchestrator
├── requirements.txt
│
├── .github/workflows/
│   ├── daily.yml            # 13:00 UTC = 18:30 IST — posts the day's Reel
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
│   ├── Cinzel.ttf           # variable font — regal headline
│   ├── PlayfairDisplay.ttf
│   └── PlayfairDisplay-Italic.ttf
│
├── output/                  # built videos (auto-committed by workflow)
│
└── scripts/
    ├── verify_token.py      # check current IG token validity + expiry (human-readable)
    ├── refresh_token.py     # used by refresh_token.yml workflow
    ├── fetch_backgrounds.py # downloader for 48 Laws backgrounds
    ├── fetch_book_assets.py # downloader for atomic + rules backgrounds & music
    ├── fetch_music.py       # downloader for Kevin MacLeod Darkness album
    ├── fetch_ccmixter.py    # downloader for ccMixter tracks (uses curl)
    ├── list_ccmixter.py     # browse ccMixter tracks by tag/mood
    ├── add_caption_hooks.py # one-time migration that injected caption_hook into quotes.json
    ├── audit_quotes.py      # validates quotes.json structure (sequence, fields, books)
    ├── list_days.py         # prints all queued days
    └── make_music.ps1       # legacy synth music generator (unused)
```

---

## Configuration (set once)

### GitHub Secrets — repo Settings → Secrets and variables → Actions

| Name | Value | Purpose |
|---|---|---|
| `IG_USER_ID` | numeric Instagram Business Account ID | identifies which IG to post to |
| `IG_ACCESS_TOKEN` | long-lived Meta user token (60 days) | authenticates Graph API calls |
| `APP_SECRET` | Meta app secret | used by refresh workflow to mint new tokens |
| `GH_TOKEN` | GitHub fine-grained PAT (Secrets read+write on this repo) | lets refresh workflow update IG_ACCESS_TOKEN |
| `MAIL_USERNAME` | Gmail address that sends notifications | SMTP auth |
| `MAIL_APP_PASSWORD` | Gmail 16-char App Password | SMTP auth |
| `MAIL_TO` | comma-separated recipient emails | who gets the daily success/failure email |

### GitHub Variables — same page, Variables tab

| Name | Value | Purpose |
|---|---|---|
| `START_DATE` | `YYYY-MM-DD` | anchors Day 1 — bot computes `day = today − START_DATE + 1` |

### Local `.env` (only for local dry-runs, never committed)

Mirror the secrets above plus:
```env
UPLOAD_BACKEND=github
GITHUB_RAW_BASE=https://raw.githubusercontent.com/karthik20251/insta/master/output
```

---

## Token lifecycle (zero maintenance)

The Meta long-lived token expires every 60 days, but the `refresh_token.yml` workflow runs **every Monday 06:00 UTC** and exchanges the current token for a fresh one — resetting the 60-day clock. As long as that workflow keeps running, the token never expires.

If the refresh ever fails, you get an urgent email so you can fix it before posts stop.

The only manual step that may eventually be needed:
- **GitHub PAT renewal** — if the `GH_TOKEN` was created with a 1-year expiry, regenerate it yearly. If created with "No expiration", never.

---

## Email notifications

Both workflows send Gmail (SMTP) emails via [dawidd6/action-send-mail](https://github.com/dawidd6/action-send-mail). Setup is silent — if `MAIL_USERNAME` secret is empty, the email steps no-op.

**Daily post success email:**
```
Subject: [OK] Day N posted — Title: Headline
Body: book + per-book day + headline + IG Media ID + workflow run link
```

**Daily post failure email:**
```
Subject: [FAIL] Daily post FAILED for Day N
Body: last-known day metadata + run logs + common causes (token, propagation, rate limit)
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

# Verify the local token in .env is still valid (human-readable expiry)
python scripts/verify_token.py

# Re-download all backgrounds (Wikimedia)
python scripts/fetch_backgrounds.py
python scripts/fetch_book_assets.py

# Re-download all music (Internet Archive + ccMixter)
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
5. Commit and push. The bot picks up automatically on the right day.

---

## Limits and notes

- Instagram Graph API allows **25 posts / 24h per account** — way more than we need.
- Repo must be **public** for `raw.githubusercontent.com` URLs to be reachable by Meta's ingester.
- IG's built-in music library (Bollywood / TikTok-style trending audio) is **not** accessible via API — all music must be royalty-free files we host.
- Reels publish with `like_and_views_counts_disabled=true` so the public post hides like/view counts.
- GitHub Actions cron is best-effort under load: scheduled runs typically fire on time but can be delayed 5–30 minutes. The 13:00 UTC schedule was chosen to land in the 6:30–7:00 PM IST evening window.
- Story cross-post is best-effort: if it fails, the Reel post is unaffected.
- Music attribution: Kevin MacLeod tracks (incompetech.com, CC-BY 4.0), ccMixter artists (CC-BY / CC-BY-NC). Attribution included in every caption.

---

## Cost

**₹0.** Everything (Python, ffmpeg, GitHub Actions free tier, Meta Graph API, Wikimedia Commons, Internet Archive, ccMixter, Gmail SMTP) is free. Estimated usage on GitHub Actions free tier: ~60 of the 2,000 free minutes/month.
