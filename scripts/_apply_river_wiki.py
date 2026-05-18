import sys, json
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'public/data/review_places_db.json'
db = json.loads(DB_PATH.read_text(encoding='utf-8'))
recs = {r['data_id']: r for r in db['records']}

# (data_id, wiki_url, country_override)
# Only sets wiki_url; country only applied if missing or wrong.

ENTRIES = [
    # ── Vetted good matches from dry run ──────────────────────────────────
    (1119,    'https://en.wikipedia.org/wiki/Albegna',                          None),
    (1248,    'https://en.wikipedia.org/wiki/Fiora_(river)',                     None),
    (1361,    'https://en.wikipedia.org/wiki/Calore_Irpino',                    None),
    (1206,    'https://it.wikipedia.org/wiki/Farfa',                            None),
    (1844,    'https://en.wikipedia.org/wiki/Shkumbin',                         None),
    (2093,    'https://de.wikipedia.org/wiki/Melen_%C3%87ay%C4%B1',            None),
    (1467,    'https://it.wikipedia.org/wiki/Savone',                           None),
    (2092,    'https://en.wikipedia.org/wiki/Sakarya_River',                    None),
    (1586,    'https://en.wikipedia.org/wiki/Sava',                             None),
    (1112,    'https://it.wikipedia.org/wiki/Ombrone',                          None),
    (1116,    'https://en.wikipedia.org/wiki/Ombrone',                          None),
    (3346,    'https://en.wikipedia.org/wiki/Danube',                           None),
    (3428,    'https://en.wikipedia.org/wiki/Some%C8%99ul_Mic',                 None),
    (3430,    'https://en.wikipedia.org/wiki/Some%C8%99',                       None),
    (3293,    'https://en.wikipedia.org/wiki/River_Thames',                     None),
    (3375,    'https://en.wikipedia.org/wiki/Tronto',                           'IT'),
    (3391,    'https://en.wikipedia.org/wiki/Garigliano',                       None),
    (3297,    'https://en.wikipedia.org/wiki/Seine',                            None),
    (3438,    'https://en.wikipedia.org/wiki/Maritsa',                          None),
    (3432,    'https://en.wikipedia.org/wiki/Daugava',                          'LV'),
    (3434,    'https://en.wikipedia.org/wiki/Dnieper',                          None),
    (3416,    'https://en.wikipedia.org/wiki/Evrotas_(river)',                  None),
    (3417,    'https://en.wikipedia.org/wiki/Pamisos_(river)',                  None),
    (3372,    'https://en.wikipedia.org/wiki/Tenna_(river)',                    None),
    (3361,    'https://en.wikipedia.org/wiki/Sava',                             None),
    (3328,    'https://en.wikipedia.org/wiki/Lambro',                           None),
    (3303,    'https://en.wikipedia.org/wiki/Sa%C3%B4ne',                       None),
    (3387,    'https://en.wikipedia.org/wiki/Ofanto',                           None),
    (3377,    'https://en.wikipedia.org/wiki/Medjerda_River',                   None),
    (3335,    'https://en.wikipedia.org/wiki/Chiese_(river)',                   None),
    (3381,    'https://it.wikipedia.org/wiki/Tavo',                             None),
    (3350,    'https://en.wikipedia.org/wiki/Vipava_(river)',                   None),
    (3299,    'https://en.wikipedia.org/wiki/Garonne',                          None),
    (3503,    'https://en.wikipedia.org/wiki/Indus_River',                      None),
    (3348,    'https://en.wikipedia.org/wiki/Salzach',                          None),
    (3318,    'https://it.wikipedia.org/wiki/Lavanestro',                       None),
    (3317,    'https://en.wikipedia.org/wiki/Arroscia',                         None),
    (3367,    'https://en.wikipedia.org/wiki/Metauro',                          None),
    (3295,    'https://en.wikipedia.org/wiki/Moselle',                          None),
    (3326,    'https://en.wikipedia.org/wiki/Tidone',                           None),
    (3323,    'https://en.wikipedia.org/wiki/Agogna',                           None),
    (3298,    'https://en.wikipedia.org/wiki/Loire',                            None),
    (3364,    'https://it.wikipedia.org/wiki/Pisciatello',                      None),
    (3445,    'https://en.wikipedia.org/wiki/Sakarya_River',                    None),
    (3415,    'https://en.wikipedia.org/wiki/Simeto',                           None),
    (3324,    'https://en.wikipedia.org/wiki/Ticino_(river)',                   None),
    (3319,    'https://en.wikipedia.org/wiki/Bisagno_(river)',                  None),
    (3491,    'https://en.wikipedia.org/wiki/Tigris',                           None),
    (3321,    'https://en.wikipedia.org/wiki/Cervo_(river)',                    None),
    (3315,    'https://en.wikipedia.org/wiki/V%C3%A9subie',                    None),
    (3477,    'https://en.wikipedia.org/wiki/Jordan_River',                     None),
    (3359,    'https://en.wikipedia.org/wiki/Tiber',                            None),
    (3327,    'https://en.wikipedia.org/wiki/Trebbia',                          None),
    (2000815, 'https://en.wikipedia.org/wiki/Meuse',                            None),
    (2000818, 'https://en.wikipedia.org/wiki/Gediz_River',                     'TR'),
    (2000819, 'https://en.wikipedia.org/wiki/K%C3%BC%C3%A7%C3%BCk_Menderes_River', 'TR'),
    (2000822, 'https://en.wikipedia.org/wiki/Ganges',                           None),
    (2000825, 'https://en.wikipedia.org/wiki/Ganges',                           None),
    (3002491, 'https://en.wikipedia.org/wiki/Adour',                            'FR'),
    (3002495, 'https://en.wikipedia.org/wiki/Durance',                          None),
    (3002500, 'https://en.wikipedia.org/wiki/Dora_Baltea',                      None),
    (3002559, 'https://en.wikipedia.org/wiki/Drava',                            None),
    (3002585, 'https://en.wikipedia.org/wiki/Cervaro_(river)',                  None),
    (3002590, 'https://en.wikipedia.org/wiki/Amaseno_(river)',                  None),
    (3002594, 'https://it.wikipedia.org/wiki/Sarno',                            None),
    (3002595, 'https://en.wikipedia.org/wiki/Sele_(river)',                     None),
    (3002611, 'https://en.wikipedia.org/wiki/Aniene',                           None),
    (3002670, 'https://en.wikipedia.org/wiki/K%C4%B1z%C4%B1l%C4%B1rmak',      None),
    (3002672, 'https://en.wikipedia.org/wiki/Rioni',                            None),
    (3002674, 'https://en.wikipedia.org/wiki/B%C3%BCy%C3%BCk_Menderes_River', 'TR'),
    (3002675, 'https://en.wikipedia.org/wiki/K%C3%B6pr%C3%BC%C3%A7ay',        None),
    (3002676, 'https://en.wikipedia.org/wiki/Manavgat_River',                   None),
    (3002678, 'https://en.wikipedia.org/wiki/Berdan_River',                     None),
    (3002679, 'https://en.wikipedia.org/wiki/Ceyhan_River',                     None),
    (3002684, 'https://en.wikipedia.org/wiki/Zarqa_River',                      None),
    (3002771, 'https://en.wikipedia.org/wiki/Kupa_(river)',                     None),
    (2000868, 'https://en.wikipedia.org/wiki/Ticino_(river)',                   None),
    # correct river articles where wrong articles were matched
    (3370,    'https://en.wikipedia.org/wiki/Potenza_(river)',                  None),
    (3334,    'https://en.wikipedia.org/wiki/Parma_(river)',                    None),
    (3357,    'https://en.wikipedia.org/wiki/Ambra_(river)',                    None),
    # ── Manual: well-known rivers the search missed ───────────────────────
    (3294,    'https://en.wikipedia.org/wiki/Rhine',                            None),
    (3435,    'https://en.wikipedia.org/wiki/Don_(river)',                      None),
    (3431,    'https://en.wikipedia.org/wiki/Dniester',                         None),
    (3002638, 'https://en.wikipedia.org/wiki/Southern_Bug',                     None),
    (3455,    'https://en.wikipedia.org/wiki/Nile',                             None),
    (1877,    'https://en.wikipedia.org/wiki/Achelous_River',                   None),
    (3436,    'https://en.wikipedia.org/wiki/Maritsa',                          None),
    (3002605, 'https://en.wikipedia.org/wiki/Haliacmon',                        None),
    (3002603, 'https://en.wikipedia.org/wiki/Vjosa',                            None),
    (3002604, 'https://en.wikipedia.org/wiki/Drin_(river)',                     None),
    (3002709, 'https://en.wikipedia.org/wiki/Amu_Darya',                        None),
    (3002712, 'https://en.wikipedia.org/wiki/Syr_Darya',                        None),
    (3002642, 'https://en.wikipedia.org/wiki/Tundzha',                          None),
    (2000821, 'https://en.wikipedia.org/wiki/Kura_(Caspian_Sea)',               None),
    (1254,    'https://en.wikipedia.org/wiki/Mignone',                          None),
    (2000826, 'https://en.wikipedia.org/wiki/Leie',                             None),
    (3347,    'https://en.wikipedia.org/wiki/Danube',                           None),
    (1851,    'https://en.wikipedia.org/wiki/Seman_(river)',                    None),
]

saved = 0
for data_id, wiki_url, country in ENTRIES:
    r = recs.get(data_id)
    if r is None:
        print(f'  MISSING {data_id}')
        continue
    if r.get('wiki_url'):
        continue  # already set, skip
    r['wiki_url'] = wiki_url
    if country:
        r['country'] = country
    saved += 1

print(f'Applied {saved} wiki_url entries')
tmp = DB_PATH.with_suffix('.tmp')
tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')
tmp.replace(DB_PATH)
print(f'Saved -> {DB_PATH.name}')
