"""Fetch backgrounds + music for the Atomic Habits and 12 Rules for Life books.

Atomic Habits — modern, optimistic, growth themes:
  - Backgrounds: bright impressionist + Hokusai landscapes (sunrise, mountains, paths)
  - Music: lighter cinematic / instrumental piano

12 Rules for Life — contemplative, philosophical, order-vs-chaos:
  - Backgrounds: dramatic landscapes, mountains, classical philosophy
  - Music: somber orchestral / classical
"""
from __future__ import annotations
import io
import sys
import time
import urllib.parse
from pathlib import Path
import requests
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).parent.parent
HEADERS = {"User-Agent": "instaautomatic/1.0 (educational; daily reels)"}
WIDTH, HEIGHT = 1080, 1920

# ---- Backgrounds (Wikimedia Commons) ----------------------------------------------------

# Atomic Habits — light, journey, growth, sunrise themes
ATOMIC_BACKGROUNDS = [
    ("hokusai_great_wave.jpg",
     "File:Tsunami by hokusai 19th century.jpg"),
    ("monet_impression_sunrise.jpg",
     "File:Monet - Impression, Sunrise.jpg"),
    ("hokusai_red_fuji.jpg",
     "File:Red Fuji southern wind clear morning.jpg"),
    ("vangogh_starry_night.jpg",
     "File:Van Gogh - Starry Night - Google Art Project.jpg"),
    ("turner_fighting_temeraire.jpg",
     "File:Turner, J. M. W. - The Fighting Téméraire tugged to her last Berth to be broken.jpg"),
    ("wanderer_fog.jpg",
     "File:Caspar David Friedrich - Wanderer above the sea of fog.jpg"),
]

# 12 Rules — dramatic, philosophical, mountain/storm themes
RULES_BACKGROUNDS = [
    ("turner_snowstorm.jpg",
     "File:Hannibal traversant les Alpes.jpg"),
    ("friedrich_monk.jpg",
     "File:Caspar David Friedrich - Der Mönch am Meer - Google Art Project.jpg"),
    ("dore_inferno.jpg",
     "File:Gustave Dore Inferno1.jpg"),
    ("durer_knight.jpg",
     "File:Knight, Death, and the Devil (Albrecht Dürer).jpg"),
    ("hokusai_kanagawa.jpg",
     "File:Great Wave off Kanagawa2.jpg"),
    ("constable_hadleigh.jpg",
     "File:John Constable - Hadleigh Castle, The Mouth of the Thames - Morning after a Stormy Night - Google Art Project, Lambeth.jpg"),
]


def fetch_url(commons_filename: str) -> str:
    api = "https://commons.wikimedia.org/w/api.php"
    r = requests.get(api, params={
        "action": "query", "titles": commons_filename,
        "prop": "imageinfo", "iiprop": "url", "iiurlwidth": "1600", "format": "json",
    }, headers=HEADERS, timeout=30)
    pages = r.json().get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    info = page.get("imageinfo", [{}])[0]
    return info.get("thumburl") or info.get("url", "")


def darken_and_blur(img: Image.Image, brightness: float = 0.40) -> Image.Image:
    img = img.convert("RGB")
    sw, sh = img.size
    target = WIDTH / HEIGHT
    src = sw / sh
    if src > target:
        new_w = int(sh * target)
        x0 = (sw - new_w) // 2
        img = img.crop((x0, 0, x0 + new_w, sh))
    else:
        new_h = int(sw / target)
        y0 = (sh - new_h) // 2
        img = img.crop((0, y0, sw, y0 + new_h))
    img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
    img = img.filter(ImageFilter.GaussianBlur(radius=14))
    img = ImageEnhance.Brightness(img).enhance(brightness)
    return img


def download_with_retry(url: str, retries: int = 4) -> bytes:
    delay = 2.0
    for _ in range(retries):
        r = requests.get(url, headers=HEADERS, timeout=120)
        if r.status_code == 200:
            return r.content
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", "0")) or delay
            time.sleep(wait)
            delay *= 2
            continue
        r.raise_for_status()
    raise RuntimeError(f"Gave up on {url}")


def fetch_backgrounds(items: list, out_dir: Path, brightness: float) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = 0
    for out_name, title in items:
        out = out_dir / out_name
        if out.exists() and out.stat().st_size > 5000:
            print(f"  [SKIP] {out_name} exists"); ok += 1; continue
        try:
            url = fetch_url(title)
            if not url:
                print(f"  [SKIP] no URL for {title}"); continue
            time.sleep(1.2)
            content = download_with_retry(url)
            img = Image.open(io.BytesIO(content))
            darken_and_blur(img, brightness).save(out, "JPEG", quality=82, optimize=True)
            print(f"  [OK]   {out_name}  {out.stat().st_size // 1024} KB")
            ok += 1
            time.sleep(1.2)
        except Exception as e:
            print(f"  [FAIL] {out_name}  {e}")
    return ok


# ---- Music (Internet Archive) ---------------------------------------------------------

# Atomic Habits — bright, uplifting classical tracks (familiar, motivating)
ATOMIC_MUSIC = {
    "archive_id": "Kevin-MacLeod_Famous-Classics_2008_FullAlbum",
    "subfolder": "Famous Classics",
    "tracks": [
        "Kevin MacLeod - 02 - Canon in D Major.mp3",
        "Kevin MacLeod - 03 - Cello Suite #1 in G - Prelude.mp3",
        "Kevin MacLeod - 06 - Dance of the Sugar Plum Fairies.mp3",
        "Kevin MacLeod - 07 - Divertimento K131.mp3",
        "Kevin MacLeod - 08 - Divertissement.mp3",
        "Kevin MacLeod - 09 - Jesu, Joy of Man's Desiring.mp3",
    ],
}

# 12 Rules — contemplative classical (Bach, orchestral, philosophical)
RULES_MUSIC = {
    "archive_id": "Classical_Sampler-9615",
    "subfolder": None,
    "tracks": [
        "Kevin_MacLeod_-_Also_Sprach_Zarathustra.mp3",
        "Kevin_MacLeod_-_Brandenburg_Concerto_No4-1_BWV1049.mp3",
        "Kevin_MacLeod_-_Canon_in_D_Major.mp3",
        "Kevin_MacLeod_-_Danse_Macabre.mp3",
        "Kevin_MacLeod_-_Funeral_March_for_Brass.mp3",
        "Kevin_MacLeod_-_Ghost_Dance.mp3",
    ],
}

# Action Cuts — energetic/cinematic for additional variety in 48 Laws + Atomic Habits
LAWS_ACTION_MUSIC = {
    "archive_id": "Kevin-Macleod_Action-Cuts_2014_FullAlbum",
    "subfolder": "Action Cuts",
    "tracks": [
        "Kevin MacLeod - 02 - Action.mp3",
        "Kevin MacLeod - 04 - Black Vortex.mp3",
        "Kevin MacLeod - 12 - Heroic Age.mp3",
        "Kevin MacLeod - 13 - Hitman.mp3",
        "Kevin MacLeod - 19 - Noble Race.mp3",
        "Kevin MacLeod - 24 - The Complex.mp3",
    ],
}

ATOMIC_ACTION_MUSIC = {
    "archive_id": "Kevin-Macleod_Action-Cuts_2014_FullAlbum",
    "subfolder": "Action Cuts",
    "tracks": [
        "Kevin MacLeod - 16 - Mighty and Meek.mp3",
        "Kevin MacLeod - 18 - Movement Proposition.mp3",
        "Kevin MacLeod - 20 - Plans in Motion.mp3",
        "Kevin MacLeod - 25 - Unity.mp3",
    ],
}


def fetch_music(spec: dict, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = 0
    for filename in spec["tracks"]:
        local_name = filename.replace(" ", "_").replace("'", "")
        out = out_dir / local_name
        if out.exists() and out.stat().st_size > 200_000:
            print(f"  [SKIP] {out.name} exists"); ok += 1; continue
        path = f"{spec['subfolder']}/{filename}" if spec.get("subfolder") else filename
        url = f"https://archive.org/download/{spec['archive_id']}/{urllib.parse.quote(path)}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=300, stream=True)
            if r.status_code != 200:
                print(f"  [FAIL] {filename}  HTTP {r.status_code}"); continue
            with open(out, "wb") as f:
                for chunk in r.iter_content(64 * 1024):
                    f.write(chunk)
            kb = out.stat().st_size // 1024
            if kb < 200:
                print(f"  [FAIL] {filename}  only {kb} KB"); out.unlink(missing_ok=True); continue
            print(f"  [OK]   {out.name}  {kb} KB")
            ok += 1
        except Exception as e:
            print(f"  [FAIL] {filename}  {e}")
        time.sleep(0.5)
    return ok


def main() -> int:
    print("\n=== Atomic Habits backgrounds ===")
    fetch_backgrounds(ATOMIC_BACKGROUNDS, ROOT / "backgrounds" / "atomic", brightness=0.55)

    print("\n=== 12 Rules backgrounds ===")
    fetch_backgrounds(RULES_BACKGROUNDS, ROOT / "backgrounds" / "rules", brightness=0.35)

    print("\n=== Atomic Habits music ===")
    fetch_music(ATOMIC_MUSIC, ROOT / "music" / "atomic")

    print("\n=== 12 Rules music ===")
    fetch_music(RULES_MUSIC, ROOT / "music" / "rules")

    print("\n=== Action Cuts -> 48 Laws (energetic for power/strategy days) ===")
    fetch_music(LAWS_ACTION_MUSIC, ROOT / "music" / "48laws")

    print("\n=== Action Cuts -> Atomic Habits (energetic for habit/action days) ===")
    fetch_music(ATOMIC_ACTION_MUSIC, ROOT / "music" / "atomic")

    return 0


if __name__ == "__main__":
    sys.exit(main())
