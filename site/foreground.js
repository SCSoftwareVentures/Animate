/* ANIMATE v0.5.0 — local foreground-difference experiment.
   NOT object recognition, ML, face/hand recognition, or a reliable scene classifier.
   Operates only on camera imageData already in the browser; never transmits images. */
(function (root) {
'use strict';
const VERSION = '0.5.0';
function createForegroundDetector(options = {}) {
  const cfg = {
    downsample: 2, captureFrames: 12, changeThreshold: 28,
    minCells: 16, maxFraction: .23, minDensity: .22,
    ...options
  };
  if (!Number.isInteger(cfg.captureFrames) || cfg.captureFrames < 3 || cfg.captureFrames > 60 ||
      !Number.isFinite(cfg.changeThreshold) || cfg.changeThreshold < 8 || cfg.changeThreshold > 120)
    throw Error('Invalid foreground configuration');
  let width = 0, height = 0, gw = 0, gh = 0, sum = null, background = null;
  let captured = 0, measured = 0, timeTotal = 0, lastTimestamp = -Infinity;
  const normaliseFrame = (data, w, h) => {
    if (!Number.isInteger(w) || !Number.isInteger(h) || w < 16 || h < 16 ||
        w % cfg.downsample || h % cfg.downsample ||
        !data || data.length !== w * h * 4) throw Error('Invalid image');
    if (width && (width !== w || height !== h)) throw Error('Camera dimensions changed; recapture background');
    if (!width) { width = w; height = h; gw = w / cfg.downsample; gh = h / cfg.downsample; }
    const out = new Float32Array(gw * gh * 3);
    for (let y = 0; y < gh; y++) for (let x = 0; x < gw; x++) {
      let r = 0, g = 0, b = 0;
      for (let dy = 0; dy < cfg.downsample; dy++) for (let dx = 0; dx < cfg.downsample; dx++) {
        const j = ((y * cfg.downsample + dy) * w + x * cfg.downsample + dx) * 4;
        r += data[j]; g += data[j + 1]; b += data[j + 2];
      }
      const scale = 1 / (cfg.downsample * cfg.downsample);
      const k = (y * gw + x) * 3;
      out[k] = r * scale; out[k + 1] = g * scale; out[k + 2] = b * scale;
    }
    return out;
  };
  function reset() {
    width = height = gw = gh = 0; sum = background = null;
    captured = measured = timeTotal = 0; lastTimestamp = -Infinity;
  }
  function capture(data, w, h) {
    if (background) throw Error('Background is already ready');
    const sampled = normaliseFrame(data, w, h);
    if (!sum) sum = new Float64Array(sampled.length);
    if (captured > 0) {
      // A large whole-frame change means the phone/object moved while establishing the reference.
      let deviation = 0;
      for (let k = 0; k < sampled.length; k += 13) deviation += Math.abs(sampled[k] - sum[k] / captured);
      if (deviation / Math.ceil(sampled.length / 13) > 14) {
        reset();
        return { ready: false, progress: 0, unstable: true };
      }
    }
    for (let i = 0; i < sampled.length; i++) sum[i] += sampled[i];
    captured++;
    if (captured >= cfg.captureFrames) {
      background = new Float32Array(sum.length);
      for (let i = 0; i < sum.length; i++) background[i] = sum[i] / captured;
      sum = null;
    }
    return { ready: !!background, progress: captured, target: cfg.captureFrames };
  }
  function detect(data, w, h, timestamp) {
    if (!background) throw Error('Capture an empty background before detection');
    if (!Number.isFinite(timestamp) || timestamp <= lastTimestamp) return null;
    lastTimestamp = timestamp;
    const begin = typeof performance !== 'undefined' ? performance.now() : Date.now();
    const pixels = normaliseFrame(data, w, h), count = gw * gh;
    // Robust median luminance shift compensates small camera auto-exposure fluctuations.
    const shifts = [];
    for (let i = 0; i < count; i += 17) {
      const k = i * 3;
      shifts.push((pixels[k] + pixels[k + 1] + pixels[k + 2] -
        background[k] - background[k + 1] - background[k + 2]) / 3);
    }
    shifts.sort((a, b) => a - b);
    const exposure = shifts[(shifts.length / 2) | 0];
    if (Math.abs(exposure) > 38) return null; // Scene illumination changed substantially.
    const raw = new Uint8Array(count);
    let changed = 0;
    for (let i = 0; i < count; i++) {
      const k = i * 3;
      const dr = Math.abs(pixels[k] - background[k] - exposure);
      const dg = Math.abs(pixels[k + 1] - background[k + 1] - exposure);
      const db = Math.abs(pixels[k + 2] - background[k + 2] - exposure);
      const d = (dr + dg + db) / 3;
      if (d >= cfg.changeThreshold) { raw[i] = 1; changed++; }
    }
    // Reject widespread change before component filtering (phone shake, moving background).
    if (changed > .30 * count) return null;
    const mask = new Uint8Array(count);
    for (let y = 1; y < gh - 1; y++) for (let x = 1; x < gw - 1; x++) {
      const i = y * gw + x;
      if (raw[i] && (raw[i - 1] + raw[i + 1] + raw[i - gw] + raw[i + gw]) >= 2) mask[i] = 1;
    }
    const seen = new Uint8Array(count), stack = [];
    let biggest = null, runnerUp = 0;
    for (let i = 0; i < count; i++) {
      if (!mask[i] || seen[i]) continue;
      let n = 0, sx = 0, sy = 0, xmin = gw, xmax = 0, ymin = gh, ymax = 0;
      stack.push(i); seen[i] = 1;
      while (stack.length) {
        const j = stack.pop(), x = j % gw, y = (j / gw) | 0;
        n++; sx += x; sy += y;
        xmin = Math.min(xmin, x); xmax = Math.max(xmax, x);
        ymin = Math.min(ymin, y); ymax = Math.max(ymax, y);
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
          if (!dx && !dy) continue;
          const xx = x + dx, yy = y + dy;
          if (xx < 0 || xx >= gw || yy < 0 || yy >= gh) continue;
          const z = yy * gw + xx;
          if (mask[z] && !seen[z]) { stack.push(z); seen[z] = 1; }
        }
      }
      if (n < cfg.minCells || n / count > cfg.maxFraction ||
          n / ((xmax - xmin + 1) * (ymax - ymin + 1)) < cfg.minDensity) continue;
      const candidate = { cells: n, x: (sx / n + .5) / gw, y: (sy / n + .5) / gh,
        fraction: n / count };
      if (!biggest || candidate.cells > biggest.cells) {
        if (biggest) runnerUp = Math.max(runnerUp, biggest.cells);
        biggest = candidate;
      } else runnerUp = Math.max(runnerUp, candidate.cells);
    }
    measured++;
    timeTotal += (typeof performance !== 'undefined' ? performance.now() : Date.now()) - begin;
    if (!biggest) return null;
    return { ...biggest, ambiguous: runnerUp >= .60 * biggest.cells };
  }
  return {
    reset, capture, detect,
    get ready() { return !!background; },
    get progress() { return captured; },
    get targetFrames() { return cfg.captureFrames; },
    metrics() { return { version: VERSION, kind: 'foreground-difference', ready: !!background,
      framesCaptured: captured, framesDetected: measured,
      avgMs: measured ? +(timeTotal / measured).toFixed(3) : null,
      bytesApprox: background?.byteLength || 0 }; }
  };
}
const api = { VERSION, createForegroundDetector };
if (typeof module !== 'undefined' && module.exports) module.exports = api;
else root.AnimateForeground = api;
})(typeof globalThis === 'undefined' ? this : globalThis);
