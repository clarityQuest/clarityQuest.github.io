#!/usr/bin/env python3
"""
Derive lat/lng and wiki_url for records that have a modern name but no coordinates,
by searching Wikipedia for the modern place name and extracting geo-coordinates from
the article summary.

Confidence levels for modern name quality:
  3 — single clean name, no ambiguity markers
  2 — cleaned (parentheticals stripped), still reliable
  1 — first of multiple alternatives ("A / B"), uncertain
  0 — skip (contains ?, km, miles, relative directions, too short)

Usage:
  python scripts/derive_coords_from_modern.py              # dry-run, all types
  python scripts/derive_coords_from_modern.py --type spa   # one type only
  python scripts/derive_coords_from_modern.py --min-conf 2 # only conf >= 2
  python scripts/derive_coords_from_modern.py --write      # apply changes
"""

import re, sys, json, time, urllib.request, urllib.parse
from pathlib import Path

DB_PATH  = Path(__file__).parent.parent / "public/data/review_places_db.json"
WRITE    = "--write" in sys.argv

TYPE_FILTER = None
if "--type" in sys.argv:
    idx = sys.argv.index("--type")
    if idx + 1 < len(sys.argv):
        val = sys.argv[idx + 1]
        TYPE_FILTER = None if val == "all" else val

MIN_CONF = 1
if "--min-conf" in sys.argv:
    idx = sys.argv.index("--min-conf")
    if idx + 1 < len(sys.argv):
        MIN_CONF = int(sys.argv[idx + 1])

# ── Country bounding-box table ────────────────────────────────────────────
COUNTRY_BBOX = [
    ["MT",35.78,36.08,14.18,14.58], ["CY",34.56,35.71,32.26,34.60],
    ["LU",49.45,50.18,5.73,6.53],   ["XK",41.86,43.27,20.01,21.79],
    ["ME",41.85,43.55,18.43,20.36], ["SI",45.42,46.88,13.38,16.61],
    ["AL",39.64,42.66,19.27,21.07], ["MK",40.85,42.37,20.45,23.04],
    ["BA",42.56,45.27,15.75,19.62], ["PT",36.96,42.15,-9.50,-6.19],
    ["IE",51.44,55.38,-10.48,-5.99],["LB",33.05,34.69,35.10,36.63],
    ["IL",29.50,33.34,34.27,35.90], ["CH",45.83,47.81,5.96,10.49],
    ["AT",46.37,49.02,9.53,17.16],  ["HR",42.39,46.55,13.50,19.43],
    ["RS",42.23,46.19,18.82,22.99], ["BG",41.24,44.22,22.36,28.61],
    ["SK",47.73,49.61,16.84,22.56], ["HU",45.74,48.59,16.11,22.90],
    ["AM",38.84,41.30,43.45,46.63], ["AZ",38.39,41.90,44.77,50.39],
    ["GE",41.05,43.59,40.00,46.64], ["JO",29.19,33.38,35.00,39.30],
    ["TN",30.24,37.55,7.52,11.60],  ["GR",34.80,41.75,19.37,29.65],
    ["RO",43.62,48.27,22.15,30.05], ["NL",50.75,53.56,3.36,7.23],
    ["BE",49.50,51.51,2.55,6.40],   ["CZ",48.55,51.06,12.09,18.86],
    ["GB",49.87,60.86,-8.65,1.76],  ["DE",47.27,55.06,6.02,15.04],
    ["PL",49.00,54.84,14.12,24.15], ["FR",42.33,51.09,-4.79,8.24],
    ["IT",36.62,47.09,6.63,18.52],  ["ES",35.17,43.79,-9.30,3.33],
    ["SY",32.31,37.32,35.73,42.38], ["IQ",29.07,37.39,38.79,48.57],
    ["UA",44.39,52.38,22.14,40.09], ["EG",21.98,31.67,24.70,36.90],
    ["LY",19.50,33.17,9.32,25.16],  ["MA",27.67,35.92,-13.17,-0.99],
    ["DZ",18.97,37.09,-8.68,11.99], ["TR",35.82,42.10,26.04,44.79],
    ["IR",25.06,39.78,44.02,63.32], ["TM",35.14,42.80,52.44,66.69],
    ["AF",29.40,38.49,60.52,74.89], ["PK",23.69,37.10,60.87,77.84],
    ["IN",8.09,35.68,68.11,97.41],
]

def guess_country_bbox(lat, lng):
    best, best_area = None, float("inf")
    for iso, la1, la2, lo1, lo2 in COUNTRY_BBOX:
        if la1 <= lat <= la2 and lo1 <= lng <= lo2:
            area = (la2 - la1) * (lo2 - lo1)
            if area < best_area:
                best_area = area; best = iso
    return best


# ── Modern name cleaning ──────────────────────────────────────────────────
_VAGUE = re.compile(
    r'\b(km|mi|miles?|bei|nahe|near|nördl|südl|östl|westl|zwischen|between|'
    r'vom|von|neben|unweit|north|south|east|west|etwa|j\.|'
    r'Hr\.|Henchir|Ruinen|ruins|road.station)\b', re.I)

def clean_modern(raw):
    """Return (cleaned_name, confidence 0-3) or (None, 0) to skip."""
    s = (raw or "").strip()
    if len(s) < 3:
        return None, 0
    if "?" in s:
        return None, 0
    if _VAGUE.search(s):
        return None, 0
    if re.match(r'^\d', s):          # starts with digit (distance desc)
        return None, 0

    conf = 3

    # Multiple alternatives — take first, lower confidence
    if "/" in s or re.search(r'\boder\b', s, re.I):
        parts = re.split(r'\s*/\s*|\s+oder\s+', s, flags=re.I)
        s = parts[0].strip()
        conf = 1

    # Strip trailing parentheticals like "(Barrington)", "(Miller)", "[5]"
    s = re.sub(r'\s*[\(\[][^\)\]]*[\)\]]\s*$', '', s).strip()
    # Strip source tags like "[4]", "[5]" anywhere
    s = re.sub(r'\s*\[\d+\]\s*', ' ', s).strip()
    # Strip trailing dot / comma
    s = s.rstrip('.,;')

    if len(s) < 3:
        return None, 0

    # If we stripped something, drop to conf 2 (unless already 1)
    if conf == 3 and s != raw.strip():
        conf = 2

    return s, conf


# ── Wikipedia lookup ──────────────────────────────────────────────────────
def _fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)

# Generic geographic words that alone don't distinguish an article
_GENERIC = {
    "isola", "isla", "ile", "iles", "island", "insula",
    "fiume", "fluss", "flumen", "fluvius", "river", "riviere",
    "mons", "monts", "monte", "mont", "berg", "berge", "gebirge", "dagh", "dag",
    "lago", "lake", "lacus", "lacum", "sinus", "meer", "mare",
    "portus", "port", "capo", "cape", "kap",
    "henchir", "hench", "djebel", "jebel",
}

def _title_match_ok(name, title):
    """Return True only if the article title plausibly matches the search name."""
    n, t = name.lower(), title.lower()
    # Exact containment
    if n in t or t in n:
        return True
    t_words = set(re.split(r"\W+", t))
    # Require ALL distinctive words (≥5 chars, not generic) to appear as words in title
    key = [w for w in re.split(r"\W+", n) if len(w) >= 5 and w not in _GENERIC]
    if key:
        return all(w in t_words for w in key)
    # Fallback: first word (≥4 chars) must be a word in title
    first = re.split(r"\W+", n)[0] if n else ""
    return len(first) >= 4 and first in t_words


def wiki_coords(name, lang="en"):
    """
    Search Wikipedia for `name` and return (wiki_url, lat, lng) if the article
    is geo-tagged and the title plausibly matches, else (None, None, None).
    Tries EN first, then DE.
    """
    for try_lang in ([lang, "de"] if lang == "en" else [lang, "en"]):
        q = urllib.parse.quote(name, safe="")
        search_url = (f"https://{try_lang}.wikipedia.org/w/api.php"
                      f"?action=opensearch&search={q}&limit=3&format=json&redirects=resolve")
        try:
            result = _fetch_json(search_url)
            titles = result[1] if result and len(result) > 1 else []
            if not titles:
                continue
            # Prefer exact match, else first title that passes similarity check
            best = next((t for t in titles if t.lower() == name.lower()), None)
            if best is None:
                best = next((t for t in titles if _title_match_ok(name, t)), None)
            if best is None:
                continue
            title_q = urllib.parse.quote(best.replace(" ", "_"), safe="")
            summary_url = (f"https://{try_lang}.wikipedia.org/api/rest_v1/page/summary/{title_q}")
            summary = _fetch_json(summary_url)
            coords = summary.get("coordinates")
            if coords:
                article_url = summary["content_urls"]["desktop"]["page"]
                return article_url, float(coords["lat"]), float(coords["lon"])
        except Exception:
            pass
        time.sleep(0.3)
    return None, None, None


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Loading {DB_PATH} …")
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)
    records = db["records"]

    # Select: no lat, has some modern name
    def has_modern(r):
        return bool(r.get("modern_preferred") or r.get("modern_omnesviae") or r.get("modern_tabula"))

    if TYPE_FILTER:
        targets = [r for r in records if r.get("lat") is None and has_modern(r)
                   and r.get("type") == TYPE_FILTER]
    else:
        targets = [r for r in records if r.get("lat") is None and has_modern(r)]

    type_label = TYPE_FILTER or "all"
    print(f"Targets: {len(targets)} records with modern name but no lat/lng (type={type_label}, min-conf={MIN_CONF})\n")

    found = 0
    skipped = 0
    no_coords = 0
    errors = 0

    for i, rec in enumerate(targets, 1):
        # Prefer omnesviae (cleanest) → tabula → preferred
        raw = (rec.get("modern_omnesviae") or rec.get("modern_tabula")
               or rec.get("modern_preferred") or "")
        name, conf = clean_modern(raw)

        latin = (rec.get("latin_std") or rec.get("latin") or "")[:35]
        prefix = f"[{i:4d}/{len(targets)}] {latin:35s} ({conf}) "

        if conf < MIN_CONF or not name:
            print(f"{prefix}SKIP  {raw[:40]!r}")
            skipped += 1
            continue

        print(f"{prefix}{name[:35]!r} … ", end="", flush=True)

        try:
            wiki_url, lat, lng = wiki_coords(name)
            time.sleep(0.4)

            if lat is None:
                print("no geo coords in article")
                no_coords += 1
                continue

            rec["lat"] = round(lat, 6)
            rec["lng"] = round(lng, 6)
            if wiki_url and not rec.get("wiki_url"):
                rec["wiki_url"] = wiki_url
            country = guess_country_bbox(lat, lng)
            if country and not rec.get("country"):
                rec["country"] = country

            print(f"{lat:.4f}, {lng:.4f}  {country or '?'}  [{wiki_url or '—'}]")
            found += 1

        except Exception as ex:
            print(f"ERR: {ex}")
            errors += 1

    print(f"\n{'─'*60}")
    print(f"Found coords:  {found} / {len(targets)}  (skipped={skipped}, no-geo={no_coords}, errors={errors})")

    if not WRITE:
        print("\nDry run — pass --write to apply changes.")
        return

    tmp = DB_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DB_PATH)
    print(f"\n✓ Saved {found} entries → {DB_PATH.name}")


if __name__ == "__main__":
    main()
