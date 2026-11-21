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
  let zone = null, confirmedMs = 0, lastSeen = null, lastUpdate = null, previousWasValid = false;
  function zoneOf(x, cur) {
    if (cur !== null && x >= cur / 3 - hyst && x < (cur + 1) / 3 + hyst) return cur;
    return Math.min(2, Math.max(0, Math.floor(x * 3)));
  }
  function reset() {
    zone = null; confirmedMs = 0; lastSeen = null;
    lastUpdate = null; previousWasValid = false;
  }
  return {
    reset,
    update(p, now) {
      if (!Number.isFinite(now)) { reset(); return { zone: null, fired: null }; }
      // A long scheduler gap or backwards timestamp cannot be credited as dwell.
      if (lastUpdate !== null && (now < lastUpdate || now - lastUpdate > grace)) reset();
      const delta = lastUpdate === null ? 0 : now - lastUpdate;
      lastUpdate = now;
      if (!p || !Number.isFinite(p.x) || p.x < 0 || p.x > 1 || p.ambiguous) {
        // Keep prior progress only for a short dropout, but never credit the
        // unobserved interval between a missing frame and a subsequent detection.
        previousWasValid = false;
        if (lastSeen !== null && now - lastSeen > grace) {
          zone = null; confirmedMs = 0;
        }
        return { zone, fired: null };
      }
      if (lastSeen !== null && now - lastSeen > grace) {
        zone = null; confirmedMs = 0; previousWasValid = false;
      }
      const z = zoneOf(p.x, zone);
      if (z !== zone) {
        zone = z; confirmedMs = 0; previousWasValid = false;
      }
      // Only adjacent, successfully observed frames in the same zone accrue
      // dwell time. An explicit null/ambiguous frame interrupts accrual.
      if (previousWasValid) confirmedMs += delta;
      lastSeen = now;
      previousWasValid = true;
      if (confirmedMs >= dwell) { confirmedMs = 0; return { zone, fired: z }; }
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
function sanitizeRecord(r, retainPrivate = false) {
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
    // Keep only a non-identifying measurement flag in researcher summaries.
    // Raw participant exports may contain free-text feedback; never echo that text into summaries.
    if (e.type === 'problem_response' && typeof e.answer === 'string' &&
        e.answer.trim().length > 0 && e.answer.trim().length <= 240) {
      safe.feedbackProvided = true;
      // Only an explicit local-record projection retains participant free text.
      if (retainPrivate) safe.answer = e.answer.trim();
    }
    if (retainPrivate && e.type === 'camera_error') {
      if (typeof e.reason === 'string' && e.reason.length <= 200) safe.reason = e.reason;
      if (typeof e.name === 'string' && /^[A-Za-z][A-Za-z0-9]{0,63}$/.test(e.name)) safe.name = e.name;
    }
    if (retainPrivate && e.type === 'camera_ready' &&
        ['user', 'environment'].includes(e.facing)) safe.facing = e.facing;
    if (retainPrivate && e.type === 'calibrated' && typeof e.skinLike === 'boolean') {
      safe.skinLike = e.skinLike;
    }
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

/**
 * Local-storage and download projection. Browser storage is untrusted: never restore
 * or export arbitrary keys, nested data, or unlimited strings from an edited record.
 * Keep only bounded participant feedback and the app's known diagnostic event fields.
 * Aggregation still calls sanitizeRecord() without private text.
 */
function sanitizeLocalRecord(raw) {
  const clean = sanitizeRecord(raw, true);
  if (!clean) return null;
  // The aggregate-only placeholder is not an enrolment choice; retain legacy omission.
  if (raw.role === undefined) delete clean.role;
  const day = raw.lastDay;
  const elapsedDays = dayOK(day) ? dayDiff(clean.createdDay, day) : -1;
  clean.lastDay = elapsedDays >= 0 && elapsedDays <= 365 ? day : clean.createdDay;
  return clean;
}

function recordMetrics(r) {
  const starts = new Map();
  const completedRuns = new Set();
  const completedCameraModeAt = new Map();
  let cameraStarts = false, validCameraCompletions = 0, touched = false;
  let feedbackRecorded = false, feedbackAfterCameraCompletion = false;
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
      completedCameraModeAt.set(e.mode, Math.min(completedCameraModeAt.get(e.mode) ?? Infinity, Date.parse(e.time)));
    }
    if (e.type === 'problem_response' && e.feedbackProvided) {
      feedbackRecorded = true;
      if (e.input === 'camera' && e.mode && completedCameraModeAt.has(e.mode) &&
          Date.parse(e.time) >= completedCameraModeAt.get(e.mode)) {
        feedbackAfterCameraCompletion = true;
      }
    }
  }
  const observable = cameraStarts && r.exportedAt != null &&
    (Date.parse(r.exportedAt) - Date.parse(r.created)) >= 7 * 864e5;
  const returned = observable && r.events.some(e => e.type === 'return' && e.days >= 1 && e.days <= 7 &&
    e.day && dayDiff(r.createdDay, e.day) === e.days &&
    Date.parse(e.time) <= Date.parse(r.exportedAt));
  return { cameraStarts, cameraCompleted: validCameraCompletions > 0, validCameraCompletions,
    observable, returned, touched, feedbackRecorded, feedbackAfterCameraCompletion,
    detectors: [...detectors], completedDetectors: [...completedDetectors] };
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
    returned: arr.filter(x => x.metrics.returned).length,
    feedbackRespondents: arr.filter(x => x.metrics.feedbackRecorded).length,
    feedbackAfterCameraCompletion: arr.filter(x => x.metrics.feedbackAfterCameraCompletion).length
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
    feedbackWarning: 'Only the number of nonempty, bounded responses is reported. Raw participant exports can contain identifiable free text; review privately and do not publish.',
    distinctSecondExperience: 'Not measured: modes share zone-control mechanics',
    pricing: 'Not measured: no pricing or hypothetical purchase prompt',
    evidenceWarning: 'All files are editable self-reports. Ledger matching is procedural, not cryptographic proof.'
  };
}

/**
 * Voluntary, RAM-only, fixed-duration camera performance sample for an iPhone bench.
 * No user agent, participant ID, timestamps, coordinates, video or model outputs.
 * FPS is analysed-frame throughput, not guaranteed camera sensor FPS.
 */
function createDeviceBench(durationMs = 60000) {
  if (!Number.isInteger(durationMs) || durationMs < 1000 || durationMs > 120000) {
    throw Error('Invalid diagnostic duration');
  }
  let started = null, ended = null, detector = null, outcome = 'not_started';
  let windows = [], inference = [], totalCalls = 0, latencyOverLimit = 0, interruptions = 0;
  let lastWindowAt = null, largestSamplingGapMs = 0, rejectedWindows = 0;
  const requiredWindows = Math.max(1, Math.ceil(durationMs / 1000 * .8));
  const maxPermittedGapMs = 2500;
  const round = n => Math.round(n * 10) / 10;
  const quantile = (values, p) => {
    if (!values.length) return null;
    const sorted = values.slice().sort((a, b) => a - b);
    return round(sorted[Math.ceil(p * sorted.length) - 1]);
  };
  const distribution = values => ({
    samples: values.length,
    min: values.length ? round(Math.min(...values)) : null,
    median: quantile(values, .5),
    p95: quantile(values, .95),
    max: values.length ? round(Math.max(...values)) : null
  });
  const active = () => started !== null && ended === null;
  function coverageIsSufficient() {
    const positiveWindows = windows.filter(w => w.analysedFps > 0).length;
    return windows.length >= requiredWindows && positiveWindows >= requiredWindows &&
      totalCalls >= requiredWindows && rejectedWindows === 0 &&
      largestSamplingGapMs <= maxPermittedGapMs &&
      lastWindowAt !== null &&
      lastWindowAt - started >= durationMs - maxPermittedGapMs;
  }
  function reset() {
    started = null; ended = null; detector = null; outcome = 'not_started';
    windows = []; inference = []; totalCalls = 0; latencyOverLimit = 0; interruptions = 0;
    lastWindowAt = null; largestSamplingGapMs = 0; rejectedWindows = 0;
  }
  function begin(now, method) {
    if (!Number.isFinite(now) || now < 0 || !['colour', 'foreground', 'hand'].includes(method)) {
      throw Error('Invalid diagnostic start');
    }
    reset(); started = now; detector = method; outcome = 'running';
    return snapshot(now);
  }
  function finish(now, reason = 'manual') {
    if (!active()) return snapshot(now);
    if (!Number.isFinite(now) || now < started) throw Error('Invalid diagnostic stop');
    if (!['manual', 'timed', 'camera_stopped', 'interrupted'].includes(reason)) {
      throw Error('Invalid diagnostic result');
    }
    ended = Math.min(now, started + durationMs);
    outcome = reason === 'timed' && !coverageIsSufficient() ?
      'insufficient_coverage' : reason;
    return snapshot(now);
  }
  function noteWindow(now, analysedFps, rafFps) {
    if (!active()) return;
    if (![now, analysedFps, rafFps].every(Number.isFinite) ||
        now <= (lastWindowAt ?? started) || analysedFps < 0 || analysedFps > 240 ||
        rafFps < 0 || rafFps > 240) {
      rejectedWindows++;
      return;
    }
    largestSamplingGapMs = Math.max(largestSamplingGapMs, now - (lastWindowAt ?? started));
    lastWindowAt = now;
    if (windows.length < 120) windows.push({analysedFps, rafFps});
    if (now - started >= durationMs) finish(now, 'timed');
  }
  function noteLatency(ms) {
    if (!active() || !Number.isFinite(ms) || ms < 0) return;
    totalCalls++;
    if (ms <= 120000 && inference.length < 4096) inference.push(ms);
    else latencyOverLimit++;
  }
  function noteInterruption(now) {
    if (!active()) return;
    interruptions++;
    finish(now, 'interrupted');
  }
  function snapshot(now) {
    const elapsed = started === null ? 0 : Math.max(0,
      Math.min(durationMs, (ended ?? (Number.isFinite(now) ? now : started)) - started));
    return {
      kind: 'ANIMATE_LOCAL_DEVICE_PERFORMANCE_SAMPLE', build: BUILD, detector,
      status: outcome, complete: outcome === 'timed', plannedMs: durationMs,
      observedMs: Math.round(elapsed), sampleWindows: windows.length,
      coverage: { requiredWindows, positiveAnalysedWindows:
        windows.filter(w => w.analysedFps > 0).length,
        largestGapMs: round(largestSamplingGapMs), rejectedWindows,
        sufficient: coverageIsSufficient() && elapsed >= durationMs },
      analysedFps: distribution(windows.map(w => w.analysedFps)),
      animationLoopFps: distribution(windows.map(w => w.rafFps)),
      inferenceMs: distribution(inference), inferredFrames: totalCalls,
      unmeasuredLatencySamples: latencyOverLimit, interruptions,
      evidenceType: 'UNVERIFIED_LOCAL_PERFORMANCE_PROXY',
      recognitionAccuracyMeasured: false, commercialDemandMeasured: false,
      contents: 'Numeric performance only. No video, coordinates, IDs, user agent or network upload.',
      limitations: 'Duration alone cannot pass: requires 80% observed and positive analysed windows, inference calls and no sampling gaps over 2.5 seconds. This does not establish sensor FPS, detection accuracy, battery, thermals, real-device provenance or commercial demand.'
    };
  }
  return { begin, finish, reset, noteWindow, noteLatency, noteInterruption, snapshot, active };
}

/**
 * Self-labelled, operator-only zone and absent-target controls.
 * Runs on analysed camera frames only; records bounded counts, never pixels,
 * coordinates, identifiers or a claim of independently verified ground truth.
 */
function createZoneControlProbe(durationMs = 10000) {
  if (!Number.isInteger(durationMs) || durationMs < 3000 || durationMs > 60000) {
    throw Error('Invalid zone-control duration');
  }
  const labels = ['absent', 'left', 'middle', 'right'];
  const zoneIndex = { left: 0, middle: 1, right: 2 };
  const tracker = createZoneTracker();
  const requiredSeconds = Math.ceil(durationMs / 1000 * .8);
  let state = null;
  const within = (time, start) => Number.isFinite(time) && time >= start;
  function begin(now, label, detector) {
    if (!Number.isFinite(now) || now < 0 || !labels.includes(label) ||
        !['colour', 'foreground', 'hand'].includes(detector)) {
      throw Error('Invalid operator zone-control label');
    }
    tracker.reset();
    state = {
      started: now, ended: null, label, detector, status: 'running',
      samples: 0, detectedFrames: 0, absentFrames: 0, ambiguousFrames: 0,
      correctZoneFrames: 0, wrongZoneFrames: 0, expectedDwellEvents: 0,
      unexpectedDwellEvents: 0, rejectedSamples: 0, maxGapMs: 0, lastAt: null,
      secondBuckets: new Map()
    };
    return snapshot(now);
  }
  function active() { return !!state && state.ended === null; }
  function adequatelyObserved() {
    const wellSampledSeconds = [...state.secondBuckets.values()].filter(n => n >= 3).length;
    return !!state && state.samples >= requiredSeconds * 3 &&
      wellSampledSeconds >= requiredSeconds && state.rejectedSamples === 0 &&
      state.maxGapMs <= 2500 && state.lastAt >= state.started + durationMs - 1000;
  }
  function add(point, now) {
    if (!active()) return snapshot(now);
    if (!within(now, state.started) || (state.lastAt !== null && now <= state.lastAt)) {
      state.rejectedSamples++;
      return snapshot(now);
    }
    const gap = now - (state.lastAt ?? state.started);
    state.maxGapMs = Math.max(gap, state.maxGapMs);
    state.lastAt = now;
    state.samples++;
    const bucket = Math.min(Math.floor((now - state.started) / 1000),
      Math.ceil(durationMs / 1000) - 1);
    state.secondBuckets.set(bucket, (state.secondBuckets.get(bucket) || 0) + 1);
    const validPoint = point && !point.ambiguous && Number.isFinite(point.x) &&
      point.x >= 0 && point.x <= 1 && Number.isFinite(point.y) &&
      point.y >= 0 && point.y <= 1;
    if (point?.ambiguous) state.ambiguousFrames++;
    if (validPoint) state.detectedFrames++;
    else state.absentFrames++;
    const result = tracker.update(validPoint ? point : null, now);
    if (state.label !== 'absent') {
      if (validPoint && result.zone === zoneIndex[state.label]) state.correctZoneFrames++;
      else if (validPoint) state.wrongZoneFrames++;
    }
    if (result.fired !== null) {
      if (state.label !== 'absent' && result.fired === zoneIndex[state.label]) {
        state.expectedDwellEvents++;
      } else {
        state.unexpectedDwellEvents++;
      }
    }
    if (now - state.started >= durationMs) finish(now, 'timed');
    return snapshot(now);
  }
  function finish(now, reason = 'manual') {
    if (!active()) return snapshot(now);
    if (!within(now, state.started) || !['timed', 'manual', 'camera_stopped', 'interrupted'].includes(reason)) {
      throw Error('Invalid zone-control stop');
    }
    state.ended = Math.min(now, state.started + durationMs);
    state.status = reason === 'timed' && !adequatelyObserved() ? 'insufficient_coverage' : reason;
    return snapshot(now);
  }
  function snapshot(now) {
    if (!state) return {
      kind: 'ANIMATE_SELF_LABELLED_ZONE_CONTROL', status: 'not_started',
      complete: false, evidenceType: 'OPERATOR_LABELLED_PROXY_NOT_VERIFIED_GROUND_TRUTH'
    };
    const end = state.ended ?? (within(now, state.started) ? now : state.started);
    const elapsedMs = Math.round(Math.min(durationMs, Math.max(0, end - state.started)));
    return {
      kind: 'ANIMATE_SELF_LABELLED_ZONE_CONTROL', build: BUILD,
      detector: state.detector, expectedCondition: state.label,
      evidenceType: 'OPERATOR_LABELLED_PROXY_NOT_VERIFIED_GROUND_TRUTH',
      status: state.status, complete: state.status === 'timed',
      elapsedMs, plannedMs: durationMs,
      coverage: {
        sampledSeconds: state.secondBuckets.size,
        secondsWithThreeFreshFrames: [...state.secondBuckets.values()].filter(n => n >= 3).length,
        requiredSeconds,
        maxGapMs: Math.round(state.maxGapMs), rejectedSamples: state.rejectedSamples,
        adequate: adequatelyObserved() && elapsedMs >= durationMs
      },
      analysedFrames: state.samples, detectedFrames: state.detectedFrames,
      undetectedFrames: state.absentFrames, ambiguousFrames: state.ambiguousFrames,
      correctZoneFrames: state.correctZoneFrames, wrongZoneFrames: state.wrongZoneFrames,
      expectedDwellEvents: state.expectedDwellEvents,
      unexpectedDwellEvents: state.unexpectedDwellEvents,
      independentlyVerified: false, userDemandMeasured: false,
      limitations: 'Requires three analysed frames in each of 80% of seconds. One manually labelled static condition. Dwell events are proxy activations, not observed task completions. An absent-labelled false alarm is an operator-reported proxy, not independently verified accuracy.'
    };
  }
  function reset() { state = null; tracker.reset(); }
  return { begin, add, finish, snapshot, reset, active };
}

/**
 * Remove only the ANIMATE research-data namespace across historical build versions.
 * Snapshot keys before deletion, since deleting while iterating shifts localStorage indices.
 * Report blocked/partial deletion instead of suggesting that a reset definitely succeeded.
 * Does not affect records previously downloaded, sent, or backed up outside this origin.
 */
function deleteLocalResearchData(storage) {
  let removed = 0, failed = 0;
  try {
    const keys = [];
    for (let index = 0; index < storage.length; index++) {
      const key = storage.key(index);
      if (typeof key === 'string' &&
          (key === 'animate-validation' || key.startsWith('animate-validation-'))) {
        keys.push(key);
      }
    }
    for (const key of keys) {
      try {
        storage.removeItem(key);
        if (storage.getItem(key) === null) removed++;
        else failed++;
      } catch (_) {
        failed++;
      }
    }
    return { ok: failed === 0, removed, failed };
  } catch (_) {
    return { ok: false, removed, failed: failed + 1 };
  }
}

/**
 * Operator-only, RAM-only packaging of the existing numeric camera reports.
 * A report packet is self-asserted, never proof of a physical device, authentic
 * commit provenance, recognition accuracy, customer demand, or acquisition value.
 * All report fields are checked against a closed schema to prohibit leaking
 * unreviewed frame data, participant identifiers, or arbitrary free text.
 */
function createOperatorPacketRecorder() {
  const methods = ['colour', 'foreground'];
  const lighting = ['bright', 'ordinary', 'dim'];
  const statuses = ['timed', 'manual', 'camera_stopped', 'interrupted', 'insufficient_coverage'];
  const deviceFields = ['kind','build','detector','status','complete','plannedMs','observedMs',
    'sampleWindows','coverage','analysedFps','animationLoopFps','inferenceMs','inferredFrames',
    'unmeasuredLatencySamples','interruptions','evidenceType','recognitionAccuracyMeasured',
    'commercialDemandMeasured','contents','limitations'];
  const zoneFields = ['kind','build','detector','expectedCondition','evidenceType','status',
    'complete','elapsedMs','plannedMs','coverage','analysedFrames','detectedFrames',
    'undetectedFrames','ambiguousFrames','correctZoneFrames','wrongZoneFrames',
    'expectedDwellEvents','unexpectedDwellEvents','independentlyVerified',
    'userDemandMeasured','limitations'];
  const deviceCoverage = ['requiredWindows','positiveAnalysedWindows','largestGapMs',
    'rejectedWindows','sufficient'];
  const zoneCoverage = ['sampledSeconds','secondsWithThreeFreshFrames','requiredSeconds',
    'maxGapMs','rejectedSamples','adequate'];
  const distFields = ['samples','min','median','p95','max'];
  let settings = null, performanceTrials = [], zoneTrials = [];

  const isPlain = v => v !== null && typeof v === 'object' && !Array.isArray(v) &&
    (Object.getPrototypeOf(v) === Object.prototype || Object.getPrototypeOf(v) === null);
  function keysExactly(value, fields) {
    if (!isPlain(value)) throw Error('Unreviewed evidence fields');
    const keys = Object.keys(value);
    if (keys.length !== fields.length || keys.some(k => !fields.includes(k))) {
      throw Error('Unreviewed evidence fields');
    }
  }
  function numeric(value, max = 1000000) {
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > max) {
      throw Error('Invalid evidence measurement');
    }
  }
  function integer(value, max = 1000000) {
    numeric(value, max);
    if (!Number.isInteger(value)) throw Error('Invalid evidence count');
  }
  function distribution(d, max) {
    keysExactly(d, distFields);
    integer(d.samples, 4096);
    const values = [d.min,d.median,d.p95,d.max];
    if (!d.samples) {
      if (values.some(v => v !== null)) throw Error('Empty distribution is contradictory');
    } else {
      values.forEach(v => numeric(v,max));
      if (values.some((v,i) => i > 0 && v < values[i-1])) throw Error('Contradictory distribution');
    }
  }
  function validateReport(kind, r) {
    const isDevice = kind === 'performance';
    if (!isDevice && kind !== 'zone') throw Error('Unknown evidence type');
    keysExactly(r, isDevice ? deviceFields : zoneFields);
    if (r.build !== BUILD || r.detector !== settings.detector ||
        !statuses.includes(r.status) || typeof r.complete !== 'boolean' ||
        r.complete !== (r.status === 'timed')) throw Error('Unreviewed evidence version or status');
    if (isDevice) {
      if (r.kind !== 'ANIMATE_LOCAL_DEVICE_PERFORMANCE_SAMPLE' ||
          r.evidenceType !== 'UNVERIFIED_LOCAL_PERFORMANCE_PROXY' ||
          r.recognitionAccuracyMeasured !== false || r.commercialDemandMeasured !== false ||
          r.contents !== 'Numeric performance only. No video, coordinates, IDs, user agent or network upload.' ||
          r.limitations !== 'Duration alone cannot pass: requires 80% observed and positive analysed windows, inference calls and no sampling gaps over 2.5 seconds. This does not establish sensor FPS, detection accuracy, battery, thermals, real-device provenance or commercial demand.') {
        throw Error('Unreviewed evidence provenance or disclaimer');
      }
      keysExactly(r.coverage, deviceCoverage);
      for (const k of ['plannedMs','observedMs','sampleWindows','inferredFrames',
        'unmeasuredLatencySamples','interruptions']) integer(r[k]);
      for (const k of ['requiredWindows','positiveAnalysedWindows','rejectedWindows']) integer(r.coverage[k]);
      numeric(r.coverage.largestGapMs);
      if (typeof r.coverage.sufficient !== 'boolean' || r.plannedMs !== 60000 ||
          r.coverage.requiredWindows !== 48 ||
          r.coverage.positiveAnalysedWindows > r.sampleWindows) {
        throw Error('Invalid camera evidence coverage');
      }
      distribution(r.analysedFps, 240);
      distribution(r.animationLoopFps, 240);
      distribution(r.inferenceMs, 120000);
      if (r.sampleWindows !== r.analysedFps.samples ||
          r.sampleWindows !== r.animationLoopFps.samples ||
          r.inferenceMs.samples + r.unmeasuredLatencySamples !== r.inferredFrames) {
        throw Error('Contradictory sample denominators');
      }
      if (r.complete && (!r.coverage.sufficient || r.observedMs !== 60000 ||
          r.sampleWindows < 48 || r.coverage.positiveAnalysedWindows < 48 ||
          r.inferredFrames < 48 || r.interruptions !== 0 ||
          r.coverage.rejectedWindows !== 0 || r.coverage.largestGapMs > 2500)) {
        throw Error('Unsubstantiated complete camera sample');
      }
    } else {
      if (r.kind !== 'ANIMATE_SELF_LABELLED_ZONE_CONTROL' ||
          r.evidenceType !== 'OPERATOR_LABELLED_PROXY_NOT_VERIFIED_GROUND_TRUTH' ||
          r.independentlyVerified !== false || r.userDemandMeasured !== false ||
          r.limitations !== 'Requires three analysed frames in each of 80% of seconds. One manually labelled static condition. Dwell events are proxy activations, not observed task completions. An absent-labelled false alarm is an operator-reported proxy, not independently verified accuracy.' ||
          !['absent','left','middle','right'].includes(r.expectedCondition)) {
        throw Error('Unreviewed zone evidence provenance');
      }
      keysExactly(r.coverage,zoneCoverage);
      for (const k of ['plannedMs','elapsedMs','analysedFrames','detectedFrames',
        'undetectedFrames','ambiguousFrames','correctZoneFrames','wrongZoneFrames',
        'expectedDwellEvents','unexpectedDwellEvents']) integer(r[k],100000);
      for (const k of ['sampledSeconds','secondsWithThreeFreshFrames','requiredSeconds','rejectedSamples']) {
        integer(r.coverage[k],100000);
      }
      numeric(r.coverage.maxGapMs,10000);
      if (typeof r.coverage.adequate !== 'boolean' || r.plannedMs !== 10000 ||
          r.coverage.requiredSeconds !== 8 ||
          r.analysedFrames !== r.detectedFrames + r.undetectedFrames ||
          r.ambiguousFrames > r.undetectedFrames ||
          r.expectedDwellEvents + r.unexpectedDwellEvents > r.detectedFrames ||
          r.coverage.secondsWithThreeFreshFrames > r.coverage.sampledSeconds ||
          r.analysedFrames < r.coverage.secondsWithThreeFreshFrames * 3 ||
          (r.expectedCondition === 'absent' &&
            (r.correctZoneFrames || r.wrongZoneFrames || r.expectedDwellEvents)) ||
          (r.expectedCondition !== 'absent' &&
            r.correctZoneFrames + r.wrongZoneFrames !== r.detectedFrames)) {
        throw Error('Invalid zone evidence coverage or frame totals');
      }
      if (r.complete && (!r.coverage.adequate || r.elapsedMs !== 10000 ||
          r.coverage.secondsWithThreeFreshFrames < 8 ||
          r.coverage.rejectedSamples !== 0 || r.coverage.maxGapMs > 2500)) {
        throw Error('Unsubstantiated complete zone control');
      }
    }
    // Only the exact, enumerated primitive fields survive. Invalid extra
    // fields are rejected outright, never silently copied or transmitted.
    return JSON.parse(JSON.stringify(r));
  }
  function begin(sourceCommit, detector, physicalIphoneConfirmed, registeredBeforeTesting) {
    if (settings) throw Error('Reset the existing packet before starting another');
    if (typeof sourceCommit !== 'string' || !/^[0-9a-f]{40}$/.test(sourceCommit) ||
        !methods.includes(detector) || physicalIphoneConfirmed !== true ||
        registeredBeforeTesting !== true) {
      throw Error('A 40-character commit claim, model-free method and both operator declarations are required');
    }
    settings = {schema:'ANIMATE_IPHONE_OPERATOR_PACKET_V1',sourceCommit,
      deviceClaim:'self-reported-physical-iphone',registeredBeforeTesting:true,detector};
    return summary();
  }
  function active() { return !!settings; }
  function method() { return settings?.detector ?? null; }
  function add(kind, light, raw) {
    if (!settings) throw Error('Begin an operator packet first');
    if (!lighting.includes(light)) throw Error('Select an approved lighting condition');
    const target = kind === 'performance' ? performanceTrials :
      kind === 'zone' ? zoneTrials : null;
    if (!target) throw Error('Unknown trial type');
    if (target.length >= 64) throw Error('Trial limit reached; export and reset');
    const report = validateReport(kind, raw);
    target.push({lighting:light,report});
    if (JSON.stringify(packet()).length > 256 * 1024) {
      target.pop();
      throw Error('Packet exceeds maximum allowed size');
    }
    return summary();
  }
  function packet() {
    if (!settings) throw Error('Operator packet not started');
    return JSON.parse(JSON.stringify({...settings, performanceTrials, zoneTrials}));
  }
  function summary() {
    return {configured:active(), detector:method(), performanceTrials:performanceTrials.length,
      zoneTrials:zoneTrials.length,
      incompletePerformance:performanceTrials.filter(x=>!x.report.complete).length,
      incompleteZone:zoneTrials.filter(x=>!x.report.complete).length,
      independentDeviceVerification:false, independentAccuracyVerification:false,
      purchaseDemandVerified:false, note:'Operator self-reported only; no automatic upload or storage.'};
  }
  function reset() {
    settings = null; performanceTrials = []; zoneTrials = [];
    return summary();
  }
  return {begin,active,method,add,packet,summary,reset};
}

const core = { BUILD, SCHEMA_VERSION, MAX_EVENTS, clamp, rgb2hsv, hueDist, sampleReference,
  skinLike, locate, createZoneTracker, localDay, dayDiff, modes, roles, sanitizeRecord, sanitizeLocalRecord, ledgerKey,
  recordMetrics, summarize, PROBE_FRAMES, probeColours, probeLights, probeBackgrounds,
  probeExpected, createRecognitionProbe, calibrationCandidate, deleteLocalResearchData, createDeviceBench, createZoneControlProbe, createOperatorPacketRecorder };
if (typeof module !== 'undefined' && module.exports) module.exports = core;
else root.AnimateCore = core;
})(typeof globalThis === 'undefined' ? this : globalThis);
