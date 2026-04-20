"""
Build improved places.json by:
1. Using OmnesViae data (with real lat/lng coordinates)
2. Merging with scraped data (for segment/grid, region, country, notes)
3. Mapping lat/lng to pixel coordinates using control points + interpolation

The Tabula Peutingeriana (Miller 1887) is 46,380 × 2,953 pixels.
It's a heavily distorted strip map — simple linear mapping won't work.
We use known landmark control points for piecewise affine interpolation.
"""

import json
import math
import re
from collections import Counter

# Load data
with open("scripts/omnesviae_sample.json", encoding="utf-8") as f:
    ov_data = json.load(f)
with open("public/data/places.json", encoding="utf-8") as f:
    scraped = json.load(f)

ov_places = [n for n in ov_data["@graph"] if n.get("@type") == "Place"]
print(f"OmnesViae places: {len(ov_places)}")
print(f"Scraped places: {len(scraped)}")

# ============================================================
# CONTROL POINTS: well-known cities with known TP pixel positions
# These are estimated from the map structure:
# - Image: 46,380 × 2,953 px, 11 segments of ~4,216 px each
# - Top = north (mostly), Bottom = south/Africa
# - Left = west, Right = east
#
# Pixel positions determined by:
# - Examining segment assignments from tabula-peutingeriana.de
# - Cross-referencing with the known layout of the Miller 1887 edition
# - General knowledge of where cities appear on the TP
# ============================================================

IMG_W = 46380
IMG_H = 2953
SEG_W = IMG_W / 11  # ~4216 px per segment

# (lat, lng) -> (px_x, px_y)
# px_x: 0 = left edge, 46380 = right edge
# px_y: 0 = top edge, 2953 = bottom edge
CONTROL_POINTS = [
    # Segment II (idx 0): Britannia, Gallia, Mauretania
    # Londinium (London) - top area, middle of segment
    (51.51, -0.09,   SEG_W * 0.5,     IMG_H * 0.18),
    # Camulodunum (Colchester) - top right
    (51.89,  0.90,   SEG_W * 0.65,    IMG_H * 0.15),
    # Lutetia (Paris) - col 3-4, row b
    (48.86,  2.35,   SEG_W * 0.7,     IMG_H * 0.40),
    # Caesarea Mauretaniae (Cherchell) - bottom
    (36.60,  2.26,   SEG_W * 0.7,     IMG_H * 0.85),

    # Segment III (idx 1): Germania, Gallia, Liguria
    # Colonia Agrippina (Cologne) - top
    (50.94,  6.96,   SEG_W * 1.3,     IMG_H * 0.15),
    # Lugdunum (Lyon) - middle
    (45.76,  4.83,   SEG_W * 1.2,     IMG_H * 0.40),
    # Genua (Genova) - mid-low
    (44.41,  8.93,   SEG_W * 1.6,     IMG_H * 0.50),
    # Carthago Nova (Cartagena) - far left bottom area
    (37.60, -0.99,   SEG_W * 0.3,     IMG_H * 0.80),

    # Segment IV (idx 2): Raetia, Italia
    # Augusta Vindelicorum (Augsburg) - top
    (48.37, 10.89,   SEG_W * 2.3,     IMG_H * 0.15),
    # Mediolanum (Milan) - middle
    (45.46,  9.19,   SEG_W * 2.2,     IMG_H * 0.38),
    # Roma - bottom-middle of seg IV going into seg V
    (41.90, 12.50,   SEG_W * 2.85,    IMG_H * 0.48),
    # Florentia (Florence)
    (43.77, 11.25,   SEG_W * 2.6,     IMG_H * 0.42),

    # Segment V (idx 3): Noricum, Italia  
    # Vindobona (Vienna) - top
    (48.21, 16.37,   SEG_W * 3.3,     IMG_H * 0.12),
    # Aquileia - middle-left
    (45.77, 13.37,   SEG_W * 3.0,     IMG_H * 0.30),
    # Neapolis (Naples) - mid
    (40.85, 14.27,   SEG_W * 3.3,     IMG_H * 0.55),
    # Carthago (Tunis) - bottom
    (36.85, 10.17,   SEG_W * 3.0,     IMG_H * 0.82),

    # Segment VI (idx 4): Dalmatia, Italia
    # Sirmium (Sremska Mitrovica) - top
    (44.97, 19.61,   SEG_W * 4.3,     IMG_H * 0.18),
    # Brundisium (Brindisi) - middle
    (40.64, 17.94,   SEG_W * 4.2,     IMG_H * 0.50),
    # Leptis Magna - bottom
    (32.64, 14.29,   SEG_W * 4.0,     IMG_H * 0.88),

    # Segment VII (idx 5): Macedonia, Achaia, Africa
    # Thessalonica (Thessaloniki) - top-mid
    (40.64, 22.94,   SEG_W * 5.3,     IMG_H * 0.20),
    # Athenae (Athens) - middle
    (37.97, 23.73,   SEG_W * 5.5,     IMG_H * 0.35),
    # Corinthus - middle
    (37.91, 22.88,   SEG_W * 5.3,     IMG_H * 0.38),
    # Cyrene - bottom
    (32.82, 21.86,   SEG_W * 5.2,     IMG_H * 0.82),

    # Segment VIII (idx 6): Thracia, Dacia
    # Constantinopolis (Istanbul) - top area
    (41.01, 28.98,   SEG_W * 6.7,     IMG_H * 0.18),
    # Sinope - top-right
    (42.02, 35.15,   SEG_W * 6.9,     IMG_H * 0.12),
    # Nicomedia (Izmit) - top area
    (40.77, 29.94,   SEG_W * 6.8,     IMG_H * 0.22),
    # Ephesus - middle
    (37.94, 27.35,   SEG_W * 6.4,     IMG_H * 0.38),

    # Segment IX (idx 7): Asia, Aegyptus
    # Ancyra (Ankara) - top
    (39.93, 32.87,   SEG_W * 7.3,     IMG_H * 0.18),
    # Iconium (Konya) - middle
    (37.87, 32.48,   SEG_W * 7.3,     IMG_H * 0.35),
    # Alexandria - bottom
    (31.20, 29.92,   SEG_W * 7.1,     IMG_H * 0.82),
    # Tarsus - right  
    (36.92, 34.89,   SEG_W * 7.7,     IMG_H * 0.38),

    # Segment X (idx 8): Cappadocia, Syria, Palaestina
    # Antiochia (Antakya) - top-left
    (36.20, 36.16,   SEG_W * 8.2,     IMG_H * 0.30),
    # Damascus - middle
    (33.51, 36.29,   SEG_W * 8.3,     IMG_H * 0.50),
    # Jerusalem - middle-bottom
    (31.77, 35.23,   SEG_W * 8.2,     IMG_H * 0.60),
    # Caesarea Palaestinae
    (32.50, 34.89,   SEG_W * 8.1,     IMG_H * 0.55),

    # Segment XI (idx 9): Mesopotamia, Arabia, Persia
    # Edessa (Urfa) - top
    (37.16, 38.79,   SEG_W * 9.3,     IMG_H * 0.18),
    # Palmyra - middle
    (34.55, 38.27,   SEG_W * 9.2,     IMG_H * 0.40),
    # Ctesiphon (near Baghdad) - middle
    (33.09, 44.58,   SEG_W * 9.7,     IMG_H * 0.50),
    # Petra - bottom
    (30.33, 35.44,   SEG_W * 9.0,     IMG_H * 0.75),

    # Segment XII (idx 10): Persia, India
    # Persepolis - middle-left
    (29.93, 52.89,   SEG_W * 10.3,    IMG_H * 0.50),
    # Indus mouth area - far right
    (24.85, 67.86,   SEG_W * 10.7,    IMG_H * 0.60),

    # Extra boundary anchors to prevent wild extrapolation
    # Northwest corner (Britain)
    (55.00, -5.00,   0,               0),
    # Southwest corner (Mauretania/Atlantic)
    (30.00, -9.00,   0,               IMG_H),
    # Northeast corner (above Crimea)
    (46.00, 35.00,   SEG_W * 7.0,     0),
    # Southeast corner (India)
    (10.00, 86.00,   IMG_W,           IMG_H),
    # Far east top
    (40.00, 65.00,   SEG_W * 10.5,    0),
]


# ============================================================
# Interpolation: Inverse Distance Weighting (IDW)
# For each query point (lat, lng), use the K nearest control points
# weighted by inverse distance to estimate (px, py).
# ============================================================

def geo_dist(lat1, lng1, lat2, lng2):
    """Approximate distance in degrees (Euclidean on lat/lng)."""
    dlat = lat1 - lat2
    dlng = (lng1 - lng2) * math.cos(math.radians((lat1 + lat2) / 2))
    return math.sqrt(dlat * dlat + dlng * dlng)


def idw_interpolate(lat, lng, control_points, k=8, power=2.0):
    """Inverse Distance Weighting interpolation."""
    # Compute distances to all control points
    dists = []
    for clat, clng, cpx, cpy in control_points:
        d = geo_dist(lat, lng, clat, clng)
        if d < 0.001:  # exact match
            return cpx, cpy
        dists.append((d, cpx, cpy))

    # Sort by distance, take k nearest
    dists.sort()
    nearest = dists[:k]

    # Weighted average
    w_sum = 0
    px_sum = 0
    py_sum = 0
    for d, cpx, cpy in nearest:
        w = 1.0 / (d ** power)
        w_sum += w
        px_sum += w * cpx
        py_sum += w * cpy

    return px_sum / w_sum, py_sum / w_sum


# ============================================================
# Name matching between OmnesViae and scraped data
# ============================================================

def normalize_name(s):
    """Normalize Latin name for matching."""
    s = s.lower().strip()
    # Remove macrons, diacritics
    s = s.replace("\u0304", "").replace("\u0305", "")
    # Common TP spelling variations
    s = re.sub(r"[^a-z ]", "", s)
    s = s.strip()
    return s


def latin_normalize(s):
    """Deep normalization for Latin spelling variations on the TP."""
    s = normalize_name(s)
    # V ↔ U (LVGDVNVM = Lugdunum)
    s = s.replace("v", "u")
    # AE ↔ E (Caesarea = Cesarea)
    s = s.replace("ae", "e")
    # OE ↔ E
    s = s.replace("oe", "e")
    # PH ↔ F
    s = s.replace("ph", "f")
    # Y ↔ I
    s = s.replace("y", "i")
    # TH ↔ T
    s = s.replace("th", "t")
    # Double consonants → single
    s = re.sub(r"(.)\1", r"\1", s)
    # Remove trailing suffixes that vary (um/us/a/is/on)
    s = re.sub(r"(um|us|is|on|os|as)$", "", s)
    # Remove spaces
    s = s.replace(" ", "")
    return s


# Build lookup from scraped data - both exact and fuzzy
scraped_by_name = {}
scraped_by_latin_norm = {}
for p in scraped:
    key = normalize_name(p["latin"])
    if key and key not in scraped_by_name:
        scraped_by_name[key] = p
    lkey = latin_normalize(p["latin"])
    if lkey and lkey not in scraped_by_latin_norm:
        scraped_by_latin_norm[lkey] = p


# ============================================================
# Process OmnesViae places
# ============================================================

# Symbol to type mapping
def symbol_to_type(symbol):
    if not symbol:
        return "road_station"
    s = symbol.upper()
    if s.startswith("AA"):
        return "major_city"
    if s.startswith("AB"):
        return "city"
    if s.startswith("AC"):
        return "city"
    if s.startswith("F"):
        return "major_city"  # special landmark (e.g. lighthouse)
    if s in ("O", "Q"):
        return "port"
    if s.startswith("C"):
        return "road_station"  # with symbol
    if s.startswith("B"):
        return "road_station"
    return "road_station"

# Process all OmnesViae places
output_places = []
ov_grid_deferred = {}  # (seg_idx, col, row) -> list of entries to sub-grid distribute
matched = 0
unmatched = 0
no_coords = 0

for idx, ovp in enumerate(ov_places):
    place_id = ovp.get("@id", "").split("#")[-1]
    label = ovp.get("label", "")
    modern = ovp.get("modern", "")
    lat = ovp.get("lat")
    lng = ovp.get("lng")
    symbol = ovp.get("symbol", "")

    if not label:
        continue

    # Try to match with scraped data (exact first, then Latin-normalized)
    norm = normalize_name(label)
    scraped_match = scraped_by_name.get(norm)
    if not scraped_match:
        lnorm = latin_normalize(label)
        scraped_match = scraped_by_latin_norm.get(lnorm)

    # Determine type
    ptype = symbol_to_type(symbol)

    # If we have scraped data, use its additional fields; also upgrade type
    region = ""
    country = ""
    notes = ""
    segment = 0
    col = 0
    row = ""

    if scraped_match:
        matched += 1
        region = scraped_match.get("region", "")
        country = scraped_match.get("country", "")
        notes = scraped_match.get("notes", "")
        segment = scraped_match.get("segment", 0)
        col = scraped_match.get("col", 0)
        row = scraped_match.get("row", "")
        if not modern and scraped_match.get("modern"):
            modern = scraped_match["modern"]
        # Use scraped type if it's more specific
        scraped_type = scraped_match.get("type", "")
        if scraped_type in ("river", "island", "mountain", "people", "region"):
            ptype = scraped_type
    else:
        unmatched += 1

    # Compute pixel position
    if lat is not None and lng is not None:
        px, py = idw_interpolate(lat, lng, CONTROL_POINTS)
        # Clamp to image bounds
        px = max(0, min(IMG_W - 1, px))
        py = max(0, min(IMG_H - 1, py))
    else:
        no_coords += 1
        # Fall back to segment grid if we have it — defer for sub-grid distribution
        if segment and col and row:
            seg_idx = segment - 2
            cell_key = (seg_idx, col, row)
            deferred_entry = {
                "latin": label,
                "modern": modern,
                "type": ptype,
                "region": region,
                "country": country,
                "notes": notes,
            }
            if cell_key not in ov_grid_deferred:
                ov_grid_deferred[cell_key] = []
            ov_grid_deferred[cell_key].append(deferred_entry)
        else:
            # Skip places without any position data
            pass
        continue

    entry = {
        "id": idx + 1,
        "latin": label,
        "modern": modern,
        "type": ptype,
        "px": round(px, 1),
        "py": round(py, 1),
        "region": region,
        "country": country,
        "notes": notes,
    }

    # Add lat/lng for possible future use
    if lat is not None:
        entry["lat"] = lat
        entry["lng"] = lng

    output_places.append(entry)


# ============================================================
# Add unmatched scraped places + deferred OV grid places
# Distribute all grid-based places within cells to avoid overlap
# ============================================================

ov_names = set(normalize_name(p.get("label", "")) for p in ov_places)
ov_latin_names = set(latin_normalize(p.get("label", "")) for p in ov_places)

extra_from_scraped = 0
# Collect grid-based places by cell for sub-grid distribution
# Start with deferred OmnesViae places that had no lat/lng
grid_cells = {}  # (seg_idx, col, row) -> list of entry dicts
for cell_key, entries in ov_grid_deferred.items():
    grid_cells[cell_key] = list(entries)  # copy

# Add scraped-only places
for sp in scraped:
    norm = normalize_name(sp["latin"])
    lnorm = latin_normalize(sp["latin"])
    if norm in ov_names or lnorm in ov_latin_names:
        continue
    segment = sp.get("segment", 0)
    col = sp.get("col", 0)
    row = sp.get("row", "")
    if not segment:
        continue

    seg_idx = segment - 2
    cell_key = (seg_idx, col, row)
    if cell_key not in grid_cells:
        grid_cells[cell_key] = []
    grid_cells[cell_key].append({
        "latin": sp["latin"],
        "modern": sp.get("modern", ""),
        "type": sp.get("type", "road_station"),
        "region": sp.get("region", ""),
        "country": sp.get("country", ""),
        "notes": sp.get("notes", ""),
    })

# Now distribute places within each grid cell using sub-grid layout
grid_placed = 0
for cell_key, places_in_cell in grid_cells.items():
    seg_idx, col, row = cell_key
    row_y_center = {"a": IMG_H * 0.17, "b": IMG_H * 0.5, "c": IMG_H * 0.83}
    cx = seg_idx * SEG_W + (col - 0.5) / 5 * SEG_W
    cy = row_y_center.get(row, IMG_H / 2)

    n = len(places_in_cell)
    # Cell size: each grid cell is SEG_W/5 wide x IMG_H*0.33 tall
    cell_w = SEG_W / 5 * 0.85  # use 85% of cell width
    cell_h = IMG_H * 0.25  # use ~25% of image height per row

    if n == 1:
        positions = [(cx, cy)]
    else:
        # Arrange in a sub-grid within the cell
        ncols = max(1, int(math.ceil(math.sqrt(n * cell_w / cell_h))))
        nrows = max(1, int(math.ceil(n / ncols)))
        positions = []
        for i in range(n):
            r = i // ncols
            c = i % ncols
            px = cx - cell_w / 2 + (c + 0.5) / ncols * cell_w
            py = cy - cell_h / 2 + (r + 0.5) / nrows * cell_h
            px = max(0, min(IMG_W - 1, px))
            py = max(0, min(IMG_H - 1, py))
            positions.append((px, py))

    for i, entry_data in enumerate(places_in_cell):
        px, py = positions[i]
        entry = {
            "id": len(output_places) + 1,
            "latin": entry_data["latin"],
            "modern": entry_data.get("modern", ""),
            "type": entry_data.get("type", "road_station"),
            "px": round(px, 1),
            "py": round(py, 1),
            "region": entry_data.get("region", ""),
            "country": entry_data.get("country", ""),
            "notes": entry_data.get("notes", ""),
        }
        output_places.append(entry)
        grid_placed += 1

extra_from_scraped = grid_placed - sum(len(v) for v in ov_grid_deferred.values())


print(f"\nMatching results:")
print(f"  OmnesViae matched with scraped: {matched}")
print(f"  OmnesViae unmatched: {unmatched}")
print(f"  No lat/lng from OmnesViae: {no_coords}")
print(f"  OV deferred to grid: {sum(len(v) for v in ov_grid_deferred.values())}")
print(f"  Extra from scraped only: {extra_from_scraped}")
print(f"  Grid cells distributed: {len(grid_cells)}")
print(f"  Grid places total: {grid_placed}")
print(f"  Total output places: {len(output_places)}")

# Type distribution
types = Counter(p["type"] for p in output_places)
print(f"\nType distribution: {dict(types.most_common())}")

# Pixel position stats
pxs = [p["px"] for p in output_places]
pys = [p["py"] for p in output_places]
print(f"Pixel X range: {min(pxs):.0f} to {max(pxs):.0f}")
print(f"Pixel Y range: {min(pys):.0f} to {max(pys):.0f}")

# Check for clustering
from collections import Counter as C2
# Round to 100px cells
cells = C2((round(p["px"]/200)*200, round(p["py"]/200)*200) for p in output_places)
print(f"\nPosition cells (200px): {len(cells)} unique cells")
print(f"Most crowded cells: {cells.most_common(5)}")

# Save
with open("public/data/places.json", "w", encoding="utf-8") as f:
    json.dump(output_places, f, ensure_ascii=False)
print(f"\nSaved {len(output_places)} places to public/data/places.json")
