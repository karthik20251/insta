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
# 2026-06-04 SMM switch: female British voice (Sonia) chosen as the strategic
# differentiator. Motivation niche is ~95% male voices on IG/YT — a premium
# British female reads as "executive mentor woman giving you the unwritten
# rules of the boardroom." Distinctive + brand-aligned + still authoritative.
#
# Tested-good neural voices (Microsoft Edge endpoint, no auth needed):
#   en-GB-SoniaNeural         - British female, premium executive (default)
#   en-US-AvaMultilingualNeural - modern conversational US female
#   en-US-MichelleNeural      - US newscaster female, authoritative
#   en-IN-NeerjaNeural        - Indian English female
#   en-US-ChristopherNeural   - US newscaster male, authoritative
#   en-GB-RyanNeural          - British male, gravelly senior-mentor
#   en-IE-ConnorNeural        - Irish male, warm/storytelling (previous default)
DEFAULT_VOICE = os.environ.get("TTS_VOICE", "en-GB-SoniaNeural")

# Pitch modulation history (kept for context):
#   ±25Hz: read as THREE DIFFERENT PEOPLE (user feedback round 1)
#   ±10Hz: closer, but the -10Hz CTA still sounded "bit odd" (round 2)
#   +10Hz hook only: too high — user wanted deeper not higher (round 3)
# Final call: ALL segments at 0Hz. The voice swap (Christopher -> Andrew
# Multilingual) gives the deeper, more conversational delivery without
# pitch shifts that always sound processed. Same voice + uniform pitch =
# one person explaining, no AI tell.
_PITCH_HOOK = "+0Hz"
_PITCH_MIDDLE = "+0Hz"
_PITCH_CTA = "+0Hz"
# Rate calibrated empirically: at -5% a 27-word script of Item 4 landed 14.16s
# (we need ~12s for the video). -10% nets ~12s while still sounding natural —
# any faster (-15% / -20%) starts to feel rushed for an "authoritative senior"
# narrator and undercuts the brand. Combined with the tighter narration_script
# word cap, this lands narrations in the 11.5-12.5s sweet spot.
# 2026-06-04: rate moved from -10% -> +0% alongside the Connor -> Sonia voice
# switch. Sonia (British female) already carries natural gravitas through her
# RP cadence; slowing her -10% was adding drag without adding authority.
# Neutral +0% is the "less but impactful" pace the user asked for.
#
# 2026-06-07 CRITICAL FIX: was "0%" (no sign) for ~36 hours. edge-tts strictly
# requires the SSML rate format with an explicit sign — "0%" raises
# ValueError: Invalid rate '0%'. The synthesize exception was caught silently
# by build() so voice became None on every CI render -> music-only videos
# with NO voice and NO burned-in captions. User caught it ("Video hasn't the
# voice"). Must always be "+0%" / "-N%" / "+N%".
DEFAULT_RATE = os.environ.get("TTS_RATE", "+0%")


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


# 2026-06-05 SMM CRITICAL: previous CTAs had explicit "Follow now" and
# "Like if this stings" spoken aloud in the audio narration on the end
# frame. YT audio analysis detects spoken Follow/Like/Subscribe CTAs and
# downranks — and these were reading aloud on ~50% of videos (rotation
# by item index, 2 of 4 CTAs were bait). Spoken bait is arguably worse
# than visual: a viewer with sound on cannot miss it.
#
# Loss-aversion CTAs — rotated by item so 66 posts don't sound identical
# (the content-farm "every post ends the same" tell that throttles reach).
# Each is ~12-15 words, ~5-6 sec at neutral Sonia rate. Frames the cost
# of NOT acting (Cialdini-correct). All 4 drive save/share — the algo-
# rewarded signals — no explicit Follow/Like/Subscribe asks anywhere.
# 2026-06-13: CTAs tightened 12-15w -> 7-9w so the BODY can run in full.
# User feedback: content was getting truncated mid-sentence. Bodies are
# the story payoff; CTAs are the action call. Body must win the budget.
_LOSS_AVERSION_CTAS = [
    "Save this before your next 1:1.",                                   # 7w
    "Save this. The next reorg won't wait.",                             # 7w
    "Send this to the coworker who needs it.",                           # 8w
    "Save this for the meeting you'll have.",                            # 7w
]


def narration_script(day: dict) -> str:
    """Build a ~45-50 word script tuned for the ~19s video at 0% rate.

    2026-06-13: REMOVED headline from narration. User feedback "content
    not so acquirable" — having the headline voiced between tease and
    body broke the story flow ("She was the only one called back...
    They wanted her to quit. WHEN RTO MEANS GET OUT. Mandates target...").
    Headline still RENDERED on the main frame visually — but in voice
    it interrupted the narrative. Now narration flows:

      0-3s    tease (specific scene hook)
      3-12s   body (the story unfolds + lesson)
      12-16s  divisive question (drives comments)
      16-19s  loss-aversion CTA (drives saves)

    Removing the headline frees ~5 words of budget for body, so the
    body no longer gets truncated mid-thought.
    """
    tease = _strip_for_speech(day.get("tease", "")).rstrip(".")
    body = _strip_for_speech(day.get("body", ""))
    question = _strip_for_speech(day.get("comment_q", "")).rstrip("?") + "?"

    # Loss-aversion CTA rotates 1 of 4 by item index. All 4 drive save/
    # share signals — no Follow/Like asks after the bait cleanup.
    item_idx = int(day.get("item", 1))
    cta = _LOSS_AVERSION_CTAS[(item_idx - 1) % len(_LOSS_AVERSION_CTAS)]

    # Budget: 52 words total ≈ 22s at 0% rate. Preserve CTA + question +
    # tease IN FULL — body is elastic and absorbs the overflow. With
    # headline dropped, body usually fits in full (~17 words) without
    # needing first-sentence truncation.
    BUDGET = 52
    fixed_words = len((tease + " " + question + " " + cta).split())
    body_budget = max(5, BUDGET - fixed_words)
    body_clean = " ".join(body.split()[:body_budget]).rstrip(",;:")

    parts = [p for p in (tease, body_clean, question, cta) if p]
    return ". ".join(parts)


def _fmt_ts(seconds: float) -> str:
    """SRT timestamp: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def _write_srt(sentences: list[tuple[float, float, str]], srt_path: Path,
               max_words_per_phrase: int = 5) -> None:
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
        # Strip em-dashes for the CAPTION text only (audio still pauses at
        # them via TTS's natural prosody). Em-dashes in burned-in captions
        # read as broken layout — replace with a comma which is visually
        # clean and keeps the prosody hint for any future parser.
        sent_text = sent_text.replace(" — ", ", ").replace("—", ",")
        words = sent_text.split()
        if not words:
            continue
        # Split into phrases of <=max_words_per_phrase, breaking early on
        # punctuation so a comma/semicolon ends a phrase even mid-sentence.
        # Phrase break on commas/semicolons/colons OR at word-count cap.
        # Removed em-dash from break triggers: em-dashes inside narrated
        # headlines (e.g. "Make Other People Come to You — Use Bait if
        # Necessary") were creating orphan caption fragments like "to You —"
        # which look broken on a Short. Em-dash is a stylistic pause, not a
        # structural sentence break — let it ride within the phrase.
        # Min-words floor: don't emit a chunk with <2 words even on
        # punctuation (avoids "Hey." being a whole caption line by itself).
        chunks: list[list[str]] = []
        current: list[str] = []
        for w in words:
            current.append(w)
            ends_punctuation = w.rstrip().endswith((",", ";", ":"))
            should_break = (ends_punctuation and len(current) >= 2) or \
                           len(current) >= max_words_per_phrase
            if should_break:
                chunks.append(current)
                current = []
        if current:
            # Tail handling: if the tail is a single word/fragment, glue it
            # onto the previous chunk so we don't leave dangling 1-word caps.
            if len(current) == 1 and chunks:
                chunks[-1].extend(current)
            else:
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


def _ensure_silence_mp3(silence_path: Path, duration_sec: float = 1.0) -> Path:
    """Generate a silent MP3 of the requested duration, matching edge-tts's
    output format (24kHz mono 48kbps) so concat is lossless. Cached: only
    regenerates if missing or empty."""
    import subprocess
    if silence_path.exists() and silence_path.stat().st_size > 256:
        return silence_path
    silence_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"anullsrc=r=24000:cl=mono",
         "-t", str(duration_sec), "-c:a", "libmp3lame", "-b:a", "48k",
         str(silence_path)],
        capture_output=True, check=True,
    )
    return silence_path


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
    # 2026-06-13: dropped headline from voice (same change as narration_script).
    # User feedback: voiced headline broke the tease->body story flow. Headline
    # still RENDERED on the main frame visually. Middle segment now is body +
    # question — body fits in full because the headline word budget freed up.
    tease = _strip_for_speech(day.get("tease", "")).rstrip(".")
    body = _strip_for_speech(day.get("body", ""))
    question = _strip_for_speech(day.get("comment_q", "")).rstrip("?") + "?"

    item_idx = int(day.get("item", 1))
    cta = _LOSS_AVERSION_CTAS[(item_idx - 1) % len(_LOSS_AVERSION_CTAS)]

    BUDGET = 52
    fixed_words = len((tease + " " + question + " " + cta).split())
    body_budget = max(5, BUDGET - fixed_words)
    body_clean = " ".join(body.split()[:body_budget]).rstrip(",;:")

    middle_parts = [p for p in (body_clean, question) if p]
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

    # 0.4-second silence between segments. 2026-06-04 tightened from 1.0s:
    # 1s read as draggy on a 22s Short. 0.4s still lets each segment land
    # but moves the video forward. 2 gaps x 0.6s shaved = 1.2s shorter video
    # per render, which materially boosts completion-rate on a 22s base.
    # The silence_path includes the duration so a stale cache from the old
    # 1s setting can't shadow the new shorter file.
    SEGMENT_GAP = 0.4
    silence_path = out_path.parent / f"_silence_{int(SEGMENT_GAP * 1000)}ms.mp3"
    _ensure_silence_mp3(silence_path, SEGMENT_GAP)

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
            # Account for the silence gap that will be inserted AFTER this
            # segment in the concat (except after the final segment) — keeps
            # SRT caption timings aligned with the gapped audio.
            if i < len(segments) - 1:
                cumulative += SEGMENT_GAP
            tmp_mp3s.append(tmp)

        # Interleave silence between segments: [seg0, silence, seg1, silence, seg2]
        audio_inputs: list[Path] = []
        for i, p in enumerate(tmp_mp3s):
            if i > 0:
                audio_inputs.append(silence_path)
            audio_inputs.append(p)
        _concat_mp3s(audio_inputs, out_path)

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
