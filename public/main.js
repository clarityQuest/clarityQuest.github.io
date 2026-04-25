/**
 * Tabula Peutingeriana — Segment IV Interactive Viewer
 *
 * Features:
 * - OpenSeadragon deep-zoom with two tile sources:
 *   · Original (Miller 1887 facsimile, segment IV viewport) — no markers
 *   · Readable (Weber Kopie, 150dpi) — with color-coded markers
 * - 320 places scraped from tabula-peutingeriana.de
 * - Latin / English label toggle
 * - Hover tooltips and click info panel
 * - Search by Latin or modern name
 * - Zoom-dependent marker visibility
 * - Canvas-overlay marker rendering
 */

"use strict";

/* ============================================================
   Constants
   ============================================================ */

// Weber 150dpi segment IV image
const IMG_W = 4371;
const IMG_H = 2105;
const DEFAULT_SEGMENT = 4;

// Miller full image
const MILLER_W = 46380;
const MILLER_H = 2953;
const SEGMENT_COUNT = 11;

const TYPE_COLORS = {
  major_city:     "#8B0000",
  city:           "#f97316",
  port:           "#1D4ED8",
  road_station:   "#92400E",
  river:          "#0e7490",
  lake:           "#0369a1",
  island:         "#15803d",
  region:         "#7c3aed",
  roman_province: "#a16207",
  modern_state:   "#475569",
  water:          "#164e63",
  spa:            "#0891b2",
  temple:         "#9333ea",
  mountain:       "#78716c",
  people:         "#9d174d",
};

const TYPE_LABELS = {
  major_city:     "Major City",
  city:           "City",
  port:           "Port",
  road_station:   "Road Station",
  river:          "River",
  lake:           "Lake",
  island:         "Island",
  region:         "Region",
  roman_province: "Roman Province",
  modern_state:   "Modern State",
  water:          "Water",
  spa:            "Spa",
  temple:         "Temple",
  mountain:       "Mountain",
  people:         "People",
};

const DRAFT_STORAGE_KEY = "tp_calibrate_seg4_rectangles_v1";
const MAP_RUNTIME_TYPES = new Set(Object.keys(TYPE_COLORS));

/* ============================================================
   State
   ============================================================ */
const S = {
  viewer:       null,
  places:       [],
  segments:     [],
  mapMode:      "old",       // "old" | "new"
  selectedSegment: DEFAULT_SEGMENT,
  newSourceKind: "readable-seg4", // "readable-seg4" | "stitched"
  markersOn:      true,
  labelsOn:       true,
  activeTypes:    new Set(["major_city", "city"]),
  millerOverlayOn: true,
  millerCalib:    [],   // loaded from miller_rect_* fields in review_places_db.json
  legendOpen:     false,
  selectedPlace:  null,
  highlightDataId: null,
  highlightUntil:  0,
  highlightVp:     null,  // {vx,vy} viewport centre stored by panToPlace for fallback ring
  isMobile: window.matchMedia("(pointer: coarse), (max-width: 600px)").matches,
  canvas:       null,
  ctx:          null,
  readableTile: null,
  originalTile: null,
  stitchedTile: null,
  boundsBySource: {
    old: {},
    stitched: {},
    readableSeg4: {},
  },
};

/* ============================================================
   Data loading
   ============================================================ */
async function loadJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

async function loadJSONOptional(url, fallback) {
  try {
    return await loadJSON(url);
  } catch {
    return fallback;
  }
}

function loadCalibrateDraftMap() {
  try {
    const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
    if (!raw) return new Map();
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return new Map();

    const out = new Map();
    for (const [did, rec] of Object.entries(parsed)) {
      const nDid = Number(did);
      if (!Number.isFinite(nDid) || !rec || typeof rec !== "object") continue;
      if (!(Number.isFinite(rec.rect_x1) && Number.isFinite(rec.rect_y1) && Number.isFinite(rec.rect_x2) && Number.isFinite(rec.rect_y2))) continue;
      out.set(nDid, {
        rect_x1: Number(rec.rect_x1),
        rect_y1: Number(rec.rect_y1),
        rect_x2: Number(rec.rect_x2),
        rect_y2: Number(rec.rect_y2),
        rect_w: Number.isFinite(rec.rect_w) ? Number(rec.rect_w) : undefined,
        rect_h: Number.isFinite(rec.rect_h) ? Number(rec.rect_h) : undefined,
        rect_user_set: true,
      });
    }
    return out;
  } catch (e) {
    console.warn("Could not read calibrate draft rectangles:", e);
    return new Map();
  }
}

/* ============================================================
   Coordinate helpers
   ============================================================ */
function viewportToCanvas(vx, vy) {
  const vp = S.viewer.viewport;
  const p = vp.viewportToViewerElementCoordinates(new OpenSeadragon.Point(vx, vy));
  return { cx: p.x, cy: p.y };
}

function imageToCanvas(ix, iy) {
  const vp = S.viewer.viewport;
  const v = vp.imageToViewportCoordinates(new OpenSeadragon.Point(ix, iy));
  const p = vp.viewportToViewerElementCoordinates(v);
  return { cx: p.x, cy: p.y };
}

function buildUniformBounds(segmentNumbers) {
  const out = {};
  const width = 1 / Math.max(segmentNumbers.length, 1);
  segmentNumbers.forEach((n, idx) => {
    const x0 = idx * width;
    const x1 = idx === segmentNumbers.length - 1 ? 1 : (idx + 1) * width;
    out[String(n)] = { x0, y0: 0, x1, y1: 1 };
  });
  return out;
}

function activeBoundsKey() {
  if (S.mapMode === "old") return "old";
  return S.newSourceKind === "stitched" ? "stitched" : "readableSeg4";
}

function boundsKeyForMode(mode) {
  if (mode === "old") return "old";
  return S.newSourceKind === "stitched" ? "stitched" : "readableSeg4";
}

function getSegmentBounds(segmentNumber, boundsKey = activeBoundsKey()) {
  const key = String(segmentNumber);
  return S.boundsBySource[boundsKey]?.[key] || null;
}

function applySegmentUIState() {
  const container = document.getElementById("segment-buttons");
  if (!container) return;
  container.querySelectorAll(".seg-btn").forEach((btn) => {
    btn.classList.toggle("active", Number(btn.dataset.seg) === S.selectedSegment);
  });
}

function focusSegment(segmentNumber, immediate = false) {
  const n = Number(segmentNumber);
  const bounds = getSegmentBounds(n);
  if (!bounds) {
    applySegmentUIState();
    const statusEl = document.getElementById("status");
    if (statusEl && S.mapMode === "new" && S.newSourceKind === "readable-seg4") {
      statusEl.textContent = "Readable fallback only supports segment IV until stitched assets are generated.";
    }
    return false;
  }

  S.selectedSegment = n;
  applySegmentUIState();
  const segW = Math.max(0.00001, bounds.x1 - bounds.x0);
  const segH = Math.max(0.00001, bounds.y1 - bounds.y0);
  const cx = bounds.x0 + segW / 2;
  const cy = bounds.y0 + segH / 2;

  // Zoom so the segment fills the viewport.
  // OSD normalises ALL coordinates to image WIDTH (x: 0..1, y: 0..1/imageAspect).
  // bounds.y0/y1 are in image-height-normalised space (0..1), so convert to OSD space.
  const vp = S.viewer.viewport;
  const containerEl = S.viewer.container;
  const viewportAspect = containerEl ? containerEl.clientWidth / Math.max(1, containerEl.clientHeight) : 1;
  const imageEl = S.viewer.world.getItemAt(0);
  const imageAspect = imageEl
    ? imageEl.getContentSize().x / Math.max(1, imageEl.getContentSize().y)
    : (S.stitchedTile?.Image?.Size
        ? Number(S.stitchedTile.Image.Size.Width) / Math.max(1, Number(S.stitchedTile.Image.Size.Height))
        : 16);

  // Convert y from image-height-fraction → OSD viewport units (divide by imageAspect)
  const osdCy = cy / imageAspect;
  // Zoom to fill width:  Z = 1/segW
  // Zoom to fill height: Z = imageAspect / (viewportAspect * segH)
  //   because viewport height in OSD units = (1/viewportAspect)/Z = segH/imageAspect
  const zoomFill = Math.max(1 / segW, imageAspect / (viewportAspect * segH)) * 0.82;

  vp.panTo(new OpenSeadragon.Point(cx, osdCy), immediate);
  vp.zoomTo(zoomFill, new OpenSeadragon.Point(cx, osdCy), immediate);
  return true;
}

function setupSegmentSelector() {
  const container = document.getElementById("segment-buttons");
  if (!container) return;
  container.innerHTML = S.segments.map((seg) => {
    const n = Number(seg.number);
    const roman = String(seg.roman || n);
    return `<button class="seg-btn" data-seg="${n}" title="Segment ${roman}">${roman}</button>`;
  }).join("");
  applySegmentUIState();
  container.addEventListener("click", (e) => {
    const btn = e.target.closest(".seg-btn");
    if (!btn) return;
    focusSegment(Number(btn.dataset.seg));
  });
}

/* ============================================================
   Marker rendering (canvas overlay)
   ============================================================ */
function sizeCanvas() {
  const el = S.viewer.element;
  const dpr = window.devicePixelRatio || 1;
  S.canvas.width  = el.clientWidth  * dpr;
  S.canvas.height = el.clientHeight * dpr;
  S.canvas.style.width  = el.clientWidth  + "px";
  S.canvas.style.height = el.clientHeight + "px";
  S.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function markerRadius(zoom, type) {
  const base = type === "major_city" ? 6 :
               type === "city" ? 4.5 :
               type === "port" ? 4 : 3;
  return Math.min(base * Math.sqrt(zoom + 0.5), 20);
}

function defaultRectSize(type) {
  if (type === "major_city") return { w: 12, h: 12 };
  if (type === "city") return { w: 9, h: 9 };
  if (type === "port") return { w: 8, h: 8 };
  return { w: 6, h: 6 };
}

function placeRectCorners(place) {
  const d = defaultRectSize(place.type);
  const w = Number.isFinite(place.rect_w) && place.rect_w > 0 ? place.rect_w : d.w;
  const h = Number.isFinite(place.rect_h) && place.rect_h > 0 ? place.rect_h : d.h;

  let x1 = place.rect_x1;
  let y1 = place.rect_y1;
  let x2 = place.rect_x2;
  let y2 = place.rect_y2;

  const hasCorners = Number.isFinite(x1) && Number.isFinite(y1) && Number.isFinite(x2) && Number.isFinite(y2);
  if (!hasCorners) {
    const cx = Number(place.px);
    const cy = Number(place.py);
    x1 = cx - w / 2;
    y1 = cy - h / 2;
    x2 = cx + w / 2;
    y2 = cy + h / 2;
  }

  // If user explicitly set a rectangle, trust the provided corners exactly.
  // Do not substitute with defaults for user-set records.
  if (place.rect_user_set && !hasCorners) {
    const cx = Number(place.px);
    const cy = Number(place.py);
    x1 = cx - w / 2;
    y1 = cy - h / 2;
    x2 = cx + w / 2;
    y2 = cy + h / 2;
  }

  if (x1 > x2) [x1, x2] = [x2, x1];
  if (y1 > y2) [y1, y2] = [y2, y1];

  x1 = Math.max(0, Math.min(IMG_W, x1));
  y1 = Math.max(0, Math.min(IMG_H, y1));
  x2 = Math.max(0, Math.min(IMG_W, x2));
  y2 = Math.max(0, Math.min(IMG_H, y2));

  return { x1, y1, x2, y2, w: Math.max(1, x2 - x1), h: Math.max(1, y2 - y1) };
}

function isVisibleAtZoom(type, zoom) {
  if (zoom >= 2.5)  return true;
  if (zoom >= 0.8)  return type !== "road_station";
  return type === "major_city" || type === "city";
}

/* ============================================================
   Miller calibration overlay
   ============================================================ */
function loadMillerCalib(allRecords) {
  try {
    const result = [];
    for (const r of allRecords) {
      const did = Number(r.data_id);
      if (!Number.isFinite(did)) continue;
      const x1 = Number(r.miller_rect_x1);
      const y1 = Number(r.miller_rect_y1);
      const x2 = Number(r.miller_rect_x2);
      const y2 = Number(r.miller_rect_y2);
      if (!(Number.isFinite(x1) && Number.isFinite(y1) &&
            Number.isFinite(x2) && Number.isFinite(y2))) continue;
      result.push({
        data_id:   did,
        rect_x1:   x1, rect_y1: y1,
        rect_x2:   x2, rect_y2: y2,
        type:      r.type || "road_station",
        latin_std: r.latin_std || r.latin || "",
        modern:    r.modern_preferred || r.modern_tabula || r.modern_omnesviae || "",
        province:  r.province || r.region || "",
        country:   r.country || "",
        lat:       r.lat != null ? Number(r.lat) : null,
        lng:       r.lng != null ? Number(r.lng) : null,
        tabula_segment: r.tabula_segment,
        tabula_row:     r.tabula_row,
        tabula_col:     r.tabula_col,
      });
    }
    return result;
  } catch (e) {
    console.warn("Could not load Miller calibration overlay:", e);
    return [];
  }
}

function startHighlight(place) {
  S.highlightDataId = Number(place.data_id);
  S.highlightUntil  = Date.now() + 20000;
  function tick() {
    renderMarkers();
    if (Date.now() < S.highlightUntil) requestAnimationFrame(tick);
    else { S.highlightDataId = null; renderMarkers(); }
  }
  requestAnimationFrame(tick);
}

function drawHighlightRing(ctx, cx, cy, baseR) {
  const now = Date.now();
  ctx.save();
  for (let i = 0; i < 2; i++) {
    const t = ((now + i * 500) % 1000) / 1000;
    ctx.globalAlpha = (1 - t) * 0.85;
    ctx.beginPath();
    ctx.arc(cx, cy, baseR + t * baseR * 2.5, 0, Math.PI * 2);
    ctx.strokeStyle = "#FFD700";
    ctx.lineWidth = 2.5;
    ctx.stroke();
  }
  ctx.restore();
}

function renderMillerOverlay(ctx) {
  if (!S.viewer || !S.viewer.viewport) return false;
  const vp = S.viewer.viewport;
  const bounds = vp.getBounds(true);

  const maxMFont    = S.isMobile ? 13 : 22;
  const maxMLabels  = S.isMobile ?  6 : 30;
  const mLabelRects = [];
  const MPAD = 4;
  let mLabelCount = 0;

  let drawn = 0;
  let highlightDrawn = false;
  for (const item of S.millerCalib) {
    if (!S.activeTypes.has(item.type)) continue;
    const vx1 = item.rect_x1 / MILLER_W;
    const vx2 = item.rect_x2 / MILLER_W;
    const vy1 = item.rect_y1 / MILLER_W;
    const vy2 = item.rect_y2 / MILLER_W;
    if (vx2 < bounds.x || vx1 > bounds.x + bounds.width) continue;
    if (vy2 < bounds.y || vy1 > bounds.y + bounds.height) continue;

    const p1 = imageToCanvas(item.rect_x1, item.rect_y1);
    const p2 = imageToCanvas(item.rect_x2, item.rect_y2);
    const x = Math.min(p1.cx, p2.cx);
    const y = Math.min(p1.cy, p2.cy);
    const w = Math.max(1, Math.abs(p2.cx - p1.cx));
    const h = Math.max(1, Math.abs(p2.cy - p1.cy));
    const color = TYPE_COLORS[item.type] || "#92400E";

    ctx.fillStyle = color;
    ctx.globalAlpha = 0.23;
    ctx.fillRect(x, y, w, h);
    ctx.globalAlpha = 0.65;
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(x, y, w, h);
    ctx.globalAlpha = 1;

    if (item.data_id === S.highlightDataId && Date.now() < S.highlightUntil) {
      drawHighlightRing(ctx, x + w / 2, y + h / 2, Math.max(w, h) / 2 + 4);
      highlightDrawn = true;
    }

    if (S.labelsOn && mLabelCount < maxMLabels) {
      // min(w,h): thin/wide markers don't get inflated font from their long axis
      const mfs = Math.min(Math.min(w, h) * 1.4, maxMFont);
      if (mfs >= 9) {
        const mAlpha = Math.min(1, (mfs - 9) * 0.6);
        if (mAlpha > 0) {
          const charW = mfs * 0.55;
          const lineH = mfs * 1.3;
          const txt1 = item.modern    || "";
          const txt2 = item.latin_std || "";
          const boxW = Math.max(txt1.length, txt2.length) * charW;
          const boxH = (txt1 ? lineH : 0) + (txt2 ? lineH : 0);
          const bx = x + 2, by = y + h + 2;
          let overlaps = false;
          for (const r of mLabelRects) {
            if (bx < r.x2 && bx + boxW > r.x1 && by < r.y2 && by + boxH > r.y1) {
              overlaps = true; break;
            }
          }
          if (!overlaps) {
            mLabelRects.push({ x1: bx - MPAD, y1: by - MPAD,
                               x2: bx + boxW + MPAD, y2: by + boxH + MPAD });
            mLabelCount++;
            ctx.save();
            ctx.globalAlpha = mAlpha;
            ctx.strokeStyle = "rgba(0,0,0,0.8)";
            ctx.lineWidth = 3;
            ctx.lineJoin = "round";
            let dy = by;
            if (txt1) {
              ctx.font = `bold ${Math.round(mfs)}px 'Segoe UI', system-ui, sans-serif`;
              ctx.textBaseline = "top";
              ctx.strokeText(txt1, bx, dy);
              ctx.fillStyle = "#ffffff";
              ctx.fillText(txt1, bx, dy);
              dy += lineH;
            }
            if (txt2) {
              ctx.font = `${Math.round(Math.max(6, mfs - 1))}px 'Segoe UI', system-ui, sans-serif`;
              ctx.textBaseline = "top";
              ctx.strokeText(txt2, bx, dy);
              ctx.fillStyle = "#e5e7eb";
              ctx.fillText(txt2, bx, dy);
            }
            ctx.restore();
          }
        }
      }
    }
    drawn++;
  }
  ctx.globalAlpha = 1;

  return highlightDrawn;
}

function renderMarkers() {
  if (!S.viewer || !S.ctx) return;
  const ctx = S.ctx;
  const el = S.viewer.element;
  ctx.clearRect(0, 0, el.clientWidth, el.clientHeight);

  let highlightDrawn = false;
  if (S.millerOverlayOn && S.millerCalib.length && S.mapMode === "old")
    highlightDrawn = renderMillerOverlay(ctx) || false;

  // SegIV readable markers (disabled when on old map)
  if (!S.markersOn || S.mapMode === "old" || S.newSourceKind === "stitched" || !S.places.length) return;

  const vp = S.viewer.viewport;
  const zoom = vp.getZoom(true);
  const bounds = vp.getBounds(true);

  const bx0 = bounds.x;
  const bx1 = bounds.x + bounds.width;
  const by0 = bounds.y;
  const by1 = bounds.y + bounds.height;

  // Font size driven by the SMALLER marker dimension (min not max) so wide rivers
  // don't inflate the font. Overlap detection + hard mobile cap prevent crowding.
  const maxLabelFont = S.isMobile ? 13 : 22;
  const MAX_LABELS   = S.isMobile ?  6 : 999;
  const labelRects = [];
  const LABEL_PAD = 4;

  let rendered = 0;
  let labelCount = 0;

  for (const p of S.places) {
    if (!S.activeTypes.has(p.type)) continue;
    if (p.vx < bx0 || p.vx > bx1 || p.vy < by0 || p.vy > by1) continue;
    if (!isVisibleAtZoom(p.type, zoom)) continue;

    const rr = placeRectCorners(p);
    const p1 = imageToCanvas(rr.x1, rr.y1);
    const p2 = imageToCanvas(rr.x2, rr.y2);
    const x = Math.min(p1.cx, p2.cx);
    const y = Math.min(p1.cy, p2.cy);
    const w = Math.max(1, Math.abs(p2.cx - p1.cx));
    const h = Math.max(1, Math.abs(p2.cy - p1.cy));
    const cx = (p1.cx + p2.cx) / 2;
    const cy = (p1.cy + p2.cy) / 2;
    const color = TYPE_COLORS[p.type] || "#92400E";

    ctx.fillStyle = color;
    ctx.globalAlpha = 0.23;
    ctx.fillRect(x, y, w, h);
    ctx.globalAlpha = 0.65;
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(x, y, w, h);
    ctx.globalAlpha = 1;

    if (p.data_id === S.highlightDataId && Date.now() < S.highlightUntil) {
      drawHighlightRing(ctx, cx, cy, Math.max(w, h) / 2 + 4);
      highlightDrawn = true;
    }

    if (S.labelsOn && labelCount < MAX_LABELS) {
      const latin  = p.latin_std || p.latin;
      const modern = p.modern || null;
      if (latin || modern) {
        // Use min(w,h): a wide-but-thin river marker shouldn't get a large font
        const fontSize = Math.min(Math.min(w, h) * 1.4, maxLabelFont);
        if (fontSize >= 9) {
          const alpha = Math.min(1, (fontSize - 9) * 0.6);
          if (alpha > 0) {
            // Estimate label bounding box (char width ≈ 0.55 × fontSize)
            const charW = fontSize * 0.55;
            const lineH = fontSize * 1.3;
            const boxW = Math.max(
              modern ? modern.length * charW : 0,
              latin  ? latin.length  * charW : 0
            );
            const boxH = (modern ? lineH : 0) + (latin ? lineH : 0);
            const bx = x + 2;
            const by = y + h + 2;

            // Skip if this label would overlap an already-placed one
            let overlaps = false;
            for (const r of labelRects) {
              if (bx < r.x2 && bx + boxW > r.x1 && by < r.y2 && by + boxH > r.y1) {
                overlaps = true; break;
              }
            }
            if (!overlaps) {
              labelRects.push({ x1: bx - LABEL_PAD, y1: by - LABEL_PAD,
                                x2: bx + boxW + LABEL_PAD, y2: by + boxH + LABEL_PAD });
              labelCount++;
              ctx.save();
              ctx.globalAlpha = alpha;
              ctx.strokeStyle = "rgba(0,0,0,0.8)";
              ctx.lineWidth = 3;
              ctx.lineJoin = "round";
              const fsBold = Math.round(fontSize);
              const fsNorm = Math.max(6, fsBold - 1);
              let dy = by;
              if (modern) {
                ctx.font = `bold ${fsBold}px 'Segoe UI', system-ui, sans-serif`;
                ctx.textBaseline = "top";
                ctx.strokeText(modern, bx, dy);
                ctx.fillStyle = "#ffffff";
                ctx.fillText(modern, bx, dy);
                dy += lineH;
              }
              if (latin) {
                ctx.font = `${fsNorm}px 'Segoe UI', system-ui, sans-serif`;
                ctx.textBaseline = "top";
                ctx.strokeText(latin, bx, dy);
                ctx.fillStyle = "#e5e7eb";
                ctx.fillText(latin, bx, dy);
              }
              ctx.restore();
            }
          }
        }
      }
    }
    rendered++;
  }

  // Fallback: draw a dot + ring at the estimated position when no real marker was rendered
  if (!highlightDrawn && S.highlightDataId && Date.now() < S.highlightUntil && S.highlightVp) {
    const { cx, cy } = viewportToCanvas(S.highlightVp.vx, S.highlightVp.vy);
    const hlPlace = S.places.find(p => p.data_id === S.highlightDataId);
    const color = hlPlace ? (TYPE_COLORS[hlPlace.type] || "#92400E") : "#92400E";
    ctx.save();
    ctx.globalAlpha = 0.9;
    ctx.beginPath();
    ctx.arc(cx, cy, 7, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.7)";
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();
    drawHighlightRing(ctx, cx, cy, 11);
  }
}

/* ============================================================
   Hit-test (find place under cursor)
   ============================================================ */
function hitTest(clientX, clientY) {
  if (!S.viewer || !S.markersOn || S.mapMode === "old" || S.newSourceKind === "stitched") return null;
  const vp = S.viewer.viewport;
  const zoom = vp.getZoom(true);
  const elRect = S.viewer.element.getBoundingClientRect();
  const ex = clientX - elRect.left;
  const ey = clientY - elRect.top;

  let best = null;
  let bestDist = Infinity;
  const threshold = 6;

  for (const p of S.places) {
    if (!S.activeTypes.has(p.type)) continue;
    if (!isVisibleAtZoom(p.type, zoom)) continue;
    const rr = placeRectCorners(p);
    const p1 = imageToCanvas(rr.x1, rr.y1);
    const p2 = imageToCanvas(rr.x2, rr.y2);
    const x0 = Math.min(p1.cx, p2.cx) - threshold;
    const x1 = Math.max(p1.cx, p2.cx) + threshold;
    const y0 = Math.min(p1.cy, p2.cy) - threshold;
    const y1 = Math.max(p1.cy, p2.cy) + threshold;
    const cx = (p1.cx + p2.cx) / 2;
    const cy = (p1.cy + p2.cy) / 2;

    if (ex >= x0 && ex <= x1 && ey >= y0 && ey <= y1) {
      const dx = cx - ex;
      const dy = cy - ey;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < bestDist) {
        bestDist = dist;
        best = p;
      }
    }
  }
  return best;
}

/* ============================================================
   Tooltip
   ============================================================ */
function showTooltip(place, x, y) {
  const tt = document.getElementById("tooltip");
  const color = TYPE_COLORS[place.type] || "#92400E";
  const typeLabel = TYPE_LABELS[place.type] || place.type;
  const displayLatin = place.latin_std || place.latin;
  const flags = countryFlags(place.country);
  tt.innerHTML = `
    <div class="tt-latin">${escHtml(displayLatin)}</div>
    ${place.modern ? `<div class="tt-modern">${flags ? flags + " " : ""}${escHtml(place.modern)}</div>` : (flags ? `<div class="tt-modern">${flags}</div>` : "")}
    <div class="tt-type"><span class="dot" style="background:${color}"></span>${typeLabel}</div>
  `;
  tt.style.left = (x + 24) + "px";
  tt.style.top  = (y - 20) + "px";
  tt.classList.remove("hidden");

  const rect = tt.getBoundingClientRect();
  if (rect.right > window.innerWidth) tt.style.left = (x - rect.width - 16) + "px";
  if (rect.bottom > window.innerHeight) tt.style.top = (y - rect.height - 16) + "px";
}

function hideTooltip() {
  const tt = document.getElementById("tooltip");
  tt.classList.add("hidden");
  tt.classList.remove("tt-rich");
}

/* ============================================================
   Miller overlay hit-test & rich tooltip
   ============================================================ */
function hitTestMillerOverlay(clientX, clientY) {
  if (!S.millerOverlayOn || !S.millerCalib.length || !S.viewer || S.mapMode !== "old") return null;
  const elRect = S.viewer.element.getBoundingClientRect();
  const ex = clientX - elRect.left;
  const ey = clientY - elRect.top;
  const pad = 4;

  for (const item of S.millerCalib) {
    const p1 = imageToCanvas(item.rect_x1, item.rect_y1);
    const p2 = imageToCanvas(item.rect_x2, item.rect_y2);
    const x0 = Math.min(p1.cx, p2.cx) - pad;
    const x1 = Math.max(p1.cx, p2.cx) + pad;
    const y0 = Math.min(p1.cy, p2.cy) - pad;
    const y1 = Math.max(p1.cy, p2.cy) + pad;
    if (ex >= x0 && ex <= x1 && ey >= y0 && ey <= y1) return item;
  }
  return null;
}

function showMillerTooltip(item, x, y) {
  const tt = document.getElementById("tooltip");
  const color = TYPE_COLORS[item.type] || "#92400E";
  const typeLabel = TYPE_LABELS[item.type] || item.type;

  tt.innerHTML = `
    <div class="tt-latin">${escHtml(item.latin_std || String(item.data_id))}</div>
    ${item.modern   ? `<div class="tt-modern">${escHtml(item.modern)}</div>` : ""}
    <div class="tt-type"><span class="dot" style="background:${color}"></span>${typeLabel}</div>
    ${item.province ? `<div class="tt-detail">Province: <span>${escHtml(item.province)}</span></div>` : ""}
    ${item.country  ? `<div class="tt-detail">${countryFlags(item.country)} <span>${escHtml(item.country)}</span></div>` : ""}
  `;
  tt.classList.add("tt-rich");
  tt.style.left = (x + 24) + "px";
  tt.style.top  = (y - 20) + "px";
  tt.classList.remove("hidden");

  // Reposition if off-screen
  const rect = tt.getBoundingClientRect();
  if (rect.right  > window.innerWidth)  tt.style.left = (x - rect.width  - 16) + "px";
  if (rect.bottom > window.innerHeight) tt.style.top  = (y - rect.height - 16) + "px";
}

/* ============================================================
   Info Panel
   ============================================================ */
function showInfoPanel(place) {
  S.selectedPlace = place;
  const panel = document.getElementById("info-panel");
  document.getElementById("panel-latin").textContent = place.latin_std || place.latin;
  document.getElementById("panel-modern").textContent = place.modern || "(unknown modern name)";

  const color = TYPE_COLORS[place.type] || "#92400E";
  const typeLabel = TYPE_LABELS[place.type] || place.type;
  panel.querySelector(".type-dot").style.background = color;
  panel.querySelector(".type-label").textContent = typeLabel;

  const dl = document.getElementById("panel-details");
  dl.innerHTML = "";

  const segNum = Number(place.tabula_segment ?? place.segment ?? S.selectedSegment);
  const segMeta = S.segments.find((s) => Number(s.number) === segNum);
  const segLabel = segMeta ? `${segMeta.roman} - ${segMeta.label}` : (Number.isFinite(segNum) ? `Segment ${segNum}` : "");

  const items = [
    ["Segment", segLabel],
    ["Province", place.province],
    ["Country", place.country],
  ];

  for (const [label, value] of items) {
    if (!value) continue;
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    if (label === "Country") {
      const flags = countryFlags(value);
      dd.textContent = flags ? `${flags} ${value}` : value;
    } else {
      dd.textContent = value;
    }
    dl.appendChild(dt);
    dl.appendChild(dd);
  }

  // OSM map (interactive — placed in panel so user can zoom/pan it)
  const panelMap = document.getElementById("panel-map");
  const lat = Number(place.lat), lng = Number(place.lng);
  if (panelMap) {
    const hasCoords = Number.isFinite(lat) && Number.isFinite(lng) &&
                      lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;
    if (hasCoords) {
      const dLon = 0.9, dLat = 0.55;
      const bbox = `${(lng-dLon).toFixed(4)},${(lat-dLat).toFixed(4)},${(lng+dLon).toFixed(4)},${(lat+dLat).toFixed(4)}`;
      const src = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat.toFixed(5)},${lng.toFixed(5)}`;
      panelMap.innerHTML = `<iframe loading="lazy" src="${escHtml(src)}" title="Location on OpenStreetMap"></iframe>`;
      panelMap.classList.remove("hidden");
    } else {
      panelMap.innerHTML = "";
      panelMap.classList.add("hidden");
    }
  }

  // Wikipedia link
  const wikiLink = document.getElementById("panel-wiki-link");
  if (wikiLink) {
    const modern = place.modern || "";
    if (modern) {
      wikiLink.href = `https://en.wikipedia.org/w/index.php?search=${encodeURIComponent(modern)}`;
      wikiLink.classList.remove("hidden");
    } else {
      wikiLink.classList.add("hidden");
    }
  }

  // tp-online (Ulm database)
  const tpLink = document.getElementById("panel-tp-link");
  if (tpLink) {
    const href = tpOnlineHref(place);
    if (href) {
      tpLink.href = href;
      tpLink.classList.remove("hidden");
    } else {
      tpLink.classList.add("hidden");
    }
  }


  panel.classList.remove("hidden");
}

function hideInfoPanel() {
  document.getElementById("info-panel").classList.add("hidden");
  S.selectedPlace = null;
}

/* ============================================================
   Search
   ============================================================ */
function setupSearch() {
  const input = document.getElementById("search-input");
  const results = document.getElementById("search-results");
  let debounce = null;

  input.addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(() => {
      const q = input.value.trim().toLowerCase();
      if (q.length < 2) { results.classList.add("hidden"); return; }

      const matches = S.places.filter(p =>
        (p.latin_std || p.latin).toLowerCase().includes(q) ||
        (p.modern && p.modern.toLowerCase().includes(q))
      ).slice(0, 30);

      if (!matches.length) { results.classList.add("hidden"); return; }

      results.innerHTML = matches.map(p => {
        const color = TYPE_COLORS[p.type] || "#92400E";
        return `<div class="search-item" data-id="${p.id}">
          <span class="dot" style="background:${color}"></span>
          <span class="si-latin">${escHtml(p.latin_std || p.latin)}</span>
          <span class="si-modern">${escHtml(p.modern || "")}</span>
        </div>`;
      }).join("");
      results.classList.remove("hidden");
    }, 200);
  });

  results.addEventListener("click", (e) => {
    const item = e.target.closest(".search-item");
    if (!item) return;
    const id = item.dataset.id;
    const place = S.places.find(p => String(p.id) === id);
    if (!place) return;

    // Ensure the place's type is visible before navigating
    if (place.type && !S.activeTypes.has(place.type)) {
      S.activeTypes.add(place.type);
      document.querySelectorAll(`.type-filter-btn[data-type="${place.type}"]`)
        .forEach(b => b.classList.add("active"));
    }

    panToPlace(place);
    startHighlight(place);
    renderMarkers();

    results.classList.add("hidden");
    input.value = "";
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest("#search-container")) {
      results.classList.add("hidden");
    }
  });
}

function panToPlace(place) {
  if (S.mapMode === "old") {
    const millerAspect = MILLER_H / MILLER_W;
    const mhw = S.isMobile ? 0.008 : 0.02;
    const mc = S.millerCalib.find(m => m.data_id === place.data_id);
    if (mc) {
      const cx = (mc.rect_x1 + mc.rect_x2) / 2 / MILLER_W;
      const cy = (mc.rect_y1 + mc.rect_y2) / 2 / MILLER_W;
      S.highlightVp = { vx: cx, vy: cy };
      S.viewer.viewport.fitBounds(
        new OpenSeadragon.Rect(cx - mhw, cy - mhw * millerAspect, mhw * 2, mhw * 2 * millerAspect)
      );
    } else {
      // Estimate from tabula segment/row when no calibration exists
      const seg = Number(place.tabula_segment);
      const segIdx = Number.isFinite(seg) ? (seg - 2) : 5;
      const estVx = (segIdx + 0.5) / 11;
      const rowMap = { a: 1 / 6, b: 1 / 2, c: 5 / 6 };
      const estVy = (rowMap[place.tabula_row] ?? 0.5) * millerAspect;
      S.highlightVp = { vx: estVx, vy: estVy };
      S.viewer.viewport.fitBounds(
        new OpenSeadragon.Rect(estVx - mhw, estVy - mhw * millerAspect, mhw * 2, mhw * 2 * millerAspect)
      );
    }
    return;
  }
  if (S.newSourceKind === "stitched") {
    const statusEl = document.getElementById("status");
    if (statusEl) statusEl.textContent = "Place overlays are calibrated for the readable 150dpi segment IV source.";
    return;
  }
  const aspect = IMG_H / IMG_W;
  const vx = Number.isFinite(place.vx) ? place.vx : 0.5;
  const vy = Number.isFinite(place.vy) ? place.vy : 0.5;
  S.highlightVp = { vx, vy };
  const hw = S.isMobile ? 0.008 : 0.02;
  S.viewer.viewport.fitBounds(
    new OpenSeadragon.Rect(vx - hw, vy - hw * aspect, hw * 2, hw * 2 * aspect)
  );
}

/* ============================================================
   Controls
   ============================================================ */
function setupControls() {
  document.getElementById("control-zoom-in").addEventListener("click", () => {
    S.viewer.viewport.zoomBy(1.4);
    S.viewer.viewport.applyConstraints();
  });
  document.getElementById("control-zoom-out").addEventListener("click", () => {
    S.viewer.viewport.zoomBy(0.7);
    S.viewer.viewport.applyConstraints();
  });
  document.getElementById("control-home").addEventListener("click", () => {
    focusSegment(S.selectedSegment);
  });
  document.getElementById("control-fullpage").addEventListener("click", () => {
    if (S.viewer.isFullPage()) {
      S.viewer.setFullScreen(false);
    } else {
      S.viewer.setFullScreen(true);
    }
  });

  // Calibration overlay toggle
  const overlayBtn = document.getElementById("toggle-overlay");
  if (overlayBtn) {
    overlayBtn.addEventListener("click", () => {
      S.millerOverlayOn = !S.millerOverlayOn;
      overlayBtn.classList.toggle("active", S.millerOverlayOn);
      renderMarkers();
    });
  }

  // Legend toggle
  document.getElementById("legend-toggle").addEventListener("click", () => {
    S.legendOpen = !S.legendOpen;
    document.getElementById("legend").classList.toggle("open", S.legendOpen);
  });

  // Close info panel
  document.getElementById("close-panel").addEventListener("click", hideInfoPanel);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") hideInfoPanel();
  });

  // Swipe-down to close info panel on mobile
  if (S.isMobile) {
    const panel = document.getElementById("info-panel");
    let swipeStartY = null;
    panel.addEventListener("touchstart", (e) => {
      swipeStartY = e.touches[0].clientY;
    }, { passive: true });
    panel.addEventListener("touchend", (e) => {
      if (swipeStartY === null) return;
      const dy = e.changedTouches[0].clientY - swipeStartY;
      if (dy > 60) hideInfoPanel();
      swipeStartY = null;
    }, { passive: true });
  }

  // Mobile menu
  setupMobileMenu();
}

function setupTypeFilters() {
  const container = document.getElementById("type-filter-buttons");
  if (!container) return;
  const types = Object.keys(TYPE_COLORS);
  container.innerHTML = types.map(t => {
    const color = TYPE_COLORS[t];
    const label = TYPE_LABELS[t];
    const active = S.activeTypes.has(t) ? " active" : "";
    return `<button class="type-filter-btn${active}" data-type="${t}" title="${label}">
      <span class="tf-dot" style="background:${color}"></span>${label}
    </button>`;
  }).join("");
  container.addEventListener("click", (e) => {
    const btn = e.target.closest(".type-filter-btn");
    if (!btn) return;
    const type = btn.dataset.type;
    if (S.activeTypes.has(type)) {
      S.activeTypes.delete(type);
      btn.classList.remove("active");
    } else {
      S.activeTypes.add(type);
      btn.classList.add("active");
    }
    renderMarkers();
  });

  const toggleAllBtn = document.getElementById("toggle-all-types");
  if (toggleAllBtn) {
    toggleAllBtn.addEventListener("click", () => {
      const allActive = S.activeTypes.size === Object.keys(TYPE_COLORS).length;
      if (allActive) {
        S.activeTypes.clear();
        container.querySelectorAll(".type-filter-btn").forEach(b => b.classList.remove("active"));
        toggleAllBtn.classList.remove("active");
        toggleAllBtn.textContent = "Select All";
      } else {
        Object.keys(TYPE_COLORS).forEach(t => S.activeTypes.add(t));
        container.querySelectorAll(".type-filter-btn").forEach(b => b.classList.add("active"));
        toggleAllBtn.classList.add("active");
        toggleAllBtn.textContent = "Select All";
      }
      renderMarkers();
    });
  }

  const labelsBtn = document.getElementById("toggle-labels");
  if (labelsBtn) {
    labelsBtn.addEventListener("click", () => {
      S.labelsOn = !S.labelsOn;
      labelsBtn.classList.toggle("active", S.labelsOn);
      renderMarkers();
    });
  }
}

function setupMobileMenu() {
  const btn = document.getElementById("mobile-menu-btn");
  const menu = document.getElementById("mobile-menu");
  const backdrop = document.getElementById("mobile-menu-backdrop");
  if (!btn || !menu) return;

  function openMenu() {
    // Sync type filter buttons
    const typeContainer = document.getElementById("mobile-type-filter-buttons");
    const types = Object.keys(TYPE_COLORS);
    const allOn = S.activeTypes.size === types.length;
    typeContainer.innerHTML =
      `<button class="ctrl-btn toggle-btn${allOn ? " active" : ""}" id="mobile-toggle-all" style="width:100%;margin-bottom:6px">Select All</button>` +
      types.map(t => {
        const color = TYPE_COLORS[t];
        const label = TYPE_LABELS[t];
        const active = S.activeTypes.has(t) ? " active" : "";
        return `<button class="type-filter-btn${active}" data-type="${t}" title="${label}">
          <span class="tf-dot" style="background:${color}"></span>${label}
        </button>`;
      }).join("");

    typeContainer.querySelector("#mobile-toggle-all").addEventListener("click", (e) => {
      const allActive = S.activeTypes.size === types.length;
      if (allActive) {
        S.activeTypes.clear();
        typeContainer.querySelectorAll(".type-filter-btn").forEach(b => b.classList.remove("active"));
        e.currentTarget.classList.remove("active");
        document.querySelectorAll("#type-filter-buttons .type-filter-btn").forEach(b => b.classList.remove("active"));
        document.getElementById("toggle-all-types")?.classList.remove("active");
      } else {
        types.forEach(t => S.activeTypes.add(t));
        typeContainer.querySelectorAll(".type-filter-btn").forEach(b => b.classList.add("active"));
        e.currentTarget.classList.add("active");
        document.querySelectorAll("#type-filter-buttons .type-filter-btn").forEach(b => b.classList.add("active"));
        document.getElementById("toggle-all-types")?.classList.add("active");
      }
      renderMarkers();
    });

    typeContainer.addEventListener("click", (e) => {
      const b = e.target.closest(".type-filter-btn");
      if (!b) return;
      const t = b.dataset.type;
      if (S.activeTypes.has(t)) { S.activeTypes.delete(t); b.classList.remove("active"); }
      else { S.activeTypes.add(t); b.classList.add("active"); }
      // Mirror to desktop buttons
      document.querySelectorAll(`#type-filter-buttons .type-filter-btn[data-type="${t}"]`)
        .forEach(db => db.classList.toggle("active", S.activeTypes.has(t)));
      renderMarkers();
    });

    // Sync segment buttons
    const segContainer = document.getElementById("mobile-segment-buttons");
    segContainer.innerHTML = document.getElementById("segment-buttons").innerHTML;
    segContainer.addEventListener("click", (e) => {
      const b = e.target.closest(".seg-btn");
      if (!b) return;
      const seg = Number(b.dataset.seg);
      focusSegment(seg);
      closeMenu();
    });

    // Labels toggle
    const dispContainer = document.getElementById("mobile-display-controls");
    dispContainer.innerHTML = `<button class="ctrl-btn toggle-btn${S.labelsOn ? " active" : ""}" id="mobile-toggle-labels">Labels</button>`;
    dispContainer.querySelector("#mobile-toggle-labels").addEventListener("click", (e) => {
      S.labelsOn = !S.labelsOn;
      e.currentTarget.classList.toggle("active", S.labelsOn);
      document.getElementById("toggle-labels")?.classList.toggle("active", S.labelsOn);
      renderMarkers();
    });

    menu.classList.remove("hidden");
  }

  function closeMenu() { menu.classList.add("hidden"); }

  btn.addEventListener("click", openMenu);
  backdrop.addEventListener("click", closeMenu);
}

function activeTileSource() {
  return S.originalTile;
}

/* ============================================================
   Tile source swap (old ↔ new)
   ============================================================ */
function swapTileSource(callback, previousMode = S.mapMode) {
  const vp = S.viewer.viewport;
  const center = vp.getCenter();
  const zoom = vp.getZoom();

  const oldBounds = getSegmentBounds(S.selectedSegment, boundsKeyForMode(previousMode));
  const oldRx = oldBounds ? (center.x - oldBounds.x0) / Math.max(oldBounds.x1 - oldBounds.x0, 0.00001) : 0.5;
  const oldRy = oldBounds ? (center.y - oldBounds.y0) / Math.max(oldBounds.y1 - oldBounds.y0, 0.00001) : 0.5;

  const source = activeTileSource();
  S.viewer.open(source);

  S.viewer.addOnceHandler("open", () => {
    const newBounds = getSegmentBounds(S.selectedSegment, activeBoundsKey());
    if (newBounds) {
      const nx = newBounds.x0 + oldRx * Math.max(newBounds.x1 - newBounds.x0, 0.00001);
      const ny = newBounds.y0 + oldRy * Math.max(newBounds.y1 - newBounds.y0, 0.00001);
      vp.zoomTo(zoom, null, true);
      vp.panTo(new OpenSeadragon.Point(nx, ny), true);
    } else {
      focusSegment(DEFAULT_SEGMENT, true);
    }
    renderMarkers();
    if (callback) callback();
  });
}

/* ============================================================
   Mouse / touch events
   ============================================================ */
function setupInteraction() {
  let lastHovered = null;

  new OpenSeadragon.MouseTracker({
    element: S.viewer.element,
    moveHandler: (e) => {
      if (S.isMobile) return;
      const pos = e.position;
      const elRect = S.viewer.element.getBoundingClientRect();
      const clientX = elRect.left + pos.x;
      const clientY = elRect.top + pos.y;

      // Don't show tooltip when cursor is over the info panel
      const panel = document.getElementById("info-panel");
      if (panel && !panel.classList.contains("hidden")) {
        const pr = panel.getBoundingClientRect();
        if (clientX >= pr.left && clientX <= pr.right && clientY >= pr.top && clientY <= pr.bottom) {
          hideTooltip();
          return;
        }
      }

      const tt = document.getElementById("tooltip");

      // SegIV markers (new map mode)
      const place = hitTest(clientX, clientY);
      if (place) {
        S.viewer.element.style.cursor = "pointer";
        if (place !== lastHovered) {
          showTooltip(place, clientX, clientY);
          lastHovered = place;
        } else {
          tt.style.left = (clientX + 24) + "px";
          tt.style.top  = (clientY - 20) + "px";
        }
        return;
      }

      // Miller calibration overlay rects (old map mode)
      const millerItem = hitTestMillerOverlay(clientX, clientY);
      if (millerItem) {
        S.viewer.element.style.cursor = "pointer";
        if (millerItem !== lastHovered) {
          showMillerTooltip(millerItem, clientX, clientY);
          lastHovered = millerItem;
        }
        // Don't reposition the rich tooltip while it's shown — the iframe would reload
        return;
      }

      S.viewer.element.style.cursor = "default";
      hideTooltip();
      lastHovered = null;
    },
    leaveHandler: () => { if (!S.isMobile) { hideTooltip(); lastHovered = null; } },
  });

  S.viewer.addHandler("canvas-click", (e) => {
    const pos = e.position;
    const elRect = S.viewer.element.getBoundingClientRect();
    const clientX = elRect.left + pos.x;
    const clientY = elRect.top + pos.y;

    // SegIV marker click
    const place = hitTest(clientX, clientY);
    if (place) {
      showInfoPanel(place);
      e.preventDefaultAction = true;
      return;
    }

    // Miller overlay click — open info panel with available data
    const millerItem = hitTestMillerOverlay(clientX, clientY);
    if (millerItem) {
      showInfoPanel({
        latin_std:      millerItem.latin_std,
        latin:          millerItem.latin_std,
        modern:         millerItem.modern,
        type:           millerItem.type,
        province:       millerItem.province,
        country:        millerItem.country,
        lat:            millerItem.lat,
        lng:            millerItem.lng,
        data_id:        millerItem.data_id,
        tabula_segment: millerItem.tabula_segment,
        tabula_row:     millerItem.tabula_row,
        tabula_col:     millerItem.tabula_col,
        grid_col:       millerItem.tabula_col,
        grid_row:       millerItem.tabula_row,
        source:         "tabula",
      });
      e.preventDefaultAction = true;
      return;
    }

    // Nothing hit — close info panel if open
    const panel = document.getElementById("info-panel");
    if (!panel.classList.contains("hidden")) hideInfoPanel();
  });
}

/* ============================================================
   Utility
   ============================================================ */
const COUNTRY_TO_ISO2 = {
  D:"DE",A:"AT",I:"IT",IT:"IT",Italy:"IT",F:"FR",E:"ES",P:"PT",H:"HU",B:"BE",
  NL:"NL",CH:"CH",CY:"CY",GB:"GB",GR:"GR",TR:"TR",BG:"BG",RO:"RO",HR:"HR",
  AL:"AL",MK:"MK",MNE:"ME",BIH:"BA",YU:"RS",SLO:"SI",RKS:"XK",V:"VA",
  TN:"TN",DZ:"DZ",MA:"MA",LAR:"LY",IL:"IL",RL:"LB",SYR:"SY",IRQ:"IQ",
  IR:"IR",JOR:"JO",GE:"GE",ARM:"AM",AZ:"AZ",RUS:"RU",UA:"UA",TM:"TM",
  PAK:"PK",AFG:"AF",IND:"IN",ET:"EG",IRE:"IE",
};

function countryFlags(raw) {
  if (!raw) return "";
  return raw.split("|").map(c => {
    const t = c.trim();
    const iso = COUNTRY_TO_ISO2[t] || (t.length === 2 ? t.toUpperCase() : null);
    if (!iso || iso.length !== 2) return "";
    return String.fromCodePoint(0x1F1E6 + iso.charCodeAt(0) - 65, 0x1F1E6 + iso.charCodeAt(1) - 65);
  }).filter(Boolean).join("");
}

function tpOnlineHref(place) {
  const rid = String(place.record_id || place.id || "");
  const m = /^TP:(\d+)$/.exec(rid);
  if (m) return `https://tp-online.ku.de/trefferanzeige.php?id=${m[1]}`;
  if (place.source === "tabula") {
    const did = Number(place.data_id);
    if (Number.isFinite(did) && did > 0 && did < 2000000)
      return `https://tp-online.ku.de/trefferanzeige.php?id=${did}`;
  }
  return "";
}

function escHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function tabulaSectionHref(place) {
  const segment = Number(place.tabula_segment ?? place.segment);
  const row = String(place.tabula_row ?? place.grid_row ?? "").trim().toLowerCase();
  const col = Number(place.tabula_col ?? place.grid_col);
  if (!Number.isFinite(segment) || segment < 1 || !/^[abc]$/.test(row) || !Number.isFinite(col) || col < 1) {
    return "";
  }
  const segmValue = Math.max(segment - 1, 0).toString(16);
  return `https://www.tabula-peutingeriana.de/tp/tabula.html?segm=${segmValue}#${row}${Math.trunc(col)}`;
}

function tabulaSourceHref(place) {
  const sectionHref = tabulaSectionHref(place);
  if (sectionHref) {
    return sectionHref;
  }
  const dataId = Number(place.data_id);
  if (place.source === "tabula" && Number.isFinite(dataId) && dataId > 0) {
    return `https://www.tabula-peutingeriana.de/tp/${Math.trunc(dataId)}.html`;
  }
  return "";
}

/* ============================================================
   Initialisation
   ============================================================ */
async function init() {
  const segmentsMeta = await loadJSONOptional("data/segments.json", null);
  const segmentList = Array.isArray(segmentsMeta?.segments) ? segmentsMeta.segments : [];
  S.segments = segmentList.length ? segmentList : [
    { number: 2, roman: "II", label: "Segment II" },
    { number: 3, roman: "III", label: "Segment III" },
    { number: 4, roman: "IV", label: "Segment IV" },
    { number: 5, roman: "V", label: "Segment V" },
    { number: 6, roman: "VI", label: "Segment VI" },
    { number: 7, roman: "VII", label: "Segment VII" },
    { number: 8, roman: "VIII", label: "Segment VIII" },
    { number: 9, roman: "IX", label: "Segment IX" },
    { number: 10, roman: "X", label: "Segment X" },
    { number: 11, roman: "XI", label: "Segment XI" },
    { number: 12, roman: "XII", label: "Segment XII" },
  ];

  const segmentNumbers = S.segments.map((s) => Number(s.number)).filter((n) => Number.isFinite(n));
  if (!segmentNumbers.includes(S.selectedSegment)) {
    S.selectedSegment = segmentNumbers[0] || DEFAULT_SEGMENT;
  }

  const boundsConfig = await loadJSONOptional("data/map_segment_bounds.json", null);
  const oldDefaultBounds = buildUniformBounds(segmentNumbers);
  const stitchedDefaultBounds = buildUniformBounds(segmentNumbers);
  S.boundsBySource.old = boundsConfig?.maps?.old?.segments || oldDefaultBounds;
  S.boundsBySource.stitched = boundsConfig?.maps?.stitched?.segments || stitchedDefaultBounds;
  S.boundsBySource.readableSeg4 = boundsConfig?.maps?.readableSeg4?.segments || { "4": { x0: 0, y0: 0, x1: 1, y1: 1 } };

  const db = await loadJSON("data/review_places_db.json?" + Date.now());
  const rawRecords = Array.isArray(db) ? db : (Array.isArray(db.records) ? db.records : []);
  console.log(`[TP] DB loaded: ${rawRecords.length} records, ` +
    `${rawRecords.filter(r => r.miller_rect_x1 != null).length} with Miller calibrations`);
  const placeData = rawRecords
    .filter((r) => {
      if (!r || typeof r !== "object") return false;
      if (!MAP_RUNTIME_TYPES.has(r.type)) return false;
      return Number.isFinite(Number(r.px)) && Number.isFinite(Number(r.py));
    })
    .map((r, idx) => ({
      ...r,
      id: r.id ?? r.record_id ?? `${r.source || "r"}-${r.data_id ?? idx}`,
      latin_std: r.latin_std || r.latin,
      modern: r.modern_preferred || r.modern_tabula || r.modern_omnesviae || "",
      province: r.province || r.region || "",
      grid_col: r.grid_col ?? r.tabula_col,
      grid_row: r.grid_row ?? r.tabula_row,
      px: Number(r.px),
      py: Number(r.py),
      data_id: Number.isFinite(Number(r.data_id)) ? Number(r.data_id) : r.data_id,
    }));
  const draftMap = loadCalibrateDraftMap();
  S.millerCalib = loadMillerCalib(rawRecords);

  // Viewport coordinates: OSD normalises by width, so vx = px/IMG_W, vy = py/IMG_W
  S.places = placeData.map(p => ({
    ...p,
    ...(Number.isFinite(Number(p.data_id)) ? (draftMap.get(Number(p.data_id)) || {}) : {}),
    vx: p.px / IMG_W,
    vy: p.py / IMG_W,
  }));

  // Readable tile source (Weber segment IV DZI)
  const isFile = window.location.protocol === "file:";
  S.readableTile = isFile ? {
    Image: {
      xmlns: "http://schemas.microsoft.com/deepzoom/2008",
      Url: "Readable_SegIV_files/",
      Format: "jpeg", Overlap: "1", TileSize: "254",
      Size: { Width: "4371", Height: "2105" }
    }
  } : "Readable_SegIV.dzi";

  // Original tile source (Miller full image)
  S.originalTile = isFile ? {
    Image: {
      xmlns: "http://schemas.microsoft.com/deepzoom/2008",
      Url: "Tabula_Peutingeriana_-_Miller_files/",
      Format: "jpeg", Overlap: "1", TileSize: "254",
      Size: { Width: "46380", Height: "2953" }
    }
  } : "Tabula_Peutingeriana_-_Miller.dzi";

  const stitchedEnabled = Boolean(boundsConfig?.maps?.stitched?.enabled);
  if (stitchedEnabled) {
    const stitchedSize = boundsConfig?.maps?.stitched?.size || {};
    if (isFile && Number.isFinite(Number(stitchedSize.width)) && Number.isFinite(Number(stitchedSize.height))) {
      const tileFolder = String(boundsConfig?.maps?.stitched?.tileFolder || "Tabula_Peutingeriana_150dpi_Stitched_files/");
      S.stitchedTile = {
        Image: {
          xmlns: "http://schemas.microsoft.com/deepzoom/2008",
          Url: tileFolder,
          Format: "jpeg", Overlap: "1", TileSize: "254",
          Size: { Width: String(Math.trunc(Number(stitchedSize.width))), Height: String(Math.trunc(Number(stitchedSize.height))) }
        }
      };
    } else {
      S.stitchedTile = String(boundsConfig?.maps?.stitched?.dzi || "Tabula_Peutingeriana_150dpi_Stitched.dzi");
    }
    S.newSourceKind = "stitched";
  } else {
    S.newSourceKind = "readable-seg4";
  }

  // Start on new map mode.
  S.viewer = OpenSeadragon({
    id: "openseadragon1",
    prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.0/images/",
    showNavigationControl: false,
    tileSources: activeTileSource(),
    showNavigator: true,
    navigatorPosition: "BOTTOM_RIGHT",
    navigatorAutoFade: true,
    defaultZoomLevel: 0,
    minZoomLevel: 0,
    maxZoomLevel: 80,
    visibilityRatio: 0.05,
    constrainDuringPan: false,
    blendTime: 0.1,
    animationTime: 0.5,
    backgroundColor: "#0f1117",
  });

  // Canvas setup
  S.canvas = document.getElementById("marker-canvas");
  S.ctx = S.canvas.getContext("2d");

  let initialFocused = false;

  S.viewer.addHandler("animation", renderMarkers);
  S.viewer.addHandler("animation-finish", renderMarkers);
  S.viewer.addHandler("resize", () => { sizeCanvas(); renderMarkers(); });
  S.viewer.addHandler("open", () => {
    sizeCanvas();
    if (!initialFocused) {
      focusSegment(S.selectedSegment, true);
      initialFocused = true;
    }
    renderMarkers();
  });

  window.addEventListener("resize", () => { sizeCanvas(); renderMarkers(); });

  // Setup UI
  setupSegmentSelector();
  setupTypeFilters();
  setupControls();
  setupSearch();
  setupInteraction();

  console.log(`Tabula Peutingeriana loaded: ${S.places.length} seg4 places, ${S.millerCalib.length} Miller calibrations`);
}

window.addEventListener("DOMContentLoaded", init);
