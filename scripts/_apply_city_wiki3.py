import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, lat, lng, country, conf, manual)
ENTRIES = [
    # ── Levant / Middle East ─────────────────────────────────────────────────
    (2380, 'https://en.wikipedia.org/wiki/Aleppo',              36.2021,  37.1343, 'SY', 3, True),  # Berya = Beroea = Aleppo
    (2695, 'https://en.wikipedia.org/wiki/Ctesiphon',           33.0942,  44.5819, 'IQ', 3, True),  # Cesiphvn
    (2439, 'https://en.wikipedia.org/wiki/Manbij',              36.5150,  37.9456, 'SY', 3, True),  # Ab Hierapoli = Hierapolis Bambyce
    (2621, 'https://en.wikipedia.org/wiki/Ras_al-Ayn',          36.8636,  40.0700, 'SY', 3, True),  # Ressaina
    ( 488, 'https://en.wikipedia.org/wiki/Sidon',               33.5608,  35.3708, 'LB', 3, True),  # Sydone
    ( 487, 'https://en.wikipedia.org/wiki/Tyre,_Lebanon',       33.2704,  35.2038, 'LB', 3, True),  # Tyro

    # ── Anatolia ─────────────────────────────────────────────────────────────
    (2184, 'https://en.wikipedia.org/wiki/Sardis',              38.4770,  28.0389, 'TR', 3, True),  # Sardes
    (2364, 'https://en.wikipedia.org/wiki/Silifke',             36.3731,  33.9331, 'TR', 3, True),  # Selevcia = Seleucia on Calycadnus
    (2297, 'https://en.wikipedia.org/wiki/Tyana',               37.8300,  34.5800, 'TR', 3, True),  # Tyana
    (2580, 'https://en.wikipedia.org/wiki/Zeugma_(city)',       37.0525,  37.8608, 'TR', 3, True),  # Zevgma
    (2208, 'https://en.wikipedia.org/wiki/Alexandria_Troas',    39.7583,  26.1583, 'TR', 3, True),  # Alexandria troas
    (2394, 'https://en.wikipedia.org/wiki/Phaselis',            36.5253,  30.5558, 'TR', 3, True),  # Phaselis
    (2180, 'https://en.wikipedia.org/wiki/Ala%C5%9Fehir',       38.3553,  28.5150, 'TR', 3, True),  # Philadelfia = Philadelphia
    (2212, 'https://en.wikipedia.org/wiki/Antandrus',           39.5517,  26.8628, 'TR', 3, True),  # Antandros
    (2345, 'https://en.wikipedia.org/wiki/Anemurion',           36.0333,  32.8167, 'TR', 3, True),  # Animvrio
    (2351, 'https://en.wikipedia.org/wiki/Antioch_in_Pisidia',  38.3492,  31.0756, 'TR', 3, True),  # Antiochia pisidia
    (2283, 'https://en.wikipedia.org/wiki/Kayseri',             38.7205,  35.4826, 'TR', 3, True),  # Mazaca cesarea
    (2213, 'https://en.wikipedia.org/wiki/Adramyttium',         39.5500,  27.0167, 'TR', 2, True),  # Adrimitios
    (2333, 'https://en.wikipedia.org/wiki/%C4%B0skenderun',     36.5833,  36.1667, 'TR', 2, True),  # Alexandria catisson = Alexandretta
    (2307, 'https://en.wikipedia.org/wiki/Comana,_Cappadocia',  38.0700,  36.6300, 'TR', 2, True),  # Comana Capadocia
    (3001379,'https://en.wikipedia.org/wiki/Comana,_Pontus',    40.3200,  36.5500, 'TR', 2, True),  # Comana pontica
    (2346, 'https://en.wikipedia.org/wiki/Apamea_Cibotus',      38.0700,  30.1700, 'TR', 2, True),  # Apamea ciboton
    (1982, 'https://en.wikipedia.org/wiki/Herakleia_Pontike',   41.2781,  31.4083, 'TR', 2, True),  # Heraclea near Erikli

    # ── Greece ───────────────────────────────────────────────────────────────
    (2059, 'https://en.wikipedia.org/wiki/Chania',              35.5138,  24.0180, 'GR', 3, True),  # Cydonia = Chania (Crete)
    ( 347, 'https://en.wikipedia.org/wiki/Cyrene,_Libya',       32.8269,  21.8584, 'LY', 3, True),  # Cyrenis col.
    (3000943,'https://en.wikipedia.org/wiki/Larissa',           39.6390,  22.4191, 'GR', 3, True),  # Larissa
    (2040, 'https://en.wikipedia.org/wiki/Philippi',            41.0144,  24.2872, 'GR', 3, True),  # Philippis
    (1874, 'https://en.wikipedia.org/wiki/Elateia',             38.6203,  22.7283, 'GR', 3, True),  # Elatia
    (1899, 'https://en.wikipedia.org/wiki/Epidaurus',           37.6300,  23.0700, 'GR', 3, True),  # Epitavro
    (2065, 'https://en.wikipedia.org/wiki/Kissamos',            35.4900,  23.6500, 'GR', 2, True),  # Cisamos = Kissamos
    (2070, 'https://en.wikipedia.org/wiki/Gortyn',              35.0619,  24.9469, 'GR', 2, True),  # Cortina = Gortyn

    # ── Balkans ───────────────────────────────────────────────────────────────
    (1826, 'https://en.wikipedia.org/wiki/Stobi',               41.5453,  21.9731, 'MK', 3, True),  # Stopis
    (1839, 'https://en.wikipedia.org/wiki/Heraclea_Lyncestis',  41.0189,  21.3292, 'MK', 3, True),  # Heraclea near Bitola
    (1858, 'https://en.wikipedia.org/wiki/Vlor%C3%AB',          40.4650,  19.4897, 'AL', 3, True),  # Avlona = Vlorë
    (1930, 'https://en.wikipedia.org/wiki/Porolissum',          47.1819,  23.1803, 'RO', 3, True),  # Porolisso
    (1958, 'https://en.wikipedia.org/wiki/Varna,_Bulgaria',     43.2048,  27.9103, 'BG', 3, True),  # Port. Callirhoë = Varna
    (1947, 'https://en.wikipedia.org/wiki/Axiopolis',           44.1927,  28.3397, 'RO', 2, True),  # Axiopolis
    (1698, 'https://en.wikipedia.org/wiki/Narona',              43.0600,  17.4200, 'HR', 3, True),  # Narona = Vid
    (2050, 'https://en.wikipedia.org/wiki/Heracleia_Sintica',   41.4883,  23.1544, 'BG', 2, True),  # Heracleasantica

    # ── North Africa ─────────────────────────────────────────────────────────
    ( 300, 'https://en.wikipedia.org/wiki/Leptis_Magna',        32.6394,  14.2917, 'LY', 3, True),  # Leptimagna
    ( 340, 'https://en.wikipedia.org/wiki/Benghazi',            32.1167,  20.0667, 'LY', 3, True),  # Bernicide
    ( 343, 'https://en.wikipedia.org/wiki/Ptolemais_(Cyrenaica)',32.7003,  20.9556, 'LY', 3, True),  # Ptolomaide
    ( 289, 'https://en.wikipedia.org/wiki/Sabratha',            32.7927,  12.4879, 'LY', 3, True),  # Sabrata
    (  26, 'https://en.wikipedia.org/wiki/Jijel',               36.8200,   5.7667, 'DZ', 3, True),  # Igilgili col.
    (  14, 'https://en.wikipedia.org/wiki/B%C3%A9ja%C3%AFa',    36.7519,   5.0564, 'DZ', 3, True),  # Saldas
    (  30, 'https://en.wikipedia.org/wiki/Skikda',              36.8761,   6.9060, 'DZ', 3, True),  # Rvsicade
    (  90, 'https://en.wikipedia.org/wiki/Djemila',             36.3228,   5.7381, 'DZ', 3, True),  # Cvlchvl = Djemila (Cuicul)
    ( 104, 'https://en.wikipedia.org/wiki/Mila,_Algeria',       36.4517,   6.2650, 'DZ', 3, True),  # Milev Colonia
    ( 120, 'https://en.wikipedia.org/wiki/Le_Kef',              36.1742,   8.7144, 'TN', 3, True),  # Sicca Veneria
    (  55, 'https://en.wikipedia.org/wiki/Utica_(ancient_city)', 37.0549,  10.0542, 'TN', 3, True),  # Vtica Colonia
    ( 374, 'https://en.wikipedia.org/wiki/Pelusium',            31.0456,  32.5483, 'EG', 3, True),  # Pelvsio
    ( 387, 'https://en.wikipedia.org/wiki/Memphis,_Egypt',      29.8468,  31.2516, 'EG', 3, True),  # Memphis
    ( 412, 'https://en.wikipedia.org/wiki/Asyut',               27.1869,  31.1833, 'EG', 3, True),  # Tyconpoli = Lycopolis
    ( 423, 'https://en.wikipedia.org/wiki/Babylon_Fortress',    30.0062,  31.2292, 'EG', 3, True),  # Babylonia = Babylon Fortress

    # ── Western Europe ────────────────────────────────────────────────────────
    ( 562, 'https://en.wikipedia.org/wiki/Nijmegen',            51.8426,   5.8528, 'NL', 3, True),  # Noviomagi
    ( 552, 'https://en.wikipedia.org/wiki/Leiden',              52.1601,   4.4970, 'NL', 1, True),  # Lvgdvno = Leiden (disputed; also Katwijk)
    ( 553, 'https://en.wikipedia.org/wiki/Praetorium_Agrippinae',52.1767,  4.4278, 'NL', 2, True),  # Pretoriū AgRippine
    ( 993, 'https://en.wikipedia.org/wiki/Wels',                48.1581,  14.0286, 'AT', 3, True),  # Ovilia = Wels
    (1265, 'https://en.wikipedia.org/wiki/Penne,_Abruzzo',      42.4545,  13.9290, 'IT', 3, True),  # Pinna
    ( 625, 'https://en.wikipedia.org/wiki/%C3%89vreux',         49.0268,   1.1510, 'FR', 3, True),  # Mediolanum Aulercorum
    ( 644, 'https://en.wikipedia.org/wiki/Vieux,_Calvados',     49.1306,  -0.4139, 'FR', 3, True),  # Araegenve = Vieux (Aregenua)
    ( 646, 'https://en.wikipedia.org/wiki/Jublains',            48.2753,  -0.4836, 'FR', 2, True),  # NV DIONNVM = Jublains
    ( 549, 'https://en.wikipedia.org/wiki/Lympne',              51.0700,   1.0200, 'GB', 2, True),  # Lemavio = Lympne
    ( 903, 'https://en.wikipedia.org/wiki/Naix-aux-Forges',     48.5761,   5.3606, 'FR', 2, True),  # Nasie = Nasium

    # ── Far east ─────────────────────────────────────────────────────────────
    (2736, 'https://en.wikipedia.org/wiki/Merv',                37.6639,  62.1861, 'TM', 2, True),  # Antiochia = Antiochia Margiana
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
    print(f'  OK  {data_id}  {(r.get("latin_std") or r.get("latin",""))[:35]}')

print(f'\nApplied {saved} wiki_url entries')
tmp = DB_PATH.with_suffix('.tmp')
tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
tmp.replace(DB_PATH)
print(f'Saved -> {DB_PATH.name}')
