#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from geocode_missing import enrich_records, now_iso


def parse_types(value: str) -> list[str]:
    return [part.strip().lower() for part in (value or "").split(",") if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Geocode a subset of review database records in place.")
    parser.add_argument("--input", default="public/data/review_places_db.json")
    parser.add_argument(
        "--types",
        default="river,lake,water,port",
        help="Comma-separated record types to process, e.g. river,lake,water,port",
    )
    parser.add_argument("--max-records", type=int, default=0, help="Limit subset size (0 = all matching records)")
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--strategy", default="wikipedia,nominatim")
    parser.add_argument("--delay", type=float, default=0.35)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--min-confidence-wikipedia", type=float, default=0.60)
    parser.add_argument("--min-confidence-nominatim", type=float, default=0.55)
    parser.add_argument("--include-empty-modern", action="store_true")
    parser.add_argument("--queue-output", default="")
    args = parser.parse_args()

    input_path = Path(args.input)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    wanted_types = parse_types(args.types)
    if not wanted_types:
        raise SystemExit("No record types provided")

    records = data.get("records") or []
    subset = [record for record in records if str(record.get("type", "")).strip().lower() in wanted_types]

    print(f"Subset rows: {len(subset)}")

    report = enrich_records(
        subset,
        dry_run=False,
        max_records=max(0, args.max_records),
        refresh_cache=args.refresh_cache,
        min_confidence=max(0.0, min(1.0, args.min_confidence)),
        min_confidence_wikipedia=max(0.0, min(1.0, args.min_confidence_wikipedia)),
        min_confidence_nominatim=max(0.0, min(1.0, args.min_confidence_nominatim)),
        delay_seconds=max(0.0, args.delay),
        timeout_sec=max(1, args.timeout),
        strategy=args.strategy,
        require_modern_name=not args.include_empty_modern,
    )

    meta = data.setdefault("meta", {})
    meta["subset_geocoding"] = {
        "timestamp": now_iso(),
        "types": wanted_types,
        "dry_run": False,
        "strategy": args.strategy,
        "summary": report["summary"],
    }

    input_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    queue_output = args.queue_output.strip()
    if not queue_output:
        suffix = "_".join(wanted_types)
        queue_output = f"public/data/geocode_refine_queue_{suffix}.json"
    queue_path = Path(queue_output)
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(json.dumps(report["refinement_queue"], ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Updated: {input_path}")
    print(f"Queue: {queue_path}")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()