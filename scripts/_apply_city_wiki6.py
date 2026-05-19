import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, lat, lng, country, conf, manual)
ENTRIES = [
    # ── Conf 3 ────────────────────────────────────────────────────────────────
    (1241,   'https://en.wikipedia.org/wiki/Tarquinia',                    42.254, 11.758, 'IT', 3, True),  # Tarqvinis
    (1614,   'https://en.wikipedia.org/wiki/Nesactium',                    44.924, 13.966, 'HR', 3, True),  # [Nesatio] = Nesactium (Istria)
    (1794,   'https://en.wikipedia.org/wiki/Thenae',                       34.963, 10.924, 'TN', 3, True),  # [Thenas] = Thenae (Tunisia)
    (2763,   'https://en.wikipedia.org/wiki/Boukephala_and_Nikaia',        32.930, 73.720, 'PK', 3, True),  # Alexandria Bvcefalos (horse of Alexander)
    (2109,   'https://en.wikipedia.org/wiki/Libyssa',                      40.800, 29.430, 'TR', 3, True),  # Livissa = Libyssa (Hannibal died here)
    (2779,   'https://en.wikipedia.org/wiki/Persepolis',                   29.935, 52.891, 'IR', 3, True),  # Persepoliscon = Persepolis
    (2353,   'https://en.wikipedia.org/wiki/Side,_Turkey',                 36.766, 31.388, 'TR', 3, True),  # Sidi = Side (Pamphylia)
    (2428,   'https://en.wikipedia.org/wiki/Tremetousia',                  35.093, 33.611, 'CY', 3, True),  # Thremitvs = Tremithus (Cyprus)
    (1181,   'https://en.wikipedia.org/wiki/Fermo',                        43.160, 13.716, 'IT', 3, True),  # Castello Firmani = Firmum Picenum
    (1256,   'https://en.wikipedia.org/wiki/Castrum_Novum',                42.038, 11.831, 'IT', 3, True),  # Castro Novo = Castrum Novum (Etruria)
    (2438,   'https://en.wikipedia.org/wiki/Al-Bab',                       36.371, 37.518, 'SY', 3, True),  # Bathna = Batnae / Al-Bab (Syria)
    (2060,   'https://en.wikipedia.org/wiki/Cisamus',                      35.490, 23.650, 'GR', 3, True),  # Cisamos = Cisamus (Crete, western)

    # ── Conf 2 ────────────────────────────────────────────────────────────────
    (2246,   'https://en.wikipedia.org/wiki/Nicopolis_(Armenia)',           40.140, 38.140, 'TR', 2, True),  # Nicopoli = Nicopolis Pontica (founded by Pompey)
    ( 346,   'https://en.wikipedia.org/wiki/Balagrae',                     32.770, 21.740, 'LY', 2, True),  # Balacris = Balagrae (Cyrenaica, temple of Asclepius); fix LAR→LY
    (1322,   'https://en.wikipedia.org/wiki/Anagni',                       41.740, 13.160, 'IT', 2, True),  # Conpito Anagnino = road junction near Anagni
    (2687,   'https://en.wikipedia.org/wiki/Sarpol-e_Zahab',               34.521, 45.576, 'IR', 2, True),  # Albania = Hulwan / Sar-pol-e Zahab
    ( 464,   'https://en.wikipedia.org/wiki/Legio_(Roman_city)',            32.572, 35.171, 'IL', 2, True),  # Caporcotani = Legio/Maximianopolis (Lejjun)
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
