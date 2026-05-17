"""Local-first Twemoji source for pilmoji + crash-proof emoji helpers.

Removes the live `emojicdn.elk.sh` single-point-of-failure from the render
critical path. Emoji PNGs are vendored into `assets/twemoji/` (committed —
git-frozen bytes ARE the version pin: the render path reads local first, so
emojicdn changing "latest" can never silently move a rendered frame
mid-experiment). The CDN remains only as a fallback for an un-vendored glyph,
and even a total CDN failure can no longer raise: `get_emoji` returns None,
and pilmoji then simply omits that one glyph while the text still renders.

Pixel-identity contract: the vendoring script fetches via pilmoji's own
`Twemoji().get_emoji` (the exact bytes the live CDN path returns) and stores
them under `emoji_key`. This source reads those exact bytes back under the
same key, so the normal path is byte-identical to the pre-patch CDN render.
"""
from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from pilmoji.source import Twemoji

ASSET_DIR = Path(__file__).parent / "assets" / "twemoji"


def emoji_key(emoji: str) -> str:
    """Stable filename stem for an emoji string. The convention is internal;
    it only has to match between `scripts/vendor_twemoji.py` and this source."""
    return "-".join(f"{ord(c):x}" for c in emoji)


class LocalTwemoji(Twemoji):
    """Twemoji, but local assets first; CDN only as a non-raising fallback."""

    def get_emoji(self, emoji: str, /) -> BytesIO | None:
        local = ASSET_DIR / f"{emoji_key(emoji)}.png"
        if local.is_file():
            return BytesIO(local.read_bytes())
        try:
            # Un-vendored glyph: degrade to CDN, but never raise on the
            # render critical path (the whole point of this module).
            return super().get_emoji(emoji)
        except Exception:
            return None


# Broad emoji / variation-selector / ZWJ / keycap stripper, used ONLY by the
# last-resort text-only fallback in render_intro_frame (if Pilmoji itself
# fails entirely, not just one glyph fetch).
_EMOJI_STRIP = re.compile(
    "["
    "\U0001F000-\U0001FAFF"   # symbols & pictographs, supplemental, extended-A
    "\U00002600-\U000027BF"   # misc symbols + dingbats
    "\U0001F1E6-\U0001F1FF"   # regional indicators (flags)
    "\U00002190-\U000021FF"   # arrows
    "\U00002B00-\U00002BFF"   # misc symbols & arrows
    "\U0000FE00-\U0000FE0F"   # variation selectors
    "\U0000200D"              # zero-width joiner
    "\U000020E3"              # combining enclosing keycap
    "]+",
    flags=re.UNICODE,
)


def strip_emoji(text: str) -> str:
    """Remove emoji so plain ImageDraw.text can render the words alone."""
    return re.sub(r"\s{2,}", " ", _EMOJI_STRIP.sub("", text)).strip()
