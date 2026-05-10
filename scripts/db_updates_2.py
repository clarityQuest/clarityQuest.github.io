#!/usr/bin/env python3
"""DB corrections batch 2."""

import json, sys, io, copy, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RDB  = os.path.join(BASE, "public", "data", "review_places_db.json")
PDB  = os.path.join(BASE, "public", "data", "places.json")

with open(RDB, 'r', encoding='utf-8') as f:
    rraw = json.load(f)
with open(PDB, 'r', encoding='utf-8') as f:
    places = json.load(f)

db = rraw['records']

changes_rdb = []
changes_pdb = []

# ── Helper: find record in review_places_db by data_id ──────────────────────
def find_r(data_id):
    # Returns the FIRST matching record with the given data_id AND match_status != 'ulm_only'
    # (to avoid hitting the auto-assigned ulm_only duplicate)
    primary = [p for p in db if p.get('data_id') == data_id and p.get('match_status') != 'ulm_only']
    return primary[0] if primary else next((p for p in db if p.get('data_id') == data_id), None)

def find_r_ulm(ulm_id):
    return next((p for p in db if p.get('ulm_id') == ulm_id), None)

# ── Helper: find record in places.json by latin (loose match) ───────────────
def find_p(latin_fragment):
    latin_fragment = latin_fragment.lower()
    return [p for p in places if latin_fragment in (p.get('latin') or '').lower()]

def set_type_r(data_id, new_type, note=""):
    rec = find_r(data_id)
    if not rec:
        print(f"  WARN: data_id {data_id} not found in review_places_db")
        return
    old = rec.get('type')
    if old == new_type:
        print(f"  SKIP data_id={data_id} already {new_type}")
        return
    rec['type'] = new_type
    changes_rdb.append(f"data_id={data_id} ({rec.get('latin')}) type {old!r} → {new_type!r} {note}")

def set_type_p(latin_fragment, new_type, note=""):
    recs = find_p(latin_fragment)
    if not recs:
        print(f"  WARN: '{latin_fragment}' not found in places.json")
        return
    for rec in recs:
        old = rec.get('type')
        if old != new_type:
            rec['type'] = new_type
            changes_pdb.append(f"places id={rec.get('id')} ({rec.get('latin')}) type {old!r} → {new_type!r} {note}")

# ════════════════════════════════════════════════════════════════════════════
print("=== 1. Individual type fixes ===")

# 1. data_id 211 → region
set_type_r(211, "region")
set_type_p("dia (Numidia)", "region")
set_type_p("Numidia", "region")

# 2. data_id 2948 → island
set_type_r(2948, "island")
set_type_p("Insulae Hercvlis", "island")
set_type_p("Insulae Herculis", "island")

# 3. data_id 1310 → lake
set_type_r(1310, "lake")
set_type_p("Ad aquas Albvlas", "lake")
set_type_p("Aquas Albulas", "lake")

# 4. data_id 242 → spa
set_type_r(242, "spa")
set_type_p("Ad Aquas", "spa", "(exact match Ad Aquas)")

# 5. data_id 226 → spa (A Silesua ad Aquas milia XIX)
set_type_r(226, "spa")
set_type_p("Silesua ad Aquas", "spa")

print()
print("=== 6. Insula/Insulae not-island → island ===")
insula_ids = [3016, 1846, 2943, 2950, 2931, 2946]
for did in insula_ids:
    set_type_r(did, "island")

# Also check any remaining insula latin_std entries that aren't island
for p in db:
    lat = (p.get('latin') or '').lower()
    if ('insula' in lat or 'insulae' in lat) and p.get('type') not in ('island', 'port', 'river'):
        old = p.get('type')
        p['type'] = 'island'
        changes_rdb.append(f"data_id={p.get('data_id')} ({p.get('latin')}) type {old!r} → 'island' [bulk insula]")

print()
print("=== 7. A Doppelturm not-city → city ===")
doppelturm_ids = [2060, 2150, 3544, 768, 2341, 2364, 1618]
for did in doppelturm_ids:
    set_type_r(did, "city")

# Bulk: any remaining doppelturm not-city
for p in db:
    vig = (p.get('vignette') or '').lower()
    if 'doppelturm' in vig and p.get('type') != 'city':
        old = p.get('type')
        p['type'] = 'city'
        changes_rdb.append(f"data_id={p.get('data_id')} ({p.get('latin')}) type {old!r} → 'city' [bulk doppelturm]")

# Mirror doppelturm cities in places.json
doppelturm_latins = []
for did in doppelturm_ids:
    rec = find_r(did)
    if rec:
        doppelturm_latins.append(rec.get('latin') or rec.get('latin_std') or '')
for lat in doppelturm_latins:
    if lat:
        set_type_p(lat.lower(), "city", "[doppelturm]")

print()
print("=== 8. Fix data_id 1768 segment (ULM shift +1): 6 → 7 ===")
r = find_r(1768)
if r:
    old_seg = r.get('tabula_segment')
    r['tabula_segment'] = 7
    r['tabula_location'] = "Seg 7 a4"
    changes_rdb.append(f"data_id=1768 ({r.get('latin')}) tabula_segment {old_seg} → 7, location → 'Seg 7 a4'")

print()
print("=== 9. Enrich data_id 2456 (Ad mercvrivm, ulm_id 1577): segment ULM 10A3 → our 11A3 ===")
r = find_r_ulm(1577)
if not r:
    # Try by data_id + source
    r = next((p for p in db if p.get('data_id') == 2456 and p.get('source') == 'omnesviae'), None)
if r:
    r['tabula_segment'] = 11
    r['tabula_row'] = 'a'
    r['tabula_col'] = 3
    r['tabula_location'] = "Seg 11 a3"
    r['ulm_img_url'] = r.get('ulm_img_url') or "https://tp-online.ku.de/insetimages/TPPlace1577insetneu.png"
    changes_rdb.append(f"data_id={r.get('data_id')} ({r.get('latin')}) segment → 11a3")
else:
    print("  WARN: Ad mercvrivm / ulm_id 1577 not found")

print()
print("=== 10. Add ULM 923 (in candabia) ===")
existing_923 = next((p for p in db if p.get('ulm_id') == 923), None)
if existing_923:
    print(f"  SKIP: ulm_id 923 already in DB as data_id={existing_923.get('data_id')}")
else:
    max_did = max((p.get('data_id') or 0) for p in db if isinstance(p.get('data_id'), int) and p.get('data_id') < 2000000)
    new_did = max_did + 1
    new_rec = {
        "record_id": f"TP:ULM:923",
        "source": "tabula",
        "data_id": new_did,
        "latin": "in candabia",
        "latin_std": "In Candabia",
        "modern_preferred": "Qukës?",
        "type": "road_station",
        "symbol": "",
        "lat": None,
        "lng": None,
        "province": "MAC",
        "country": "AL",
        "region": "MAC",
        "tabula_segment": 7,
        "tabula_row": "b",
        "tabula_col": 4,
        "tabula_location": "Seg 7 b4",
        "ulm_id": 923,
        "ulm_img_url": "https://tp-online.ku.de/insetimages/TPPlace923insetneu.png",
        "match_status": "manual_add",
        "miller_px": None,
        "miller_py": None,
    }
    db.append(new_rec)
    changes_rdb.append(f"ADDED data_id={new_did} ULM:923 'In Candabia' seg 7b4")

print()
print("=== 9 (item). City no-symbol no-vignette → road_station ===")
nosym_ids = [978, 2027, 2224, 266]
for did in nosym_ids:
    r = find_r(did)
    if r:
        old = r.get('type')
        vig = r.get('vignette') or ''
        sym = r.get('symbol') or ''
        if old == 'city' and not vig and not sym:
            r['type'] = 'road_station'
            changes_rdb.append(f"data_id={did} ({r.get('latin')}) city→road_station [no symbol, no vignette]")
            set_type_p((r.get('latin') or '').lower(), 'road_station', "[no-sym city]")

# ════════════════════════════════════════════════════════════════════════════
print()
print("=== Summary ===")
print(f"review_places_db changes: {len(changes_rdb)}")
for c in changes_rdb:
    print(f"  {c}")
print()
print(f"places.json changes: {len(changes_pdb)}")
for c in changes_pdb:
    print(f"  {c}")

# ── Write back ──────────────────────────────────────────────────────────────
rraw['records'] = db
tmp_r = RDB + ".tmp"
with open(tmp_r, 'w', encoding='utf-8') as f:
    json.dump(rraw, f, ensure_ascii=False, indent=2)
os.replace(tmp_r, RDB)
print(f"\nWrote {RDB}")

tmp_p = PDB + ".tmp"
with open(tmp_p, 'w', encoding='utf-8') as f:
    json.dump(places, f, ensure_ascii=False, indent=2)
os.replace(tmp_p, PDB)
print(f"Wrote {PDB}")
