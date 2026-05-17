"""Upload factory output into ONE shared Google Drive folder.

Auth is method-agnostic (same dual pattern as post_youtube.py) so the code
never blocks on which path you choose — only your one-time setup differs:

  A) SERVICE ACCOUNT (pure robot, zero sign-in):
       env GOOGLE_SERVICE_ACCOUNT_JSON -> path to the SA key file
       (default: gdrive_service_account.json, gitignored).
       You share the ONE folder with the SA's email (Editor).
       Caveat: SA-owned files need a Workspace **Shared Drive** (SA has no
       My-Drive quota). On consumer Gmail use path B.

  B) ONE-TIME OAUTH (like the YouTube setup, you pre-approved this):
       reuses client_secret.json + gdrive_token.json (gitignored).
       Files owned by you, your quota — robust on any account.

Folder is addressed by GDRIVE_FOLDER_ID (the long id in the folder URL).
Scope: drive.file (only files this tool creates — minimal). Uploads are
idempotent: an existing file of the same name in the folder is UPDATED,
never duplicated, so re-running the weekly top-up is safe.
"""
from __future__ import annotations

import os
from pathlib import Path

from googleapiclient.discovery import build as _build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).parent
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
SA_KEY = ROOT / os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "gdrive_service_account.json")
OAUTH_CLIENT = ROOT / "client_secret.json"
OAUTH_TOKEN = ROOT / "gdrive_token.json"


def _credentials():
    if SA_KEY.exists():
        from google.oauth2 import service_account
        return service_account.Credentials.from_service_account_file(
            str(SA_KEY), scopes=SCOPES)
    if OAUTH_TOKEN.exists():
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(str(OAUTH_TOKEN), SCOPES)
        if not creds.valid:
            creds.refresh(Request())
            OAUTH_TOKEN.write_text(creds.to_json(), encoding="utf-8")
        return creds
    raise RuntimeError(
        "No Drive credentials. Provide gdrive_service_account.json (service "
        "account) OR run scripts/gdrive_auth_bootstrap.py once (OAuth)."
    )


def _service():
    return _build("drive", "v3", credentials=_credentials(), cache_discovery=False)


def _folder_id() -> str:
    fid = os.environ.get("GDRIVE_FOLDER_ID", "").strip()
    if not fid:
        raise RuntimeError("GDRIVE_FOLDER_ID not set (the id in the folder URL)")
    return fid


def upload(local_path: Path, *, mime: str) -> str:
    """Create-or-update `local_path` in the shared folder by exact name.
    Returns the Drive file id. Idempotent."""
    svc = _service()
    folder = _folder_id()
    name = local_path.name
    q = (f"name = '{name}' and '{folder}' in parents and trashed = false")
    existing = svc.files().list(
        q=q, fields="files(id)", pageSize=1,
        supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute().get("files", [])
    media = MediaFileUpload(str(local_path), mimetype=mime, resumable=True)
    if existing:
        fid = existing[0]["id"]
        svc.files().update(fileId=fid, media_body=media,
                           supportsAllDrives=True).execute()
        return fid
    meta = {"name": name, "parents": [folder]}
    created = svc.files().create(
        body=meta, media_body=media, fields="id",
        supportsAllDrives=True).execute()
    return created["id"]


def exists(name: str) -> bool:
    svc = _service()
    q = f"name = '{name}' and '{_folder_id()}' in parents and trashed = false"
    return bool(svc.files().list(
        q=q, fields="files(id)", pageSize=1,
        supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute().get("files", []))
