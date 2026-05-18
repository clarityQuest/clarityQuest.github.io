import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, lat, lng, country, conf, manual)
ENTRIES = [
    # ── From dry-run candidates (with correct country) ───────────────────────
    (2211, 'https://en.wikipedia.org/wiki/Gargara',        39.5861, 26.5342, 'TR', 3, False),  # Gargara
    (1164, 'https://it.wikipedia.org/wiki/Porto_Recanati', 43.4299, 13.6649, 'IT', 2, False),  # Polentia = Porto Recanati
    (1986, 'https://de.wikipedia.org/wiki/Sestos',         40.2328, 26.4225, 'TR', 3, False),  # Sestos
    (2682, 'https://it.wikipedia.org/wiki/Kirkuk',         35.2800, 44.2400, 'IQ', 3, False),  # Thelser = Kirkuk

    # ── Manual (Latin name ≠ Wikipedia title) ────────────────────────────────
    (2166, 'https://en.wikipedia.org/wiki/Savatra',        37.9693, 33.1225, 'TR', 3, True),   # Sabatra
    (2195, 'https://en.wikipedia.org/wiki/Cyzicus',        40.3897, 27.8897, 'TR', 3, True),   # Cyzico
    (2155, 'https://en.wikipedia.org/wiki/Pessinus',       39.3333, 31.5167, 'TR', 3, True),   # Pesinvnte
    ( 199, 'https://en.wikipedia.org/wiki/Thysdrus',       35.3000, 10.7100, 'TN', 3, True),   # Thisdro
]

saved = 0
for data_id, wiki_url, lat, lng, country, conf, manual in ENTRIES:
    r = recs.get(data_id)
    if r is None:
        print(f'  MISSING {data_id}')
        continue
    if r.get('wiki_url'):
        print(f'  SKIP (already has wiki_url) {data_id}  {r.get("wiki_url","")[:60]}')
        continue
    r['wiki_url']        = wiki_url
    r['wiki_confidence'] = conf
    r['wiki_manual']     = manual
    if r.get('lat') is None and lat is not None:
        r['lat'] = lat
        r['lng'] = lng
    if country:
        r['country'] = country
    saved += 1
    print(f'  OK  {data_id}  {(r.get("latin_std") or r.get("latin",""))[:35]}')

print(f'\nApplied {saved} wiki_url entries')
tmp = DB_PATH.with_suffix('.tmp')
tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
tmp.replace(DB_PATH)
print(f'Saved -> {DB_PATH.name}')
