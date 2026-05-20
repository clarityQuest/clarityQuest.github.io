import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# Correct URLs that were applied with wrong/non-existent Wikipedia titles
# Agent research confirmed these are the actual existing pages
FIXES = [
    (3002624, 'https://en.wikipedia.org/wiki/Cinyps_(Libya)'),       # Wadi_Caam does not exist → Cinyps_(Libya) confirmed
    (3002653, 'https://en.wikipedia.org/wiki/Filyos_River'),          # Filyos_(river) does not exist → Filyos_River confirmed
    (3002610, 'https://en.wikipedia.org/wiki/Farfa'),                 # Farfa_(river) does not exist → Farfa (river info there)
    (3002609, 'https://en.wikipedia.org/wiki/Melito_(river)'),        # Halex does not exist → Melito_(river) mentions "possibly Latin: Halex"
    (3339,    'https://it.wikipedia.org/wiki/Lavino'),                # Lavino_(river) (EN) does not exist → Italian WP
    (3002367, 'https://en.wikipedia.org/wiki/Pamphylia'),             # Pamphylian_Sea does not exist → Pamphylia covers mare Pamphylium
]

fixed = 0
for data_id, new_url in FIXES:
    r = recs.get(data_id)
    if r is None:
        print(f'  MISSING {data_id}')
        continue
    old = r.get('wiki_url', '')
    r['wiki_url'] = new_url
    fixed += 1
    print(f'  FIX {data_id:<12}  {old} → {new_url}')

print(f'\nFixed {fixed} URLs')
tmp = DB_PATH.with_suffix('.tmp')
tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
tmp.replace(DB_PATH)
print(f'Saved -> {DB_PATH.name}')
