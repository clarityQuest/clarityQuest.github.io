#!/usr/bin/env python3
"""
Harvest Wikipedia URLs from ULM pages and write them to wiki_url in review_places_db.json.

Usage:
  python scripts/derive_wiki_urls.py              # dry-run, cities only
  python scripts/derive_wiki_urls.py --type all   # all record types
  python scripts/derive_wiki_urls.py --write      # apply changes
  python scripts/derive_wiki_urls.py --type all --write
"""

import re, sys, json, time, urllib.request
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "public/data/review_places_db.json"
WRITE   = "--write" in sys.argv

# Determine type filter
TYPE_FILTER = "city"
if "--type" in sys.argv:
    idx = sys.argv.index("--type")
    if idx + 1 < len(sys.argv):
        TYPE_FILTER = sys.argv[idx + 1]


def fetch_ulm_wiki(ulm_id):
    """Fetch ULM page and return the first real Wikipedia article URL found, or None."""
    url = f"https://tp-online.ku.de/trefferanzeige.php?id={ulm_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        html = r.read().decode("utf-8", errors="replace")
    for m in re.finditer(r'(https?://[a-z]{2,3}\.wikipedia\.org/wiki/[^\s"\'<)\]]+)', html):
        wiki_url = m.group(1).rstrip(".,;)")
        # Skip media/file links and non-article pages
        if re.search(r'[#/](media|Datei|File|Special|Help|Talk)[:/#]', wiki_url,
                     re.IGNORECASE):
            continue
        if re.search(r'\.(jpg|jpeg|png|gif|svg|webp)$', wiki_url, re.IGNORECASE):
            continue
        return wiki_url
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    print(f"Loading {DB_PATH} …")
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)
    records = db["records"]

    # Select targets: have ulm_id, no wiki_url yet, matching type filter
    if TYPE_FILTER == "all":
        targets = [r for r in records if r.get("ulm_id") and not r.get("wiki_url")]
    else:
        targets = [r for r in records
                   if r.get("ulm_id") and not r.get("wiki_url") and r.get("type") == TYPE_FILTER]

    print(f"Targets: {len(targets)} records (type={TYPE_FILTER})\n")

    found = []
    errors = 0

    for i, rec in enumerate(targets, 1):
        ulm_id = rec["ulm_id"]
        latin  = rec.get("latin_std") or rec.get("latin") or ""
        print(f"[{i:4d}/{len(targets)}] ULM {ulm_id:5d}  {latin[:40]:40s} … ", end="", flush=True)
        try:
            wiki_url = fetch_ulm_wiki(ulm_id)
            if wiki_url:
                print(wiki_url)
                found.append((rec, wiki_url))
            else:
                print("—")
        except Exception as ex:
            print(f"ERR: {ex}")
            errors += 1
        time.sleep(0.35)

    print(f"\n{'─'*60}")
    print(f"Found Wikipedia URLs: {len(found)} / {len(targets)}  (errors: {errors})\n")
    for rec, url in found:
        latin = rec.get("latin_std") or rec.get("latin") or ""
        print(f"  data_id={rec.get('data_id')}  {latin[:35]:35s}  {url}")

    if not WRITE:
        print("\nDry run — pass --write to apply changes.")
        return

    for rec, url in found:
        rec["wiki_url"] = url

    tmp = DB_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DB_PATH)
    print(f"\n✓ Saved {len(found)} wiki_url entries → {DB_PATH.name}")


if __name__ == "__main__":
    main()
