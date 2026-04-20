"""Verify key landmark positions in the generated places.json."""
import json

data = json.load(open("public/data/places.json", encoding="utf-8"))

targets = ["Roma", "Constantinopolis", "Londinio", "Carthago", "Alexandria",
           "Athenae", "Antiochia", "Avgvsta vindelicv", "Neapolis", "Lvgdvnvm",
           "Hierosolyma", "Damascus", "Palmyra"]

for t in targets:
    matches = [p for p in data if t.lower() in p["latin"].lower()]
    for m in matches[:2]:
        seg = int(m["px"] / (46380 / 11)) + 2
        print(f"{m['latin']:30s} modern={m.get('modern',''):20s} "
              f"px={m['px']:8.0f} py={m['py']:7.0f}  seg~{seg}  type={m['type']}")
    if not matches:
        print(f"  {t}: NOT FOUND")
