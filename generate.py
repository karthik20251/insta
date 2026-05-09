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
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(exist_ok=True)

WIDTH, HEIGHT = 1080, 1920
DURATION_SEC = 12

GOLD = (212, 175, 55)
WHITE = (240, 240, 240)
DIM = (170, 170, 170)


def load_day(day_num: int) -> dict:
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    for d in data["days"]:
        if d["day"] == day_num:
            return {**d, "book": data["book"], "author": data["author"]}
    raise ValueError(f"No entry for day {day_num}")


def pick_font(preferred: list[str], size: int) -> ImageFont.FreeTypeFont:
    for name in preferred:
        p = FONTS_DIR / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    # fall back to any .ttf in fonts/, else PIL default
    any_ttf = sorted(FONTS_DIR.glob("*.ttf")) + sorted(FONTS_DIR.glob("*.otf"))
    if any_ttf:
        return ImageFont.truetype(str(any_ttf[0]), size)
    return ImageFont.load_default()


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
    img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw_gradient(img)
    draw = ImageDraw.Draw(img)

    font_title = pick_font(["Cinzel-Bold.ttf", "PlayfairDisplay-Bold.ttf"], 64)
    font_head = pick_font(["Cinzel-Bold.ttf", "PlayfairDisplay-Bold.ttf"], 84)
    font_body = pick_font(["PlayfairDisplay-Regular.ttf", "Cinzel-Regular.ttf"], 52)
    font_foot = pick_font(["PlayfairDisplay-Italic.ttf", "Cinzel-Regular.ttf"], 38)

    margin = 90
    max_w = WIDTH - 2 * margin

    # Top: "Day N · The 48 Laws of Power"
    top_label = f"DAY {day['day']}  ·  THE 48 LAWS OF POWER"
    bbox = draw.textbbox((0, 0), top_label, font=font_title)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, 180), top_label, fill=GOLD, font=font_title)

    # Headline (the law)
    head_lines = wrap_text(day["headline"].upper(), font_head, max_w)
    y = 360
    for line in head_lines:
        bbox = draw.textbbox((0, 0), line, font=font_head)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, y), line, fill=WHITE, font=font_head)
        y += (bbox[3] - bbox[1]) + 18

    # Divider
    y += 30
    draw.line([(WIDTH / 2 - 80, y), (WIDTH / 2 + 80, y)], fill=GOLD, width=3)
    y += 60

    # Body
    body_lines = wrap_text(day["body"], font_body, max_w)
    for line in body_lines:
        bbox = draw.textbbox((0, 0), line, font=font_body)
        draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, y), line, fill=WHITE, font=font_body)
        y += (bbox[3] - bbox[1]) + 14

    # Footer
    foot = f"— {day['author']}, {day['book']}"
    bbox = draw.textbbox((0, 0), foot, font=font_foot)
    draw.text(((WIDTH - (bbox[2] - bbox[0])) / 2, HEIGHT - 200), foot, fill=DIM, font=font_foot)

    img.save(out_path, "PNG", optimize=True)


def pick_music() -> Path | None:
    tracks = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.m4a")) + list(MUSIC_DIR.glob("*.wav"))
    return random.choice(tracks) if tracks else None


def make_video(image_path: Path, music_path: Path | None, out_path: Path) -> None:
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
    ]
    if music_path:
        cmd += ["-i", str(music_path)]
        cmd += [
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-shortest",
            "-t", str(DURATION_SEC),
            "-r", "30",
            "-vf", f"scale={WIDTH}:{HEIGHT}",
            str(out_path),
        ]
    else:
        cmd += [
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-t", str(DURATION_SEC),
            "-r", "30",
            "-vf", f"scale={WIDTH}:{HEIGHT}",
            str(out_path),
        ]
    subprocess.run(cmd, check=True)


def build(day_num: int) -> dict:
    day = load_day(day_num)
    image_path = OUT_DIR / f"day_{day_num:02d}.png"
    video_path = OUT_DIR / f"day_{day_num:02d}.mp4"
    render_image(day, image_path)
    music = pick_music()
    make_video(image_path, music, video_path)
    return {
        "day": day,
        "image": image_path,
        "video": video_path,
        "music": music,
    }


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    result = build(n)
    print(f"Built day {n}: {result['video']}")
