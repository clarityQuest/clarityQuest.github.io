"""
Build places.json from OmnesViae data:
1. Use lat/lng → pixel mapping via IDW interpolation for 2,574 coordinated places
2. Use route-graph interpolation for ~749 uncoordinated places
3. Merge with existing places.json for modern names, region, country, notes

The Tabula Peutingeriana (Miller 1887) is 46,380 × 2,953 pixels.
It's a heavily distorted strip map — simple linear mapping won't work.
We use known landmark control points for piecewise IDW interpolation.
"""

import json
import math
import re
from collections import Counter, deque

# Load data
with open("scripts/omnesviae_sample.json", encoding="utf-8") as f:
    ov_data = json.load(f)

# Load existing places.json for supplementary data (modern names, region, etc.)
with open("public/data/places.json", encoding="utf-8") as f:
    existing = json.load(f)

ov_places = [n for n in ov_data["@graph"] if n.get("@type") == "Place"]
ov_actions = [n for n in ov_data["@graph"] if n.get("@type") == "TravelAction"]
print(f"OmnesViae places: {len(ov_places)}")
print(f"OmnesViae routes: {len(ov_actions)}")
print(f"Existing places: {len(existing)}")

# ============================================================
# CONTROL POINTS
# ============================================================

IMG_W = 46380
IMG_H = 2953
SEG_W = IMG_W / 11  # ~4216 px per segment

# (lat, lng) -> (px_x, px_y)
CONTROL_POINTS = [
    # Segment II (idx 0): Britannia, Gallia, Mauretania
    (51.51, -0.09,   SEG_W * 0.5,     IMG_H * 0.18),   # Londinium
    (51.89,  0.90,   SEG_W * 0.65,    IMG_H * 0.15),   # Camulodunum
    (48.86,  2.35,   SEG_W * 0.7,     IMG_H * 0.40),   # Lutetia
    (36.60,  2.26,   SEG_W * 0.7,     IMG_H * 0.85),   # Caesarea Mauretaniae

    # Segment III (idx 1): Germania, Gallia, Liguria
    (50.94,  6.96,   SEG_W * 1.3,     IMG_H * 0.15),   # Colonia Agrippina
    (45.76,  4.83,   SEG_W * 1.2,     IMG_H * 0.40),   # Lugdunum
    (44.41,  8.93,   SEG_W * 1.6,     IMG_H * 0.50),   # Genua
    (37.60, -0.99,   SEG_W * 0.3,     IMG_H * 0.80),   # Carthago Nova

    # Segment IV (idx 2): Raetia, Italia
    (48.37, 10.89,   SEG_W * 2.3,     IMG_H * 0.15),   # Augusta Vindelicorum
    (45.46,  9.19,   SEG_W * 2.2,     IMG_H * 0.38),   # Mediolanum
    (41.90, 12.50,   SEG_W * 2.85,    IMG_H * 0.48),   # Roma
    (43.77, 11.25,   SEG_W * 2.6,     IMG_H * 0.42),   # Florentia

    # Segment V (idx 3): Noricum, Italia
    (48.21, 16.37,   SEG_W * 3.3,     IMG_H * 0.12),   # Vindobona
    (45.77, 13.37,   SEG_W * 3.0,     IMG_H * 0.30),   # Aquileia
    (40.85, 14.27,   SEG_W * 3.3,     IMG_H * 0.55),   # Neapolis
    (36.85, 10.17,   SEG_W * 3.0,     IMG_H * 0.82),   # Carthago

    # Segment VI (idx 4): Dalmatia, Italia
    (44.97, 19.61,   SEG_W * 4.3,     IMG_H * 0.18),   # Sirmium
    (40.64, 17.94,   SEG_W * 4.2,     IMG_H * 0.50),   # Brundisium
    (32.64, 14.29,   SEG_W * 4.0,     IMG_H * 0.88),   # Leptis Magna

    # Segment VII (idx 5): Macedonia, Achaia, Africa
    (40.64, 22.94,   SEG_W * 5.3,     IMG_H * 0.20),   # Thessalonica
    (37.97, 23.73,   SEG_W * 5.5,     IMG_H * 0.35),   # Athenae
    (37.91, 22.88,   SEG_W * 5.3,     IMG_H * 0.38),   # Corinthus
    (32.82, 21.86,   SEG_W * 5.2,     IMG_H * 0.82),   # Cyrene

    # Segment VIII (idx 6): Thracia, Dacia
    (41.01, 28.98,   SEG_W * 6.7,     IMG_H * 0.18),   # Constantinopolis
    (42.02, 35.15,   SEG_W * 6.9,     IMG_H * 0.12),   # Sinope
    (40.77, 29.94,   SEG_W * 6.8,     IMG_H * 0.22),   # Nicomedia
    (37.94, 27.35,   SEG_W * 6.4,     IMG_H * 0.38),   # Ephesus

    # Segment IX (idx 7): Asia, Aegyptus
    (39.93, 32.87,   SEG_W * 7.3,     IMG_H * 0.18),   # Ancyra
    (37.87, 32.48,   SEG_W * 7.3,     IMG_H * 0.35),   # Iconium
    (31.20, 29.92,   SEG_W * 7.1,     IMG_H * 0.82),   # Alexandria
    (36.92, 34.89,   SEG_W * 7.7,     IMG_H * 0.38),   # Tarsus

    # Segment X (idx 8): Cappadocia, Syria, Palaestina
    (36.20, 36.16,   SEG_W * 8.2,     IMG_H * 0.30),   # Antiochia
    (33.51, 36.29,   SEG_W * 8.3,     IMG_H * 0.50),   # Damascus
    (31.77, 35.23,   SEG_W * 8.2,     IMG_H * 0.60),   # Jerusalem
    (32.50, 34.89,   SEG_W * 8.1,     IMG_H * 0.55),   # Caesarea Palaestinae

    # Segment XI (idx 9): Mesopotamia, Arabia, Persia
    (37.16, 38.79,   SEG_W * 9.3,     IMG_H * 0.18),   # Edessa
    (34.55, 38.27,   SEG_W * 9.2,     IMG_H * 0.40),   # Palmyra
    (33.09, 44.58,   SEG_W * 9.7,     IMG_H * 0.50),   # Ctesiphon
    (30.33, 35.44,   SEG_W * 9.0,     IMG_H * 0.75),   # Petra

    # Segment XII (idx 10): Persia, India
    (29.93, 52.89,   SEG_W * 10.3,    IMG_H * 0.50),   # Persepolis
    (24.85, 67.86,   SEG_W * 10.7,    IMG_H * 0.60),   # Indus mouth

    # Boundary anchors
    (55.00, -5.00,   0,               0),
    (30.00, -9.00,   0,               IMG_H),
    (46.00, 35.00,   SEG_W * 7.0,     0),
    (10.00, 86.00,   IMG_W,           IMG_H),
    (40.00, 65.00,   SEG_W * 10.5,    0),
]


# ============================================================
# IDW Interpolation
# ============================================================

def geo_dist(lat1, lng1, lat2, lng2):
    dlat = lat1 - lat2
    dlng = (lng1 - lng2) * math.cos(math.radians((lat1 + lat2) / 2))
    return math.sqrt(dlat * dlat + dlng * dlng)


def idw_interpolate(lat, lng, control_points, k=8, power=2.0):
    dists = []
    for clat, clng, cpx, cpy in control_points:
        d = geo_dist(lat, lng, clat, clng)
        if d < 0.001:
            return cpx, cpy
        dists.append((d, cpx, cpy))
    dists.sort()
    nearest = dists[:k]
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
# Name matching
# ============================================================

def normalize_name(s):
    s = s.lower().strip()
    s = s.replace("\u0304", "").replace("\u0305", "")
    s = re.sub(r"[^a-z ]", "", s)
    return s.strip()


def latin_normalize(s):
    s = normalize_name(s)
    s = s.replace("v", "u")
    s = s.replace("ae", "e")
    s = s.replace("oe", "e")
    s = s.replace("ph", "f")
    s = s.replace("y", "i")
    s = s.replace("th", "t")
    s = re.sub(r"(.)\1", r"\1", s)  # double → single
    s = re.sub(r"(um|us|is|on|os|as)$", "", s)
    s = s.replace(" ", "")
    return s


# Build lookup from existing places.json for supplementary data
existing_by_name = {}
existing_by_latin = {}
for p in existing:
    key = normalize_name(p.get("latin", ""))
    if key and key not in existing_by_name:
        existing_by_name[key] = p
    lkey = latin_normalize(p.get("latin", ""))
    if lkey and lkey not in existing_by_latin:
        existing_by_latin[lkey] = p


# ============================================================
# Route graph for interpolating uncoordinated places
# ============================================================

place_by_id = {}
for p in ov_places:
    place_by_id[p["@id"]] = p

# Build adjacency list with distances
adj = {}
for a in ov_actions:
    frm_list = a.get("from", [])
    to_list = a.get("to", [])
    dist = a.get("dist", 0) or 0
    frm = frm_list[0]["@id"] if frm_list else None
    to = to_list[0]["@id"] if to_list else None
    if frm and to:
        adj.setdefault(frm, []).append((to, dist))
        adj.setdefault(to, []).append((frm, dist))

# First pass: compute pixel positions for all coordinated places
pixel_positions = {}  # place_id -> (px, py)
for p in ov_places:
    pid = p["@id"]
    lat = p.get("lat")
    lng = p.get("lng")
    if lat is not None and lng is not None:
        px, py = idw_interpolate(lat, lng, CONTROL_POINTS)
        px = max(0, min(IMG_W - 1, px))
        py = max(0, min(IMG_H - 1, py))
        pixel_positions[pid] = (px, py)

print(f"IDW-positioned places: {len(pixel_positions)}")

# Remember which places were IDW-positioned (accurate) vs route-interpolated
idw_positioned_ids = set(pixel_positions.keys())

# Route interpolation: position uncoordinated places by linear interpolation
# along route chains between positioned endpoints.
#
# Strategy: For each unpositioned place, find chains of consecutive unpositioned
# places between two positioned endpoints, then interpolate linearly.

def find_chain(start_id, start_nbr, adj, positioned):
    """Follow the route from start_id through unpositioned places until
    hitting a positioned place or dead end. Returns (chain, end_id) where
    chain is list of (place_id, cumulative_dist) and end_id is the positioned
    endpoint (or None)."""
    chain = []
    cum_dist = 0
    current = start_id
    prev = start_nbr  # where we came from
    while True:
        # Find neighbors other than where we came from
        neighbors = adj.get(current, [])
        next_hops = [(n, d) for n, d in neighbors if n != prev]
        if not next_hops:
            # Dead end
            return chain, None
        # Take first unvisited neighbor (route networks are mostly linear)
        found_next = False
        for nbr_id, dist in next_hops:
            cum_dist += max(dist, 1)
            if nbr_id in positioned:
                # Reached a positioned endpoint
                return chain, (nbr_id, cum_dist)
            # Continue through this unpositioned place
            chain.append((nbr_id, cum_dist))
            prev = current
            current = nbr_id
            found_next = True
            break
        if not found_next:
            return chain, None

positioned = dict(pixel_positions)  # copy
route_positioned = 0
MAX_ROUNDS = 10

# Process all unpositioned places that have at least one positioned neighbor
for _round in range(MAX_ROUNDS):
    newly_positioned = 0
    for p in ov_places:
        pid = p["@id"]
        if pid in positioned:
            continue
        neighbors = adj.get(pid, [])

        # Find positioned neighbors
        pos_nbrs = [(n, d) for n, d in neighbors if n in positioned]
        if not pos_nbrs:
            continue

        if len(pos_nbrs) >= 2:
            # Place is between two positioned places - interpolate
            n1_id, d1 = pos_nbrs[0]
            n2_id, d2 = pos_nbrs[1]
            p1x, p1y = positioned[n1_id]
            p2x, p2y = positioned[n2_id]
            total = max(d1 + d2, 1)
            t = d1 / total
            px = p1x + t * (p2x - p1x)
            py = p1y + t * (p2y - p1y)
        elif len(pos_nbrs) == 1:
            # Only one positioned neighbor - try to find a chain to another
            n1_id, d1 = pos_nbrs[0]
            p1x, p1y = positioned[n1_id]
            # Look ahead through unpositioned neighbors
            unpos_nbrs = [(n, d) for n, d in neighbors if n not in positioned]
            found_chain = False
            for un_id, un_d in unpos_nbrs:
                chain, end = find_chain(un_id, pid, adj, positioned)
                if end:
                    end_id, end_dist = end
                    p2x, p2y = positioned[end_id]
                    total = d1 + un_d + end_dist
                    t = d1 / max(total, 1)
                    px = p1x + t * (p2x - p1x)
                    py = p1y + t * (p2y - p1y)
                    found_chain = True
                    break
            if not found_chain:
                # Place at small offset from neighbor
                px, py = p1x, p1y
                h = hash(pid) % 1000
                px += ((h % 31) - 15) * 12
                py += ((h // 31 % 31) - 15) * 6
        else:
            continue

        px = max(0, min(IMG_W - 1, px))
        py = max(0, min(IMG_H - 1, py))
        positioned[pid] = (px, py)
        newly_positioned += 1
        route_positioned += 1

    if newly_positioned == 0:
        break
    print(f"  Round {_round + 1}: positioned {newly_positioned} places via routes")

# Update pixel_positions with route-interpolated ones
pixel_positions.update(positioned)

unpositioned = sum(1 for p in ov_places if p["@id"] not in pixel_positions)
print(f"Route-interpolated total: {len(pixel_positions)}")
print(f"Still unpositioned: {unpositioned}")

# ============================================================
# Post-processing: spread clusters
# Places that land within MIN_DIST of each other get displaced
# ============================================================

MIN_DIST = 80  # pixels - minimum distance between places
SPREAD_PASSES = 5

# Only route-interpolated places are moveable; IDW-positioned ones stay fixed
# idw_positioned_ids was captured before route interpolation

for pass_num in range(SPREAD_PASSES):
    grid_size = MIN_DIST * 2
    spatial_grid = {}
    all_ids = list(positioned.keys())
    for pid in all_ids:
        px, py = positioned[pid]
        gx, gy = int(px // grid_size), int(py // grid_size)
        spatial_grid.setdefault((gx, gy), []).append(pid)

    displaced = 0
    for pid in all_ids:
        if pid in idw_positioned_ids:
            continue  # don't move IDW-positioned places
        px, py = positioned[pid]
        gx, gy = int(px // grid_size), int(py // grid_size)

        too_close = []
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                for nbr_id in spatial_grid.get((gx + dx, gy + dy), []):
                    if nbr_id == pid:
                        continue
                    nx, ny = positioned[nbr_id]
                    dist = math.sqrt((px - nx) ** 2 + (py - ny) ** 2)
                    if dist < MIN_DIST:
                        too_close.append((nbr_id, nx, ny, dist))

        if not too_close:
            continue

        for nbr_id, nx, ny, dist in too_close:
            if dist < 1:
                h = hash(pid) % 360
                angle = math.radians(h)
                push = MIN_DIST * 0.6
            else:
                angle = math.atan2(py - ny, px - nx)
                push = (MIN_DIST - dist) * 0.3

            new_px = px + math.cos(angle) * push
            new_py = py + math.sin(angle) * push
            new_px = max(0, min(IMG_W - 1, new_px))
            new_py = max(0, min(IMG_H - 1, new_py))
            px, py = new_px, new_py

        positioned[pid] = (px, py)
        displaced += 1

    print(f"  Spread pass {pass_num + 1}: displaced {displaced} places")

# Final pixel_positions = IDW positions + spread route positions
pixel_positions = dict(positioned)


# ============================================================
# Symbol to type mapping
# ============================================================

def symbol_to_type(symbol):
    if not symbol:
        return "road_station"
    s = symbol.upper()
    if s.startswith("AA"):
        return "major_city"
    if s.startswith("AB") or s.startswith("AC"):
        return "city"
    if s.startswith("F"):
        return "major_city"
    if s in ("O", "Q"):
        return "port"
    return "road_station"


# ============================================================
# Build output
# ============================================================

output_places = []
matched_existing = 0

for p in ov_places:
    pid = p["@id"]
    label = p.get("label", "")
    modern = p.get("modern", "")
    symbol = p.get("symbol", "")
    lat = p.get("lat")
    lng = p.get("lng")

    if not label:
        continue

    if pid not in pixel_positions:
        continue  # can't position this place at all

    px, py = pixel_positions[pid]
    ptype = symbol_to_type(symbol)

    # Try to match with existing data for supplementary info
    norm = normalize_name(label)
    lnorm = latin_normalize(label)
    ex_match = existing_by_name.get(norm) or existing_by_latin.get(lnorm)

    region = ""
    country = ""
    notes = ""
    if ex_match:
        matched_existing += 1
        region = ex_match.get("region", "")
        country = ex_match.get("country", "")
        notes = ex_match.get("notes", "")
        if not modern and ex_match.get("modern"):
            modern = ex_match["modern"]
        # Use existing type if more specific
        ex_type = ex_match.get("type", "")
        if ex_type in ("river", "island", "mountain", "people", "region"):
            ptype = ex_type

    entry = {
        "id": len(output_places) + 1,
        "latin": label,
        "modern": modern,
        "type": ptype,
        "px": round(px, 1),
        "py": round(py, 1),
        "region": region,
        "country": country,
        "notes": notes,
    }
    if lat is not None:
        entry["lat"] = lat
        entry["lng"] = lng

    output_places.append(entry)


# ============================================================
# Stats
# ============================================================

print(f"\nResults:")
print(f"  OmnesViae matched with existing: {matched_existing}")
print(f"  Total output places: {len(output_places)}")

types = Counter(p["type"] for p in output_places)
print(f"\nType distribution: {dict(types.most_common())}")

pxs = [p["px"] for p in output_places]
pys = [p["py"] for p in output_places]
print(f"Pixel X range: {min(pxs):.0f} to {max(pxs):.0f}")
print(f"Pixel Y range: {min(pys):.0f} to {max(pys):.0f}")

# Clustering check
cells = Counter((round(p["px"]/200)*200, round(p["py"]/200)*200) for p in output_places)
print(f"\nPosition cells (200px): {len(cells)} unique cells")
print(f"Most crowded cells: {cells.most_common(5)}")
max_crowd = max(cells.values())
print(f"Max places per cell: {max_crowd}")

# Save
with open("public/data/places.json", "w", encoding="utf-8") as f:
    json.dump(output_places, f, ensure_ascii=False)
print(f"\nSaved {len(output_places)} places to public/data/places.json")
