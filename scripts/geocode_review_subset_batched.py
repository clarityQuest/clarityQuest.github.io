#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path

from geocode_missing import enrich_records, now_iso


def parse_types(value: str) -> list[str]:
    return [part.strip().lower() for part in (value or "").split(",") if part.strip()]


def unresolved(record: dict, wanted_types: set[str], include_empty_modern: bool) -> bool:
    if str(record.get("type", "")).strip().lower() not in wanted_types:
        return False
    if record.get("geocoding_status"):
        return False
    if not include_empty_modern and not str(record.get("modern_preferred") or "").strip():
        return False
    return record.get("lat") is None or record.get("lng") is None


def main() -> None:
    parser = argparse.ArgumentParser(description="Batched subset geocoding with incremental writes.")
    parser.add_argument("--input", default="public/data/review_places_db.json")
    parser.add_argument("--types", default="river,lake,water,port")
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--max-batches", type=int, default=0, help="0 = all batches")
    parser.add_argument("--refresh-cache-first-batch", action="store_true")
    parser.add_argument("--strategy", default="wikipedia,nominatim")
    parser.add_argument("--delay", type=float, default=0.1)
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--min-confidence-wikipedia", type=float, default=0.40)
    parser.add_argument("--min-confidence-nominatim", type=float, default=0.55)
    parser.add_argument("--include-empty-modern", action="store_true")
    parser.add_argument("--queue-output", default="")
    args = parser.parse_args()

    input_path = Path(args.input)
    wanted_types = set(parse_types(args.types))
    if not wanted_types:
        raise SystemExit("No types provided")

    queue_output = args.queue_output.strip()
    if not queue_output:
        suffix = "_".join(sorted(wanted_types))
        queue_output = f"public/data/geocode_refine_queue_{suffix}.json"
    queue_path = Path(queue_output)

    total_summary = {
        "processed": 0,
        "accepted": 0,
        "needs_refinement": 0,
        "no_candidate": 0,
        "no_query": 0,
        "errors": 0,
        "cached": 0,
        "skipped_has_coords": 0,
        "accepted_by_source": {"wikipedia": 0, "google_wikipedia": 0, "nominatim": 0},
        "strategy": [s for s in args.strategy.split(",") if s],
    }
    combined_queue: list[dict] = []

    batch_index = 0
    while True:
        data = json.loads(input_path.read_text(encoding="utf-8"))
        records = data.get("records") or []
        pending = [record for record in records if unresolved(record, wanted_types, args.include_empty_modern)]
        if not pending:
            break

        batch = pending[: max(1, args.batch_size)]
        batch_index += 1
        print(f"Batch {batch_index}: {len(batch)} rows")

        report = enrich_records(
            batch,
            dry_run=False,
            max_records=0,
            refresh_cache=args.refresh_cache_first_batch and batch_index == 1,
            min_confidence=max(0.0, min(1.0, args.min_confidence)),
            min_confidence_wikipedia=max(0.0, min(1.0, args.min_confidence_wikipedia)),
            min_confidence_nominatim=max(0.0, min(1.0, args.min_confidence_nominatim)),
            delay_seconds=max(0.0, args.delay),
            timeout_sec=max(1, args.timeout),
            strategy=args.strategy,
            require_modern_name=not args.include_empty_modern,
        )

        summary = report["summary"]
        if int(summary.get("processed", 0) or 0) == 0:
            print("No processable rows in this batch; stopping to avoid an infinite loop.")
            break
        for key in ["processed", "accepted", "needs_refinement", "no_candidate", "no_query", "errors", "cached", "skipped_has_coords"]:
            total_summary[key] += int(summary.get(key, 0) or 0)
        for provider in total_summary["accepted_by_source"]:
            total_summary["accepted_by_source"][provider] += int((summary.get("accepted_by_source") or {}).get(provider, 0) or 0)

        combined_queue.extend(report["refinement_queue"])

        data.setdefault("meta", {})["subset_geocoding"] = {
            "timestamp": now_iso(),
            "types": sorted(wanted_types),
            "dry_run": False,
            "strategy": args.strategy,
            "summary": total_summary,
            "batch_index": batch_index,
        }
        input_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        queue_path.write_text(json.dumps(combined_queue, ensure_ascii=False, indent=2), encoding="utf-8")

        if args.max_batches > 0 and batch_index >= args.max_batches:
            break

    print(f"Updated: {input_path}")
    print(f"Queue: {queue_path}")
    print(json.dumps(total_summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()