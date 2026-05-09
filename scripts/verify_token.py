"""Verify your Meta tokens are correct before going live.

Usage:
    .\.venv\Scripts\python.exe scripts\verify_token.py
"""
from __future__ import annotations
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

GRAPH = "https://graph.facebook.com/v21.0"


def step(n: int, msg: str) -> None:
    print(f"\n[{n}] {msg}")


def main() -> int:
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    user_id = os.environ.get("IG_USER_ID", "").strip()

    if not token:
        print("ERROR: IG_ACCESS_TOKEN not set in .env"); return 1

    step(1, "Checking token validity + permissions...")
    r = requests.get(f"{GRAPH}/debug_token", params={
        "input_token": token, "access_token": token,
    }, timeout=30)
    data = r.json().get("data", {})
    if not data.get("is_valid"):
        print(f"  [FAIL] Token is INVALID: {r.json()}"); return 1
    print(f"  [OK] Token is valid")
    print(f"    type:    {data.get('type')}")
    print(f"    expires: {data.get('expires_at')} (0 = never; long-lived ~ 60 days)")
    scopes = data.get("scopes", [])
    print(f"    scopes:  {', '.join(scopes)}")
    needed = {"instagram_basic", "instagram_content_publish", "pages_show_list"}
    missing = needed - set(scopes)
    if missing:
        print(f"  [WARN] Missing required permissions: {missing}")

    step(2, "Listing your Facebook Pages...")
    r = requests.get(f"{GRAPH}/me/accounts", params={"access_token": token}, timeout=30)
    pages = r.json().get("data", [])
    if not pages:
        print("  [FAIL] No pages found. You need a Facebook Page linked to your IG."); return 1
    for p in pages:
        print(f"  * {p['name']}  (page_id={p['id']})")

    step(3, "Looking up Instagram Business Account ID for each page...")
    found_ig: list[str] = []
    for p in pages:
        r = requests.get(
            f"{GRAPH}/{p['id']}",
            params={"fields": "instagram_business_account", "access_token": token},
            timeout=30,
        )
        ig = r.json().get("instagram_business_account")
        if ig:
            print(f"  [OK] Page '{p['name']}' -> IG_USER_ID={ig['id']}")
            found_ig.append(ig["id"])
        else:
            print(f"  - Page '{p['name']}' has no linked Instagram Business account")

    if not found_ig:
        print("\nERROR: No Instagram Business account is linked to any of your Facebook Pages.")
        print("  Fix: Open Facebook -> your Page -> Settings -> Linked Accounts -> connect Instagram (Business/Creator).")
        return 1

    if not user_id:
        print(f"\nNext step: copy one of the IG_USER_ID values above into your .env")
        return 0

    if user_id not in found_ig:
        print(f"\n[WARN] The IG_USER_ID in .env ({user_id}) is NOT one of the linked accounts above.")
        return 1

    step(4, f"Fetching IG account details for {user_id}...")
    r = requests.get(
        f"{GRAPH}/{user_id}",
        params={"fields": "username,name,followers_count,media_count", "access_token": token},
        timeout=30,
    )
    print(f"  {r.json()}")

    print("\n[OK] All good. You can now post for real (remove --dry-run).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
