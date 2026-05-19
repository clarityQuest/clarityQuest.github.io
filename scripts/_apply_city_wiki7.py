import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, lat, lng, country, conf, manual)
ENTRIES = [
    # ── Conf 2 ─────────────────────────────────────────────────────────────
    (  341, 'https://en.wikipedia.org/wiki/Hadrianopolis_(Cyrenaica)', 32.350, 20.310, 'LY', 2, True),  # Hadrianopolis Cyrenaica; fix LAR→LY
    (  410, 'https://en.wikipedia.org/wiki/Berenice_Troglodytica',     23.950, 35.480, 'EG', 2, True),  # Pernicide portvm = Berenice Troglodytica (Red Sea)
    ( 2524, 'https://en.wikipedia.org/wiki/Zimara',                    39.410, 38.380, 'TR', 2, True),  # Zimara (Pontus Cappadocia)
    ( 1627, 'https://en.wikipedia.org/wiki/Burnum',                    43.980, 15.960, 'HR', 2, True),  # aBHaDRe Burnomilia XIII = road marker at Burnum
    (3001939,'https://en.wikipedia.org/wiki/Dharanikota',              16.580, 80.350, 'IN', 2, True),  # [Pitinna] Miller = Dharanikota (Andhra Pradesh)
    ( 2717, 'https://en.wikipedia.org/wiki/Charax_Spasinu',           30.430, 47.750, 'IQ', 2, True),  # Spasinucara = Charax Spasinu (Mesopot.) — fix coords & country
]

saved = 0
for data_id, wiki_url, lat, lng, country, conf, manual in ENTRIES:
    r = recs.get(data_id)
    if r is None:
        print(f'  MISSING {data_id}')
        continue
    if r.get('wiki_url'):
        print(f'  SKIP (already has wiki_url) {data_id}')
        continue
    r['wiki_url']        = wiki_url
    r['wiki_confidence'] = conf
    r['wiki_manual']     = manual
    # Override lat/lng for Spasinucara (existing coords wrong)
    if data_id == 2717 or r.get('lat') is None:
        r['lat'] = lat
        r['lng'] = lng
    if country:
        r['country'] = country
    saved += 1
    print(f'  OK  {data_id:<10}  {(r.get("latin_std") or r.get("latin",""))[:40]}')

print(f'\nApplied {saved} wiki_url entries')
tmp = DB_PATH.with_suffix('.tmp')
tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
tmp.replace(DB_PATH)
print(f'Saved -> {DB_PATH.name}')
