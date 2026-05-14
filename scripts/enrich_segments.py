#!/usr/bin/env python3
"""Enrich roman_province/people/region DB entries with tabula segment data."""
import json, sys, io, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(BASE, "public", "data", "review_places_db.json")
with open(path, encoding='utf-8') as f:
    db = json.load(f)

# Data from tabula-peutingeriana.de/list.html?typ=reg and ?typ=gen
SOURCE = [
    # REGIONS / PROVINCES
    {'latin':'ACHAIA','seg':6,'row':'b','col':4},
    {'latin':'AFRICA','seg':4,'row':'c','col':3},
    {'latin':'ALAMANNIA','seg':2,'row':'a','col':4},
    {'latin':'ALBANIA','seg':11,'row':'b','col':1},
    {'latin':'APVLIA','seg':5,'row':'b','col':2},
    {'latin':'AQUITANIA','seg':1,'row':'b','col':5},
    {'latin':'ARABIA','seg':9,'row':'c','col':5},
    {'latin':'ARCADIA','seg':6,'row':'c','col':5},
    {'latin':'ARIACTA','seg':7,'row':'b','col':2},
    {'latin':'ASIA','seg':8,'row':'b','col':2},
    {'latin':'ATRAPATENE','seg':11,'row':'a','col':2},
    {'latin':'BABYLONIA','seg':10,'row':'c','col':4},
    {'latin':'BACTRIANOE','seg':11,'row':'a','col':4},
    {'latin':'BELGICA','seg':1,'row':'a','col':1},
    {'latin':'BITHINIA','seg':8,'row':'a','col':2},
    {'latin':'BRITTIVS','seg':6,'row':'b','col':1},
    {'latin':'BVLINIA','seg':5,'row':'a','col':2},
    {'latin':'CALABRIA','seg':5,'row':'b','col':5},
    {'latin':'CAMPI DESERTI','seg':11,'row':'b','col':1},
    {'latin':'CAPANIA','seg':5,'row':'b','col':1},
    {'latin':'CAPPADOCIA','seg':9,'row':'b','col':1},
    {'latin':'CARIA','seg':9,'row':'b','col':1},
    {'latin':'CASPIANE','seg':11,'row':'a','col':2},
    {'latin':'CASPYRE','seg':11,'row':'b','col':4},
    {'latin':'CERONESOS','seg':7,'row':'b','col':5},
    {'latin':'CILICIA','seg':9,'row':'b','col':3},
    {'latin':'CLENDERITIS','seg':9,'row':'b','col':3},
    {'latin':'COTII REGNVM','seg':2,'row':'b','col':3},
    {'latin':'DALMATIA','seg':5,'row':'a','col':2},
    {'latin':'DAMIRICE','seg':11,'row':'b','col':4},
    {'latin':'DESERTA','seg':10,'row':'c','col':3},
    {'latin':'DESERTVM','seg':10,'row':'c','col':3},
    {'latin':'DIA','seg':3,'row':'c','col':2},
    {'latin':'DIABENE','seg':11,'row':'a','col':2},
    {'latin':'DRANGIANE','seg':11,'row':'b','col':2},
    {'latin':'EGYPTVS','seg':8,'row':'c','col':3},
    {'latin':'AEGYPTUS','seg':8,'row':'c','col':3},
    {'latin':'ETRVRA','seg':4,'row':'b','col':1},
    {'latin':'ETRURIA','seg':4,'row':'b','col':1},
    {'latin':'FRANCIA','seg':1,'row':'a','col':4},
    {'latin':'GALATIA','seg':8,'row':'b','col':3},
    {'latin':'GALLIA COMATA','seg':1,'row':'b','col':3},
    {'latin':'HIBERIA','seg':11,'row':'b','col':1},
    {'latin':'IEPIRVM NOVVM','seg':6,'row':'b','col':3},
    {'latin':'EPIRUS','seg':6,'row':'b','col':3},
    {'latin':'INDIA','seg':11,'row':'b','col':2},
    {'latin':'ISTERIA','seg':4,'row':'a','col':1},
    {'latin':'HISTRIA','seg':4,'row':'a','col':1},
    {'latin':'ITALIA','seg':2,'row':'b','col':5},
    {'latin':'LACONICE','seg':6,'row':'b','col':5},
    {'latin':'LACONIA','seg':6,'row':'b','col':5},
    {'latin':'LIBVRNIA','seg':4,'row':'a','col':1},
    {'latin':'LIBURNIA','seg':4,'row':'a','col':1},
    {'latin':'LIGVRIA','seg':2,'row':'b','col':3},
    {'latin':'LIGURIA','seg':2,'row':'b','col':3},
    {'latin':'LVCCANIA','seg':5,'row':'b','col':5},
    {'latin':'LUCANIA','seg':5,'row':'b','col':5},
    {'latin':'LYCIA','seg':9,'row':'b','col':1},
    {'latin':'MACEDONIA','seg':6,'row':'a','col':3},
    {'latin':'MARDIANE','seg':11,'row':'a','col':1},
    {'latin':'MEDIA','seg':11,'row':'b','col':3},
    {'latin':'MEDIA MAIOR','seg':10,'row':'a','col':4},
    {'latin':'MESOPOTAMIA','seg':10,'row':'b','col':3},
    {'latin':'MOESIA INFERIOR','seg':6,'row':'a','col':2},
    {'latin':'MESIA INFERIOR','seg':6,'row':'a','col':2},
    {'latin':'MOESIA SUPERIOR','seg':5,'row':'a','col':5},
    {'latin':'MESIA SVPERIOR','seg':5,'row':'a','col':5},
    {'latin':'NORICUM','seg':4,'row':'a','col':1},
    {'latin':'NORICO','seg':4,'row':'a','col':1},
    {'latin':'PAFLAGONIA','seg':8,'row':'a','col':5},
    {'latin':'PAPHLAGONIA','seg':8,'row':'a','col':5},
    {'latin':'PALAESTINA','seg':9,'row':'c','col':2},
    {'latin':'PALESTINA','seg':9,'row':'c','col':2},
    {'latin':'PANNONIA INFERIOR','seg':5,'row':'a','col':2},
    {'latin':'PANNONIA SUPERIOR','seg':4,'row':'a','col':3},
    {'latin':'PANNONIA SVPERIOR','seg':4,'row':'a','col':3},
    {'latin':'PARRIA','seg':11,'row':'c','col':1},
    {'latin':'PATAVIA','seg':1,'row':'a','col':1},
    {'latin':'BATAVIA','seg':1,'row':'a','col':1},
    {'latin':'PERSIA','seg':10,'row':'b','col':5},
    {'latin':'PERSIDA','seg':10,'row':'b','col':5},
    {'latin':'SYRIA PHOENIX','seg':9,'row':'c','col':3},
    {'latin':'PHOENIX','seg':9,'row':'c','col':3},
    {'latin':'PHRYGIA','seg':8,'row':'b','col':3},
    {'latin':'PICENUM','seg':4,'row':'b','col':3},
    {'latin':'PICENVM','seg':4,'row':'b','col':3},
    {'latin':'PONTUS','seg':9,'row':'a','col':2},
    {'latin':'PONTVS POLEMONIACVS','seg':9,'row':'a','col':2},
    {'latin':'THRACIA','seg':7,'row':'b','col':2},
    {'latin':'TRHACIA','seg':7,'row':'b','col':2},
    {'latin':'ACHAEA','seg':6,'row':'b','col':4},
    {'latin':'SCYTHIA','seg':11,'row':'c','col':4},
    {'latin':'SCYTIA DYMIRICE','seg':11,'row':'c','col':4},
    # PEOPLES
    {'latin':'ALANI','seg':9,'row':'a','col':3},
    {'latin':'AMAZONES','seg':9,'row':'a','col':5},
    {'latin':'BAGIGETVLI','seg':7,'row':'c','col':2},
    {'latin':'BLASTARNI','seg':8,'row':'a','col':3},
    {'latin':'BOSFORANI','seg':9,'row':'a','col':1},
    {'latin':'BVR','seg':5,'row':'a','col':3},
    {'latin':'CHAMAVI','seg':2,'row':'a','col':1},
    {'latin':'CHACI','seg':2,'row':'a','col':1},
    {'latin':'COLCHI','seg':11,'row':'b','col':2},
    {'latin':'DACPETOPORIANI','seg':8,'row':'a','col':3},
    {'latin':'DAMASCENI','seg':10,'row':'c','col':2},
    {'latin':'DERBICCE','seg':12,'row':'a','col':2},
    {'latin':'ENIOCHI','seg':9,'row':'a','col':3},
    {'latin':'GAETE','seg':8,'row':'a','col':3},
    {'latin':'GAETVLIA','seg':3,'row':'c','col':5},
    {'latin':'GARAMANTES','seg':7,'row':'c','col':4},
    {'latin':'INSVBRES','seg':3,'row':'a','col':5},
    {'latin':'LAZI','seg':9,'row':'a','col':3},
    {'latin':'MARCOMANNI','seg':4,'row':'a','col':3},
    {'latin':'MEDIOMATRICI','seg':3,'row':'a','col':1},
    {'latin':'MEMNOCONES ETHIOPES','seg':8,'row':'c','col':2},
    {'latin':'NABABES','seg':2,'row':'c','col':2},
    {'latin':'PENASTII','seg':8,'row':'b','col':4},
    {'latin':'PENTAPOLITES','seg':8,'row':'c','col':4},
    {'latin':'PSACCANI','seg':9,'row':'a','col':2},
    {'latin':'QVADI','seg':4,'row':'a','col':5},
    {'latin':'QUADI','seg':4,'row':'a','col':5},
    {'latin':'ROXVLANI SARMATE','seg':8,'row':'a','col':5},
    {'latin':'SARMATE VAGI','seg':5,'row':'a','col':5},
    {'latin':'SARMATAE VAGI','seg':5,'row':'a','col':5},
    {'latin':'SALENTINI','seg':6,'row':'b','col':5},
    {'latin':'SYRTITES','seg':8,'row':'c','col':2},
    {'latin':'TREVERI','seg':3,'row':'a','col':1},
    {'latin':'VANDVLI','seg':4,'row':'a','col':3},
    {'latin':'VANDALI','seg':4,'row':'a','col':3},
    {'latin':'VENADI SARMATAE','seg':8,'row':'a','col':1},
    {'latin':'VENEDI','seg':8,'row':'a','col':4},
    {'latin':'VENETI','seg':2,'row':'a','col':2},
    {'latin':'AMAXOBII SARMATE','seg':7,'row':'a','col':2},
    {'latin':'LVPIONES SARMATE','seg':7,'row':'a','col':4},
    {'latin':'SASONE SARMATE','seg':10,'row':'a','col':5},
    {'latin':'SARMATE','seg':7,'row':'a','col':2},
]

def norm(s):
    s = (s or '').upper().strip()
    # Remove PROVINCIA, PROVINCE prefix
    s = re.sub(r'^PROVINCIA\s+', '', s)
    s = re.sub(r'[^A-Z0-9 ]', '', s)
    return re.sub(r'\s+', ' ', s).strip()

src_map = {}
for e in SOURCE:
    src_map[norm(e['latin'])] = e

updated = 0
no_match = []
for r in db['records']:
    if r.get('type') not in ('roman_province', 'people', 'region', 'modern_state'):
        continue
    if r.get('tabula_segment'):
        continue  # already has segment
    key = norm(r.get('latin_std') or r.get('latin') or '')
    match = src_map.get(key)
    if not match:
        for k, e in src_map.items():
            if k and key and (k in key or key in k) and len(min(k, key, key=len)) > 3:
                match = e
                break
    if match:
        r['tabula_segment'] = match['seg']
        r['tabula_row'] = match['row']
        r['tabula_col'] = match['col']
        r['grid_row'] = match['row']
        r['grid_col'] = match['col']
        r['tabula_location'] = f'Seg {match["seg"]} {match["row"]}{match["col"]}'
        print(f'  OK  {r.get("latin","")[:38]:38} -> Seg {match["seg"]} {match["row"]}{match["col"]}')
        updated += 1
    else:
        no_match.append(r.get('latin','')[:50])

print(f'\nUpdated: {updated}')
if no_match:
    print(f'No match ({len(no_match)}):')
    for n in no_match:
        print(f'  - {n}')

tmp = path + '.tmp'
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(db, f, ensure_ascii=False, indent=2)
os.replace(tmp, path)
print('Saved.')
