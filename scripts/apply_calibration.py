"""Apply manual calibration JSON to apply_transform_v2.py, then re-run it.

Usage:
    python scripts/apply_calibration.py calibration.json

The calibration.json is downloaded from public/calibrate.html.
Format: { "data_id": [px, py], ... }

This script:
1. Reads calibration.json
2. Merges values into CONTROL_PIXELS in apply_transform_v2.py
3. Writes the updated script back
4. Re-runs apply_transform_v2.py to regenerate seg4_places.json
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANSFORM_SCRIPT = os.path.join(ROOT, "scripts", "apply_transform_v2.py")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/apply_calibration.py calibration.json")
        sys.exit(1)

    cal_path = sys.argv[1]
    with open(cal_path, "r", encoding="utf-8") as f:
        calibration = json.load(f)

    print(f"Loaded {len(calibration)} calibration points from {cal_path}")

    # Read the existing transform script
    with open(TRANSFORM_SCRIPT, "r", encoding="utf-8") as f:
        script = f.read()

    # Extract existing CONTROL_PIXELS block
    pattern = re.compile(
        r"(CONTROL_PIXELS\s*=\s*\{)(.*?)(\})",
        re.DOTALL
    )
    m = pattern.search(script)
    if not m:
        print("ERROR: Could not find CONTROL_PIXELS in apply_transform_v2.py")
        sys.exit(1)

    # Parse existing entries
    existing = {}
    for line in m.group(2).splitlines():
        line = line.strip()
        entry = re.match(r"(\d+)\s*:\s*\(([^)]+)\)", line)
        if entry:
            did = int(entry.group(1))
            coords = [float(x.strip()) for x in entry.group(2).split(",")]
            existing[did] = coords
        # Also match comment for label

    # Merge: new calibration values override existing
    before = dict(existing)
    for did_str, coords in calibration.items():
        did = int(did_str)
        existing[did] = coords

    changed = {k: (before.get(k), existing[k]) for k in existing if before.get(k) != existing[k]}
    new_keys = {k for k in existing if k not in before}

    print(f"  Updated: {len(changed) - len(new_keys)} existing entries")
    print(f"  Added:   {len(new_keys)} new entries")
    for did, (old, new) in changed.items():
        if old is None:
            print(f"    NEW  data_id={did}: {new}")
        else:
            print(f"    MOD  data_id={did}: {old} → {new}")

    if not changed:
        print("No changes — nothing to do.")
        return

    # Build new CONTROL_PIXELS block
    lines = ["CONTROL_PIXELS = {"]
    for did, coords in sorted(existing.items()):
        lines.append(f"    {did}: ({coords[0]:.1f}, {coords[1]:.1f}),")
    lines.append("}")
    new_block = "\n".join(lines)

    # Replace in script
    new_script = pattern.sub(
        lambda _: new_block,
        script
    )

    with open(TRANSFORM_SCRIPT, "w", encoding="utf-8") as f:
        f.write(new_script)
    print(f"\nUpdated {TRANSFORM_SCRIPT}")

    # Re-run the calibration
    print("\nRe-running apply_transform_v2.py ...")
    result = subprocess.run(
        [sys.executable, TRANSFORM_SCRIPT],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    print(result.stdout)
    if result.returncode != 0:
        print("ERRORS:")
        print(result.stderr)
        sys.exit(result.returncode)

    print("Done. Reload http://localhost:8080/ to see updated positions.")


if __name__ == "__main__":
    main()
