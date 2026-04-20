#!/usr/bin/env python3
"""
Scrape all place data from tabula-peutingeriana.de and generate places.json.

The site uses Bootstrap rows with class 'row locus' (or 'row regio', etc.)
Each row has structured columns:
  - col-md-5: Original Latin name (span.tp-orig) + standardized name (bold)
  - col-md-2: Type keyword + segment/grid link
  - col-md-5: Province (div.prov), country (div.lkz), modern name (italic), KML link
  - input[data-id]: Talbert reference ID

Usage:
    python scripts/scrape_places.py

Outputs: public/data/places.json

Attribution: Data sourced from tabula-peutingeriana.de by M. Weber.
"""

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.tabula-peutingeriana.de/"
OUTPUT = Path(__file__).resolve().parent.parent / "public" / "data" / "places.json"

LETTER_PAGES = ["!", "a", "b", "d", "i", "n", "s"]
ROW_CLASSES = ["locus", "regio", "gens", "aquae", "insula", "mons", "portus"]


def segm_to_number(s):
    try:
        v = int(s, 16)
    except ValueError:
        return None
    return v + 1


def fetch_page(url, session):
    for attempt in range(3):
        try:
            r = session.get(url, timeout=30)
            r.encoding = "utf-8"
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            print(f"  Retry {attempt+1}: {e}", file=sys.stderr)
            time.sleep(2)
    return None


def classify_type(row_class, type_text, full_text=""):
    rc = row_class.lower() if row_class else ""
    tt = type_text.lower().strip()
    ft = full_text.lower()
    if re.search(r"symb\.\s*(f\d|aa)", ft):
        return "major_city"
    if re.search(r"symb\.\s*ab", ft):
        return "city"
    if "regio" in rc:
        return "region"
    if "gens" in rc:
        return "people"
    if "aquae" in rc or "flumen" in tt or "fl(umen)" in tt:
        return "river"
    if "insula" in rc:
        return "island"
    if "mons" in rc:
        return "mountain"
    if "portus" in rc or "portvs" in tt:
        return "port"
    return "road_station"


def parse_row(row):
    classes = row.get("class", [])
    row_class = next((c for c in classes if c in ROW_CLASSES), "")

    col1 = row.find("div", class_=re.compile(r"col-md-5"))
    if not col1:
        return None

    bold = col1.find("b")
    latin = bold.get_text(strip=True) if bold else ""
    if not latin:
        orig = col1.find("span", class_="tp-orig")
        latin = orig.get_text(strip=True) if orig else ""
    if not latin:
        return None

    col2 = row.find("div", class_=re.compile(r"col-md-2"))
    type_text = ""
    segment = col_num = row_letter = None

    if col2:
        type_text = col2.get_text(strip=True)
        seg_link = col2.find("a", href=re.compile(r"tabula\.html\?segm="))
        if seg_link:
            href = seg_link.get("href", "")
            parsed = urlparse(href)
            params = parse_qs(parsed.query)
            fragment = parsed.fragment
            segm_str = params.get("segm", [None])[0]
            if segm_str:
                segment = segm_to_number(segm_str)
            if fragment and len(fragment) >= 2:
                row_letter = fragment[0].lower()
                try:
                    col_num = int(fragment[1])
                except ValueError:
                    pass

    if not segment or segment < 2 or not col_num or not row_letter:
        return None
    if row_letter not in ("a", "b", "c") or col_num < 1 or col_num > 5:
        return None

    all_col5 = row.find_all("div", class_=re.compile(r"col-md-5"))
    col3 = all_col5[1] if len(all_col5) > 1 else None
    region = country = modern = ""

    if col3:
        prov = col3.find("div", class_="prov")
        if prov:
            region = prov.get_text(strip=True)
        lkz = col3.find("div", class_="lkz")
        if lkz:
            country = lkz.get_text(strip=True)
        italic = col3.find("i")
        if italic:
            modern = italic.get_text(strip=True)

    place_id = None
    inp = row.find("input", attrs={"data-id": True})
    if inp:
        try:
            place_id = int(inp["data-id"])
        except (ValueError, KeyError):
            pass
    if not place_id:
        kml = row.find("a", class_="kml")
        if kml:
            m = re.search(r"id=(\d+)", kml.get("href", ""))
            if m:
                place_id = int(m.group(1))
    if not place_id:
        m = re.search(r"#(\d{2,5})\b", row.get_text())
        if m:
            place_id = int(m.group(1))

    ptype = classify_type(row_class, type_text, row.get_text())
    latin = re.sub(r"\s+", " ", latin).strip().strip(".,;: ")

    return {
        "id": place_id or 0,
        "latin": latin,
        "modern": modern,
        "segment": segment,
        "col": col_num,
        "row": row_letter,
        "type": ptype,
        "region": region,
        "country": country,
        "notes": ""
    }


def parse_page(soup):
    entries = []
    for row in soup.find_all("div", class_="row"):
        if not set(row.get("class", [])).intersection(ROW_CLASSES):
            continue
        entry = parse_row(row)
        if entry and entry["latin"]:
            entries.append(entry)
    return entries


def main():
    print("Tabula Peutingeriana Place Scraper v2")
    print("=" * 50)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "TabulaPeutingeriana-ResearchBot/1.0 (educational)",
    })

    all_entries = []

    for letter in LETTER_PAGES:
        url = f"{BASE_URL}list.html?alfa={letter}"
        print(f"Fetching {url} ...")
        soup = fetch_page(url, session)
        if not soup:
            print("  FAILED")
            continue
        entries = parse_page(soup)
        print(f"  Found {len(entries)} entries")
        all_entries.extend(entries)
        time.sleep(1.5)

    for typ, label in [("aqu", "waters"), ("reg", "regions"), ("gen", "peoples"),
                       ("ins", "islands"), ("mon", "mountains")]:
        url = f"{BASE_URL}list.html?typ={typ}"
        print(f"Fetching {url} ({label}) ...")
        soup = fetch_page(url, session)
        if not soup:
            continue
        entries = parse_page(soup)
        type_map = {"aqu": "river", "reg": "region", "gen": "people",
                    "ins": "island", "mon": "mountain"}
        for e in entries:
            if e["type"] == "road_station":
                e["type"] = type_map.get(typ, e["type"])
        print(f"  Found {len(entries)} entries")
        all_entries.extend(entries)
        time.sleep(1.5)

    by_id = {}
    for e in all_entries:
        if e["id"] and e["id"] > 0:
            key = e["id"]
            if key not in by_id:
                by_id[key] = e
            else:
                old = by_id[key]
                if not old["modern"] and e["modern"]:
                    old["modern"] = e["modern"]
                if not old["region"] and e["region"]:
                    old["region"] = e["region"]
                if not old["country"] and e["country"]:
                    old["country"] = e["country"]
        else:
            dedup = f"{e['latin']}_{e['segment']}_{e['row']}{e['col']}"
            e["id"] = abs(hash(dedup)) % 100000 + 50000
            if e["id"] not in by_id:
                by_id[e["id"]] = e

    final = sorted(by_id.values(), key=lambda x: (x["segment"], x["col"], x["row"]))

    MAJOR = ["Roma", "Constantinopolis", "Antiochia", "Alexandria", "Carthago",
             "Ravenna", "Mediolanum", "Aquileia", "Thessalonice", "Athenas",
             "Nicomedia", "Epheso", "Lugdunum", "Burdigala", "Massilia",
             "Lutetia", "Durocortorum", "Sirmium", "Neapolis", "Brundisium",
             "Augusta Taurinorum", "Londinium"]
    for e in final:
        for mc in MAJOR:
            if mc.lower() in e["latin"].lower():
                e["type"] = "major_city"
                break

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"\nTotal unique places: {len(final)}")
    print(f"Output: {OUTPUT}")
    types = {}
    for e in final:
        types[e["type"]] = types.get(e["type"], 0) + 1
    print("\nBy type:")
    for t, c in sorted(types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
    segs = {}
    for e in final:
        segs[e["segment"]] = segs.get(e["segment"], 0) + 1
    print("\nBy segment:")
    for s, c in sorted(segs.items()):
        print(f"  Segment {s}: {c}")
    print("\nSample entries:")
    for e in final[:10]:
        print(f"  {e['latin']:25s} -> {e['modern']:20s} Seg {e['segment']:2d} "
              f"{e['row']}{e['col']} [{e['type']}] {e['region']}/{e['country']}")


if __name__ == "__main__":
    main()
