#!/usr/bin/env python3
"""
Find Wikipedia articles for river records that have a modern name but no wiki_url.
Adapts language and name-cleaning strategies for rivers.

Usage:
  python scripts/derive_river_wiki.py              # dry-run
  python scripts/derive_river_wiki.py --min-conf 2 # only conf >= 2
  python scripts/derive_river_wiki.py --write      # apply all results
  python scripts/derive_river_wiki.py --accept 1,3,5 --write
"""

import re, sys, json, time, urllib.request, urllib.parse
from pathlib import Path

DB_PATH  = Path(__file__).parent.parent / "public/data/review_places_db.json"
WRITE    = "--write" in sys.argv

MIN_CONF = 1
if "--min-conf" in sys.argv:
    idx = sys.argv.index("--min-conf")
    if idx + 1 < len(sys.argv):
        MIN_CONF = int(sys.argv[idx + 1])

ACCEPT_IDS = set()
if "--accept" in sys.argv:
    idx = sys.argv.index("--accept")
    if idx + 1 < len(sys.argv):
        ACCEPT_IDS = {int(x) for x in sys.argv[idx + 1].split(",") if x.strip().isdigit()}

# ── Vague pattern — skip these modern names ───────────────────────────────
_VAGUE = re.compile(
    r'\b(km|mi|miles?|bei|nahe|near|nördl|südl|östl|westl|zwischen|between|'
    r'vom|von|neben|unweit|north|south|east|west|etwa|j\.|'
    r'Flußübergang|crossing|Mündung|mouth|branch|'
    r'Hr\.|Henchir|probably|barrington|miller|pleiades)\b', re.I)

_LOCATIONAL = re.compile(
    r'^\s*(where|am |an der |westl|östl|nördl|südl|bei |near |'
    r'zwischen |mouth|branch|crossing|Mündung)', re.I)

# ── River prefix/suffix stripping ─────────────────────────────────────────
_RIVER_PREFIX = re.compile(
    r'^(Fiume|Torrente|Oued|Wadi|Nahr\s+el-|Nahr\s+|F\.\s+|Fl\.\s+|'
    r'Râul\s+|Rîul\s+|Rivière\s+|Río\s+|Rio\s+)\s*', re.I)
_RIVER_SUFFIX = re.compile(
    r'\s+(Çay[ı]?|Irmağı|Irmak|Nehri|Dere[si]?|Bach|Ache|'
    r'Nehir|Çayı|fluss|rivier|rivière|nehri)$', re.I)

def clean_modern(raw):
    """Return (cleaned_name, confidence 0–3) or (None, 0) to skip."""
    s = (raw or "").strip()
    if len(s) < 3:
        return None, 0
    if _VAGUE.search(s) or _LOCATIONAL.match(s):
        return None, 0
    if re.match(r'^\d', s):
        return None, 0

    conf = 3

    # Strip leading/trailing "?"
    has_question = "?" in s
    s = s.lstrip("? ").rstrip("? ").strip()
    if has_question:
        conf = 1

    # Multiple alternatives — take first
    if "/" in s or re.search(r'\boder\b|\boder\b|\bo\.\b', s, re.I):
        parts = re.split(r'\s*/\s*|\s+oder\s+|\s+o\.\s+', s, flags=re.I)
        s = parts[0].strip()
        conf = min(conf, 1)

    # Strip surrounding parentheses/brackets
    s = re.sub(r'^\s*[\(\[]', '', s).strip()
    s = re.sub(r'[\)\]]\s*$', '', s).strip()
    # Strip source tags [1], [5], (Barrington) etc.
    s = re.sub(r'\s*\[\d+\]\s*', ' ', s).strip()
    s = re.sub(r'\s*\(Barrington\)\s*|\s*\(Miller\)\s*', ' ', s, flags=re.I).strip()
    s = s.rstrip('.,;~').strip("? ")

    if len(s) < 3:
        return None, 0

    if conf == 3 and s != (raw or "").strip():
        conf = 2

    return s, conf


def _strip_river_affixes(name):
    """Return name with river prefixes/suffixes removed for cleaner searching."""
    s = _RIVER_PREFIX.sub('', name).strip()
    s = _RIVER_SUFFIX.sub('', s).strip()
    return s if len(s) >= 3 else name


def lang_order(name):
    """Language priority for Wikipedia searches."""
    n = name.lower()
    if re.search(r'\boued\b|\bwadi\b|\bnahr\b', n):
        return ["en", "fr", "ar", "de"]
    if re.search(r'çay|ırmak|irmak|dere|nehri', n):
        return ["en", "tr", "de"]
    if re.search(r'\btorrente\b|\bfiume\b|\bfiumara\b|\bfosso\b', n):
        return ["en", "it", "de", "fr"]
    if re.search(r'\bbach\b|\bache\b', n):
        return ["en", "de", "it"]
    if re.search(r'\brivière\b|\bsaône\b|\bgaron\b', n):
        return ["en", "fr", "de"]
    if re.search(r'[Ͱ-Ͽ]', name):
        return ["el", "en"]
    return ["en", "de", "it", "fr"]


def _name_variants(name):
    """Generate search variants — clean stem + 'river' suffix for disambiguation."""
    variants = [name]
    stem = _strip_river_affixes(name)
    if stem != name:
        variants.append(stem)
    # Try with explicit "(river)" suffix for disambiguation
    if not re.search(r'\briver\b|\brivière\b|\brivier\b', name, re.I):
        variants.append(f"{stem} river")
    return list(dict.fromkeys(variants))  # deduplicate preserving order


# ── Wikipedia fetch ───────────────────────────────────────────────────────
_GENERIC_RIVER = {
    "fiume", "torrente", "oued", "wadi", "nahr", "river", "rivière",
    "bach", "ache", "dere", "çay", "irmak", "nehri", "nehir",
    "fluss", "fl", "stream", "creek",
}

def _title_match_ok(name, title):
    n, t = name.lower(), title.lower()
    if n in t or t in n:
        return True
    t_words = set(re.split(r"\W+", t))
    key = [w for w in re.split(r"\W+", n) if len(w) >= 4 and w not in _GENERIC_RIVER]
    if key:
        return all(w in t_words for w in key)
    first = re.split(r"\W+", n)[0] if n else ""
    return len(first) >= 4 and first in t_words


def _fetch_json(url, retries=2):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (tabula-peutingeriana research)",
        "Accept": "application/json"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                time.sleep(4 * (attempt + 1))
                continue
            raise


def wiki_search(name):
    """Try Wikipedia in language-priority order. Returns (url, lat, lng, lang, title, match_type)."""
    for lang in lang_order(name):
        for variant in _name_variants(name):
            q = urllib.parse.quote(variant, safe="")
            search_url = (f"https://{lang}.wikipedia.org/w/api.php"
                          f"?action=opensearch&search={q}&limit=5&format=json&redirects=resolve")
            try:
                result = _fetch_json(search_url)
                titles = result[1] if result and len(result) > 1 else []
                if not titles:
                    time.sleep(0.4)
                    continue
                best = next((t for t in titles
                             if t.lower() in (name.lower(), variant.lower())), None)
                match_type = "exact"
                if best is None:
                    best = next((t for t in titles if _title_match_ok(variant, t)), None)
                    match_type = "partial"
                if best is None:
                    time.sleep(0.4)
                    continue
                title_q = urllib.parse.quote(best.replace(" ", "_"), safe="")
                summary = _fetch_json(
                    f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title_q}")
                coords = summary.get("coordinates")
                if coords:
                    url = summary["content_urls"]["desktop"]["page"]
                    return url, float(coords["lat"]), float(coords["lon"]), lang, best, match_type
            except Exception:
                pass
            time.sleep(0.4)
    return None, None, None, None, None, None


# ── Country bbox ──────────────────────────────────────────────────────────
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


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Loading {DB_PATH} …")
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)
    records = db["records"]

    def best_modern(r):
        return (r.get("modern_preferred") or r.get("modern_omnesviae")
                or r.get("modern_tabula") or r.get("modern_state") or "")

    targets = [r for r in records
               if r.get("type") == "river" and best_modern(r) and not r.get("wiki_url")]
    print(f"Rivers with modern name, no wiki_url: {len(targets)}  (min-conf={MIN_CONF})\n")

    results = []
    seq = 0

    for rec in targets:
        raw = best_modern(rec)
        name, base_conf = clean_modern(raw)
        latin = (rec.get("latin_std") or rec.get("latin") or "")[:30]
        data_id = rec["data_id"]

        if not name or base_conf < MIN_CONF:
            print(f"  [{data_id:8d}] SKIP  {raw[:55]!r}")
            continue

        print(f"  [{data_id:8d}] {latin:30s} '{name[:35]}' … ", end="", flush=True)

        wiki_url, lat, lng, lang, article_title, match_type = wiki_search(name)

        if lat is None:
            print("not found")
            continue

        conf = base_conf
        if match_type == "exact":
            conf = min(3, conf + 1) if conf < 3 else 3

        if conf < MIN_CONF:
            print(f"conf={conf} below threshold")
            continue

        seq += 1
        country = guess_country_bbox(lat, lng)
        results.append((seq, rec, name, conf, wiki_url, lat, lng, lang, article_title or name, country))
        print(f"[{seq}] conf={conf}  {lat:.4f},{lng:.4f}  {country or '?':2}  ({lang}/{match_type})  → {article_title}")

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{'═'*90}")
    print(f"{'#':>4}  {'data_id':>8}  {'name':28}  {'c'}  {'lat':>9}  {'lng':>9}  {'ct'}  wiki_url")
    print(f"{'─'*90}")
    for seq, rec, name, conf, wiki_url, lat, lng, lang, atitle, country in results:
        mark = "✓" if (ACCEPT_IDS and seq in ACCEPT_IDS) else " "
        print(f"{mark}{seq:>4}  {rec['data_id']:>8}  {name:28}  {conf}  {lat:>9.4f}  {lng:>9.4f}"
              f"  {country or '??':2}  {(wiki_url or '—')[:55]}")

    if not results:
        print("No candidates found.")
        return

    if not WRITE and not ACCEPT_IDS:
        print(f"\nDry run.  --write to accept all  |  --accept 1,2,3 --write for specific")
        return

    apply_all = WRITE and not ACCEPT_IDS
    saved = 0
    for seq, rec, name, conf, wiki_url, lat, lng, lang, atitle, country in results:
        if not (apply_all or seq in ACCEPT_IDS):
            continue
        if wiki_url and not rec.get("wiki_url"):
            rec["wiki_url"] = wiki_url
        if rec.get("lat") is None and lat is not None:
            rec["lat"] = round(lat, 6)
            rec["lng"] = round(lng, 6)
        if country and not rec.get("country"):
            rec["country"] = country
        saved += 1

    tmp = DB_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DB_PATH)
    print(f"\n✓ Saved {saved} entries → {DB_PATH.name}")


if __name__ == "__main__":
    main()
