import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, lat, lng, country, conf, manual)
# lat/lng only applied if record has none; country always overwritten when provided
ENTRIES = [
    # ── Conf 3 — clear ancient-name match ───────────────────────────────────────
    (1092,    'https://en.wikipedia.org/wiki/Arno',              43.724361, 10.392,  'IT', 3, True),  # Arnvm Fl — fix I→IT
    (1143,    'https://en.wikipedia.org/wiki/Rubicon',           44.154621, 12.456,  'IT', 3, True),  # Rubico fl
    (1157,    'https://en.wikipedia.org/wiki/Metauro',           43.830441, 13.025,  'IT', 3, True),  # Matavrum fl — fix I→IT
    (1549,    'https://en.wikipedia.org/wiki/Rába',              47.684052, 17.633,  'HU', 3, True),  # Arrabo Fl — fix H→HU
    (1615,    'https://en.wikipedia.org/wiki/Raša_(river)',      45.078854, 14.072,  'HR', 3, True),  # ArSia Fl (Arsia)
    (1666,    'https://en.wikipedia.org/wiki/Drina',             44.868279, 19.217,  'BA', 3, True),  # Drinum fl — fix BIH→BA
    (3493,    'https://en.wikipedia.org/wiki/Aras_(river)',      40.018400, 44.772,  'AZ', 3, True),  # Fl. Araxes
    (510,     'https://en.wikipedia.org/wiki/Orontes_River',     35.378376, 36.155,  'SY', 3, True),  # Orontem Fl
    (3002657, 'https://en.wikipedia.org/wiki/Karamenderes_River',39.970,    26.130,  'TR', 3, True),  # Fl Scamander (Troad)
    (3002658, 'https://en.wikipedia.org/wiki/Bakırçay',          39.120,    26.900,  'TR', 3, True),  # Fl Caicus (Pergamon area)
    (3002632, 'https://en.wikipedia.org/wiki/Olt_(river)',       45.489293, 24.367,  'RO', 3, True),  # river 15H = Aluta/Olt
    (3429,    'https://en.wikipedia.org/wiki/Someș',             48.114000, 23.594,  'RO', 3, True),  # Samus fl = Someș
    (3002599, 'https://en.wikipedia.org/wiki/Drin_(river)',      42.069369, 19.513,  'AL', 3, True),  # Fl. Drilo — fix ME→AL
    (3425,    'https://en.wikipedia.org/wiki/Iskar_(river)',     42.194440, 24.452,  'BG', 3, True),  # Fl. Escvs = Iskar
    (1878,    'https://en.wikipedia.org/wiki/Evinos',            38.326395, 21.573,  'GR', 3, True),  # Evvenos fl = Evinos (Aetolia)
    (3341,    'https://en.wikipedia.org/wiki/Brenta_(river)',    45.183800, 12.145,  'IT', 3, True),  # Fl Meduacvm = Brenta — fix I→IT
    (2000817, 'https://en.wikipedia.org/wiki/Var_(river)',       43.710000,  7.193,  'FR', 3, True),  # Fl Varvm = Var
    (1147,    'https://en.wikipedia.org/wiki/Idice',             44.458271, 12.285,  'IT', 3, True),  # Isex Fluvius = Idice — fix I→IT
    (3002608, 'https://en.wikipedia.org/wiki/Amato_(river)',     38.953347, 16.157,  'IT', 3, True),  # Lametus fl = Amato (Calabria)
    (3002686, 'https://en.wikipedia.org/wiki/Abraham_River',     34.070000, 35.650,  'LB', 3, True),  # Adonius/Adonis fl = Nahr Ibrahim
    (508,     'https://en.wikipedia.org/wiki/Nahr_al-Kabir',    34.620239, 36.015,  'LB', 3, True),  # Fl. Eleuter = Nahr al-Kabir (Eleutherus)
    (3002492, 'https://en.wikipedia.org/wiki/Soummam_River',    36.473358,  5.069,  'DZ', 3, True),  # Fl. Nasabath = Soummam (Algeria)
    (1250,    'https://en.wikipedia.org/wiki/Marta_(river)',     42.252232, 11.756,  'IT', 3, True),  # Marta Fl — fix I→IT
    (3360,    'https://en.wikipedia.org/wiki/Paglia_(river)',    42.694500, 12.405,  'IT', 3, True),  # Fl Pallia = Paglia — fix I→IT
    (3371,    'https://en.wikipedia.org/wiki/Musone',            43.473900, 13.617,  'IT', 3, True),  # Fl Misiv = Musone — fix I→IT
    (2658,    'https://en.wikipedia.org/wiki/Tigris',            37.325001, 42.196,  'TR', 3, True),  # Ad flumen Tigrim
    (3002690, 'https://en.wikipedia.org/wiki/Euphrates',         36.830000, 38.010,  'SY', 3, True),  # Fl. Euphrates
    (3497,    'https://en.wikipedia.org/wiki/Tigris',            30.900000, 47.780,  'IQ', 3, True),  # Hostia fluminis Tygris (mouth)

    # ── Conf 2 — probable / position-based match ─────────────────────────────────
    (1850,    'https://en.wikipedia.org/wiki/Vjosa',             41.157651, 19.855,  'AL', 2, True),  # Genesis Fl = Vjosa (ancient Aoos, Albania)
    (1716,    'https://en.wikipedia.org/wiki/Great_Morava',      44.224551, 21.426,  'RS', 2, True),  # river 15C [Margum fl.] = Great Morava (Serbia)
    (3333,    'https://en.wikipedia.org/wiki/Oglio',             45.225000, 10.613,  'IT', 2, True),  # Fl Vmatia ~ Oglio (Po tributary, Cremona area) — fix I→IT
    (3308,    'https://en.wikipedia.org/wiki/Maira_(river)',     44.840300,  7.502,  'IT', 2, True),  # Fl Latis ~ Maira (Piedmont) — fix I→IT
    (3314,    'https://en.wikipedia.org/wiki/Bormida_(river)',   45.055306,  8.521,  'IT', 2, True),  # Fl BeRsvla ~ Bormida (Piedmont/Liguria) — fix I→IT
    (3312,    'https://en.wikipedia.org/wiki/Stura_di_Demonte',  44.821111,  7.724,  'IT', 2, True),  # Fl VaRvsa ~ Stura di Demonte — fix I→IT
    (2000816, 'https://en.wikipedia.org/wiki/Varaita',           44.640000,  7.530,  'IT', 2, True),  # Fl Fėvos ~ Varaita (Piedmont, joins Po at Saluzzo)
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
    print(f'  OK  {data_id:<12}  {(r.get("latin_std") or r.get("latin",""))[:40]}')

print(f'\nApplied {saved} wiki_url entries')
tmp = DB_PATH.with_suffix('.tmp')
tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
tmp.replace(DB_PATH)
print(f'Saved -> {DB_PATH.name}')
