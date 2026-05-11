"""One-time YouTube OAuth bootstrap.

Opens a local browser, asks you to sign in to your Google account, captures the
authorization code, and exchanges it for a refresh token. Prints all three
values (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN) so you can paste them into
GitHub Secrets.

Usage:
    .\\.venv\\Scripts\\python.exe scripts\\yt_auth_bootstrap.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).parent.parent
CLIENT_SECRET = ROOT / "client_secret.json"
TOKEN_FILE = ROOT / "yt_token.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> int:
    if not CLIENT_SECRET.exists():
        print(f"ERROR: {CLIENT_SECRET} not found")
        return 1

    print(">> Starting OAuth flow. Your default browser will open in a moment...")
    print(">> If you see 'Google hasn't verified this app', click 'Advanced' ->")
    print("   'Go to instaautomatic-youtube (unsafe)' — that's normal for personal apps")
    print(">> Approve the 'Manage your YouTube videos' permission.")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    # access_type=offline + prompt=consent guarantees we get a refresh token
    creds = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
        open_browser=True,
    )

    # Save full credentials locally too (in case we want them later)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    # Pull values for GitHub Secrets
    secrets_json = json.loads(CLIENT_SECRET.read_text(encoding="utf-8"))
    config = secrets_json.get("installed") or secrets_json.get("web", {})
    client_id = config["client_id"]
    client_secret = config["client_secret"]

    print()
    print("=" * 70)
    print(" SUCCESS — copy these three values into GitHub Secrets")
    print("=" * 70)
    print()
    print(f"  YT_CLIENT_ID")
    print(f"      = {client_id}")
    print()
    print(f"  YT_CLIENT_SECRET")
    print(f"      = {client_secret}")
    print()
    print(f"  YT_REFRESH_TOKEN")
    print(f"      = {creds.refresh_token}")
    print()
    print("=" * 70)
    print(" URL: https://github.com/karthik20251/insta/settings/secrets/actions")
    print(" Then click 'New repository secret' three times — once per value.")
    print("=" * 70)
    print()
    print(f"(Local copy saved to {TOKEN_FILE.name} for safekeeping; it is gitignored.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
