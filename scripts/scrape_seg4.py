"""
Scrape segment IV places from tabula-peutingeriana.de list page.
Extracts: Latin name, modern name, type, grid position, tile ref, Talbert ID.
Maps grid positions to pixel coordinates on the 150dpi Weber image (4371x2105).

Grid system: 5 columns x 3 rows per segment.
  Rows: o = oben (top/a), m = middle (b), u = unten (bottom/c)
  Cols: 1-5 left to right

Output: public/data/seg4_places.json
"""

import json
import math
import re
import requests
from bs4 import BeautifulSoup

URL = "https://www.tabula-peutingeriana.de/list.html?segm=3"
# Weber 150dpi image for segment IV
IMG_W = 4371
IMG_H = 2105
COLS = 5
ROWS = 3
CELL_W = IMG_W / COLS   # ~874
CELL_H = IMG_H / ROWS   # ~702

ROW_MAP = {"o": 0, "m": 1, "u": 2}  # oben/mitte/unten -> row index

print(f"Fetching {URL} ...")
r = requests.get(URL, timeout=30)
r.encoding = "utf-8"
soup = BeautifulSoup(r.text, "html.parser")

# Find all place rows - they have classes like 'row locus', 'row regio', etc.
place_rows = soup.select("div.row.locus, div.row.regio, div.row.gens, div.row.insula, div.row.mons, div.row.aqua")
print(f"Found {len(place_rows)} place rows")

TYPE_MAP = {
    "locus": "road_station",
    "regio": "region",
    "gens": "people",
    "insula": "island",
    "mons": "mountain",
    "aqua": "river",
}

places = []

for row_div in place_rows:
    classes = row_div.get("class", [])
    # Determine type from CSS class
    ptype = "road_station"
    for cls in classes:
        if cls in TYPE_MAP:
            ptype = TYPE_MAP[cls]
            break

    cols = row_div.select("div[class*='col-md']")
    if len(cols) < 2:
        continue

    # Column 1: Latin name — text before ‖ separator
    col1 = cols[0]
    col1_text = col1.get_text(" ", strip=True)
    # Split on ‖ to get original name vs standardized
    parts = col1_text.split("\u2016")  # ‖
    latin = parts[0].strip() if parts else ""
    latin_std = parts[1].strip() if len(parts) > 1 else ""

    # Clean up Latin name — remove [ ] brackets for unnamed/uncertain
    latin_clean = latin.replace("[ ]", "").replace("[]", "").strip()
    if latin_clean.startswith("[") and latin_clean.endswith("]"):
        latin_clean = latin_clean[1:-1].strip()
    # Remove leading/trailing brackets from partial names
    latin_clean = re.sub(r"^\[\s*", "", latin_clean)
    latin_clean = re.sub(r"\s*\]$", "", latin_clean)

    # Extract symbol type from col1 text: e.g. "(Symb. Aa1)"
    sym_match = re.search(r"Symb\.\s*(\w+)", col1_text)
    if sym_match:
        sym = sym_match.group(1)
        if sym.startswith("Aa"):
            ptype = "major_city"
        elif sym.startswith("Ab") or sym.startswith("Ac"):
            ptype = "city"
        elif sym.startswith("Ad"):
            ptype = "port"  # double tower/port
        elif sym.startswith("E"):
            ptype = "port"  # harbor symbol

    # Also extract standardized Latin name from bold or 2nd part
    bold = col1.select_one("b")
    if bold:
        latin_std = bold.get_text(strip=True)
    # Best Latin: use cleaned original if non-empty, else standardized
    latin_final = latin_clean if latin_clean else latin_std

    # Column 2: Type keyword + grid reference
    col2 = cols[1]
    col2_text = col2.get_text(" ", strip=True)
    # Grid ref: "IV 3 m" means segment IV, column 3, row m (middle)
    grid_match = re.search(r"IV\s+(\d)\s+([omu])", col2_text)
    grid_col = 0
    grid_row = ""
    if grid_match:
        grid_col = int(grid_match.group(1))
        grid_row = grid_match.group(2)

    # data-id from input element
    data_input = row_div.select_one("input[data-id]")
    data_id = int(data_input["data-id"]) if data_input else 0

    # Column 3+: Province, country, modern name
    province = ""
    country = ""
    modern = ""
    if len(cols) >= 3:
        col3 = cols[2]
        # Province code (2-3 letters like ITA, NOR, etc.)
        col3_text = col3.get_text(" ", strip=True)
        prov_match = re.match(r"([A-Z]{2,4})", col3_text)
        if prov_match:
            province = prov_match.group(1)
        # Country code
        country_match = re.search(r"\b([A-Z]{1,2})\b", col3_text[len(province):])
        if country_match:
            country = country_match.group(1)
    if len(cols) >= 4:
        col4 = cols[3]
        col4_text = col4.get_text(strip=True)
        if col4_text:
            modern = col4_text

    # Skip completely unnamed/unidentifiable places
    if not latin_final or latin_final in ("?", "[ ? ]"):
        continue

    places.append({
        "latin": latin_final,
        "latin_std": latin_std,
        "modern": modern,
        "type": ptype,
        "grid_col": grid_col,
        "grid_row": grid_row,
        "province": province,
        "country": country,
        "data_id": data_id,
    })

print(f"Parsed {len(places)} places")

# Show type distribution
from collections import Counter
types = Counter(p["type"] for p in places)
print(f"Types: {dict(types.most_common())}")

# Check grid coverage
grid_counts = Counter((p["grid_col"], p["grid_row"]) for p in places if p["grid_col"])
print(f"Grid cells used: {len(grid_counts)}")
for cell, count in sorted(grid_counts.items()):
    print(f"  col={cell[0]} row={cell[1]}: {count} places")

# ============================================================
# Map grid positions to pixel coordinates on 4371x2105 image
# ============================================================

# Group by grid cell for sub-grid distribution
by_cell = {}
no_grid = []
for p in places:
    if p["grid_col"] and p["grid_row"]:
        key = (p["grid_col"], p["grid_row"])
        by_cell.setdefault(key, []).append(p)
    else:
        no_grid.append(p)

output = []
for (col, row_key), cell_places in by_cell.items():
    row_idx = ROW_MAP.get(row_key, 1)
    # Cell center
    cx = (col - 0.5) * CELL_W
    cy = (row_idx + 0.5) * CELL_H

    n = len(cell_places)
    if n == 1:
        positions = [(cx, cy)]
    else:
        # Sub-grid distribution within the cell
        usable_w = CELL_W * 0.8
        usable_h = CELL_H * 0.8
        ncols = max(1, int(math.ceil(math.sqrt(n * usable_w / usable_h))))
        nrows = max(1, int(math.ceil(n / ncols)))
        positions = []
        for i in range(n):
            r = i // ncols
            c = i % ncols
            px = cx - usable_w / 2 + (c + 0.5) / ncols * usable_w
            py = cy - usable_h / 2 + (r + 0.5) / nrows * usable_h
            px = max(0, min(IMG_W - 1, px))
            py = max(0, min(IMG_H - 1, py))
            positions.append((px, py))

    for i, p in enumerate(cell_places):
        px, py = positions[i]
        entry = {
            "id": len(output) + 1,
            "latin": p["latin"],
            "latin_std": p["latin_std"],
            "modern": p["modern"],
            "type": p["type"],
            "px": round(px, 1),
            "py": round(py, 1),
            "province": p["province"],
            "country": p["country"],
            "data_id": p["data_id"],
            "grid_col": p["grid_col"],
            "grid_row": p["grid_row"],
        }
        output.append(entry)

# Handle places without grid reference
for p in no_grid:
    entry = {
        "id": len(output) + 1,
        "latin": p["latin"],
        "latin_std": p["latin_std"],
        "modern": p["modern"],
        "type": p["type"],
        "px": IMG_W / 2,  # center fallback
        "py": IMG_H / 2,
        "province": p["province"],
        "country": p["country"],
        "data_id": p["data_id"],
        "grid_col": 0,
        "grid_row": "",
    }
    output.append(entry)

print(f"\nOutput: {len(output)} places")
print(f"Places without grid ref: {len(no_grid)}")

# Position stats
from collections import Counter as C2
cells = C2((round(p["px"] / 200) * 200, round(p["py"] / 200) * 200) for p in output)
print(f"Unique 200px cells: {len(cells)}")
print(f"Max per cell: {max(cells.values())}")

# Save
with open("public/data/seg4_places.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\nSaved to public/data/seg4_places.json")

# Show some examples
print("\nSample places:")
for p in output[:10]:
    print(f"  {p['latin']:30s} {p['modern']:20s} ({p['type']:15s}) px={p['px']:.0f} py={p['py']:.0f}")
