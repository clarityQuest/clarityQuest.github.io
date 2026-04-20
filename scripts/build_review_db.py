#!/usr/bin/env python3
"""Build a review-friendly combined database for OmnesViae + Tabula data.

Rules:
1) Include all OmnesViae Place entries.
2) Include non-city Tabula markings only when a modern place is known.

Outputs:
- public/data/review_places_db.json
- scripts/tabula_places_full.json (cache)
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
OMNESVIAE_PATH = ROOT / "scripts" / "omnesviae_sample.json"
TABULA_CACHE_PATH = ROOT / "scripts" / "tabula_places_full.json"
TABULA_PLACES_PATH = ROOT / "public" / "data" / "places.json"
OUTPUT_PATH = ROOT / "public" / "data" / "review_places_db.json"
TABULA_IMG_W = 46380.0
TABULA_IMG_H = 2953.0
TABULA_SEGMENTS = 11
TABULA_ROWS = ("a", "b", "c")
TABULA_COLS = 5
PLACES_PATH = ROOT / "public" / "data" / "places.json"
SEG4_PATH = ROOT / "public" / "data" / "seg4_places.json"
REFINE_QUEUE_PATH = ROOT / "public" / "data" / "geocode_refine_queue.json"

TABULA_BASE_URL = "https://www.tabula-peutingeriana.de/"
TABULA_PROVINCES_URL = f"{TABULA_BASE_URL}index.html?cont=prov"
TABULA_CIVI_URL = f"{TABULA_BASE_URL}list.html?civi=xxx"
TABULA_LETTER_PAGES = ["!", "a", "b", "d", "i", "n", "s"]
TABULA_TYPE_PAGES = ["aqu", "flu", "lac", "por", "reg", "gen", "ins", "mon"]

NON_CITY_TYPES = {"water", "river", "lake", "island", "mountain", "people", "region", "port", "roman_province", "modern_state"}
MAP_RUNTIME_TYPES = {"major_city", "city", "port", "road_station"}

TYPE_PRIORITY = {
    "road_station": 0,
    "city": 1,
    "major_city": 2,
    "water": 3,
    "lake": 4,
    "river": 5,
    "port": 6,
    "island": 6,
    "mountain": 6,
    "people": 6,
    "region": 6,
    "roman_province": 6,
    "modern_state": 6,
}


def normalize_compare(value: Any) -> str:
    text = normalize_space(value).lower()
    text = re.sub(r"^[~?]+", "", text)
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tabula_location(place: dict[str, Any] | None) -> str:
    if not place:
        return ""
    segment = place.get("segment")
    row = place.get("row")
    col = place.get("col")
    if segment and row and col:
        return f"Seg {segment} {row}{col}"
    return ""


def derive_grid_from_px_py(place: dict[str, Any]) -> dict[str, Any]:
    if place.get("segment") and place.get("row") and place.get("col"):
        return place

    px = place.get("px")
    py = place.get("py")
    try:
        pxf = float(px)
        pyf = float(py)
    except (TypeError, ValueError):
        return place

    seg_w = TABULA_IMG_W / TABULA_SEGMENTS
    row_h = TABULA_IMG_H / len(TABULA_ROWS)
    col_w = seg_w / TABULA_COLS

    seg_idx = max(0, min(TABULA_SEGMENTS - 1, int(pxf // seg_w)))
    col_idx = max(0, min(TABULA_COLS - 1, int((pxf - seg_idx * seg_w) // col_w)))
    row_idx = max(0, min(len(TABULA_ROWS) - 1, int(pyf // row_h)))

    out = dict(place)
    out.setdefault("segment", seg_idx + 2)
    out.setdefault("col", col_idx + 1)
    out.setdefault("row", TABULA_ROWS[row_idx])
    return out


def load_existing_review_fields() -> dict[str, dict[str, Any]]:
    if not OUTPUT_PATH.exists():
        return {}
    try:
        with OUTPUT_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, list):
        return {}

    out: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        record_id = normalize_space(record.get("record_id"))
        if not record_id:
            continue
        out[record_id] = record
    return out


def preserve_review_fields(record: dict[str, Any], existing: dict[str, Any] | None) -> dict[str, Any]:
    if not existing:
        return record

    preserved_prefixes = (
        "geocoding_",
        "review_",
        "manual_",
        "rect_",
    )
    preserved_keys = {
        "notes_review",
        "selected_candidate",
        "selected_modern_name",
    }

    out = dict(record)
    for key, value in existing.items():
        if key in out:
            continue
        if key in preserved_keys or key.startswith(preserved_prefixes):
            out[key] = value

    # If the accepted geocoding result provides lat/lng but the base record has
    # none (tabula-only records have no source lat/lng), promote geocoding_lat/lng.
    if out.get("geocoding_status") == "accepted":
        if out.get("lat") is None and out.get("geocoding_lat") is not None:
            out["lat"] = out["geocoding_lat"]
            out["lng"] = out["geocoding_lng"]

    return out


def load_seg4_runtime_index() -> dict[int, dict[str, Any]]:
    if not SEG4_PATH.exists():
        return {}

    try:
        with SEG4_PATH.open("r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception:
        return {}

    if not isinstance(items, list):
        return {}

    by_data_id: dict[int, dict[str, Any]] = {}
    for row in items:
        if not isinstance(row, dict):
            continue
        did = row.get("data_id")
        if not isinstance(did, int):
            continue
        by_data_id[did] = row
    return by_data_id


def load_seg4_runtime_rows() -> list[dict[str, Any]]:
    if not SEG4_PATH.exists():
        return []
    try:
        with SEG4_PATH.open("r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception:
        return []
    if not isinstance(items, list):
        return []
    return [row for row in items if isinstance(row, dict)]


def append_missing_seg4_runtime_records(
    records: list[dict[str, Any]],
    existing_review_fields: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    seg4_rows = load_seg4_runtime_rows()
    if not seg4_rows:
        return records

    def runtime_data_id_key(type_value: Any, data_id_value: Any) -> int | None:
        if not isinstance(data_id_value, int):
            return None
        type_norm = normalize_space(type_value)
        if type_norm not in MAP_RUNTIME_TYPES:
            return None
        return int(data_id_value)

    existing_counts: Counter[int] = Counter(
        key
        for r in records
        for key in [runtime_data_id_key(r.get("type"), r.get("data_id"))]
        if key is not None
    )

    seg4_groups: dict[int, list[dict[str, Any]]] = {}
    for row in seg4_rows:
        key = runtime_data_id_key(row.get("type"), row.get("data_id"))
        if key is None:
            continue
        seg4_groups.setdefault(key, []).append(row)

    out = list(records)
    for key, rows in seg4_groups.items():
        skip_count = min(existing_counts.get(key, 0), len(rows))
        for row in rows[skip_count:]:
            did = int(row.get("data_id"))
            record_id = f"SEG4:{did}:{row.get('px')}:{row.get('py')}"
            out.append(
                preserve_review_fields({
                    "record_id": record_id,
                    "source": "tabula_runtime",
                    "data_id": did,
                    "id": row.get("id"),
                    "latin": normalize_space(row.get("latin_std")) or normalize_space(row.get("latin")),
                    "latin_std": normalize_space(row.get("latin_std")) or normalize_space(row.get("latin")),
                    "modern_omnesviae": "",
                    "modern_tabula": normalize_space(row.get("modern")),
                    "modern_preferred": normalize_space(row.get("modern")),
                    "type": normalize_space(row.get("type")) or "road_station",
                    "symbol": "",
                    "lat": None,
                    "lng": None,
                    "px": row.get("px"),
                    "py": row.get("py"),
                    "grid_col": row.get("grid_col"),
                    "grid_row": row.get("grid_row"),
                    "tabula_segment": None,
                    "tabula_col": None,
                    "tabula_row": None,
                    "tabula_location": "",
                    "province": normalize_space(row.get("province")),
                    "region": normalize_space(row.get("province")),
                    "country": normalize_space(row.get("country")),
                    "match_status": "seg4_runtime_only",
                }, existing_review_fields.get(record_id))
            )

    return out


def enrich_runtime_fields(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seg4_by_data_id = load_seg4_runtime_index()
    if not seg4_by_data_id:
        return records

    out: list[dict[str, Any]] = []
    for record in records:
        enriched = dict(record)

        # Always expose segment/grid aliases expected by map and calibrator code.
        if enriched.get("grid_col") is None:
            enriched["grid_col"] = enriched.get("tabula_col")
        if enriched.get("grid_row") is None:
            enriched["grid_row"] = enriched.get("tabula_row")
        if not normalize_space(enriched.get("latin_std")):
            enriched["latin_std"] = normalize_space(enriched.get("latin"))

        did = enriched.get("data_id")
        if isinstance(did, int):
            seg4 = seg4_by_data_id.get(did)
            if seg4 and normalize_space(seg4.get("type")) in MAP_RUNTIME_TYPES:
                keep_runtime_coords = (
                    enriched.get("source") == "tabula_runtime"
                    and enriched.get("px") is not None
                    and enriched.get("py") is not None
                )

                if not keep_runtime_coords:
                    try:
                        enriched["px"] = float(seg4.get("px"))
                        enriched["py"] = float(seg4.get("py"))
                    except (TypeError, ValueError):
                        enriched["px"] = None
                        enriched["py"] = None

                    enriched["id"] = seg4.get("id")
                enriched["latin_std"] = normalize_space(seg4.get("latin_std")) or enriched.get("latin_std")
                enriched["province"] = normalize_space(seg4.get("province")) or normalize_space(enriched.get("province"))
                enriched["country"] = normalize_space(seg4.get("country")) or normalize_space(enriched.get("country"))
                enriched["grid_col"] = seg4.get("grid_col") if seg4.get("grid_col") is not None else enriched.get("grid_col")
                enriched["grid_row"] = seg4.get("grid_row") if seg4.get("grid_row") is not None else enriched.get("grid_row")

        out.append(enriched)

    return out


def symbol_to_type(symbol: str) -> str:
    if not symbol:
        return "road_station"
    upper = symbol.upper()
    if upper.startswith("AA") or upper.startswith("F"):
        return "major_city"
    if upper.startswith("AB") or upper.startswith("AC"):
        return "city"
    if upper in ("O", "Q"):
        return "port"
    return "road_station"


def preferred_type(tabula_match: dict[str, Any] | None, symbol: str) -> str:
    if tabula_match:
        tabula_type = normalize_space(tabula_match.get("type"))
        if tabula_type:
            return tabula_type
    return symbol_to_type(symbol)


def match_status(modern_omnesviae: str, modern_tabula: str, has_tabula_match: bool) -> str:
    if not has_tabula_match:
        return "omnesviae_only"
    if modern_omnesviae and modern_tabula:
        if normalize_compare(modern_omnesviae) == normalize_compare(modern_tabula):
            return "modern_match"
        return "modern_differs"
    return "linked_by_id"


def should_replace_type(current_type: str, new_type: str) -> bool:
    return TYPE_PRIORITY.get(new_type or "", 0) > TYPE_PRIORITY.get(current_type or "", 0)


def find_tabula_match(
    data_id: int | None,
    latin: str,
    modern_omnesviae: str,
    symbol: str,
    tabula_by_id: dict[int, dict[str, Any]],
    tabula_by_latin: dict[str, list[dict[str, Any]]],
    tabula_by_modern: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    latin_key = normalize_compare(latin)
    modern_key = normalize_compare(modern_omnesviae)

    if data_id is not None:
        direct = tabula_by_id.get(data_id)
        if direct:
            direct_latin = normalize_compare(direct.get("latin"))
            direct_modern = normalize_compare(direct.get("modern"))
            if (
                (latin_key and direct_latin and latin_key == direct_latin)
                or (modern_key and direct_modern and modern_key == direct_modern)
            ):
                return direct

            # Some OmnesViae TPPlace ids collide numerically with unrelated Tabula ids.
            # In that case, ignore the direct id and continue with name-based matching.
            direct = None

    preferred_type_name = symbol_to_type(symbol)

    def _score(candidate: dict[str, Any]) -> tuple[int, int, int]:
        cand_type = normalize_space(candidate.get("type"))
        type_score = 1 if cand_type == preferred_type_name else 0
        has_location = 1 if tabula_location(candidate) else 0
        has_modern = 1 if normalize_space(candidate.get("modern")) else 0
        return (type_score, has_location, has_modern)

    def _pick(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        ranked = sorted(candidates, key=_score, reverse=True)
        if len(ranked) >= 2 and _score(ranked[0]) == _score(ranked[1]):
            return None
        return ranked[0]

    if latin_key:
        match = _pick(tabula_by_latin.get(latin_key, []))
        if match:
            return match

    if modern_key:
        match = _pick(tabula_by_modern.get(modern_key, []))
        if match:
            return match

    return None


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def parse_data_id(iri: str) -> int | None:
    if "TPPlace" not in iri:
        return None
    try:
        return int(iri.rsplit("TPPlace", 1)[1])
    except (TypeError, ValueError):
        return None


def fallback_latin_label(iri: str) -> str:
    if not iri:
        return ""
    tail = iri.rsplit("#", 1)[-1]
    return tail or iri


def fetch_soup(url: str, session: requests.Session):
    from bs4 import BeautifulSoup

    try:
        response = session.get(url, timeout=30)
        response.encoding = "utf-8"
        return BeautifulSoup(response.text, "html.parser")
    except Exception:
        return None


def scrape_modern_states(session: requests.Session) -> list[dict[str, Any]]:
    try:
        response = session.get(TABULA_CIVI_URL, timeout=30)
        response.encoding = "utf-8"
        html = response.text
    except Exception:
        return []

    states: list[dict[str, Any]] = []
    pattern = re.compile(
        r'<a[^>]+href="list\.html\?civi=([A-Za-z0-9]+)"[^>]*>.*?<b[^>]*class="lkz"[^>]*>([^<]+)</b>\s*</a>\s*-\s*([^<(<br>]+)',
        re.I | re.S,
    )
    seq = 0

    for match in pattern.finditer(html):
        code_href = normalize_space(match.group(1))
        code_lkz = normalize_space(match.group(2))
        code = code_lkz or code_href
        modern_name = normalize_space(match.group(3))
        modern_name = modern_name.strip(" -")
        modern_name = modern_name or code

        seq += 1
        states.append(
            {
                "id": 950000 + seq,
                "latin": code,
                "modern": modern_name,
                "type": "modern_state",
                "country": code,
                "region": "",
                "segment": None,
                "col": None,
                "row": None,
                "notes": "",
            }
        )

    return states


def scrape_roman_provinces(session: requests.Session) -> list[dict[str, Any]]:
    soup = fetch_soup(TABULA_PROVINCES_URL, session)
    if soup is None:
        return []

    provinces: list[dict[str, Any]] = []
    rows = soup.select("div.row.locus")
    seq = 0

    for row in rows:
        prov_anchor = row.select_one('a[href*="list.html?prov="]')
        if not prov_anchor:
            continue

        code_el = prov_anchor.select_one("strong")
        prov_code = normalize_space(code_el.get_text(" ", strip=True) if code_el else "")

        cols = row.select("div[class*='col-md-']")
        province_name = ""
        modern_codes = []
        if len(cols) >= 2:
            province_name = normalize_space(cols[1].select_one("strong").get_text(" ", strip=True) if cols[1].select_one("strong") else cols[1].get_text(" ", strip=True))
        if len(cols) >= 4:
            modern_codes = [normalize_space(a.get_text(" ", strip=True)) for a in cols[3].select("a.lkz") if normalize_space(a.get_text(" ", strip=True))]

        if not prov_code and not province_name:
            continue

        seq += 1
        provinces.append(
            {
                "id": 960000 + seq,
                "latin": province_name or prov_code,
                "modern": province_name or prov_code,
                "type": "roman_province",
                "country": "|".join(modern_codes),
                "region": prov_code,
                "segment": None,
                "col": None,
                "row": None,
                "notes": "",
            }
        )

    return provinces


def scrape_tabula_places() -> list[dict[str, Any]]:
    # Import lazily so this script only depends on bs4/requests when scraping.
    from scrape_places import fetch_page, parse_page

    session = requests.Session()
    session.headers.update({
        "User-Agent": "TabulaPeutingeriana-ResearchBot/1.0 (educational)",
    })

    all_entries: list[dict[str, Any]] = []

    for letter in TABULA_LETTER_PAGES:
        url = f"{TABULA_BASE_URL}list.html?alfa={letter}"
        soup = fetch_page(url, session)
        if soup:
            all_entries.extend(parse_page(soup))

    for typ in TABULA_TYPE_PAGES:
        url = f"{TABULA_BASE_URL}list.html?typ={typ}"
        soup = fetch_page(url, session)
        if soup:
            entries = parse_page(soup)
            type_map = {
                "aqu": "water",
                "flu": "river",
                "lac": "lake",
                "por": "port",
                "reg": "region",
                "gen": "people",
                "ins": "island",
                "mon": "mountain",
            }
            for entry in entries:
                if entry.get("type") == "road_station":
                    entry["type"] = type_map.get(typ, entry.get("type"))
            all_entries.extend(entries)

    all_entries.extend(scrape_roman_provinces(session))
    all_entries.extend(scrape_modern_states(session))

    by_id: dict[int, dict[str, Any]] = {}
    synthetic_id_seed = 50000

    for entry in all_entries:
        pid = entry.get("id") or 0
        if isinstance(pid, int) and pid > 0:
            current = by_id.get(pid)
            if not current:
                by_id[pid] = entry
                continue
            if not current.get("modern") and entry.get("modern"):
                current["modern"] = entry["modern"]
            if not current.get("region") and entry.get("region"):
                current["region"] = entry["region"]
            if not current.get("country") and entry.get("country"):
                current["country"] = entry["country"]
            if should_replace_type(current.get("type", ""), entry.get("type", "")):
                current["type"] = entry.get("type")
            continue

        synthetic_id_seed += 1
        entry["id"] = synthetic_id_seed
        by_id[synthetic_id_seed] = entry

    return sorted(
        by_id.values(),
        key=lambda x: (
            x.get("segment") if isinstance(x.get("segment"), int) else 99,
            x.get("col") if isinstance(x.get("col"), int) else 99,
            x.get("row") if isinstance(x.get("row"), str) and x.get("row") else "z",
            x.get("id", 0),
        ),
    )


def load_tabula_places(refresh: bool) -> list[dict[str, Any]]:
    scraped_places: list[dict[str, Any]]
    if not refresh and TABULA_CACHE_PATH.exists():
        with TABULA_CACHE_PATH.open("r", encoding="utf-8") as f:
            scraped_places = json.load(f)
    else:
        scraped_places = scrape_tabula_places()
        TABULA_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with TABULA_CACHE_PATH.open("w", encoding="utf-8") as f:
            json.dump(scraped_places, f, ensure_ascii=False, indent=2)

    # `public/data/places.json` is the curated Tabula import used elsewhere in the repo
    # and contains corrected core place records (for example Vindobona/Wien for id 385).
    # Prefer it for normal TP place ids, but keep synthetic province/state entries from the
    # richer scrape cache.
    if not TABULA_PLACES_PATH.exists():
        return scraped_places

    with TABULA_PLACES_PATH.open("r", encoding="utf-8") as f:
        authoritative_places = [derive_grid_from_px_py(p) for p in json.load(f)]

    scraped_name_keys: set[str] = set()
    for entry in scraped_places:
        latin_key = normalize_compare(entry.get("latin"))
        modern_key = normalize_compare(entry.get("modern"))
        if latin_key:
            scraped_name_keys.add(f"latin:{latin_key}")
        if modern_key:
            scraped_name_keys.add(f"modern:{modern_key}")

    supplemental_places = []
    supplemental_seed = 2_000_000
    for entry in authoritative_places:
        latin_key = normalize_compare(entry.get("latin"))
        modern_key = normalize_compare(entry.get("modern"))
        has_latin = bool(latin_key and f"latin:{latin_key}" in scraped_name_keys)
        has_modern = bool(modern_key and f"modern:{modern_key}" in scraped_name_keys)
        if has_latin or has_modern:
            continue
        supplemental_seed += 1
        extra = dict(entry)
        extra["id"] = supplemental_seed
        extra["_authority_source"] = "places_json"
        supplemental_places.append(extra)

    merged_places = scraped_places + supplemental_places

    return sorted(
        merged_places,
        key=lambda x: (
            x.get("segment") if isinstance(x.get("segment"), int) else 99,
            x.get("col") if isinstance(x.get("col"), int) else 99,
            x.get("row") if isinstance(x.get("row"), str) and x.get("row") else "z",
            x.get("id", 0),
        ),
    )


def build_review_db(omnesviae_data: dict[str, Any], tabula_places: list[dict[str, Any]]) -> dict[str, Any]:
    graph = omnesviae_data.get("@graph", [])
    ov_places = [n for n in graph if n.get("@type") == "Place"]
    existing_review_fields = load_existing_review_fields()

    tabula_by_id = {
        int(p["id"]): p
        for p in tabula_places
        if isinstance(p.get("id"), int)
        and p.get("id", 0) > 0
        and not p.get("_authority_source")
    }
    tabula_by_latin: dict[str, list[dict[str, Any]]] = {}
    tabula_by_modern: dict[str, list[dict[str, Any]]] = {}

    for place in tabula_places:
        latin_key = normalize_compare(place.get("latin"))
        if latin_key:
            tabula_by_latin.setdefault(latin_key, []).append(place)
        modern_key = normalize_compare(place.get("modern"))
        if modern_key:
            tabula_by_modern.setdefault(modern_key, []).append(place)

    records: list[dict[str, Any]] = []
    ov_data_ids: set[int] = set()

    for p in ov_places:
        pid = str(p.get("@id", ""))
        data_id = parse_data_id(pid)
        if data_id is not None:
            ov_data_ids.add(data_id)

        modern_omnesviae = normalize_space(p.get("modern"))
        symbol = normalize_space(p.get("symbol"))
        latin = normalize_space(p.get("label")) or fallback_latin_label(pid)
        tabula_match = find_tabula_match(
            data_id,
            latin,
            modern_omnesviae,
            symbol,
            tabula_by_id,
            tabula_by_latin,
            tabula_by_modern,
        )
        modern_tabula = normalize_space(tabula_match.get("modern")) if tabula_match else ""
        resolved_type = preferred_type(tabula_match, symbol)
        resolved_country = normalize_space((tabula_match or {}).get("country"))
        resolved_region = normalize_space((tabula_match or {}).get("region"))

        records.append(
            preserve_review_fields({
                "record_id": f"OV:{pid}",
                "source": "omnesviae",
                "data_id": data_id,
                "latin": latin,
                "latin_std": latin,
                "modern_omnesviae": modern_omnesviae,
                "modern_tabula": modern_tabula,
                "modern_preferred": modern_tabula or modern_omnesviae,
                "type": resolved_type,
                "symbol": symbol,
                "lat": p.get("lat"),
                "lng": p.get("lng"),
                "px": None,
                "py": None,
                "province": resolved_region,
                "country": resolved_country,
                "region": resolved_region,
                "tabula_segment": (tabula_match or {}).get("segment"),
                "tabula_col": (tabula_match or {}).get("col"),
                "tabula_row": (tabula_match or {}).get("row"),
                "grid_col": (tabula_match or {}).get("col"),
                "grid_row": (tabula_match or {}).get("row"),
                "tabula_location": tabula_location(tabula_match),
                "match_status": match_status(modern_omnesviae, modern_tabula, bool(tabula_match)),
            }, existing_review_fields.get(f"OV:{pid}"))
        )

    for t in tabula_places:
        tab_type = normalize_space(t.get("type"))
        if tab_type not in NON_CITY_TYPES:
            continue

        modern = normalize_space(t.get("modern"))
        if not modern and tab_type not in {"region", "roman_province", "modern_state"}:
            continue

        data_id = t.get("id") if isinstance(t.get("id"), int) else None
        if data_id is not None and data_id in ov_data_ids:
            continue

        record_id = f"TP:{t.get('id')}"
        records.append(
            preserve_review_fields({
                "record_id": record_id,
                "source": "tabula",
                "data_id": data_id,
                "latin": normalize_space(t.get("latin")),
                "latin_std": normalize_space(t.get("latin")),
                "modern_omnesviae": "",
                "modern_tabula": modern,
                "modern_preferred": modern,
                "type": tab_type,
                "symbol": "",
                "lat": None,
                "lng": None,
                "px": None,
                "py": None,
                "tabula_segment": t.get("segment"),
                "tabula_col": t.get("col"),
                "tabula_row": t.get("row"),
                "grid_col": t.get("col"),
                "grid_row": t.get("row"),
                "tabula_location": tabula_location(t),
                "province": normalize_space(t.get("region")),
                "region": normalize_space(t.get("region")),
                "country": normalize_space(t.get("country")),
                "match_status": "tabula_only",
            }, existing_review_fields.get(record_id))
        )

    records = append_missing_seg4_runtime_records(records, existing_review_fields)
    records = enrich_runtime_fields(records)

    records.sort(key=lambda r: (str(r.get("source", "")), str(r.get("latin", "")).lower(), int(r.get("data_id") or 0)))

    overview = {
        "omnesviae_place_count": len(ov_places),
        "tabula_place_count": len(tabula_places),
        "records_total": len(records),
        "records_omnesviae": sum(1 for r in records if r["source"] == "omnesviae"),
        "records_tabula_markings": sum(1 for r in records if r["source"] == "tabula"),
        "records_with_tabula_modern": sum(1 for r in records if r.get("modern_tabula")),
        "records_modern_match": sum(1 for r in records if r.get("match_status") == "modern_match"),
        "records_modern_differs": sum(1 for r in records if r.get("match_status") == "modern_differs"),
    }

    return {
        "meta": {
            "name": "OmnesViae + Tabula Review Database",
            "description": "All OmnesViae places + non-city Tabula markings with known modern names.",
            "version": 1,
            "overview": overview,
        },
        "records": records,
    }


def is_missing_coord(value: Any) -> bool:
    return value is None or value == ""


def core_match_key(value: Any) -> str:
    return normalize_compare(value)


def build_unique_lookup(entries: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        key = core_match_key(entry.get(field, ""))
        if not key:
            continue
        grouped.setdefault(key, []).append(entry)
    return {k: v[0] for k, v in grouped.items() if len(v) == 1}


def build_geocoded_updates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    updates = []
    for r in records:
        status = str(r.get("geocoding_status", ""))
        if status != "accepted":
            continue

        lat = r.get("lat")
        lng = r.get("lng")
        if is_missing_coord(lat) or is_missing_coord(lng):
            lat = r.get("geocoding_lat")
            lng = r.get("geocoding_lng")
        if is_missing_coord(lat) or is_missing_coord(lng):
            continue

        updates.append(
            {
                "data_id": r.get("data_id"),
                "latin": r.get("latin", ""),
                "modern": r.get("modern_preferred", ""),
                "lat": lat,
                "lng": lng,
                "geocoding_confidence": r.get("geocoding_confidence"),
                "geocoding_source": r.get("geocoding_source") or r.get("geocoding_provider") or "nominatim",
                "geocoding_timestamp": r.get("geocoding_timestamp"),
            }
        )
    return updates


def update_core_file(file_path: Path, updates: list[dict[str, Any]], label: str) -> tuple[int, int]:
    if not file_path.exists():
        return 0, 0

    with file_path.open("r", encoding="utf-8") as f:
        items = json.load(f)

    if not isinstance(items, list):
        return 0, 0

    by_data_id = {
        int(u["data_id"]): u
        for u in updates
        if isinstance(u.get("data_id"), int)
    }
    by_modern = build_unique_lookup(updates, "modern")
    by_latin = build_unique_lookup(updates, "latin")

    touched = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        if not is_missing_coord(item.get("lat")) and not is_missing_coord(item.get("lng")):
            continue

        selected = None
        did = item.get("data_id")
        if isinstance(did, int) and did in by_data_id:
            selected = by_data_id[did]
        if not selected:
            selected = by_modern.get(core_match_key(item.get("modern", "")))
        if not selected:
            selected = by_latin.get(core_match_key(item.get("latin", "")))
        if not selected:
            selected = by_latin.get(core_match_key(item.get("latin_std", "")))
        if not selected:
            continue

        item["lat"] = selected["lat"]
        item["lng"] = selected["lng"]
        item["geocoding_source"] = selected.get("geocoding_source", "nominatim")
        item["geocoding_confidence"] = selected.get("geocoding_confidence")
        item["geocoding_timestamp"] = selected.get("geocoding_timestamp")
        touched += 1

    if touched > 0:
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    return touched, len(items)


def write_core_datasets(records: list[dict[str, Any]]) -> dict[str, Any]:
    updates = build_geocoded_updates(records)
    places_updated, places_total = update_core_file(PLACES_PATH, updates, "places")
    seg4_updated, seg4_total = update_core_file(SEG4_PATH, updates, "seg4")
    return {
        "updates_available": len(updates),
        "places_updated": places_updated,
        "places_total": places_total,
        "seg4_updated": seg4_updated,
        "seg4_total": seg4_total,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build combined review database JSON")
    parser.add_argument(
        "--refresh-tabula",
        action="store_true",
        help="Force a fresh scrape from tabula-peutingeriana.de and update local cache.",
    )
    parser.add_argument(
        "--geocode",
        action="store_true",
        help="Fill missing lat/lng from modern place names via internet geocoding.",
    )
    parser.add_argument(
        "--geocode-dry-run",
        action="store_true",
        help="Run geocoding matching without writing new coordinates.",
    )
    parser.add_argument(
        "--geocode-max",
        type=int,
        default=0,
        help="Limit number of missing-coordinate records to geocode (0 = all).",
    )
    parser.add_argument(
        "--geocode-refresh-cache",
        action="store_true",
        help="Ignore local geocoding cache for this run.",
    )
    parser.add_argument(
        "--geocode-min-confidence",
        type=float,
        default=0.55,
        help="Minimum confidence for automatic coordinate acceptance.",
    )
    parser.add_argument(
        "--geocode-min-confidence-wikipedia",
        type=float,
        default=0.62,
        help="Minimum confidence for Wikipedia acceptance.",
    )
    parser.add_argument(
        "--geocode-min-confidence-nominatim",
        type=float,
        default=0.55,
        help="Minimum confidence for Nominatim acceptance.",
    )
    parser.add_argument(
        "--geocode-strategy",
        type=str,
        default="wikipedia,nominatim",
        help="Provider order as CSV. Allowed: wikipedia,google,nominatim",
    )
    parser.add_argument(
        "--geocode-google-api-key",
        type=str,
        default="",
        help="Optional Google API key for CSE fallback (or use GOOGLE_API_KEY env).",
    )
    parser.add_argument(
        "--geocode-google-cse-id",
        type=str,
        default="",
        help="Optional Google Custom Search Engine ID (or use GOOGLE_CSE_ID env).",
    )
    parser.add_argument(
        "--geocode-include-empty-modern",
        action="store_true",
        help="Also attempt geocoding rows without a modern_preferred name.",
    )
    parser.add_argument(
        "--geocode-delay",
        type=float,
        default=1.0,
        help="Delay in seconds between network geocoding requests.",
    )
    parser.add_argument(
        "--write-core-datasets",
        action="store_true",
        help="Write accepted geocoded coordinates to places.json and seg4_places.json.",
    )
    args = parser.parse_args()

    with OMNESVIAE_PATH.open("r", encoding="utf-8") as f:
        omnesviae_data = json.load(f)

    tabula_places = load_tabula_places(refresh=args.refresh_tabula)
    out = build_review_db(omnesviae_data, tabula_places)

    geocode_report: dict[str, Any] | None = None
    if args.geocode:
        from geocode_missing import enrich_records

        geocode_report = enrich_records(
            out["records"],
            dry_run=args.geocode_dry_run,
            max_records=max(0, args.geocode_max),
            refresh_cache=args.geocode_refresh_cache,
            min_confidence=max(0.0, min(1.0, args.geocode_min_confidence)),
            min_confidence_wikipedia=max(0.0, min(1.0, args.geocode_min_confidence_wikipedia)),
            min_confidence_nominatim=max(0.0, min(1.0, args.geocode_min_confidence_nominatim)),
            strategy=args.geocode_strategy,
            google_api_key=args.geocode_google_api_key,
            google_cse_id=args.geocode_google_cse_id,
            require_modern_name=not args.geocode_include_empty_modern,
            delay_seconds=max(0.0, args.geocode_delay),
            timeout_sec=30,
        )

        out["meta"]["geocoding"] = {
            "enabled": True,
            "dry_run": args.geocode_dry_run,
            "min_confidence": args.geocode_min_confidence,
            "min_confidence_wikipedia": args.geocode_min_confidence_wikipedia,
            "min_confidence_nominatim": args.geocode_min_confidence_nominatim,
            "strategy": args.geocode_strategy,
            "summary": geocode_report["summary"],
        }

        REFINE_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with REFINE_QUEUE_PATH.open("w", encoding="utf-8") as f:
            json.dump(geocode_report["refinement_queue"], f, ensure_ascii=False, indent=2)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    core_report: dict[str, Any] | None = None
    if args.write_core_datasets and not args.geocode_dry_run:
        core_report = write_core_datasets(out["records"])

    o = out["meta"]["overview"]
    print("Built review database")
    print(f"  OmnesViae places: {o['omnesviae_place_count']}")
    print(f"  Tabula places loaded: {o['tabula_place_count']}")
    print(f"  Output records: {o['records_total']}")
    print(f"  OmnesViae records: {o['records_omnesviae']}")
    print(f"  Tabula markings: {o['records_tabula_markings']}")
    print(f"  With modern from Tabula: {o['records_with_tabula_modern']}")
    if geocode_report:
        g = geocode_report["summary"]
        print("Geocoding summary")
        print(f"  Strategy: {','.join(g.get('strategy', []))}")
        print(f"  Processed: {g['processed']}")
        print(f"  Accepted: {g['accepted']}")
        accepted_by_source = g.get("accepted_by_source", {})
        print(f"    Wikipedia: {accepted_by_source.get('wikipedia', 0)}")
        print(f"    Google->Wikipedia: {accepted_by_source.get('google_wikipedia', 0)}")
        print(f"    Nominatim: {accepted_by_source.get('nominatim', 0)}")
        print(f"  Needs refinement: {g['needs_refinement']}")
        print(f"  No candidate: {g['no_candidate']}")
        print(f"  Cache hits: {g['cached']}")
        print(f"  Refinement queue: {REFINE_QUEUE_PATH}")
    if core_report:
        print("Core dataset write-back")
        print(f"  places.json updated rows: {core_report['places_updated']} / {core_report['places_total']}")
        print(f"  seg4_places.json updated rows: {core_report['seg4_updated']} / {core_report['seg4_total']}")
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
