/* ANIMATE core v0.7.0. No network, no dependencies. Pure functions for deterministic testing. */
(function (root) {
'use strict';

const clamp = (x, a, b) => Math.max(a, Math.min(b, x));

function rgb2hsv(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const m = Math.max(r, g, b), n = Math.min(r, g, b), d = m - n;
  let h = 0;
  if (d) {
    if (m === r) h = ((g - b) / d) % 6;
    else if (m === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h *= 60;
    if (h < 0) h += 360;
  }
  return [h, m ? d / m : 0, m];
}

function hueDist(a, b) {
  const d = Math.abs(a - b);
  return Math.min(d, 360 - d);
}

/* Reference colour from a (2*half+1)^2 patch: circular-mean hue, median s and v.
   Replaces "brightest single pixel in 5x5", which locked onto sensor noise / specular glints. */
function sampleReference(data, w, h, cx, cy, half) {
  half = half || 3;
  let sx = 0, sy = 0, n = 0;
  const ss = [], vs = [];
  for (let y = clamp(cy - half, 0, h - 1); y <= clamp(cy + half, 0, h - 1); y++) {
    for (let x = clamp(cx - half, 0, w - 1); x <= clamp(cx + half, 0, w - 1); x++) {
      const i = (y * w + x) * 4;
      const [hh, s, v] = rgb2hsv(data[i], data[i + 1], data[i + 2]);
      if (v < 0.15) continue;
      sx += Math.cos(hh * Math.PI / 180) * s; sy += Math.sin(hh * Math.PI / 180) * s;
      ss.push(s); vs.push(v); n++;
    }
  }
  if (n < 5) return null;
  ss.sort((a, b) => a - b); vs.sort((a, b) => a - b);
  let hue = Math.atan2(sy, sx) * 180 / Math.PI; if (hue < 0) hue += 360;
  const s = ss[n >> 1], v = vs[n >> 1];
  return (s < 0.3 || v < 0.22) ? null : [hue, s, v];
}

/* Hue 345-50 deg with moderate saturation overlaps human skin; colour keying cannot separate them. */
function skinLike(ref) { return !!ref && (ref[0] <= 50 || ref[0] >= 345) && ref[1] < 0.72; }

const DEFAULTS = { hueTol: 22, satFloor: 0.28, satSlack: 0.35, vMin: 0.18, vSlack: 0.55,
                   minCells: 6, maxFrac: 0.25, link: 2, minDensity: 0.3 };

/* Colour-blob locator.
   v0.1 took the centroid of EVERY matching pixel and rejected the frame if the bounding box was sparse,
   so one stray matching pixel 40 px away returned null. v0.2 averages 2x2 blocks (noise), labels connected
   cells (gap tolerance `link`), and reports the LARGEST component only. */
function locate(data, w, h, ref, opts) {
  if (!ref || ref[1] < 0.3) return null;
  const o = Object.assign({}, DEFAULTS, opts || {});
  const gw = Math.floor(w / 2), gh = Math.floor(h / 2), N = gw * gh;
  const mask = new Uint8Array(N);
  const sMin = Math.max(o.satFloor, ref[1] - o.satSlack);
  let total = 0;
  for (let gy = 0; gy < gh; gy++) {
    for (let gx = 0; gx < gw; gx++) {
      let r = 0, g = 0, b = 0;
      for (let dy = 0; dy < 2; dy++) for (let dx = 0; dx < 2; dx++) {
        const i = ((gy * 2 + dy) * w + gx * 2 + dx) * 4;
        r += data[i]; g += data[i + 1]; b += data[i + 2];
      }
      const [hh, s, v] = rgb2hsv(r / 4, g / 4, b / 4);
      if (hueDist(hh, ref[0]) <= o.hueTol && s >= sMin && v >= o.vMin && Math.abs(v - ref[2]) <= o.vSlack) {
        mask[gy * gw + gx] = 1; total++;
      }
    }
  }
  if (total < o.minCells) return null;
  const seen = new Uint8Array(N), stack = [];
  let best = null, second = 0;
  for (let s0 = 0; s0 < N; s0++) {
    if (!mask[s0] || seen[s0]) continue;
    let n = 0, sx = 0, sy = 0, x0 = gw, y0 = gh, x1 = 0, y1 = 0;
    seen[s0] = 1; stack.push(s0);
    while (stack.length) {
      const c = stack.pop(), cx = c % gw, cy = (c / gw) | 0;
      n++; sx += cx; sy += cy;
      if (cx < x0) x0 = cx; if (cx > x1) x1 = cx; if (cy < y0) y0 = cy; if (cy > y1) y1 = cy;
      for (let dy = -o.link; dy <= o.link; dy++) {
        const ny = cy + dy; if (ny < 0 || ny >= gh) continue;
        for (let dx = -o.link; dx <= o.link; dx++) {
          const nx = cx + dx; if (nx < 0 || nx >= gw) continue;
          const k = ny * gw + nx;
          if (mask[k] && !seen[k]) { seen[k] = 1; stack.push(k); }
        }
      }
    }
    const density = n / ((x1 - x0 + 1) * (y1 - y0 + 1));
    const comp = { n, x: (sx / n * 2 + 1) / w, y: (sy / n * 2 + 1) / h, density };
    if (!best || n > best.n) { if (best) second = Math.max(second, best.n); best = comp; }
    else second = Math.max(second, n);
  }
  if (!best || best.n < o.minCells || best.n / N > o.maxFrac || best.density < o.minDensity) return null;
  return { x: best.x, y: best.y, fraction: best.n / N, cells: best.n, ambiguous: second >= 0.6 * best.n };
}

/* Zone tracker: hysteresis instead of a dead band, and a dropout grace period instead of resetting on one
   missed frame (v0.1 reset the dwell on every null frame and ignored 10% of the width). */
function createZoneTracker(opt) {
  const dwell = opt?.dwellMs ?? 260;
  const grace = opt?.graceMs ?? 150;
  const hyst = opt?.hyst ?? 0.03;
  if (!Number.isFinite(dwell) || dwell <= 0 || !Number.isFinite(grace) || grace < 0 ||
      !Number.isFinite(hyst) || hyst < 0 || hyst >= 1 / 3) throw Error('Invalid tracker options');
  let zone = null, since = null, lastSeen = null, lastUpdate = null;
  function zoneOf(x, cur) {
    if (cur !== null && x >= cur / 3 - hyst && x < (cur + 1) / 3 + hyst) return cur;
    return Math.min(2, Math.max(0, Math.floor(x * 3)));
  }
  function reset() { zone = null; since = null; lastSeen = null; lastUpdate = null; }
  return {
    reset,
    update(p, now) {
      if (!Number.isFinite(now)) { reset(); return { zone: null, fired: null }; }
      // A long scheduler gap is not continuous observed dwell, even if no null frames arrived.
      if (lastUpdate !== null && (now < lastUpdate || now - lastUpdate > grace)) reset();
      lastUpdate = now;
      if (!p || !Number.isFinite(p.x) || p.x < 0 || p.x > 1 || p.ambiguous) {
        if (lastSeen !== null && now - lastSeen > grace) { zone = null; since = null; }
        return { zone, fired: null };
      }
      // Do not retroactively count an interval where the object was unobserved.
      if (lastSeen !== null && now - lastSeen > grace) { zone = null; since = null; }
      const z = zoneOf(p.x, zone);
      lastSeen = now;
      if (z !== zone || since === null) { zone = z; since = now; }
      if (now - since >= dwell) { since = now; return { zone, fired: z }; }
      return { zone, fired: null };
    }
  };
}

function localDay(d) {
  d = d || new Date();
  const p = n => String(n).padStart(2, '0');
  return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
}
function dayDiff(a, b) {
  const t = s => { const [y, m, d] = s.split('-').map(Number); return Date.UTC(y, m - 1, d); };
  return Math.round((t(b) - t(a)) / 864e5);
}

const BUILD = '0.7.0';
const SCHEMA_VERSION = 5;
const MAX_EVENTS = 2000;
const modes = ['play', 'create', 'learn'];
// Self-declared customer segments, not independently verified identities.
const roles = ['Game creator', 'Content creator', 'Parent / family', 'Educator', 'Developer', 'Other'];
const probeColours = ['blue', 'green', 'red', 'other'];
const probeLights = ['bright', 'normal', 'dim'];
const probeBackgrounds = ['plain', 'cluttered'];
const probeExpected = ['present', 'absent'];
const PROBE_FRAMES = 600;

/* This manually labelled on-device probe does NOT establish spatial ground truth or object identity.
   It measures what the colour locator reports under an operator-specified condition. */
function createRecognitionProbe() {
  let current = null;
  return {
    start(condition) {
      if (!condition || !probeColours.includes(condition.colour) ||
          !probeLights.includes(condition.light) || !probeBackgrounds.includes(condition.background) ||
          !probeExpected.includes(condition.expected)) throw Error('Invalid benchmark condition');
      current = { colour: condition.colour, light: condition.light,
        background: condition.background, expected: condition.expected,
        frames: 0, matched: 0, ambiguous: 0, locateTotalMs: 0, locateMaxMs: 0 };
      return { ...current };
    },
    add(found, elapsedMs) {
      if (!current) return null;
      if (!Number.isFinite(elapsedMs) || elapsedMs < 0 || elapsedMs > 1000) throw Error('Invalid inference time');
      current.frames++;
      if (found && !found.ambiguous) current.matched++;
      if (found?.ambiguous) current.ambiguous++;
      current.locateTotalMs += elapsedMs;
      current.locateMaxMs = Math.max(current.locateMaxMs, elapsedMs);
      return { frames: current.frames, target: PROBE_FRAMES };
    },
    finish() {
      if (!current || !current.frames) return null;
      const sample = { ...current, avgMs: +(current.locateTotalMs / current.frames).toFixed(3),
        maxMs: +current.locateMaxMs.toFixed(3), complete: current.frames >= PROBE_FRAMES };
      delete sample.locateTotalMs; delete sample.locateMaxMs;
      current = null;
      return sample;
    },
    cancel() { current = null; },
    get active() { return !!current; },
    get progress() { return current?.frames || 0; },
  };
}

/* Reject non-isolated calibration blobs and mismatched taps. This cannot tell two same-colour
   objects apart and is not a machine-learning recognition system. */
function calibrationCandidate(data, w, h, ref, x, y, maxDistance = .14) {
  if (!Number.isFinite(x) || !Number.isFinite(y) || x < 0 || x > 1 || y < 0 || y > 1) return null;
  const candidate = locate(data, w, h, ref);
  if (!candidate || candidate.ambiguous || Math.hypot(candidate.x - x, candidate.y - y) > maxDistance) return null;
  return candidate;
}

// Accept only real Gregorian calendar days and canonical UTC ISO timestamps produced by the app.
// Date.parse() alone normalises dates such as February 30 instead of rejecting them.
const dayOK = s => {
  if (typeof s !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
  const year = Number(s.slice(0, 4)), month = Number(s.slice(5, 7)), day = Number(s.slice(8, 10));
  const date = new Date(0);
  date.setUTCFullYear(year, month - 1, day);
  date.setUTCHours(0, 0, 0, 0);
  return date.getUTCFullYear() === year && date.getUTCMonth() + 1 === month && date.getUTCDate() === day;
};
const dateOK = s => {
  if (typeof s !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(s) ||
      !dayOK(s.slice(0, 10))) return false;
  const time = Date.parse(s);
  return Number.isFinite(time) && new Date(time).toISOString() === s;
};

// Client-generated events are NOT authenticated. These checks improve metric consistency,
// not fraud resistance. Decision-grade counts also require an independent recruitment ledger.
function sanitizeRecord(r) {
  if (!r || typeof r !== 'object' || Array.isArray(r) || r.version !== SCHEMA_VERSION ||
      r.build !== BUILD || typeof r.id !== 'string' || !/^[a-zA-Z0-9-]{8,80}$/.test(r.id) ||
      !dateOK(r.created) || !dayOK(r.createdDay) || !Array.isArray(r.events) ||
      (r.role !== undefined && !roles.includes(r.role)) ||
      r.events.length > MAX_EVENTS || (r.exportedAt != null && !dateOK(r.exportedAt)) ||
      !['iPhone', 'Android', 'Other'].includes(r.device)) return null;
  const created = Date.parse(r.created);
  // Local-day labels can differ by at most one calendar date from their UTC timestamp.
  if (Math.abs(dayDiff(r.created.slice(0, 10), r.createdDay)) > 1) return null;
  const exported = dateOK(r.exportedAt) ? Date.parse(r.exportedAt) : null;
  if (exported !== null && exported < created) return null;
  const events = [];
  for (const e of r.events) {
    if (!e || typeof e !== 'object' || Array.isArray(e) ||
        typeof e.type !== 'string' || e.type.length > 40 || !dateOK(e.time)) continue;
    const t = Date.parse(e.time);
    if (t < created - 60000 || (exported !== null && t > exported + 60000)) continue;
    // Explicit projection eliminates arbitrary nested/oversized imported properties.
    const safe = { type: e.type, time: e.time };
    if (typeof e.input === 'string' && ['camera', 'touch'].includes(e.input)) safe.input = e.input;
    if (['colour', 'foreground', 'hand'].includes(e.detector)) safe.detector = e.detector;
    if (typeof e.mode === 'string' && modes.includes(e.mode)) safe.mode = e.mode;
    if (e.model === 'mediapipe-hand-landmarker-float16-v1' && e.detector === 'hand') safe.model = e.model;
    if (typeof e.runId === 'string' && /^[a-zA-Z0-9-]{8,80}$/.test(e.runId)) safe.runId = e.runId;
    // A claimed local return-day must be plausible for that event's UTC timestamp.
    if (typeof e.day === 'string' && dayOK(e.day) &&
        Math.abs(dayDiff(e.time.slice(0, 10), e.day)) <= 1) safe.day = e.day;
    if (Number.isInteger(e.days) && e.days >= 0 && e.days <= 365) safe.days = e.days;
    if (Number.isFinite(e.elapsed) && e.elapsed >= 0 && e.elapsed <= 1200000) safe.elapsed = e.elapsed;
    if (e.type === 'benchmark_sample' && e.sample && typeof e.sample === 'object') {
      const s = e.sample;
      if (['colour','foreground'].includes(s.detector) &&
          probeColours.includes(s.colour) && probeLights.includes(s.light) &&
          probeBackgrounds.includes(s.background) && probeExpected.includes(s.expected) &&
          Number.isInteger(s.frames) && s.frames >= 1 && s.frames <= PROBE_FRAMES &&
          Number.isInteger(s.matched) && s.matched >= 0 && s.matched <= s.frames &&
          Number.isInteger(s.ambiguous) && s.ambiguous >= 0 && s.ambiguous <= s.frames &&
          s.ambiguous + s.matched <= s.frames &&
          Number.isFinite(s.avgMs) && s.avgMs >= 0 && s.avgMs <= 1000 &&
          Number.isFinite(s.maxMs) && s.maxMs >= s.avgMs && s.maxMs <= 1000 &&
          typeof s.complete === 'boolean' && s.complete === (s.frames >= PROBE_FRAMES)) {
        safe.sample = { colour: s.colour, light: s.light, background: s.background,
          expected: s.expected, detector: s.detector,
          frames: s.frames, matched: s.matched, ambiguous: s.ambiguous,
          avgMs: s.avgMs, maxMs: s.maxMs, complete: s.complete };
      }
    }
    events.push(safe);
  }
  return { id: r.id, version: r.version, build: r.build, device: r.device,
    role: r.role ?? 'Unspecified',
    created: r.created, createdDay: r.createdDay, exportedAt: r.exportedAt ?? null, events };
}

function recordMetrics(r) {
  const starts = new Map();
  const completedRuns = new Set();
  let cameraStarts = false, validCameraCompletions = 0, touched = false;
  const detectors = new Set(), completedDetectors = new Set();
  let firstValidStart = null;
  for (const e of r.events) {
    if (e.type === 'start' && e.runId && e.mode && e.input &&
        (e.input !== 'camera' || (['colour','foreground','hand'].includes(e.detector) &&
        (e.detector !== 'hand' || e.model === 'mediapipe-hand-landmarker-float16-v1')))) {
      const k = e.runId;
      if (!starts.has(k)) starts.set(k, e);
      if (e.input === 'camera') { cameraStarts = true; detectors.add(e.detector); firstValidStart ??= e.time; }
      else if (e.input === 'touch') touched = true;
    }
    if (e.type === 'complete' && e.runId && e.mode && e.input === 'camera' && e.elapsed !== undefined) {
      const st = starts.get(e.runId);
      if (!st || st.input !== 'camera' || st.mode !== e.mode || st.detector !== e.detector ||
          completedRuns.has(e.runId) || (e.detector === 'hand' &&
          (st.model !== 'mediapipe-hand-landmarker-float16-v1' || e.model !== st.model))) continue;
      const seconds = Date.parse(e.time) - Date.parse(st.time);
      // Permit moderate timing jitter but reject impossible history and instantaneous camera successes.
      if (seconds < 400 || seconds > 1200000 || Math.abs(seconds - e.elapsed) > 10000) continue;
      completedRuns.add(e.runId);
      validCameraCompletions++; completedDetectors.add(e.detector);
    }
  }
  const observable = cameraStarts && r.exportedAt != null &&
    (Date.parse(r.exportedAt) - Date.parse(r.created)) >= 7 * 864e5;
  const returned = observable && r.events.some(e => e.type === 'return' && e.days >= 1 && e.days <= 7 &&
    e.day && dayDiff(r.createdDay, e.day) === e.days &&
    Date.parse(e.time) <= Date.parse(r.exportedAt));
  return { cameraStarts, cameraCompleted: validCameraCompletions > 0, validCameraCompletions,
    observable, returned, touched, detectors: [...detectors], completedDetectors: [...completedDetectors] };
}

function ledgerKey(r) { return r.id + '|' + r.createdDay + '|' + r.device; }
function summarize(records, ledger = []) {
  const unique = new Map();
  let rejected = 0;
  for (const raw of records) {
    const r = sanitizeRecord(raw);
    if (!r) { rejected++; continue; }
    const existing = unique.get(r.id);
    // Prefer most recent valid export, not longest edited history.
    if (!existing || Date.parse(r.exportedAt || r.created) > Date.parse(existing.exportedAt || existing.created)) unique.set(r.id, r);
  }
  const all = [...unique.values()];
  const ledgerSet = new Set(Array.isArray(ledger) ? ledger.filter(v => typeof v === 'string' && v.length < 140) : []);
  const inspected = all.map(r => ({ record: r, metrics: recordMetrics(r), verified: ledgerSet.has(ledgerKey(r)) }));
  const verified = inspected.filter(x => x.verified && x.record.exportedAt !== null);
  const counts = arr => ({
    cameraTesters: arr.filter(x => x.metrics.cameraStarts).length,
    first: arr.filter(x => x.metrics.cameraCompleted).length,
    returnEligible: arr.filter(x => x.metrics.observable).length,
    returnUnobservable: arr.filter(x => x.metrics.cameraStarts && !x.metrics.observable).length,
    returned: arr.filter(x => x.metrics.returned).length
  });
  return {
    build: BUILD, importedRecords: records.length, acceptedRecords: all.length, rejectedRecords: rejected,
    duplicatesRemoved: records.length - rejected - all.length,
    ledgerMatches: verified.length, unmatchedRecords: all.length - verified.length,
    provisional: counts(inspected), verified: counts(verified),
    byDetector: Object.fromEntries(['colour','foreground','hand'].map(detector => [detector, {
      provisionalTesters: inspected.filter(x => x.metrics.detectors.includes(detector)).length,
      provisionalCompleted: inspected.filter(x => x.metrics.completedDetectors.includes(detector)).length,
      verifiedTesters: verified.filter(x => x.metrics.detectors.includes(detector)).length,
      verifiedCompleted: verified.filter(x => x.metrics.completedDetectors.includes(detector)).length
    }])),
    byRole: Object.fromEntries([...roles, 'Unspecified'].map(role => {
      const cohort = inspected.filter(x => x.record.role === role);
      const matched = cohort.filter(x => x.verified && x.record.exportedAt !== null);
      return [role, {
        acceptedExports: cohort.length, verifiedExports: matched.length,
        provisional: counts(cohort), verified: counts(matched)
      }];
    })),
    roleWarning: 'Intended-use categories are self-reported; cohorts are not independent evidence of demand.',
    distinctSecondExperience: 'Not measured: modes share zone-control mechanics',
    pricing: 'Not measured: no pricing or hypothetical purchase prompt',
    evidenceWarning: 'All files are editable self-reports. Ledger matching is procedural, not cryptographic proof.'
  };
}

const core = { BUILD, SCHEMA_VERSION, MAX_EVENTS, clamp, rgb2hsv, hueDist, sampleReference,
  skinLike, locate, createZoneTracker, localDay, dayDiff, modes, roles, sanitizeRecord, ledgerKey,
  recordMetrics, summarize, PROBE_FRAMES, probeColours, probeLights, probeBackgrounds,
  probeExpected, createRecognitionProbe, calibrationCandidate };
if (typeof module !== 'undefined' && module.exports) module.exports = core;
else root.AnimateCore = core;
})(typeof globalThis === 'undefined' ? this : globalThis);
