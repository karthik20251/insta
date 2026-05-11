"""Generate sample 'end frame' images showing what the visual CTA + tomorrow teaser would look like.

Produces:
  output/end_frame_day_02.png  — what would appear at seconds 9-12 of Day 2's Reel
  output/end_frame_day_49.png  — what would appear for Day 49 (transition into Atomic Habits)
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from generate import (
    WIDTH, HEIGHT, GOLD, WHITE, DIM,
    make_background, pick_font, wrap_text, load_day, total_days,
)


def render_end_frame(day_num: int, out_path: Path) -> None:
    day = load_day(day_num)
    img = make_background(day_num, day.get("book", ""))
    draw = ImageDraw.Draw(img)

    # Look up tomorrow's day. If beyond series end, tomorrow_day = None.
    next_day = None
    if day_num < total_days():
        try:
            next_day = load_day(day_num + 1)
        except ValueError:
            next_day = None

    font_cta = pick_font(["Cinzel.ttf"], 76, weight=900)
    font_label = pick_font(["Cinzel.ttf"], 44, weight=600)
    font_next = pick_font(["PlayfairDisplay.ttf"], 60, weight=700)
    font_arrow = pick_font(["PlayfairDisplay.ttf"], 80, weight=700)

    margin = 90
    max_w = WIDTH - 2 * margin

    # ── Top section: big call-to-action ────────────────────────────────
    # No emoji in the bold serif font (it lacks emoji glyphs and renders as boxes)
    cta_main = "COMMENT BELOW"
    cta_sub = "Save · Share · Tag a friend"

    bbox = draw.textbbox((0, 0), cta_main, font=font_cta)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, 400), cta_main, fill=GOLD, font=font_cta)

    bbox = draw.textbbox((0, 0), cta_sub, font=font_label)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, 520), cta_sub, fill=WHITE, font=font_label)

    # Divider
    draw.line([(WIDTH / 2 - 100, 660), (WIDTH / 2 + 100, 660)], fill=GOLD, width=4)

    # ── Bottom section: tomorrow's teaser ──────────────────────────────
    if next_day:
        label = "TOMORROW"
        bbox = draw.textbbox((0, 0), label, font=font_label)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, 760), label, fill=GOLD, font=font_label)

        teaser_line1 = f"{next_day['title'].upper()}"
        bbox = draw.textbbox((0, 0), teaser_line1, font=font_next)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, 840), teaser_line1, fill=WHITE, font=font_next)

        teaser_lines = wrap_text(next_day["headline"], font_next, max_w)
        y = 930
        for line in teaser_lines:
            bbox = draw.textbbox((0, 0), line, font=font_next)
            draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, y), line, fill=WHITE, font=font_next)
            y += (bbox[3] - bbox[1]) + 12

        # Use a chevron line instead of an arrow character (more universal in fonts)
        chevron = "» » »"
        bbox = draw.textbbox((0, 0), chevron, font=font_arrow)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, y + 50), chevron, fill=GOLD, font=font_arrow)

        # Footer hook
        font_follow = pick_font(["PlayfairDisplay-Italic.ttf"], 38, weight=500)
        follow = "follow @nandetroll_ for daily"
        bbox = draw.textbbox((0, 0), follow, font=font_follow)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, HEIGHT - 200), follow, fill=DIM, font=font_follow)
    else:
        # End of series frame
        label = "SERIES COMPLETE"
        bbox = draw.textbbox((0, 0), label, font=font_label)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, 800), label, fill=GOLD, font=font_label)
        thanks = "Thank you for following along"
        bbox = draw.textbbox((0, 0), thanks, font=font_next)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, 900), thanks, fill=WHITE, font=font_next)

    img.save(out_path, "PNG", optimize=True)
    print(f"  wrote {out_path}")


if __name__ == "__main__":
    out_dir = Path(__file__).parent.parent / "output"
    out_dir.mkdir(exist_ok=True)
    render_end_frame(2, out_dir / "end_frame_day_02.png")    # Day 2 → tomorrow is Law 2
    render_end_frame(49, out_dir / "end_frame_day_49.png")   # Day 49 → tomorrow is Atomic Habits intro
    render_end_frame(79, out_dir / "end_frame_day_79.png")   # Day 79 → tomorrow is 12 Rules intro
    render_end_frame(92, out_dir / "end_frame_day_92.png")   # final day → series complete
