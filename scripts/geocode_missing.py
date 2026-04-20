#!/usr/bin/env python3
"""Geocode missing coordinates for Tabula review records.

Provider chain defaults to: wikipedia -> nominatim.
Optional Google CSE fallback can be inserted as: wikipedia -> google -> nominatim,
where Google is only used to discover likely Wikipedia pages.
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "scripts" / "geocoding_cache.json"
CACHE_QUERY_VERSION = "v4_types"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"

COUNTRY_HINTS = {
    "D": "de",
    "I": "it",
    "F": "fr",
    "E": "es",
    "P": "pt",
    "H": "hr",
    "A": "at",
    "G": "gr",
    "R": "ro",
    "B": "be",
    "N": "nl",
    "S": "ch",
    "T": "tr",
}

WATER_HINT_TYPES = {"river", "lake", "water", "port", "island"}
CITY_TYPES = {"city", "major_city", "road_station"}

COUNTRY_NAMES = {
    "it": "italy",
    "de": "germany",
    "fr": "france",
    "es": "spain",
    "pt": "portugal",
    "gr": "greece",
    "tr": "turkey",
    "hr": "croatia",
    "ro": "romania",
    "be": "belgium",
    "nl": "netherlands",
    "ch": "switzerland",
    "at": "austria",
    "bg": "bulgaria",
    "tn": "tunisia",
    "dz": "algeria",
    "ma": "morocco",
    "ly": "libya",
    "eg": "egypt",
    "et": "ethiopia",
    "sy": "syria",
    "iq": "iraq",
    "il": "israel",
    "lb": "lebanon",
    "jo": "jordan",
    "rs": "serbia",
    "yu": "yugoslavia",
}

TYPE_QUERY_TERMS = {
    "river": "river",
    "lake": "lake",
    "water": "water",
    "port": "port",
    "island": "island",
    "mountain": "mountain",
    "region": "region",
    "roman_province": "province",
    "modern_state": "state",
    "city": "city",
    "major_city": "city",
    "road_station": "settlement",
    "people": "people",
}

SEARCH_NAME_OVERRIDES = {
    # rivers
    ("river", "iskar"): "Iskar (river)",
    ("river", "don"): "Don (river)",
    ("river", "mella"): "Mella (river)",
    ("river", "donau"): "Danube",
    ("river", "duna"): "Danube",
    ("river", "dunav"): "Danube",
    ("river", "nil"): "Nile",
    ("river", "vesubia"): "Vésubie",
    ("river", "vippaco"): "Vipava",
    ("river", "imper"): "Impero (river)",
    ("river", "marica"): "Maritsa",
    ("river", "garigliano"): "Garigliano",
    ("river", "ebrosu"): "Maritsa",
    ("river", "ebros"): "Maritsa",
    ("river", "pineios"): "Pineios (Thessaly)",
    ("river", "arzilla"): "Torrente Arzilla",
    ("river", "arestra"): "Arrestra",
    ("river", "staffera"): "Staffora",
    ("river", "giarretta"): "Simeto (river)",
    ("river", "bessagno"): "Bisagno",
    ("river", "varsita"): "Varaita",
    ("river", "araxes"): "Aras (river)",
    # islands
    ("island", "rhodos"): "Rhodes (island)",
    ("island", "giglio"): "Isola del Giglio",
    ("island", "otok mljet"): "Mljet",
    ("island", "otok pag"): "Pag",
    ("island", "otok korcula"): "Korčula",
    ("island", "otok hvar"): "Hvar",
    ("island", "otok vis"): "Vis (island)",
    ("island", "otok lastovo"): "Lastovo (island)",
    ("island", "otok brac"): "Brač",
    ("island", "otok ciovo"): "Čiovo (island)",
    ("island", "gialesine"): "Aeolian Islands",
    ("island", "gialesine korabalo and marmoras"): "Aeolian Islands",
    ("island", "otok brijuni"): "Brijuni",
    ("island", "otok uglian"): "Ugljan",
    ("island", "otok scedro"): "Šćedro",
    ("island", "otok sv ivan"): "Sveti Ivan na pučini",
    ("island", "djazira djalita"): "Galite Islands",
    ("island", "isola basiluzza"): "Basiluzzo",
    ("island", "koufonissi"): "Koufonisia",
    ("island", "delos"): "Delos",
    ("island", "paxos"): "Paxos",
    ("island", "kasos"): "Kasos",
    ("island", "piperi"): "Piperi island",
    # lakes
    ("lake", "bahr lut"): "Dead Sea",
    ("lake", "azovskoe more"): "Sea of Azov",
    ("lake", "liqeni i ohrit"): "Lake Ohrid",
}

SEARCH_LANGUAGE_OVERRIDES: dict[tuple[str, str], list[str]] = {
    ("river", "torrente arzilla"): ["ceb"],
    ("river", "arzilla"): ["ceb"],
}

# Words in various languages that prefix a geographic type name and can be stripped to
# reach the base toponym (e.g. "Fiume Magra" → strip "Fiume" → try "Magra (river)").
# Keys are normalised type_hint values; values are prefix words (case-insensitive match).
TYPE_PREFIX_WORDS: dict[str, list[str]] = {
    "river": [
        "Fiume", "Fiumara", "Torrente",       # Italian
        "Río", "Rio",                          # Spanish / Portuguese
        "Fleuve", "Rivière", "Ruisseau",       # French
        "Fluss", "Bach", "Strom",              # German
        "Rivier",                              # Dutch
        "Nehir", "Irmak",                      # Turkish
        "Râul", "Pârâul",                      # Romanian
        "Reka",                                # South Slavic
    ],
    "lake": ["Lago", "Laguna", "Lac", "See", "Meer", "Göl", "Lacul"],
    "mountain": ["Monte", "Mont", "Berg", "Cerro", "Sierra", "Pico", "Pic", "Mount"],
    "island": ["Île", "Isla", "Isola", "Insel", "Otok"],
}

# Maps a normalised type_hint to the Wikipedia disambiguation parenthetical used in article
# titles (e.g. "Paglia" → "Paglia (river)", "Biel" → "Biel (lake)").
TYPE_DISAMBIGUATION_WORDS: dict[str, str] = {
    "river": "river",
    "lake": "lake",
    "mountain": "mountain",
    "island": "island",
    "region": "region",
    "roman_province": "province",
    "sea": "sea",
    "gulf": "gulf",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ascii_fold(value: Any) -> str:
    text = "" if value is None else str(value)
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_text(value: Any) -> str:
    text = ascii_fold(value)
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def cleaned_modern_name(value: str) -> str:
    text = value or ""
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"^[~?]+", "", text)
    text = text.replace("?", " ")
    text = text.replace("|", " ")
    text = text.replace("/", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,;:-")


def extract_name_alternatives(value: str) -> list[str]:
    """Return all cleaned alternative names from a '|' or ',' separated value.

    Used to populate extra title candidates when modern_preferred lists several
    alternative names (e.g. "Tavo | Vomano", "Vippaco, Vipava").
    """
    raw = value or ""
    parts: list[str] = []
    for pipe_part in raw.split("|"):
        for comma_part in pipe_part.split(","):
            cleaned = cleaned_modern_name(comma_part.strip())
            cleaned = re.sub(r"^[~?\s]+", "", cleaned).strip()
            if cleaned:
                parts.append(cleaned)
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        key = normalize_text(p)
        if key and key not in seen:
            out.append(p)
            seen.add(key)
    return out


def primary_search_name(value: str, type_hint: str) -> str:
    # Take the first alternative when multiple names are pipe-separated (e.g. "Tavo | Vomano")
    raw = value or ""
    if "|" in raw:
        raw = raw.split("|", 1)[0]
    text = cleaned_modern_name(raw)
    if not text:
        return ""

    # Many rows contain alias lists like "Donau, Duna, Dunărea...".
    # Querying the first clean alias is substantially more precise.
    if "," in text:
        first = text.split(",", 1)[0].strip(" ,;:-")
        if first:
            text = first

    if type_hint in WATER_HINT_TYPES and " ~ " in text:
        first = text.split(" ~ ", 1)[0].strip(" ,;:-")
        if first:
            text = first

    override = SEARCH_NAME_OVERRIDES.get((normalize_text(type_hint), normalize_text(text)))
    if override:
        return override

    return text


def latin_fallback_search_name(value: str, type_hint: str) -> str:
    """Extract a usable toponym from latin_std when modern_preferred is missing."""
    text = cleaned_modern_name(value or "")
    if not text:
        return ""

    # Normalize compact type markers that often prefix Tabula hydronyms.
    text = re.sub(r"^\s*(fl|flu|flum|flumen|fluvius|lac|lacus|lacum)\b\.?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*(fl\{|fl\()", "", text, flags=re.IGNORECASE)
    text = text.strip(" ,;:-")
    if not text:
        return ""

    override = SEARCH_NAME_OVERRIDES.get((normalize_text(type_hint), normalize_text(text)))
    if override:
        return override
    return text


def country_code_hint(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        return ""
    if len(text) == 2 and text.isalpha():
        return text.lower()
    if len(text) == 1 and text.isalpha():
        return COUNTRY_HINTS.get(text.upper(), "")
    return ""


def overlap_ratio(query: str, text: str) -> float:
    query_tokens = {t for t in normalize_text(query).split(" ") if t}
    text_tokens = {t for t in normalize_text(text).split(" ") if t}
    if not query_tokens:
        return 0.0
    common = len(query_tokens.intersection(text_tokens))
    return common / max(len(query_tokens), 1)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def has_valid_coords(lat: Any, lng: Any) -> bool:
    try:
        latf = float(lat)
        lngf = float(lng)
    except (TypeError, ValueError):
        return False
    return -90.0 <= latf <= 90.0 and -180.0 <= lngf <= 180.0


def parse_geohack_params(params: str) -> tuple[float, float] | None:
    raw = unquote(params or "")
    raw = raw.split("_type:", 1)[0]
    raw = raw.split("_region:", 1)[0]
    tokens = [tok for tok in raw.split("_") if tok]
    if not tokens:
        return None

    def _find_hemisphere(items: list[str], hemispheres: set[str], start: int = 0) -> int:
        for idx in range(start, len(items)):
            if items[idx].upper() in hemispheres:
                return idx
        return -1

    lat_hemi_idx = _find_hemisphere(tokens, {"N", "S"})
    if lat_hemi_idx <= 0:
        return None
    lon_hemi_idx = _find_hemisphere(tokens, {"E", "W"}, lat_hemi_idx + 1)
    if lon_hemi_idx <= lat_hemi_idx + 1:
        return None

    def _to_decimal(parts: list[str], hemi: str) -> float | None:
        if not parts:
            return None
        try:
            deg = float(parts[0])
            minutes = float(parts[1]) if len(parts) > 1 else 0.0
            seconds = float(parts[2]) if len(parts) > 2 else 0.0
        except ValueError:
            return None
        value = abs(deg) + (minutes / 60.0) + (seconds / 3600.0)
        if hemi.upper() in {"S", "W"}:
            value *= -1.0
        return value

    lat = _to_decimal(tokens[:lat_hemi_idx], tokens[lat_hemi_idx])
    lng = _to_decimal(tokens[lat_hemi_idx + 1:lon_hemi_idx], tokens[lon_hemi_idx])
    if not has_valid_coords(lat, lng):
        return None
    return lat, lng


def cache_key(name: str, country: str, type_hint: str, strategy: str) -> str:
    return "|".join(
        [
            CACHE_QUERY_VERSION,
            normalize_text(name),
            country_code_hint(country),
            normalize_text(type_hint),
            normalize_text(strategy),
        ]
    )


def country_name_hint(country_raw: Any) -> str:
    text = "" if country_raw is None else str(country_raw).strip()
    if not text:
        return ""
    first = text.split("|", 1)[0].strip()
    if len(first) == 2 and first.isalpha():
        return COUNTRY_NAMES.get(first.lower(), "")
    if len(first) == 1 and first.isalpha():
        code = COUNTRY_HINTS.get(first.upper(), "")
        return COUNTRY_NAMES.get(code, "")
    return ""


def type_query_hint(type_hint: str) -> str:
    return TYPE_QUERY_TERMS.get(normalize_text(type_hint), "")


def build_query_variants(modern_name: str, country_raw: Any, type_hint: str, cc_hint: str) -> list[str]:
    country_term = country_name_hint(country_raw) or cc_hint
    category_term = type_query_hint(type_hint)

    candidates = [
        " ".join(v for v in [modern_name, country_term, category_term] if v),
        " ".join(v for v in [modern_name, country_term] if v),
        " ".join(v for v in [modern_name, category_term] if v),
        modern_name,
    ]

    out: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        query = " ".join(c.split()).strip()
        key = normalize_text(query)
        if not key or key in seen:
            continue
        out.append(query)
        seen.add(key)
    return out


def load_cache(refresh: bool) -> dict[str, Any]:
    if refresh or not CACHE_PATH.exists():
        return {}
    with CACHE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(cache: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_PATH.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def type_fit_score(type_hint: str, klass: str, typ: str) -> float:
    klass = klass.lower()
    typ = typ.lower()

    if type_hint in WATER_HINT_TYPES:
        if klass in {"waterway", "natural"}:
            return 0.25
        if typ in {"river", "stream", "canal", "lake", "reservoir", "bay", "strait"}:
            return 0.25
        if type_hint == "port" and typ in {"harbour", "port", "dock"}:
            return 0.25
        return -0.1

    if type_hint in CITY_TYPES:
        if klass in {"place", "boundary"}:
            return 0.15
        if typ in {"city", "town", "village", "municipality", "hamlet"}:
            return 0.15
        return -0.05

    if type_hint == "mountain":
        if typ in {"peak", "mountain", "volcano", "ridge"}:
            return 0.2
        return -0.05

    if type_hint in {"region", "roman_province", "modern_state"}:
        if klass in {"boundary", "place"}:
            return 0.12
        return 0.0

    return 0.0


def wiki_country_boost(text_blob: str, cc_hint: str) -> float:
    if not cc_hint:
        return 0.0
    t = normalize_text(text_blob)
    country_aliases = {
        "it": ["italy", "italian"],
        "de": ["germany", "german"],
        "fr": ["france", "french"],
        "es": ["spain", "spanish"],
        "pt": ["portugal", "portuguese"],
        "gr": ["greece", "greek"],
        "tr": ["turkey", "turkish"],
        "hr": ["croatia", "croatian"],
        "ro": ["romania", "romanian"],
        "be": ["belgium", "belgian"],
        "nl": ["netherlands", "dutch"],
        "ch": ["switzerland", "swiss"],
        "at": ["austria", "austrian"],
    }
    aliases = country_aliases.get(cc_hint, [])
    if any(alias in t for alias in aliases):
        return 0.12
    return 0.0


def build_wiki_query(modern_name: str, country_raw: Any, type_hint: str, cc_hint: str) -> str:
    variants = build_query_variants(modern_name, country_raw, type_hint, cc_hint)
    return variants[0] if variants else modern_name


def build_title_variants(
    modern_name: str,
    type_hint: str = "",
    extra_alternatives: list[str] | None = None,
) -> list[str]:
    """Return Wikipedia title candidates for *modern_name*.

    For each source name (primary + *extra_alternatives*) the function emits:
    - The name as-is
    - Name without a leading language-specific type-prefix word
      (e.g. "Fiume Magra" → "Magra")
    - "Name (disambig_word)" Wikipedia disambiguation variant
      (e.g. "Magra (river)", "Ohrid (lake)")
    """
    dab_word = TYPE_DISAMBIGUATION_WORDS.get(type_hint, "")
    type_pfx_lower = {p.lower().rstrip(".,") for p in TYPE_PREFIX_WORDS.get(type_hint, [])}

    def _base_names(name: str) -> list[str]:
        bases = [name]
        words = name.split(None, 1)
        if len(words) == 2 and words[0].lower().rstrip(".,") in type_pfx_lower:
            bases.append(words[1])
        return bases

    sources: list[str] = [modern_name]
    if extra_alternatives:
        sources.extend(extra_alternatives)

    out: list[str] = []
    seen: set[str] = set()

    def _add(title: str) -> None:
        t = " ".join(title.split()).strip(" ,;:-")
        key = normalize_text(t)
        if not t or key in seen:
            return
        out.append(t)
        seen.add(key)

    for src in sources:
        for base in _base_names(src):
            no_paren = base.split(" (", 1)[0].strip() if " (" in base else base
            candidates = [no_paren]

            folded_no_paren = ascii_fold(no_paren).strip()
            if folded_no_paren and folded_no_paren != no_paren:
                candidates.append(folded_no_paren)

            if no_paren != base:
                candidates.append(base)
                folded_base = ascii_fold(base).strip()
                if folded_base and folded_base != base:
                    candidates.append(folded_base)

            for cand in candidates:
                _add(cand)
                if dab_word and "(" not in cand:
                    _add(f"{cand} ({dab_word})")

    return out


def wiki_language_variants(cc_hint: str) -> list[str]:
    mapping = {
        "bg": ["en", "bg", "de"],
        "de": ["en", "de"],
        "fr": ["en", "fr"],
        "it": ["en", "it"],
        "es": ["en", "es"],
        "pt": ["en", "pt"],
        "tr": ["en", "tr"],
        "ro": ["en", "ro"],
        "hr": ["en", "hr"],
        "nl": ["en", "nl"],
        "be": ["en", "fr", "nl", "de"],
        "ch": ["en", "de", "fr", "it"],
        "at": ["en", "de"],
        "gr": ["en", "el"],
        "yu": ["en", "sr", "hr"],
    }
    langs = mapping.get(cc_hint, ["en"])
    seen: set[str] = set()
    out: list[str] = []
    for lang in langs:
        if not lang or lang in seen:
            continue
        out.append(lang)
        seen.add(lang)
    return out


def wiki_language_variants_for_name(modern_name: str, type_hint: str, cc_hint: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    override_langs = SEARCH_LANGUAGE_OVERRIDES.get((normalize_text(type_hint), normalize_text(modern_name)), [])
    for lang in override_langs + wiki_language_variants(cc_hint):
        if not lang or lang in seen:
            continue
        out.append(lang)
        seen.add(lang)
    return out


def fetch_wiki_search_candidates(
    session: requests.Session,
    query: str,
    timeout_sec: int,
    limit: int = 6,
) -> list[dict[str, Any]]:
    params = {
        "action": "query",
        "list": "search",
        "format": "json",
        "srsearch": query,
        "srlimit": limit,
        "srprop": "snippet|titlesnippet",
        "utf8": 1,
    }
    res = session.get(WIKI_API_URL, params=params, timeout=timeout_sec)
    res.raise_for_status()
    data = res.json()
    search = (data.get("query") or {}).get("search") or []
    return [item for item in search if isinstance(item, dict)]


def fetch_wiki_page_details(
    session: requests.Session,
    *,
    pageid: int | None = None,
    title: str | None = None,
    timeout_sec: int,
) -> dict[str, Any] | None:
    if pageid is None and not title:
        return None

    params: dict[str, Any] = {
        "action": "query",
        "format": "json",
        "prop": "coordinates|info|pageprops|categories",
        "inprop": "url",
        "redirects": 1,
        "colimit": 1,
        "cllimit": 20,
        "clshow": "!hidden",
        "utf8": 1,
    }
    if pageid is not None:
        params["pageids"] = int(pageid)
    else:
        params["titles"] = title

    res = session.get(WIKI_API_URL, params=params, timeout=timeout_sec)
    res.raise_for_status()
    data = res.json()
    pages = (data.get("query") or {}).get("pages") or {}
    if not isinstance(pages, dict) or not pages:
        return None

    page = next((p for p in pages.values() if isinstance(p, dict) and "missing" not in p), None)
    if not page:
        return None

    coords = page.get("coordinates") if isinstance(page.get("coordinates"), list) else []
    lat = None
    lng = None
    if coords:
        lat = coords[0].get("lat")
        lng = coords[0].get("lon")

    cats = []
    if isinstance(page.get("categories"), list):
        for c in page["categories"]:
            if isinstance(c, dict) and c.get("title"):
                cats.append(str(c["title"]))

    return {
        "pageid": page.get("pageid"),
        "title": page.get("title", ""),
        "fullurl": page.get("fullurl", ""),
        "lat": lat,
        "lng": lng,
        "categories": cats,
        "is_disambiguation": bool((page.get("pageprops") or {}).get("disambiguation")),
    }


def fetch_wiki_html_page_details(
    session: requests.Session,
    *,
    title: str,
    lang: str,
    timeout_sec: int,
) -> dict[str, Any] | None:
    if not title or not lang:
        return None

    url = f"https://{lang}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
    res = session.get(url, timeout=timeout_sec)
    res.raise_for_status()
    html = res.text

    coord_match = re.search(r'class="geo">\s*([+-]?\d+(?:\.\d+)?)\s*;\s*([+-]?\d+(?:\.\d+)?)\s*<', html)
    if not coord_match:
        coord_match = re.search(r'class="geo-dec"[^>]*>\s*([+-]?\d+(?:\.\d+)?)°?[NS]?\s+([+-]?\d+(?:\.\d+)?)°?[EW]?\s*<', html)
    lat = None
    lng = None
    if coord_match:
        lat = float(coord_match.group(1))
        lng = float(coord_match.group(2))
        if not has_valid_coords(lat, lng):
            lat = None
            lng = None

    if lat is None or lng is None:
        maplink_match = re.search(r'data-lat="([+-]?\d+(?:\.\d+)?)"[^>]*data-lon="([+-]?\d+(?:\.\d+)?)"', html)
        if maplink_match:
            parsed_lat = float(maplink_match.group(1))
            parsed_lng = float(maplink_match.group(2))
            if has_valid_coords(parsed_lat, parsed_lng):
                lat = parsed_lat
                lng = parsed_lng

    if lat is None or lng is None:
        geohack_match = re.search(r'geohack\.php[^"\']*?params=([^"\'&<>\s]+)', html)
        if geohack_match:
            parsed = parse_geohack_params(geohack_match.group(1))
            if parsed:
                lat, lng = parsed

    if lat is None or lng is None:
        return None

    title_match = re.search(r'<title>([^<]+?) - Wikipedia</title>', html)
    page_title = title_match.group(1).strip() if title_match else title
    categories = re.findall(r'title="Category:([^"]+)"', html)

    return {
        "pageid": None,
        "title": page_title,
        "fullurl": str(res.url),
        "lat": lat,
        "lng": lng,
        "categories": categories,
        "is_disambiguation": False,
    }


def wiki_candidate_score(
    modern_name: str,
    cc_hint: str,
    type_hint: str,
    search_hit: dict[str, Any],
    details: dict[str, Any],
) -> float:
    title = str(details.get("title", ""))
    snippet = str(search_hit.get("snippet", ""))
    categories = " ".join(details.get("categories", []))

    title_overlap = overlap_ratio(modern_name, title)
    snippet_overlap = overlap_ratio(modern_name, snippet)
    score = 0.0
    score += title_overlap * 0.5
    score += snippet_overlap * 0.2
    score += wiki_country_boost(" ".join([snippet, categories, title]), cc_hint)

    cat_blob = normalize_text(categories)
    type_score = 0.0
    if type_hint in WATER_HINT_TYPES:
        if any(tok in cat_blob for tok in ["rivers", "lakes", "bodies of water", "harbors", "ports", "islands"]):
            type_score = 0.22
        else:
            type_score = -0.08
    elif type_hint in CITY_TYPES:
        if any(tok in cat_blob for tok in ["cities", "towns", "villages", "municipalities"]):
            type_score = 0.16
    elif type_hint == "mountain":
        if any(tok in cat_blob for tok in ["mountains", "peaks", "volcanoes"]):
            type_score = 0.2
    elif type_hint in {"region", "roman_province", "modern_state"}:
        if any(tok in cat_blob for tok in ["regions", "provinces", "states"]):
            type_score = 0.15
    score += type_score

    if details.get("is_disambiguation"):
        score -= 0.25

    if not has_valid_coords(details.get("lat"), details.get("lng")):
        score -= 0.3

    return clamp(score, 0.0, 1.0)


def geocode_with_wikipedia(
    session: requests.Session,
    modern_name: str,
    country_raw: Any,
    cc_hint: str,
    type_hint: str,
    min_confidence: float,
    timeout_sec: int,
    extra_alternatives: list[str] | None = None,
) -> dict[str, Any]:
    title_variants = build_title_variants(modern_name, type_hint, extra_alternatives)
    html_scored: list[tuple[float, dict[str, Any], str, str]] = []
    for lang in wiki_language_variants_for_name(modern_name, type_hint, cc_hint):
        for title in title_variants:
            try:
                details = fetch_wiki_html_page_details(session, title=title, lang=lang, timeout_sec=timeout_sec)
            except Exception:
                continue
            if not details:
                continue
            pseudo_hit = {"snippet": details.get("title", ""), "title": details.get("title", "")}
            score = wiki_candidate_score(modern_name, cc_hint, type_hint, pseudo_hit, details)
            score = clamp(score + 0.14, 0.0, 1.0)
            html_scored.append((score, details, title, lang))

    if html_scored:
        html_scored.sort(key=lambda item: item[0], reverse=True)
        best_score, details, title_used, lang_used = html_scored[0]
        accepted = best_score >= min_confidence
        result = {
            "accepted": accepted,
            "provider": "wikipedia",
            "query": f"{title_used} [{lang_used}]",
            "lat": float(details["lat"]),
            "lng": float(details["lng"]),
            "confidence": round(best_score, 3),
            "display_name": str(details.get("title", "")),
            "provider_title": str(details.get("title", "")),
            "provider_url": str(details.get("fullurl", "")),
            "timestamp": now_iso(),
            "provider_chain": ["wikipedia"],
            "used_network": True,
        }
        return {"status": "accepted" if accepted else "needs_refinement", **result}

    direct_scored: list[tuple[float, dict[str, Any], str]] = []
    for title in title_variants:
        try:
            details = fetch_wiki_page_details(session, title=title, timeout_sec=timeout_sec)
        except Exception:
            continue
        if not details:
            continue

        pseudo_hit = {"snippet": details.get("title", ""), "title": details.get("title", "")}
        score = wiki_candidate_score(modern_name, cc_hint, type_hint, pseudo_hit, details)
        score = clamp(score + 0.12, 0.0, 1.0)
        direct_scored.append((score, details, title))

    if direct_scored:
        direct_scored.sort(key=lambda item: item[0], reverse=True)
        best_score, details, title_used = direct_scored[0]
        lat = details.get("lat")
        lng = details.get("lng")
        if has_valid_coords(lat, lng):
            accepted = best_score >= min_confidence
            result = {
                "accepted": accepted,
                "provider": "wikipedia",
                "query": title_used,
                "lat": float(lat),
                "lng": float(lng),
                "confidence": round(best_score, 3),
                "display_name": str(details.get("title", "")),
                "provider_title": str(details.get("title", "")),
                "provider_url": str(details.get("fullurl", "")),
                "timestamp": now_iso(),
                "provider_chain": ["wikipedia"],
                "used_network": True,
            }
            return {"status": "accepted" if accepted else "needs_refinement", **result}

    variants = build_query_variants(modern_name, country_raw, type_hint, cc_hint)
    scored: list[tuple[float, dict[str, Any], dict[str, Any], str]] = []
    last_query = modern_name

    for query in variants:
        last_query = query
        try:
            hits = fetch_wiki_search_candidates(session, query, timeout_sec)
        except Exception as exc:
            return {"status": "error", "error": f"wikipedia_search: {exc}", "provider": "wikipedia", "used_network": True}

        if not hits:
            continue

        for hit in hits:
            pageid = hit.get("pageid")
            if not isinstance(pageid, int):
                continue
            try:
                details = fetch_wiki_page_details(session, pageid=pageid, timeout_sec=timeout_sec)
            except Exception:
                continue
            if not details:
                continue
            score = wiki_candidate_score(modern_name, cc_hint, type_hint, hit, details)
            scored.append((score, hit, details, query))

        if scored:
            break

    if not scored:
        return {"status": "no_candidate", "provider": "wikipedia", "query": last_query, "used_network": True}

    scored.sort(key=lambda item: item[0], reverse=True)
    # Prefer the best scored page that actually has coordinates.
    valid_scored = [item for item in scored if has_valid_coords(item[2].get("lat"), item[2].get("lng"))]
    if not valid_scored:
        return {
            "status": "no_candidate",
            "provider": "wikipedia",
            "query": last_query,
            "reason": "no_coordinates",
            "used_network": True,
        }

    best_score, hit, details, query_used = valid_scored[0]
    second_score = valid_scored[1][0] if len(valid_scored) > 1 else 0.0

    lat = details.get("lat")
    lng = details.get("lng")

    accepted = best_score >= min_confidence and (best_score - second_score) >= 0.03
    result = {
        "accepted": accepted,
        "provider": "wikipedia",
        "query": query_used,
        "lat": float(lat),
        "lng": float(lng),
        "confidence": round(best_score, 3),
        "display_name": str(details.get("title", "")),
        "provider_title": str(details.get("title", "")),
        "provider_url": str(details.get("fullurl", "")),
        "timestamp": now_iso(),
        "provider_chain": ["wikipedia"],
        "used_network": True,
    }
    return {"status": "accepted" if accepted else "needs_refinement", **result}


def extract_wikipedia_title_from_url(url: str) -> str:
    try:
        parsed = urlparse(url)
    except Exception:
        return ""
    if "wikipedia.org" not in parsed.netloc.lower():
        return ""
    path = parsed.path or ""
    if "/wiki/" not in path:
        return ""
    title = path.split("/wiki/", 1)[1]
    return re.sub(r"#.*$", "", title).strip()


def extract_wikipedia_title_lang_from_url(url: str) -> tuple[str, str]:
    try:
        parsed = urlparse(url)
    except Exception:
        return "", ""

    netloc = parsed.netloc.lower()
    if "wikipedia.org" not in netloc:
        # Handle redirect wrappers like duckduckgo's /l/?uddg=...
        qs = parse_qs(parsed.query or "")
        wrapped = (qs.get("uddg") or [""])[0]
        if wrapped:
            return extract_wikipedia_title_lang_from_url(unquote(wrapped))
        return "", ""

    lang = netloc.split(".", 1)[0]
    title = extract_wikipedia_title_from_url(url)
    return title, lang


def fetch_wikipedia_links_via_web_search(
    session: requests.Session,
    query: str,
    timeout_sec: int,
) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    # Try Ecosia first (no API key). Some environments may return 403 for bot traffic.
    ecosia_ok = False
    try:
        res = session.get(
            "https://www.ecosia.org/search",
            params={"q": query},
            timeout=timeout_sec,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        if res.status_code == 200:
            ecosia_ok = True
            found = re.findall(r'https?://[a-z]+\\.wikipedia\\.org/wiki/[^"\\s<>]+', res.text)
            for url in found:
                if url in seen:
                    continue
                urls.append(url)
                seen.add(url)
    except Exception:
        pass

    # Fallback: DuckDuckGo HTML endpoint, still without API key.
    if not urls:
        try:
            ddg = session.get(
                "https://duckduckgo.com/html/",
                params={"q": query},
                timeout=timeout_sec,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if ddg.status_code == 200:
                found = re.findall(r'https?://[^"\'\s<>]+', ddg.text)
                for raw in found:
                    decoded = unquote(raw)
                    title, lang = extract_wikipedia_title_lang_from_url(decoded)
                    if not title or not lang:
                        continue
                    canonical = f"https://{lang}.wikipedia.org/wiki/{title}"
                    if canonical in seen:
                        continue
                    urls.append(canonical)
                    seen.add(canonical)
        except Exception:
            pass

    # Keep a hint for debugging in caller by ordering: ecosia URLs first if any.
    if ecosia_ok:
        return urls
    return urls


def geocode_with_ecosia_wikipedia_fallback(
    session: requests.Session,
    modern_name: str,
    country_raw: Any,
    cc_hint: str,
    type_hint: str,
    min_confidence: float,
    timeout_sec: int,
) -> dict[str, Any]:
    variants = build_query_variants(modern_name, country_raw, type_hint, cc_hint)
    q = f"site:wikipedia.org {variants[0] if variants else modern_name}".strip()

    links = fetch_wikipedia_links_via_web_search(session, q, timeout_sec)
    if not links:
        return {"status": "no_candidate", "provider": "ecosia", "query": q, "used_network": True}

    best: tuple[float, dict[str, Any], str, str] | None = None
    for link in links[:10]:
        title_encoded, lang = extract_wikipedia_title_lang_from_url(link)
        if not title_encoded or not lang:
            continue
        title = title_encoded.replace("_", " ")
        try:
            details = fetch_wiki_html_page_details(session, title=title, lang=lang, timeout_sec=timeout_sec)
        except Exception:
            continue
        if not details:
            continue
        pseudo_hit = {
            "snippet": str(details.get("title", "")),
            "title": str(details.get("title", "")),
        }
        score = wiki_candidate_score(modern_name, cc_hint, type_hint, pseudo_hit, details)
        score = clamp(score + 0.1, 0.0, 1.0)
        if best is None or score > best[0]:
            best = (score, details, title, lang)

    if best is None:
        return {"status": "no_candidate", "provider": "ecosia", "query": q, "used_network": True}

    score, details, title, lang = best
    accepted = score >= min_confidence
    out = {
        "accepted": accepted,
        "provider": "ecosia_wikipedia",
        "query": q,
        "lat": float(details["lat"]),
        "lng": float(details["lng"]),
        "confidence": round(score, 3),
        "display_name": str(details.get("title", "")),
        "provider_title": str(details.get("title", "")),
        "provider_url": str(details.get("fullurl", "")),
        "timestamp": now_iso(),
        "provider_chain": ["ecosia", "wikipedia"],
        "used_network": True,
    }
    return {"status": "accepted" if accepted else "needs_refinement", **out}


def geocode_with_google_wikipedia_fallback(
    session: requests.Session,
    modern_name: str,
    country_raw: Any,
    cc_hint: str,
    type_hint: str,
    min_confidence: float,
    timeout_sec: int,
    google_api_key: str,
    google_cse_id: str,
) -> dict[str, Any]:
    if not google_api_key or not google_cse_id:
        return {"status": "skipped", "provider": "google", "used_network": False}

    variants = build_query_variants(modern_name, country_raw, type_hint, cc_hint)
    q = f"site:en.wikipedia.org {variants[0] if variants else modern_name}".strip()

    params = {
        "key": google_api_key,
        "cx": google_cse_id,
        "q": q,
        "num": 5,
    }

    try:
        res = session.get(GOOGLE_CSE_URL, params=params, timeout=timeout_sec)
        res.raise_for_status()
        data = res.json()
    except Exception as exc:
        return {"status": "error", "error": f"google_cse: {exc}", "provider": "google", "used_network": True}

    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list) or not items:
        return {"status": "no_candidate", "provider": "google", "query": q, "used_network": True}

    for item in items:
        link = str((item or {}).get("link", ""))
        title_encoded = extract_wikipedia_title_from_url(link)
        if not title_encoded:
            continue
        title = title_encoded.replace("_", " ")

        try:
            details = fetch_wiki_page_details(session, title=title, timeout_sec=timeout_sec)
        except Exception:
            continue
        if not details:
            continue

        hit = {
            "snippet": str((item or {}).get("snippet", "")),
            "title": str((item or {}).get("title", "")),
        }
        score = wiki_candidate_score(modern_name, cc_hint, type_hint, hit, details)
        if not has_valid_coords(details.get("lat"), details.get("lng")):
            continue

        accepted = score >= min_confidence
        out = {
            "accepted": accepted,
            "provider": "google_wikipedia",
            "query": q,
            "lat": float(details["lat"]),
            "lng": float(details["lng"]),
            "confidence": round(score, 3),
            "display_name": str(details.get("title", "")),
            "provider_title": str(details.get("title", "")),
            "provider_url": str(details.get("fullurl", link)),
            "timestamp": now_iso(),
            "provider_chain": ["google", "wikipedia"],
            "used_network": True,
        }
        return {"status": "accepted" if accepted else "needs_refinement", **out}

    return {"status": "no_candidate", "provider": "google", "query": q, "used_network": True}


def nominatim_candidate_score(query_name: str, cc_hint: str, type_hint: str, candidate: dict[str, Any]) -> float:
    importance = float(candidate.get("importance", 0.0) or 0.0)
    display = str(candidate.get("display_name", ""))
    candidate_name = str(candidate.get("name", ""))
    overlap = max(overlap_ratio(query_name, display), overlap_ratio(query_name, candidate_name))

    score = 0.0
    score += clamp(importance, 0.0, 1.0) * 0.35
    score += overlap * 0.45
    score += type_fit_score(type_hint, str(candidate.get("class", "")), str(candidate.get("type", "")))

    addr = candidate.get("address", {}) if isinstance(candidate.get("address"), dict) else {}
    cc_returned = str(addr.get("country_code", "")).lower()
    if cc_hint:
        if cc_returned and cc_returned == cc_hint:
            score += 0.15
        elif cc_returned:
            score -= 0.2

    return clamp(score, 0.0, 1.0)


def geocode_with_nominatim(
    session: requests.Session,
    modern_name: str,
    country_raw: Any,
    cc_hint: str,
    type_hint: str,
    min_confidence: float,
    timeout_sec: int,
) -> dict[str, Any]:
    variants = build_query_variants(modern_name, country_raw, type_hint, cc_hint)
    candidates: list[dict[str, Any]] = []
    query_used = modern_name
    for query in variants:
        params = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 5,
        }
        if cc_hint:
            params["countrycodes"] = cc_hint

        try:
            res = session.get(NOMINATIM_URL, params=params, timeout=timeout_sec)
            res.raise_for_status()
            raw = res.json()
        except Exception as exc:
            return {"status": "error", "error": f"nominatim: {exc}", "provider": "nominatim", "used_network": True}

        if isinstance(raw, list) and raw:
            candidates = [c for c in raw if isinstance(c, dict)]
            query_used = query
            break

    if not candidates:
        return {"status": "no_candidate", "provider": "nominatim", "query": query_used, "used_network": True}

    scored: list[tuple[float, dict[str, Any]]] = []
    for c in candidates:
        if not isinstance(c, dict):
            continue
        scored.append((nominatim_candidate_score(modern_name, cc_hint, type_hint, c), c))

    if not scored:
        return {"status": "no_candidate", "provider": "nominatim", "query": modern_name, "used_network": True}

    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0

    try:
        lat = float(best.get("lat"))
        lng = float(best.get("lon"))
    except (TypeError, ValueError):
        return {"status": "no_candidate", "provider": "nominatim", "query": modern_name, "used_network": True}

    accepted = best_score >= min_confidence and (best_score - second_score) >= 0.03
    out = {
        "accepted": accepted,
        "provider": "nominatim",
        "query": query_used,
        "lat": lat,
        "lng": lng,
        "confidence": round(best_score, 3),
        "display_name": str(best.get("display_name", "")),
        "provider_title": str(best.get("display_name", "")),
        "provider_url": f"https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=11/{lat}/{lng}",
        "timestamp": now_iso(),
        "provider_chain": ["nominatim"],
        "used_network": True,
    }
    return {"status": "accepted" if accepted else "needs_refinement", **out}


def parse_strategy(value: str) -> list[str]:
    tokens = [normalize_text(v) for v in (value or "").split(",")]
    allowed = {"wikipedia", "ecosia", "google", "nominatim"}
    out = [t for t in tokens if t in allowed]
    if not out:
        return ["wikipedia", "nominatim"]
    # Keep order while removing duplicates.
    seen: set[str] = set()
    uniq: list[str] = []
    for t in out:
        if t in seen:
            continue
        uniq.append(t)
        seen.add(t)
    return uniq


def geocode_record(
    record: dict[str, Any],
    session: requests.Session,
    cache: dict[str, Any],
    *,
    strategy_steps: list[str],
    min_confidence: float,
    min_confidence_wikipedia: float,
    min_confidence_nominatim: float,
    timeout_sec: int,
    google_api_key: str,
    google_cse_id: str,
) -> dict[str, Any]:
    # Skip only when our geocoding pipeline has already produced output coordinates.
    # Records may carry raw input lat/lng from the source data but still need
    # Wikipedia enrichment (geocoding_lat == None means we haven't geocoded yet).
    if record.get("geocoding_lat") is not None and record.get("geocoding_lng") is not None:
        return {"status": "skipped_has_coords", "used_network": False}

    cc_hint = country_code_hint(record.get("country", ""))
    country_raw = record.get("country", "")
    type_hint = str(record.get("type", "")).strip().lower()
    modern_name = primary_search_name(str(record.get("modern_preferred", "")), type_hint)
    if not modern_name:
        modern_name = latin_fallback_search_name(str(record.get("latin_std", "")), type_hint)
    if not modern_name:
        return {"status": "no_query", "used_network": False}
    # Collect alternative names from "|"-separated fields (e.g. "Tavo | Vomano")
    _all_alts = extract_name_alternatives(str(record.get("modern_preferred", "")))
    extra_alternatives = [a for a in _all_alts if normalize_text(a) != normalize_text(modern_name)]
    strategy_key = ",".join(strategy_steps)
    key = cache_key(modern_name, cc_hint, type_hint, strategy_key)

    cached = cache.get(key)
    if isinstance(cached, dict):
        out = dict(cached)
        out["status"] = "cached_accepted" if cached.get("accepted") else "cached_refine"
        out["used_network"] = False
        return out

    history: list[dict[str, Any]] = []

    for step in strategy_steps:
        if step == "wikipedia":
            outcome = geocode_with_wikipedia(
                session,
                modern_name,
                country_raw,
                cc_hint,
                type_hint,
                min_confidence=min_confidence_wikipedia,
                timeout_sec=timeout_sec,
                extra_alternatives=extra_alternatives,
            )
        elif step == "ecosia":
            outcome = geocode_with_ecosia_wikipedia_fallback(
                session,
                modern_name,
                country_raw,
                cc_hint,
                type_hint,
                min_confidence=min_confidence_wikipedia,
                timeout_sec=timeout_sec,
            )
        elif step == "google":
            outcome = geocode_with_google_wikipedia_fallback(
                session,
                modern_name,
                country_raw,
                cc_hint,
                type_hint,
                min_confidence=min_confidence_wikipedia,
                timeout_sec=timeout_sec,
                google_api_key=google_api_key,
                google_cse_id=google_cse_id,
            )
        elif step == "nominatim":
            outcome = geocode_with_nominatim(
                session,
                modern_name,
                country_raw,
                cc_hint,
                type_hint,
                min_confidence=min_confidence_nominatim,
                timeout_sec=timeout_sec,
            )
        else:
            continue

        history.append(
            {
                "step": step,
                "status": outcome.get("status"),
                "provider": outcome.get("provider", step),
                "confidence": outcome.get("confidence"),
                "display_name": outcome.get("display_name", ""),
                "provider_url": outcome.get("provider_url", ""),
            }
        )

        status = str(outcome.get("status", ""))
        if status in {"accepted", "needs_refinement"}:
            result = {
                "accepted": status == "accepted",
                "lat": outcome.get("lat"),
                "lng": outcome.get("lng"),
                "confidence": float(outcome.get("confidence", 0.0) or 0.0),
                "query": modern_name,
                "country": cc_hint,
                "type": type_hint,
                "display_name": outcome.get("display_name", ""),
                "provider": outcome.get("provider", step),
                "provider_title": outcome.get("provider_title", ""),
                "provider_url": outcome.get("provider_url", ""),
                "provider_chain": outcome.get("provider_chain", [step]),
                "history": history,
                "timestamp": outcome.get("timestamp", now_iso()),
            }
            cache[key] = result
            return {"status": status, "used_network": True, **result}

    cache[key] = {
        "accepted": False,
        "query": modern_name,
        "country": cc_hint,
        "type": type_hint,
        "provider": "none",
        "reason": "no_candidate",
        "provider_chain": strategy_steps,
        "history": history,
        "timestamp": now_iso(),
    }
    return {
        "status": "no_candidate",
        "query": modern_name,
        "provider": "none",
        "provider_chain": strategy_steps,
        "history": history,
        "used_network": True,
    }


def enrich_records(
    records: list[dict[str, Any]],
    *,
    dry_run: bool,
    max_records: int,
    refresh_cache: bool,
    min_confidence: float,
    delay_seconds: float,
    timeout_sec: int,
    strategy: str = "wikipedia,nominatim",
    min_confidence_wikipedia: float | None = None,
    min_confidence_nominatim: float | None = None,
    google_api_key: str | None = None,
    google_cse_id: str | None = None,
    require_modern_name: bool = True,
) -> dict[str, Any]:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "TabulaPeutingeriana-Geocoder/2.0 (research; contact: local)",
            "Accept-Language": "en",
        }
    )

    cache = load_cache(refresh=refresh_cache)
    strategy_steps = parse_strategy(strategy)
    wiki_threshold = min_confidence if min_confidence_wikipedia is None else min_confidence_wikipedia
    nominatim_threshold = min_confidence if min_confidence_nominatim is None else min_confidence_nominatim

    google_key = google_api_key or os.getenv("GOOGLE_API_KEY", "")
    google_cx = google_cse_id or os.getenv("GOOGLE_CSE_ID", "")

    summary = {
        "processed": 0,
        "accepted": 0,
        "needs_refinement": 0,
        "no_candidate": 0,
        "no_query": 0,
        "errors": 0,
        "cached": 0,
        "skipped_has_coords": 0,
        "accepted_by_source": {
            "wikipedia": 0,
            "ecosia_wikipedia": 0,
            "google_wikipedia": 0,
            "nominatim": 0,
        },
        "strategy": strategy_steps,
    }
    refinement_queue: list[dict[str, Any]] = []

    candidates = [r for r in records if r.get("lat") is None or r.get("lng") is None]
    if require_modern_name:
        candidates = [r for r in candidates if primary_search_name(str(r.get("modern_preferred", "")), str(r.get("type", "")).strip().lower())]
    if max_records > 0:
        candidates = candidates[:max_records]

    for record in candidates:
        outcome = geocode_record(
            record,
            session,
            cache,
            strategy_steps=strategy_steps,
            min_confidence=min_confidence,
            min_confidence_wikipedia=max(0.0, min(1.0, wiki_threshold)),
            min_confidence_nominatim=max(0.0, min(1.0, nominatim_threshold)),
            timeout_sec=timeout_sec,
            google_api_key=google_key,
            google_cse_id=google_cx,
        )
        status = outcome.get("status", "")
        used_network = bool(outcome.get("used_network"))

        summary["processed"] += 1
        if str(status).startswith("cached"):
            summary["cached"] += 1
            status = "accepted" if status == "cached_accepted" else "needs_refinement"

        if status == "skipped_has_coords":
            summary["skipped_has_coords"] += 1
        elif status == "accepted":
            summary["accepted"] += 1
            provider = str(outcome.get("provider", ""))
            if provider in summary["accepted_by_source"]:
                summary["accepted_by_source"][provider] += 1
            if not dry_run:
                record["lat"] = outcome.get("lat")
                record["lng"] = outcome.get("lng")
                record["geocoding_confidence"] = outcome.get("confidence")
                record["geocoding_status"] = "accepted"
                record["geocoding_timestamp"] = outcome.get("timestamp")
                record["geocoding_provider_title"] = outcome.get("provider_title")
                record["geocoding_provider_url"] = outcome.get("provider_url")
        elif status == "needs_refinement":
            summary["needs_refinement"] += 1
            refinement_queue.append(
                {
                    "record_id": record.get("record_id"),
                    "data_id": record.get("data_id"),
                    "modern_preferred": record.get("modern_preferred"),
                    "country": record.get("country"),
                    "type": record.get("type"),
                    "suggested_lat": outcome.get("lat"),
                    "suggested_lng": outcome.get("lng"),
                    "confidence": outcome.get("confidence"),
                    "display_name": outcome.get("display_name", ""),
                    "query": outcome.get("query"),
                    "provider": outcome.get("provider", ""),
                    "provider_url": outcome.get("provider_url", ""),
                    "history": outcome.get("history", []),
                }
            )
            if not dry_run:
                record["geocoding_status"] = "needs_refinement"
                record["geocoding_confidence"] = outcome.get("confidence")
                record["geocoding_timestamp"] = outcome.get("timestamp")
                record["geocoding_provider_title"] = outcome.get("provider_title")
                record["geocoding_provider_url"] = outcome.get("provider_url")
        elif status == "no_candidate":
            summary["no_candidate"] += 1
            if not dry_run:
                record["geocoding_status"] = "no_candidate"
                record["geocoding_confidence"] = outcome.get("confidence")
                record["geocoding_timestamp"] = outcome.get("timestamp", now_iso())
                record["geocoding_provider_title"] = outcome.get("provider_title")
                record["geocoding_provider_url"] = outcome.get("provider_url")
        elif status == "no_query":
            summary["no_query"] += 1
            if not dry_run:
                record["geocoding_status"] = "no_query"
                record["geocoding_confidence"] = None
                record["geocoding_timestamp"] = now_iso()
                record["geocoding_provider_title"] = None
                record["geocoding_provider_url"] = None
        elif status == "error":
            summary["errors"] += 1
            if not dry_run:
                record["geocoding_status"] = "error"
                record["geocoding_confidence"] = outcome.get("confidence")
                record["geocoding_timestamp"] = outcome.get("timestamp", now_iso())
                record["geocoding_provider_title"] = outcome.get("provider_title")
                record["geocoding_provider_url"] = outcome.get("provider_url")
                record["geocoding_error"] = outcome.get("error")

        if used_network and delay_seconds > 0:
            time.sleep(delay_seconds)

    save_cache(cache)

    return {
        "summary": summary,
        "refinement_queue": refinement_queue,
    }
