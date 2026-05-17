# Reliability Patch — pre-Day-11, experiment-defending

Status: **SPEC. Recommended to SHIP before the Day 11 post** (not merely staged).
Rationale identical to the idempotency guard: a crashed or unrecoverable post day
destroys the Days 11–15 contrast-test attribution window. This patch defends the
experiment; that is what makes it lock-safe to ship, not cosmetics.

Scope (FOUR experiment-killing roads + hygiene): 🔴 pilmoji SPOF + 🟠a YouTube
idempotency + 🟠b workflow push-race + 🟠c raw-URL propagation race + 🟡-today
unification + 🟢 comment rot. One coherent patch — all four roads cause exactly the
"crashed/unrecoverable/false-fail day" the patch's justification names; scoping in
the control-flow split while excluding a 2-line push-retry would be internally
inconsistent with that justification. Explicitly OUT: 🟡 loudnorm → music spec.

All findings verified in code, not asserted (line refs below).

---

## 🔴 pilmoji is an uncaught single point of total failure

**Defect.** `generate.py:263-264` — `render_intro_frame` uses `Pilmoji` with the
`Twemoji` source, which fetches emoji PNGs from a CDN at render time. `main.py:120`
`result = build(day_num)` is not wrapped; the IG post path is not wrapped. Story
(`main.py:146`) and YT (`main.py:154`) are best-effort. A CDN blip / network hiccup /
runner egress limit on a single emoji PNG crashes the whole day: no Reel, no Story,
no YT. Cosmetic feature, live network dependency, zero fallback, critical path. Also
a per-render latency+flakiness tax even on the happy path (N CDN calls every run).

**Fix — two layers, in priority order:**

1. **Primary: local Twemoji asset bundle (removes the dependency).** Vendor the
   exact set of Twemoji PNGs the corpus uses into `assets/twemoji/` and point pilmoji
   at a local source instead of the CDN. Determinism: scan all `tease`/label strings
   in `quotes.json`, extract the emoji codepoints actually used, fetch those PNGs
   once at build-time-of-the-repo (a one-off vendoring script, run by a human, not in
   the cron), commit them. Render then has **zero network dependency** and the emoji
   render **identically** → no attribution confound.
   - Pin the Twemoji asset version (record it in the vendoring script) so a future
     re-vendor can't silently change glyph appearance mid-experiment.

2. **Last-resort net: never crash the post for an emoji.** Wrap the emoji-rendering
   step so that if pilmoji raises for any reason, the frame still renders with the
   text minus the emoji glyphs (strip, don't box) and the post proceeds.
   **MANDATORY: emit a loud, unmistakable marker** when this path fires —
   `print("‼ PILMOJI_FALLBACK_FIRED day=<n>")` and a `write_github_output(
   pilmoji_fallback="true")`. This makes any affected day detectable so it can be
   **excluded from the Days 11–15 attribution set**. The fallback is itself a
   first-frame visual change = the exact variable under test; an unlogged fallback
   would silently corrupt the experiment. Logged, it's recoverable.

**Lock note:** layer 1 has zero confound by construction. Layer 2 is a confound but
rare and, because it's logged + excludable, strictly better than a missing day.

**Condition 1 — pixel-identity (mandatory gate before ship).** The bundle is the one
place a reliability patch could smuggle in the exact variable under test (the first
frame). The local assets MUST be the identical Twemoji set the CDN path renders. A
different set (Noto vs Twemoji, or a different Twemoji version) changes the normal-
path thumbnail = the contrast-test variable.
- **Pin the Twemoji version.** A custom source uses one fixed version URL for BOTH
  the one-off vendoring AND the last-resort CDN fallback. Local and CDN are then the
  same assets by construction, and pilmoji's unpinned "latest" can never silently
  move the thumbnail mid-experiment (a latent confound, closed now).
- **Verification protocol:** (1) BEFORE patch, with CDN reachable, rebuild Day
  5/51/81 and snapshot the intro-frame PNGs as reference. (2) Apply patch. (3)
  Rebuild the same three with the local bundle. (4) Pixel-diff post vs reference —
  **must be zero diff** on the normal path. Only the deliberately-triggered failure
  path (→ plain text, no crash) may differ. Ship is blocked until this is green.

## 🟠a idempotency guard doesn't cover YouTube — can permanently drop the stronger platform

**Defect.** `main.py:114-118` — guard checks only IG's latest media, then `return 0`
*before* the YT block (`main.py:154`). Scenario: scheduled run posts IG OK, YT upload
fails (best-effort, swallowed). Manual re-run to recover YT → guard sees today's IG
post → exits → YT never retried, permanently. YT is the stronger platform (~1.5–2×).
The "safe for partial failure" guarantee given earlier was IG-only — corrected here.

**Fix — per-platform idempotency, not all-or-nothing.** Replace the single
`already_posted_today_ist() -> bool` skip with two independent checks:

- `ig_posted_today() -> bool` — current IG media query (unchanged logic).
- `yt_posted_today() -> bool` — query the channel's uploads for a video dated today
  (IST). Requires the `yt-analytics.readonly`/`youtube.readonly`-class read; the
  re-auth (already specced, `scripts/yt_auth_bootstrap.py`) enables it. Until the
  re-auth lands, `yt_posted_today()` returns `False` (fail-open: never blocks a YT
  retry — the worst case reverts to today's behavior, a possible duplicate, which is
  far less bad than permanent loss of the stronger platform).

Control flow in `main()`:
- If `ig_posted_today()` → skip the IG post block only.
- If `yt_posted_today()` → skip the YT upload only.
- If both → `write_github_output(skipped="true"); return 0` (the only case that
  emits `skipped=true`, preserving the §daily.yml email gate).
- Build still runs once; render output is reused for whichever platform still needs
  posting.

Fail-open preserved throughout (network/API error on either check → proceed).
No side effects on caption / timing / render / payload — same contract the original
guard satisfied.

**Secondary (record, don't fix now):** the guard skips if *any* post dated today
exists, so a manual human post that day silently suppresses the bot's scheduled
content. Low frequency. Documented; out of scope for this patch.

## 🟠b workflow git push non-fast-forward race — false-fail day

**Defect.** `.github/workflows/daily.yml:36-41` commits `output/` and `git push`
with no pull/rebase. If origin moved since checkout (a prior run's auto-commit, our
own commits, an overlapping run), the push fails non-fast-forward → the workflow step
fails → the day's run fails AFTER possibly already posting, or the raw URL the post
step needs is never pushed. Demonstrated repeatedly this session on our own pushes.

**Fix (~2 lines).** Before `git push`, `git pull --rebase origin "$BRANCH"`; wrap the
push in a short bounded retry (rebase → push, up to 3 attempts) so a concurrent
cron/manual push can't false-fail the day. `[skip ci]` already prevents a commit loop.
Self-referential bonus: this also dissolves the risk of THIS patch's own commit
colliding with the cron push (Condition 2) — a second, independent reason it is in
scope, not deferred.

## 🟠c raw-URL propagation race — false-fail day (already documented by the repo)

**Defect.** `main.py:83-88` (`upload_to_public_url`, github backend) returns
`{base}/{name}` the instant the workflow commits, but `raw.githubusercontent.com` has
CDN propagation lag (seconds–minutes). IG's container creation (`post.py`) fetches
that URL; if it 404s pre-propagation → ingestion ERROR → post fails. Not speculative:
`daily.yml:112` already lists "GitHub raw URL not yet propagated… re-run" as a known
failure cause. A pre-existing, acknowledged false-fail road left unguarded.

**Fix (~10 lines).** In `upload_to_public_url`, before returning the github URL,
HEAD-poll it until 200 (e.g., 12 attempts × 5s = 60s ceiling, then proceed and let
the post path surface a real failure rather than hang forever). Turns a race into a
bounded wait. No behaviour change when propagation is already done (first HEAD = 200).

**Defect.** `main.py:111` `current_day()` → `date.today()` (runner-local = UTC on
GitHub Actions). `main.py:49` guard → explicit IST. Diverge 00:00–05:30 UTC; a
delayed/manual run there computes day N+1 (UTC) while idempotency's "today" is day N
(IST) → boundary double-post or wrong-skip. This is the precise failure mode the 🟠
recovery path triggers, so it ships with 🟠 — fixing recovery while leaving its date
logic split is an incomplete fix.

**Fix.** Single source of truth: `today_ist()` helper
(`datetime.now(timezone.utc).astimezone(IST).date()`). `current_day()` computes
`n = (today_ist() - start_d).days + 1`. Both `current_day()` and both per-platform
guards use it. One definition of "today" in the file.

## 🟢 comment rot from the 12s revert — folded in (lock-safe, landmine)

**Defect.** `generate.py:495-505` docstring says "24-sec Reel… 0-3… 22-24"; inline
`# 2.5 / # 9.5 / # 21.5` are stale 24s offsets. Code computes correctly from the
constants; actual offsets are **1.5 / 5.5 / 9.5**, fade-out st=`DURATION_SEC-1`=11.
Comments don't execute → lock-safe by definition. Wrong 24s numbers in the timing
code during an active timing-sensitive experiment is a debugging landmine given this
project's timing thrash.

**Fix.** Rewrite the docstring to the 12s/2-4-4-2 reality; replace the three inline
offset comments with the formula, not hardcoded numbers
(`# = INTRO+MAIN-0.5`, etc.) so they can't rot again on the next timing change.

## Hard prerequisite to the re-auth step (non-code, must not fall off)

**OAuth consent screen must be "In production" BEFORE re-minting the token.** Google
expires refresh tokens for apps in **"Testing"** publishing status after **7 days**.
Re-running `scripts/yt_auth_bootstrap.py` while the consent screen is still "Testing"
just mints another token that silently dies in a week — the highest-probability
silent YT killer, and it would look exactly like a random YT outage. This is a manual
Google Cloud Console setting (APIs & Services → OAuth consent screen → Publish App),
not code, so it cannot live in this patch — but it is a **blocking prerequisite** to
the `yt-analytics.readonly` re-auth and to any future YT_REFRESH_TOKEN rotation.
Recorded here so it cannot be forgotten when the re-auth is finally done.

## Out of scope (named, not dropped)

- **🟡 single-pass loudnorm** (`generate.py:541`). Real — single-pass loudnorm pumps
  and overshoots on dynamic-range classical material; a genuine contributor to "the
  music sounds bad," independent of track choice. Folds into the **music spec**
  (two-pass: a measurement pass feeding `measured_I/TP/LRA/thresh` into the apply
  pass). Not in this patch — different surface, different test, no attribution risk.

## Verification before this patch is considered shipped

0. **GATING — Condition 1 pixel-identity:** pre-patch CDN reference vs post-patch
   local-bundle render of Day 5/51/81 intro frames → **zero pixel diff**. Ship
   blocked until green. (Failure path may differ; normal path may not.)
1. `python main.py --dry-run` on a normal day → builds, no crash, no skip.
2. Simulate pilmoji failure (monkeypatch the source to raise) → frame still renders
   text, post path proceeds, `PILMOJI_FALLBACK_FIRED` marker emitted.
3. Local-asset path: render a tease day with network disabled → emoji still render
   from `assets/twemoji/` (proves the dependency is actually removed).
4. Per-platform guard: simulate IG-posted-today / YT-not → confirm IG skipped, YT
   proceeds; both-posted → `skipped=true` + early return.
5. `today_ist()` unification: assert `current_day()` and guards agree at a
   03:00-UTC clock (the old divergence window).
6. 🟠b push-retry: simulate a non-fast-forward (push to a stale ref) → rebase-retry
   recovers within the bounded attempts instead of failing the step.
7. 🟠c raw-URL poll: point at a not-yet-existing raw path → HEAD-poll waits, then
   proceeds at the ceiling; an already-propagated URL returns immediately (no
   added latency on the happy path).
8. ffprobe a freshly built video → still exactly 12.000000s (the patch must not
   touch timing behavior, only timing *comments*).
