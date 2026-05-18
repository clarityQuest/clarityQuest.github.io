import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, lat, lng, country)
# lat/lng only written if record has no coordinates yet
ENTRIES = [
    # ── Auto-matched (vetted, reject: 3060 Poland, 2956 Russia) ──────────
    (2998,  'https://en.wikipedia.org/wiki/Salento',              40.3333, 18.0000, 'IT'),
    (3179,  'https://en.wikipedia.org/wiki/Cappadocia',           38.6183, 34.8672, 'TR'),
    (3198,  'https://en.wikipedia.org/wiki/Cilicia',              36.9850, 35.1200, 'TR'),
    (3279,  'https://en.wikipedia.org/wiki/Malabar_Coast',        12.0167, 75.2833, 'IN'),
    (2843,  'https://en.wikipedia.org/wiki/Nijmegen',             51.8475,  5.8625, 'NL'),
    (3282,  'https://en.wikipedia.org/wiki/Malabar_Coast',        12.0167, 75.2833, 'IN'),
    (2906,  'https://en.wikipedia.org/wiki/Black_Forest',         48.0000,  8.0000, 'DE'),
    (2883,  'https://en.wikipedia.org/wiki/Vosges_(mountains)',   48.0000,  7.0000, 'FR'),

    # ── Manual additions ──────────────────────────────────────────────────
    (3060,  'https://en.wikipedia.org/wiki/Arcadia',              37.5000, 22.3333, 'GR'),
    (3158,  'https://en.wikipedia.org/wiki/Asia_(Roman_province)', 38.4607, 27.2000, 'TR'),
    (3010,  'https://en.wikipedia.org/wiki/Bruttium',             38.9600, 16.3000, 'IT'),
    (3278,  'https://en.wikipedia.org/wiki/Kashmir',              33.7782, 76.5762, None),
    (3160,  'https://en.wikipedia.org/wiki/Egypt',                26.0000, 30.0000, 'EG'),
    (2962,  'https://en.wikipedia.org/wiki/Etruria',              43.0000, 11.5000, 'IT'),
    (3156,  'https://en.wikipedia.org/wiki/Galatia',              39.5000, 32.5000, 'TR'),
    (3258,  'https://en.wikipedia.org/wiki/India',                20.5937, 78.9629, 'IN'),
    (2956,  'https://en.wikipedia.org/wiki/Istria',               45.3333, 14.0000, 'HR'),
    (2910,  'https://en.wikipedia.org/wiki/Italy',                41.8719, 12.5674, 'IT'),
    (3213,  'https://en.wikipedia.org/wiki/Mesopotamia',          33.0000, 44.0000, 'IQ'),
    (2849,  'https://en.wikipedia.org/wiki/Gallia_Aquitania',     44.5000,  1.0000, 'FR'),
    (2980,  'https://en.wikipedia.org/wiki/Pannonia_Inferior',    45.8000, 18.0000, 'HU'),
    (2973,  'https://en.wikipedia.org/wiki/Picenum',              43.3000, 13.7000, 'IT'),
    (3255,  'https://en.wikipedia.org/wiki/Drangiana',            31.0000, 64.0000, 'AF'),
]

saved = 0
for data_id, wiki_url, lat, lng, country in ENTRIES:
    r = recs.get(data_id)
    if r is None:
        print(f'  MISSING {data_id}')
        continue
    if r.get('wiki_url'):
        print(f'  SKIP (already has wiki_url) {data_id}')
        continue
    r['wiki_url'] = wiki_url
    if r.get('lat') is None and lat is not None:
        r['lat'] = lat
        r['lng'] = lng
    if country and not r.get('country'):
        r['country'] = country
    saved += 1
    print(f'  OK  {data_id}  {(r.get("latin_std") or r.get("latin",""))[:35]}')

print(f'\nApplied {saved} wiki_url entries')
tmp = DB_PATH.with_suffix('.tmp')
tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
tmp.replace(DB_PATH)
print(f'Saved -> {DB_PATH.name}')
