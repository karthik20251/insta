"""Build a 1080x1920 Reel: gradient background + quote text + a music track."""
from __future__ import annotations
import json
import os
import random
import subprocess
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
QUOTES = ROOT / "quotes.json"
MUSIC_DIR = ROOT / "music"
FONTS_DIR = ROOT / "fonts"
BG_DIR = ROOT / "backgrounds"
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(exist_ok=True)

WIDTH, HEIGHT = 1080, 1920
DURATION_SEC = 24
INTRO_FRAME_SEC = 2        # 0-2:    just headline (hook)
MAIN_FRAME_SEC = 8         # 2-10:   the law/principle (abstract)
EXAMPLE_FRAME_SEC = 12     # 10-22:  real-life example (acceptance for life)
END_FRAME_SEC = 2          # 22-24:  CTA + tomorrow teaser

GOLD = (212, 175, 55)
WHITE = (240, 240, 240)
DIM = (170, 170, 170)


def load_day(day_num: int) -> dict:
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    default_book = data["book"]
    default_author = data["author"]

    # Compute book_day (position within book) and book_total (size of book) for every day
    by_book: dict[str, list[dict]] = {}
    for d in data["days"]:
        bk = d.get("book", default_book)
        by_book.setdefault(bk, []).append(d)

    for d in data["days"]:
        if d["day"] == day_num:
            book = d.get("book", default_book)
            day_list = by_book[book]
            book_day = next(i for i, x in enumerate(day_list) if x["day"] == day_num) + 1
            result = dict(d)
            result.setdefault("book", default_book)
            result.setdefault("author", default_author)
            result["total_days"] = len(data["days"])
            result["book_day"] = book_day
            result["book_total"] = len(day_list)
            return result
    raise ValueError(f"No entry for day {day_num}")


def total_days() -> int:
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    return len(data["days"])


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
    return "48laws"


def make_background(day_num: int, book: str = "") -> Image.Image:
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

    # Deterministic per day so re-renders look identical
    bg_path = backgrounds[(day_num * 7 + 3) % len(backgrounds)]
    bg = Image.open(bg_path).convert("RGB")
    if bg.size != (WIDTH, HEIGHT):
        bg = bg.resize((WIDTH, HEIGHT), Image.LANCZOS)

    # Build a single-row darkening mask (white where we want darker, black where we want lighter)
    # Then stretch it to full image and use as opacity mask blending bg with black.
    # Slightly lighter overlay for Atomic Habits so the brighter paintings show through.
    base_dark = 0.55 if slug == "atomic" else 0.62
    edge_dark = 0.20 if slug == "atomic" else 0.22
    mask_col = Image.new("L", (1, HEIGHT))
    mp = mask_col.load()
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        bell = abs(t - 0.5) * 2  # 1 at edges, 0 at center
        darken = base_dark + edge_dark * bell
        mp[0, y] = int(darken * 255)
    mask = mask_col.resize((WIDTH, HEIGHT))
    black = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    return Image.composite(black, bg, mask)


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


def render_intro_frame(day: dict, out_path: Path) -> None:
    """First 2 seconds — just the headline + day label, centered.

    Used as a hook before the full quote fades in. Same background painting as
    the main frame for visual continuity, just less content.
    """
    img = make_background(day["day"], day.get("book", ""))
    draw = ImageDraw.Draw(img)

    font_head = pick_font(["Cinzel.ttf", "Cinzel-Bold.ttf", "PlayfairDisplay.ttf"], 78, weight=900)
    font_day = pick_font(["Cinzel.ttf"], 36, weight=600)

    margin = 90
    max_w = WIDTH - 2 * margin

    head_lines = wrap_text(day["headline"].upper(), font_head, max_w)

    def line_h(font: ImageFont.FreeTypeFont, line: str = "Mg") -> int:
        bbox = draw.textbbox((0, 0), line, font=font)
        return bbox[3] - bbox[1]

    h_head = sum(line_h(font_head, l) + 18 for l in head_lines) - 18
    y = (HEIGHT - h_head) // 2  # dead-center vertically

    for line in head_lines:
        bbox = draw.textbbox((0, 0), line, font=font_head)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, y), line, fill=WHITE, font=font_head)
        y += line_h(font_head, line) + 18

    # Day label at bottom (same position as main frame for visual continuity)
    day_label = f"{day['title'].upper()}  ·  DAY {day['book_day']} OF {day['book_total']}"
    bbox = draw.textbbox((0, 0), day_label, font=font_day)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, HEIGHT - 240), day_label, fill=GOLD, font=font_day)

    img.save(out_path, "PNG", optimize=True)


def render_example_frame(day: dict, out_path: Path) -> None:
    """Third frame (12 sec) — a real-life example showing how to apply the law/principle.

    Layout:
      Top: "FOR YOUR LIFE" gold label
      Middle: the example text (centered, large readable body font)
      Bottom: same day label + author/book as main frame (continuity)
    """
    img = make_background(day["day"], day.get("book", ""))
    draw = ImageDraw.Draw(img)

    font_label = pick_font(["Cinzel.ttf"], 52, weight=700)
    font_body = pick_font(["PlayfairDisplay.ttf"], 54, weight=500)
    font_day = pick_font(["Cinzel.ttf"], 36, weight=600)
    font_foot = pick_font(["PlayfairDisplay-Italic.ttf"], 38, weight=500)

    margin = 90
    max_w = WIDTH - 2 * margin

    # Book-specific label: each book has its own tone signature
    slug = book_slug(day.get("book", ""))
    if slug == "48laws":
        label_text = "TODAY'S MOVE"        # tactical, game-like
    elif slug == "atomic":
        label_text = "THE PRACTICE"        # habit-focused, ritualistic
    elif slug == "rules":
        label_text = "LIVE BY THIS"        # philosophical, principled
    else:
        label_text = "IN PRACTICE"         # fallback for future books

    example_lines = wrap_text(day.get("example", ""), font_body, max_w)

    def line_h(font: ImageFont.FreeTypeFont, line: str = "Mg") -> int:
        bbox = draw.textbbox((0, 0), line, font=font)
        return bbox[3] - bbox[1]

    h_label = line_h(font_label)
    gap_label_to_body = 80
    h_body = sum(line_h(font_body, l) + 16 for l in example_lines) - 16
    total = h_label + gap_label_to_body + h_body

    top_margin = 240
    footer_zone = 320
    available = HEIGHT - top_margin - footer_zone
    y = top_margin + max(0, (available - total) // 2)

    bbox = draw.textbbox((0, 0), label_text, font=font_label)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, y), label_text, fill=GOLD, font=font_label)
    y += h_label + gap_label_to_body

    for line in example_lines:
        bbox = draw.textbbox((0, 0), line, font=font_body)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, y), line, fill=WHITE, font=font_body)
        y += line_h(font_body, line) + 16

    # Footer (day label + attribution) — same as main frame for continuity
    day_label = f"{day['title'].upper()}  ·  DAY {day['book_day']} OF {day['book_total']}"
    bbox = draw.textbbox((0, 0), day_label, font=font_day)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, HEIGHT - 240), day_label, fill=GOLD, font=font_day)
    foot = f"— {day['author']}, {day['book']}"
    bbox = draw.textbbox((0, 0), foot, font=font_foot)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, HEIGHT - 180), foot, fill=DIM, font=font_foot)

    img.save(out_path, "PNG", optimize=True)


def render_end_frame(day: dict, out_path: Path) -> None:
    """Render the last-3-second 'COMMENT BELOW + TOMORROW teaser' frame.

    Cross-book transitions are handled automatically: if the next day belongs to
    a different book, the teaser shows the new book's title. If there is no next
    day (final post), shows 'SERIES COMPLETE'."""
    img = make_background(day["day"], day.get("book", ""))
    draw = ImageDraw.Draw(img)

    font_cta = pick_font(["Cinzel.ttf"], 76, weight=900)
    font_label = pick_font(["Cinzel.ttf"], 44, weight=600)
    font_next = pick_font(["PlayfairDisplay.ttf"], 60, weight=700)
    font_arrow = pick_font(["PlayfairDisplay.ttf"], 80, weight=700)
    font_follow = pick_font(["PlayfairDisplay-Italic.ttf"], 38, weight=500)

    margin = 90
    max_w = WIDTH - 2 * margin

    # Top: big CTA
    cta_main = "COMMENT BELOW"
    cta_sub = "Save · Share · Tag a friend"
    bbox = draw.textbbox((0, 0), cta_main, font=font_cta)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, 400), cta_main, fill=GOLD, font=font_cta)
    bbox = draw.textbbox((0, 0), cta_sub, font=font_label)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, 520), cta_sub, fill=WHITE, font=font_label)
    draw.line([(WIDTH / 2 - 100, 660), (WIDTH / 2 + 100, 660)], fill=GOLD, width=4)

    # Look up tomorrow's content for the teaser
    next_day = None
    if day["day"] < total_days():
        try:
            next_day = load_day(day["day"] + 1)
        except ValueError:
            next_day = None

    if next_day:
        label = "TOMORROW"
        bbox = draw.textbbox((0, 0), label, font=font_label)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, 760), label, fill=GOLD, font=font_label)

        title_line = next_day["title"].upper()
        bbox = draw.textbbox((0, 0), title_line, font=font_next)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, 840), title_line, fill=WHITE, font=font_next)

        y = 930
        for line in wrap_text(next_day["headline"], font_next, max_w):
            bbox = draw.textbbox((0, 0), line, font=font_next)
            draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, y), line, fill=WHITE, font=font_next)
            y += (bbox[3] - bbox[1]) + 12

        chevron = "» » »"
        bbox = draw.textbbox((0, 0), chevron, font=font_arrow)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, y + 50), chevron, fill=GOLD, font=font_arrow)

        follow = "follow @nandetroll_ for daily"
        bbox = draw.textbbox((0, 0), follow, font=font_follow)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, HEIGHT - 200), follow, fill=DIM, font=font_follow)
    else:
        label = "SERIES COMPLETE"
        bbox = draw.textbbox((0, 0), label, font=font_label)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, 800), label, fill=GOLD, font=font_label)
        thanks = "Thank you for following along"
        bbox = draw.textbbox((0, 0), thanks, font=font_next)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, 900), thanks, fill=WHITE, font=font_next)

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
    """Build a 24-sec Reel as four frames with crossfades:
       0-2 sec     intro      (headline + day label only)
       2-10 sec    main       (law explanation, with Ken Burns zoom)
       10-22 sec   example    (real-life application, with subtle zoom)
       22-24 sec   end frame  (CTA + tomorrow teaser)

    Each transition uses a 0.5-sec crossfade.
    """
    t_intro_to_main = INTRO_FRAME_SEC - 0.5                              # 1.5
    t_main_to_example = INTRO_FRAME_SEC + MAIN_FRAME_SEC - 0.5            # 9.5
    t_example_to_end = INTRO_FRAME_SEC + MAIN_FRAME_SEC + EXAMPLE_FRAME_SEC - 0.5  # 21.5

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


def build(day_num: int) -> dict:
    day = load_day(day_num)
    intro_image_path = OUT_DIR / f"day_{day_num:02d}_intro.png"
    image_path = OUT_DIR / f"day_{day_num:02d}.png"
    example_image_path = OUT_DIR / f"day_{day_num:02d}_example.png"
    end_image_path = OUT_DIR / f"day_{day_num:02d}_end.png"
    video_path = OUT_DIR / f"day_{day_num:02d}.mp4"
    render_intro_frame(day, intro_image_path)
    render_image(day, image_path)
    render_example_frame(day, example_image_path)
    render_end_frame(day, end_image_path)
    music = pick_music(day.get("book", ""), day.get("mood", ""))
    make_video(intro_image_path, image_path, example_image_path, end_image_path, music, video_path)
    return {
        "day": day,
        "intro_image": intro_image_path,
        "image": image_path,
        "example_image": example_image_path,
        "end_image": end_image_path,
        "video": video_path,
        "music": music,
    }


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    result = build(n)
    print(f"Built day {n}: {result['video']}")
