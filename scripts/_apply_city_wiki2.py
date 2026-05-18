import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, lat, lng, country, conf, manual)
# lat/lng written only if record has no coordinates yet
# country always written (corrects bbox mistakes)
# conf: 3=exact, 2=cleaned match, 1=uncertain
# manual: True if hand-curated, False if from automated search
#
# REJECTED from dry-run:
#    575 Agripina → Köln Hauptbahnhof (wrong article) → added manually as Cologne below
#   1947 Axiopolis → Hinogawa Dam (Japan)
#   2380 Berya → Halebidu (India, not Aleppo)
#   2409 Bylae → Kolathur (India, conf=1, wrong region)
#    149 Gvrra → Kalaa at wrong coords
#   1951 Troesmis → Igli (Morocco, not Romania)
#   2454 Sebastopolis → Sokhumi Institute of Physics (wrong article) → added manually as Sukhumi below
ENTRIES = [
    # ── Auto-matched (run 1 + run 2 search log) ─────────────────────────
    ( 511,  'https://en.wikipedia.org/wiki/Qalaat_al-Madiq',            35.4100,  36.3900, 'SY', 3, False),
    (2404,  'https://de.wikipedia.org/wiki/Gonio',                      41.5609,  41.5708, 'GE', 3, False),
    (1890,  'https://de.wikipedia.org/wiki/Athen',                      37.9778,  23.7278, 'GR', 2, False),
    (1000,  'https://en.wikipedia.org/wiki/Augsburg',                   48.3689,  10.8978, 'DE', 3, False),  # AT→DE
    ( 658,  'https://fr.wikipedia.org/wiki/Autun',                      46.9517,   4.2994, 'FR', 3, False),
    ( 738,  'https://it.wikipedia.org/wiki/Cahors',                     44.4333,   1.4333, 'FR', 3, False),
    (1454,  'https://it.wikipedia.org/wiki/Santa_Maria_Capua_Vetere',   41.0833,  14.2500, 'IT', 3, False),
    (2491,  'https://en.wikipedia.org/wiki/Erci%C5%9F',                 39.0311,  43.3597, 'TR', 3, False),
    (2386,  'https://it.wikipedia.org/wiki/Tekirda%C4%9F',              40.9833,  27.5167, 'TR', 3, False),  # GR→TR
    (2107,  'https://en.wikipedia.org/wiki/Bolu',                       40.7347,  31.6075, 'TR', 3, False),
    (2082,  'https://it.wikipedia.org/wiki/Istanbul',                   41.0167,  28.9667, 'TR', 3, False),  # GR→TR
    (3544,  'https://en.wikipedia.org/wiki/Rasht',                      37.2744,  49.5889, 'IR', 3, False),
    ( 547,  'https://en.wikipedia.org/wiki/Dover',                      51.1295,   1.3089, 'GB', 3, False),
    ( 494,  'https://en.wikipedia.org/wiki/Baalbek',                    34.0063,  36.2073, 'LB', 3, False),
    ( 837,  'https://de.wikipedia.org/wiki/Fr%C3%A9jus',                43.4330,   6.7370, 'FR', 3, False),
    (2013,  'https://en.wikipedia.org/wiki/Edirne',                     41.6769,  26.5556, 'TR', 3, False),  # BG→TR
    (2164,  'https://en.wikipedia.org/wiki/Ladik',                      40.9167,  35.5833, 'TR', 3, False),
    ( 700,  'https://fr.wikipedia.org/wiki/Saintes',                    45.7464,  -0.6333, 'FR', 3, False),
    (2532,  'https://de.wikipedia.org/wiki/Malatya',                    38.3486,  38.3194, 'TR', 1, False),  # Eski Malatya / Melitene
    (2384,  'https://it.wikipedia.org/wiki/Balat',                      41.0320,  28.9483, 'TR', 3, False),  # GR→TR
    ( 513,  'https://it.wikipedia.org/wiki/Homs',                       34.7333,  36.7167, 'SY', 3, False),
    ( 782,  'https://en.wikipedia.org/wiki/N%C3%AEmes',                 43.8383,   4.3597, 'FR', 3, False),
    (2257,  'https://de.wikipedia.org/wiki/Niksar',                     40.5833,  36.9667, 'TR', 3, False),
    (2110,  'https://en.wikipedia.org/wiki/%C4%B0zmit',                 40.7600,  29.9200, 'TR', 2, False),
    (1312,  'https://it.wikipedia.org/wiki/Palestrina',                 41.8333,  12.9000, 'IT', 3, False),
    (   7,  'https://en.wikipedia.org/wiki/Dellys',                     36.9133,   3.9141, 'DZ', 3, False),
    (2415,  'https://de.wikipedia.org/wiki/Sadak',                      40.0264,  39.5958, 'TR', 2, False),
    (1648,  'https://en.wikipedia.org/wiki/Belgrade',                   44.8178,  20.4569, 'RS', 2, False),
    (2104,  'https://de.wikipedia.org/wiki/Sinop',                      42.0250,  35.1472, 'TR', 3, False),
    (1511,  'https://it.wikipedia.org/wiki/Siracusa',                   37.0692,  15.2875, 'IT', 2, False),
    (2190,  'https://en.wikipedia.org/wiki/%C4%B0zmir',                 38.4244,  27.1322, 'TR', 2, False),  # GR→TR
    (2469,  'https://it.wikipedia.org/wiki/Sabirabad',                  40.0053,  48.4719, 'AZ', 3, False),
    ( 462,  'https://en.wikipedia.org/wiki/Tiberias',                   32.7944,  35.5333, 'IL', 3, False),
    ( 704,  'https://de.wikipedia.org/wiki/P%C3%A9rigueux',             45.1842,   0.7181, 'FR', 3, False),

    # ── Manual additions ──────────────────────────────────────────────────
    # Corrected false positives from dry-run
    ( 575,  'https://en.wikipedia.org/wiki/Cologne',                    50.9333,   6.9600, 'DE', 3, True),  # NL→DE; script matched Köln Hauptbahnhof
    (2454,  'https://en.wikipedia.org/wiki/Sukhumi',                    43.0019,  41.0194, 'GE', 3, True),  # script matched Sokhumi Institute (wrong)

    # Famous cities not found (vague/foreign modern names)
    ( 681,  'https://en.wikipedia.org/wiki/Chalon-sur-Sa%C3%B4ne',     46.7811,   4.8522, 'FR', 3, True),  # Cabillione
    (1583,  'https://en.wikipedia.org/wiki/Celje',                      46.2309,  15.2625, 'SI', 3, True),  # Celeia
    ( 442,  'https://en.wikipedia.org/wiki/Caesarea_Maritima',          32.5000,  34.9000, 'IL', 3, True),  # Cesaria
    ( 497,  'https://en.wikipedia.org/wiki/Byblos',                     34.1228,  35.6489, 'LB', 3, True),  # Biblo
    ( 477,  'https://en.wikipedia.org/wiki/Bosra',                      32.5171,  36.4833, 'SY', 3, True),  # Bostris
    (1898,  'https://en.wikipedia.org/wiki/Argos,_Peloponnese',         37.6333,  22.7333, 'GR', 3, True),  # Argos
    (2464,  'https://en.wikipedia.org/wiki/Artashat',                   39.9594,  44.5503, 'AM', 3, True),  # Artaxata — ancient Armenian capital
    (1836,  'https://en.wikipedia.org/wiki/Thessaloniki',               40.6401,  22.9444, 'GR', 3, True),  # Tessalonicę
    (1957,  'https://en.wikipedia.org/wiki/Constan%C8%9Ba',             44.1833,  28.6333, 'RO', 3, True),  # Tomis — Ovid's place of exile
    (2627,  'https://en.wikipedia.org/wiki/Sinjar',                     36.3250,  41.8261, 'IQ', 3, True),  # Singara
    ( 527,  'https://en.wikipedia.org/wiki/Palmyra,_Syria',             34.5503,  38.2674, 'SY', 3, True),  # Palmyra (Tudmur)
    (  37,  'https://en.wikipedia.org/wiki/Annaba',                     36.9170,   7.7667, 'DZ', 3, True),  # Hippone Regio / Hippo Regius
    (2659,  'https://en.wikipedia.org/wiki/Hatra',                      35.5853,  42.7207, 'IQ', 3, True),  # Hatris — UNESCO WH site
    (1901,  'https://en.wikipedia.org/wiki/Sparta',                     37.0750,  22.4300, 'GR', 3, True),  # Lacedemone
    (2702,  'https://en.wikipedia.org/wiki/Babylon',                    32.5421,  44.4216, 'IQ', 3, True),  # Babylonia
    ( 588,  'https://en.wikipedia.org/wiki/Bavay',                      50.3006,   3.7986, 'FR', 3, True),  # Baca Conervio
    ( 583,  'https://en.wikipedia.org/wiki/Cassel,_Nord',               50.7997,   2.4936, 'FR', 3, True),  # Castello Menapiorvm
    ( 228,  'https://en.wikipedia.org/wiki/Gab%C3%A8s',                 33.8833,  10.1167, 'TN', 3, True),  # Tacape
    ( 461,  'https://en.wikipedia.org/wiki/Beit_She%27an',              32.5072,  35.5028, 'IL', 3, True),  # Scytopoli
    ( 434,  'https://en.wikipedia.org/wiki/Ashkelon',                   31.6685,  34.5744, 'IL', 3, True),  # Ascalone
    (1745,  'https://en.wikipedia.org/wiki/Alba_Iulia',                  46.0631,  23.5799, 'RO', 3, True),  # Apula
    (1902,  'https://en.wikipedia.org/wiki/Olympia,_Greece',             37.6386,  21.6306, 'GR', 3, True),  # Olympia
    (1893,  'https://en.wikipedia.org/wiki/Ancient_Corinth',             37.9058,  22.8650, 'GR', 3, True),  # Corintho
    ( 292,  'https://en.wikipedia.org/wiki/Tripoli',                     32.9028,  13.1806, 'LY', 3, True),  # Osa — ancient Oea / Tripoli Libya
    (2582,  'https://en.wikipedia.org/wiki/Silvan,_Turkey',              38.1444,  41.0022, 'TR', 3, True),  # Triganocarten — ancient Martyropolis
    (2691,  'https://en.wikipedia.org/wiki/Tikrit',                      34.6000,  43.6800, 'IQ', 3, True),  # Peloriarca — Tikrit
    (1976,  'https://en.wikipedia.org/wiki/Marmara_Ereglis',             40.9711,  27.9636, 'TR', 3, True),  # Perintus — ancient Perinthus / Heraclea
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
    r['wiki_url']         = wiki_url
    r['wiki_confidence']  = conf
    r['wiki_manual']      = manual
    if r.get('lat') is None and lat is not None:
        r['lat'] = lat
        r['lng'] = lng
    if country:
        r['country'] = country
    saved += 1
    print(f'  OK  {data_id}  {(r.get("latin_std") or r.get("latin",""))[:35]}')

print(f'\nApplied {saved} wiki_url entries')
tmp = DB_PATH.with_suffix('.tmp')
tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
tmp.replace(DB_PATH)
print(f'Saved -> {DB_PATH.name}')
