"""Pre-flight check before relying on the bot. Validates every moving part.

Run before any major deployment or when troubleshooting.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

CHECKS_RUN = 0
CHECKS_PASS = 0
CHECKS_FAIL = 0


def check(name: str, condition, message_ok: str = "OK", message_fail: str = "FAIL"):
    global CHECKS_RUN, CHECKS_PASS, CHECKS_FAIL
    CHECKS_RUN += 1
    if condition:
        CHECKS_PASS += 1
        print(f"  [PASS] {name}: {message_ok}")
    else:
        CHECKS_FAIL += 1
        print(f"  [FAIL] {name}: {message_fail}")


print("\n=== Pre-flight check ===\n")

# 1. quotes.json
print("[1] quotes.json")
quotes = json.loads((Path(__file__).parent.parent / "quotes.json").read_text(encoding="utf-8"))
days = quotes["days"]
check("total days", len(days) == 92, f"{len(days)} days", f"expected 92, got {len(days)}")
check("sequence", [d["day"] for d in days] == list(range(1, 93)), "1-92 contiguous", "gaps or duplicates")

# 2. Required fields per day (all load-bearing on the renderer)
print("\n[2] required fields per day")
required = ["day", "title", "headline", "body", "caption_hook", "tease", "example", "mood"]
missing = [(d["day"], f) for d in days for f in required if f not in d]
check("all fields present", not missing,
      f"all 92 days x {len(required)} fields",
      f"missing: {missing[:5]}")

# 3. Music + backgrounds present per book
print("\n[3] assets per book")
root = Path(__file__).parent.parent
for slug in ("48laws", "atomic", "rules"):
    bg = list((root / "backgrounds" / slug).glob("*.jpg")) + list((root / "backgrounds" / slug).glob("*.png"))
    mu = list((root / "music" / slug).glob("*.mp3"))
    check(f"backgrounds/{slug}", len(bg) >= 3, f"{len(bg)} images", f"only {len(bg)} (need >=3)")
    check(f"music/{slug}", len(mu) >= 5, f"{len(mu)} tracks", f"only {len(mu)} (need >=5)")

# 4. Fonts
print("\n[4] fonts")
fonts_dir = root / "fonts"
required_fonts = ["Cinzel.ttf", "PlayfairDisplay.ttf", "PlayfairDisplay-Italic.ttf"]
for f in required_fonts:
    check(f"fonts/{f}", (fonts_dir / f).exists(), "present", "missing")

# 5. Workflows
print("\n[5] workflows")
wf = root / ".github" / "workflows"
check("daily.yml", (wf / "daily.yml").exists(), "present", "missing")
check("refresh_token.yml", (wf / "refresh_token.yml").exists(), "present", "missing")
daily_yml = (wf / "daily.yml").read_text(encoding="utf-8")
for env_var in ("IG_USER_ID", "IG_ACCESS_TOKEN", "YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
    check(f"daily.yml uses {env_var}", env_var in daily_yml, "passed to job", "not referenced")

# 6. Code modules
print("\n[6] code modules importable")
try:
    from generate import build, load_day, total_days
    check("generate.py imports", True, "OK")
    check("total_days() = 92", total_days() == 92, f"= {total_days()}")
except Exception as e:
    check("generate.py imports", False, "", str(e))

try:
    from post import build_caption, post_reel, post_story
    check("post.py imports", True, "OK")
except Exception as e:
    check("post.py imports", False, "", str(e))

try:
    from post_youtube import build_youtube_metadata, upload_short, get_credentials
    check("post_youtube.py imports", True, "OK")
except Exception as e:
    check("post_youtube.py imports", False, "", str(e))

# 7. .gitignore protects secrets
print("\n[7] .gitignore protects secrets")
gi = (root / ".gitignore").read_text(encoding="utf-8")
for pattern in (".env", "client_secret", "yt_token.json"):
    check(f".gitignore: {pattern}", pattern in gi, "protected", "NOT in .gitignore — DANGER")

# 8. No secrets accidentally tracked
print("\n[8] no secret files tracked in git")
import subprocess
tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split()
for danger in (".env", "client_secret.json", "yt_token.json"):
    check(f"git: {danger}", danger not in tracked, "not tracked", "TRACKED — leak risk")

# 9. Local IG token quick check
print("\n[9] credentials availability (local)")
env = (root / ".env").read_text(encoding="utf-8") if (root / ".env").exists() else ""
check(".env present", env != "", "found", "missing — local dry-run won't work")
check(".env has IG_ACCESS_TOKEN", "IG_ACCESS_TOKEN=EAA" in env, "looks present", "stub or missing")
check("yt_token.json present", (root / "yt_token.json").exists(), "found", "missing — local YT backfill won't work")

# 10. Today's day computation
print("\n[10] day-of-series computation")
from datetime import date, datetime
import re
m = re.search(r"START_DATE=(\d{4}-\d{2}-\d{2})", env)
if m:
    start = datetime.strptime(m.group(1), "%Y-%m-%d").date()
    today_day = (date.today() - start).days + 1
    print(f"  local START_DATE={start}, today=Day {today_day}/92")
    if 1 <= today_day <= 92:
        check("today within series range", True, f"Day {today_day}")
    else:
        check("today within series range", False, "", f"Day {today_day} is outside 1-92")
else:
    check("START_DATE in .env", False, "", "not set")

# Summary
print(f"\n=== {CHECKS_PASS}/{CHECKS_RUN} checks passed " +
      (f"({CHECKS_FAIL} failures)" if CHECKS_FAIL else "(0 failures)") + " ===")
sys.exit(0 if CHECKS_FAIL == 0 else 1)
