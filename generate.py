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
DURATION_SEC = 12
INTRO_FRAME_SEC = 2        # 0-2:    tease (curiosity hook — no law reveal)
MAIN_FRAME_SEC = 4         # 2-6:    the law/principle reveal
EXAMPLE_FRAME_SEC = 4      # 6-10:   real-life example (acceptance for life)
END_FRAME_SEC = 2          # 10-12:  CTA + tomorrow teaser

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


def make_background(day_num: int, book: str = "", scrim: str = "standard") -> Image.Image:
    """Pick a (deterministic-per-day) background painting from the book's subfolder.

    Falls back to top-level backgrounds/ then gradient if subfolder is empty."""
    slug = book_slug(book) if book else "48laws"
    book_dir = BG_DIR / slug
    backgrounds = sorted(book_dir.glob("*.jpg")) + sorted(book_dir.glob("*.png"))
    if not backgrounds:
        backgrounds = sorted(BG_DIR.glob("*.jpg")) + sorted(BG_DIR.glob("*.png"))
    if not backgrounds:
        img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
        draw_gradient(img)
        return img

    # Deterministic per day so re-renders look identical.
    # MULTIPLIER must be coprime with every pool size we'll ever ship,
    # otherwise (day*K) % len collapses to a single index and the same
    # painting plays every day. Old K=7 broke against rules-pool size 7
    # (every day_num resolved to index 3 -> only dore_inferno shown for
    # 49 days). 11 was unsafe once 48laws grew to 11 entries —
    # gcd(11,11)=11 collapses the formula to a constant. 23 is prime
    # and coprime with every pool size 1-22, leaving headroom for any
    # realistic future growth. Book offset adds variety across books so
    # AM/PM on the same day don't drift toward the same relative index.
    K = 23
    book_offset = sum(ord(c) for c in slug) % len(backgrounds)
    bg_path = backgrounds[(day_num * K + 3 + book_offset) % len(backgrounds)]
    try:
        bg = Image.open(bg_path).convert("RGB")
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
    override = PER_IMAGE_SCRIM.get(bg_path.name)
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
    post = PER_IMAGE_POSTPROCESS.get(bg_path.name)
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
    """Render the main quote frame.

    Visual hierarchy (top → bottom):
      1. HEADLINE (biggest, top portion) — grabs first-second attention
      2. Divider
      3. Body text — explains the principle
      4. Day label (small gold) + author/book attribution (italic dim) — footer
    """
    img = make_background(day["day"], day.get("book", ""))
    draw = ImageDraw.Draw(img)

    font_head = pick_font(["Cinzel.ttf", "Cinzel-Bold.ttf", "PlayfairDisplay.ttf"], 78, weight=900)
    font_body = pick_font(["PlayfairDisplay.ttf", "PlayfairDisplay-Regular.ttf"], 50, weight=500)
    font_day = pick_font(["Cinzel.ttf"], 36, weight=600)
    font_foot = pick_font(["PlayfairDisplay-Italic.ttf"], 38, weight=500)

    margin = 90
    max_w = WIDTH - 2 * margin

    head_lines = wrap_text(day["headline"].upper(), font_head, max_w)
    body_lines = wrap_text(day["body"], font_body, max_w)

    def line_h(font: ImageFont.FreeTypeFont, line: str = "Mg") -> int:
        bbox = draw.textbbox((0, 0), line, font=font)
        return bbox[3] - bbox[1]

    # ── Pre-pass: measure total height of headline + divider + body
    h_head = sum(line_h(font_head, l) + 18 for l in head_lines) - 18
    gap_head_to_divider = 30
    h_divider = 3
    gap_divider_to_body = 60
    h_body = sum(line_h(font_body, l) + 14 for l in body_lines) - 14
    total = h_head + gap_head_to_divider + h_divider + gap_divider_to_body + h_body

    # Reserve top + bottom margins (bottom margin includes day label + footer zone)
    top_margin = 200
    footer_zone = 320
    available = HEIGHT - top_margin - footer_zone
    y = top_margin + max(0, (available - total) // 2)

    # ── Draw pass — headline first ─────────────────────────────────────────────
    for line in head_lines:
        bbox = draw.textbbox((0, 0), line, font=font_head)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, y), line, fill=WHITE, font=font_head)
        y += line_h(font_head, line) + 18

    y += gap_head_to_divider - 18
    draw.line([(WIDTH / 2 - 80, y), (WIDTH / 2 + 80, y)], fill=GOLD, width=h_divider)
    y += gap_divider_to_body

    for line in body_lines:
        bbox = draw.textbbox((0, 0), line, font=font_body)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, y), line, fill=WHITE, font=font_body)
        y += line_h(font_body, line) + 14

    # ── Footer block (day label in gold + author/book in italic) ──────────────
    day_label = f"{day['title'].upper()}  ·  DAY {day['book_day']} OF {day['book_total']}"
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
    """Frame 3: the divisive comment_q ('example' is gone in the variant model).
    A 'YOUR MOVE' provocation that demands a reply — same question pinned as
    first comment by the post pack. This is the engagement engine."""
    from pilmoji import Pilmoji

    from twemoji_local import LocalTwemoji, strip_emoji

    img = make_background(day["day"], day.get("book", ""))
    draw = ImageDraw.Draw(img)

    margin = 90
    max_w = WIDTH - 2 * margin
    font_label = pick_font(["Cinzel.ttf"], 56, weight=800)
    font_q = pick_font(["PlayfairDisplay.ttf"], 72, weight=800)
    font_foot = pick_font(["PlayfairDisplay-Italic.ttf"], 36, weight=500)

    q = strip_emoji(day.get("comment_q", ""))   # clean frame; the 👇 stays in the caption only

    # Semantic split: comment_q is typed as "setup — choice?" OR "setup: choice?"
    # — render those as TWO blocks (setup, bigger vertical gap, choice) instead
    # of one word-wrapped paragraph. Visual feedback was that the wrap broke
    # "confront or log it?" across lines mid-phrase. Applies UNIFORMLY to every
    # comment_q in the catalog that uses either separator; falls through to
    # single-block rendering when neither is present.
    def _split_q(text: str) -> list[str]:
        for sep in (" — ", ": "):
            if sep in text:
                a, b = text.split(sep, 1)
                b = b.strip()
                # Colon split: only honor it if the second part is actually a
                # question (avoids splitting on labels like "Day 1: ..." that
                # may slip in). Em-dash always splits — it's almost always
                # semantic in this catalog.
                if sep == ": " and "?" not in b:
                    continue
                if b and b[0].islower():
                    b = b[0].upper() + b[1:]
                return [a.strip(), b]
        return [text]

    q_blocks = _split_q(q)

    # Step font down until ALL blocks combined fit a reasonable line count.
    for size in (72, 64, 56):
        font_q = pick_font(["PlayfairDisplay.ttf"], size, weight=800)
        wrapped_blocks = [wrap_text(b, font_q, max_w) for b in q_blocks]
        if sum(len(lines) for lines in wrapped_blocks) <= 4 or size == 56:
            break

    def line_h(font, s: str = "Mg") -> int:
        b = draw.textbbox((0, 0), s, font=font)
        return b[3] - b[1]

    # Flat (line, gap_after_px) sequence: small gap inside a block, bigger
    # gap between blocks so setup vs choice reads as TWO visual chunks.
    INTRA_GAP, BLOCK_GAP = 18, 56
    rendered: list[tuple[str, int]] = []
    for bi, lines in enumerate(wrapped_blocks):
        for li, ln in enumerate(lines):
            last_of_block = (li == len(lines) - 1)
            has_next_block = bi < len(wrapped_blocks) - 1
            rendered.append((ln, BLOCK_GAP if (last_of_block and has_next_block) else INTRA_GAP))

    h_label = line_h(font_label)
    gap = 70
    h_q = sum(line_h(font_q, ln) for ln, _ in rendered) + sum(g for _, g in rendered[:-1])
    total = h_label + gap + h_q
    top_margin, footer_zone = 260, 300
    y0 = top_margin + max(0, ((HEIGHT - top_margin - footer_zone) - total) // 2)

    def centered(text, y, font, fill, drawer):
        b = draw.textbbox((0, 0), text, font=font)
        drawer((WIDTH - (b[2] - b[0])) // 2, y, text, font, fill)

    def paint(drawer):
        y = y0
        centered("YOUR MOVE", y, font_label, GOLD, drawer)
        y += h_label + gap
        for ln, gap_after in rendered:
            centered(ln, y, font_q, WHITE, drawer)
            y += line_h(font_q, ln) + gap_after

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
        y += h_label + gap
        for ln, gap_after in rendered:
            centered(strip_emoji(ln), y, font_q, WHITE,
                     lambda x, yy, t, ff, c: draw.text((x, yy), t, fill=c, font=ff))
            y += line_h(font_q, ln) + gap_after

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

    line1 = day.get("series_label", "SUBSCRIBE FOR THE REST")  # book-aware, stable parent
    line2 = "BOOKS  ·  LINK IN BIO"

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
               music_path: Path | None, out_path: Path) -> None:
    """Build the Reel as four crossfaded frames. Durations are driven ENTIRELY
    by the constants at the top of this file (currently 2/4/4/2 = 12s); do not
    hardcode timings here — that comment rot is what bit us on the 24->12 revert.

       intro    INTRO_FRAME_SEC      tease (curiosity hook, no law reveal)
       main     MAIN_FRAME_SEC       law/principle reveal (Ken Burns zoom)
       example  EXAMPLE_FRAME_SEC    real-life application (subtle zoom)
       end      END_FRAME_SEC        CTA + tomorrow teaser

    Each transition is a 0.5-sec crossfade; total = DURATION_SEC.
    """
    # Offsets are formulas, not numbers, so they cannot rot on the next retiming.
    t_intro_to_main = INTRO_FRAME_SEC - 0.5                                       # = INTRO-0.5
    t_main_to_example = INTRO_FRAME_SEC + MAIN_FRAME_SEC - 0.5                     # = INTRO+MAIN-0.5
    t_example_to_end = INTRO_FRAME_SEC + MAIN_FRAME_SEC + EXAMPLE_FRAME_SEC - 0.5  # = INTRO+MAIN+EXAMPLE-0.5

    main_out_frames = int((MAIN_FRAME_SEC + 0.5) * 30)
    example_out_frames = int((EXAMPLE_FRAME_SEC + 0.5) * 30)

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
        f"[abc][v3]xfade=transition=fade:duration=0.5:offset={t_example_to_end}[outv]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-framerate", "30", "-loop", "1", "-t", str(INTRO_FRAME_SEC + 0.5), "-i", str(intro_path),
        "-framerate", "1",  "-loop", "1", "-t", "1",                          "-i", str(main_path),
        "-framerate", "1",  "-loop", "1", "-t", "1",                          "-i", str(example_path),
        "-framerate", "30", "-loop", "1", "-t", str(END_FRAME_SEC + 0.5),     "-i", str(end_path),
    ]
    if music_path:
        cmd += ["-i", str(music_path)]
        # Audio is now the 5th input (index 4) since we have 4 video frames.
        # Chain: loudness norm (-14 LUFS broadcast standard) + 1-sec fade-in + 1-sec fade-out
        audio_filter = (
            f"[4:a]loudnorm=I=-14:TP=-1.5:LRA=11,"
            f"afade=t=in:d=1,"
            f"afade=t=out:st={DURATION_SEC - 1}:d=1[outa]"
        )
        cmd += [
            "-filter_complex", vfilter + ";" + audio_filter,
            "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(DURATION_SEC),
            "-r", "30",
            str(out_path),
        ]
    else:
        cmd += [
            "-filter_complex", vfilter,
            "-map", "[outv]",
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-t", str(DURATION_SEC),
            "-r", "30",
            str(out_path),
        ]
    subprocess.run(cmd, check=True)


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
    "This one took me three jobs to figure out.",
]
_FOLLOW_CTAS = [
    "Follow for daily corporate survival.",
    "Follow if office politics is draining you.",
    "Daily tactics so you stop getting played — follow.",
    "Read by people who got promoted last quarter. Up to you.",
    "Follow before the person after your job does.",
]
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
    cta = _FOLLOW_CTAS[(i // 2) % len(_FOLLOW_CTAS)]
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
    make_video(intro_image_path, image_path, example_image_path, end_image_path, music, video_path)
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
