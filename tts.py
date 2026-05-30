"""AI voice narration for the Reels pipeline (Microsoft Edge TTS — free, no API key).

Why this exists: faceless quote-card Reels in saturated niches cap at ~150 views
with ~0 engagement. The bottleneck is parasocial connection, and a consistent
narrator voice is the cheapest, most automatable way to create it without a
face. This module turns each item's text into spoken narration; generate.py
mixes that narration over the background music.

Voice is configurable so a paid upgrade (OpenAI 'onyx' / ElevenLabs) is a
one-file swap later. Default is the best free option that requires no signup.

Design rules (consistent with the rest of the pipeline):
  - Fails open: if TTS errors (network blip, rate limit, anything), return None.
    generate.make_video must fall back to music-only and continue. Never crash a
    post for a missing voiceover.
  - Idempotent: if the target mp3 already exists and non-empty, skip.
  - No emoji in the spoken text — they read out loud as garbage. Strip first.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

# Default = best free voice with no API key. Override via TTS_VOICE env var.
# Tested-good neural voices (Microsoft Edge endpoint, no auth needed):
#   en-US-ChristopherNeural  - newscaster male, authoritative  (default)
#   en-US-GuyNeural          - warmer male
#   en-GB-RyanNeural         - British, gravelly senior-mentor
#   en-IN-PrabhatNeural      - Indian English male
DEFAULT_VOICE = os.environ.get("TTS_VOICE", "en-US-ChristopherNeural")

# Pitch modulation across the narration — same voice, three energies:
#   HOOK (start): slightly higher pitch → excited, attention-grabbing
#   MIDDLE:       neutral pitch → content delivery, authority
#   CTA (close):  slightly lower pitch → deep, dramatic, drives action
# Classic narrator technique (news anchors, podcasters): vary energy through
# a segment so the listener never settles into background-mode. Single voice
# keeps the brand consistent; pitch alone does the variety work.
#
# Pitch range calibrated empirically:
#   ±25Hz: read as THREE DIFFERENT PEOPLE (user feedback round 1)
#   ±10Hz: closer, but the -10Hz CTA still sounded "bit odd" (user round 2)
# Pitch DOWN on TTS produces more artifacts than pitch UP — the human voice
# naturally lifts in pitch when excited but doesn't drop in linear Hz when
# settling (it lowers via slower rate + weighted emphasis, not pure pitch).
# So: keep a small +10Hz hook lift, but leave both MIDDLE and CTA at 0Hz so
# the CTA returns cleanly to the narrator's natural register.
_PITCH_HOOK = "+10Hz"
_PITCH_MIDDLE = "+0Hz"
_PITCH_CTA = "+0Hz"
# Rate calibrated empirically: at -5% a 27-word script of Item 4 landed 14.16s
# (we need ~12s for the video). -10% nets ~12s while still sounding natural —
# any faster (-15% / -20%) starts to feel rushed for an "authoritative senior"
# narrator and undercuts the brand. Combined with the tighter narration_script
# word cap, this lands narrations in the 11.5-12.5s sweet spot.
DEFAULT_RATE = os.environ.get("TTS_RATE", "-10%")


def _strip_for_speech(text: str) -> str:
    """Remove emoji + decorative chars so they don't get read aloud as garbage
    ('downwards black arrow', 'crossed swords', etc). Keep punctuation —
    commas/periods drive natural prosody."""
    try:
        from twemoji_local import strip_emoji
        text = strip_emoji(text)
    except Exception:
        # twemoji_local should always be present, but if not: brute-strip via
        # the same emoji set used by pilmoji. Better to skip emojis than crash.
        try:
            import emoji  # type: ignore
            text = emoji.replace_emoji(text, replace="")
        except Exception:
            pass
    # Remove any stray non-ASCII that survived (rare ornaments, ZWJ remnants)
    # while keeping the en-dash, em-dash, curly quotes which read fine.
    keep = set("–—’‘“”·")
    cleaned = "".join(ch for ch in text if ch.isascii() or ch in keep)
    return " ".join(cleaned.split())


# Loss-aversion CTAs — rotated by item, so 276 posts don't sound identical
# (the content-farm "every post ends the same" tell that throttles reach).
# Each is ~12-15 words, ~5-6 sec at -10% rate. Frames the cost of NOT acting,
# never the benefit of acting — Cialdini-correct, the strongest CTA mode.
_LOSS_AVERSION_CTAS = [
    # SAVE — fear of needing it later
    "Save this before your next one-on-one. Or be the one who needed it, and forgot.",
    # FOLLOW — fear of falling behind a peer
    "Follow now. The next move drops tomorrow. Don't watch someone else get there first.",
    # SHARE — fear of a colleague stumbling
    "Send this to the coworker who's about to learn this the hard way.",
    # LIKE + COMMENT — fear of being the quiet one who doesn't engage
    "Like if this stings. Comment your move. The quiet ones get left behind.",
]


def narration_script(day: dict) -> str:
    """Build a ~45-50 word script tuned for the 22s video at the -10% rate:
    tease (hook) -> headline (the law) -> one-sentence body -> divisive
    question (drives comments) -> ONE rotating loss-aversion CTA (drives
    save/follow/share/like).

    Time landing target:
      0-3s   tease (hook)
      3-10s  headline + body
      10-17s comment question
      17-22s loss-aversion CTA

    The CTA rotates by item index so consecutive posts don't repeat the same
    line — variety prevents the "this is a bot" sniff that kills reach.
    """
    tease = _strip_for_speech(day.get("tease", "")).rstrip(".")
    headline = _strip_for_speech(day.get("headline", "")).rstrip(".")
    body = _strip_for_speech(day.get("body", ""))
    question = _strip_for_speech(day.get("comment_q", "")).rstrip("?") + "?"
    body_first = body.split(".", 1)[0].strip()

    # Loss-aversion CTA rotates 1 of 4 by item index (covers save/follow/
    # share/like+comment across 4 consecutive posts).
    item_idx = int(day.get("item", 1))
    cta = _LOSS_AVERSION_CTAS[(item_idx - 1) % len(_LOSS_AVERSION_CTAS)]

    # Budget: 52 words total ≈ 22s at -10%. Preserve CTA + question + tease +
    # headline IN FULL (they're load-bearing for engagement). The body is the
    # only variable-length elastic — it absorbs the overflow. This protects
    # the CTA from getting mid-word-cut (item 7's "Never Put Too Much Trust
    # in Friends..." headline used to chop the CTA's final word).
    BUDGET = 52
    fixed_words = len((tease + " " + headline + " " + question + " " + cta).split())
    body_budget = max(3, BUDGET - fixed_words)
    body_first = " ".join(body_first.split()[:body_budget]).rstrip(",;:")

    parts = [p for p in (tease, headline, body_first, question, cta) if p]
    return ". ".join(parts)


def _fmt_ts(seconds: float) -> str:
    """SRT timestamp: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def _write_srt(sentences: list[tuple[float, float, str]], srt_path: Path,
               max_words_per_phrase: int = 4) -> None:
    """Group sentence-boundary events into readable phrases, write SRT.

    edge-tts 7.x emits SentenceBoundary (not WordBoundary by default), so we
    take each sentence's [start, duration, text], split the text into ~4-word
    phrases at punctuation or word count, and DISTRIBUTE the sentence's time
    across its phrases by word-count proportion. Result: captions land in
    sync with the spoken sentence's pace, even though we don't have per-word
    timing. 3-4 words per phrase is the readability sweet spot for vertical-
    video captions — coherent thought, glance-readable, no overflow.
    """
    if not sentences:
        return

    phrases_with_time: list[tuple[float, float, str]] = []
    for sent_start, sent_dur, sent_text in sentences:
        words = sent_text.split()
        if not words:
            continue
        # Split into phrases of <=max_words_per_phrase, breaking early on
        # punctuation so a comma/semicolon ends a phrase even mid-sentence.
        chunks: list[list[str]] = []
        current: list[str] = []
        for w in words:
            current.append(w)
            ends_punctuation = w.rstrip().endswith((",", ";", ":", "—"))
            if ends_punctuation or len(current) >= max_words_per_phrase:
                chunks.append(current)
                current = []
        if current:
            chunks.append(current)
        # Distribute the sentence's audio time by word-count proportion.
        total_words = sum(len(c) for c in chunks)
        cursor = sent_start
        for c in chunks:
            share = len(c) / total_words
            chunk_dur = share * sent_dur
            phrases_with_time.append((cursor, chunk_dur, " ".join(c)))
            cursor += chunk_dur

    lines: list[str] = []
    for i, (start, dur, text) in enumerate(phrases_with_time, 1):
        # End extends to the next phrase's start (no flicker gap), with a
        # short tail for the final phrase.
        if i < len(phrases_with_time):
            end = phrases_with_time[i][0]
        else:
            end = start + dur + 0.4
        lines.append(f"{i}\n{_fmt_ts(start)} --> {_fmt_ts(end)}\n{text}\n")
    srt_path.write_text("\n".join(lines), encoding="utf-8")


async def _synthesize_async(text: str, out_path: Path, srt_path: Path | None,
                            voice: str, rate: str, pitch: str = "+0Hz") -> None:
    """Stream synthesis so we can capture BOTH audio chunks AND timing events
    in one pass. Audio writes to out_path; sentence timings (if srt_path is
    provided) get split into ~4-word phrases and written as a burnable SRT.
    edge-tts 7.x emits SentenceBoundary; older docs reference WordBoundary
    which is not emitted by this version — we capture either if seen.
    `pitch` shifts the voice frequency (e.g. '+25Hz' = excited, '-25Hz' =
    deep) without changing rate — used by the 3-segment pitched pipeline."""
    import edge_tts
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    sentences: list[tuple[float, float, str]] = []
    TICKS_PER_SEC = 10_000_000
    with open(out_path, "wb") as audio_f:
        async for chunk in communicate.stream():
            t = chunk.get("type")
            if t == "audio":
                audio_f.write(chunk["data"])
            elif t in ("SentenceBoundary", "WordBoundary") and srt_path is not None:
                off = chunk["offset"] / TICKS_PER_SEC
                dur = chunk["duration"] / TICKS_PER_SEC
                sentences.append((off, dur, chunk["text"]))
    if srt_path is not None and sentences:
        _write_srt(sentences, srt_path)


async def _synthesize_segment_async(
    text: str, out_path: Path, voice: str, rate: str, pitch: str
) -> list[tuple[float, float, str]]:
    """Stream one pitched segment, return the timing events for SRT merging.
    Caller is responsible for combining events from multiple segments with
    cumulative-time offsets."""
    import edge_tts
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    events: list[tuple[float, float, str]] = []
    TICKS_PER_SEC = 10_000_000
    with open(out_path, "wb") as audio_f:
        async for chunk in communicate.stream():
            t = chunk.get("type")
            if t == "audio":
                audio_f.write(chunk["data"])
            elif t in ("SentenceBoundary", "WordBoundary"):
                off = chunk["offset"] / TICKS_PER_SEC
                dur = chunk["duration"] / TICKS_PER_SEC
                events.append((off, dur, chunk["text"]))
    return events


def _mp3_duration(mp3_path: Path) -> float:
    """Get an MP3's duration via ffprobe (used to compute caption-time offsets
    between concatenated segments)."""
    import subprocess
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(mp3_path)],
        capture_output=True, text=True, check=True
    )
    return float(r.stdout.strip())


def _concat_mp3s(input_paths: list[Path], out_path: Path) -> None:
    """Concatenate MP3 files lossless via ffmpeg's concat demuxer. All inputs
    must share codec/sample-rate (edge-tts output does)."""
    import subprocess
    list_file = out_path.parent / f"_concat_{out_path.stem}.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in input_paths:
            f.write(f"file '{p.name}'\n")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", list_file.name, "-c", "copy", out_path.name],
            cwd=str(out_path.parent),
            capture_output=True, check=True
        )
    finally:
        try: list_file.unlink()
        except FileNotFoundError: pass


def narration_segments(day: dict) -> list[tuple[str, str]]:
    """Split the narration into 3 pitch-modulated segments.

    Returns: [(text, pitch), ...] in playback order.
      seg 1 = HOOK   (high pitch +25Hz): the tease
      seg 2 = MIDDLE (neutral 0Hz):      headline + body + question
      seg 3 = CTA    (deep -25Hz):       loss-aversion close

    Same content split as narration_script(), same word-budget enforcement
    (CTA + question preserved, body trims to fit). Only the delivery changes:
    pitch shifts per segment so the narrator's energy modulates through the
    video — excited opening → measured middle → grave authoritative close.
    """
    tease = _strip_for_speech(day.get("tease", "")).rstrip(".")
    headline = _strip_for_speech(day.get("headline", "")).rstrip(".")
    body = _strip_for_speech(day.get("body", ""))
    question = _strip_for_speech(day.get("comment_q", "")).rstrip("?") + "?"
    body_first = body.split(".", 1)[0].strip()

    item_idx = int(day.get("item", 1))
    cta = _LOSS_AVERSION_CTAS[(item_idx - 1) % len(_LOSS_AVERSION_CTAS)]

    BUDGET = 52
    fixed_words = len((tease + " " + headline + " " + question + " " + cta).split())
    body_budget = max(3, BUDGET - fixed_words)
    body_first = " ".join(body_first.split()[:body_budget]).rstrip(",;:")

    middle_parts = [p for p in (headline, body_first, question) if p]
    return [
        (tease + ".", _PITCH_HOOK),
        (". ".join(middle_parts), _PITCH_MIDDLE),
        (cta, _PITCH_CTA),
    ]


def synthesize_pitched(day: dict, out_path: Path, srt_path: Path | None = None,
                      voice: str = DEFAULT_VOICE,
                      rate: str = DEFAULT_RATE) -> Path | None:
    """Synthesize the 3-segment pitch-modulated narration as a single audio
    file + merged SRT. Returns audio path on success, None on failure (caller
    falls back to music-only, same pattern as synthesize())."""
    audio_ok = out_path.exists() and out_path.stat().st_size > 256
    srt_ok = srt_path is None or (srt_path.exists() and srt_path.stat().st_size > 16)
    if audio_ok and srt_ok:
        return out_path

    segments = narration_segments(day)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_mp3s: list[Path] = []
    all_events: list[tuple[float, float, str]] = []
    cumulative = 0.0

    try:
        for i, (text, pitch) in enumerate(segments):
            if not text.strip():
                continue
            tmp = out_path.parent / f"_tmp_seg{i}_{out_path.stem}.mp3"
            seg_events = asyncio.run(
                _synthesize_segment_async(text, tmp, voice, rate, pitch))
            seg_dur = _mp3_duration(tmp)
            for off, dur, t in seg_events:
                all_events.append((off + cumulative, dur, t))
            cumulative += seg_dur
            tmp_mp3s.append(tmp)

        _concat_mp3s(tmp_mp3s, out_path)

        if srt_path is not None and all_events:
            _write_srt(all_events, srt_path)
    except Exception as e:
        print(f"!! TTS_FALLBACK_FIRED day={day.get('day')} err={type(e).__name__}: {e}")
        gh_out = os.environ.get("GITHUB_OUTPUT")
        if gh_out:
            try:
                with open(gh_out, "a", encoding="utf-8") as f:
                    f.write("tts_fallback=true\n")
            except Exception:
                pass
        for p in tmp_mp3s:
            try: p.unlink()
            except FileNotFoundError: pass
        return None

    for p in tmp_mp3s:
        try: p.unlink()
        except FileNotFoundError: pass

    return out_path if (out_path.exists() and out_path.stat().st_size > 256) else None


def synthesize(text: str, out_path: Path, srt_path: Path | None = None,
               voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE) -> Path | None:
    """Synthesize `text` to `out_path` (an .mp3). If `srt_path` is given, also
    write a phrase-grouped SRT subtitle file synced to the audio. Returns the
    audio path on success, None on any failure (caller falls back to music-only).

    Idempotent: if BOTH the audio and (if requested) the SRT already exist
    non-empty, reuse them — keeps the renderer fast on rebuilds.
    """
    if not text or not text.strip():
        return None
    audio_ok = out_path.exists() and out_path.stat().st_size > 256
    srt_ok = srt_path is None or (srt_path.exists() and srt_path.stat().st_size > 16)
    if audio_ok and srt_ok:
        return out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        asyncio.run(_synthesize_async(text.strip(), out_path, srt_path, voice, rate))
    except Exception as e:
        # Loud, grep-able marker so a tts-fallback day is detectable and can
        # be excluded from attribution (same pattern as PILMOJI_FALLBACK_FIRED).
        print(f"!! TTS_FALLBACK_FIRED text={text[:60]!r} err={type(e).__name__}: {e}")
        gh_out = os.environ.get("GITHUB_OUTPUT")
        if gh_out:
            try:
                with open(gh_out, "a", encoding="utf-8") as f:
                    f.write("tts_fallback=true\n")
            except Exception:
                pass
        if out_path.exists() and out_path.stat().st_size <= 256:
            try:
                out_path.unlink()
            except Exception:
                pass
        return None
    if not (out_path.exists() and out_path.stat().st_size > 256):
        return None
    return out_path
