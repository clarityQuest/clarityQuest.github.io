import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, lat, lng, country, conf, manual)
ENTRIES = [
    # ── Conf 3 — clear ancient-name match ────────────────────────────────────────
    (2654,    'https://en.wikipedia.org/wiki/Lycus_(river_of_Phrygia)', 37.843, 29.100, 'TR', 3, True),  # [Licus] = Lycus of Phrygia (Çürüksu, joins Maeander near Laodicea)
    (1487,    'https://en.wikipedia.org/wiki/Tanagro',                  40.640, 15.480, 'IT', 3, True),  # Fluvius Tanno = Tanagro/Tanager (ancient Tanager; Campania)
    (1163,    'https://en.wikipedia.org/wiki/Musone',                   43.475, 13.615, 'IT', 3, True),  # Misco fl = Musone (Latin name Misco confirmed in Wikipedia article)
    (2650,    'https://en.wikipedia.org/wiki/Tell_Brak',                36.412, 41.060, 'SY', 3, True),  # Lacvs Beberaci — Wikipedia article explicitly cites "Lacus Beberaci" on the Tabula Peutingeriana (dried lake east of Tell Brak, NE Syria)
    (3002284, 'https://en.wikipedia.org/wiki/Black_Sea',                43.000, 34.000, None, 3, True),  # Sinus Eusinus = Pontus Euxinus = Black Sea (second label, variant spelling)

    # ── Conf 2 — probable match ───────────────────────────────────────────────────
    (2106,    'https://en.wikipedia.org/wiki/Sakarya_River',            40.666, 30.000, 'TR', 2, True),  # Sagar Fl = Sangarius/Sakarya (scribal "Sagar" from Sangarius; Black Sea, Bithynia)
    (3002430, 'https://en.wikipedia.org/wiki/Gulf_of_Oman',             27.000, 57.000, 'IR', 2, True),  # Sinus Carmanius = Gulf of Carmania = Gulf of Oman
    (2000824, 'https://en.wikipedia.org/wiki/Chelif_River',             36.500,  1.900, 'DZ', 2, True),  # Fl CHvlcvl = Chelif/Chinalaph (longest river in Algeria)
    (3002582, 'https://en.wikipedia.org/wiki/Chiana',                   42.279, 11.940, 'IT', 2, True),  # Fl? ClocoRis = Clanis = Chiana (Tuscany/Umbria; ancient Clanis)
    (3026,    'https://en.wikipedia.org/wiki/Strait_of_Messina',        38.264, 15.590, 'IT', 2, True),  # PoRt TragecvNvs = Portus Traectus = Messina Strait ferry crossing
    (1879,    'https://en.wikipedia.org/wiki/Achelous_River',           38.327, 21.100, 'GR', 2, True),  # [Calidon fl.] = river near Calydon (Aetolia) = Achelous (major river bounding Calydon's territory)
    (514,     'https://en.wikipedia.org/wiki/Orontes_River',            34.960, 36.550, 'SY', 2, True),  # Aretusa Fl = river near Arethusa/al-Rastan = Orontes (third label on map)
    (1719,    'https://it.wikipedia.org/wiki/Aposa',                    44.500, 11.340, 'IT', 2, True),  # apo Fl = Aposa (stream through Bologna; Italian WP confirms name)
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
    print(f'  OK  {data_id:<12}  {(r.get("latin_std") or r.get("latin",""))[:45]}')

print(f'\nApplied {saved} wiki_url entries')
tmp = DB_PATH.with_suffix('.tmp')
tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
tmp.replace(DB_PATH)
print(f'Saved -> {DB_PATH.name}')
