"""Download a curated set of ccMixter instrumental tracks across moods.

ccMixter tracks are Creative Commons licensed. Most are CC-BY-NC (non-commercial
attribution required). Safe for personal social accounts; if the account ever
monetizes (sponsorships/ads), tracks marked NC should be removed.
"""
from __future__ import annotations
import ssl
import sys
import urllib.request
from pathlib import Path

# ccMixter has stale cert chain. Public read-only downloads — safe to skip verification.
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

ROOT = Path(__file__).parent.parent
MUSIC = ROOT / "music"

CURATED = {
    "48laws": [
        # Dark / strategic / mask vibes
        ("https://ccmixter.org/content/7OOP3D/7OOP3D_-_Feeling_Dark_(Behind_The_Mask).mp3", "7OOP3D_-_Feeling_Dark.mp3"),
        ("https://ccmixter.org/content/cdk/cdk_-_Silence_Await.mp3", "cdk_-_Silence_Await.mp3"),
    ],
    "atomic": [
        # Upbeat / motivational / forward-moving
        ("https://ccmixter.org/content/AlexBeroza/AlexBeroza_-_Drive.mp3", "AlexBeroza_-_Drive.mp3"),
        ("https://ccmixter.org/content/AlexBeroza/AlexBeroza_-_Spinnin_.mp3", "AlexBeroza_-_Spinnin.mp3"),
        ("https://ccmixter.org/content/mindmapthat/mindmapthat_-_Pulse_of_the_Party_1.mp3", "mindmapthat_-_Pulse_of_the_Party.mp3"),
    ],
    "rules": [
        # Contemplative / ambient / reflective
        ("https://ccmixter.org/content/oldDog/oldDog_-_too_quiet_(piano).mp3", "oldDog_-_too_quiet_piano.mp3"),
        ("https://ccmixter.org/content/zeos/zeos_-_Photo_theme_Window_like.mp3", "zeos_-_Photo_theme.mp3"),
        ("https://ccmixter.org/content/doxent/doxent_-_Forgotten_Land.mp3", "doxent_-_Forgotten_Land.mp3"),
    ],
}


def download(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 200_000:
        print(f"  [SKIP] {dest.name}")
        return True
    # Use curl — handles ccMixter's quirky cert chain + headers more permissively
    import subprocess
    try:
        result = subprocess.run([
            "curl", "-sSL", "-k", "--max-time", "120",
            "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "-e", "https://ccmixter.org/",
            "-o", str(dest), url,
        ], capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            print(f"  [FAIL] {dest.name}  curl rc={result.returncode}: {result.stderr.strip()[:200]}")
            dest.unlink(missing_ok=True)
            return False
        if not dest.exists() or dest.stat().st_size < 200_000:
            print(f"  [FAIL] {dest.name}  too small ({dest.stat().st_size if dest.exists() else 0} bytes)")
            dest.unlink(missing_ok=True)
            return False
        print(f"  [OK]   {dest.name}  {dest.stat().st_size // 1024} KB")
        return True
    except Exception as e:
        print(f"  [FAIL] {dest.name}  {e}")
        return False


def main() -> int:
    ok = 0
    total = 0
    for book, tracks in CURATED.items():
        print(f"\n=== {book} ===")
        out_dir = MUSIC / book
        out_dir.mkdir(parents=True, exist_ok=True)
        for url, name in tracks:
            total += 1
            if download(url, out_dir / name):
                ok += 1
    print(f"\n{ok}/{total} tracks downloaded.")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
