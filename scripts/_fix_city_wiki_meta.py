"""
Backfill wiki_confidence and wiki_manual for the 169 city entries
applied by _apply_city_wiki.py.  Migration set them all to None/False;
this script corrects them to the known confidence values from the dry-run.
"""
import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, conf, manual)  — all from _apply_city_wiki.py
# conf: 3=exact, 2=cleaned match, 1=uncertain  manual: True if hand-curated
CITY_META = [
    # ── Auto-matched ────────────────────────────────────────────
    (1691, 3, False), (1935, 2, False), (1603, 2, False), (2021, 3, False),
    ( 735, 3, False), (2122, 3, False), (2252, 3, False), (1967, 2, False),
    (2489, 3, False), ( 921, 3, False), (2374, 3, False), (1554, 3, False),
    ( 995, 3, False), ( 784, 3, False), ( 885, 2, False), ( 580, 2, False),
    ( 677, 3, False), ( 941, 3, False), ( 890, 3, False), ( 708, 3, False),
    ( 628, 3, False), ( 635, 3, False), ( 720, 3, False), ( 599, 3, False),
    ( 492, 3, False), ( 871, 3, False), ( 996, 3, False), (1550, 3, False),
    ( 697, 3, False), (2108, 3, False), (1341, 3, False), ( 218, 2, False),
    (1545, 3, False), ( 624, 3, False), (2457, 3, False), (1504, 3, False),
    ( 650, 3, False), (2424, 3, False), ( 489, 3, False), (  60, 3, False),
    (2084, 3, False), (  43, 3, False), ( 249, 2, False), ( 571, 3, False),
    (2150, 3, False), ( 668, 3, False), (1639, 2, False), ( 666, 3, False),
    ( 485, 3, False), ( 689, 3, False), (1488, 3, False), ( 912, 3, False),
    ( 546, 3, False), ( 609, 3, False), (1944, 2, False), (1841, 3, False),
    (2516, 3, False), (2634, 3, False), (2187, 3, False), (1803, 3, False),
    (1776, 2, False), (1730, 3, False), (1184, 3, False), ( 729, 3, False),
    (2118, 3, False), ( 150, 2, False), ( 438, 3, False), ( 458, 3, False),
    (1628, 2, False), (  52, 2, False), ( 551, 3, False), (2501, 3, False),
    (1013, 3, False), ( 673, 3, False), (1420, 3, False), (2191, 3, False),
    ( 530, 3, False), ( 693, 3, False), ( 256, 2, False), (1848, 2, False),
    (1490, 3, False), ( 768, 3, False), (1080, 3, False), ( 730, 3, False),
    ( 840, 3, False), (2100, 3, False), ( 144, 2, False), (1885, 2, False),
    (1499, 3, False), (2236, 3, False), ( 878, 3, False), (1652, 2, False),
    (1784, 2, False), (1926, 2, False), ( 766, 3, False), ( 445, 3, False),
    (1849, 2, False), (2129, 2, False), (2624, 3, False), (1475, 3, False),
    (1268, 3, False), (2421, 3, False), (2390, 3, False), (2204, 3, False),
    ( 468, 3, False), ( 473, 3, False), (2001, 2, False), (2119, 3, False),
    (2366, 3, False), ( 486, 3, False), (1612, 2, False), (1712, 3, False),
    ( 621, 3, False), (1408, 3, False), ( 834, 3, False), (1561, 2, False),
    (2426, 3, False), (1364, 3, False), (1681, 3, False), ( 601, 3, False),
    (2556, 3, False), ( 974, 2, False), (2466, 3, False), (1633, 3, False),
    (1740, 3, False), (1801, 2, False), (1818, 2, False), ( 741, 3, False),
    (2700, 3, False), (1618, 2, False), (1791, 2, False), (2290, 3, False),
    (  65, 2, False), (1657, 2, False), (1609, 3, False), (  93, 3, False),
    (2422, 3, False), (1211, 3, False), ( 647, 3, False), (2080, 3, False),
    (2168, 3, False), (1617, 3, False), ( 342, 3, False), (1646, 2, False),
    ( 594, 3, False), (2642, 3, False), ( 180, 3, False), (2576, 3, False),
    (1306, 3, False), ( 755, 3, False), (1654, 3, False), (2540, 3, False),
    (2396, 3, False), (2934, 3, False), (2188, 3, False), (1104, 3, False),
    ( 924, 3, False), ( 572, 3, False), ( 807, 3, False), (1717, 2, False),
    (1542, 2, False), (1226, 3, False), (2322, 3, False), (2262, 3, False),
    (2000834, 3, False), (2000861, 3, False), (2000862, 3, False), (3001559, 2, False),
    # ── Manual ─────────────────────────────────────────────────
    (1564, 3, True),  # Ptuj — was matched to wrong UK village, hand-corrected
]

updated = 0
for data_id, conf, manual in CITY_META:
    r = recs.get(data_id)
    if r is None:
        print(f'  MISSING {data_id}')
        continue
    if not r.get('wiki_url'):
        print(f'  NO WIKI {data_id}')
        continue
    r['wiki_confidence'] = conf
    r['wiki_manual']     = manual
    updated += 1

print(f'Updated wiki meta for {updated} city records')
tmp = DB_PATH.with_suffix('.tmp')
tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
tmp.replace(DB_PATH)
print(f'Saved -> {DB_PATH.name}')
