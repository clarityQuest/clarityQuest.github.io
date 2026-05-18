import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, lat, lng, country_override)
# lat/lng only applied if record has no coordinates yet.
# country only applied if missing.

ENTRIES = [
    # ── SPAs — vetted auto-matches ────────────────────────────────────────
    (179,    'https://en.wikipedia.org/wiki/Youks-les-Bains',          35.4500, 7.9500,   'DZ'),
    (226,    'https://en.wikipedia.org/wiki/Al-Hamma,_Tiberias',       32.6861, 35.6642,  'IL'),
    (1741,   'https://en.wikipedia.org/wiki/C%C4%83lan',               45.7319, 23.0247,  'RO'),
    (833,    'https://en.wikipedia.org/wiki/Aix-en-Provence',          43.5263, 5.4454,   'FR'),
    (1207,   'https://de.wikipedia.org/wiki/Acquaviva',                43.9464, 12.4222,  'IT'),
    (1506,   'https://en.wikipedia.org/wiki/Sciacca',                  37.5092, 13.0889,  'IT'),
    (664,    'https://en.wikipedia.org/wiki/Bourbon-Lancy',            46.6203, 3.7742,   'FR'),
    (724,    'https://en.wikipedia.org/wiki/Vichy',                    46.1278, 3.4267,   'FR'),
    (2320,   'https://en.wikipedia.org/wiki/%C3%87iftehan',            37.5122, 34.7694,  'TR'),
    (767,    'https://en.wikipedia.org/wiki/Capvern',                  43.1000, 0.3200,   'FR'),  # bbox gives ES, override FR
    (2000866,'https://en.wikipedia.org/wiki/Greba%C5%A1tica',         43.6333, 15.9833,  'HR'),
    (3001369,'https://en.wikipedia.org/wiki/Al-Hamma,_Tiberias',      32.6861, 35.6642,  'IL'),
    # ── SPAs — manual additions ───────────────────────────────────────────
    (44,     'https://en.wikipedia.org/wiki/Hammam_Meskoutine',        36.4667, 7.2667,   'DZ'),
    (2008,   'https://en.wikipedia.org/wiki/Burgas_Mineral_Baths',     42.5000, 27.4167,  'BG'),
    (2000833,'https://en.wikipedia.org/wiki/Antrodoco',                42.4167, 13.0833,  'IT'),
    (2000860,'https://en.wikipedia.org/wiki/Bosanska_Gradi%C5%A1ka',  45.1500, 17.2500,  'BA'),

    # ── LAKEs — vetted auto-matches ───────────────────────────────────────
    (2907,   'https://de.wikipedia.org/wiki/Bodensee',                 47.6333, 9.3667,   'DE'),
    (2884,   'https://fr.wikipedia.org/wiki/L%C3%A9man',              46.4500, 6.5500,   'CH'),
    (3150,   'https://de.wikipedia.org/wiki/%C4%B0znik_G%C3%B6l%C3%BC', 40.4336, 29.5186, 'TR'),  # bbox gives GR, override TR
    (2000827,'https://de.wikipedia.org/wiki/Bodensee',                 47.6333, 9.3667,   'DE'),
    (2000828,'https://en.wikipedia.org/wiki/Lake_Maggiore',            46.0981, 8.7147,   'IT'),
    (2000829,'https://en.wikipedia.org/wiki/Lake_of_Pusiano',         45.8000, 9.2700,   'IT'),
    # ── LAKEs — manual additions ──────────────────────────────────────────
    (1310,   'https://en.wikipedia.org/wiki/Acque_Albule',             41.9667, 12.7833,  'IT'),
    (3121,   'https://en.wikipedia.org/wiki/Sea_of_Azov',             46.0000, 36.5000,  'UA'),
    (3184,   'https://en.wikipedia.org/wiki/Dead_Sea',                 31.5000, 35.4833,  'IL'),
    (3047,   'https://en.wikipedia.org/wiki/Lake_Ohrid',               41.0000, 20.7167,  'AL'),
    (3194,   'https://en.wikipedia.org/wiki/Sea_of_Galilee',           32.8000, 35.5833,  'IL'),
    (3313,   'https://en.wikipedia.org/wiki/Lake_Viverone',            45.4167, 8.0500,   'IT'),
    (3547,   'https://en.wikipedia.org/wiki/Sivash',                   45.8333, 34.5000,  'UA'),
    (2000830,'https://en.wikipedia.org/wiki/Sea_of_Azov',             46.0000, 36.5000,  'UA'),
    (3550,   'https://en.wikipedia.org/wiki/Lake_Vico',                42.3167, 12.1667,  'IT'),
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
    print(f'  OK  {data_id}  {r.get("latin_std") or r.get("latin","")[:25]}')

print(f'\nApplied {saved} wiki_url entries')
tmp = DB_PATH.with_suffix('.tmp')
tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
tmp.replace(DB_PATH)
print(f'Saved -> {DB_PATH.name}')
