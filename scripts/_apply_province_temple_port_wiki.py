import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, lat, lng, country)
ENTRIES = [
    # ── Roman Provinces — auto-matched ───────────────────────────────────
    (960002, 'https://en.wikipedia.org/wiki/Aegyptus_(Roman_province)',   28.7600, 30.8700, 'EG'),
    (960004, 'https://en.wikipedia.org/wiki/Alpes_Graiae_et_Poeninae',    46.0000,  7.0000, 'IT'),
    (960005, 'https://en.wikipedia.org/wiki/Arabia_Petraea',              30.0700, 35.3500, 'JO'),  # bbox→IL, override JO
    (960006, 'https://en.wikipedia.org/wiki/Armenia',                     40.1833, 44.5167, 'AM'),
    (960013, 'https://en.wikipedia.org/wiki/Cyprus',                      35.0000, 33.0000, 'CY'),
    (960014, 'https://en.wikipedia.org/wiki/Dacia',                       45.7000, 26.5000, 'RO'),
    (960022, 'https://en.wikipedia.org/wiki/Germania_Inferior',           50.5800,  5.2200, 'DE'),
    (960024, 'https://en.wikipedia.org/wiki/Hispania_Baetica',            37.5000, -6.0000, 'ES'),
    (960029, 'https://en.wikipedia.org/wiki/Lusitania',                   38.7689, -7.2181, 'PT'),
    (960043, 'https://en.wikipedia.org/wiki/Syria_(Roman_province)',      35.0000, 38.0000, 'SY'),
    (960044, 'https://en.wikipedia.org/wiki/Thracia_(Roman_province)',    42.0000, 26.0000, 'BG'),
    # ── Roman Provinces — manual additions ───────────────────────────────
    (960003, 'https://en.wikipedia.org/wiki/Africa_(Roman_province)',     35.0000, 10.0000, 'TN'),
    (960008, 'https://en.wikipedia.org/wiki/Bithynia_et_Pontus',         41.0000, 32.0000, 'TR'),
    (960009, 'https://en.wikipedia.org/wiki/Roman_Britain',              53.0000, -2.0000, 'GB'),
    (960011, 'https://en.wikipedia.org/wiki/Crete_and_Cyrenaica',        35.5000, 24.0000, 'GR'),
    (960015, 'https://en.wikipedia.org/wiki/Dalmatia_(Roman_province)',  43.5000, 16.5000, 'HR'),
    (960017, 'https://en.wikipedia.org/wiki/Gallia_Aquitania',           44.5000,  1.5000, 'FR'),
    (960019, 'https://en.wikipedia.org/wiki/Gallia_Lugdunensis',         47.0000,  2.5000, 'FR'),
    (960020, 'https://en.wikipedia.org/wiki/Gallia_Narbonensis',         43.5000,  4.5000, 'FR'),
    (960023, 'https://en.wikipedia.org/wiki/Germania_Superior',          48.0000,  8.0000, 'DE'),
    (960025, 'https://en.wikipedia.org/wiki/Hispania_Tarraconensis',     41.5000, -1.0000, 'ES'),
    (960027, 'https://en.wikipedia.org/wiki/Judaea_(Roman_province)',    31.5000, 35.0000, 'IL'),
    (960028, 'https://en.wikipedia.org/wiki/Lycia_et_Pamphylia',         37.0000, 30.0000, 'TR'),
    (960030, 'https://en.wikipedia.org/wiki/Macedonia_Prima',            41.0000, 22.0000, 'GR'),
    (960032, 'https://en.wikipedia.org/wiki/Moesia',                     44.0000, 22.0000, 'RS'),
    (960033, 'https://en.wikipedia.org/wiki/Moesia',                     44.5000, 21.0000, 'RS'),
    (960034, 'https://en.wikipedia.org/wiki/Mauretania_Caesariensis',    36.0000,  2.5000, 'DZ'),
    (960035, 'https://en.wikipedia.org/wiki/Mauretania_Tingitana',       33.0000, -5.5000, 'MA'),
    (960037, 'https://en.wikipedia.org/wiki/Numidia',                    36.0000,  6.5000, 'DZ'),
    (960039, 'https://en.wikipedia.org/wiki/Pannonia_Superior',          47.5000, 16.5000, 'AT'),
    (960041, 'https://en.wikipedia.org/wiki/Sardinia_and_Corsica_(Roman_province)', 40.5000, 9.0000, 'IT'),
    (960042, 'https://en.wikipedia.org/wiki/Sicily_(Roman_province)',    37.5000, 14.0000, 'IT'),

    # ── Temples — vetted auto-matches (reject #3 Obzor Hill in Antarctica) ─
    (1816,    'https://en.wikipedia.org/wiki/%C5%BDitora%C4%91a',       43.1833, 21.7167, 'XK'),
    (671,     'https://en.wikipedia.org/wiki/Corseul',                  48.4825, -2.1689, 'FR'),
    (2105,    'https://en.wikipedia.org/wiki/Kand%C4%B1ra',             41.0722, 30.1611, 'TR'),
    (2000863, 'https://en.wikipedia.org/wiki/Gubbio',                   43.3500, 12.5667, 'IT'),
    # ── Temples — manual correction (Obzor was matched wrong, add correct) ─
    (1965,    'https://en.wikipedia.org/wiki/Obzor',                    42.8317, 27.8794, 'BG'),

    # ── Ports — vetted auto-matches ───────────────────────────────────────
    (838,     'https://en.wikipedia.org/wiki/Fos-sur-Mer',              43.4403,  4.9486, 'FR'),
    (2405,    'https://en.wikipedia.org/wiki/Batumi',                   41.6458, 41.6417, 'GE'),
    (691,     'https://en.wikipedia.org/wiki/Nantes',                   47.2181, -1.5528, 'FR'),
    (2861,    'https://en.wikipedia.org/wiki/Port-Vendres',             42.5189,  3.1058, 'FR'),  # bbox→ES, override FR
    (2966,    'https://en.wikipedia.org/wiki/Senj',                     44.9901, 14.9030, 'HR'),
    (2985,    'https://en.wikipedia.org/wiki/Solin',                    43.5317, 16.4949, 'HR'),  # bbox→BA, override HR
    # ── Ports — manual additions ──────────────────────────────────────────
    (1260,    'https://en.wikipedia.org/wiki/Fiumicino',                41.7729, 12.2361, 'IT'),
    (3025,    'https://en.wikipedia.org/wiki/Corfu',                    39.6243, 19.9217, 'GR'),
    (2904,    'https://en.wikipedia.org/wiki/Portoferraio',             42.8150, 10.3228, 'IT'),
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
