"""Split YouTube OAuth: the agent runs the exchange, the human does consent.

Phase A (no YT_AUTH_RESP):  prints the consent URL + saves PKCE state.
Phase B (YT_AUTH_RESP set): exchanges the pasted code/redirect-URL,
                            writes yt_token.json, prints the refresh token.

Run via the same client_secret.json (Desktop app -> loopback redirect ok).
"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from google_auth_oauthlib.flow import Flow

ROOT = Path(__file__).parent.parent
CS = ROOT / "client_secret.json"
TOK = ROOT / "yt_token.json"
STATE = ROOT / ".yt_oauth_state.json"          # PKCE verifier between phases
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
REDIRECT = "http://localhost"                   # loopback; browser will just 404 — fine


def _flow() -> Flow:
    f = Flow.from_client_secrets_file(str(CS), scopes=SCOPES)
    f.redirect_uri = REDIRECT
    return f


def main() -> int:
    resp = os.environ.get("YT_AUTH_RESP", "").strip()

    if not resp:                                # Phase A
        f = _flow()
        url, _ = f.authorization_url(
            access_type="offline", prompt="consent", include_granted_scopes="true")
        STATE.write_text(json.dumps({"code_verifier": f.code_verifier}), encoding="utf-8")
        print("AUTH_URL_BEGIN")
        print(url)
        print("AUTH_URL_END")
        return 0

    # Phase B — resp is the full redirected URL or just the code
    code = resp
    if "code=" in resp:
        code = parse_qs(urlparse(resp).query).get("code", [resp])[0]
    f = _flow()
    if STATE.exists():
        f.code_verifier = json.loads(STATE.read_text(encoding="utf-8")).get("code_verifier")
    f.fetch_token(code=code)
    c = f.credentials
    TOK.write_text(c.to_json(), encoding="utf-8")
    STATE.unlink(missing_ok=True)
    print("WROTE", TOK.name)
    print("SCOPES:", list(c.scopes or SCOPES))
    print("HAS_REFRESH:", bool(c.refresh_token))
    print("YT_REFRESH_TOKEN_BEGIN")
    print(c.refresh_token)
    print("YT_REFRESH_TOKEN_END")
    return 0


if __name__ == "__main__":
    sys.exit(main())
