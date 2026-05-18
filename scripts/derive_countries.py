#!/usr/bin/env python3
"""
Derive missing countries for city records in review_places_db.json.

Strategy (in order of preference):
  1. tabula-peutingeriana.de list pages — match by KML id (= data_id) then
     by normalized Latin name → use the website's "lkz" (Länderkennzeichen).
  2. Lat/lng bounding-box lookup (existing coordinates in DB).
  3. ULM page (tp-online.ku.de) for still-unresolved entries:
       a. Parse Pleiades URL → fetch Pleiades JSON → reprPoint → bbox lookup.
       b. Map "Großraum" (ULM broad-region field) to ISO2 as last resort.

Usage:
  python scripts/derive_countries.py          # dry run — shows changes only
  python scripts/derive_countries.py --write  # apply changes and save
"""

import re, sys, json, time, urllib.request
from pathlib import Path

DB_PATH  = Path(__file__).parent.parent / "public/data/review_places_db.json"
WRITE    = "--write" in sys.argv

# ── Country code mapping ───────────────────────────────────────────────────
# Maps tabula-peutingeriana.de "lkz" codes → ISO 3166-1 alpha-2
LKZ_TO_ISO2 = {
    "A":"AT","AL":"AL","ARM":"AM","AZ":"AZ","B":"BE","BIH":"BA","BG":"BG",
    "CH":"CH","CY":"CY","CZ":"CZ","D":"DE","DZ":"DZ","E":"ES","EG":"EG",
    "ET":"EG","F":"FR","GB":"GB","GE":"GE","GR":"GR","H":"HU","HR":"HR",
    "I":"IT","IL":"IL","IND":"IN","IR":"IR","IRQ":"IQ","IRE":"IE","JOR":"JO",
    "LAR":"LY","LB":"LB","LU":"LU","MA":"MA","MK":"MK","MNE":"ME","NL":"NL",
    "P":"PT","PAK":"PK","PL":"PL","AFG":"AF","TM":"TM","RL":"LB","RO":"RO",
    "RS":"RS","RU":"RU","RUS":"RU","SI":"SI","SK":"SK","SLO":"SI","SYR":"SY",
    "TN":"TN","TR":"TR","UA":"UA","V":"VA","XK":"XK","YU":"RS",
    # extra codes seen in the data
    "RO":"RO","PL":"PL","LT":"LT","LV":"LV","EE":"EE",
}

# ── Lat/lng bounding boxes ─────────────────────────────────────────────────
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
    if lat is None or lng is None:
        return None
    la, lo = float(lat), float(lng)
    best, best_area = None, float("inf")
    for iso, la1, la2, lo1, lo2 in COUNTRY_BBOX:
        if la1 <= la <= la2 and lo1 <= lo <= lo2:
            area = (la2 - la1) * (lo2 - lo1)
            if area < best_area:
                best_area = area; best = iso
    return best

# ── Großraum → ISO2 (rough region labels from ULM) ───────────────────────
GROSSRAUM_ISO2 = {
    "indien": "IN",
    "china": "CN",
    "ägypten": "EG",
    "mesopotamien": "IQ",
    "arabien": None,          # too broad
    "nordafrika": None,
    "mittelmeerinseln": "IT", # Sicily / Sardinia default
    "hispanien": "ES",
    "gallien": "FR",
    "britannien": "GB",
    "germanien": "DE",
    "pannonien": "HU",
    "griechenland": "GR",
    "kleinasien": "TR",
    "syrien": "SY",
    "palästina": "IL",
    "persien": "IR",
    "armenien": "AM",
    "kaukasus": "GE",
    "zentralasien": "TM",
    "afghanistan": "AF",
    "pakistan": "PK",
}

def grossraum_to_iso2(text):
    if not text:
        return None
    t = text.lower()
    for key, iso in GROSSRAUM_ISO2.items():
        if key in t:
            return iso
    return None

# ── ULM page parser ────────────────────────────────────────────────────────
def _ulm_cell(html, label):
    m = re.search(re.escape(label) + r".*?</td>\s*<td[^>]*>(.*?)</td>",
                  html, re.DOTALL | re.IGNORECASE)
    if m:
        raw = re.sub(r"<[^>]+>", " ", m.group(1)).strip()
        return " ".join(raw.split())
    return None

def fetch_ulm_detail(ulm_id):
    """Fetch ULM page and return {pleiades_id, grossraum, barrington_name, wiki_url}."""
    url = f"https://tp-online.ku.de/trefferanzeige.php?id={ulm_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        html = r.read().decode("utf-8", errors="replace")

    m_pleiades = re.search(r"pleiades\.stoa\.org/places/(\d+)", html)
    m_wiki     = re.search(r"(https?://[a-z]+\.wikipedia\.org[^\s\"<]+)", html)
    grossraum  = _ulm_cell(html, "Großraum:")
    modern_raw = _ulm_cell(html, "Name (modern):")

    # Clean the modern/Barrington name: strip trailing "(Barrington)" and qualifiers
    barrington = None
    if modern_raw and modern_raw not in ("&nbsp", "---", ""):
        b = re.sub(r"\s*\(Barrington\)\s*$", "", modern_raw, flags=re.IGNORECASE).strip()
        b = re.sub(r"\s*\?$", "", b).strip()
        # Reject vague descriptions
        if not re.search(r"\bsettlement\b|\bunknown\b|\btal\b|\bvalley\b|\briver\b",
                         b, re.IGNORECASE) and len(b) > 1:
            # If "oder" (German "or"), take first alternative
            parts = re.split(r"\s+oder\s+", b, flags=re.IGNORECASE)
            barrington = parts[0].strip()

    return {
        "pleiades_id":   m_pleiades.group(1) if m_pleiades else None,
        "grossraum":     grossraum,
        "barrington":    barrington,
        "wiki_url":      m_wiki.group(1) if m_wiki else None,
    }

def fetch_pleiades_coords(pleiades_id):
    """Return (lat, lng) from Pleiades using reprPoint → bbox → feature/location geometry."""
    url = f"https://pleiades.stoa.org/places/{pleiades_id}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.load(r)
    if "unlocated" in data.get("placeTypes", []):
        return None, None
    pt = data.get("reprPoint")
    if pt and len(pt) == 2:
        return float(pt[1]), float(pt[0])
    bb = data.get("bbox")
    if bb and len(bb) == 4:
        return (bb[1] + bb[3]) / 2, (bb[0] + bb[2]) / 2
    for feat in data.get("features", []):
        geom = feat.get("geometry") or {}
        if geom.get("type") == "Point":
            c = geom.get("coordinates", [])
            if len(c) >= 2:
                return float(c[1]), float(c[0])
    for loc in data.get("locations", []):
        geom = loc.get("geometry") or {}
        if geom.get("type") == "Point":
            c = geom.get("coordinates", [])
            if len(c) >= 2:
                return float(c[1]), float(c[0])
    return None, None

# ── Latin name normalization for fuzzy matching ────────────────────────────
def norm_latin(s):
    """Lowercase, strip punctuation and special chars used in TP names."""
    s = s.lower()
    s = re.sub(r"[·.\[\]~\s\-\']+", "", s)  # middle dots, brackets, hyphens
    s = s.replace("v", "u")                  # V/U equivalence in Latin
    return s

# ── Fetch and parse one segment list page ─────────────────────────────────
def fetch_segment(segm):
    """Returns list of {id, latin, lkz} dicts for one segment page."""
    url = f"https://www.tabula-peutingeriana.de/list.html?segm={segm}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", errors="replace")

    entries = []
    for block in re.split(r'<div class="row locus">', html)[1:]:
        m_latin = re.search(r"<b[^>]*>([^<]+)</b>", block)
        m_lkz   = re.search(r'<div class="lkz">([^<]*)</div>', block)
        m_id    = re.search(r"make_kml\.php\?id=(\d+)", block)
        if not m_latin:
            continue
        latin = m_latin.group(1).strip()
        if latin in ("[ ? ]", "[?]", ""):
            continue  # unnamed entry
        entries.append({
            "id":    int(m_id.group(1)) if m_id else None,
            "latin": latin,
            "lkz":   m_lkz.group(1).strip() if m_lkz else None,
        })
    return entries

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Loading {DB_PATH} …")
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)
    records = db["records"]

    # Collect city records without country
    targets = [r for r in records if r.get("type") == "city" and not r.get("country")]
    print(f"Cities without country: {len(targets)}\n")

    # ── Scrape tabula-peutingeriana.de (segments 2–12 → segm=1..11) ────────
    print("Fetching segment list pages …")
    # Build lookup maps: kml_id → iso2, norm_latin → iso2
    by_kml  = {}   # int → iso2
    by_name = {}   # norm_latin_str → iso2  (last write wins)

    for segm in range(1, 12):  # segm 1..11 → segments II..XII
        seg_label = segm + 1
        print(f"  segm={segm}  (Segment {seg_label}) … ", end="", flush=True)
        try:
            entries = fetch_segment(segm)
            print(f"{len(entries)} entries")
            for e in entries:
                iso2 = LKZ_TO_ISO2.get(e["lkz"]) if e["lkz"] else None
                if not iso2:
                    continue
                if e["id"] is not None:
                    by_kml[e["id"]] = iso2
                key = norm_latin(e["latin"])
                if key:
                    by_name[key] = iso2
        except Exception as ex:
            print(f"ERROR: {ex}")
        time.sleep(0.4)  # be polite

    print(f"\nBuilt lookup: {len(by_kml)} by-id, {len(by_name)} by-name\n")

    # ── Assign countries ───────────────────────────────────────────────────
    changes = []
    unresolved = []

    for rec in targets:
        data_id  = rec.get("data_id")
        latin    = rec.get("latin_std") or rec.get("latin") or ""
        lat, lng = rec.get("lat"), rec.get("lng")
        country  = None
        source   = None

        # 1) Match by KML id (= data_id on the website)
        if data_id is not None and int(data_id) in by_kml:
            country = by_kml[int(data_id)]
            source  = "tp-de/id"

        # 2) Match by normalized Latin name
        if not country:
            key = norm_latin(latin)
            if key and key in by_name:
                country = by_name[key]
                source  = "tp-de/name"

        # 3) Lat/lng bounding box fallback
        if not country:
            country = guess_country_bbox(lat, lng)
            if country:
                source = "bbox"

        if country:
            changes.append((rec, country, source))
        else:
            unresolved.append(rec)

    # ── Pass 3: ULM page → Pleiades coords or Großraum ────────────────────
    still_unresolved = []
    if unresolved:
        print(f"\nFetching ULM pages for {len(unresolved)} still-unresolved entries …")
        for rec in unresolved:
            ulm_id = rec.get("ulm_id")
            latin  = rec.get("latin_std") or rec.get("latin") or ""
            if not ulm_id:
                still_unresolved.append(rec)
                continue
            print(f"  ULM {ulm_id}  {latin} … ", end="", flush=True)
            country = None
            source  = None
            try:
                detail = fetch_ulm_detail(ulm_id)
                time.sleep(0.3)

                # 3a. Pleiades coordinates
                if detail["pleiades_id"]:
                    lat, lng = fetch_pleiades_coords(detail["pleiades_id"])
                    time.sleep(0.3)
                    if lat is not None:
                        country = guess_country_bbox(lat, lng)
                        if country:
                            source = f"pleiades/{detail['pleiades_id']}"
                            # Also store coordinates back into the record
                            rec["lat"] = round(lat, 6)
                            rec["lng"] = round(lng, 6)

                # 3b. Großraum label
                if not country and detail["grossraum"]:
                    country = grossraum_to_iso2(detail["grossraum"])
                    if country:
                        source = f"grossraum/{detail['grossraum'][:20]}"

                # 3c. Direct Wikipedia URL from ULM page
                if detail["wiki_url"] and not rec.get("wiki_url"):
                    rec["wiki_url"] = detail["wiki_url"]
                    print(f"(wiki_url set) ", end="")

            except Exception as ex:
                print(f"error: {ex}")

            if country:
                print(country)
                changes.append((rec, country, source))
            else:
                print("unresolved")
                still_unresolved.append(rec)

    unresolved = still_unresolved

    # ── Report ────────────────────────────────────────────────────────────
    print(f"Resolved {len(changes)}/{len(targets)} entries:")
    by_source = {}
    for rec, country, source in changes:
        by_source.setdefault(source, []).append((rec, country))
        latin = rec.get("latin_std") or rec.get("latin") or ""
        print(f"  [{source:12s}] {country}  data_id={rec.get('data_id')}  {latin}")

    if unresolved:
        print(f"\nUnresolved ({len(unresolved)}):")
        for rec in unresolved:
            latin = rec.get("latin_std") or rec.get("latin") or ""
            print(f"  data_id={rec.get('data_id')} seg={rec.get('tabula_segment')}  {latin}")

    if not WRITE:
        print("\nDry run — pass --write to apply changes.")
        return

    # ── Apply and save ────────────────────────────────────────────────────
    for rec, country, _ in changes:
        rec["country"] = country

    tmp = DB_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DB_PATH)
    print(f"\n✓ Saved {len(changes)} changes → {DB_PATH.name}")

if __name__ == "__main__":
    main()
