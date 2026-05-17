"""One-off: vendor the exact Twemoji PNGs the corpus renders.

Run by a human (network required); the resulting assets/twemoji/*.png is
committed and becomes the git-frozen pin. NOT run in the cron.

Why this guarantees pixel-identity:
  - emoji SET = exactly what pilmoji will request, because we extract it with
    pilmoji's own parser (`to_nodes`), not a hand-rolled regex.
  - emoji BYTES = exactly what the live CDN path returns, because we fetch via
    pilmoji's own `Twemoji().get_emoji` (same method the renderer calls).
  - stored under `emoji_key`, the same key `LocalTwemoji` reads back.

Usage:
    .\\.venv\\Scripts\\python.exe scripts\\vendor_twemoji.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pilmoji.helpers import NodeType, to_nodes
from pilmoji.source import Twemoji

from twemoji_local import ASSET_DIR, emoji_key

ROOT = Path(__file__).parent.parent
QUOTES = ROOT / "quotes.json"

# Emojis hardcoded in generate.py (_book_top_label) — not in quotes.json text.
EXTRA = ["⚔️", "\U0001f331", "⚖️", "\U0001f4d6"]  # ⚔️ 🌱 ⚖️ 📖


def collect_emojis() -> list[str]:
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    strings: list[str] = []

    def walk(o):
        if isinstance(o, str):
            strings.append(o)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(data)
    strings.extend(EXTRA)

    found: set[str] = set()
    for s in strings:
        for line in to_nodes(s):
            for node in line:
                if node.type is NodeType.emoji:
                    found.add(node.content)
    return sorted(found)


def main() -> int:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    emojis = collect_emojis()
    print(f"Corpus uses {len(emojis)} distinct emoji. Vendoring to {ASSET_DIR} ...")
    src = Twemoji()
    ok = miss = 0
    missing: list[str] = []
    for e in emojis:
        dest = ASSET_DIR / f"{emoji_key(e)}.png"
        if dest.is_file():
            ok += 1
            continue
        try:
            bio = src.get_emoji(e)
        except Exception as ex:  # noqa: BLE001 — vendor-time diagnostics
            print(f"  ERR  {emoji_key(e)}: {ex!r}")
            missing.append(e)
            miss += 1
            continue
        if bio is None:
            print(f"  MISS {emoji_key(e)}: CDN returned None")
            missing.append(e)
            miss += 1
            continue
        dest.write_bytes(bio.getvalue())
        ok += 1

    print(f"\nDone: {ok} present/vendored, {miss} missing.")
    if missing:
        print("Missing (render will CDN-fallback, then omit glyph if CDN down):")
        for e in missing:
            print(f"  {emoji_key(e)}")
    return 1 if miss else 0


if __name__ == "__main__":
    sys.exit(main())
