import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, lat, lng, country)
# lat/lng written only if record has no coordinates yet
# country always written (corrects bbox mistakes)
#
# REJECTED (false positives):
#   1947 Hinog → Hinogawa Dam (Japan)
#   2380 Haleb → Halebidu (India, not Aleppo)
#    149 Kalaa-Kebira → Kalaa at wrong coords in Algeria (conf=1)
#    300 Lebda → Lebda in Burkina Faso (not Libya)
#   1564 Pettau → Pettaugh village UK (not Ptuj) → manual add below
#   1951 Igliţa → Igli in Morocco (not Romania)
ENTRIES = [
    # ── Auto-matched (with corrected countries) ──────────────────────────
    (1691,  'https://fr.wikipedia.org/wiki/Otinovci',                         43.9789,  17.3072, 'BA'),
    (1935,  'https://en.wikipedia.org/wiki/Svishtov',                         43.6167,  25.3500, 'BG'),
    (1603,  'https://en.wikipedia.org/wiki/Pristava_pri_Trebnjem',            45.9089,  14.9981, 'SI'),
    (2021,  'https://en.wikipedia.org/wiki/Enez',                             40.7222,  26.0833, 'TR'),  # GR→TR
    ( 735,  'https://en.wikipedia.org/wiki/Agen',                             44.2049,   0.6212, 'FR'),
    (2122,  'https://en.wikipedia.org/wiki/Amasya',                           40.6500,  35.8331, 'TR'),
    (2252,  'https://en.wikipedia.org/wiki/Amasya',                           40.6500,  35.8331, 'TR'),
    (1967,  'https://en.wikipedia.org/wiki/Pomorie',                          42.5683,  27.6167, 'BG'),
    (2489,  'https://en.wikipedia.org/wiki/Adilcevaz',                        38.8058,  42.7469, 'TR'),
    ( 921,  'https://en.wikipedia.org/wiki/Langres',                          47.8633,   5.3339, 'FR'),
    (2374,  'https://fr.wikipedia.org/wiki/Antakya',                          36.2000,  36.1700, 'TR'),  # SY→TR
    (1554,  'https://en.wikipedia.org/wiki/Budapest',                         47.4925,  19.0514, 'HU'),
    ( 995,  'https://it.wikipedia.org/wiki/Arbon_(Svizzera)',                 47.5167,   9.4333, 'CH'),
    ( 784,  'https://en.wikipedia.org/wiki/Arles',                            43.6767,   4.6278, 'FR'),
    ( 885,  'https://en.wikipedia.org/wiki/Strasbourg',                       48.5833,   7.7458, 'FR'),  # DE→FR
    ( 580,  'https://de.wikipedia.org/wiki/Tongern',                          50.7808,   5.4647, 'BE'),
    ( 677,  'https://en.wikipedia.org/wiki/Bourges',                          47.0844,   2.3964, 'FR'),
    ( 941,  'https://en.wikipedia.org/wiki/Avenches',                         46.8833,   7.0333, 'CH'),
    ( 890,  'https://en.wikipedia.org/wiki/Augst',                            47.5333,   7.7167, 'CH'),
    ( 708,  'https://en.wikipedia.org/wiki/Limoges',                          45.8353,   1.2625, 'FR'),
    ( 628,  'https://en.wikipedia.org/wiki/Chartres',                         48.4560,   1.4840, 'FR'),
    ( 635,  'https://en.wikipedia.org/wiki/Troyes',                           48.2997,   4.0792, 'FR'),
    ( 720,  'https://en.wikipedia.org/wiki/Clermont-Ferrand',                 45.7831,   3.0824, 'FR'),
    ( 599,  'https://en.wikipedia.org/wiki/Soissons',                         49.3817,   3.3236, 'FR'),
    ( 492,  'https://en.wikipedia.org/wiki/Beirut',                           33.8981,  35.5058, 'LB'),
    ( 871,  'https://en.wikipedia.org/wiki/Bonn',                             50.7353,   7.1022, 'DE'),
    ( 996,  'https://en.wikipedia.org/wiki/Bregenz',                          47.5050,   9.7492, 'AT'),  # CH→AT
    (1550,  'https://en.wikipedia.org/wiki/Sz%C5%91ny',                       47.7333,  18.1667, 'HU'),  # SK→HU
    ( 697,  'https://en.wikipedia.org/wiki/Bordeaux',                         44.8400,  -0.5800, 'FR'),
    (2108,  'https://en.wikipedia.org/wiki/Kad%C4%B1k%C3%B6y',               40.9934,  29.0374, 'TR'),  # GR→TR
    (1341,  'https://en.wikipedia.org/wiki/Canosa_di_Puglia',                 41.2167,  16.0667, 'IT'),
    ( 218,  'https://en.wikipedia.org/wiki/Gafsa',                            34.4225,   8.7842, 'TN'),
    (1545,  'https://it.wikipedia.org/wiki/Bad_Deutsch-Altenburg',            48.1333,  16.9000, 'AT'),  # SK→AT
    ( 624,  'https://en.wikipedia.org/wiki/Beauvais',                         49.4303,   2.0952, 'FR'),
    (2457,  'https://en.wikipedia.org/wiki/Kaspi',                            41.9250,  44.4222, 'GE'),
    (1504,  'https://en.wikipedia.org/wiki/Catania',                          37.5000,  15.0903, 'IT'),
    ( 650,  'https://fr.wikipedia.org/wiki/Orl%C3%A9ans',                     47.9025,   1.9090, 'FR'),
    (2424,  'https://en.wikipedia.org/wiki/Kyrenia',                          35.3403,  33.3192, 'CY'),
    ( 489,  'https://en.wikipedia.org/wiki/Banias',                           33.2486,  35.6944, 'SY'),  # LB→SY (Golan Hts)
    (  60,  'https://fr.wikipedia.org/wiki/Carthage',                         36.8580,  10.3309, 'TN'),
    (2084,  'https://de.wikipedia.org/wiki/%C3%9Csk%C3%BCdar',               41.0167,  29.0167, 'TR'),  # GR→TR
    (  43,  'https://de.wikipedia.org/wiki/Constantine',                      36.3650,   6.6147, 'DZ'),
    ( 249,  'https://en.wikipedia.org/wiki/Kelibia',                          36.8500,  11.1000, 'TN'),
    ( 571,  'https://en.wikipedia.org/wiki/Xanten',                           51.6622,   6.4539, 'DE'),  # NL→DE
    (2150,  'https://en.wikipedia.org/wiki/Aksaray',                          38.3742,  34.0289, 'TR'),
    ( 668,  'https://en.wikipedia.org/wiki/Rennes',                           48.1147,  -1.6794, 'FR'),
    (1639,  'https://en.wikipedia.org/wiki/Sotin',                            45.2950,  19.0970, 'RS'),
    ( 666,  'https://en.wikipedia.org/wiki/Coutances',                        49.0500,  -1.4400, 'FR'),
    ( 485,  'https://de.wikipedia.org/wiki/Damaskus',                         33.5097,  36.3092, 'SY'),  # LB→SY
    ( 689,  'https://en.wikipedia.org/wiki/Vannes',                           47.6559,  -2.7603, 'FR'),
    (1488,  'https://en.wikipedia.org/wiki/Trapani',                          38.0175,  12.5150, 'IT'),
    ( 912,  'https://en.wikipedia.org/wiki/Metz',                             49.1203,   6.1778, 'FR'),  # DE→FR
    ( 546,  'https://en.wikipedia.org/wiki/Canterbury',                       51.2800,   1.0800, 'GB'),
    ( 609,  'https://en.wikipedia.org/wiki/Reims',                            49.2628,   4.0347, 'FR'),
    (1944,  'https://en.wikipedia.org/wiki/Silistra',                         44.1172,  27.2606, 'BG'),
    (1841,  'https://en.wikipedia.org/wiki/Durr%C3%ABs',                      41.3133,  19.4458, 'AL'),
    (2516,  'https://en.wikipedia.org/wiki/Hamadan',                          34.7983,  48.5147, 'IR'),  # IQ→IR
    (2634,  'https://en.wikipedia.org/wiki/Urfa',                             37.1583,  38.7917, 'TR'),  # SY→TR
    (2187,  'https://en.wikipedia.org/wiki/Sel%C3%A7uk',                      37.9500,  27.3667, 'TR'),  # GR→TR
    (1803,  'https://en.wikipedia.org/wiki/Cavtat',                           42.5794,  18.2208, 'HR'),  # BA→HR
    (1776,  'https://de.wikipedia.org/wiki/Gigen',                            43.7000,  24.4833, 'BG'),
    (1730,  'https://fr.wikipedia.org/wiki/Veliki_Gradac',                    45.2836,  16.2617, 'HR'),
    (1184,  'https://en.wikipedia.org/wiki/Fermo',                            43.1608,  13.7158, 'IT'),  # HR→IT
    ( 729,  'https://en.wikipedia.org/wiki/Feurs',                            45.7417,   4.2267, 'FR'),
    (2118,  'https://en.wikipedia.org/wiki/%C3%87ank%C4%B1r%C4%B1',          40.5986,  33.6192, 'TR'),
    ( 150,  'https://en.wikipedia.org/wiki/Sousse',                           35.8333,  10.6333, 'TN'),
    ( 438,  'https://en.wikipedia.org/wiki/Jerusalem',                        31.7789,  35.2256, 'IL'),
    ( 458,  'https://en.wikipedia.org/wiki/Jericho',                          31.8561,  35.4600, 'IL'),
    (1628,  'https://en.wikipedia.org/wiki/Zadar',                            44.1142,  15.2275, 'HR'),
    (  52,  'https://en.wikipedia.org/wiki/Bizerte',                          37.2778,   9.8639, 'TN'),
    ( 551,  'https://en.wikipedia.org/wiki/Exeter',                           50.7256,  -3.5269, 'GB'),  # FR→GB
    (2501,  'https://en.wikipedia.org/wiki/Patnos',                           39.2358,  42.8686, 'TR'),
    (1013,  'https://en.wikipedia.org/wiki/Salzburg',                         47.8000,  13.0450, 'AT'),
    ( 673,  'https://en.wikipedia.org/wiki/Angers',                           47.4736,  -0.5542, 'FR'),
    (1420,  'https://en.wikipedia.org/wiki/Capo_Colonna',                     39.0294,  17.2050, 'IT'),
    (2191,  'https://en.wikipedia.org/wiki/Lapseki',                          40.3439,  26.6836, 'TR'),  # GR→TR
    ( 530,  'https://en.wikipedia.org/wiki/Latakia',                          35.5200,  35.7781, 'SY'),
    ( 693,  'https://en.wikipedia.org/wiki/Poitiers',                         46.5800,   0.3400, 'FR'),
    ( 256,  'https://fr.wikipedia.org/wiki/Lamta',                            35.6754,  10.8807, 'TN'),
    (1848,  'https://fr.wikipedia.org/wiki/Ohrid',                            41.1172,  20.8020, 'MK'),
    (1490,  'https://en.wikipedia.org/wiki/Marsala',                          37.7981,  12.4342, 'IT'),
    ( 768,  'https://en.wikipedia.org/wiki/Saint-Bertrand-de-Comminges',      43.0283,   0.5716, 'FR'),  # ES→FR
    (1080,  'https://en.wikipedia.org/wiki/Lucca',                            43.8417,  10.5028, 'IT'),
    ( 730,  'https://en.wikipedia.org/wiki/Lyon',                             45.7675,   4.8350, 'FR'),
    ( 840,  'https://en.wikipedia.org/wiki/Marseille',                        43.2964,   5.3700, 'FR'),
    (2100,  'https://en.wikipedia.org/wiki/Amasra',                           41.7494,  32.3864, 'TR'),
    ( 144,  'https://fr.wikipedia.org/wiki/Rad%C3%A8s',                       36.7600,  10.2800, 'TN'),
    (1885,  'https://en.wikipedia.org/wiki/Megara',                           37.9964,  23.3444, 'GR'),
    (1499,  'https://en.wikipedia.org/wiki/Messina',                          38.1936,  15.5542, 'IT'),
    (2236,  'https://it.wikipedia.org/wiki/Samsun',                           41.2903,  36.3336, 'TR'),
    ( 878,  'https://en.wikipedia.org/wiki/Mainz',                            49.9994,   8.2736, 'DE'),
    (1652,  'https://en.wikipedia.org/wiki/Osijek',                           45.5556,  18.6944, 'HR'),
    (1784,  'https://en.wikipedia.org/wiki/Ni%C5%A1',                         43.3208,  21.8958, 'RS'),
    (1926,  'https://fr.wikipedia.org/wiki/Cluj-Napoca',                      46.7689,  23.5907, 'RO'),
    ( 766,  'https://en.wikipedia.org/wiki/Narbonne',                         43.1836,   3.0042, 'FR'),  # ES→FR
    ( 445,  'https://en.wikipedia.org/wiki/Nablus',                           32.2222,  35.2611, 'IL'),
    (1849,  'https://de.wikipedia.org/wiki/Capari',                           41.0558,  21.1781, 'MK'),
    (2129,  'https://en.wikipedia.org/wiki/%C4%B0znik',                       40.4292,  29.7211, 'TR'),
    (2624,  'https://de.wikipedia.org/wiki/Nusaybin',                         37.0786,  41.2181, 'TR'),  # SY→TR
    (1475,  'https://en.wikipedia.org/wiki/Torre_Annunziata',                 40.7500,  14.4500, 'IT'),
    (1268,  'https://en.wikipedia.org/wiki/Pescara',                          42.4639,  14.2142, 'IT'),  # HR→IT
    (2421,  'https://en.wikipedia.org/wiki/Paphos',                           34.7667,  32.4167, 'CY'),
    (2390,  'https://en.wikipedia.org/wiki/Gelemi%C5%9F%2C_Ka%C5%9F',        36.2833,  29.3167, 'TR'),  # GR→TR
    (2204,  'https://en.wikipedia.org/wiki/Bergama',                          39.1167,  27.1833, 'TR'),  # GR→TR
    ( 468,  'https://en.wikipedia.org/wiki/Wadi_Musa',                        30.3200,  35.4783, 'JO'),  # IL→JO
    ( 473,  'https://en.wikipedia.org/wiki/Amman',                            31.9497,  35.9328, 'JO'),
    (2001,  'https://it.wikipedia.org/wiki/Plovdiv',                          42.1421,  24.7415, 'BG'),
    (2119,  'https://de.wikipedia.org/wiki/Ta%C5%9Fk%C3%B6pr%C3%BC',         41.5097,  34.2142, 'TR'),
    (2366,  'https://en.wikipedia.org/wiki/Mersin',                           36.7944,  34.6272, 'TR'),
    ( 486,  'https://de.wikipedia.org/wiki/Akkon',                            32.9211,  35.0686, 'IL'),
    (1612,  'https://en.wikipedia.org/wiki/Koper',                            45.5500,  13.7333, 'SI'),
    (1712,  'https://en.wikipedia.org/wiki/Trogir',                           43.5169,  16.2514, 'HR'),  # BA→HR
    ( 621,  'https://en.wikipedia.org/wiki/Rouen',                            49.4428,   1.0886, 'FR'),
    (1408,  'https://en.wikipedia.org/wiki/Reggio_Calabria',                  38.1114,  15.6619, 'IT'),
    ( 834,  'https://en.wikipedia.org/wiki/Riez',                             43.8189,   6.0936, 'FR'),
    (1561,  'https://en.wikipedia.org/wiki/Szombathely',                      47.2351,  16.6219, 'HU'),
    (2426,  'https://en.wikipedia.org/wiki/Famagusta',                        35.1250,  33.9417, 'CY'),
    (1364,  'https://en.wikipedia.org/wiki/Gulf_of_Salerno',                  40.5167,  14.7000, 'IT'),
    (1681,  'https://de.wikipedia.org/wiki/Solin',                            43.5317,  16.4949, 'HR'),  # BA→HR
    ( 601,  'https://fr.wikipedia.org/wiki/Amiens',                           49.8943,   2.2957, 'FR'),
    (2556,  'https://en.wikipedia.org/wiki/Samsat',                           37.5794,  38.4814, 'TR'),
    ( 974,  'https://en.wikipedia.org/wiki/Rottenburg_am_Neckar',             48.4772,   8.9344, 'DE'),
    (2466,  'https://en.wikipedia.org/wiki/Ordubad',                          38.9081,  46.0278, 'AZ'),  # AM→AZ
    (1633,  'https://de.wikipedia.org/wiki/Skradin',                          43.8167,  15.9222, 'HR'),  # BA→HR
    (1740,  'https://fr.wikipedia.org/wiki/Sarmizegetusa',                    45.6225,  23.3100, 'RO'),
    (1801,  'https://de.wikipedia.org/wiki/Shkodra',                          42.0681,  19.5119, 'AL'),  # ME→AL
    (1818,  'https://en.wikipedia.org/wiki/Skopje',                           41.9961,  21.4317, 'MK'),  # XK→MK
    ( 741,  'https://en.wikipedia.org/wiki/Rodez',                            44.3506,   2.5750, 'FR'),
    (2700,  'https://de.wikipedia.org/wiki/Bagdad',                           33.3333,  44.3833, 'IQ'),
    (1618,  'https://en.wikipedia.org/wiki/Senj',                             44.9901,  14.9030, 'HR'),
    (1791,  'https://en.wikipedia.org/wiki/Sofia',                            42.7000,  23.3300, 'BG'),
    (2290,  'https://en.wikipedia.org/wiki/Sivas',                            39.7506,  37.0150, 'TR'),
    (  65,  'https://en.wikipedia.org/wiki/Chemtou',                          36.4919,   8.5761, 'TN'),
    (1657,  'https://de.wikipedia.org/wiki/Sremska_Mitrovica',                44.9797,  19.6097, 'RS'),  # BA→RS
    (1609,  'https://en.wikipedia.org/wiki/Sisak',                            45.4872,  16.3761, 'HR'),  # SI→HR
    (  93,  'https://en.wikipedia.org/wiki/S%C3%A9tif',                       36.1900,   5.4100, 'DZ'),
    (2422,  'https://en.wikipedia.org/wiki/Karavostasi',                      35.1364,  32.8339, 'CY'),
    (1211,  'https://en.wikipedia.org/wiki/Spoleto',                          42.7344,  12.7385, 'IT'),
    ( 647,  'https://de.wikipedia.org/wiki/Le_Mans',                          48.0042,   0.1969, 'FR'),
    (2080,  'https://en.wikipedia.org/wiki/Galata',                           41.0228,  28.9736, 'TR'),  # GR→TR
    (2168,  'https://fr.wikipedia.org/wiki/%C5%9Euhut',                       38.5300,  30.5300, 'TR'),
    (1617,  'https://de.wikipedia.org/wiki/Trsat',                            45.3311,  14.4572, 'HR'),
    ( 342,  'https://en.wikipedia.org/wiki/Tocra',                            32.5322,  20.5722, 'LY'),
    (1646,  'https://de.wikipedia.org/wiki/Zemun',                            44.8453,  20.4103, 'RS'),
    ( 594,  'https://en.wikipedia.org/wiki/Th%C3%A9rouanne',                  50.6375,   2.2597, 'FR'),
    (2642,  'https://en.wikipedia.org/wiki/Harran',                           36.8708,  39.0250, 'TR'),  # SY→TR
    ( 180,  'https://en.wikipedia.org/wiki/T%C3%A9bessa',                     35.4000,   8.1167, 'DZ'),  # TN→DZ
    (2576,  'https://en.wikipedia.org/wiki/Kilis',                            36.7167,  37.1167, 'TR'),  # SY→TR
    (1306,  'https://it.wikipedia.org/wiki/Tivoli',                           41.9667,  12.8000, 'IT'),
    ( 755,  'https://en.wikipedia.org/wiki/Toulouse',                         43.6045,   1.4440, 'FR'),  # ES→FR
    (1654,  'https://en.wikipedia.org/wiki/Vinkovci',                         45.2911,  18.8011, 'HR'),
    (2540,  'https://en.wikipedia.org/wiki/Diyarbak%C4%B1r',                  37.9100,  40.2400, 'TR'),
    (2396,  'https://en.wikipedia.org/wiki/Trabzon',                          41.0050,  39.7225, 'TR'),
    (2934,  'https://en.wikipedia.org/wiki/Porto_Torres',                     40.8333,   8.4000, 'IT'),
    (2188,  'https://en.wikipedia.org/wiki/Akhisar',                          38.9239,  27.8400, 'TR'),  # GR→TR
    (1104,  'https://en.wikipedia.org/wiki/Volterra',                         43.4000,  10.8667, 'IT'),
    ( 924,  'https://en.wikipedia.org/wiki/Besan%C3%A7on',                    47.2400,   6.0200, 'FR'),  # CH→FR
    ( 572,  'https://en.wikipedia.org/wiki/Xanten',                           51.6622,   6.4539, 'DE'),  # NL→DE
    ( 807,  'https://de.wikipedia.org/wiki/Vienne',                           45.5258,   4.8747, 'FR'),
    (1717,  'https://en.wikipedia.org/wiki/Kostolac',                         44.7147,  21.1700, 'RS'),
    (1542,  'https://en.wikipedia.org/wiki/Vienna',                           48.2083,  16.3725, 'AT'),  # HU→AT
    (1226,  'https://de.wikipedia.org/wiki/Bolsena',                          42.6447,  11.9858, 'IT'),
    (2322,  'https://en.wikipedia.org/wiki/Konya',                            37.8744,  32.4931, 'TR'),
    (2262,  'https://en.wikipedia.org/wiki/Zile',                             40.3000,  35.8833, 'TR'),
    (2000834, 'https://en.wikipedia.org/wiki/Termini_Imerese',                37.9872,  13.6961, 'IT'),
    (2000861, 'https://it.wikipedia.org/wiki/Avrolles',                       48.0036,   3.6833, 'FR'),
    (2000862, 'https://en.wikipedia.org/wiki/Gemlik',                         40.4317,  29.1561, 'TR'),  # GR→TR
    (3001559, 'https://en.wikipedia.org/wiki/Manbij',                         36.5275,  37.9553, 'SY'),

    # ── Manual additions (automated search failed) ────────────────────────
    # 1564 PETAVIONE/Pettau → Ptuj (Slovenia); search returned Pettaugh UK village
    (1564,  'https://en.wikipedia.org/wiki/Ptuj',                             46.4200,  15.8700, 'SI'),
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
    if country:
        r['country'] = country
    saved += 1
    print(f'  OK  {data_id}  {(r.get("latin_std") or r.get("latin",""))[:35]}')

print(f'\nApplied {saved} wiki_url entries')
tmp = DB_PATH.with_suffix('.tmp')
tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
tmp.replace(DB_PATH)
print(f'Saved -> {DB_PATH.name}')
