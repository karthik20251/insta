"""Preview what a 'tease' intro frame would look like — WITHOUT modifying production code.

Renders sample intro frames for days 5, 50, 80 (with proposed teases) and day 10
(fallback to caption_hook). Saves to output/preview_tease_*.png so you can eyeball
before approving the change.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image, ImageDraw, ImageFont
from generate import (
    WIDTH, HEIGHT, GOLD, WHITE, DIM,
    make_background, pick_font, wrap_text, load_day,
)


# Strip emoji glyphs that PIL can't render (Cinzel/Playfair have no emoji)
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"   # symbols & pictographs
    "\U00002600-\U000027BF"   # misc symbols, dingbats
    "\U0001F1E6-\U0001F1FF"   # flags
    "]",
    flags=re.UNICODE,
)


def strip_emoji(text: str) -> str:
    return EMOJI_RE.sub("", text).strip()


# Proposed teases (only for these 3 days; everything else falls back)
TEASES = {
    5:  "The 1 silence that gets you a higher salary 💰 wait for it",
    50: "The math that turns reading 10 pages a day into 120 books — stay for it 📚",
    80: "When life feels chaotic, do this one thing first 🪞 wait for the move",
}


def render_tease_intro(day: dict, tease_text: str, out_path: Path, label: str = "") -> None:
    img = make_background(day["day"], day.get("book", ""))
    draw = ImageDraw.Draw(img)

    margin = 90
    max_w = WIDTH - 2 * margin

    text = strip_emoji(tease_text)
    # Start at 80px, drop to 68px if it wraps to 3+ lines
    font = pick_font(["PlayfairDisplay.ttf"], 80, weight=700)
    lines = wrap_text(text, font, max_w)
    if len(lines) >= 3:
        font = pick_font(["PlayfairDisplay.ttf"], 68, weight=700)
        lines = wrap_text(text, font, max_w)

    def line_h(f, l="Mg"):
        b = draw.textbbox((0, 0), l, font=f)
        return b[3] - b[1]

    h_total = sum(line_h(font, l) + 16 for l in lines) - 16
    # Center in top 60% of canvas
    y = (HEIGHT - 320 - h_total) // 2 + 80

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, y), line, fill=WHITE, font=font)
        y += line_h(font, line) + 16

    # Day label at bottom (continuity with main frame)
    font_day = pick_font(["Cinzel.ttf"], 36, weight=600)
    day_label = f"{day['title'].upper()}  ·  DAY {day['book_day']} OF {day['book_total']}"
    bbox = draw.textbbox((0, 0), day_label, font=font_day)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, HEIGHT - 240), day_label, fill=GOLD, font=font_day)

    # Tiny attribution badge so the source is clear
    font_src = pick_font(["PlayfairDisplay-Italic.ttf"], 32, weight=500)
    src_text = f"({label})" if label else ""
    if src_text:
        bbox = draw.textbbox((0, 0), src_text, font=font_src)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, 100), src_text, fill=GOLD, font=font_src)

    img.save(out_path, "PNG", optimize=True)
    print(f"  wrote {out_path.name}  ({len(lines)} lines @ {font.size}px)")


def main() -> int:
    out_dir = Path(__file__).parent.parent / "output"
    for day_num, tease in TEASES.items():
        day = load_day(day_num)
        render_tease_intro(day, tease, out_dir / f"preview_tease_day_{day_num:02d}.png", "TEASE")

    # Day 10 — no tease defined, falls back to caption_hook
    day10 = load_day(10)
    fallback = day10.get("caption_hook", "")
    render_tease_intro(day10, fallback, out_dir / "preview_tease_day_10.png", "FALLBACK · caption_hook")
    return 0


if __name__ == "__main__":
    sys.exit(main())
