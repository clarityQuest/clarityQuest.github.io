#!/usr/bin/env python3
"""
Derive lat/lng from Pleiades for records with ulm_id but no coordinates.
Also derives country from the new coordinates, and stores the Barrington
modern name into modern_preferred when that field is currently empty.

Usage:
  python scripts/derive_geolocations.py              # dry-run, all types
  python scripts/derive_geolocations.py --type city  # cities only
  python scripts/derive_geolocations.py --write      # apply changes
  python scripts/derive_geolocations.py --type city --write
"""

import re, sys, json, time, urllib.request
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "public/data/review_places_db.json"
WRITE   = "--write" in sys.argv

TYPE_FILTER = None  # None = all types
if "--type" in sys.argv:
    idx = sys.argv.index("--type")
    if idx + 1 < len(sys.argv):
        val = sys.argv[idx + 1]
        TYPE_FILTER = None if val == "all" else val

# ── Country bounding-box table (copied from derive_countries.py) ──────────
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


def _ulm_cell(html, label):
    m = re.search(re.escape(label) + r".*?</td>\s*<td[^>]*>(.*?)</td>",
                  html, re.DOTALL | re.IGNORECASE)
    if m:
        raw = re.sub(r"<[^>]+>", " ", m.group(1)).strip()
        return " ".join(raw.split())
    return None


def fetch_ulm_detail(ulm_id):
    """Return {pleiades_id, grossraum, barrington, wiki_url} from ULM page."""
    url = f"https://tp-online.ku.de/trefferanzeige.php?id={ulm_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        html = r.read().decode("utf-8", errors="replace")

    m_pleiades = re.search(r"pleiades\.stoa\.org/places/(\d+)", html)
    m_wiki     = re.search(r"(https?://[a-z]+\.wikipedia\.org[^\s\"<]+)", html)
    grossraum  = _ulm_cell(html, "Großraum:")
    modern_raw = _ulm_cell(html, "Name (modern):")

    barrington = None
    if modern_raw and modern_raw not in ("&nbsp", "---", ""):
        b = re.sub(r"\s*\(Barrington\)\s*$", "", modern_raw, flags=re.IGNORECASE).strip()
        b = re.sub(r"\s*\?$", "", b).strip()
        if not re.search(r"\bsettlement\b|\bunknown\b|\btal\b|\bvalley\b|\briver\b",
                         b, re.IGNORECASE) and len(b) > 1:
            parts = re.split(r"\s+oder\s+", b, flags=re.IGNORECASE)
            barrington = parts[0].strip()

    return {
        "pleiades_id": m_pleiades.group(1) if m_pleiades else None,
        "grossraum":   grossraum,
        "barrington":  barrington,
        "wiki_url":    m_wiki.group(1) if m_wiki else None,
    }


def _fetch_pleiades_kml_coords(pleiades_id):
    """Return (lat, lng) from the KML endpoint's representativePointField, or (None, None)."""
    url = f"https://pleiades.stoa.org/places/{pleiades_id}/kml"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        kml = r.read().decode("utf-8", errors="replace")
    # Find the representativePointField Placemark coordinates (KML: lng,lat[,alt])
    m = re.search(
        r"representativePointField.*?<coordinates>\s*([-\d.]+),\s*([-\d.]+)",
        kml, re.DOTALL)
    if m:
        return float(m.group(2)), float(m.group(1))  # lat, lng
    return None, None


def fetch_pleiades_coords(pleiades_id):
    """Return (lat, lng, source_label) from Pleiades, trying multiple fallbacks.

    Fallback order:
      1. reprPoint  [lng, lat]  from JSON
      2. bbox centroid  [lon1, lat1, lon2, lat2]  from JSON
      3. First Point geometry in features[]  from JSON
      4. First Point geometry in locations[]  from JSON
      5. representativePointField from KML endpoint (works even when JSON
         returns placeTypes=['unlocated'] but the web page shows coordinates)
    Returns (None, None, reason_str) when no coords found.
    """
    url = f"https://pleiades.stoa.org/places/{pleiades_id}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.load(r)

    is_unlocated = "unlocated" in data.get("placeTypes", [])

    # 1. reprPoint [lng, lat]
    pt = data.get("reprPoint")
    if pt and len(pt) == 2:
        return float(pt[1]), float(pt[0]), "reprPoint"

    # 2. bbox centroid [lon1, lat1, lon2, lat2]
    bb = data.get("bbox")
    if bb and len(bb) == 4:
        return (bb[1] + bb[3]) / 2, (bb[0] + bb[2]) / 2, "bbox"

    # 3. First Point geometry in features
    for feat in data.get("features", []):
        geom = feat.get("geometry") or {}
        if geom.get("type") == "Point":
            c = geom.get("coordinates", [])
            if len(c) >= 2:
                return float(c[1]), float(c[0]), "feature/Point"

    # 4. First Point geometry in locations
    for loc in data.get("locations", []):
        geom = loc.get("geometry") or {}
        if geom.get("type") == "Point":
            c = geom.get("coordinates", [])
            if len(c) >= 2:
                return float(c[1]), float(c[0]), "location/Point"

    # 5. KML representativePointField — catches cases where the web page shows
    #    a centroid that the JSON API omits (e.g. placeTypes=['unlocated'])
    try:
        time.sleep(0.3)
        lat, lng = _fetch_pleiades_kml_coords(pleiades_id)
        if lat is not None:
            return lat, lng, "kml/reprPoint"
    except Exception:
        pass

    return None, None, "unlocated" if is_unlocated else "no geometry"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Loading {DB_PATH} …")
    with open(DB_PATH, encoding="utf-8") as f:
        db = json.load(f)
    records = db["records"]

    # Select records with ulm_id but no lat/lng
    if TYPE_FILTER:
        targets = [r for r in records
                   if r.get("ulm_id") and r.get("lat") is None
                   and r.get("type") == TYPE_FILTER]
    else:
        targets = [r for r in records
                   if r.get("ulm_id") and r.get("lat") is None]

    type_label = TYPE_FILTER or "all"
    print(f"Targets: {len(targets)} records with ulm_id but no lat/lng (type={type_label})\n")

    found_coords = 0
    found_country = 0
    errors = 0

    for i, rec in enumerate(targets, 1):
        ulm_id = rec["ulm_id"]
        latin  = rec.get("latin_std") or rec.get("latin") or ""
        print(f"[{i:4d}/{len(targets)}] ULM {ulm_id:5d}  {latin[:40]:40s} … ", end="", flush=True)

        try:
            detail = fetch_ulm_detail(ulm_id)
            time.sleep(0.5)

            if not detail["pleiades_id"]:
                print("no Pleiades")
                continue

            lat, lng, geo_src = fetch_pleiades_coords(detail["pleiades_id"])
            time.sleep(0.5)

            if lat is None:
                print(f"Pleiades {detail['pleiades_id']} — {geo_src}")
                continue

            rec["lat"] = round(lat, 6)
            rec["lng"] = round(lng, 6)
            found_coords += 1

            country = guess_country_bbox(lat, lng)
            if country and not rec.get("country"):
                rec["country"] = country
                found_country += 1

            if detail["barrington"] and not rec.get("modern_preferred"):
                rec["modern_preferred"] = detail["barrington"]

            suffix = f"  {country or '?':2s}  {detail['pleiades_id']} [{geo_src}]"
            print(f"{lat:.4f}, {lng:.4f}{suffix}")

        except Exception as ex:
            print(f"ERR: {ex}")
            errors += 1

    print(f"\n{'─'*60}")
    print(f"Coords found:  {found_coords} / {len(targets)}  (errors: {errors})")
    print(f"Countries set: {found_country}")

    if not WRITE:
        print("\nDry run — pass --write to apply changes.")
        return

    tmp = DB_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DB_PATH)
    print(f"\n✓ Saved {found_coords} lat/lng entries → {DB_PATH.name}")


if __name__ == "__main__":
    main()
