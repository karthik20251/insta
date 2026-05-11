"""Query ccMixter for CC-BY (commercial-safe) instrumental tracks across moods."""
import json, sys, urllib.request, urllib.parse

QUERIES = [
    ("dark/cinematic for 48 Laws", "instrumental,cinematic"),
    ("upbeat/electronic for Atomic Habits", "instrumental,electronic"),
    ("ambient/reflective for 12 Rules", "instrumental,ambient"),
]

for label, tags in QUERIES:
    url = f"http://ccmixter.org/api/query?f=json&dataview=links_dl&limit=20&sort=rank&tags={urllib.parse.quote(tags)}"
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=30).read())
        print(f"\n=== {label}  ({len(data)} tracks) ===")
        for t in data:
            files = t.get("files", [])
            mp3 = next((f for f in files if f.get("file_nicname") == "mp3"), None)
            if not mp3:
                continue
            dur = mp3.get("file_format_info", {}).get("ps", "?")
            size = mp3.get("file_filesize", "?").strip()
            name = t["upload_name"][:42]
            # Hunt for license fields in the response
            lic = (t.get("license_name") or t.get("license") or
                   t.get("upload_extra", {}).get("license") or
                   mp3.get("file_extra", {}).get("ccud") or "?")
            lic_str = str(lic)[:25]
            print(f"  {name:42s} | {dur:>5} | {lic_str:25s} | {t['download_url']}")
    except Exception as e:
        print(f"  ERROR: {e}")
