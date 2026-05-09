# instaautomatic

A fully autonomous daily Instagram Reel bot. Builds a video each day from a book quote, picks a fitting royalty-free music track, posts it via the Instagram Graph API. Runs on GitHub Actions — no server, no maintenance.

Currently queued: **92 days** of content across 3 books → posts daily at **7:15 PM IST** to **@nandetroll_**.

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

## Architecture

```
              ┌──────────────────────────┐
              │  GitHub Actions cron     │
              │  · daily.yml @ 13:45 UTC │
              │  · refresh_token.yml @   │
              │    Mon 06:00 UTC         │
              └────────────┬─────────────┘
                           │
    ┌──────────────────────▼──────────────────────┐
    │  main.py                                     │
    │   • computes today's day from START_DATE     │
    │   • generate.build(day_num)                  │
    │   • upload_to_public_url() — github raw URL  │
    │   • post_reel() → Graph API                  │
    └───────────────┬──────────────────────────────┘
                    │
        ┌───────────┴────────────┐
        │                        │
        ▼                        ▼
  ┌──────────────┐      ┌──────────────────┐
  │ generate.py  │      │ post.py          │
  │ • PIL render │      │ • Graph API call │
  │ • ffmpeg mp4 │      │ • polls ingestion│
  └──────────────┘      └──────────────────┘
```

Day → content lookup happens via [quotes.json](quotes.json), grouped by book; each day knows its own book + per-book day index (e.g. *Atomic Habits Day 11 of 30*).

---

## Files

```
├── quotes.json              # 92 days × {day, title, headline, body, book, author}
├── generate.py              # Pillow render → ffmpeg → 1080x1920 mp4
├── post.py                  # IG Graph API publishing + caption builder
├── main.py                  # daily orchestrator
├── requirements.txt
│
├── .github/workflows/
│   ├── daily.yml            # 13:45 UTC = 19:15 IST — posts the day's Reel
│   └── refresh_token.yml    # Mondays 06:00 UTC — refreshes long-lived IG token
│
├── backgrounds/
│   ├── 48laws/              # 6 dark classical paintings
│   ├── atomic/              # 6 brighter landscapes
│   └── rules/                # 3 dramatic philosophical
│
├── music/
│   ├── 48laws/              # 9 Kevin MacLeod "Darkness" tracks
│   ├── atomic/              # 6 uplifting Famous Classics tracks
│   └── rules/                # 6 Classical Sampler tracks
│
├── fonts/
│   ├── Cinzel.ttf           # variable font — regal headline
│   ├── PlayfairDisplay.ttf
│   └── PlayfairDisplay-Italic.ttf
│
├── output/                  # built videos (auto-committed by workflow)
│
└── scripts/
    ├── verify_token.py      # check current IG token validity + expiry
    ├── refresh_token.py     # used by refresh_token.yml workflow
    ├── fetch_backgrounds.py # one-time downloader for 48 Laws backgrounds
    ├── fetch_music.py       # one-time downloader for 48 Laws music
    ├── fetch_book_assets.py # downloader for atomic + rules backgrounds & music
    ├── make_music.ps1       # legacy synth music generator (now unused)
    ├── audit_quotes.py      # validates quotes.json structure
    └── list_days.py         # prints all queued days
```

---

## Configuration (set once)

### GitHub Secrets — repo Settings → Secrets and variables → Actions
| Name | Value | Purpose |
|---|---|---|
| `IG_USER_ID` | numeric Instagram Business Account ID | identifies which IG to post to |
| `IG_ACCESS_TOKEN` | long-lived Meta user token (60 days) | authenticates Graph API calls |
| `APP_SECRET` | Meta app secret | used by refresh workflow |
| `GH_TOKEN` | GitHub fine-grained PAT (Secrets read+write on this repo) | lets refresh workflow update IG_ACCESS_TOKEN |

### GitHub Variables — same page, Variables tab
| Name | Value | Purpose |
|---|---|---|
| `START_DATE` | `YYYY-MM-DD` | anchors Day 1 — bot computes `day = today − START_DATE + 1` |

### Local `.env` (only needed for local dry-runs, never committed)
Mirror the secrets above plus:
```env
UPLOAD_BACKEND=github
GITHUB_RAW_BASE=https://raw.githubusercontent.com/karthik20251/insta/master/output
```

---

## Token lifecycle (zero maintenance)

The Meta long-lived token expires every 60 days, but the `refresh_token.yml` workflow runs **every Monday 06:00 UTC** and exchanges the current token for a fresh one — resetting the 60-day clock. As long as that workflow keeps running, the token never expires.

The only manual step that may eventually be needed:
- **GitHub PAT renewal** — if the `GH_TOKEN` was created with a 1-year expiry, it will need to be regenerated yearly. If created with "No expiration", never.

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

# Verify the local token in .env is still valid
python scripts/verify_token.py

# Re-download all background images (Wikimedia)
python scripts/fetch_backgrounds.py
python scripts/fetch_book_assets.py

# Re-download all music (Internet Archive)
python scripts/fetch_music.py
python scripts/fetch_book_assets.py
```

---

## Adding a 4th (or 5th, 6th…) book

1. Append entries to `quotes.json` `days` array, continuing from the next day number, with `"book"` and `"author"` per day:
   ```json
   { "day": 93, "book": "Meditations", "author": "Marcus Aurelius",
     "title": "Book I", "headline": "...", "body": "..." }
   ```
2. Drop ~5–10 backgrounds into `backgrounds/<slug>/` and ~5 music tracks into `music/<slug>/`.
3. Update `generate.py::book_slug()` to map the new book name to its folder slug.
4. Update `post.py::build_caption()` to add a hashtag branch.
5. Commit and push. The bot picks up automatically.

---

## Limits and notes

- Instagram Graph API allows **25 posts / 24h per account** — way more than we need.
- Repo must be **public** for `raw.githubusercontent.com` URLs to be reachable by Meta's ingester.
- IG's built-in music library is **not** accessible via API — all music must be royalty-free files we host.
- Music currently uses Kevin MacLeod tracks (CC-BY 4.0); attribution is auto-included in every caption.

---

## Cost

**₹0.** Everything (Python, ffmpeg, GitHub Actions, Meta Graph API, Wikimedia, Internet Archive) is free.
