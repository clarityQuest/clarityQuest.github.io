"""Apply manually researched geocoding corrections to review_places_db.json."""
import json
from datetime import datetime, timezone

TIMESTAMP = datetime.now(timezone.utc).isoformat()

# record_id -> correction dict
# source: 'wikipedia' | 'omnesviae' | 'nominatim'
# For OV records that already have lat/lng from OmnesViae, no lat/lng override needed (they'll keep existing values)
CORRECTIONS = {
    # OV entries: already have lat/lng from OmnesViae; just accept them
    "OV:https://omnesviae.org/#TPPlace940": {
        "source": "omnesviae", "confidence": 1.0,
        "title": "Lausanne / Lake Geneva area (OmnesViae)",
        "url": "https://omnesviae.org/#TPPlace940", "query": "Lacvm Losonne",
    },
    "OV:https://omnesviae.org/#TPPlace1095": {
        "source": "omnesviae", "confidence": 1.0,
        "title": "Fiume Ombrone (OmnesViae)",
        "url": "https://omnesviae.org/#TPPlace1095", "query": "Umbro Flumen",
    },
    "OV:https://omnesviae.org/#TPPlace1112": {
        "source": "omnesviae", "confidence": 1.0,
        "title": "Fiume Ombrone (OmnesViae)",
        "url": "https://omnesviae.org/#TPPlace1112", "query": "Umbro Flumen",
    },
    # TP entries with Wikipedia-sourced coordinates
    "TP:3404": {
        "lat": 39.7236, "lng": 16.5292,
        "source": "wikipedia", "confidence": 1.0,
        "title": "Crati", "url": "https://en.wikipedia.org/wiki/Crati", "query": "Grati",
    },
    "TP:3350": {
        "lat": 45.8990, "lng": 13.5533,
        "source": "wikipedia", "confidence": 1.0,
        "title": "Vipava (river)", "url": "https://en.wikipedia.org/wiki/Vipava_(river)", "query": "Vipava",
    },
    "TP:3322": {
        "lat": 45.0347, "lng": 10.0536,
        "source": "wikipedia", "confidence": 1.0,
        "title": "Arda (Italy)", "url": "https://en.wikipedia.org/wiki/Arda_(Italy)", "query": "Larda",
    },
    "TP:3315": {
        "lat": 43.8597, "lng": 7.1975,
        "source": "wikipedia", "confidence": 1.0,
        "title": "Vesubia / Vesubie river", "url": "https://en.wikipedia.org/wiki/V%C3%A9subie", "query": "Vesubia",
    },
    "TP:3336": {
        "lat": 44.5674, "lng": 11.9637,
        "source": "wikipedia", "confidence": 1.0,
        "title": "Santerno", "url": "https://en.wikipedia.org/wiki/Santerno", "query": "Saterno",
    },
    "TP:3317": {
        "lat": 43.8858, "lng": 8.0372,
        "source": "wikipedia", "confidence": 1.0,
        "title": "Impero (river)", "url": "https://en.wikipedia.org/wiki/Impero_(river)", "query": "Imper",
    },
    "TP:3405": {
        "lat": 43.2343, "lng": 13.7779,
        "source": "wikipedia", "confidence": 1.0,
        "title": "Tenna (river)", "url": "https://en.wikipedia.org/wiki/Tenna_(river)", "query": "San Ippolito",
    },
    "TP:3505": {
        "lat": 44.0635, "lng": 12.5475,
        "source": "wikipedia", "confidence": 1.0,
        "title": "Ausa (river)", "url": "https://en.wikipedia.org/wiki/Ausa_(river)", "query": "Aunes",
    },
    # Malea: accept the nominatim candidate (Canale Malea, conf 0.897)
    "TP:3310": {
        "lat": 44.8380, "lng": 12.0987,
        "source": "nominatim", "confidence": 0.897,
        "title": "Canale Malea",
        "url": "https://www.openstreetmap.org/?mlat=44.8380167&mlon=12.09865",
        "query": "Malea",
    },
    # Lavenza / Aventia: Avenza area near Carrara (Carrione river)
    "TP:3354": {
        "lat": 44.046, "lng": 10.065,
        "source": "nominatim", "confidence": 0.5,
        "title": "Avenza/Carrara area (near Carrione)",
        "url": "https://www.openstreetmap.org/?mlat=44.046&mlon=10.065",
        "query": "Lavenza",
    },
    # Aspido / Aspia: Aspio river, Marche
    "TP:3369": {
        "lat": 43.5406, "lng": 13.4454,
        "source": "wikipedia", "confidence": 1.0,
        "title": "Aspio (fiume)",
        "url": "https://it.wikipedia.org/wiki/Aspio_(fiume)",
        "query": "Aspido",
    },
}


def main():
    db_path = "public/data/review_places_db.json"
    with open(db_path, encoding="utf-8") as f:
        db = json.load(f)

    updated = 0
    for r in db["records"]:
        rid = r.get("record_id")
        if rid not in CORRECTIONS:
            continue
        c = CORRECTIONS[rid]
        if "lat" in c:
            r["lat"] = c["lat"]
            r["lng"] = c["lng"]
            # Also set geocoding_lat/lng so they survive a DB rebuild
            # (preserve_review_fields preserves geocoding_* prefix fields)
            r["geocoding_lat"] = c["lat"]
            r["geocoding_lng"] = c["lng"]
        r["geocoding_status"] = "accepted"
        r["geocoding_source"] = c["source"]
        r["geocoding_confidence"] = c["confidence"]
        r["geocoding_query"] = c["query"]
        r["geocoding_provider_title"] = c["title"]
        r["geocoding_provider_url"] = c["url"]
        r["geocoding_timestamp"] = TIMESTAMP
        r["geocoding_provider"] = "manual"
        updated += 1
        print(f"  updated: {rid} => lat={r['lat']}, lng={r['lng']}")

    db["meta"]["manual_geocoding_timestamp"] = TIMESTAMP
    db["meta"]["manual_geocoding_count"] = updated

    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print(f"\nDone: {updated} records updated.")


if __name__ == "__main__":
    main()
