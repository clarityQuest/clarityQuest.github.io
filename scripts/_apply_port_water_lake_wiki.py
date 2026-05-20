import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, lat, lng, country, conf, manual)
# lat/lng only applied if record has none; pass None for country to leave unchanged
ENTRIES = [
    # ── PORTS (conf 3) ─────────────────────────────────────────────────────────
    (2958,    'https://en.wikipedia.org/wiki/Kvarner_Gulf',           45.137856, 14.500,  'HR', 3, True),  # Port Flanaticus = Sinus Flanaticus (Kvarner Gulf)
    (2991,    'https://en.wikipedia.org/wiki/Epetion',                43.499440, 16.415,  'HR', 3, True),  # Portus Epitius = Epetion (Stobreč near Split)
    (3027,    'https://en.wikipedia.org/wiki/Santa_Maria_di_Leuca',   40.280000, 18.350,  'IT', 3, True),  # Port Salentinum = Leuca (southernmost Apulia)
    (3002147, 'https://en.wikipedia.org/wiki/Kaštela_Bay',            43.540000, 16.350,  'HR', 3, True),  # Portus Salonitanus = Kaštela Bay (harbor of Salona)

    # ── WATER BODIES (conf 3) ───────────────────────────────────────────────────
    (3002203, 'https://en.wikipedia.org/wiki/Adriatic_Sea',           42.470054, 16.000,  None, 3, True),  # Hadriaticvm Pelagvs = Adriatic Sea
    (3002181, 'https://en.wikipedia.org/wiki/Aegean_Sea',             38.913957, 25.000,  'GR', 3, True),  # IG˙EVM MARE = Aegean Sea
    (3002300, 'https://en.wikipedia.org/wiki/Black_Sea',              43.078685, 33.000,  None, 3, True),  # PONTVS EVXIN[.] = Black Sea (Pontus Euxinus)
    (3235,    'https://en.wikipedia.org/wiki/Caspian_Sea',            42.000000, 51.000,  'AZ', 3, True),  # MARE HYRCANIVM = Caspian Sea (Hyrcanian Sea)
    (3495,    'https://en.wikipedia.org/wiki/Caspian_Sea',            40.432985, 50.107,  'AZ', 3, True),  # Mare Caspium = Caspian Sea (western label)
    (3001998, 'https://en.wikipedia.org/wiki/Bay_of_Biscay',          44.000000, -4.000,  'FR', 3, True),  # SINVS AQVTANICVS = Bay of Biscay (Aquitanic Gulf)
    (3002234, 'https://en.wikipedia.org/wiki/Gulf_of_Gabès',          33.500000, 10.500,  'TN', 3, True),  # SyRtes iNoRes = Gulf of Gabès (Lesser Syrtis)
    (3002276, 'https://en.wikipedia.org/wiki/Gulf_of_Sidra',          31.474808, 18.000,  'LY', 3, True),  # Syrtes Maiores = Gulf of Sidra (Greater Syrtis)
    (2857,    'https://en.wikipedia.org/wiki/Cap_de_Creus',           42.319170,  3.317,  'ES', 3, True),  # Promontorium Pyreneum = Cap de Creus — fix E→ES
    (3002328, 'https://en.wikipedia.org/wiki/Gulf_of_İzmit',          40.750000, 29.900,  'TR', 3, True),  # Sinvs Nicomedicvs = Gulf of Izmit — fix GR→TR
    (3002224, 'https://en.wikipedia.org/wiki/Thermaic_Gulf',          40.383333, 22.800,  'GR', 3, True),  # Sinvs Mac[e]donicvs = Thermaic Gulf

    # ── LAKES (conf 3) ──────────────────────────────────────────────────────────
    (940,     'https://en.wikipedia.org/wiki/Lake_Geneva',            46.519478,  6.537,  'CH', 3, True),  # Lacvm Losonne = Lake Geneva (Lacus Lemannus)
    (2928,    'https://en.wikipedia.org/wiki/Lake_Como',              45.980000,  9.260,  'IT', 3, True),  # Lacvs Comacinus = Lake Como
    (3565,    'https://en.wikipedia.org/wiki/Lake_Tritonis',          33.500000,  9.000,  'TN', 3, True),  # lacvs Tri..nvm = Lake Tritonis (Tunisia)
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
