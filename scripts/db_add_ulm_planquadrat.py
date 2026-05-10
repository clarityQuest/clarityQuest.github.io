#!/usr/bin/env python3
"""Add ulm_planquadrat field to all records that have a ulm_id, and fix data_id 1125 type."""

import json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RDB  = os.path.join(BASE, "public", "data", "review_places_db.json")
UDB  = os.path.join(BASE, "public", "data", "ulm_db.json")

with open(RDB, 'r', encoding='utf-8') as f:
    rraw = json.load(f)
with open(UDB, 'r', encoding='utf-8') as f:
    ulm_entries = json.load(f)['entries']

db = rraw['records']

# Build ulm_id → planquadrat lookup
ulm_pq = {u['ulm_id']: u.get('planquadrat', '') for u in ulm_entries}

added = 0
already = 0

for p in db:
    uid = p.get('ulm_id')
    if not uid:
        continue
    pq = ulm_pq.get(uid, '')
    if not pq:
        continue
    if p.get('ulm_planquadrat') == pq:
        already += 1
        continue
    p['ulm_planquadrat'] = pq
    added += 1

print(f"ulm_planquadrat: {added} added, {already} already correct")

# Fix data_id 1125 → city
fixed = 0
for p in db:
    if p.get('data_id') == 1125:
        old = p.get('type')
        if old != 'city':
            p['type'] = 'city'
            print(f"data_id=1125 ({p.get('latin')}) type {old!r} → 'city'")
            fixed += 1
        else:
            print(f"data_id=1125 already city")

if fixed == 0 and not any(p.get('data_id') == 1125 for p in db):
    print("WARN: data_id 1125 not found")

# Write back
rraw['records'] = db
tmp = RDB + ".tmp"
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(rraw, f, ensure_ascii=False, indent=2)
os.replace(tmp, RDB)
print(f"Wrote {RDB}")
