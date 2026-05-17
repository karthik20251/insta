# First-Frame Hook Test — staged spec (ship at Day 11 post)

Status: **STAGED, not shipped.** No render/post pipeline changes until the Day 11 post.
This document is the single source of truth for the next intervention. It is written
to be executed by a fresh context — every code location, value, and decision rule is
explicit. Do not "improve" beyond what is written here; scope creep is the failure
mode this whole test exists to correct.

---

## 0. Why this test exists (one paragraph, no re-derivation)

Diagnosis converged from two independent instruments: (a) cross-platform divergence —
identical videos lost ~19% on IG vs ~11% on YT in the tease era, isolating a
first-frame/surface mechanic; (b) YouTube retention on Law 4 (best post, matured 7d,
N=1 but corroborated): **31.8% stayed to watch, 68.3% swiped away**, monotonic
retention decline, **no payoff spike anywhere**. Traffic source 90.5% Shorts feed /
85.7% new / ~0 external — distribution works, junk-traffic / shadowban / bot branches
are eliminated. The machine delivers fresh humans to the door; ~2 of 3 take one look
and leave. **It is a hook problem, not a reach problem.** Mechanic confirmed in code:
all frames share one scrim (`make_background`, 62% black center → 84% edges); the old
format's bold headline dominates at grid/feed scale, the sparse tease frame does not —
it reads as a near-black box. Frame-0 verification (see §5) confirms this frame IS the
cover/hook on both surfaces.

## 1. The single variable

**Visual contrast / text-mass of the first frame (= IG grid cover = YT Shorts hook).**
Exactly one lever moves. See the anti-confound contract — it is the point of this test.

## 2. Anti-confound contract — DO NOT TOUCH

- **Tease copy: byte-identical.** Same words, same emoji, same `quotes.json`.
  Including "wait for it" / "stay for it". (See §7 — this is a *conscious* sequencing
  choice, not an oversight. Copy is the **next** test.)
- **Length:** 12s. `DURATION_SEC` + the 2/4/4/2 split unchanged.
- **Main / example / end frames:** unchanged. They keep the standard scrim. They are
  not the hook.
- **Music, hashtags, caption text, posting time, CTA/end-frame:** unchanged.
- **YouTube path:** no code change. Same video → same first frame fixes the YT hook
  for free. We *measure* YT; we don't *modify* it.

Result: if anything moves, it is contrast. One lever, attributable result.

## 3. The change (precise diff — apply at Day 11, not before)

**Empirical reweighting (from the live-cover inspection in §5):** the old Day 1 cover
works despite the SAME crushed-dark painting — its win is **bright text-mass** (huge
bold headline + gold rule + full body paragraph fills the frame), not background
reveal. The tease frame is sparse by design (one hook line). Therefore **scrim-
lightening alone (3a) will under-deliver** — revealing a crushed painting behind one
thin line still reads dark. The dominant sub-lever is maximizing **bright text-mass /
text contrast on the tease frame itself** (3b/3d). 3a stays in the treatment but is
now the weaker sub-lever, not the workhorse. This remains ONE variable: "visual
contrast of the first frame" is a single coherent treatment (the user defined it as
"large bold text, visible artwork, gold accent"). Sub-levers ship together as one
intervention. Copy stays byte-identical (§2) — bigger/bolder is the *same words* with
more contrast, not a copy or structure change; that is still the single variable.

**Named caveat (chosen eyes-open, not smuggled):** {bigger, bolder, more text-mass,
brighter scrim} is one construct — *thumbnail visual weight* — with copy held
byte-identical. At the attribution level §4 measures (IG views, Days 11–15) this is
legitimately one variable. But a positive result tells us only "high-visual-weight
thumbnail beats sparse"; it will NOT separate size vs. weight vs. wrap vs. scrim
within that construct. This is acceptable because those are facets of one lever, not
the copy/contrast/structure conflation we repeatedly made — but it is accepted
knowingly. If a future test needs to decompose visual-weight into its facets, that is
a separate, later, single-variable test, not something this test can retroactively
answer.

All edits in `generate.py`.

**3a. Add an opt-in lighter scrim — do NOT edit the global default.**
`make_background(day_num, book="", scrim="standard")`:
- `standard` → `base_dark 0.62 / edge_dark 0.22` (current values — main/example/end keep this)
- `bright`   → `base_dark 0.32 / edge_dark 0.14` (intro frame only)

`render_intro_frame` (~line 266) calls `make_background(..., scrim="bright")`.

**3b. Local legibility panel (MANDATORY — a bright bg kills white-text contrast).**
Behind the wrapped tease block only, composite a soft dark panel: vertical-gradient
or rounded-rect, ~55% black, ~40px padding around the tease lines. Net: bright frame
globally, text locally protected. This is "bright thumbnail, readable copy" — it is a
contrast device, **not** a copy or layout change.

**3c. Gold accent.** 6px gold rule (`GOLD = (212,175,55)`) full text-width under the
top label. NOTE (non-blocking, see §8): at 320px grid scale + JPEG this is ~1.7px —
keep it, it doesn't hurt, but it is **not** the workhorse. The brightened scrim +
protected text-mass do the work.

**3d. Text-mass — the workhorse (revised per §3 empirical reweighting).** The tease
must fill more of the frame with bright pixels, like the old headline did. Increase
tease size (e.g., 76→96px, 64→80px for the 3+-line case) AND weight 700→800 if the
face exists. Size increase here is NOT a layout confound: copy is byte-identical
(§2), so this is the *same words* rendered with more contrast — that is precisely the
single variable. Keep proportional wrap logic; just larger. Center mass vertically so
the frame reads as a full card, not a thin line on black.

## 4. Success metric & PRE-REGISTERED decision rule

**Primary instrument: IG reach/views over Days 11–15 (5 posts).** The intervention is
a static-frame contrast change; its causal path is the **IG pre-play grid tap** — a
decision on a still image. That mechanism runs through IG views, so IG views is the
mechanistically-correct primary metric. Its noise (identical-format posts swung
123→293) is beaten the honest way: **more data points (5 posts, Days 11–15), not by
switching to a cleaner-but-causally-irrelevant instrument.** Earlier drafts made YT
retention primary — that was a metric-design error: YT Shorts autoplays, frame-0
contrast barely gates a moving-video stay decision, so its causal path does not run
through this intervention.

- **Baseline:** Days 6–8 matured IG views, the ~122 band (Days 9–10 confirm it).
- **Decision (judge Days 11–15, 5 posts, each matured ~5–7d):**
  - **5-post IG mean climbs off ~122 toward ≥150** → contrast was the bleed. Lock the
    high-contrast tease frame. Next test: engagement (the real disease — §6).
  - **5-post IG mean stays ~122** → contrast was NOT it → tease **copy** is
    implicated → next single-variable test is copy (instant-value vs. deferral),
    thumbnail held at the new high-contrast treatment.
- **Secondary corroborator (weak, not the verdict):** YT "stayed to watch" drifting
  off Law 4's 31.8% — *only* its swipe component, *only* if it moves at all. A
  black-vs-bright opening still nudges the YT split-second stay slightly, so it is a
  weak supporting signal, not noise — but it does not decide anything.
  Length note: avg-view-% and curve shape are length-dependent (24s Law 4 vs 12s
  posts) and are NOT comparable; only the length-independent swipe component is even
  a weak read.

## 5. Frame-0 verification — DONE, EMPIRICALLY (this is the linchpin; it passed)

Not asserted from API docs — proven with live production data. Pulled
`thumbnail_url` from the Graph API for two posts and inspected the actual published
covers (`scripts/_probe_cover.py`, since deleted):
- **Tease Day 5 (May 13) live cover** = the tease frame verbatim ("The 1 silence
  that gets you a higher salary 💰 wait for it"). Frame 0. NOT an auto-selected
  mid-video frame.
- **Old Day 1 (May 9) live cover** = the headline frame (frame 0 in the old format).

Reconfirmed on a second requested pair: **Law 4 (tease, May 13)** served cover = the
tease frame verbatim; **Law 2 (old-format, May 11)** served cover = the headline
frame. Both = frame 0, both clean (no leader / no xfade blend; xfade is at 1.5s).

Code side independently traced GREEN: `main.py` → `post_reel(video_url, caption)` →
`_create_and_publish` payload has no `cover_url`/`thumb_offset`. We send no override.

Both residuals closed by served pixels: (1) IG ML "representative-frame" re-pick —
refuted (tease post serves the sparse tease, not the richer mid-video headline);
(2) encode leader / xfade at ms 0 — refuted (served frame is the clean designed
frame). → **the first frame IS the IG grid cover.** Confidence: empirical/high.
Distinct tease-era N=1 (Law 4) but `render_intro_frame` is deterministic across all
tease days, so this is definitive, not thin. Residual: manual in-app cover edit (bot
never does this). **Spec targets the correct surface — no rework. GATE CLOSED.**

**The Day 5 live cover also confirms the diagnosis directly:** it is a near-total
black field with thin floating text — the "black box at grid scale" is real and
visible in production, not inferred from view counts. See §3 refinement.

## 6. Affirmed, out of scope for THIS test (named so we don't bundle)

- **Zero-engagement / dead CTA** (0 comments every post, both platforms): the real
  long-game threat. No hook fix touches it. It is the **next** test after this one,
  and it is a content fix, not a render fix.
- **`like_and_views_counts_disabled: "true"`** in `post.py:post_reel` — every Reel
  publishes with counts hidden. Plausible social-proof suppressor of engagement.
  Strong candidate for the engagement test. **Observation only — do not change now.**
- **YouTube is the stronger surface** (~1.5–2× IG reach, on less maturation). Worth
  weighting future effort there. Strategic note, not an action here.

## 7. Conscious tradeoff (chosen, not backed into)

The retention curve already hinted "wait for it" (copy) is part of the problem — on a
swipe feed, telling a stranger to wait tells them to leave. We are still testing
**contrast first, copy second**. This is a deliberate choice to prioritize
methodological cleanliness (one attributable variable) over speed, made with eyes
open: **if Days 11–13 stay flat, we will have spent one cycle confirming contrast was
not it, when the curve hinted copy.** Accepted knowingly. Rationale: we have burned
three cycles on un-attributable bundles; a clean negative on contrast is worth one
cycle and immediately routes us to the copy test with the thumbnail no longer a
confound.

## 8. Timing rationale — corrected

Ship at the **Day 11 post**. The reason is NOT "need Days 6–8 IG view baseline" —
**that rationale is retired.** Retention is the baseline; it is per-video and already
matured (Law 4). The correct reason to ship Day 11 and not sooner is that the
**staging work is real and must not be rushed**:
1. Frame-0 verification — DONE (§5).
2. Per-background prototyping at worst case (§9).
3. Eyeballing at true grid scale (~320px wide, post-JPEG).
Right timeline, right reason. Do not let the noisy-view-baseline logic creep back.

## 9. Staging tasks (Days 9–10, preview-only, lock-safe)

1. **DONE:** frame-0 / `cover_url` verification in `post.py` (§5).
2. Prototype the `bright` scrim + legibility panel as **preview PNGs only** (via the
   `scripts/preview_tease_intro.py` path — renders images, posts nothing). Prototype
   on the **visually busiest background per book**, NOT benign 51/81. Halving the
   scrim reveals whatever painting is underneath — it will look great behind a clean
   Hokusai wave and possibly cluttered behind a 20-figure Baroque court scene. The
   worst-case background decides whether this works. Pick the busiest 48laws / atomic
   / rules background explicitly and judge on those.
3. Downscale each preview to ~320px wide, JPEG it, and confirm it still stops the
   scroll at true grid scale. The 6px gold rule will ~vanish here — that's expected
   (§3c); judge on scrim brightness + protected text-mass.

## 9b. Pre-ship prerequisites — status

1. **Frame-0 = grid cover:** ✅ DONE, empirically (§5). The gate passed.
2. **Same-length 12s retention pre-image (Law 5 or 6):** ⚠️ BLOCKED. The local
   `yt_token.json` is `youtube.upload` scope only — it cannot query the YouTube
   Analytics API. Retention is owner-only, never public, not in the Data API. I
   cannot pull it. Two unblocks: (a) manual 30-sec read in YT Studio → Content →
   Law 5/6 → Analytics → "Average percentage viewed" + Reach→Traffic source; or
   (b) re-auth `scripts/yt_auth_bootstrap.py` with `yt-analytics.readonly` added,
   one browser consent, then it is permanently automatable. (b) is recommended —
   this exact blocker has stopped the engagement diagnosis 4+ times and will keep
   doing so. NOTE: under §4's corrected metric this is now a *secondary*
   corroborator, not the primary gate, so it is **not ship-blocking** — but it is
   the only YT read worth having and the re-auth is overdue regardless.

## 10. What "ship" means at Day 11

Apply §3a–3d, render the Day 11 video, post normally. Commit message states this is
the single-variable contrast intervention, names Law 4 (31.8% stayed) as the
pre-registered baseline, and quotes the §4 decision rule verbatim so the verdict
cannot be rationalized after the fact.
