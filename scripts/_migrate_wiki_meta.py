"""
Add wiki_confidence and wiki_manual fields to all records that have wiki_url
but are missing these metadata fields.

wiki_confidence: int 1-3 (match quality), or None = unknown/pre-existing
wiki_manual:     bool — True if URL was hand-curated, False if automated

Records already having both fields are left untouched.
"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))

patched = 0
for r in db['records']:
    if not r.get('wiki_url'):
        continue
    changed = False
    if 'wiki_confidence' not in r:
        r['wiki_confidence'] = None   # pre-existing entry, confidence unknown
        changed = True
    if 'wiki_manual' not in r:
        r['wiki_manual'] = False
        changed = True
    if changed:
        patched += 1

print(f'Patched {patched} records (added missing wiki_confidence/wiki_manual)')
tmp = DB_PATH.with_suffix('.tmp')
tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
tmp.replace(DB_PATH)
print(f'Saved -> {DB_PATH.name}')
