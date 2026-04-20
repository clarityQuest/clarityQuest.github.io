import json, os, sys, re
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('public/data/review_places_db.json', encoding='utf-8'))
records = data['records']
existing_ids = {r['data_id'] for r in records}

def talbert(ref):
    m = re.match(r'^(\d+)([ABC])(\d+)$', ref.strip())
    if not m: return None, None, None
    return int(m.group(1)) + 1, m.group(2).lower(), int(m.group(3))

entries = [
    (3259, 'ABYOS CYTHAE',         'Abii Scythae',         'Abii Scythae',            '11A3'),
    (2831, 'ACHEI',                'Achei',                'Achaei',                   '9A1'),
    (3127, 'ALANI',                'Alani',                'Alanorum',                 '8A3'),
    (3020, 'AMAXOBII SARMATE',     'Amaxobii Sarmatae',    None,                       '6A2'),
    (3168, 'AMAZONES',             'Amazones',             'Amazonum',                 '8A5'),
    (2816, 'Amyrni',               'Amyrni',               'Kerch region',             '8A2'),
    (3286, 'ANDRE INDI',           'Andre Indi',           None,                       '11B5'),
    (2938, 'ARMA LAVSI',           'Arma Lausi',           None,                       '3A2'),
    (3285, 'AROTE',                'Arote',                None,                       '11A5'),
    (2826, 'Arsoae',               'Arsoae',               None,                       '8A5'),
    (3176, 'ARSOAE',               'Arsoae',               None,                       '9A1'),
    (3126, 'ASPVRGIANI',           'Aspurgiani',           None,                       '8A3'),
    (3036, 'BAGIGETVLI',           'Bagigetuli',           None,                       '6C2'),
    (2895, 'BAGITENNI',            'Bagitenni',            'Vagienni',                 '2B3'),
    (3261, 'BARIANI',              'Bariani',              'Barriana',                 '11A3'),
    (3197, 'Bechiricae',           'Bechiricae',           None,                       '9A3'),
    (3096, 'BETTEGERRI',           'Bettegerri',           None,                       '7B4'),
    (2854, 'BETVRIGES',            'Beturiges',            'Beturiges Cubi',           '1B2'),
    (2873, 'BITVRIGES',            'Bituriges',            'Vivisci',                  '1B5'),
    (3075, 'BLASTARNI',            'Blastarni',            'Bastarnae',                '7A3'),
    (2880, 'BOCONTII',             'Bocontii',             'Vocontii',                 '2B1'),
    (3122, 'BOSFORANI',            'Bosforani',            'Licania Bosforaniae',      '8A1'),
    (2815, 'Bruani',               'Bruani',               'Biruani, Abritani',        '8A2'),
    (3083, 'Brusdorciani',         'Brusdorciani',         'Odrusae Dorciani',         '7B3'),
    (2968, 'BVR',                  'Bur',                  'Burii',                    '4A3'),
    (2877, 'BVRCTVRI',             'Burctori',             None,                       '2A1'),
    (3110, 'BYZANTINI',            'Byzantini',            None,                       '7A5'),
    (2858, 'CADVRCI',              'Cadurcii',             None,                       '1B3'),
    (2864, 'CAMBIOVICENSES',       'Cambiovicenses',       None,                       '1B4'),
    (3124, 'CANNATE',              'Cannate',              None,                       '8A2'),
    (3254, 'CATACE',               'Catace',               None,                       '11B2'),
    (2885, 'CATVRIGES',            'Caturiges',            None,                       '2B2'),
    (2881, 'CAVARES',              'Cavares',              None,                       '2B1'),
    (3169, 'CAVCASI',              'Caucasi',              None,                       '8A5'),
    (3267, 'CEDROSIANI',           'Cedrosiani',           'Gedrosii',                 '11C3'),
    (2898, 'CENOMANI',             'Cenomani',             None,                       '2A4'),
    (2839, 'CHACI',                'Chaci',                'Chauci',                   '1A2'),
    (2842, 'CHAMAVI QVIELPRANCI',  'Chamavi qui et Franci','Franci',                   '1A1'),
    (3175, 'CHIREOE',              'Chireoe',              'Colchia Circeon',          '9A1'),
    (3163, 'CHISOE',               'Chisoe',               None,                       '8A4'),
    (3276, 'CIRRABE INDI',         'Cirrabe Indi',         None,                       '11B4'),
    (3277, 'CIRRIBE INDI',         'Cirribe Indi',         'Zirra',                    '11B4'),
    (3208, 'COLCHI',               'Colchi',               None,                       '10B2'),
    (3185, 'Colopheni',            'Colopheni',            None,                       '9A2'),
    (2838, 'CRHEPSTINI',           'Crhepstini',           None,                       '1A1'),
    (3076, 'DACPETOPORIANI',       'Dacpetoporiani',       None,                       '7A3'),
    (3089, 'DAGAE',                'Dagae',                None,                       '7A4'),
    (3192, 'DAMASCENI',            'Damasceni',            None,                       '9C2'),
    (3248, 'DERBICCE',             'Derbicce',             None,                       '11A2'),
    (3209, 'DIVALI',               'Divali',               'Dibalon',                  '10A2'),
    (3205, 'DIVALIMVSETICE',       'Divalimvsetice',       'Micetiton',                '9A5'),
    (3129, 'ENIOCHI',              'Eniochi',              'Heniochi',                 '8A3'),
    (3260, 'ESSEDONES SCYTHAE',    'Essedones Scythae',    'Issedones Scythae',        '11A3'),
    (3229, 'FLVMEIPERSI',          'Flumeipersi',          None,                       '10B5'),
    (3078, 'GAETE',                'Gaete',                'Getho Githorum',           '7A3'),
    (2913, 'GAETVLI',              'Gaetuli',              'Provincia Gaetulia',       '2C5'),
    (3265, 'GANDARI INDI',         'Gandari Indi',         None,                       '11B3'),
    (3052, 'GARAMANTES',           'Garamantes',           None,                       '6C4'),
    (2869, 'GEDALVSIVM',           'Gedalusium',           None,                       '1C4'),
    (3087, 'Gnadegetuli',          'Gnadegetuli',          None,                       '7C3'),
    (3227, 'HIROAE',               'Hiroae',               'Eroon',                    '10A5'),
    (2850, 'ICAMPENSES',           'Icampenses',           None,                       '1C1'),
    (3268, 'ICHTYOFAGI',           'Ichtyofagi',           None,                       '11C3'),
    (3130, 'ILMERDE',              'Ilmerde',              None,                       '8A3'),
    (2909, 'INSVBRES',             'Insubres',             None,                       '2B5'),
    (2926, 'INSVBRES',             'Insubres',             None,                       '3A1'),
    (2952, 'IVTVGI',               'Iutungi',              'Iuthungi',                 '3A5'),
    (2855, 'LACTORATESAVCI',       'Lactorates Auci',      None,                       '1B2'),
    (3128, 'LAZI',                 'Lazi',                 None,                       '8A3'),
    (2848, 'LVGDVNENSES',          'Lugdunenses',          None,                       '1A1'),
    (3046, 'LVPIONES SARMATE',     'Lupiones Sarmatae',    None,                       '6A4'),
    (3226, 'LVPONES',              'Lupones',              'Lepon',                    '10A5'),
    (3256, 'MADOBALANI',           'Madobalani',           None,                       '11B2'),
    (2833, 'Malichi',              'Malichi',              'Limachi',                  '9A2'),
    (3106, 'MANIRATE',             'Manirate',             None,                       '7A5'),
    (2944, 'MARCOMANNI',           'Marcomanni',           None,                       '3A3'),
    (2977, 'MAVRVCENI',            'Mauruceni',            'Marrucini',                '4B5'),
    (3275, 'MAXERE',               'Maxere',               None,                       '11B4'),
    (2879, 'MEDIOMATRICI',         'Mediomatrici',         None,                       '2A1'),
    (3073, 'MEMNOCONES ETHIOPES',  'Memnocones Ethiopes',  None,                       '7C2'),
    (3119, 'MEOTE',                'Meote',                None,                       '8A1'),
    (2927, 'MESIATES',             'Mesiates',             None,                       '2A5'),
    (2853, 'MVSONIORVM',           'Musoniorum',           None,                       '1C2'),
    (2876, 'MVSVLAMIORVM',         'Musulamiorum',         None,                       '1C5'),
    (2852, 'NABABES',              'Nababes',              None,                       '1C2'),
    (2893, 'NABVRNI',              'Naburni',              None,                       '2B3'),
    (2870, 'NAGMVS',               'Nagmus',               None,                       '1C4'),
    (2894, 'NANTVANI',             'Nantuani',             None,                       '2B3'),
    (3056, 'NATIO SELOR(VM)',       'Natio Selorum',        None,                       '6C5'),
    (3162, 'NERDANI',              'Nerdani',              None,                       '8A4'),
    (3072, 'NESAMONES',            'Nesamones',            'Nasamones',                '7C2'),
    (3088, 'Nigizegetuli',         'Nigizegetuli',         None,                       '7C3'),
    (2863, 'NITIOBRO',             'Nitiobro',             None,                       '1A4'),
    (2875, 'NVMIDARVM',            'Numidarum',            'Provincia Numidiae',       '1C5'),
    (2845, 'Osismi',               'Osismi',               'Osimii',                   '1A2'),
    (3232, 'OTIOS CYTHAE',         'Otios Cythae',         'Otio Scythae',             '11A1'),
    (3217, 'PARALOCAESCYTHAE',     'Paralocea Scythae',    'Paraliton',                '10A4'),
    (2871, 'PARISI',               'Parisi',               None,                       '1A5'),
    (3186, 'PARNACI',              'Parnaci',              None,                       '9A2'),
    (3095, 'PENASTII',             'Penastii',             None,                       '7B4'),
    (3098, 'PENTAPOLITES',         'Pentapolites',         None,                       '7C4'),
    (3177, 'PHRYSTANITE',          'Phrystanite',          None,                       '9A1'),
    (3287, 'PIRATE',               'Pirate',               None,                       '11C5'),
    (3077, 'PITI',                 'Piti',                 None,                       '7A3'),
    (3178, 'PONTICI',              'Pontici',              'Pontus',                   '9A1'),
    (3196, 'POTAMIAE',             'Potamiae',             None,                       '9A3'),
    (3125, 'PSACCANI',             'Psaccani',             None,                       '8A2'),
    (2823, 'Psacccani',            'Psaccani',             None,                       '8A4'),
    (3065, 'PYROGERI',             'Pyrogeri',             None,                       '7B2'),
    (2951, 'QVADI',                'Quadi',                None,                       '3A5'),
    (3257, 'RAVDIANI',             'Ravdiani',             None,                       '11B2'),
    (2891, 'RAVRACI',              'Rauraci',              None,                       '2B3'),
    (2872, 'RERVIGES',             'Reruiges',             None,                       '1A5'),
    (3107, 'ROXVLANI SARMATE',     'Roxulani Sarmatae',    'Roxulanorum',              '7A5'),
    (3234, 'RVMI SCYTHAE',         'Rumi Scythae',         None,                       '11A1'),
    (2859, 'RVTENI',               'Ruteni',               None,                       '1B3'),
    (3233, 'SAGAES CYTHAE',        'Sagaes Cythae',        'Sacens Scython',           '11A1'),
    (3272, 'SAGAE SCYTHAE',        'Sagae Scythae',        None,                       '11A4'),
    (2999, 'SALENTINI',            'Salentini',            None,                       '5B5'),
    (2827, 'Sannigae',             'Sannigae',             None,                       '8A5'),
    (2821, 'SARDETAE',             'Sardetae',             None,                       '8A3'),
    (2976, 'SARMATE VAGI',         'Sarmatae Vagi',        'Sauromatum',               '4A5'),
    (3204, 'SASONE SARMATE',       'Sasone Sarmatae',      'Saxona',                   '9A5'),
    (2886, 'SELTERI',              'Selteri',              'Suelteri',                 '2B2'),
    (2929, 'SENGAVNI',             'Sengauni',             'Ingauni',                  '3B1'),
    (3146, 'Seracoe',              'Seracoe',              'Coroea',                   '8A2'),
    (2805, 'Sorices',              'Sorices',              'Suaricum',                 '8A1'),
    (2834, 'Svani',                'Suani',                'Siania Caucusorum',        '9A2'),
    (3195, 'SVANI SARMATAE',       'Suani Sarmatae',       None,                       '9A3'),
    (3202, 'Suedehiberi',          'Suedehiberi',          'Suevi Hiberi',             '9A4'),
    (3071, 'SYRTITES',             'Syrtites',             None,                       '7C2'),
    (3284, 'TANCHIRE',             'Tanchire',             None,                       '11A5'),
    (2900, 'TAVRIANI',             'Tauriani',             'Taurini',                  '2B4'),
    (3239, 'TOLOMENI',             'Tolomeni',             None,                       '11B1'),
    (2878, 'TREVERI',              'Treveri',              None,                       '2A1'),
    (3230, 'Trogoditi Persi',      'Trogoditi Persi',      None,                       '10B5'),
    (2925, 'TRVMPLI',              'Trumpli',              'Triumpilini',              '3A1'),
    (2949, 'TVSCI',                'Tusci',                'Etrusci',                  '3B2'),
    (2945, 'VANDVLI',              'Vanduli',              'Vandali',                  '3A3'),
    (2840, 'VAPII',                'Vapii',                None,                       '1A2'),
    (2841, 'VARII',                'Varii',                'Attuarii',                 '1A3'),
    (2911, 'VELIATE',              'Veliate',              None,                       '2B5'),
    (3057, 'VENADI SARMATAE',      'Venadi Sarmatae',      None,                       '7A1'),
    (3090, 'VENEDI',               'Venedi',               None,                       '7A4'),
    (2846, 'VENETI',               'Veneti',               None,                       '1A2'),
    (2865, 'VOLCETECTOSI',         'Volcae Tectosages',    'Volcae Tectosages',        '1B4'),
    (3274, 'XATIS SCYTHAE',        'Xatis Scythae',        'Chatae Scythae',           '11A4'),
    (2888, 'ZIMISES',              'Zimises',              None,                       '2C2'),
]

wrong_type_ids = {2938,2926,2952,2944,2951,2929,2925,2949,2945}
fixed = 0
for r in records:
    if r['data_id'] in wrong_type_ids and r['type'] != 'people':
        r['type'] = 'people'
        fixed += 1
        print(f"  fix  {r['data_id']:7} {r['latin_std']}")

added = 0
for did, latin, latin_std, modern, tref in entries:
    if did in existing_ids:
        continue
    seg, row, col = talbert(tref)
    if seg is None:
        print(f"  WARN bad ref {tref} for {latin_std}")
        continue
    records.append({
        'record_id': f'TP:WL:{did}', 'source': 'tabula', 'data_id': did,
        'latin': latin, 'latin_std': latin_std,
        'modern_omnesviae': None, 'modern_tabula': modern, 'modern_preferred': modern,
        'type': 'people', 'symbol': None,
        'lat': None, 'lng': None, 'px': None, 'py': None,
        'province': None, 'country': None, 'region': None,
        'tabula_segment': seg, 'tabula_col': col, 'tabula_row': row,
        'tabula_location': f'Seg {seg} {row}{col}', 'match_status': 'manual_add',
    })
    added += 1

from collections import Counter
types = Counter(r['type'] for r in records)
print(f"\nFixed: {fixed}  Added: {added}  Total people: {types['people']}")
print(f"DB total: {len(records)}")

tmp = 'public/data/review_places_db.json.tmp'
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
os.replace(tmp, 'public/data/review_places_db.json')
print('Saved.')
