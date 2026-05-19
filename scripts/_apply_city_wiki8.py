import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, lat, lng, country, conf, manual)
ENTRIES = [
    # ── Conf 3 ────────────────────────────────────────────────────────────────
    (2201,   'https://en.wikipedia.org/wiki/Apamea_Myrlea',          40.380, 28.880, 'TR', 3, True),   # Lamasco = Apamea Myrlea (Mudanya/Marmara coast)
    (2740,   'https://en.wikipedia.org/wiki/Zaranj',                  31.110, 61.890, 'AF', 3, True),   # Aris = Zarang/Zaranj (Sistan); fix AFG→AF

    # ── Conf 2 ────────────────────────────────────────────────────────────────
    ( 536,   'https://en.wikipedia.org/wiki/Sitomagus',               52.210,  1.490, 'GB', 2, True),   # Sinomagi = Sitomagus (Roman Britain, Suffolk)
    (2475,   'https://en.wikipedia.org/wiki/Takht-e_Soleyman',        36.600, 47.240, 'IR', 2, True),   # Lazo = Takht-e Soleyman (Taht-i-Suleiman, NW Iran)
    (3001941,'https://en.wikipedia.org/wiki/Merv',                    37.664, 62.186, 'TM', 2, True),   # Antiohia tharmata = Merv/Alexandria Margiana; fix IN→TM
    (3000995,'https://en.wikipedia.org/wiki/Megalopolis,_Greece',     37.400, 22.000, 'GR', 2, True),   # Melena (Arcadia) = near Megalopolis
    (2586,   'https://en.wikipedia.org/wiki/Apamea_(Euphrates)',      36.430, 38.280, 'SY', 2, True),   # Apammari = Apamea on Euphrates; fix SYR→SY
    (2728,   'https://en.wikipedia.org/wiki/Hecatompylos',            36.230, 54.430, 'IR', 2, True),   # Nagae = Hecatompylos (Parthian capital, Semnan area)
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
    if r.get('lat') is None and lat is not None:
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
