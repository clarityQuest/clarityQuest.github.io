import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, lat, lng, country)
# Many Croatian islands inside Dalmatia are bbox-assigned to BA — override to HR.
ENTRIES = [
    # ── Vetted auto-matches ───────────────────────────────────────────────
    (3030,    'https://en.wikipedia.org/wiki/Vulcano',              38.3994, 14.9640, 'IT'),
    (2902,    'https://en.wikipedia.org/wiki/Capraia',              43.0371,  9.8183, 'IT'),
    (2936,    'https://en.wikipedia.org/wiki/La_Maddalena',         41.2153,  9.4069, 'IT'),
    (3011,    'https://en.wikipedia.org/wiki/Ustica',               38.7053, 13.1761, 'IT'),
    (2974,    'https://en.wikipedia.org/wiki/Rab_(island)',          44.7560, 14.7611, 'HR'),
    (3013,    'https://en.wikipedia.org/wiki/Alicudi',              38.5425, 14.3525, 'IT'),
    (3043,    'https://en.wikipedia.org/wiki/Kefalonia',            38.2333, 20.5667, 'GR'),
    (2915,    'https://en.wikipedia.org/wiki/Corsica',              42.0000,  9.0000, 'FR'),  # bbox→IT, override FR
    (2961,    'https://en.wikipedia.org/wiki/Krk',                  45.0789, 14.6008, 'HR'),
    (3051,    'https://en.wikipedia.org/wiki/Arkoudi',              38.5500, 20.7070, 'GR'),
    (3068,    'https://en.wikipedia.org/wiki/Kythira',              36.2575, 22.9975, 'GR'),
    (2990,    'https://en.wikipedia.org/wiki/Hvar',                 43.1500, 16.7500, 'HR'),  # bbox→BA, override HR
    (3009,    'https://en.wikipedia.org/wiki/Lastovo',              42.7500, 16.8667, 'HR'),  # bbox→BA, override HR
    (3032,    'https://en.wikipedia.org/wiki/Lipari',               38.4667, 14.9500, 'IT'),
    (3008,    'https://en.wikipedia.org/wiki/Mljet',                42.7450, 17.5350, 'HR'),  # bbox→BA, override HR
    (3084,    'https://en.wikipedia.org/wiki/Milos',                36.6875, 24.4325, 'GR'),
    (2932,    'https://en.wikipedia.org/wiki/Pianosa,_Tuscany',     42.5822, 10.0783, 'IT'),
    (2959,    'https://en.wikipedia.org/wiki/Brijuni',              44.9167, 13.7667, 'HR'),
    (2856,    'https://en.wikipedia.org/wiki/Hy%C3%A8res',          43.1199,  6.1316, 'FR'),
    (3023,    'https://en.wikipedia.org/wiki/Sazan',                40.4936, 19.2806, 'AL'),
    (3041,    'https://en.wikipedia.org/wiki/Sazan',                40.4936, 19.2806, 'AL'),
    (2972,    'https://en.wikipedia.org/wiki/Ugljan',               44.0833, 15.1667, 'HR'),  # bbox→BA, use EN article
    (2988,    'https://en.wikipedia.org/wiki/%C5%A0olta',           43.3700, 16.3100, 'HR'),  # bbox→BA, override HR
    (3033,    'https://en.wikipedia.org/wiki/Stromboli',            38.7939, 15.2111, 'IT'),
    (3004,    'https://en.wikipedia.org/wiki/%C5%A0%C4%87edro',    43.0833, 16.7000, 'HR'),  # bbox→BA, override HR
    (3040,    'https://en.wikipedia.org/wiki/Zakynthos',            37.8000, 20.7500, 'GR'),
    (3028,    'https://en.wikipedia.org/wiki/Filicudi',             38.5714, 14.5625, 'IT'),
    (2986,    'https://en.wikipedia.org/wiki/%C4%8Ciovo',           43.5000, 16.2833, 'HR'),  # bbox→BA, override HR
    (3193,    'https://en.wikipedia.org/wiki/Cyprus',               35.1167, 33.4000, 'CY'),
    (3182,    'https://en.wikipedia.org/wiki/Rhodes',               36.1836, 27.9639, 'GR'),
    (3135,    'https://en.wikipedia.org/wiki/Lesbos',               39.2000, 26.3000, 'GR'),
    (3136,    'https://en.wikipedia.org/wiki/Karpathos',            35.5833, 27.1333, 'GR'),
    (3002137, 'https://en.wikipedia.org/wiki/Ischia',               40.7312, 13.8957, 'IT'),
    (3002145, 'https://en.wikipedia.org/wiki/Tremiti_Islands',      42.1167, 15.5000, 'IT'),
    (3002242, 'https://en.wikipedia.org/wiki/Antiparos',            37.0000, 25.0500, 'GR'),
    (3747,    'https://en.wikipedia.org/wiki/Elba',                 42.7800, 10.2750, 'IT'),

    # ── Manual additions — well-known islands missed by search ────────────
    (3016,    'https://en.wikipedia.org/wiki/Djerba',               33.8000, 10.9000, 'TN'),
    (2989,    'https://en.wikipedia.org/wiki/Bra%C4%8D',            43.3167, 16.6333, 'HR'),
    (3152,    'https://en.wikipedia.org/wiki/Kasos',                35.4000, 26.9333, 'GR'),
    (3038,    'https://en.wikipedia.org/wiki/Kefalonia',            38.2333, 20.5667, 'GR'),
    (3007,    'https://en.wikipedia.org/wiki/Kor%C4%8Dula',         42.9600, 17.1350, 'HR'),
    (2971,    'https://en.wikipedia.org/wiki/Pag_(island)',          44.4500, 14.9833, 'HR'),
    (3042,    'https://en.wikipedia.org/wiki/Paxos',                39.2000, 20.1667, 'GR'),
    (2916,    'https://en.wikipedia.org/wiki/Sardinia',             40.0000,  9.0000, 'IT'),
    (3097,    'https://en.wikipedia.org/wiki/Santorini',            36.4000, 25.4333, 'GR'),
    (3283,    'https://en.wikipedia.org/wiki/Sri_Lanka',             7.8731, 80.7718, None),
    (3137,    'https://en.wikipedia.org/wiki/Delos',                37.3958, 25.2694, 'GR'),
    (3138,    'https://en.wikipedia.org/wiki/Symi',                 36.6167, 27.8500, 'GR'),
    (3140,    'https://en.wikipedia.org/wiki/Donousa',              37.1000, 25.7833, 'GR'),
    (3134,    'https://en.wikipedia.org/wiki/Lemnos',               39.9167, 25.2167, 'GR'),
    (3132,    'https://en.wikipedia.org/wiki/Marmara_Island',       40.6000, 27.6000, 'TR'),
    (2867,    'https://en.wikipedia.org/wiki/%C3%8Ele_Saint-Marguerite', 43.5167, 7.0500, 'FR'),
    (2868,    'https://en.wikipedia.org/wiki/%C3%8Ele_Saint-Honor%C3%A9', 43.5175, 7.0503, 'FR'),
    (3507,    'https://en.wikipedia.org/wiki/Djerba',               33.8744, 10.8572, 'TN'),
    (3002090, 'https://en.wikipedia.org/wiki/Gorgona_(island)',      43.4000,  9.9000, 'IT'),
    (2946,    'https://en.wikipedia.org/wiki/Isola_del_Giglio',     42.3600, 10.9033, 'IT'),
    (3049,    'https://en.wikipedia.org/wiki/Ithaca_(island)',       38.4000, 20.6667, 'GR'),
    (3131,    'https://en.wikipedia.org/wiki/Burgaz_Island',        40.8667, 29.0667, 'TR'),
    (3144,    'https://en.wikipedia.org/wiki/Snake_Island_(Black_Sea)', 45.2500, 30.2000, 'UA'),
    (2933,    'https://en.wikipedia.org/wiki/Sant%27Antioco',       39.0667,  8.4500, 'IT'),
    (2987,    'https://en.wikipedia.org/wiki/Vis_(island)',          43.0600, 16.1900, 'HR'),
    (2837,    'https://en.wikipedia.org/wiki/Isle_of_Wight',        50.6938, -1.3040, 'GB'),
    (3029,    'https://en.wikipedia.org/wiki/Salina_(island)',       38.5667, 14.8667, 'IT'),
    (3050,    'https://en.wikipedia.org/wiki/Kalamos_(island)',      38.6167, 20.9333, 'GR'),
    (3002058, 'https://en.wikipedia.org/wiki/Palmarola',            40.9361, 12.8597, 'IT'),
    (3002408, 'https://en.wikipedia.org/wiki/Bahrain',              26.0275, 50.5500, None),
    (3133,    'https://en.wikipedia.org/wiki/Ano_Koufonisi',        36.9333, 25.6167, 'GR'),
    (2987,    'https://en.wikipedia.org/wiki/Vis_(island)',          43.0600, 16.1900, 'HR'),
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
