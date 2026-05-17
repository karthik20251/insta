"""One-time Google Drive OAuth bootstrap (path B — only if NOT using a
service account). Mirrors scripts/yt_auth_bootstrap.py exactly.

Opens a browser, you sign in ONCE (never a password to anyone), and writes
gdrive_token.json (gitignored). Scope is drive.file — this tool can only
touch files it creates in the folder you point it at; it cannot read the
rest of your Drive.

  .\\.venv\\Scripts\\python.exe scripts\\gdrive_auth_bootstrap.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).parent.parent
CLIENT_SECRET = ROOT / "client_secret.json"
TOKEN_FILE = ROOT / "gdrive_token.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def main() -> int:
    if not CLIENT_SECRET.exists():
        print(f"ERROR: {CLIENT_SECRET} not found")
        return 1
    print(">> Browser will open. Sign in to the Google account that owns the")
    print(">> delivery folder. Approve 'See, edit, create, and delete only the")
    print(">> specific Drive files you use with this app'. No password is shared.")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline",
                                  prompt="consent", open_browser=True)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    print(f"\nSUCCESS — wrote {TOKEN_FILE.name} (gitignored).")
    print("Now set GDRIVE_FOLDER_ID in .env and run scripts/stock_drive.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
