# 48 Laws of Power — Daily Instagram Reel Bot

Posts a Reel every day for 49 days: Day 1 = introduction, Days 2–49 = one law each.

## What you set up once

### A. Instagram + Meta (free)
1. Switch your Instagram to **Business** or **Creator** (Settings → Account type).
2. Create a Facebook **Page** and link it to that Instagram in *Settings → Linked accounts*.
3. Go to https://developers.facebook.com → My Apps → Create App → type **Business**.
4. Add the **Instagram Graph API** product.
5. In **Graph API Explorer**, generate a **User Access Token** with these permissions:
   `instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement, business_management`
6. Convert it to a **long-lived (60-day) token**:
   ```
   https://graph.facebook.com/v21.0/oauth/access_token?
     grant_type=fb_exchange_token&
     client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN
   ```
7. Get your **IG Business Account ID**:
   ```
   GET /me/accounts                          → get page_id
   GET /{page_id}?fields=instagram_business_account
   ```

### B. GitHub (free, runs the bot in the cloud)
1. Create a **public** repo (must be public for raw URL hosting), push this folder to it.
2. In the repo: *Settings → Secrets and variables → Actions*
   - **Secrets**: `IG_USER_ID`, `IG_ACCESS_TOKEN`
   - **Variables**: `START_DATE` (e.g. `2026-05-11` — the day you want intro to post)
3. Done — the workflow runs daily at 09:00 IST (03:30 UTC). Edit cron in `.github/workflows/daily.yml` to change.

### C. Local one-time
```
pip install -r requirements.txt
# install ffmpeg: https://ffmpeg.org/download.html — add to PATH
```

## What you drop into the folders

- `music/` — 5–10 royalty-free `.mp3` tracks (sources: pixabay.com/music, youtube.com/audiolibrary). Bot picks one at random per day.
- `fonts/` — at least one `.ttf`. Recommended free fonts (Google Fonts):
  - `Cinzel-Bold.ttf` (regal headline)
  - `PlayfairDisplay-Regular.ttf` (body)
  - `PlayfairDisplay-Italic.ttf` (footer)

If `fonts/` is empty the bot falls back to PIL's default font (works but ugly).

## Test locally before going live

```bash
# build day 1 only, don't post
python main.py --dry-run

# preview the image
start output/day_01.png
```

## Daily flow (what the workflow does)

1. Compute `day = today - START_DATE + 1`
2. `generate.py` → renders 1080x1920 PNG → ffmpeg merges with random music track → 12-sec MP4
3. Commits `output/day_NN.mp4` back to the repo so it has a public raw URL
4. `post.py` → calls Graph API: create REELS container → wait for ingestion → publish

## Caption (auto-built)

```
Law N — <headline>

<body text>

— Robert Greene, The 48 Laws of Power

Day N of 49 · The 48 Laws of Power series

#48lawsofpower #robertgreene ...
```

## Limits / gotchas

- IG Graph API allows 25 posts per 24h — daily is fine.
- Long-lived token expires after 60 days. Refresh by running step A.6 again, or add a refresh step.
- Music must be royalty-free (you upload it yourself). IG's built-in music library is **not** accessible via API.
- Repo must be **public** for `raw.githubusercontent.com` URLs to work. If you need private, set `UPLOAD_BACKEND=transfer` in `.env` (uses transfer.sh, but URLs expire ~14 days — IG only needs it during ingestion so this is OK).
