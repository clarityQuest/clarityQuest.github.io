import json, sys, os
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('public/data/review_places_db.json', encoding='utf-8'))
wl   = json.load(open('scripts/weber_list.json', encoding='utf-8'))

db_ids   = {r['data_id'] for r in data['records']}
wl_by_id = {r['weber_id']: r for r in wl if r.get('weber_id')}

# (weber_id, latin, latin_std, type, modern, lat, lng)
entries_from_weber = [
    (940,  'Lacum Losonne',         'Lacus Losannensis',   'lake',     'Lake Geneva (Lac Leman)',    46.45,  6.55),
    (2899, 'Lacus Henus',           'Lacus Henus',         'lake',     None,                         None,   None),
    (3313, 'Lacus Clisius',         'Lacus Clisius',       'lake',     None,                         None,   None),
    (3550, 'Lacus et Mons Ciminus', 'Lacus et Mons Ciminus','lake',    'Lago di Vico',               42.32,  12.17),
    (2992, 'Lac(us) Avernus',       'Lacus Avernus',       'lake',     "Lago d'Averno",              40.85,  14.06),
    (2993, 'Lac(us) Acerusius',     'Lacus Acerusius',     'lake',     'Lago Fusaro',                40.82,  14.06),
    (3565, 'Lacus Tri[tho]n(um)',   'Lacus Tritonium',     'lake',     'Chott el-Djerid (Tunisia)',  33.50,   8.43),
    (3150, 'Lac(us). Asson',        'Lacus Asson',         'lake',     None,                         None,   None),
    (3547, 'Lac(us) Salina(rum)',   'Lacus Salinarum',     'lake',     None,                         None,   None),
    (447,  'Lacus Mori',            'Lacus Mori',          'lake',     None,                         None,   None),
    (3184, 'Lac{us} As[phaltites]', 'Lacus Asphaltites',  'lake',     'Dead Sea',                   31.50,  35.50),
    (3194, 'Lac{(us)} Tib[e]ris',  'Lacus Tiberias',      'lake',     'Sea of Galilee',             32.82,  35.59),
    (1591, 'Aqua Viva',             'Aqua Viva',           'water',    None,                         None,   None),
    (311,  'Di(ss)io Aqua Amara',   'Dissio Aqua Amara',   'water',    None,                         None,   None),
    (1293, 'Mons Imeus',            'Mons Imeus',          'mountain', 'Haemus / Balkan Mountains',  42.80,  25.50),
    (1365, 'Mons Balabo',           'Mons Balabo',         'mountain', None,                         None,   None),
    (3086, 'Boecolen Montes',       'Boecolen Montes',     'mountain', None,                         None,   None),
    (3117, 'Montes Cyrenei',        'Montes Cyrenei',      'mountain', 'Jebel Akhdar (Libya)',       32.50,  21.90),
    (3166, 'Mons Syna',             'Mons Syna',           'mountain', 'Mount Sinai',                28.54,  33.97),
    (3183, 'Mons Oliveti',          'Mons Oliveti',        'mountain', 'Mount of Olives',            31.78,  35.24),
]

# (latin, latin_std, type, modern, lat, lng, seg, row, col)
entries_extra = [
    ('Lacus Brigantinus',  'Lacus Brigantinus',  'lake',     'Lake Constance',        47.65,  9.39,  2, 'a', 5),
    ('Lacus Verbanus',     'Lacus Verbanus',     'lake',     'Lake Maggiore',         45.90,  8.62,  3, 'a', 5),
    ('Lacus Eupilis',      'Lacus Eupilis',      'lake',     'Lake Como',             46.00,  9.26,  3, 'a', 5),
    ('Lacus Meotidis',     'Lacus Meotidis',     'lake',     'Sea of Azov',           47.00, 37.00,  8, 'a', 5),
    ('Lacus Nusaptis',     'Lacus Nusaptis',     'lake',     None,                    None,   None,   8, 'c', 5),
    ('Aquae Populaniae',   'Aquae Populaniae',   'water',    'Acquapendente',         42.74, 11.86,  5, 'b', 4),
    ('Aquae Cutilliae',    'Aquae Cutilliae',    'water',    'Antrodoco (Rieti)',     42.42, 13.08,  5, 'b', 4),
    ('Thermis',            'Thermis',            'water',    None,                    None,   None,   7, 'b', 1),
    ('Mons Feratus',       'Mons Feratus',       'mountain', 'Monti Cimini',          42.39, 12.10,  5, 'b', 4),
    ('Mons Taurus',        'Mons Taurus',        'mountain', 'Taurus Mountains',      37.00, 33.00,  9, 'a', 2),
    ('Mons Parverdes',     'Mons Parverdes',     'mountain', None,                    None,   None,  10, 'b', 5),
    ('Mons Catacas',       'Mons Catacas',       'mountain', None,                    None,   None,  10, 'a', 5),
    ('Mons Daropanisos',   'Mons Daropanisos',   'mountain', 'Hindu Kush',            35.00, 71.00, 12, 'a', 3),
    ('Mons Lymodus',       'Mons Lymodus',       'mountain', None,                    None,   None,  10, 'b', 2),
    ('[Mons Appenninus]',  'Mons Appenninus',    'mountain', 'Apennine Mountains',   44.00, 11.00,  4, 'b', 3),
    ('[Mons Vesuvius]',    'Mons Vesuvius',      'mountain', 'Mount Vesuvius',        40.82, 14.43,  6, 'c', 2),
    ('[Mons Lepinus]',     'Mons Lepinus',       'mountain', 'Monti Lepini',          41.55, 13.06,  5, 'c', 5),
    ('[Mons Massicus]',    'Mons Massicus',      'mountain', 'Monte Massico',         41.22, 13.99,  6, 'b', 3),
    ('[Mons Tifata]',      'Mons Tifata',        'mountain', 'Monte Tifata',          41.08, 14.33,  6, 'c', 1),
    ('[Mons Taburnus]',    'Mons Taburnus',      'mountain', 'Monte Taburno',         41.11, 14.55,  6, 'c', 2),
    ('[Mons Ciminus]',     'Mons Ciminus',       'mountain', 'Monte Cimino',          42.42, 12.14,  5, 'b', 4),
]

next_id = 2000827
added = 0

for weber_id, latin, latin_std, typ, modern, lat, lng in entries_from_weber:
    if weber_id in db_ids:
        print(f'  skip {weber_id} {latin_std}')
        continue
    wl_e = wl_by_id.get(weber_id)
    if not wl_e:
        print(f'  WARN no weber_list for {weber_id} {latin_std}')
        continue
    seg, row, col = wl_e['seg'], wl_e['row'], wl_e['col']
    data['records'].append({
        'record_id': f'TP:WL:{weber_id}', 'source': 'tabula', 'data_id': weber_id,
        'latin': latin, 'latin_std': latin_std,
        'modern_omnesviae': None, 'modern_tabula': modern, 'modern_preferred': modern,
        'type': typ, 'symbol': None,
        'lat': lat, 'lng': lng, 'px': None, 'py': None,
        'province': None, 'country': None, 'region': None,
        'tabula_segment': seg, 'tabula_col': col, 'tabula_row': row,
        'tabula_location': f'Seg {seg} {row}{col}', 'match_status': 'manual_add',
    })
    added += 1
    print(f'  + {typ:10} {latin_std[:35]:35} Seg {seg} {row}{col}  id={weber_id}')

for latin, latin_std, typ, modern, lat, lng, seg, row, col in entries_extra:
    did = next_id; next_id += 1
    data['records'].append({
        'record_id': f'TP:ULM:{did}', 'source': 'tabula', 'data_id': did,
        'latin': latin, 'latin_std': latin_std,
        'modern_omnesviae': None, 'modern_tabula': modern, 'modern_preferred': modern,
        'type': typ, 'symbol': None,
        'lat': lat, 'lng': lng, 'px': None, 'py': None,
        'province': None, 'country': None, 'region': None,
        'tabula_segment': seg, 'tabula_col': col, 'tabula_row': row,
        'tabula_location': f'Seg {seg} {row}{col}', 'match_status': 'manual_add',
    })
    added += 1
    print(f'  + {typ:10} {latin_std[:35]:35} Seg {seg} {row}{col}  id={did}')

from collections import Counter
types = Counter(r['type'] for r in data['records'])
print(f'\nAdded: {added}  Total: {len(data["records"])}')
print('Type counts:', dict(types))

tmp = 'public/data/review_places_db.json.tmp'
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
os.replace(tmp, 'public/data/review_places_db.json')
print('Saved.')
