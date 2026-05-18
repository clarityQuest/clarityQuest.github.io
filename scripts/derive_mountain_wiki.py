#!/usr/bin/env python3
"""
Find Wikipedia articles + geo-coordinates for mountain records.

Strategy:
  1. Use modern_preferred / modern_omnesviae / modern_tabula as search term
  2. Choose Wikipedia language by name pattern (Djebel→FR, Dağ→TR, Monte→IT, etc.)
  3. Fetch Wikidata entity search as final fallback
  4. Score match confidence (0–3) and show results for user review

Confidence scale:
  3 — exact title match (case-insensitive), geo-tagged article
  2 — all distinctive words (≥5 chars) appear in article title, geo-tagged
  1 — first-word only match or Wikidata fuzzy match, geo-tagged (needs review)
  0 — skipped (name too vague, contains ?, too short)

Usage:
  python scripts/derive_mountain_wiki.py              # dry-run, shows candidates
  python scripts/derive_mountain_wiki.py --min-conf 2 # only show conf >= 2
  python scripts/derive_mountain_wiki.py --write      # apply changes
  python scripts/derive_mountain_wiki.py --accept 1,3,5  # accept specific result numbers
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
    r'Hr\.|Henchir|Ruinen|ruins|road.station|plateau)\b', re.I)

def clean_modern(raw):
    """Return (cleaned_name, confidence 0-3) or (None, 0) to skip."""
    s = (raw or "").strip()
    if len(s) < 3:
        return None, 0
    if _VAGUE.search(s):
        return None, 0
    if re.match(r'^\d', s):
        return None, 0

    conf = 3

    # Strip leading/trailing "?" and lower confidence
    has_question = "?" in s
    s = s.lstrip("? ").rstrip("? ").strip()
    if has_question:
        conf = 1

    if "/" in s or re.search(r'\boder\b', s, re.I):
        parts = re.split(r'\s*/\s*|\s+oder\s+', s, flags=re.I)
        s = parts[0].strip()
        conf = min(conf, 1)

    # Strip surrounding parentheses/brackets (leading OR trailing)
    s = re.sub(r'^\s*[\(\[]', '', s).strip()   # leading ( or [
    s = re.sub(r'[\)\]]\s*$', '', s).strip()   # trailing ) or ]
    s = re.sub(r'\s*\[\d+\]\s*', ' ', s).strip()
    s = s.rstrip('.,;').strip("? ")

    if len(s) < 3:
        return None, 0

    if conf == 3 and s != (raw or "").strip():
        conf = 2

    return s, conf


# ── Language ordering based on name patterns ──────────────────────────────
def lang_order(name):
    """Return list of Wikipedia language codes to try, most promising first.
    EN is always tried — it has the best coordinate coverage.
    'la' (Latin Wikipedia) is a useful fallback for ancient names.
    'ceb' (Cebuano) has many bot-generated geo-tagged articles for obscure locations."""
    n = name.lower()
    if re.search(r'\bdjebel\b|\bjebel\b|\bdjad\b', n):
        return ["en", "fr", "ar", "ceb", "de", "la"]
    if re.search(r'\bdağ\b|\bdaği\b|\bdagh\b|\bdag\b', n):
        return ["en", "tr", "de", "la"]
    if re.search(r'\bmonte\b|\bmonti\b|\balpi\b', n):
        return ["en", "it", "de", "fr", "la"]
    if re.search(r'\bsierra\b|\bcordillera\b', n):
        return ["en", "es", "fr", "la"]
    if re.search(r'\balpes\b|\balps\b|\balpen\b|\balpine\b', n):
        return ["en", "fr", "de", "it", "la"]
    if re.search(r'\bplanina\b|\bgorje\b|\bhor[ay]\b', n):
        return ["en", "sr", "hr", "bg", "de"]
    if re.search(r'\bmons\b|\bmontes\b|\bmont[es]\b', n, re.I):
        # Ancient Latin names — try Latin Wikipedia first
        return ["la", "en", "de", "fr", "it"]
    if re.search(r'[Ͱ-Ͽ]', name):   # Greek chars
        return ["el", "en", "de"]
    return ["en", "de", "fr", "it", "la"]


def _name_variants(name):
    """Generate search variants for a name.
    - Turkish 'Boz Dağ' → 'Bozdağ', 'Bozdağlar'
    - Latin 'Mons Imaus' → 'Imaus', 'Mount Imaus', 'Imeon'
    - Any name → also try 'Mount {name}' to catch mountain-specific articles
    """
    variants = [name]
    # Turkish: "Boz Dağ" → "Bozdağ", "Bozdağlar"
    dag_m = re.match(r'^(\w+)\s+[Dd]a[ğg]ı?$', name)
    if dag_m:
        stem = dag_m.group(1)
        variants += [f"{stem}dağ", f"{stem}dağlar"]
    # Latin: "Mons X" → "X", "Mount X"
    mons_m = re.match(r'^Mons\s+(\w+)$', name, re.I)
    if mons_m:
        stem = mons_m.group(1)
        variants += [stem, f"Mount {stem}"]
    # "Alpes X" → "X Alps", "X"
    alpes_m = re.match(r'^(?:Alpes|Alpen)\s+(.+)$', name, re.I)
    if alpes_m:
        stem = alpes_m.group(1)
        variants += [f"{stem} Alps", stem]
    # General: also try "Mount {name}" if no prefix already
    if not re.match(r'^(Mount|Mons|Mont|Monte|Monti|Alpes?)\b', name, re.I):
        variants.append(f"Mount {name}")
    return variants


# ── Wikipedia lookup ──────────────────────────────────────────────────────
def _fetch_json(url, retries=2):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (tabula-peutingeriana research)",
                                               "Accept": "application/json"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                time.sleep(3 * (attempt + 1))
                continue
            raise

_GENERIC = {
    "isola","isla","ile","iles","island","insula",
    "fiume","fluss","flumen","fluvius","river","riviere",
    "mons","monts","monte","mont","berg","berge","gebirge","dagh","dag",
    "lago","lake","lacus","lacum","sinus","meer","mare",
    "portus","port","capo","cape","kap",
    "henchir","hench","djebel","jebel","sierra","alpes","alps","alpen",
    "planina","gorje","montes",
}

def _title_match_ok(name, title):
    n, t = name.lower(), title.lower()
    if n in t or t in n:
        return True
    t_words = set(re.split(r"\W+", t))
    key = [w for w in re.split(r"\W+", n) if len(w) >= 5 and w not in _GENERIC]
    if key:
        return all(w in t_words for w in key)
    first = re.split(r"\W+", n)[0] if n else ""
    return len(first) >= 4 and first in t_words

def _match_conf(name, title):
    """Return match confidence contribution: 1 for exact, 0 for partial."""
    return 1 if name.lower() == title.lower() else 0


def wiki_search(name):
    """
    Try Wikipedia in language-priority order, including name variants.
    Returns (wiki_url, lat, lng, lang_used, article_title, match_type) or all-None tuple.
    """
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
                # Prefer exact match on original name or variant
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
                summary_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title_q}"
                summary = _fetch_json(summary_url)
                coords = summary.get("coordinates")
                if coords:
                    url = summary["content_urls"]["desktop"]["page"]
                    return url, float(coords["lat"]), float(coords["lon"]), lang, best, match_type
            except Exception:
                pass
            time.sleep(0.4)
    return None, None, None, None, None, None


def wikidata_search(name):
    """
    Search Wikidata for a geo-tagged entity matching `name`.
    Returns (wiki_url, lat, lng, label) or all-None.
    """
    q = urllib.parse.quote(name, safe="")
    search_url = (f"https://www.wikidata.org/w/api.php"
                  f"?action=wbsearchentities&search={q}&language=en"
                  f"&type=item&limit=5&format=json")
    try:
        result = _fetch_json(search_url)
        items = result.get("search", [])
        for item in items:
            label = item.get("label", "")
            if not _title_match_ok(name, label):
                continue
            qid = item["id"]
            sparql = (f"https://query.wikidata.org/sparql?format=json&query="
                      + urllib.parse.quote(
                          f"SELECT ?coords ?enwiki WHERE {{"
                          f"  wd:{qid} wdt:P625 ?coords ."
                          f"  OPTIONAL {{ ?enwiki schema:about wd:{qid} ; "
                          f"schema:isPartOf <https://en.wikipedia.org/> }}"
                          f"}}", safe=""))
            try:
                sparql_result = _fetch_json(sparql)
                bindings = sparql_result.get("results", {}).get("bindings", [])
                if bindings:
                    coord_str = bindings[0]["coords"]["value"]
                    m = re.search(r"Point\(([-\d.]+)\s+([-\d.]+)\)", coord_str)
                    if m:
                        lng, lat = float(m.group(1)), float(m.group(2))
                        wiki_url = bindings[0].get("enwiki", {}).get("value")
                        return wiki_url, lat, lng, label
            except Exception:
                pass
            time.sleep(0.3)
    except Exception:
        pass
    return None, None, None, None


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Loading {DB_PATH} …")
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)
    records = db["records"]

    mountains = [r for r in records
                 if r.get("type") == "mountain" and r.get("lat") is None]
    print(f"Mountains without lat: {len(mountains)}")

    def best_modern(r):
        return (r.get("modern_preferred") or r.get("modern_omnesviae")
                or r.get("modern_tabula") or "")

    targets = [(r, best_modern(r)) for r in mountains if best_modern(r)]
    print(f"With modern name: {len(targets)}  (min-conf={MIN_CONF})\n")

    results = []   # list of (seq_no, rec, name, conf, wiki_url, lat, lng, src, article_title)
    seq = 0

    for rec, raw in targets:
        name, base_conf = clean_modern(raw)
        latin = (rec.get("latin_std") or rec.get("latin") or "")[:35]
        data_id = rec["data_id"]

        if not name or base_conf < MIN_CONF:
            print(f"  [{data_id:8d}] SKIP  {raw!r}  (conf={base_conf})")
            continue

        print(f"  [{data_id:8d}] {latin:35s}  '{name}' … ", end="", flush=True)

        wiki_url, lat, lng, lang, article_title, match_type = wiki_search(name)
        src = "wiki"

        if lat is None:
            print("→ no Wikipedia match, trying Wikidata … ", end="", flush=True)
            wiki_url, lat, lng, article_title = wikidata_search(name)
            lang = "wikidata"
            match_type = "wikidata"
            src = "wikidata"
            time.sleep(0.3)

        if lat is None:
            print("not found")
            continue

        # Final confidence: base_conf + exact-match bonus
        conf = base_conf
        if match_type == "exact":
            conf = min(3, conf + 1) if conf < 3 else 3
        elif match_type == "wikidata":
            conf = min(conf, 1)

        if conf < MIN_CONF:
            print(f"conf={conf} below threshold, skip")
            continue

        seq += 1
        country = guess_country_bbox(lat, lng)
        results.append((seq, rec, name, conf, wiki_url, lat, lng, lang, article_title or name, country))
        print(f"[{seq}] conf={conf}  {lat:.4f},{lng:.4f}  {country or '?'}  ({lang}/{match_type})  → {article_title}")

    # ── Summary table ─────────────────────────────────────────────────────
    print(f"\n{'═'*80}")
    print(f"{'#':>3}  {'data_id':>8}  {'name':30}  {'conf'}  {'lat':>9}  {'lng':>9}  {'ctry'}  wiki_url")
    print(f"{'─'*80}")
    for seq, rec, name, conf, wiki_url, lat, lng, lang, atitle, country in results:
        mark = "✓" if (ACCEPT_IDS and seq in ACCEPT_IDS) else " "
        print(f"{mark}{seq:>3}  {rec['data_id']:>8}  {name:30}  {conf}     {lat:>9.4f}  {lng:>9.4f}"
              f"  {country or '??':2}    {(wiki_url or '—')[:60]}")

    if not results:
        print("No candidates found.")
        return

    if not WRITE and not ACCEPT_IDS:
        print(f"\nDry run. To accept specific results: --accept 1,2,3 --write")
        print(f"To accept all conf>={MIN_CONF}: --write")
        return

    # ── Apply ─────────────────────────────────────────────────────────────
    apply_all = WRITE and not ACCEPT_IDS
    saved = 0
    for seq, rec, name, conf, wiki_url, lat, lng, lang, atitle, country in results:
        if not (apply_all or seq in ACCEPT_IDS):
            continue
        rec["lat"] = round(lat, 6)
        rec["lng"] = round(lng, 6)
        if wiki_url and not rec.get("wiki_url"):
            rec["wiki_url"] = wiki_url
        if country and not rec.get("country"):
            rec["country"] = country
        saved += 1

    if WRITE or ACCEPT_IDS:
        tmp = DB_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(DB_PATH)
        print(f"\n✓ Saved {saved} entries → {DB_PATH.name}")


if __name__ == "__main__":
    main()
