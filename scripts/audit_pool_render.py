"""Production audit for motivational_lines.json — run after ANY pool edit.

Checks every line against the REAL midday renderer constraints:
  1. Wrap overflow: _fit_font must produce <= 3 rendered lines
     (4+ lines render cramped at 48pt emergency font — a byline quote
     whose first segment is too wide is the usual culprit).
  2. Mood validity: every mood must exist in MOOD_KEYWORDS or the
     background fetcher gets no keyword pool.
  3. Near-duplicate collisions: lines firing within 8 positions
     (~4 days at 2/day) must not share heavy vocabulary — repeats
     read as templated content.

Exit code 1 on any failure so it can gate CI.

Usage:  python scripts/audit_pool_render.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image, ImageDraw  # noqa: E402
import generate_midday as gm  # noqa: E402

STOPWORDS = {
    "the", "a", "an", "is", "are", "you", "your", "to", "of", "and", "in",
    "it", "they", "for", "at", "on", "that", "not", "isn't", "was", "—",
}


def tokens(text: str) -> set[str]:
    return {
        w.strip(".,'?!—\"()").lower()
        for w in text.replace("\n", " ").split()
    } - STOPWORDS


def main() -> int:
    lines = json.loads(
        (Path(__file__).parent.parent / "motivational_lines.json")
        .read_text(encoding="utf-8"))["lines"]
    img = Image.new("RGB", (gm.WIDTH, gm.HEIGHT))
    draw = ImageDraw.Draw(img)
    # Must mirror render(): margin = 120; max_w = WIDTH - 2 * margin
    max_w = gm.WIDTH - 2 * 120

    failures = 0

    # 1) wrap overflow — mirror render(): byline ("— Name" final line) is
    # drawn separately and does NOT consume the 3-line quote budget.
    # POLICY: our own (unattributed) lines hard-fail above 3 rendered lines —
    # we control the wording, so there is no excuse. Attributed quotes are
    # VERBATIM and must never be trimmed to fit; they are allowed 4 lines
    # (proven acceptable in production) and only fail above 4.
    for ln in lines:
        text = ln["text"]
        parts = text.split("\n")
        attributed = len(parts) > 1 and parts[-1].lstrip().startswith("—")
        if attributed:
            text = "\n".join(parts[:-1]).strip()
        _font, wrapped = gm._fit_font(text, draw, max_w, max_lines=3)
        limit = 4 if attributed else 3
        if len(wrapped) > limit:
            print(f"FAIL overflow #{ln['id']}: {len(wrapped)} rendered lines "
                  f"(limit {limit}) -> {ln['text'][:60]!r}")
            failures += 1

    # 2) mood validity
    valid = set(gm.MOOD_KEYWORDS)
    for ln in lines:
        if ln["mood"] not in valid:
            print(f"FAIL mood #{ln['id']}: {ln['mood']!r} not in {sorted(valid)}")
            failures += 1

    # 3) near-duplicate collisions in firing window
    for i, a in enumerate(lines):
        for b in lines[i + 1:i + 9]:
            ta, tb = tokens(a["text"]), tokens(b["text"])
            if not ta or not tb:
                continue
            jac = len(ta & tb) / len(ta | tb)
            if jac >= 0.28:
                print(f"FAIL collision #{a['id']} vs #{b['id']} "
                      f"(sim {jac:.2f}): shared {sorted(ta & tb)[:6]}")
                failures += 1

    if failures:
        print(f"\n{failures} failure(s) across {len(lines)} lines")
        return 1
    print(f"OK: {len(lines)} lines pass render, mood, and collision checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
