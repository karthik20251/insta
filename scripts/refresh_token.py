"""Refresh the Meta long-lived access token and update the IG_ACCESS_TOKEN GitHub secret.

Runs weekly via .github/workflows/refresh_token.yml. Each refresh resets the 60-day
clock, so as long as this job keeps running, the token effectively never expires.

Required env vars (provided by the workflow):
- APP_SECRET           — Meta app secret
- CURRENT_TOKEN        — current value of IG_ACCESS_TOKEN
- GH_TOKEN             — GitHub fine-grained PAT with Secrets: read+write on this repo
- GITHUB_REPOSITORY    — owner/repo (auto-populated in Actions)
"""
from __future__ import annotations
import os
import subprocess
import sys

import requests

APP_ID = "1686113425976963"
GRAPH = "https://graph.facebook.com/v21.0"


def main() -> int:
    app_secret = os.environ.get("APP_SECRET", "").strip()
    current = os.environ.get("CURRENT_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()

    if not (app_secret and current and repo):
        print("ERROR: missing one of APP_SECRET / CURRENT_TOKEN / GITHUB_REPOSITORY")
        return 1

    print("[1/3] Asking Meta for a fresh long-lived token...")
    r = requests.get(
        f"{GRAPH}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": app_secret,
            "fb_exchange_token": current,
        },
        timeout=30,
    )
    if r.status_code != 200:
        print(f"      HTTP {r.status_code}: {r.text[:500]}")
        return 1
    data = r.json()
    if "error" in data:
        print(f"      Meta error: {data['error']}")
        return 1
    new_token = data["access_token"]
    expires_in = data.get("expires_in", 0)
    print(f"      OK. New token, expires in ~{expires_in // 86400} days")

    if new_token == current:
        print("      (Note: token unchanged. Meta returned the same token.)")

    print(f"[2/3] Updating IG_ACCESS_TOKEN secret on {repo}...")
    # `gh secret set` reads the value from stdin when neither --body nor --body-file is given.
    # Passing via stdin avoids the token appearing in the process command line.
    result = subprocess.run(
        ["gh", "secret", "set", "IG_ACCESS_TOKEN", "--repo", repo],
        input=new_token,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"      gh secret set failed: {result.stderr.strip()}")
        return 1
    print("      OK. Secret updated.")

    print("[3/3] Done. Daily posts will now use the refreshed token.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
