"""One-shot: convert a short-lived user token (from Graph Explorer) into a
long-lived Page access token that includes `instagram_manage_insights`.

Usage:
    # 1. https://developers.facebook.com/tools/explorer
    #    - App: automaticup
    #    - Permissions: tick instagram_manage_insights (in ADDITION to the
    #      existing ones: instagram_basic, instagram_content_publish,
    #      pages_show_list, pages_read_engagement, business_management)
    #    - Generate Access Token  ->  copy the short-lived USER token
    # 2. set env, then run:
    #      $env:IG_SHORT_TOKEN = "<paste user token>"
    #      $env:APP_SECRET     = "<your app secret>"
    #      python scripts/ig_auth_insights.py
    # 3. The script prints the new long-lived PAGE token (~60-day life).
    #    Paste it into:
    #       - .env             (IG_ACCESS_TOKEN=...)
    #       - GitHub Secrets   (IG_ACCESS_TOKEN)
"""
from __future__ import annotations
import os
import sys
import requests

APP_ID = "1686113425976963"
IG_USER_ID = "17841416954482292"          # nandetroll_ business account
GRAPH = "https://graph.facebook.com/v21.0"
NEEDED = "instagram_manage_insights"


def main() -> int:
    short = os.environ.get("IG_SHORT_TOKEN", "").strip()
    secret = os.environ.get("APP_SECRET", "").strip()
    if not short or not secret:
        print("ERROR: set IG_SHORT_TOKEN (from Graph Explorer) and APP_SECRET")
        return 1

    # 1) Confirm the short token actually has the new scope -- fail FAST so
    #    we don't mint a long token that's still missing insights.
    d = requests.get("https://graph.facebook.com/debug_token",
                     params={"input_token": short, "access_token": short}, timeout=30)
    d.raise_for_status()
    scopes = d.json().get("data", {}).get("scopes", [])
    print(f"[1/4] short-token scopes: {scopes}")
    if NEEDED not in scopes:
        print(f"ERROR: '{NEEDED}' missing on the short token.")
        print("       In Graph Explorer, tick that permission and re-generate.")
        return 1

    # 2) Short-lived user -> long-lived user
    print("[2/4] exchanging short user token -> long-lived user token...")
    r = requests.get(f"{GRAPH}/oauth/access_token", params={
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": secret,
        "fb_exchange_token": short,
    }, timeout=30)
    r.raise_for_status()
    long_user = r.json()["access_token"]
    print("      OK")

    # 3) Pull Page accounts; Page tokens minted off a long-lived user token
    #    do NOT expire (per Meta docs), and inherit the user's scopes.
    print("[3/4] fetching Page access tokens via /me/accounts...")
    p = requests.get(f"{GRAPH}/me/accounts",
                     params={"access_token": long_user, "fields": "id,name,access_token,instagram_business_account"},
                     timeout=30)
    p.raise_for_status()
    pages = p.json().get("data", [])
    target = None
    for pg in pages:
        iba = pg.get("instagram_business_account") or {}
        if iba.get("id") == IG_USER_ID:
            target = pg
            break
    if not target:
        print("ERROR: no Page linked to IG_USER_ID", IG_USER_ID)
        print("Pages seen:", [(p.get("name"), (p.get("instagram_business_account") or {}).get("id")) for p in pages])
        return 1
    page_token = target["access_token"]
    print(f"      OK — page: {target['name']}")

    # 4) Verify the page token has the scope we wanted.
    print("[4/4] verifying scopes on the Page token...")
    d2 = requests.get("https://graph.facebook.com/debug_token",
                      params={"input_token": page_token, "access_token": page_token}, timeout=30)
    d2.raise_for_status()
    sc2 = d2.json().get("data", {}).get("scopes", [])
    print(f"      page-token scopes: {sc2}")
    print(f"      has instagram_manage_insights: {NEEDED in sc2}")

    print()
    print("IG_ACCESS_TOKEN_BEGIN")
    print(page_token)
    print("IG_ACCESS_TOKEN_END")
    print()
    print("NEXT:")
    print(" 1. .env       -> replace IG_ACCESS_TOKEN with the value above")
    print(" 2. GitHub Secrets (gh secret set IG_ACCESS_TOKEN --repo <repo>)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
