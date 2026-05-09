"""Download cinematic dark instrumental tracks from Internet Archive.

Source: Kevin MacLeod's "Darkness" album, hosted on archive.org.
License: CC-BY 4.0 — attribution required (we add it to the caption).
"""
from __future__ import annotations
import sys
import time
import urllib.parse
from pathlib import Path
import requests

ROOT = Path(__file__).parent.parent
MUSIC_DIR = ROOT / "music"
MUSIC_DIR.mkdir(exist_ok=True)

ARCHIVE_ID = "Kevin-MacLeod_Darkness_2014_FullAlbum"

# Hand-picked tracks fitting the 48 Laws of Power theme (dark, cinematic, regal).
TRACKS = [
    "Kevin MacLeod - 04 - Dark Times.mp3",
    "Kevin MacLeod - 05 - Darkest Child.mp3",
    "Kevin MacLeod - 07 - Epic Unease.mp3",
    "Kevin MacLeod - 09 - Gagool.mp3",
    "Kevin MacLeod - 14 - Phantasm.mp3",
    "Kevin MacLeod - 15 - Power Restored.mp3",
    "Kevin MacLeod - 22 - Tectonic.mp3",
    "Kevin MacLeod - 23 - The Chamber.mp3",
    "Kevin MacLeod - 24 - The Reveal.mp3",
    "Kevin MacLeod - 16 - Shamanistic.mp3",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (instaautomatic; daily reels)"}


def download(filename: str) -> bool:
    # Files in this archive item live under a "Darkness/" subfolder
    quoted = urllib.parse.quote(f"Darkness/{filename}")
    url = f"https://archive.org/download/{ARCHIVE_ID}/{quoted}"
    out = MUSIC_DIR / filename.replace(" ", "_").replace("'", "")
    if out.exists() and out.stat().st_size > 200_000:
        print(f"[SKIP] {out.name} already present ({out.stat().st_size // 1024} KB)")
        return True
    try:
        r = requests.get(url, headers=HEADERS, timeout=300, allow_redirects=True, stream=True)
        if r.status_code != 200:
            print(f"[FAIL] {filename}  HTTP {r.status_code}")
            return False
        with open(out, "wb") as f:
            for chunk in r.iter_content(chunk_size=64 * 1024):
                f.write(chunk)
        kb = out.stat().st_size // 1024
        if kb < 200:
            print(f"[FAIL] {filename}  only {kb} KB (probably error page)")
            out.unlink(missing_ok=True)
            return False
        print(f"[OK]   {out.name}  {kb} KB")
        return True
    except Exception as e:
        print(f"[FAIL] {filename}  {e}")
        return False


def cleanup_synthetic() -> None:
    """Remove the placeholder synth tracks now that we have real music."""
    for old in ("01_iron_resolve.mp3", "02_the_strategist.mp3", "03_throne_of_power.mp3"):
        p = MUSIC_DIR / old
        if p.exists():
            p.unlink()
            print(f"[REMOVE] {old}")


def main() -> int:
    ok = 0
    for t in TRACKS:
        if download(t):
            ok += 1
        time.sleep(0.5)
    if ok >= 3:
        cleanup_synthetic()
    print(f"\n{ok}/{len(TRACKS)} tracks ready in {MUSIC_DIR}")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
