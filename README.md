# Tabula Peutingeriana — Interactive Map Viewer

The [Tabula Peutingeriana](https://en.wikipedia.org/wiki/Tabula_Peutingeriana) is a medieval copy of an ancient Roman road map (cursus publicus), covering Europe, North Africa, and Asia. This project provides an interactive web viewer with a georeferenced place database.

## Live Viewer

- **[Map Viewer](https://clarityquest.github.io/Ancient-Roadmap-Tabula-Peutingeriana/public/index.html)**
- **[Database Viewer](https://clarityquest.github.io/Ancient-Roadmap-Tabula-Peutingeriana/public/database_viewer.html)**
- **[Calibration Tool](https://clarityquest.github.io/Ancient-Roadmap-Tabula-Peutingeriana/public/calibrate.html)** *(requires local server for saving)*

## Features

- **Dual-map viewer** — switch between the original Miller 1887 facsimile and the Readable Segment IV edition
- **3 800+ place database** sourced from [tabula-peutingeriana.de](https://www.tabula-peutingeriana.de/) (M. Weber) and the Ulm tp-online database
- **Category filters** — Major City, City, Port, Road Station, River, Lake, Island, Spa/Bath, Mountain, People/Tribes, Region, Roman Province, and more
- **Place labels** — modern name inside each marker, Latin name below; toggle on/off
- **Select All / deselect** toggle for all category filters at once
- **Search** by Latin or modern place name
- **Info panel** — click any marker for details and a direct link to the Ulm database entry
- **Calibration tool** (`calibrate.html`) — mark precise pixel positions of places on the Miller map; auto-saves to the database via the local dev server
- **Database viewer** (`database_viewer.html`) — browse, filter, and inspect all records

## Repository Structure

```
public/
  index.html                          Main viewer
  calibrate.html                      Calibration tool (requires local server)
  database_viewer.html                Place database browser
  main.js                             Viewer logic
  styles.css                          Styles
  data/
    review_places_db.json             Primary place database (~3 800 records)
    map_segment_bounds.json           Segment viewport bounds
    places.json                       Derived place positions (SegIV)
    segments.json                     Segment metadata
  Tabula_Peutingeriana_-_Miller.dzi   Miller map DZI descriptor
  Tabula_Peutingeriana_-_Miller_files/ Miller map tiles
  Readable_SegIV.dzi                  Readable SegIV descriptor
  Readable_SegIV_files/               Readable SegIV tiles
  Tabula_Peutingeriana_150dpi_Stitched.dzi  Stitched map descriptor
  Tabula_Peutingeriana_150dpi_Stitched_files/ Stitched map tiles

scripts/
  server.py                           Local dev server (port 8080)
  build_places.py                     Build place position data
  build_review_db.py                  Build/update the place database
  add_missing_places.py               Add lakes, mountains, rivers manually
  add_people.py                       Add peoples/tribes from Weber
  apply_calibration.py                Apply Miller calibration to database
  weber_list.json                     Weber place list reference data
```

## Running Locally

The calibration tool and database saves require a local server (browser security blocks file writes).

```bash
python scripts/server.py
# → http://localhost:8080/
```

The main viewer (`index.html`) and database viewer work directly via file:// or any static server.

## Place Database

`public/data/review_places_db.json` contains ~3 800 records with fields:

| Field | Description |
|---|---|
| `data_id` | Weber/tp-online numeric ID |
| `latin` / `latin_std` | Latin name as on map / standardised |
| `modern_preferred` | Modern place name |
| `type` | Category (see below) |
| `symbol` | Map symbol code (e.g. Aa1, C2) |
| `lat` / `lng` | Geographic coordinates |
| `tabula_segment` / `tabula_row` / `tabula_col` | Grid position on the Tabula |
| `miller_rect_x1/y1/x2/y2` | Calibrated pixel bounds on the Miller image |

**Place types:** `major_city`, `city`, `port`, `road_station`, `river`, `lake`, `island`, `spa`, `mountain`, `people`, `region`, `roman_province`, `modern_state`, `water`

## Calibration Workflow

1. `python scripts/server.py`
2. Open `http://localhost:8080/calibrate.html`
3. Filter by type / segment; navigate to a place
4. Draw a rectangle around the place symbol on the Miller map
5. Accept → position saved automatically to `review_places_db.json`

## Deploy to GitHub Pages

1. Push to `<username>.github.io` repository, branch `main`
2. Go to `Settings > Pages`, set Source to `GitHub Actions`
3. Site publishes automatically at `https://<username>.github.io/`

## Credits

- Map image: K. Miller, 1887 facsimile — public domain, via Wikimedia Commons
- Place data: [tabula-peutingeriana.de](https://www.tabula-peutingeriana.de/) (M. Weber) and [tp-online.ku.de](https://tp-online.ku.de/) (Universität Ulm)
- Viewer: [OpenSeadragon](https://openseadragon.github.io/)
