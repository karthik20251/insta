"""Render the brand avatar + banner with the SAME PIL engine, fonts and
palette as the video frames, so the channel identity matches the content.

Outputs (upload these, nothing is committed):
  output/brand_avatar.png   800x800   -> YouTube Picture + Instagram pic
  output/brand_banner.png   2048x1152 -> YouTube banner (text in safe area)
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
FONTS = ROOT / "fonts"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

BG = (11, 10, 9)            # near-black, matches make_background floor
GOLD = (212, 175, 55)       # generate.py GOLD
WHITE = (240, 240, 240)
DIM = (165, 160, 150)
RED = (198, 40, 40)         # carries the old N logo's red bar forward


def font(name: str, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONTS / name), size)
    if weight is not None:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


def _center(draw, text, font_, cx, y, fill):
    b = draw.textbbox((0, 0), text, font=font_)
    draw.text((cx - (b[2] - b[0]) / 2 - b[0], y), text, font=font_, fill=fill)
    return b[3] - b[1]


def make_avatar() -> Path:
    S = 800
    img = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(img)
    cx = S // 2

    # Monogram — large, bold, gold, vertically centered with room for the bar.
    fz = 380
    fmono = font("Cinzel.ttf", fz, weight=900)
    b = d.textbbox((0, 0), "UR", font=fmono)
    tw, th = b[2] - b[0], b[3] - b[1]
    ty = (S - th) // 2 - b[1] - 40
    d.text((cx - tw / 2 - b[0], ty), "UR", font=fmono, fill=GOLD)

    # Red underline bar (brand continuity with the old logo).
    bar_w, bar_h = int(S * 0.40), 26
    bar_y = ty + th + b[1] + 70
    d.rounded_rectangle(
        [cx - bar_w // 2, bar_y, cx + bar_w // 2, bar_y + bar_h],
        radius=bar_h // 2, fill=RED,
    )
    p = OUT / "brand_avatar.png"
    img.save(p, "PNG", optimize=True)
    return p


def _fit_font(d, text, path, max_w, start, weight=None, floor=24):
    """Largest size whose rendered width <= max_w (auto-fit, never overflow)."""
    for sz in range(start, floor - 1, -2):
        f = font(path, sz, weight=weight)
        if d.textlength(text, font=f) <= max_w:
            return f
    return font(path, floor, weight=weight)


def make_banner() -> Path:
    W, H = 2048, 1152
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    cx = W // 2
    # YouTube's tightest crop ("all devices") is ~1235x338 centered. Stay
    # well inside it: ~1080 usable width, ~300 usable height (pad ~12%).
    USABLE_W, USABLE_H = 1080, 300

    name, tag = "UNWRITTEN RULES", "The career moves nobody teaches you."
    f_name = _fit_font(d, name, "Cinzel.ttf", USABLE_W, 132, weight=900)
    f_tag = _fit_font(d, tag, "PlayfairDisplay-Italic.ttf", USABLE_W, 50,
                      weight=500)

    bn = d.textbbox((0, 0), name, font=f_name)
    bt = d.textbbox((0, 0), tag, font=f_tag)
    h_name, h_tag = bn[3] - bn[1], bt[3] - bt[1]
    gap1, gap2, rule_h = 38, 38, 5
    block = h_name + gap1 + rule_h + gap2 + h_tag
    # Shrink proportionally if the stack is taller than the safe height.
    if block > USABLE_H:
        scale = USABLE_H / block
        f_name = _fit_font(d, name, "Cinzel.ttf", USABLE_W,
                           int((bn[3] - bn[1]) * scale) + 40, weight=900)
        f_tag = _fit_font(d, tag, "PlayfairDisplay-Italic.ttf", USABLE_W,
                          int((bt[3] - bt[1]) * scale) + 20, weight=500)
        bn = d.textbbox((0, 0), name, font=f_name)
        bt = d.textbbox((0, 0), tag, font=f_tag)
        h_name, h_tag = bn[3] - bn[1], bt[3] - bt[1]
        block = h_name + gap1 + rule_h + gap2 + h_tag

    y = (H - block) // 2
    y += _center(d, name, f_name, cx, y - bn[1], GOLD) + bn[1] + gap1
    d.line([(cx - 150, y), (cx + 150, y)], fill=GOLD, width=rule_h)
    y += rule_h + gap2
    _center(d, tag, f_tag, cx, y - bt[1], DIM)

    name_w = int(d.textlength(name, font=f_name))
    print(f"  banner: title width {name_w}px (safe<= {USABLE_W}), "
          f"block height {block}px (safe<= {USABLE_H})")
    p = OUT / "brand_banner.png"
    img.save(p, "PNG", optimize=True)
    return p


if __name__ == "__main__":
    a = make_avatar()
    b = make_banner()
    print(f"avatar: {a}")
    print(f"banner: {b}")
    sys.exit(0)
