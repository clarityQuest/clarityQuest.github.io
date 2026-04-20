"""Download official Tabula Peutingeriana 150dpi segment images only.

This script intentionally does NOT stitch images. It just downloads segment
files into a local folder so you can compose/stitch manually.

Outputs:
- public/segments_150dpi/tp_150dpi_01_seg2.jpg ... tp_150dpi_11_seg12.jpg
- public/data/tabula_150dpi_segments_manifest.json

Usage:
    python scripts/stitch_tabula_150dpi.py
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
DATA_DIR = PUBLIC / "data"
SEGMENTS_DIR = PUBLIC / "segments_150dpi"
OUT_MANIFEST = DATA_DIR / "tabula_150dpi_segments_manifest.json"

BASE_URL = "https://www.tabula-peutingeriana.de/download"
SEGMENT_NUMBERS = list(range(2, 13))  # II..XII
SEGMENT_URL_OVERRIDES = {
    11: "https://www.tabula-peutingeriana.de/download/full/tp_weber_a.jpg",
    12: "https://www.tabula-peutingeriana.de/download/full/tp_weber_b.jpg",
}

@dataclass
class SegmentImage:
    number: int
    src_index: int
    url: str
    image: Image.Image


def download_segment(src_index: int, number: int) -> SegmentImage:
    url = SEGMENT_URL_OVERRIDES.get(number, f"{BASE_URL}/tp_150dpi_{src_index}.jpg")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
    return SegmentImage(number=number, src_index=src_index, url=url, image=img)


def save_segment_file(seg: SegmentImage) -> str:
    file_name = f"tp_150dpi_{seg.src_index:02d}_seg{seg.number}.jpg"
    out_path = SEGMENTS_DIR / file_name
    seg.image.save(out_path, quality=95, optimize=True)
    return file_name


def write_manifest(segments: list[dict]) -> None:
    payload = {
        "version": 1,
        "mode": "download-only",
        "output_folder": str(SEGMENTS_DIR.relative_to(PUBLIC)).replace("\\", "/"),
        "segments": segments,
    }
    OUT_MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)

    segments: list[SegmentImage] = []
    manifest_segments: list[dict] = []
    for src_index, number in enumerate(SEGMENT_NUMBERS, start=1):
        seg = download_segment(src_index, number)
        segments.append(seg)
        file_name = save_segment_file(seg)
        manifest_segments.append(
            {
                "number": seg.number,
                "src_index": seg.src_index,
                "url": seg.url,
                "file": file_name,
                "width": seg.image.width,
                "height": seg.image.height,
            }
        )
        print(
            f"Downloaded segment {number} from {seg.url} "
            f"({seg.image.width}x{seg.image.height}) -> {file_name}"
        )

    write_manifest(manifest_segments)

    print(f"Saved {len(manifest_segments)} segment images to: {SEGMENTS_DIR}")
    print(f"Saved download manifest: {OUT_MANIFEST}")
    print("Stitching algorithm removed. You can now stitch manually from the downloaded files.")


if __name__ == "__main__":
    main()
