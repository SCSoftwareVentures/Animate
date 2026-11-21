/* ANIMATE v0.7 — MediaPipe hand landmarks adapter. Hand control only; not object recognition.
 * Runtime + weights MUST be bundled under same-origin vendor/ after licence review.
 * No remote imports, CDN fallback, recording, or video uploads.
 */
(function (root) {
'use strict';
const MODEL_ID = 'mediapipe-hand-landmarker-float16-v1';
const PKG_VERSION = '1.2.3';

function pointFromResult(result) {
  const hands = result?.landmarks;
  if (!Array.isArray(hands) || hands.length === 0) return null;
  if (hands.length > 1) return { ambiguous: true };
  if (!Array.isArray(hands[0]) || hands[0].length < 21) return null;
  const tip = hands[0][8];
  if (!tip || !Number.isFinite(tip.x) || !Number.isFinite(tip.y) ||
      tip.x < 0 || tip.x > 1 || tip.y < 0 || tip.y > 1) return null;
  return { x: tip.x, y: tip.y, source: 'index-fingertip' };
}

async function loadSameOrigin() {
  const base = new URL('./vendor/mediapipe/', document.baseURI);
  // A local dynamic import is subject to the document CSP's script-src 'self'.
  const vision = await import(new URL('vision_bundle.mjs', base).href);
  const wasm = await vision.FilesetResolver.forVisionTasks(new URL('wasm', base).href);
  return vision.HandLandmarker.createFromOptions(wasm, {
    baseOptions: { modelAssetPath: new URL('models/hand_landmarker.task', base).href, delegate: 'CPU' },
    runningMode: 'VIDEO', numHands: 2, minHandDetectionConfidence: 0.7,
    minHandPresenceConfidence: 0.7, minTrackingConfidence: 0.7
  });
}
function createHandDetector({loader = loadSameOrigin, minIntervalMs = 95, loadTimeoutMs = 12000} = {}) {
  if (!Number.isFinite(minIntervalMs) || minIntervalMs < 0) throw Error('Invalid inference interval');
  if (!Number.isFinite(loadTimeoutMs) || loadTimeoutMs <= 0 || loadTimeoutMs > 120000) {
    throw Error('Invalid ML loading deadline');
  }
  let engine = null, generation = 0, ready = false, lastAt = -1;
  let calls = 0, totalMs = 0, worstMs = 0, failures = 0;
  function stop() {
    generation++;
    ready = false;
    lastAt = -1;
    const previous = engine; engine = null;
    try { previous?.close?.(); } catch (_) { /* already closed */ }
  }
  async function start() {
    // An overlapping or repeated start must never leak the previous WASM engine.
    stop();
    const mine = generation;
    let timer;
    // If the deadline wins, the still-pending loader must close any late engine.
    const loading = Promise.resolve().then(() => {
      // Stop may happen synchronously before this microtask: never start an obsolete ML load.
      if (mine !== generation) return null;
      return loader();
    }).then(loaded => {
      if (mine !== generation) { try { loaded?.close?.(); } catch (_) {} return null; }
      return loaded;
    });
    const deadline = new Promise((_, reject) => {
      timer = setTimeout(() => reject(Error('Hand model load timed out')), loadTimeoutMs);
    });
    try {
      const loaded = await Promise.race([loading, deadline]);
      if (mine !== generation) return false;
      if (!loaded || typeof loaded.detectForVideo !== 'function') {
        try { loaded?.close?.(); } catch (_) {}
        throw Error('Invalid local hand model runtime');
      }
      engine = loaded; ready = true; lastAt = -1;
      return true;
    } catch (error) {
      // No model load failure may leave a live engine, scoreable results, or a stale reference.
      if (mine === generation) stop();
      throw error;
    } finally { clearTimeout(timer); }
  }
  function detect(frame, timestamp) {
    if (!ready || !engine) return null;
    if (!Number.isFinite(timestamp) || timestamp <= lastAt) {
      stop(); throw Error('Invalid ML frame timestamp');
    }
    if (lastAt >= 0 && timestamp - lastAt < minIntervalMs) return { skipped: true };
    lastAt = timestamp;
    const began = performance.now();
    try {
      const result = engine.detectForVideo(frame, timestamp);
      const elapsed = performance.now() - began;
      calls++; totalMs += elapsed; worstMs = Math.max(worstMs, elapsed);
      return pointFromResult(result);
    } catch (e) { failures++; stop(); throw e; }
  }
  return { start, stop, detect,
    get ready() { return ready; },
    metrics() { return { model: MODEL_ID, version: PKG_VERSION, ready,
      inferenceCount: calls, avgMs: calls ? totalMs / calls : null,
      maxMs: calls ? worstMs : null, errors: failures }; }
  };
}
const api = { MODEL_ID, PKG_VERSION, pointFromResult, createHandDetector };
if (typeof module === 'object' && module.exports) module.exports = api;
root.AnimateHandML = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
