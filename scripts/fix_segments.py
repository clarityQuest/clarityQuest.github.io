#!/usr/bin/env python3
"""Fix tabula_segment: set to MAX(ulm_seg)+1 for all entries with ulm_planquadrat.
ULM uses 1-indexed segments where ULM-1 = Tabula II (the first surviving segment;
Tabula I is the lost western segment). Rule: tabula_segment = max_ulm_seg + 1.
Also fills in missing tabula_segment/row/col from ulm_planquadrat.
"""
import json, sys, io, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(BASE, "public", "data", "review_places_db.json")

with open(path, encoding='utf-8') as f:
    db = json.load(f)

def parse_ulm_pq(pq):
    """Return list of (seg, row, col) from ulm_planquadrat string."""
    cells = []
    for p in re.split(r'[/,]', pq):
        p = p.strip()
        m = re.match(r'^(\d+)([A-Ca-c])(\d+)$', p)
        if m:
            cells.append((int(m.group(1)), m.group(2).lower(), int(m.group(3))))
    return cells

added = corrected = skipped = 0

for r in db['records']:
    pq = r.get('ulm_planquadrat', '')
    if not pq:
        continue

    cells = parse_ulm_pq(pq)
    if not cells:
        skipped += 1
        continue

    # Use cell with max ULM segment, breaking ties by max column (rightmost within segment)
    max_cell = max(cells, key=lambda c: (c[0], c[2]))
    expected_seg = max_cell[0] + 1
    expected_row = max_cell[1]
    expected_col = max_cell[2]

    current_seg = r.get('tabula_segment')

    if current_seg is None:
        r['tabula_segment'] = expected_seg
        r['tabula_row'] = expected_row
        r['tabula_col'] = expected_col
        r['grid_row'] = expected_row
        r['grid_col'] = expected_col
        r['tabula_location'] = f'Seg {expected_seg} {expected_row}{expected_col}'
        print(f'  ADD  {r.get("latin","")[:38]:38}  -> Seg {expected_seg} {expected_row}{expected_col}')
        added += 1
    elif current_seg != expected_seg:
        print(f'  FIX  {r.get("latin","")[:38]:38}  seg {current_seg}->{expected_seg}  pq={pq[:28]}')
        r['tabula_segment'] = expected_seg
        r['tabula_row'] = expected_row
        r['tabula_col'] = expected_col
        r['grid_row'] = expected_row
        r['grid_col'] = expected_col
        r['tabula_location'] = f'Seg {expected_seg} {expected_row}{expected_col}'
        corrected += 1

print(f'\nAdded: {added}  Corrected: {corrected}  Skipped (no parse): {skipped}')

# Report remaining tabula_segment=1 (lost segment I — no miller markings possible)
seg1 = [r for r in db['records'] if r.get('tabula_segment') == 1]
if seg1:
    print(f'\nEntries at tabula_segment=1 (lost Segment I — no miller position possible):')
    for r in seg1:
        print(f'  data_id={r["data_id"]} latin={r.get("latin","")!r:.50}')

tmp = path + '.tmp'
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(db, f, ensure_ascii=False, indent=2)
os.replace(tmp, path)
print('\nSaved.')
