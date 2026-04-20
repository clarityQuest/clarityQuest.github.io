"""Robust lat/lng -> pixel calibration for Segment IV.

Method:
0) Directly pin control-point places to their verified pixel coordinates.
1) Fit global polynomial from all places with lat/lng to pinned/baseline px/py.
2) Apply local correction from control points via hybrid residuals:
    smooth RBF + nearest-control IDW for stronger local behavior.
3) Keep baseline grid positions for places without lat/lng.
"""
import json
import os
import numpy as np
from scipy.interpolate import Rbf
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEG4_PATH = os.path.join(ROOT, 'public', 'data', 'seg4_places.json')
OV_PATH = os.path.join(ROOT, 'scripts', 'omnesviae_sample.json')
IMG_PATH = os.path.join(ROOT, 'scripts', 'tp_150dpi_3.jpg')

IMG_W, IMG_H = 4371, 2105

# data_id -> manually verified pixel coords from tile inspection.
# These are pinned directly — the polynomial/RBF is only used for everything else.
# Bug fix: Augusta Vindelicum is data_id=1000 (not 1006 which is Abodiaco).
CONTROL_PIXELS = {
    120: (3549.4, 1637.4),
    215: (3946.6, 1860.8),
    989: (2724.3, 300.3),
    1000: (789.1, 416.9),
    1039: (2595.7, 592.6),
    1048: (1270.8, 679.4),
    1051: (1680.0, 800.0),
    1069: (3030.0, 880.0),
    1086: (1997.4, 1051.7),
    1125: (3645.0, 580.0),
    1126: (2650.0, 500.0),
    2934: (346.6, 1413.4),
}

with open(SEG4_PATH, 'r', encoding='utf-8') as f:
    places = json.load(f)
with open(OV_PATH, 'r', encoding='utf-8') as f:
    ov = json.load(f)

ov_lookup = {}
for entry in ov.get('@graph', []):
    if entry.get('@type') == 'Place' and 'TPPlace' in entry.get('@id', ''):
        did = int(entry['@id'].split('TPPlace')[1])
        ov_lookup[did] = entry

# Step 0: Pin control-point places to their verified pixel coordinates.
# This happens before polynomial training so the pinned values become
# the ground truth that the polynomial and RBF learn from.
pinned = 0
for p in places:
    did = p.get('data_id', 0)
    if did in CONTROL_PIXELS:
        true_px, true_py = CONTROL_PIXELS[did]
        p['px'] = true_px
        p['py'] = true_py
        p['_pinned'] = True
        pinned += 1
    else:
        p['_pinned'] = False
print(f"Pinned control points: {pinned}")

# Preserve baseline fallback values (after pinning so pinned values propagate)
for p in places:
    p['_base_px'] = float(p['px'])
    p['_base_py'] = float(p['py'])

train_lat = []
train_lng = []
train_px = []
train_py = []

for p in places:
    did = p.get('data_id', 0)
    o = ov_lookup.get(did, {})
    lat = o.get('lat')
    lng = o.get('lng')
    if lat is None or lng is None:
        continue
    if p['latin'].startswith('[') and p['latin'].endswith(']'):
        continue
    # Baseline training from current grid coordinates
    train_lat.append(float(lat))
    train_lng.append(float(lng))
    train_px.append(float(p['_base_px']))
    train_py.append(float(p['_base_py']))

train_lat = np.array(train_lat)
train_lng = np.array(train_lng)
train_px = np.array(train_px)
train_py = np.array(train_py)

print(f"Training points (global fit): {len(train_lat)}")

# 2nd-order polynomial global model
X = np.column_stack([
    np.ones_like(train_lat),
    train_lat,
    train_lng,
    train_lat * train_lng,
    train_lat * train_lat,
    train_lng * train_lng,
])

coef_px, *_ = np.linalg.lstsq(X, train_px, rcond=None)
coef_py, *_ = np.linalg.lstsq(X, train_py, rcond=None)

def global_predict(lat, lng):
    f = np.array([1.0, lat, lng, lat * lng, lat * lat, lng * lng])
    return float(f @ coef_px), float(f @ coef_py)


def idw_local_residual(lat, lng, k=4, power=2.0):
    """Nearest-control inverse-distance residual for local sharpening."""
    if len(ctl_lat) == 0:
        return 0.0, 0.0

    d2 = (ctl_lat - lat) ** 2 + (ctl_lng - lng) ** 2
    take = min(k, len(d2))
    idx = np.argsort(d2)[:take]
    sel_d2 = d2[idx]

    # Exact (or near-exact) lat/lng match with a control point.
    very_close = sel_d2 < 1e-12
    if np.any(very_close):
        j = idx[np.where(very_close)[0][0]]
        return float(ctl_dx[j]), float(ctl_dy[j])

    dist = np.sqrt(sel_d2)
    w = 1.0 / np.power(dist + 1e-6, power)
    w = w / np.sum(w)

    dx = float(np.sum(w * ctl_dx[idx]))
    dy = float(np.sum(w * ctl_dy[idx]))
    return dx, dy

# Build control-point residuals for local correction
ctl_lat = []
ctl_lng = []
ctl_dx = []
ctl_dy = []

for did, (true_px, true_py) in CONTROL_PIXELS.items():
    o = ov_lookup.get(did, {})
    lat = o.get('lat')
    lng = o.get('lng')
    if lat is None or lng is None:
        continue
    pred_px, pred_py = global_predict(float(lat), float(lng))
    ctl_lat.append(float(lat))
    ctl_lng.append(float(lng))
    ctl_dx.append(true_px - pred_px)
    ctl_dy.append(true_py - pred_py)

ctl_lat = np.array(ctl_lat)
ctl_lng = np.array(ctl_lng)
ctl_dx = np.array(ctl_dx)
ctl_dy = np.array(ctl_dy)
print(f"Control points (local correction): {len(ctl_lat)}")

# Smooth thin-plate local correction
rbf_dx = Rbf(ctl_lat, ctl_lng, ctl_dx, function='thin_plate', smooth=0.4)
rbf_dy = Rbf(ctl_lat, ctl_lng, ctl_dy, function='thin_plate', smooth=0.4)

updated = 0
fallback_no_latlng = 0
outliers_kept_base = 0

for p in places:
    # Control-point places are already pinned to verified coords — skip.
    if p.get('_pinned'):
        p['px'] = round(float(p['_base_px']), 1)
        p['py'] = round(float(p['_base_py']), 1)
        continue

    did = p.get('data_id', 0)
    o = ov_lookup.get(did, {})
    lat = o.get('lat')
    lng = o.get('lng')

    # Keep baseline for unknown / reconstructed points
    if lat is None or lng is None or (p['latin'].startswith('[') and p['latin'].endswith(']')):
        p['px'] = round(float(p['_base_px']), 1)
        p['py'] = round(float(p['_base_py']), 1)
        fallback_no_latlng += 1
        continue

    lat = float(lat)
    lng = float(lng)
    gpx, gpy = global_predict(lat, lng)

    rbf_rx = float(rbf_dx(lat, lng))
    rbf_ry = float(rbf_dy(lat, lng))
    idw_rx, idw_ry = idw_local_residual(lat, lng, k=4, power=2.0)

    ptype = p.get('type', 'road_station')
    # Small places benefit from stronger local behavior.
    if ptype == 'road_station':
        alpha = 0.45
        max_shift = 260.0
    elif ptype in ('major_city', 'city', 'port'):
        alpha = 0.75
        max_shift = 600.0
    else:
        alpha = 0.60
        max_shift = 380.0

    rx = alpha * rbf_rx + (1.0 - alpha) * idw_rx
    ry = alpha * rbf_ry + (1.0 - alpha) * idw_ry
    px = gpx + rx
    py = gpy + ry

    base_px = float(p['_base_px'])
    base_py = float(p['_base_py'])
    shift = float(np.hypot(px - base_px, py - base_py))
    if shift > max_shift and shift > 1e-9:
        s = max_shift / shift
        px = base_px + (px - base_px) * s
        py = base_py + (py - base_py) * s

    # Guard against extreme extrapolation: fallback to baseline for bad outliers
    if px < -60 or px > IMG_W + 60 or py < -60 or py > IMG_H + 60:
        px = base_px
        py = base_py
        outliers_kept_base += 1
    else:
        # Clamp soft bounds
        px = max(5.0, min(IMG_W - 5.0, px))
        py = max(5.0, min(IMG_H - 5.0, py))

    p['px'] = round(px, 1)
    p['py'] = round(py, 1)
    updated += 1

for p in places:
    p.pop('_base_px', None)
    p.pop('_base_py', None)
    p.pop('_pinned', None)

with open(SEG4_PATH, 'w', encoding='utf-8') as f:
    json.dump(places, f, indent=2, ensure_ascii=False)

print(f"Updated from model: {updated}")
print(f"Fallback no lat/lng: {fallback_no_latlng}")
print(f"Outliers fallback base: {outliers_kept_base}")

# Save a lightweight debug image under 2000 px max side to avoid payload limits
img = Image.open(IMG_PATH).convert('RGB')
draw = ImageDraw.Draw(img)

color = {
    'major_city': 'red',
    'city': 'orange',
    'port': 'cyan',
    'road_station': 'yellow',
}
for p in places:
    px = p['px']
    py = p['py']
    r = 3 if p['type'] in ('major_city', 'city', 'port') else 2
    c = color.get(p['type'], 'white')
    draw.ellipse([px - r, py - r, px + r, py + r], fill=c, outline=c)

for did, (x, y) in CONTROL_PIXELS.items():
    draw.ellipse([x - 6, y - 6, x + 6, y + 6], outline='lime', width=2)

# downscale for safer viewing in chat context
scale = min(1800.0 / img.width, 1800.0 / img.height, 1.0)
if scale < 1.0:
    img = img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.LANCZOS)

dbg = os.path.join(ROOT, 'scripts', 'debug_calibrated_small.jpg')
img.save(dbg, quality=88)
print(f"Saved {dbg}")
