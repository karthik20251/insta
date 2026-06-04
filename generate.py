"""Build a 1080x1920 Reel: gradient background + quote text + a music track."""
from __future__ import annotations
import json
import os
import random
import subprocess
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

try:
    from dotenv import load_dotenv
    load_dotenv()  # factory is run directly now — pick up AMAZON_AFFILIATE_TAG
except Exception:
    pass

ROOT = Path(__file__).parent
QUOTES = ROOT / "quotes.json"
MUSIC_DIR = ROOT / "music"
FONTS_DIR = ROOT / "fonts"
BG_DIR = ROOT / "backgrounds"
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(exist_ok=True)

WIDTH, HEIGHT = 1080, 1920
DURATION_SEC = 22
INTRO_FRAME_SEC = 3        # 0-3:    tease (hook — voiced)
MAIN_FRAME_SEC = 7         # 3-10:   the law/principle reveal (voiced)
EXAMPLE_FRAME_SEC = 7      # 10-17:  real-life application + comment question
END_FRAME_SEC = 5          # 17-22:  loss-aversion CTA (save/follow/share/like)

GOLD = (212, 175, 55)
WHITE = (240, 240, 240)
DIM = (170, 170, 170)


# Variant -> mood, so the (untouched) music selector keeps working without a
# stored `mood` field. TACTIC = assertive, MISTAKE = tense, SCENARIO = reflective.
_VARIANT_MOOD = {"TACTIC": "regal", "MISTAKE": "tense", "SCENARIO": "contemplative"}


def load_day(day_num: int) -> dict:
    """Load variant-item `day_num` (1-based) from the repositioned items[] model.

    Returns the item augmented with backward-compatible keys (`day`, `mood`,
    `book_day`, `book_total`, `total_days`) so the dormant post.py / main.py /
    post_youtube paths keep working unchanged while manual posting is active.
    """
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    default_book = data["book"]
    default_author = data["author"]
    items = data["items"]

    # parent (law/rule/principle) position within its book, for legacy footers
    parent_seen: dict[str, list[str]] = {}
    for it in items:
        b = it.get("book", default_book)
        lst = parent_seen.setdefault(b, [])
        if it["parent_law"] not in lst:
            lst.append(it["parent_law"])

    for it in items:
        if it["item"] == day_num:
            book = it.get("book", default_book)
            plist = parent_seen[book]
            result = dict(it)
            result["day"] = it["item"]
            result.setdefault("author", default_author)
            result["mood"] = it.get("mood") or _VARIANT_MOOD.get(it.get("variant_type", ""), "regal")
            result["book_day"] = plist.index(it["parent_law"]) + 1
            result["book_total"] = len(plist)
            result["total_days"] = len(items)
            return result
    raise ValueError(f"No entry for item {day_num}")


def total_days() -> int:
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    return len(data["items"])


def pick_font(preferred: list[str], size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    """Load the first font in `preferred` that exists. If `weight` is given and the font
    is a variable font with a 'wght' axis, set the weight (e.g. 700 for bold)."""
    chosen: Path | None = None
    for name in preferred:
        p = FONTS_DIR / name
        if p.exists():
            chosen = p
            break
    if chosen is None:
        any_ttf = sorted(FONTS_DIR.glob("*.ttf")) + sorted(FONTS_DIR.glob("*.otf"))
        if any_ttf:
            chosen = any_ttf[0]
    if chosen is None:
        return ImageFont.load_default()
    font = ImageFont.truetype(str(chosen), size)
    if weight is not None:
        try:
            font.set_variation_by_axes([weight])
        except Exception:
            pass
    return font


def draw_gradient(img: Image.Image) -> None:
    """Vertical dark gradient: near-black top → very dark gold bottom."""
    top = (8, 6, 4)
    bottom = (28, 20, 6)
    px = img.load()
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        for x in range(WIDTH):
            px[x, y] = (r, g, b)


def book_slug(book_name: str) -> str:
    """Map a book name to its asset subfolder."""
    b = book_name.lower()
    if "atomic" in b:
        return "atomic"
    if "12 rules" in b or "jordan peterson" in b:
        return "rules"
    if book_name and "48 laws" not in b and "robert greene" not in b:
        import sys
        print(f"[generate] WARN: unknown book {book_name!r} -> falling back to '48laws' slug", file=sys.stderr)
    return "48laws"


# Per-image scrim overrides — pulls bright backgrounds under the readability
# ceiling without changing the global atomic palette. Tuple = (base_dark_bright,
# edge_dark_bright, base_dark_standard, edge_dark_standard). Audit confirmed
# these three atomic backgrounds have center_text_zone_luminance > 75 — bump
# them to the 48laws-strength scrim values.
PER_IMAGE_SCRIM: dict[str, tuple[float, float, float, float]] = {
    "hokusai_great_wave.jpg":      (0.32, 0.14, 0.62, 0.22),
    "turner_fighting_temeraire.jpg":(0.32, 0.14, 0.62, 0.22),
    "wanderer_fog.jpg":            (0.32, 0.14, 0.62, 0.22),
}

# Per-image post-processing — applied AFTER scrim composite, BEFORE return.
# Currently only Monet, whose low std-dev is artistic intent but renders flat
# without a slight contrast+saturation bump.
PER_IMAGE_POSTPROCESS: dict[str, dict] = {
    "monet_impression_sunrise.jpg": {"contrast": 1.15, "color": 1.20},
}


# Pexels keyword pools per book — same idea as generate_midday.py but tuned
# for video-frame backgrounds (less text-heavy, more atmospheric). 8 keywords
# per book so day-to-day rotation gets visual variety even for one book.
PEXELS_BOOK_KEYWORDS = {
    "48laws": [
        "dark corporate office building night",
        "executive suit silhouette city",
        "moody city skyline at night",
        "marble lobby corporate dark",
        "chess board strategy dramatic light",
        "luxury penthouse night view",
        "boardroom dark wood table",
        "modern office tower at dusk",
    ],
    "atomic": [
        "morning workout sunrise outdoor",
        "lone runner dawn city",
        "minimalist workspace coffee",
        "person reading by window morning",
        "early morning fog mountain trail",
        "habit journal notebook minimalist",
        "discipline workout gym dim",
        "morning meditation calm light",
    ],
    "rules": [
        "marble statue ancient philosophy",
        "ancient stone temple columns",
        "old library wooden books warm light",
        "candle dark room contemplation",
        "classical sculpture dramatic shadow",
        "ancient ruins moody light",
        "philosophical bust marble close-up",
        "monk monastery stone arches",
    ],
}


def _try_pexels_background(book: str, day_num: int) -> Image.Image | None:
    """Fetch a Pexels portrait photo matched to the book's energy. Returns the
    cropped 1080x1920 image, or None if Pexels is unavailable (no key, network
    error, no results). Caller falls back to painting on None.

    Cached to backgrounds/pexels_cache/ so the 4 frames of a single video share
    one API call, and re-renders of the same (book, day) are free."""
    api_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not api_key:
        return None

    import hashlib
    import io
    try:
        import requests
    except ImportError:
        return None

    slug = book_slug(book) if book else "48laws"
    keywords = PEXELS_BOOK_KEYWORDS.get(slug, PEXELS_BOOK_KEYWORDS["48laws"])
    keyword = keywords[day_num % len(keywords)]

    digest = hashlib.md5(f"{slug}:{day_num}:{keyword}".encode()).hexdigest()[:10]
    cache_dir = BG_DIR / "pexels_cache"
    cache_dir.mkdir(exist_ok=True)
    cache_file = cache_dir / f"video_{slug}_d{day_num:03d}_{digest}.jpg"
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
                return None
            photo = photos[day_num % len(photos)]
            img_url = photo["src"].get("large2x") or photo["src"].get("large") or photo["src"]["original"]
            ir = requests.get(img_url, timeout=45)
            ir.raise_for_status()
            img = Image.open(io.BytesIO(ir.content)).convert("RGB")
            # Resize-and-center-crop to 1080x1920
            sw, sh = img.size
            target_ratio = WIDTH / HEIGHT
            src_ratio = sw / sh
            if src_ratio > target_ratio:
                new_h, new_w = HEIGHT, int(round(sw * (HEIGHT / sh)))
            else:
                new_w, new_h = WIDTH, int(round(sh * (WIDTH / sw)))
            img = img.resize((new_w, new_h), Image.LANCZOS)
            left, top = (new_w - WIDTH) // 2, (new_h - HEIGHT) // 2
            img = img.crop((left, top, left + WIDTH, top + HEIGHT))
            img.save(cache_file, "JPEG", quality=88, optimize=True)
            return img
        except (requests.RequestException, OSError) as e:
            last_err = e
            if attempt == 1:
                continue
    import sys
    print(f"[generate] Pexels failed for {keyword!r}: {last_err}", file=sys.stderr)
    return None


def make_background(day_num: int, book: str = "", scrim: str = "standard") -> Image.Image:
    """Build a 1080x1920 video-frame background.

    PRIMARY:  Pexels photo matched to the book's energy (modern, atmospheric).
    FALLBACK: deterministic painting from backgrounds/<book>/ (if Pexels
              unavailable — no key, network down, no results, etc).
    ULTIMATE: gradient (if even paintings are missing)."""
    slug = book_slug(book) if book else "48laws"

    # Try Pexels first — modern photographic backgrounds.
    pexels_bg = _try_pexels_background(book, day_num)
    if pexels_bg is not None:
        bg = pexels_bg
        bg_name = "pexels"  # disables PER_IMAGE_* overrides (those key on filename)
    else:
        # Fallback: deterministic painting from book's subfolder.
        # K=23 is coprime with every pool size we'll ship (gcd-safe).
        # Book offset adds variety so AM/PM on the same day don't drift to
        # the same relative index across books.
        book_dir = BG_DIR / slug
        backgrounds = sorted(book_dir.glob("*.jpg")) + sorted(book_dir.glob("*.png"))
        if not backgrounds:
            backgrounds = sorted(BG_DIR.glob("*.jpg")) + sorted(BG_DIR.glob("*.png"))
        if not backgrounds:
            img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
            draw_gradient(img)
            return img
        K = 23
        book_offset = sum(ord(c) for c in slug) % len(backgrounds)
        bg_path = backgrounds[(day_num * K + 3 + book_offset) % len(backgrounds)]
        try:
            bg = Image.open(bg_path).convert("RGB")
            bg_name = bg_path.name
        except OSError as e:
            import sys
            print(f"[generate] WARN: could not open {bg_path.name}: {e} — using gradient", file=sys.stderr)
            img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
            draw_gradient(img)
            return img

    if bg.size != (WIDTH, HEIGHT):
        bg = bg.resize((WIDTH, HEIGHT), Image.LANCZOS)

    # Build a single-row darkening mask (white where we want darker, black where we want lighter)
    # Then stretch it to full image and use as opacity mask blending bg with black.
    # `bright` (intro + end frames) realizes the committed contrast spec §3a:
    # the scrim is the WEAK sub-lever — text-mass does the work — but a much
    # lighter scrim stops the near-black-box thumbnail. standard = main/3rd.
    if scrim == "bright":
        base_dark = 0.28 if slug == "atomic" else 0.32
        edge_dark = 0.12 if slug == "atomic" else 0.14
    else:
        base_dark = 0.55 if slug == "atomic" else 0.62
        edge_dark = 0.20 if slug == "atomic" else 0.22
    # Per-image override: bright atomic paintings get pulled to 48laws-strength
    # so white hook text stays readable on the y=720-1200 band.
    # PER_IMAGE_* overrides only apply to known painting files. For Pexels
    # photos, bg_name is "pexels" which never matches — overrides are bypassed.
    override = PER_IMAGE_SCRIM.get(bg_name)
    if override:
        if scrim == "bright":
            base_dark, edge_dark = override[0], override[1]
        else:
            base_dark, edge_dark = override[2], override[3]
    mask_col = Image.new("L", (1, HEIGHT))
    mp = mask_col.load()
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        bell = abs(t - 0.5) * 2  # 1 at edges, 0 at center
        darken = base_dark + edge_dark * bell
        mp[0, y] = int(darken * 255)
    mask = mask_col.resize((WIDTH, HEIGHT))
    black = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    result = Image.composite(black, bg, mask)
    post = PER_IMAGE_POSTPROCESS.get(bg_name)
    if post:
        from PIL import ImageEnhance
        if "contrast" in post:
            result = ImageEnhance.Contrast(result).enhance(post["contrast"])
        if "color" in post:
            result = ImageEnhance.Color(result).enhance(post["color"])
    return result


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines, line = [], ""
    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    for w in words:
        candidate = (line + " " + w).strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def render_image(day: dict, out_path: Path) -> None:
    """Render the main quote frame — headline + compact body + footer.

    Body text was briefly stripped (let captions deliver it) but user feedback
    was the frame felt "blank" with only headline. Restored body in a more
    compact form (smaller font, tighter spacing) positioned in the upper-
    middle so the lower strip (~y=1450+) stays clear for the burned-in
    captions and the gold day label (y=HEIGHT-240).

    Visual hierarchy (top → bottom):
      1. HEADLINE (gold/white, big — the iconic law statement)
      2. Gold divider
      3. Body text (white, compact — explains the principle)
      4. (captions land below, in the lower-third strip)
      5. Day label (gold) + author/book (italic) — footer at the bottom
    """
    img = make_background(day["day"], day.get("book", ""))
    draw = ImageDraw.Draw(img)

    font_head = pick_font(["Cinzel.ttf", "Cinzel-Bold.ttf", "PlayfairDisplay.ttf"], 72, weight=900)
    font_body = pick_font(["PlayfairDisplay.ttf", "PlayfairDisplay-Regular.ttf"], 42, weight=500)
    font_day = pick_font(["Cinzel.ttf"], 36, weight=600)
    font_foot = pick_font(["PlayfairDisplay-Italic.ttf"], 38, weight=500)

    margin = 90
    max_w = WIDTH - 2 * margin

    head_lines = wrap_text(day["headline"].upper(), font_head, max_w)
    body_lines = wrap_text(day["body"], font_body, max_w)

    def line_h(font: ImageFont.FreeTypeFont, line: str = "Mg") -> int:
        bbox = draw.textbbox((0, 0), line, font=font)
        return bbox[3] - bbox[1]

    # Pre-pass: total height of headline + divider + body
    h_head = sum(line_h(font_head, l) + 16 for l in head_lines) - 16
    gap_to_divider = 28
    h_divider = 3
    gap_to_body = 48
    h_body = sum(line_h(font_body, l) + 12 for l in body_lines) - 12
    total = h_head + gap_to_divider + h_divider + gap_to_body + h_body

    # Push the whole block into the UPPER region so the body text ends above
    # the caption strip (~y=1450). top_margin=200 starts it high; footer_zone
    # reserves the bottom 540px for captions + day label + footer.
    top_margin = 200
    footer_zone = 540
    available = HEIGHT - top_margin - footer_zone
    y = top_margin + max(0, (available - total) // 2)

    for line in head_lines:
        bbox = draw.textbbox((0, 0), line, font=font_head)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, y), line, fill=WHITE, font=font_head)
        y += line_h(font_head, line) + 16

    y += gap_to_divider - 16
    draw.line([(WIDTH / 2 - 80, y), (WIDTH / 2 + 80, y)], fill=GOLD, width=h_divider)
    y += gap_to_body

    for line in body_lines:
        bbox = draw.textbbox((0, 0), line, font=font_body)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, y), line, fill=WHITE, font=font_body)
        y += line_h(font_body, line) + 12

    # 2026-06-04 SMM fix: dropped "DAY 2 OF 49" tail — misleading now that
    # the queue is curated (20 of 48 Laws, 8 of 30 Habits, 5 of 13 Rules).
    # Also dropped the headline tail (was duplicating the body heading above).
    # Just the title now — clean chapter marker, gold accent, no redundancy.
    day_label = day['title'].upper()
    bbox = draw.textbbox((0, 0), day_label, font=font_day)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, HEIGHT - 240), day_label, fill=GOLD, font=font_day)

    foot = f"— {day['author']}, {day['book']}"
    bbox = draw.textbbox((0, 0), foot, font=font_foot)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, HEIGHT - 180), foot, fill=DIM, font=font_foot)

    img.save(out_path, "PNG", optimize=True)


def _book_kicker(day: dict) -> str:
    """Small gold credibility kicker — the book is the product, never stripped."""
    return str(day.get("book", "")).upper()


def _draw_hook(day: dict, img: "Image.Image", draw: "ImageDraw.ImageDraw") -> None:
    """Shared hook composition for the intro frame AND the loop-matched end
    frame: book kicker → gold rule → big bold payoff-first tease, on a local
    legibility panel (so the bright scrim doesn't kill white-text contrast).

    CHANGE 2: text-mass is the workhorse (committed contrast spec §3-reweighted).
    Reused by render_end_frame so the last frame is visually identical to the
    first — a clean Shorts loop with no fade-to-CTA.
    """
    from pilmoji import Pilmoji

    from twemoji_local import LocalTwemoji, strip_emoji

    tease = strip_emoji(day["tease"])   # clean editorial type, no Twemoji (AI tell)
    margin = 80
    max_w = WIDTH - 2 * margin

    font_kick = pick_font(["Cinzel.ttf"], 34, weight=700)
    # Workhorse: big + heavy. Step down only as line count grows.
    for size in (98, 84, 72, 62):
        font_tease = pick_font(["PlayfairDisplay.ttf"], size, weight=800)
        lines = wrap_text(tease, font_tease, max_w)
        if len(lines) <= 3 or size == 62:
            break

    def line_h(font, s: str = "Mg") -> int:
        b = draw.textbbox((0, 0), s, font=font)
        return b[3] - b[1]

    gap = 20
    h_tease = sum(line_h(font_tease, l) + gap for l in lines) - gap
    h_kick = line_h(font_kick)
    rule_gap = 36
    block_h = h_kick + rule_gap + 6 + rule_gap + h_tease
    block_top = (HEIGHT - block_h) // 2

    # Local legibility panel behind the whole hook block (semi-opaque black,
    # rounded) — bright scrim everywhere else, protected text here.
    pad = 56
    panel = Image.new("RGBA", img.size, (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(panel)
    pdraw.rounded_rectangle(
        [margin - pad, block_top - pad, WIDTH - margin + pad, block_top + block_h + pad],
        radius=44, fill=(0, 0, 0, 150),
    )
    img.paste(Image.alpha_composite(img.convert("RGBA"), panel).convert("RGB"), (0, 0))
    draw = ImageDraw.Draw(img)

    def centered(text: str, y: int, font, fill, drawer) -> None:
        b = draw.textbbox((0, 0), text, font=font)
        drawer((WIDTH - (b[2] - b[0])) // 2, y, text, font, fill)

    kick = _book_kicker(day)

    def paint(drawer) -> None:
        y = block_top
        centered(kick, y, font_kick, GOLD, drawer)
        y += h_kick + rule_gap
        draw.line([(WIDTH / 2 - 90, y), (WIDTH / 2 + 90, y)], fill=GOLD, width=6)
        y += 6 + rule_gap
        for ln in lines:
            centered(ln, y, font_tease, WHITE, drawer)
            y += line_h(font_tease, ln) + gap

    try:
        with Pilmoji(img, source=LocalTwemoji) as pm:
            paint(lambda x, y, t, f, c: pm.text((x, y), t, fill=c, font=f))
    except Exception as e:  # noqa: BLE001 — never crash the post for an emoji
        print(f"!! PILMOJI_FALLBACK_FIRED day={day.get('day')} err={e!r}")
        gh_out = os.environ.get("GITHUB_OUTPUT")
        if gh_out:
            with open(gh_out, "a", encoding="utf-8") as f:
                f.write("pilmoji_fallback=true\n")
        kick = strip_emoji(kick)
        lines = [strip_emoji(l) for l in lines]
        paint(lambda x, y, t, f, c: draw.text((x, y), t, fill=c, font=f))


def render_intro_frame(day: dict, out_path: Path) -> None:
    """Frame 1 (CHANGE 2): the payoff-first contrast hook. Must read in <1s.
    Bright scrim + big bold tease on a legibility panel. No bottom series
    label — that lives on the loop-matched end frame only."""
    if not day.get("tease"):
        raise ValueError(f"Item {day.get('day')} missing required 'tease'")
    img = make_background(day["day"], day.get("book", ""), scrim="bright")
    draw = ImageDraw.Draw(img)
    _draw_hook(day, img, draw)
    img.save(out_path, "PNG", optimize=True)


def render_example_frame(day: dict, out_path: Path) -> None:
    """Frame 3: gold action header + compact question text + footer.

    Question text was briefly stripped (let captions deliver it) but user
    feedback was the frame felt "blank" with only the gold header. Restored
    in compact form: header band at top (YOUR MOVE / COMMENT BELOW), question
    in the upper-middle, captions own the lower strip, footer at the bottom.
    """
    from pilmoji import Pilmoji
    from twemoji_local import LocalTwemoji, strip_emoji

    img = make_background(day["day"], day.get("book", ""))
    draw = ImageDraw.Draw(img)

    margin = 90
    max_w = WIDTH - 2 * margin
    font_label = pick_font(["Cinzel.ttf"], 56, weight=800)
    font_cta = pick_font(["Cinzel.ttf"], 52, weight=800)
    font_q = pick_font(["PlayfairDisplay.ttf"], 60, weight=800)
    font_foot = pick_font(["PlayfairDisplay-Italic.ttf"], 36, weight=500)
    CTA_TEXT = "👇 COMMENT BELOW"
    CTA_INTRA_GAP = 20    # tight gap between YOUR MOVE and CTA (one band)
    HEADER_TO_Q_GAP = 70  # space between gold header band and the question

    q = strip_emoji(day.get("comment_q", ""))

    # Wrap the question; step the font down if it would take more than 3 lines
    # (keeps the centered block compact so it doesn't push into the caption
    # strip).
    for size in (60, 52, 46):
        font_q = pick_font(["PlayfairDisplay.ttf"], size, weight=800)
        q_lines = wrap_text(q, font_q, max_w)
        if len(q_lines) <= 3 or size == 46:
            break

    def line_h(font, s: str = "Mg") -> int:
        b = draw.textbbox((0, 0), s, font=font)
        return b[3] - b[1]

    h_label = line_h(font_label)
    h_cta = line_h(font_cta)
    h_q = sum(line_h(font_q, ln) + 14 for ln in q_lines) - 14
    total = h_label + CTA_INTRA_GAP + h_cta + HEADER_TO_Q_GAP + h_q

    # Pin to UPPER region so the question ends above the caption strip
    # (~y=1450). top_margin starts the gold header band high; footer_zone
    # reserves the bottom 540px for captions + footer.
    top_margin = 220
    footer_zone = 540
    available = HEIGHT - top_margin - footer_zone
    y0 = top_margin + max(0, (available - total) // 2)

    def centered(text, y, font, fill, drawer):
        b = draw.textbbox((0, 0), text, font=font)
        drawer((WIDTH - (b[2] - b[0])) // 2, y, text, font, fill)

    def paint(drawer):
        y = y0
        centered("YOUR MOVE", y, font_label, GOLD, drawer)
        y += h_label + CTA_INTRA_GAP
        centered(CTA_TEXT, y, font_cta, GOLD, drawer)
        y += h_cta + HEADER_TO_Q_GAP
        for ln in q_lines:
            centered(ln, y, font_q, WHITE, drawer)
            y += line_h(font_q, ln) + 14

    try:
        with Pilmoji(img, source=LocalTwemoji) as pm:
            paint(lambda x, y, t, f, c: pm.text((x, y), t, fill=c, font=f))
    except Exception as e:  # noqa: BLE001
        print(f"!! PILMOJI_FALLBACK_FIRED day={day.get('day')} err={e!r}")
        gh_out = os.environ.get("GITHUB_OUTPUT")
        if gh_out:
            with open(gh_out, "a", encoding="utf-8") as f:
                f.write("pilmoji_fallback=true\n")
        y = y0
        centered("YOUR MOVE", y, font_label, GOLD,
                 lambda x, yy, t, ff, c: draw.text((x, yy), t, fill=c, font=ff))
        y += h_label + CTA_INTRA_GAP
        centered(strip_emoji(CTA_TEXT), y, font_cta, GOLD,
                 lambda x, yy, t, ff, c: draw.text((x, yy), t, fill=c, font=ff))
        y += h_cta + HEADER_TO_Q_GAP
        for ln in q_lines:
            centered(strip_emoji(ln), y, font_q, WHITE,
                     lambda x, yy, t, ff, c: draw.text((x, yy), t, fill=c, font=ff))
            y += line_h(font_q, ln) + 14

    foot = f"— {day.get('author', '')}, {day.get('book', '')}"
    b = draw.textbbox((0, 0), foot, font=font_foot)
    draw.text(((WIDTH - (b[2] - b[0])) / 2, HEIGHT - 170), foot, fill=DIM, font=font_foot)
    img.save(out_path, "PNG", optimize=True)


def render_end_frame(day: dict, out_path: Path) -> None:
    """CHANGE 3: the loop-matched closer. NO CTA card, NO tomorrow teaser.

    It re-renders the exact intro hook composition on the same bright scrim, so
    the final frame is visually identical to frame 1 — a seamless Shorts loop
    that rewards rewatch. The only addition is a SMALL persistent bottom
    overlay (book-aware stable-parent series label + bio funnel)."""
    img = make_background(day["day"], day.get("book", ""), scrim="bright")
    draw = ImageDraw.Draw(img)
    _draw_hook(day, img, draw)               # identical to frame 1 -> clean loop
    draw = ImageDraw.Draw(img)               # _draw_hook re-pastes the image

    font_sub = pick_font(["Cinzel.ttf"], 34, weight=700)
    font_books = pick_font(["Cinzel.ttf"], 30, weight=600)

    # 2026-06-04 SMM fix (round 2): the queue is curated — not all 48 Laws,
    # not all 30 habits, not all 13 rules. The old "LAW 1/48" framing implied
    # "watch all 48" which is misleading. New framing: "BEST OF {book}" —
    # communicates explicit curation, sets up "you're getting the curated
    # best, not the firehose" perception. Also removes the algorithm-
    # penalized "SUBSCRIBE FOR THE REST" tail that was burned into every
    # video before.
    book_lower = day.get("book", "").lower()
    if "48 laws" in book_lower:
        line1 = "BEST OF 48 LAWS OF POWER"
    elif "atomic" in book_lower:
        line1 = "BEST OF ATOMIC HABITS"
    elif "12 rules" in book_lower or "jordan peterson" in book_lower:
        line1 = "BEST OF 12 RULES FOR LIFE"
    else:
        line1 = "THE UNWRITTEN RULES"
    line2 = "LINK IN BIO"

    b = draw.textbbox((0, 0), line1, font=font_sub)
    draw.text(((WIDTH - (b[2] - b[0])) / 2, HEIGHT - 200), line1, fill=GOLD, font=font_sub)
    b = draw.textbbox((0, 0), line2, font=font_books)
    draw.text(((WIDTH - (b[2] - b[0])) / 2, HEIGHT - 150), line2, fill=WHITE, font=font_books)

    img.save(out_path, "PNG", optimize=True)


def _load_music_metadata() -> dict:
    """Load mood tags for music tracks from music_metadata.json (if present)."""
    p = ROOT / "music_metadata.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def pick_music(book: str = "", mood: str = "") -> Path | None:
    """Pick a track from the book's subfolder, preferring mood-matched tracks.

    Selection order:
      1. Tracks in book/ folder matching the requested mood
      2. Any track in book/ folder
      3. Any track in top-level music/ folder
    """
    slug = book_slug(book) if book else "48laws"
    book_dir = MUSIC_DIR / slug
    all_tracks = list(book_dir.glob("*.mp3")) + list(book_dir.glob("*.m4a")) + list(book_dir.glob("*.wav"))

    if mood:
        metadata = _load_music_metadata().get(slug, {})
        mood_tracks = [t for t in all_tracks if metadata.get(t.name) == mood]
        if mood_tracks:
            return random.choice(mood_tracks)

    if not all_tracks:
        all_tracks = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.m4a")) + list(MUSIC_DIR.glob("*.wav"))
    return random.choice(all_tracks) if all_tracks else None


def make_video(intro_path: Path, main_path: Path, example_path: Path, end_path: Path,
               music_path: Path | None, out_path: Path,
               voice_path: Path | None = None,
               caption_srt: Path | None = None,
               frame_durs: tuple[float, float, float, float] | None = None) -> None:
    """Build the Reel as four crossfaded frames. Durations are driven ENTIRELY
    by the constants at the top of this file (currently 2/4/4/2 = 12s); do not
    hardcode timings here — that comment rot is what bit us on the 24->12 revert.

       intro    INTRO_FRAME_SEC      tease (curiosity hook, no law reveal)
       main     MAIN_FRAME_SEC       law/principle reveal (Ken Burns zoom)
       example  EXAMPLE_FRAME_SEC    real-life application (subtle zoom)
       end      END_FRAME_SEC        CTA + tomorrow teaser

    Each transition is a 0.5-sec crossfade; total = DURATION_SEC.

    Audio: music ducks to 0.25 volume so the voice sits on top clearly. If
    voice_path is None (TTS failed or disabled), music plays at full volume —
    the post still ships, just without narration (degrades gracefully).
    """
    # Per-build frame durations: caller (build()) sizes them from the actual
    # voice narration length so video duration = voice + 0.5s tail — no dead
    # air at the end, no mid-word cut. Falls back to module constants for
    # call paths that don't synthesize voice (legacy / fallback / dry runs).
    if frame_durs is None:
        intro_s, main_s, example_s, end_s = (
            INTRO_FRAME_SEC, MAIN_FRAME_SEC, EXAMPLE_FRAME_SEC, END_FRAME_SEC)
    else:
        intro_s, main_s, example_s, end_s = frame_durs
    total_sec = intro_s + main_s + example_s + end_s

    # Offsets are formulas of the per-build durations — no global-constant
    # rot, and they auto-track whatever sizing build() chose.
    t_intro_to_main = intro_s - 0.5
    t_main_to_example = intro_s + main_s - 0.5
    t_example_to_end = intro_s + main_s + example_s - 0.5

    main_out_frames = int((main_s + 0.5) * 30)
    example_out_frames = int((example_s + 0.5) * 30)

    # Decide the final video-output label so we can optionally chain a
    # captions burn-in on top: [outv_pre] -> subtitles -> [outv].
    vlabel = "outv" if caption_srt is None else "outv_pre"
    vfilter = (
        # Intro — static
        f"[0:v]setpts=PTS-STARTPTS[v0];"
        # Main — slow zoom
        f"[1:v]scale={WIDTH * 2}:{HEIGHT * 2},"
        f"zoompan=z='1+0.0004*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={main_out_frames}:fps=30:s={WIDTH}x{HEIGHT}[v1];"
        # Example — slow zoom (continues motion)
        f"[2:v]scale={WIDTH * 2}:{HEIGHT * 2},"
        f"zoompan=z='1+0.0003*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={example_out_frames}:fps=30:s={WIDTH}x{HEIGHT}[v2];"
        # End — static
        f"[3:v]setpts=PTS-STARTPTS[v3];"
        # Stitch all four with 0.5-sec crossfades
        f"[v0][v1]xfade=transition=fade:duration=0.5:offset={t_intro_to_main}[ab];"
        f"[ab][v2]xfade=transition=fade:duration=0.5:offset={t_main_to_example}[abc];"
        f"[abc][v3]xfade=transition=fade:duration=0.5:offset={t_example_to_end}[{vlabel}]"
    )
    # Burn captions into the stitched video (sound-off accessibility — most
    # short-form viewers watch muted, so on-screen text is required, not nice-
    # to-have). Bottom-third placement; large white Arial Bold with thick
    # black outline so it reads on any background painting. Run from cwd =
    # output dir so the SRT path stays a bare filename, avoiding libass's
    # well-known Windows colon-escaping pain on absolute paths.
    if caption_srt is not None:
        # User feedback after first live post: the prior Arial + thick Outline=4
        # combo read as "90s YouTube default" — utilitarian, unbranded.
        # Modern Shorts captions = bold sans with thinner outline + subtle
        # shadow for depth. Bumped FontSize 16->20 (more readable on phone),
        # Outline 4->2 (thinner, less chunky), added Shadow=1 (clean depth),
        # PrimaryColour explicit alpha (FF=opaque). libass on Ubuntu runners
        # falls back Arial -> Liberation Sans which is cleaner than DejaVu.
        style = (
            "FontName=Arial,FontSize=16,PrimaryColour=&H00FFFFFF&,"
            "OutlineColour=&H00000000&,BorderStyle=1,Outline=2,Shadow=1,"
            "Bold=1,Alignment=2,MarginV=75"
        )
        vfilter += (
            f";[outv_pre]subtitles=filename={caption_srt.name}:"
            f"force_style='{style}'[outv]"
        )

    cmd = [
        "ffmpeg", "-y",
        "-framerate", "30", "-loop", "1", "-t", str(intro_s + 0.5), "-i", str(intro_path),
        "-framerate", "1",  "-loop", "1", "-t", "1",                "-i", str(main_path),
        "-framerate", "1",  "-loop", "1", "-t", "1",                "-i", str(example_path),
        "-framerate", "30", "-loop", "1", "-t", str(end_s + 0.5),   "-i", str(end_path),
    ]
    # Build audio inputs + filter chain dynamically based on what we have.
    # Music goes in input slot 4 (after the 4 video frames); voice (if any)
    # goes in slot 5. Each branch handles all four music/voice combinations.
    audio_filter = ""
    audio_args: list[str] = []
    if music_path and voice_path:
        cmd += ["-i", str(music_path), "-i", str(voice_path)]
        # Music ducked to 0.25 so the narrator sits clearly on top. Voice
        # at 1.0 with a 0.5s fade-out at the tail as a safety net if the
        # synthesis runs slightly long (better than mid-word ffmpeg -t cut).
        audio_filter = (
            f"[4:a]loudnorm=I=-14:TP=-1.5:LRA=11,volume=0.25,"
            f"afade=t=in:d=1,afade=t=out:st={total_sec - 1}:d=1[music];"
            f"[5:a]volume=1.0,afade=t=out:st={total_sec - 0.5}:d=0.5[voice];"
            f"[music][voice]amix=inputs=2:duration=first:normalize=0[outa]"
        )
        audio_args = ["-map", "[outv]", "-map", "[outa]",
                      "-c:a", "aac", "-b:a", "192k"]
    elif voice_path:
        cmd += ["-i", str(voice_path)]
        audio_filter = (
            f"[4:a]volume=1.0,afade=t=out:st={total_sec - 0.5}:d=0.5[outa]"
        )
        audio_args = ["-map", "[outv]", "-map", "[outa]",
                      "-c:a", "aac", "-b:a", "192k"]
    elif music_path:
        cmd += ["-i", str(music_path)]
        audio_filter = (
            f"[4:a]loudnorm=I=-14:TP=-1.5:LRA=11,"
            f"afade=t=in:d=1,afade=t=out:st={total_sec - 1}:d=1[outa]"
        )
        audio_args = ["-map", "[outv]", "-map", "[outa]",
                      "-c:a", "aac", "-b:a", "192k"]
    else:
        audio_args = ["-map", "[outv]"]

    filter_complex = vfilter + (";" + audio_filter if audio_filter else "")
    cmd += [
        "-filter_complex", filter_complex,
        *audio_args,
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-t", str(total_sec),
        "-r", "30",
        str(out_path),
    ]
    # When burning captions, cwd MUST be the output dir so the bare SRT
    # filename in the subtitles filter resolves correctly (libass + Windows
    # absolute paths is a known headache; relative-from-cwd is the safe path).
    cwd = str(out_path.parent) if caption_srt is not None else None
    subprocess.run(cmd, check=True, cwd=cwd)


# Energetic amplifier line — rotated per item so 276 posts don't read as one
# templated stamp (the content-farm signal that throttles reach).
_AMPLIFIERS = [
    "Most people learn this the hard way.",
    "The quiet ones at work already know this.",
    "This is why some get promoted and you don't.",
    "Nobody teaches you this at work.",
    "Notice who in your office already does this.",
    "Read it twice. Then watch your office differently.",
    "They won't say this in the all-hands.",
    # 2026-06-04 SMM swap: previous line ("This one took me three jobs to
    # figure out") faked a personal narrative on an anonymous account —
    # audience smells the inauthenticity. Replaced with a tactical observe-
    # the-world prompt that works for an anonymous brand voice.
    "Watch the next promotion at your org. You'll see this play out.",
]
# 2026-06-04 SMM rewrite: previous CTAs used explicit "Follow" 4/5 times.
# IG/YT 2026 algorithms pattern-detect "Follow for X" as bait and downrank.
# New CTAs drive saves/shares/tags (the actual ranking signals) — no
# "follow" anywhere. Brand positioning is implicit via the content style.
_CTAS = [
    "Save this. You'll need it next time HR calls you in.",
    "Send this to the colleague who needs to read it.",
    "Save it. Re-read it before your next 1:1.",
    "Tag the friend whose boss just promoted the wrong person.",
    "Save this. The next reorg won't wait.",
]
# Backward-compat alias so older imports don't break.
_FOLLOW_CTAS = _CTAS
_FUNNEL = "The 3 books this comes from: linktr.ee/unwrittenrules"
# Tight core (always) + a rotating pack so no two posts share the same tag set.
_HASHTAG_CORE = ["#officepolitics", "#managingup", "#48lawsofpower",
                 "#climbingtheladder", "#powerdynamics"]
_HASHTAG_POOL = [
    "#gettingpromoted", "#newmanager", "#workplacedrama", "#officepoliticstips",
    "#promotiontips", "#bosstips", "#corporatesurvival", "#robertgreene",
    "#workplacepolitics", "#careerstrategy", "#workplacetips", "#corporateladder",
    "#careerhacks", "#workadvice",
]
_AFF_PLACEHOLDER = "{SET_AMAZON_AFFILIATE_TAG}"


def _affiliate_tag() -> str:
    return os.environ.get("AMAZON_AFFILIATE_TAG", "").strip() or _AFF_PLACEHOLDER


def _amazon_link(book: str, tag: str) -> str:
    from urllib.parse import quote_plus
    return f"https://www.amazon.in/s?k={quote_plus(book + ' book')}&tag={tag}"


def _series_tag(series_label: str) -> str:
    """'LAW 7/48 · SUBSCRIBE FOR THE REST' -> 'Law 7/48' for the caption."""
    head = series_label.split("·")[0].strip()
    return head.title() if head else "the series"


def write_bio_guide() -> Path:
    """The single affiliate DESTINATION (put behind one bio link / Linktree).
    'Which of these 3 should you read first' captures intent without a hard
    sell and 3x's the qualifying-sale surface for Amazon's 3/180-day gate."""
    tag = _affiliate_tag()
    books = [
        ("The 48 Laws of Power", "you're being out-maneuvered and don't know the rules"),
        ("Atomic Habits", "you know what to do but can't stay consistent"),
        ("12 Rules for Life", "the chaos is getting to you and you need an anchor"),
    ]
    lines = [
        "# Start here: which book should you read first?",
        "",
        "Three books, one question — where are you actually stuck right now?",
        "",
    ]
    for b, who in books:
        lines += [f"## {b}", f"Read this first if **{who}**.", f"→ {_amazon_link(b, tag)}", ""]
    lines += ["_As an Amazon Associate, qualifying purchases support the channel._", ""]
    p = OUT_DIR / "_bio_guide.md"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


_ORDER_CACHE: list[int] | None = None


def ordered_item(pos: int) -> int:
    """Map 1-based posting position -> item number, using the SAME deterministic
    interleave as scripts/build_queue.py (a law's TACTIC/MISTAKE/SCENARIO never
    post back-to-back; books stay mixed). The automatic poster uses this so a
    hands-off feed has the same variety as the planned queue."""
    global _ORDER_CACHE
    if _ORDER_CACHE is None:
        data = json.loads(QUOTES.read_text(encoding="utf-8"))
        items = data["items"]
        by_key = {(it["parent_law"], it["variant_type"]): it["item"] for it in items}
        by_book: dict[str, list[str]] = {}
        for it in items:
            by_book.setdefault(it["book"], [])
            if it["parent_law"] not in by_book[it["book"]]:
                by_book[it["book"]].append(it["parent_law"])
        spread = []
        for book, parents in by_book.items():
            n = len(parents)
            for i, p in enumerate(parents):
                spread.append(((i + 0.5) / n, -n, book, p))
        spread.sort()
        porder = [p for _, _, _, p in spread]
        variants = ("TACTIC", "MISTAKE", "SCENARIO")
        _ORDER_CACHE = [by_key[(porder[k % len(porder)], variants[k % 3])]
                        for k in range(len(items))]
    return _ORDER_CACHE[(pos - 1) % len(_ORDER_CACHE)]


def _parent_order() -> tuple[list[str], dict]:
    """92 parents, book-interleaved (shared with ordered_item's logic)."""
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    items = data["items"]
    by_key = {(it["parent_law"], it["variant_type"]): it["item"] for it in items}
    by_book: dict[str, list[str]] = {}
    for it in items:
        by_book.setdefault(it["book"], [])
        if it["parent_law"] not in by_book[it["book"]]:
            by_book[it["book"]].append(it["parent_law"])
    spread = []
    for book, parents in by_book.items():
        n = len(parents)
        for i, p in enumerate(parents):
            spread.append(((i + 0.5) / n, -n, book, p))
    spread.sort()
    return [p for _, _, _, p in spread], by_key


def _weave(a: list[int], b: list[int]) -> list[int]:
    """Deterministically interleave two lists by even position-fraction so the
    shorter one is spread through the longer (no clumping)."""
    tagged = [((i + 0.5) / len(a), x) for i, x in enumerate(a)] + \
             [((i + 0.5) / len(b), x) for i, x in enumerate(b)]
    tagged.sort(key=lambda t: t[0])
    return [x for _, x in tagged]


_SLOT_CACHE: dict[int, list[int]] | None = None


def scheduled_item(day: int, slot: int) -> int:
    """Fixed slot themes (NOT random): morning(slot 0)=technique-y, evening
    (slot 1)=book/story. Balanced over the full corpus, every item used once:

      AM = all 92 TACTIC + 46 MISTAKE   (the move + the trap)
      PM = all 92 SCENARIO + 46 MISTAKE (the story + the rest of the bait)

    SCENARIO is only 1/3 of items but PM is 1/2 the slots, so the 92 MISTAKEs
    are split 46/46 across AM/PM — that's the one unavoidable adjustment to
    keep both slots full for the whole run instead of PM drying up at day 92.
    """
    global _SLOT_CACHE
    if _SLOT_CACHE is None:
        porder, by_key = _parent_order()
        tac = [by_key[(p, "TACTIC")] for p in porder]
        mis = [by_key[(p, "MISTAKE")] for p in porder]
        scn = [by_key[(p, "SCENARIO")] for p in porder]
        half = len(mis) // 2
        _SLOT_CACHE = {
            0: _weave(tac, mis[:half]),          # AM: technique-y
            1: _weave(scn, mis[half:]),          # PM: book/story
        }
    seq = _SLOT_CACHE[1 if slot else 0]
    return seq[(day - 1) % len(seq)]


def corporate_caption(day: dict) -> str:
    """The repositioned caption — used by BOTH the paste-ready pack and the
    automatic poster, so a hands-off post carries the same hook + divisive
    question + bio funnel + corporate hashtags as a manual one."""
    from twemoji_local import strip_emoji
    i = int(day.get("item", 1))
    amp = _AMPLIFIERS[i % len(_AMPLIFIERS)]
    cta = _CTAS[(i // 2) % len(_CTAS)]
    # Rotating window over the pool so each post's tag set differs (kills the
    # identical-hashtags-every-post throttle) — core tags always present.
    start = (i * 3) % len(_HASHTAG_POOL)
    rot = [_HASHTAG_POOL[(start + k) % len(_HASHTAG_POOL)] for k in range(2)]
    tags = " ".join(_HASHTAG_CORE + rot)
    return "\n".join([
        strip_emoji(day["tease"]),     # clean, human — no decorative emoji
        amp,
        "",
        day["comment_q"],              # keeps the one functional 👇
        "",
        cta,
        _FUNNEL,
        "",
        tags,
    ])


def emit_post_pack(day: dict, video_path: Path, out_path: Path) -> None:
    """The paste-ready content-factory output (for manual posting). The
    automatic poster uses corporate_caption() directly."""
    tag = _affiliate_tag()
    cq = day["comment_q"]
    aff = _amazon_link(day.get("book", ""), tag)
    caption = corporate_caption(day)

    pack = "\n".join([
        f"# ITEM {day['day']:03d}  ·  {day.get('book','')}  ·  {day.get('parent_law','')}"
        f"  ·  {day.get('variant_type','')}",
        f"# video: {video_path.name}",
        "",
        "[CAPTION]",
        caption,
        "",
        "[PIN AS FIRST COMMENT]   (post this as the first comment, then pin it)",
        cq,
        "",
        "[TRENDING AUDIO]",
        "Pick a TRENDING sound in-app before posting. Do NOT post on the muted /"
        " licensed track — trending audio is the reach lever.",
        "",
        "[BIO LINK / AFFILIATE]   (destination lives behind ONE 'link in bio')",
        "Bio link -> output/_bio_guide.md  (host on Linktree / one-pager)",
        f"This item's book, tagged: {aff}",
        (f"NOTE: AMAZON_AFFILIATE_TAG is unset — {_AFF_PLACEHOLDER} is a visible"
         " placeholder, NOT a live link. Set it before posting."
         if tag == _AFF_PLACEHOLDER else f"Affiliate tag active: {tag}"),
        "",
    ])
    out_path.write_text(pack, encoding="utf-8")


def build(day_num: int) -> dict:
    """Render item `day_num` (1-based over the 276 variant items) + emit its
    paste-ready post pack. Content factory: builds, does NOT post."""
    day = load_day(day_num)
    n = f"{day_num:03d}"
    intro_image_path = OUT_DIR / f"item_{n}_intro.png"
    image_path = OUT_DIR / f"item_{n}.png"
    example_image_path = OUT_DIR / f"item_{n}_q.png"
    end_image_path = OUT_DIR / f"item_{n}_end.png"
    video_path = OUT_DIR / f"item_{n}.mp4"
    post_path = OUT_DIR / f"item_{n}_post.txt"
    render_intro_frame(day, intro_image_path)
    render_image(day, image_path)
    render_example_frame(day, example_image_path)
    render_end_frame(day, end_image_path)
    music = pick_music(day.get("book", ""), day.get("mood", ""))
    # AI voice narration + synced captions (parasocial identity layer + sound-
    # off accessibility — ~85% of mobile viewers mute by default, so on-screen
    # captions are required not optional). Idempotent + fails open on both: if
    # TTS errors, voice=None AND caption_srt=None, and the video still ships
    # music-only with no captions rather than crashing the post.
    voice_path = OUT_DIR / f"item_{n}_voice.mp3"
    srt_path = OUT_DIR / f"item_{n}.srt"
    voice = None
    caption_srt = None
    try:
        from tts import synthesize_pitched, _mp3_duration
        voice = synthesize_pitched(day, voice_path, srt_path=srt_path)
        if voice is not None and srt_path.exists() and srt_path.stat().st_size > 16:
            caption_srt = srt_path
    except Exception as e:
        print(f"!! TTS_IMPORT_FAILED day={day_num} err={type(e).__name__}: {e}")

    # Dynamic per-item video duration — sized to the actual narration length
    # so EVERY video is fully completed (voice never cut, no dead-air tail).
    # Andrew voice at -15% rate runs ~0.5s/word; item word counts vary 28-52,
    # so narration lengths span ~14-26s. Scale frames proportionally from the
    # base 3:7:7:5 ratio. Falls back to constants if voice missing.
    frame_durs = None
    if voice is not None and voice_path.exists():
        try:
            voice_dur = _mp3_duration(voice_path)
            target = max(voice_dur + 0.5, 16.0)  # never below 16s
            target = min(target, 60.0)            # platform hard cap (Shorts)
            BASE = 22.0
            frame_durs = (
                target * INTRO_FRAME_SEC / BASE,
                target * MAIN_FRAME_SEC / BASE,
                target * EXAMPLE_FRAME_SEC / BASE,
                target * END_FRAME_SEC / BASE,
            )
        except Exception as e:
            print(f"!! VOICE_DUR_MEASURE_FAILED day={day_num} err={type(e).__name__}: {e}")
    make_video(intro_image_path, image_path, example_image_path, end_image_path,
               music, video_path, voice_path=voice, caption_srt=caption_srt,
               frame_durs=frame_durs)
    write_bio_guide()
    emit_post_pack(day, video_path, post_path)
    return {
        "day": day,
        "intro_image": intro_image_path,
        "image": image_path,
        "example_image": example_image_path,
        "end_image": end_image_path,
        "video": video_path,
        "post_pack": post_path,
        "music": music,
    }


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    result = build(n)
    print(f"Built item {n}: {result['video']}  +  {result['post_pack'].name}")
