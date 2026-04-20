#!/usr/bin/env python3
"""
Dev server for Tabula Peutingeriana calibration tool.

Usage:
    python scripts/server.py          # serves on http://localhost:8080/
    python scripts/server.py 9000     # custom port

Serves public/ as static files and handles:
    POST /api/save-calibration  ->  atomically writes public/data/review_places_db.json
"""
import http.server
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT    = Path(__file__).parent.parent / "public"
DB_PATH = ROOT / "data" / "review_places_db.json"
PORT    = 8080


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    # ── POST handler ──────────────────────────────────────────────────────────
    def do_POST(self):
        if self.path == "/api/save-calibration":
            self._save_calibration()
        elif self.path == "/api/ulm-search":
            self._ulm_search()
        else:
            self.send_error(404, "Not found")

    def _save_calibration(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            data   = json.loads(body)
            if not isinstance(data, dict) or "records" not in data:
                raise ValueError("Expected JSON object with 'records' array")

            # Atomic write: write to .tmp then rename so the file is never half-written
            tmp = DB_PATH.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            tmp.replace(DB_PATH)

            n = len(data["records"])
            self._json_ok({"ok": True, "records": n})
            print(f"  \u2713 Saved {n} records \u2192 {DB_PATH.name}")

        except Exception as exc:
            self._json_error(str(exc))
            print(f"  \u2717 Save error: {exc}")

    def _ulm_search(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            data   = json.loads(body)
            modern = data.get("name", "").strip()
            latin  = data.get("latin", "").strip()

            def search_ulm(toponym_a="", name_modern=""):
                params = urllib.parse.urlencode({
                    "toponym_a": toponym_a, "name_modern": name_modern,
                    "name_barrington": "", "itant": "", "name_f": "", "planquadrat": "",
                }).encode()
                req = urllib.request.Request(
                    "https://tp-online.ku.de/treffer.php",
                    data=params,
                    headers={"Content-Type": "application/x-www-form-urlencoded",
                             "User-Agent": "Mozilla/5.0"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    html = resp.read().decode("utf-8", errors="replace")
                m = re.search(r'trefferanzeige\.php\?id=(\d+)', html)
                return m.group(1) if m else None

            def vu_variants(s):
                """Yield V↔U substitution variants of s (Latin V/U are the same letter)."""
                variants = {s}
                variants.add(s.replace("v", "u").replace("V", "U"))
                variants.add(s.replace("u", "v").replace("U", "V"))
                # mixed: only v→u in first half, etc. — just yield the three
                return [v for v in variants if v != s]

            ulm_id = None
            if modern:
                ulm_id = search_ulm(name_modern=modern)
            if not ulm_id and latin:
                ulm_id = search_ulm(toponym_a=latin)
            # V↔U fallback for Latin names
            if not ulm_id and latin:
                for variant in vu_variants(latin):
                    ulm_id = search_ulm(toponym_a=variant)
                    if ulm_id:
                        break
            if not ulm_id and modern:
                for variant in vu_variants(modern):
                    ulm_id = search_ulm(name_modern=variant)
                    if ulm_id:
                        break

            if ulm_id:
                detail_url = f"https://tp-online.ku.de/trefferanzeige.php?id={ulm_id}"
                img_url = self._ulm_inset_url(ulm_id)
                self._json_ok({"url": detail_url, "img": img_url})
            else:
                self._json_ok({"url": None, "img": None})

        except Exception as exc:
            self._json_error(str(exc))

    def _ulm_inset_url(self, ulm_id):
        try:
            req = urllib.request.Request(
                f"https://tp-online.ku.de/trefferanzeige.php?id={ulm_id}",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            m = re.search(r'(insetimages/TPPlace\d+insetneu[^"\'<\s]*)', html)
            if m:
                return f"https://tp-online.ku.de/{m.group(1)}"
        except Exception:
            pass
        return None

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _json_ok(self, payload):
        self._json_response(200, payload)

    def _json_error(self, msg):
        self._json_response(400, {"ok": False, "error": msg})

    def _json_response(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        # Prevent caching of JSON data files so calibration updates are seen immediately
        if self.path.endswith(".json") or self.path.split("?")[0].endswith(".json"):
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
        super().end_headers()

    # Suppress noisy tile/image requests from the log
    def log_message(self, fmt, *args):
        msg = args[0] if args else ""
        noisy = (".jpg", ".jpeg", ".png", ".dzi", "_files/", ".js", ".css")
        if not any(ext in str(msg) for ext in noisy):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    os.chdir(ROOT)
    with http.server.HTTPServer(("", port), Handler) as srv:
        print(f"Serving  http://localhost:{port}/")
        print(f"DB path  {DB_PATH}")
        print(f"Press Ctrl+C to stop.\n")
        srv.serve_forever()
