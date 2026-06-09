"""Render a single 1080x1920 portrait PNG with one trending motivation line
centered on a Pexels-sourced background matched to the line's mood, plus a
paste-ready caption .txt with rotating templates + hashtags.

NO video, NO audio, NO posting — just two files (image + caption) per run.

Inputs
------
- motivational_lines.json (project root) — shape: {"lines": [{"id": int,
  "text": str, "mood": str}, ...]}.
- PEXELS_API_KEY (env, via python-dotenv) — required; sign up free at
  pexels.com/api.

CLI
---
    python generate_midday.py                  # date-deterministic line
    python generate_midday.py --line-id 7      # explicit line by id

Outputs (overwrite each run)
----------------------------
    output/midday_<YYYY-MM-DD>.png    (1080x1920, valid PNG)
    output/midday_<YYYY-MM-DD>.txt    (paste-ready caption)
    output/bg_cache/midday_<id>_*.jpg (Pexels background cache, reused)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import io
import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import requests
from PIL import Image, ImageDraw

# Only reuse the font picker + text-wrap helpers + canvas dims from generate.py.
# We do NOT use make_background here — backgrounds are Pexels-sourced now.
from generate import (
    HEIGHT,
    WIDTH,
    GOLD,
    WHITE,
    pick_font,
)

ROOT = Path(__file__).parent
LINES_JSON = ROOT / "motivational_lines.json"
OUT_DIR = ROOT / "output"
BG_CACHE = OUT_DIR / "bg_cache"
# Cursor file: tracks which line to render NEXT. Advances by 1 on each render
# (manual workflow_dispatch). Lives in state/ so it's git-tracked and persists
# across ephemeral GitHub Actions runners.
CURSOR_FILE = ROOT / "state" / "midday_cursor.json"
OUT_DIR.mkdir(exist_ok=True)
BG_CACHE.mkdir(exist_ok=True, parents=True)

# ---------------------------------------------------------------------------
# Mood -> Pexels search keywords. Each list contains 5 keyword variants so the
# background rotates even *within* a mood (line id modulo list length).
# The visual feel of each keyword set echoes the line's emotional tone.
MOOD_KEYWORDS = {
    "hustle":     ["city sunrise skyline", "lone runner dawn", "neon city night", "morning workout sunrise", "mountain trail runner"],
    "mindset":    ["calm mountain lake sunrise", "starry night sky", "misty forest sunlight", "peaceful ocean sunset", "person looking out window"],
    "resilience": ["stormy ocean waves", "lone tree storm", "lightning dramatic sky", "lighthouse storm", "mountain peak climber"],
    "worth":      ["golden hour silhouette portrait", "elegant night city lights", "gold sunset bridge", "marble statue dramatic light", "luxury rooftop sunset"],
    "truth":      ["dramatic dark clouds", "fog city street dawn", "moody mountain landscape", "abandoned road desert", "single light dark room"],
    # Office politics: corporate, suit, boardroom, glass tower energy.
    "office":     ["executive boardroom dark", "suit silhouette city window", "modern office tower night", "corporate skyline dusk", "marble lobby corporate"],
    # Wisdom / philosophy: timeless, contemplative, ancient + classical energy.
    "wisdom":     ["marble statue ancient", "old library books wooden", "candle dark room contemplation", "ancient temple columns", "sunset mountain reflection"],
}

# Instagram handle + YouTube handle (kept in code, not in image data) — image
# stays platform-agnostic; handles only appear in the caption text.
HANDLE_IG = "@nandetroll_"
HANDLE_YT = "@getunwrittenrules"

# ---- INSTAGRAM caption templates ---------------------------------------------
# 4 rotating templates; ~10 hashtags per post (IG sweet spot in 2026).
# Engagement-tuned: save/share/reply drivers, NO explicit "follow" asks (IG
# anti-bait detection penalizes those), NO "close the app" CTAs (kills dwell
# time, which IG rewards). Handle appears as identity ("{h} —"), not a request.
IG_TEMPLATES = [
    # A — save-driver (#1 IG algorithm signal). Universal across moods —
    # "you'll need it again" works for hustle/resilience AND office/wisdom.
    "{line}\n\nSave this. You'll need it again.\n\n{h} — daily lessons that hit.\n\n{hashtags}\n",
    # B — save + share (KEPT — best performer of the original set)
    "{line}\n\nSave this. Send it to someone who needs it today.\n\n{h} — more like this every day.\n\n{hashtags}\n",
    # C — read + apply (in-app action, no exit signal)
    "{line}\n\nRead it twice. Screenshot it. Use it tomorrow.\n\n{h} — wisdom you can actually use.\n\n{hashtags}\n",
    # D — open question (drives comments without bait-pattern phrasing)
    "{line}\n\nWhich part of this hit hardest? \U0001F447\n\n{h} — for the ones building quietly.\n\n{hashtags}\n",
]
# SMM-2026 strategy: small accounts cannot rank on >50M-post tags. Algorithm
# never surfaces sub-1K-follower accounts in #motivation (350M posts) or
# #mindset (100M). Strategy = mostly mid-volume (1M-30M, where small accounts
# can rank) + niche (50K-500K, where small accounts can DOMINATE) + 1-2 high-
# volume tags for ceiling discovery if a post breaks out.
# 2026-06-09: hashtag pools refreshed to match the new 12 market-trending
# lines (quiet firing / AI / layoffs / RTO / boundaries / anti-hustle). Old
# generic-motivation tags (#hustlewisdom, #weatheredwisdom etc.) replaced
# with current-discourse tags people actually search in 2026:
#   #quietquitting, #worklifebalance, #boundaries, #layoffsurvivor,
#   #burnout, #hustleculture, #ailayoffs, #protectyourpeace.
IG_HASHTAGS_UNIVERSAL = [
    "#unwrittenrules",     # brand tag — discoverability corpus over time
    "#worklifebalance",    # high-volume, on-brand for 2026 zeitgeist
    "#careeradvice",       # mid-volume, niche-appropriate
    "#corporatesurvival",  # niche, room to rank
]
IG_HASHTAGS_BY_MOOD = {
    # Each pool: trending-theme tags matching the line content. Mix of high-
    # volume (broad discovery) and niche (rankable for small accounts).
    # NOTE: tags here must NOT overlap with IG_HASHTAGS_UNIVERSAL above —
    # otherwise the final caption ends up with the same hashtag twice, which
    # IG reads as spam/desperation signal.
    "worth":      ["#knowyourworth", "#boundaries", "#protectyourpeace", "#toxicworkplace", "#careerwellness", "#boundariesatwork"],
    "resilience": ["#layoffsurvivor", "#careergrowth", "#careertransition", "#resilience", "#joblossadvice", "#careerresilience"],
    "mindset":    ["#burnout", "#mentalhealth", "#selfcare", "#worksmarter", "#careerwellness", "#mentalhealthatwork"],
    "office":     ["#officepolitics", "#ailayoffs", "#quietfiring", "#careerstrategy", "#climbingtheladder", "#workplacewisdom"],
    "truth":      ["#hustleculture", "#antihustle", "#realtalk", "#burnoutawareness", "#harshtruths", "#hardtruths"],
    "hustle":     ["#quietgrind", "#discipline", "#highperformance", "#careergrowth", "#ambition", "#selfmade"],
    "wisdom":     ["#stoicwisdom", "#stoicism", "#philosophyoflife", "#mentalhealth", "#realtalk", "#hardtruths"],
}

# ---- YOUTUBE (Shorts) caption templates --------------------------------------
# YT Shorts: #shorts ALWAYS first (mandatory for Shorts ranking), 3-5 tags
# total. No explicit "subscribe" asks (YT penalizes pattern-bait similar to
# IG). Handle appears as channel identity, not a CTA. Engagement asks favor
# in-app actions (comment/replay) over "go do X elsewhere".
YT_TEMPLATES = [
    # A — replay-driver (YT rewards rewatches on Shorts)
    "{line}\n\nWatch it twice. The second one hits different.\n{h} — daily lessons.\n\n{hashtags}\n",
    # B — share-driver
    "{line}\n\nShare this with one person who needs to hear it today.\n{h} — more like this every day.\n\n{hashtags}\n",
    # C — apply (in-app screenshot, no exit signal)
    "{line}\n\nScreenshot it. Use it tomorrow.\n{h} — wisdom you can actually use.\n\n{hashtags}\n",
    # D — open comment question (not bait-pattern)
    "{line}\n\nWhich part hit hardest? Tell me below.\n{h} — for the ones building quietly.\n\n{hashtags}\n",
]
# YT Shorts: #shorts is mandatory and goes first. Drop overused #motivation
# (350M-tag = invisible for small channels) in favor of #unwrittenrules (brand)
# and #dailylessons (mid-volume, on-brand).
# YT: 3 universal + 3 mood-specific. Same anti-overlap rule.
YT_HASHTAGS_UNIVERSAL = ["#shorts", "#unwrittenrules", "#worklifebalance"]
YT_HASHTAGS_BY_MOOD = {
    "worth":      ["#boundaries", "#knowyourworth", "#careerwellness"],
    "resilience": ["#layoffsurvivor", "#careertransition", "#careergrowth"],
    "mindset":    ["#burnout", "#mentalhealth", "#selfcare"],
    "office":     ["#officepolitics", "#careeradvice", "#corporatesurvival"],
    "truth":      ["#hustleculture", "#antihustle", "#realtalk"],
    "hustle":     ["#quietgrind", "#discipline", "#careergrowth"],
    "wisdom":     ["#stoicism", "#philosophyoflife", "#mentalhealth"],
}


# ---------------------------------------------------------------------------
# Line loading + selection
# ---------------------------------------------------------------------------
def _load_lines() -> list[dict]:
    if not LINES_JSON.exists():
        raise FileNotFoundError(f"{LINES_JSON.name} not found at {LINES_JSON}")
    data = json.loads(LINES_JSON.read_text(encoding="utf-8"))
    lines = data.get("lines")
    if not isinstance(lines, list) or not lines:
        raise ValueError(f"{LINES_JSON.name} must contain a non-empty 'lines' list.")
    return lines


def _read_cursor() -> int:
    """Read the cursor index. Defaults to 0 if file missing/corrupt."""
    if not CURSOR_FILE.exists():
        return 0
    try:
        data = json.loads(CURSOR_FILE.read_text(encoding="utf-8"))
        return int(data.get("next_idx", 0))
    except (json.JSONDecodeError, ValueError, KeyError):
        return 0


def _write_cursor(next_idx: int) -> None:
    """Persist the cursor for the next manual run."""
    CURSOR_FILE.parent.mkdir(exist_ok=True, parents=True)
    CURSOR_FILE.write_text(
        json.dumps({"next_idx": next_idx}, indent=2) + "\n",
        encoding="utf-8",
    )


def _pick_line(lines: list[dict], line_id: int | None) -> tuple[dict, int | None]:
    """Pick the next line to render.

    Returns (line, new_cursor). If line_id is provided (explicit override for
    testing), new_cursor is None — caller should NOT advance the cursor.
    Otherwise the cursor is advanced by 1 (and wraps at len(lines))."""
    if line_id is not None:
        for ln in lines:
            if int(ln.get("id", -1)) == int(line_id):
                return ln, None
        raise ValueError(f"No line with id={line_id} in {LINES_JSON.name}")

    idx = _read_cursor() % len(lines)
    next_idx = (idx + 1) % len(lines)
    return lines[idx], next_idx


# ---------------------------------------------------------------------------
# Background: Pexels fetch + cache + crop + scrim
# ---------------------------------------------------------------------------
def _fetch_pexels(mood: str, line_id: int) -> Image.Image:
    """Query Pexels for a portrait photo matching the mood, cache it, return PIL.
    Retries once on transient network errors so a flaky Pexels call doesn't
    silently degrade the daily render to the solid-fallback path."""
    api_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "PEXELS_API_KEY not set. Sign up free at pexels.com/api and put the "
            "key in .env (PEXELS_API_KEY=...) or GitHub Secrets."
        )

    keywords = MOOD_KEYWORDS.get((mood or "").strip().lower(), MOOD_KEYWORDS["mindset"])
    keyword = keywords[line_id % len(keywords)]

    digest = hashlib.md5(f"{mood}:{line_id}:{keyword}".encode()).hexdigest()[:10]
    cache_file = BG_CACHE / f"midday_{line_id}_{digest}.jpg"
    if cache_file.exists():
        return Image.open(cache_file).convert("RGB")

    last_err: Exception | None = None
    for attempt in (1, 2):
        try:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": api_key},
                params={"query": keyword, "orientation": "portrait", "per_page": 15, "size": "large"},
                timeout=20,
            )
            r.raise_for_status()
            photos = r.json().get("photos", [])
            if not photos:
                raise RuntimeError(f"No Pexels results for query: {keyword!r}")

            photo = photos[line_id % len(photos)]
            img_url = photo["src"].get("large2x") or photo["src"].get("large") or photo["src"]["original"]
            img_resp = requests.get(img_url, timeout=45)
            img_resp.raise_for_status()
            img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
            img.save(cache_file, "JPEG", quality=88, optimize=True)
            return img
        except (requests.RequestException, RuntimeError) as e:
            last_err = e
            if attempt == 1:
                continue
            raise
    raise last_err  # unreachable but satisfies the type checker


def _crop_to_canvas(img: Image.Image) -> Image.Image:
    """Resize-and-center-crop any source photo to exactly 1080x1920."""
    target_w, target_h = WIDTH, HEIGHT
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h
    if src_ratio > target_ratio:
        new_h = target_h
        new_w = int(round(src_w * (new_h / src_h)))
    else:
        new_w = target_w
        new_h = int(round(src_h * (new_w / src_w)))
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _apply_scrim(img: Image.Image, alpha: int = 150) -> Image.Image:
    """Two-layer dark overlay so the text + watermark stay legible on any photo:
      1) uniform alpha=`alpha` scrim across the full image for body-text contrast
      2) bottom-anchored gradient (transparent at y=HEIGHT-340 → opaque at bottom)
         so the gold watermark at HEIGHT-180 always sits on near-black, even
         when the source photo has a bright lower third (sunsets, rocks, etc.)
    """
    w, h = img.size
    full = Image.new("RGBA", (w, h), (0, 0, 0, alpha))
    bottom_band_h = 340
    band = Image.new("RGBA", (w, bottom_band_h), (0, 0, 0, 0))
    band_draw = ImageDraw.Draw(band)
    for row in range(bottom_band_h):
        a = int(180 * (row / max(1, bottom_band_h - 1)))
        band_draw.line([(0, row), (w - 1, row)], fill=(0, 0, 0, a))
    base = img.convert("RGBA")
    base = Image.alpha_composite(base, full)
    base.paste(band, (0, h - bottom_band_h), band)
    return base.convert("RGB")


# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
def _line_w(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    b = draw.textbbox((0, 0), text, font=font)
    return b[2] - b[0]


def _greedy_wrap(words: list[str], draw: ImageDraw.ImageDraw, font, max_w: int) -> list[str]:
    """Standard greedy word-wrap — used only to discover the minimum line count."""
    out: list[str] = []
    line: list[str] = []
    for w in words:
        candidate = " ".join(line + [w])
        if not line or _line_w(draw, candidate, font) <= max_w:
            line.append(w)
        else:
            out.append(" ".join(line))
            line = [w]
    if line:
        out.append(" ".join(line))
    return out


_PUNCT_ENDS = (".", ",", ";", ":", "!", "?", "—")
# Per-bad-break penalty (pixels-equivalent). Punctuation-aligned layouts win
# over alphabetic-split layouts even when slightly wider.
_BAD_BREAK_PENALTY = 250
# Word-count variance penalty. Strong enough to favor balanced word-counts
# (e.g. [3,3] over [4,2]) when widths are close — kills orphan "YOU" endings.
_BALANCE_PENALTY = 150


def _is_good_break(word: str) -> bool:
    """A break is 'good' if the word ending the line terminates a clause."""
    return word.endswith(_PUNCT_ENDS)


def _wrap_one_segment(words: list[str], draw: ImageDraw.ImageDraw, font, max_w: int) -> list[str]:
    """Balanced wrap of a single segment (no hard \\n inside). Score combines:
      max_line_width + bad-break-penalty + word-count-balance-penalty
    Picks the layout that's wide-balanced AND clause-aligned AND word-balanced."""
    if not words:
        return [""]
    greedy = _greedy_wrap(words, draw, font, max_w)
    n_lines = len(greedy)
    if n_lines <= 1:
        return greedy

    from itertools import combinations

    def score(chunks: list[str], splits: tuple[int, ...]) -> int:
        widest = max(_line_w(draw, c, font) for c in chunks)
        bad = sum(_BAD_BREAK_PENALTY for s in splits if not _is_good_break(words[s - 1]))
        counts = [len(c.split()) for c in chunks]
        if len(counts) > 1:
            mean = sum(counts) / len(counts)
            variance = sum((c - mean) ** 2 for c in counts) / len(counts)
            balance = int(variance * _BALANCE_PENALTY)
        else:
            balance = 0
        return widest + bad + balance

    best = greedy
    best_score = score(greedy, tuple(
        sum(len(g.split()) for g in greedy[:i + 1]) for i in range(n_lines - 1)
    ))

    for splits in combinations(range(1, len(words)), n_lines - 1):
        chunks = []
        prev = 0
        for s in splits:
            chunks.append(" ".join(words[prev:s]))
            prev = s
        chunks.append(" ".join(words[prev:]))
        if any(_line_w(draw, c, font) > max_w for c in chunks):
            continue
        sc = score(chunks, splits)
        if sc < best_score:
            best = chunks
            best_score = sc
    return best


def _balanced_wrap(text: str, draw: ImageDraw.ImageDraw, font, max_w: int) -> list[str]:
    """Wrap text into balanced lines. Honors `\\n` in source as hard breaks
    (editorial control). Each segment is wrapped independently and joined."""
    # Hard breaks first — editorial overrides everything else.
    segments = text.split("\n")
    out: list[str] = []
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        out.extend(_wrap_one_segment(seg.split(), draw, font, max_w))
    return out or [""]


def _fit_font(text: str, draw: ImageDraw.ImageDraw, max_w: int, max_lines: int = 3):
    """Prefer FEWER lines over bigger font — fewer lines means natural break
    points fall on stronger semantic boundaries. Tries 2 lines at each size,
    then 3 as fallback. 48pt is the emergency rung for long lines with hard
    \\n breaks that can't fit otherwise."""
    sizes = (80, 68, 56, 48)
    for target_lines in range(2, max_lines + 1):
        for size in sizes:
            font = pick_font(["Cinzel.ttf"], size, weight=700)
            lines = _balanced_wrap(text, draw, font, max_w)
            if len(lines) <= target_lines:
                return font, lines
    font = pick_font(["Cinzel.ttf"], sizes[-1], weight=700)
    return font, _balanced_wrap(text, draw, font, max_w)


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render(line: dict, out_png: Path) -> None:
    mood = str(line.get("mood", "")).strip().lower() or "mindset"
    line_id = int(line.get("id", 1))

    try:
        bg = _fetch_pexels(mood, line_id)
        bg = _crop_to_canvas(bg)
        bg = _apply_scrim(bg, alpha=150)
        source = "pexels"
    except Exception as e:
        # Fallback: solid dark gradient so the pipeline still produces a file.
        print(f"[warn] Pexels failed ({e}); using solid dark fallback", file=sys.stderr)
        bg = Image.new("RGB", (WIDTH, HEIGHT), (12, 12, 16))
        source = "fallback"

    img = bg
    draw = ImageDraw.Draw(img)

    margin = 120
    max_w = WIDTH - 2 * margin

    text = str(line.get("text", "")).strip()
    if not text:
        raise ValueError(f"Line id={line_id} has empty 'text'")

    font, wrapped = _fit_font(text, draw, max_w, max_lines=3)

    line_gap = 18

    def lh(s: str) -> int:
        b = draw.textbbox((0, 0), s, font=font)
        return b[3] - b[1]

    total_h = sum(lh(s) for s in wrapped) + line_gap * max(0, len(wrapped) - 1)
    y = (HEIGHT - total_h) // 2

    for s in wrapped:
        b = draw.textbbox((0, 0), s, font=font)
        x = (WIDTH - (b[2] - b[0])) // 2
        draw.text((x, y), s, fill=WHITE, font=font)
        y += lh(s) + line_gap

    # Dual-handle gold watermark at bottom — both IG and YT handles with short
    # platform labels so viewers know which is which. Image stays usable on
    # either platform without re-rendering.
    wm_font = pick_font(["Cinzel.ttf"], 26, weight=600)
    wm = f"IG  {HANDLE_IG}     YT  {HANDLE_YT}"
    b = draw.textbbox((0, 0), wm, font=wm_font)
    wm_x = (WIDTH - (b[2] - b[0])) // 2
    draw.text((wm_x, HEIGHT - 180), wm, fill=GOLD, font=wm_font)

    img.save(out_png, "PNG", optimize=True)
    print(f"bg source: {source}")


# ---------------------------------------------------------------------------
# Caption
# ---------------------------------------------------------------------------
def _resolve_body(line: dict) -> str:
    """Strip the editorial \\n hard-break markers — captions read as one
    continuous sentence; the \\n only affects on-image wrap."""
    return str(line.get("text", "")).strip().replace("\n", " ")


def build_caption_ig(line: dict) -> str:
    line_id = int(line.get("id", 1))
    mood = str(line.get("mood", "")).strip().lower() or "mindset"
    body = _resolve_body(line)
    template = IG_TEMPLATES[line_id % len(IG_TEMPLATES)]
    mood_tags = IG_HASHTAGS_BY_MOOD.get(mood, IG_HASHTAGS_BY_MOOD["mindset"])
    hashtags = " ".join(IG_HASHTAGS_UNIVERSAL + mood_tags)
    return template.format(line=body, h=HANDLE_IG, hashtags=hashtags)


def build_caption_yt(line: dict) -> str:
    line_id = int(line.get("id", 1))
    mood = str(line.get("mood", "")).strip().lower() or "mindset"
    body = _resolve_body(line)
    template = YT_TEMPLATES[line_id % len(YT_TEMPLATES)]
    mood_tags = YT_HASHTAGS_BY_MOOD.get(mood, YT_HASHTAGS_BY_MOOD["mindset"])
    hashtags = " ".join(YT_HASHTAGS_UNIVERSAL + mood_tags)
    return template.format(line=body, h=HANDLE_YT, hashtags=hashtags)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render midday motivation PNG + caption.")
    ap.add_argument("--line-id", type=int, default=None,
                    help="Pick a specific line by id (defaults to today's date-deterministic choice).")
    args = ap.parse_args(argv)

    lines = _load_lines()
    chosen, new_cursor = _pick_line(lines, args.line_id)

    today = _dt.date.today().isoformat()
    out_png = OUT_DIR / f"midday_{today}.png"
    out_ig = OUT_DIR / f"midday_{today}_ig.txt"
    out_yt = OUT_DIR / f"midday_{today}_yt.txt"

    render(chosen, out_png)
    out_ig.write_text(build_caption_ig(chosen), encoding="utf-8")
    out_yt.write_text(build_caption_yt(chosen), encoding="utf-8")

    # Post-number-in-cycle: the position of THIS image in the rotation. If
    # the picker advanced the cursor (no --line-id override), new_cursor is
    # set; we report the position BEFORE the advance ("post 5/65" means this
    # render is the 5th in the cycle).
    if new_cursor is not None:
        post_num = ((new_cursor - 1) % len(lines)) + 1
        _write_cursor(new_cursor)
    else:
        post_num = 0  # 0 indicates an override (--line-id) render, not part of the rotation
    cycle_len = len(lines)

    print(f"line id={chosen.get('id')} mood={chosen.get('mood')!r}")
    print(f"post={post_num}/{cycle_len}")
    print(f"mood={chosen.get('mood')}")
    print(f"image: {out_png}")
    print(f"ig caption: {out_ig}")
    print(f"yt caption: {out_yt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
