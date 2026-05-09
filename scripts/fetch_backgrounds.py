"""Download power-themed public-domain paintings from Wikimedia Commons.

Each is auto-processed into a 1080x1920 dark, blurred backdrop suitable for text overlay.
Run once. Re-run to refresh the pool.
"""
from __future__ import annotations
import io
import sys
import time
from pathlib import Path
import requests
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).parent.parent
BG_DIR = ROOT / "backgrounds"
BG_DIR.mkdir(exist_ok=True)

# Curated. All public domain (artists died >100 yrs ago). Theme: power, strategy, drama.
PAINTINGS = [
    ("napoleon_crossing.jpg",
     "File:Jacques-Louis David - Bonaparte franchissant le Grand Saint-Bernard, 20 mai 1800 - Versailles.jpg"),
    ("napoleon_coronation.jpg",
     "File:Jacques-Louis David, The Coronation of Napoleon edit.jpg"),
    ("liberty_leading.jpg",
     "File:Eugène Delacroix - Le 28 Juillet. La Liberté guidant le peuple.jpg"),
    ("saturn_devouring.jpg",
     "File:Francisco de Goya, Saturno devorando a su hijo (1819-1823).jpg"),
    ("third_of_may.jpg",
     "File:El Tres de Mayo, by Francisco de Goya, from Prado thin black margin.jpg"),
    ("wanderer_fog.jpg",
     "File:Caspar David Friedrich - Wanderer above the sea of fog.jpg"),
    ("judith_holofernes.jpg",
     "File:Caravaggio Judith Beheading Holofernes.jpg"),
    ("calling_matthew.jpg",
     "File:The Calling of Saint Matthew-Caravaggo (1599-1600).jpg"),
    ("raft_medusa.jpg",
     "File:JEAN LOUIS THÉODORE GÉRICAULT - La Balsa de la Medusa (Museo del Louvre, 1818-19).jpg"),
    ("las_meninas.jpg",
     "File:Las Meninas, by Diego Velázquez, from Prado in Google Earth.jpg"),
]

WIDTH, HEIGHT = 1080, 1920
HEADERS = {"User-Agent": "instaautomatic/1.0 (educational; daily reels)"}


def fetch_url(commons_filename: str) -> str:
    """Resolve a 'File:...' Commons title to a direct image URL."""
    api = "https://commons.wikimedia.org/w/api.php"
    r = requests.get(api, params={
        "action": "query", "titles": commons_filename,
        "prop": "imageinfo", "iiprop": "url",
        "iiurlwidth": "1600", "format": "json",
    }, headers=HEADERS, timeout=30)
    pages = r.json().get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    info = page.get("imageinfo", [{}])[0]
    return info.get("thumburl") or info.get("url", "")


def darken_and_blur(img: Image.Image) -> Image.Image:
    """Crop to 9:16, blur, darken — so text on top is legible."""
    img = img.convert("RGB")

    # Cover-fit crop to 1080x1920 (preserve aspect, crop to fill)
    src_w, src_h = img.size
    target_ratio = WIDTH / HEIGHT
    src_ratio = src_w / src_h
    if src_ratio > target_ratio:
        # source is wider — crop sides
        new_w = int(src_h * target_ratio)
        x0 = (src_w - new_w) // 2
        img = img.crop((x0, 0, x0 + new_w, src_h))
    else:
        # source is taller — crop top/bottom
        new_h = int(src_w / target_ratio)
        y0 = (src_h - new_h) // 2
        img = img.crop((0, y0, src_w, y0 + new_h))
    img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)

    # Heavy blur (so the painting is atmospheric, not distracting)
    img = img.filter(ImageFilter.GaussianBlur(radius=14))

    # Darken to ~30% brightness
    img = ImageEnhance.Brightness(img).enhance(0.35)

    # Slight cool→warm tone shift (push toward dark amber)
    r, g, b = img.split()
    r = r.point(lambda v: min(255, int(v * 1.05)))
    b = b.point(lambda v: int(v * 0.85))
    img = Image.merge("RGB", (r, g, b))

    return img


def download_with_retry(url: str, retries: int = 4) -> bytes:
    delay = 2.0
    for i in range(retries):
        r = requests.get(url, headers=HEADERS, timeout=120)
        if r.status_code == 200:
            return r.content
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", "0")) or delay
            print(f"      429 — sleeping {wait}s...")
            time.sleep(wait)
            delay *= 2
            continue
        r.raise_for_status()
    raise RuntimeError(f"Gave up on {url}")


def main() -> int:
    ok = 0
    for out_name, commons_title in PAINTINGS:
        out_path = BG_DIR / out_name
        if out_path.exists() and out_path.stat().st_size > 5000:
            print(f"[SKIP] {out_name} already exists")
            ok += 1
            continue
        try:
            url = fetch_url(commons_title)
            if not url:
                print(f"[SKIP] no URL for {commons_title}"); continue
            time.sleep(1.5)
            content = download_with_retry(url)
            src = Image.open(io.BytesIO(content))
            processed = darken_and_blur(src)
            processed.save(out_path, "JPEG", quality=82, optimize=True)
            print(f"[OK] {out_name}  {out_path.stat().st_size // 1024} KB")
            ok += 1
            time.sleep(1.5)
        except Exception as e:
            print(f"[FAIL] {out_name}  {e}")
    print(f"\n{ok}/{len(PAINTINGS)} backgrounds ready in {BG_DIR}")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
