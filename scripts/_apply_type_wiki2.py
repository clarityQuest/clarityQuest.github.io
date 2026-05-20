import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, lat, lng, country, conf, manual)
ENTRIES = [
    # ── RIVERS conf=3 — clear ancient-name match ─────────────────────────────────
    (1095,    'https://en.wikipedia.org/wiki/Ombrone',            43.465813, 11.014, 'IT', 3, True),  # Vmbro fl = Ombrone (Tuscany) — fix I→IT
    (1532,    'https://en.wikipedia.org/wiki/Vipava_River',       45.888573, 13.970, 'SI', 3, True),  # Fl. Frigido = Vipava/Frigidus (Battle of Frigidus 394 AD)
    (1149,    'https://en.wikipedia.org/wiki/Sillaro',            44.400127, 11.620, 'IT', 3, True),  # Silarvm Fluvius (44.4°N Emilia) = Sillaro — fix I→IT
    (1368,    'https://en.wikipedia.org/wiki/Sele_(river)',       40.549696, 14.960, 'IT', 3, True),  # Silarvm fl (40.5°N Campania) = Sele/Silarus (Paestum)
    (3325,    'https://en.wikipedia.org/wiki/Ticino_(river)',     45.082,     9.016, 'IT', 3, True),  # Fl. Ticenum = Ticino (ancient Ticinus; Pavia confluence)
    (3355,    'https://en.wikipedia.org/wiki/Arno',               43.725,    10.393, 'IT', 3, True),  # Fl. Arnu = Arno (second label) — fix I→IT
    (1225,    'https://en.wikipedia.org/wiki/Paglia_(river)',     42.754555, 12.405, 'IT', 3, True),  # Pallia Fl = Paglia (second label) — fix I→IT
    (1397,    'https://en.wikipedia.org/wiki/Crati',              39.718,    16.470, 'IT', 3, True),  # Crater Fl = Crati (ancient Crathis, Calabria)
    (3002610, 'https://en.wikipedia.org/wiki/Farfa_(river)',      42.226247, 12.680, 'IT', 3, True),  # Fl. Farfar = Farfa (Tiber tributary, Lazio)
    (3002680, 'https://en.wikipedia.org/wiki/Orontes_River',     36.300,    36.100, 'TR', 3, True),  # river 119 Fl Orontes = Orontes (second label; mouth near Antioch)
    (3002681, 'https://en.wikipedia.org/wiki/Pedieos_River',     35.100,    33.900, 'CY', 3, True),  # Pediaeus = Pedieos River (Cyprus)

    # ── WATER conf=3 ─────────────────────────────────────────────────────────────
    (2028,    'https://en.wikipedia.org/wiki/Rh%C3%B4ne',        45.128522, 4.820,  'FR', 3, True),  # OSTIA RODANI = Ostia/mouth of Rhône
    (2225,    'https://en.wikipedia.org/wiki/Gulf_of_Saros',     40.530676, 26.500, 'GR', 3, True),  # Milascolpvs = Melas Kolpos (Gulf of Saros)

    # ── PORT conf=3 ───────────────────────────────────────────────────────────────
    (3005,    'https://en.wikipedia.org/wiki/Porto_Torres',       41.066667,  8.400, 'IT', 3, True),  # Portus Turris Iuliana = Porto Torres (Sardinia) — fix I→IT

    # ── WATER conf=2 — probable match ────────────────────────────────────────────
    (3002367, 'https://en.wikipedia.org/wiki/Pamphylian_Sea',    36.399581, 31.000, 'TR', 2, True),  # Pamphilicum Pelagus = Pamphylian Sea (southern Anatolia)
    (3002368, 'https://en.wikipedia.org/wiki/Levantine_Sea',     35.706467, 34.000, None, 2, True),  # Finicum et Syriacum Pelagus = Levantine Sea

    # ── RIVERS conf=2 — probable match ───────────────────────────────────────────
    (3339,    'https://en.wikipedia.org/wiki/Lavino_(river)',     44.480956, 11.350, 'IT', 2, True),  # Fl. Lavinius = Lavino (Reno tributary, Bologna area)
    (3002609, 'https://en.wikipedia.org/wiki/Halex',             37.991356, 15.530, 'IT', 2, True),  # Halex fl / Kaikinos = Halex (Bruttium/Rhegion border river)
    (3002624, 'https://en.wikipedia.org/wiki/Wadi_Caam',         32.312956, 14.100, 'LY', 2, True),  # Fl. Cẏnips = Cinyps/Wadi Caam (Libya, Lepcis Magna area)
    (3002646, 'https://en.wikipedia.org/wiki/Lethon_River',      32.500000, 21.800, 'LY', 2, True),  # Lathon = Lethon (Lethe river near Cyrene, Libya)
    (3002653, 'https://en.wikipedia.org/wiki/Filyos_River',      41.117870, 32.050, 'TR', 2, True),  # Fl Bilis = Billaeus/Filyos (Heraclea Pontica area, Pontus)
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
