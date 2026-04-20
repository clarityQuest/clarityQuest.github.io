"""One-time project cleanup script.

Actions:
  1. Creates archive/ directory structure.
  2. Moves unused files to appropriate archive sub-folders.
  3. Creates a dated backup of review_places_db.json.
  4. Strips 7 internal/legacy columns from review_places_db.json in-place.

Run from the repo root:
  python scripts/cleanup_archive.py
"""

from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Archive destination folders
# ---------------------------------------------------------------------------
ARCHIVE = ROOT / "archive"
DEST_ONETIME = ARCHIVE / "scripts_onetime"
DEST_SCRIPTS_DATA = ARCHIVE / "scripts_data"
DEST_PUBLIC_BAK = ARCHIVE / "public_backup"
DEST_DATA_PIPELINE = ARCHIVE / "data_pipeline"

for d in [DEST_ONETIME, DEST_SCRIPTS_DATA, DEST_PUBLIC_BAK, DEST_DATA_PIPELINE]:
    d.mkdir(parents=True, exist_ok=True)

moved: list[str] = []
skipped: list[str] = []


def move(src: Path, dest_dir: Path) -> None:
    if not src.exists():
        skipped.append(str(src.relative_to(ROOT)))
        return
    dest = dest_dir / src.name
    # Avoid clobbering an existing file in the archive.
    if dest.exists():
        skipped.append(f"{src.relative_to(ROOT)} (already in archive)")
        return
    shutil.move(str(src), str(dest))
    moved.append(f"{src.relative_to(ROOT)} -> archive/{dest_dir.name}/{src.name}")


# ---------------------------------------------------------------------------
# 1. One-time analysis / run scripts
# ---------------------------------------------------------------------------
SCRIPTS = ROOT / "scripts"

ONETIME_SCRIPTS = [
    "analyze_matching.py",
    "analyze_omnesviae.py",
    "analyze_tabula.py",
    "apply_transform.py",         # superseded by apply_transform_v2.py
    "build_seg4_dzi.py",
    "calibrate_positions.py",     # superseded by public/calibrate.html workflow
    "check_dare_pleiades.py",
    "check_sections.py",
    "check_tabula_page.py",
    "compare_river_queries.py",
    "decode_svg_images.py",
    "download_svg.py",
    "extract_svg_abs.py",
    "extract_svg_texts.py",
    "fetch_omnesviae.py",
    "fetch_place_page.py",
    "inspect_tp_js.py",
    "list_candidates.py",
    "run_geocode_sample.py",
    "save_ref_crops.py",
    "save_targeted_crops.py",
    "test_match.py",
    "tmp_sweep_nocandidate.py",
    "tmp_sweep_rivers.py",
]

for name in ONETIME_SCRIPTS:
    move(SCRIPTS / name, DEST_ONETIME)

# ---------------------------------------------------------------------------
# 2. Debug/scratch data files from scripts/
# ---------------------------------------------------------------------------
for p in sorted(SCRIPTS.glob("crop_*.jpg")):
    move(p, DEST_SCRIPTS_DATA)

for p in sorted(SCRIPTS.glob("ref_*.jpg")):
    move(p, DEST_SCRIPTS_DATA)

for p in sorted(SCRIPTS.glob("debug_*.jpg")):
    move(p, DEST_SCRIPTS_DATA)

SCRIPTS_DATA_FILES = [
    "svg_texts_abs.json",
    "geocode_run_summary.json",
    "loc_info_1174.html",
    "tabula_seg4.html",
    "tpplace_1174.html",
]

for name in SCRIPTS_DATA_FILES:
    move(SCRIPTS / name, DEST_SCRIPTS_DATA)

# ---------------------------------------------------------------------------
# 3. Root-level stale data / image files
# ---------------------------------------------------------------------------
ROOT_DATA_FILES = [
    "svg_texts.json",
    "TabulaPeutingeriana.jpg",
    "tp_72dpi_3.jpg",
    "omnesviae.url",
]

for name in ROOT_DATA_FILES:
    move(ROOT / name, DEST_SCRIPTS_DATA)

# ---------------------------------------------------------------------------
# 4. public/ backup/scratch files
# ---------------------------------------------------------------------------
PUBLIC = ROOT / "public"

PUBLIC_BAK_FILES = [
    "index.html.bak",
    "main.js.bak",
    "styles.css.bak",
    "tmp_tpmvs11.jpg",
    "tmp_tpmvsb.jpg",
    "tmp_w_11c5.jpg",
    "tmp_w_bc5.jpg",
    "Tabula_Peutingeriana_-_Miller.jpg",   # DZI tiles already built; .jpg not referenced by active code
]

for name in PUBLIC_BAK_FILES:
    move(PUBLIC / name, DEST_PUBLIC_BAK)

# ---------------------------------------------------------------------------
# 5. Pipeline output artefacts from public/data/
# ---------------------------------------------------------------------------
DATA = PUBLIC / "data"

DATA_PIPELINE_FILES = [
    "geocode_refine_queue.json",
    "geocode_refine_queue_island.json",
    "geocode_refine_queue_lake.json",
    "geocode_refine_queue_port_water.json",
    "geocode_refine_queue_river.json",
    "geocode_refine_queue_river_lake.json",
    "geocode_refine_queue_water_port.json",
    "geocode_sample_summary.json",
    "river_query_compare.json",
    # NOTE: river_lake_remaining_refinement.csv is intentionally NOT moved –
    #       it is referenced by public/database_viewer.html.
]

for name in DATA_PIPELINE_FILES:
    move(DATA / name, DEST_DATA_PIPELINE)

# ---------------------------------------------------------------------------
# 6. Back up review_places_db.json before stripping columns
# ---------------------------------------------------------------------------
DB_PATH = DATA / "review_places_db.json"
today_str = date.today().isoformat().replace("-", "")
DB_BACKUP = DEST_DATA_PIPELINE / f"review_places_db_backup_{today_str}.json"

if DB_PATH.exists() and not DB_BACKUP.exists():
    shutil.copy2(str(DB_PATH), str(DB_BACKUP))
    print(f"[backup] review_places_db.json -> archive/data_pipeline/{DB_BACKUP.name}")
elif DB_BACKUP.exists():
    print(f"[backup] skipped – backup already exists: {DB_BACKUP.name}")
else:
    print("[backup] ERROR: review_places_db.json not found!")

# ---------------------------------------------------------------------------
# 7. Strip 7 internal/legacy fields from review_places_db.json
# ---------------------------------------------------------------------------
FIELDS_TO_REMOVE = {
    "include_reason",          # internal build filter; 3 enum values; not used in any UI code
    "modern_known_tabula",     # internal bool echo of bool(modern_tabula); not used in UI
    "geocoding_query",         # internal geocoding search string; not displayed anywhere
    "geocoding_provider_chain",# internal list; not displayed anywhere
    "geocoding_source",        # redundant with geocoding_provider (newer field that supersedes it)
    "geocoding_display_name",  # legacy orphan – NOT written by current pipeline
    "geocoding_url",           # legacy orphan – NOT written by current pipeline
}

print(f"\n[strip] Loading {DB_PATH.name} …")
with DB_PATH.open("r", encoding="utf-8") as f:
    db = json.load(f)

records = db.get("records", [])
total = len(records)
fields_found: dict[str, int] = {k: 0 for k in FIELDS_TO_REMOVE}

for rec in records:
    for field in FIELDS_TO_REMOVE:
        if field in rec:
            fields_found[field] += 1
            del rec[field]

print(f"[strip] Processed {total} records.")
print("[strip] Fields removed (count = records that contained the field):")
for field, count in sorted(fields_found.items()):
    print(f"         {field}: {count}")

with DB_PATH.open("w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

print(f"[strip] {DB_PATH.name} saved.\n")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"[done] Moved {len(moved)} files:")
for m in moved:
    print(f"     {m}")

if skipped:
    print(f"\n[skip] {len(skipped)} entries skipped (missing or already archived):")
    for s in skipped:
        print(f"       {s}")
