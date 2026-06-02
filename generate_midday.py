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
    wrap_text,
)

ROOT = Path(__file__).parent
LINES_JSON = ROOT / "motivational_lines.json"
OUT_DIR = ROOT / "output"
BG_CACHE = OUT_DIR / "bg_cache"
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
}

# Caption templates — rotate by line id so consecutive posts don't repeat phrasing.
CAPTION_TEMPLATES = [
    "{line}\n\nDrop a \U0001F525 if this hit.\n\nFollow @nandetroll_ for daily lessons.\n\n{hashtags}\n",
    "{line}\n\nSave this. Send it to someone who needs it today.\n\n@nandetroll_ for more.\n\n{hashtags}\n",
    "{line}\n\nRead it twice. Then close the app and go build.\n\n@nandetroll_ — daily wisdom, no fluff.\n\n{hashtags}\n",
    "{line}\n\nComment \"YES\" if this is exactly what you needed today.\n\nFollow @nandetroll_ for daily motivation.\n\n{hashtags}\n",
]

# Hashtag pools — universal + per-mood. Each post mixes both.
HASHTAGS_UNIVERSAL = ["#motivation", "#mindset", "#notetoself", "#dailywisdom"]
HASHTAGS_BY_MOOD = {
    "hustle":     ["#hustle", "#grindset", "#discipline", "#selfmade", "#ambition", "#betteryou"],
    "mindset":    ["#growthmindset", "#selfgrowth", "#personalgrowth", "#mindsetshift", "#reinvention", "#becoming"],
    "resilience": ["#resilience", "#keepgoing", "#neverquit", "#strongerthanyesterday", "#risingup", "#nevergiveup"],
    "worth":      ["#knowyourworth", "#selflove", "#boundaries", "#standards", "#worthit", "#respectyourself"],
    "truth":      ["#realtalk", "#harshreality", "#lifelessons", "#wisdom", "#truthbomb", "#lifequotes"],
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


def _pick_line(lines: list[dict], line_id: int | None) -> dict:
    if line_id is not None:
        for ln in lines:
            if int(ln.get("id", -1)) == int(line_id):
                return ln
        raise ValueError(f"No line with id={line_id} in {LINES_JSON.name}")
    today = _dt.date.today()
    epoch = _dt.date(2026, 1, 1)
    idx = (today - epoch).days % len(lines)
    return lines[idx]


# ---------------------------------------------------------------------------
# Background: Pexels fetch + cache + crop + scrim
# ---------------------------------------------------------------------------
def _fetch_pexels(mood: str, line_id: int) -> Image.Image:
    """Query Pexels for a portrait photo matching the mood, cache it, return PIL."""
    api_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "PEXELS_API_KEY not set. Sign up free at pexels.com/api and put the "
            "key in .env (PEXELS_API_KEY=...) or GitHub Secrets."
        )

    keywords = MOOD_KEYWORDS.get((mood or "").strip().lower(), MOOD_KEYWORDS["mindset"])
    keyword = keywords[line_id % len(keywords)]

    # Cache key: mood + line id + keyword digest, so changing keyword pool re-fetches.
    digest = hashlib.md5(f"{mood}:{line_id}:{keyword}".encode()).hexdigest()[:10]
    cache_file = BG_CACHE / f"midday_{line_id}_{digest}.jpg"
    if cache_file.exists():
        return Image.open(cache_file).convert("RGB")

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
    """Solid dark overlay so white text stays readable over any photo."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
def _fit_font(text: str, draw: ImageDraw.ImageDraw, max_w: int, max_lines: int = 3):
    """Step font 80 -> 68 -> 56 until text wraps to <= max_lines."""
    for size in (80, 68, 56):
        font = pick_font(["Cinzel.ttf"], size, weight=700)
        lines = wrap_text(text, font, max_w)
        if len(lines) <= max_lines or size == 56:
            return font, lines
    return font, lines  # type: ignore[possibly-undefined]


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

    # Gold IG-handle watermark at the bottom.
    wm_font = pick_font(["Cinzel.ttf"], 32, weight=600)
    wm = "@nandetroll_"
    b = draw.textbbox((0, 0), wm, font=wm_font)
    wm_x = (WIDTH - (b[2] - b[0])) // 2
    draw.text((wm_x, HEIGHT - 180), wm, fill=GOLD, font=wm_font)

    img.save(out_png, "PNG", optimize=True)
    print(f"bg source: {source}")


# ---------------------------------------------------------------------------
# Caption
# ---------------------------------------------------------------------------
def build_caption(line: dict) -> str:
    line_id = int(line.get("id", 1))
    mood = str(line.get("mood", "")).strip().lower() or "mindset"
    body = str(line.get("text", "")).strip()

    template = CAPTION_TEMPLATES[line_id % len(CAPTION_TEMPLATES)]
    mood_tags = HASHTAGS_BY_MOOD.get(mood, HASHTAGS_BY_MOOD["mindset"])
    hashtags = " ".join(HASHTAGS_UNIVERSAL + mood_tags)
    return template.format(line=body, hashtags=hashtags)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render midday motivation PNG + caption.")
    ap.add_argument("--line-id", type=int, default=None,
                    help="Pick a specific line by id (defaults to today's date-deterministic choice).")
    args = ap.parse_args(argv)

    lines = _load_lines()
    chosen = _pick_line(lines, args.line_id)

    today = _dt.date.today().isoformat()
    out_png = OUT_DIR / f"midday_{today}.png"
    out_txt = OUT_DIR / f"midday_{today}.txt"

    render(chosen, out_png)
    out_txt.write_text(build_caption(chosen), encoding="utf-8")

    print(f"line id={chosen.get('id')} mood={chosen.get('mood')!r}")
    print(f"image: {out_png}")
    print(f"caption: {out_txt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
