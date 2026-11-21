'use strict';
/* ANIMATE v0.7.0: optional locally hosted MediaPipe hand tracking, not generic object recognition. */
const C = AnimateCore;
const F = AnimateForeground;
const H = AnimateHandML;
const $ = id => document.getElementById(id);
const STORE = 'animate-validation-v07';
const DEBUG = new URLSearchParams(location.search).get('debug') === '1';
const BENCHMARK = new URLSearchParams(location.search).get('benchmark') === '1';
const view = $('view');
const ctx = view.getContext('2d');
const analysis = document.createElement('canvas');
analysis.width = 160;
analysis.height = 120;
const ac = analysis.getContext('2d', { willReadFrequently: true });
const descriptions = {
  play: 'Guide one coloured object into the highlighted zones. This is a dwell-control demonstration, not a fast reaction game.',
  create: 'Change three display settings using the same zone-control mechanics. This is not a content editor.',
  learn: 'Use three zones to illustrate thirds (1/3, 2/3, 3/3). This is an experimental teaching aid.'
};
const targetsFor = { play: [1, 0, 2], create: [2, 0, 1], learn: [0, 1, 2] };
const names = ['left', 'middle', 'right'];
function secureId() {
  const crypt = globalThis.crypto;
  if (typeof crypt?.randomUUID === 'function') return crypt.randomUUID();
  if (typeof crypt?.getRandomValues !== 'function') throw Error('Secure participant ID unavailable');
  const bytes = crypt.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = [...bytes].map(v => v.toString(16).padStart(2, '0')).join('');
  return [hex.slice(0, 8), hex.slice(8, 12), hex.slice(12, 16),
    hex.slice(16, 20), hex.slice(20)].join('-');
}
const deviceCategory = () => /iPhone/i.test(navigator.userAgent) ? 'iPhone' :
  /Android/i.test(navigator.userAgent) ? 'Android' : 'Other';
const inApp = () => /FBAN|FBAV|Instagram|Line\/|MicroMessenger|Snapchat|TikTok|WhatsApp|GSA\//i.test(navigator.userAgent);

let record = null;
let mode = 'learn';
let input = null;
let stream = null;
let reference = null;
let detectorKind = 'colour';
const hand = H.createHandDetector({minIntervalMs:55});
let backgroundCapture = false;
const foreground = F.createForegroundDetector();
let rafId = 0;
let frameWatcherGeneration = 0;
let frameNumber = 0;
let processedFrame = -1;
let lastFrameAt = 0;
let lastMediaTime = -1;
let interrupted = false;
let stale = false;
let startInProgress = false;
let calibrating = false;
let mirror = false;
let lastPosition = null;
let run = null;
let wakeLock = null;
let fpsCounter = 0;
let analysedFpsCounter = 0;
let fpsAt = performance.now();
let detectionMs = 0;
let detectionCount = 0;
let lastError = '';
let importedRecords = [];
let importedLedger = [];
let unreadableFiles = 0;
const tracker = C.createZoneTracker();
const probe = C.createRecognitionProbe();
const deviceBench = C.createDeviceBench();
const zoneControl = C.createZoneControlProbe();
let probeSamples = [];

function setStatus(message) {
  if ($('status').textContent !== message) $('status').textContent = message;
}
function store() {
  if (!record) return;
  try {
    const safe = C.sanitizeLocalRecord(record);
    if (!safe) {
      $('recordStatus').textContent = 'Local record is invalid. Do not export this session.';
      return;
    }
    record = safe;
    localStorage.setItem(STORE, JSON.stringify(safe));
  } catch (_) {
    $('recordStatus').textContent = 'Storage unavailable. Export this session before closing the page.';
  }
}
function log(type, details = {}) {
  if (!record) return;
  // Bound client-side history so local storage and subsequent aggregate imports remain manageable.
  if (record.events.length >= C.MAX_EVENTS) {
    $('recordStatus').textContent = 'Record event limit reached. Export and delete before running further tests.';
    return;
  }
  record.events.push({ type, time: new Date().toISOString(), ...details });
  store();
}
function updateParticipant() { $('participantId').textContent = record ? `Record ID: ${record.id} · Build ${C.BUILD}` : ''; }
function showExperiment() {
  $('intro').hidden = true;
  $('lab').hidden = false;
  $('results').hidden = false;
  updateParticipant();
  chooseMode(mode);
}
function restoreRecord() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORE) || 'null');
    if (!saved) return;
    const safe = C.sanitizeLocalRecord(saved);
    if (!safe) {
      $('introerr').textContent = 'The saved record failed validation. Clear this website\'s data in Safari settings to start again.';
      return;
    }
    record = safe;
    const today = C.localDay();
    if (record.lastDay !== today) {
      const days = C.dayDiff(record.createdDay, today);
      record.lastDay = today;
      if (days >= 1 && days <= 365) log('return', { days, day: today });
      else store();
    } else store();
    showExperiment();
  } catch (_) {
    $('introerr').textContent = 'Unable to restore the saved record. Clear ANIMATE website data to start again.';
  }
}

function resetChallenge() {
  run = null;
  tracker.reset();
  $('score').textContent = '0 / 3';
  $('progress').style.width = '0%';
  $('progressBar').setAttribute('aria-valuenow', '0');
  $('clock').textContent = '—';
  $('effect').textContent = mode === 'learn' ? 'Fraction: 0/3' :
    mode === 'create' ? 'Scene control: waiting' : 'Game: 0 targets';
  $('effect').style.background = '#152b40';
  updateTarget();
}
function chooseMode(next) {
  if (zoneControl.active()) {
    zoneControl.finish(performance.now(), 'interrupted');
    refreshZoneControl();
  }
  mode = next;
  resetChallenge();
  $('feedbackPanel').hidden = true;
  $('feedbackStatus').textContent = '';
  $('problem').value = '';
  $('saveProblem').disabled = false;
  for (const button of document.querySelectorAll('[data-mode]')) {
    const selected = button.dataset.mode === mode;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-pressed', String(selected));
  }
  $('description').textContent = descriptions[mode];
  if (input === 'touch' || (input === 'camera' && (reference || hand.ready || foreground.ready))) setStatus('Ready. Start the challenge.');
  draw(lastPosition);
}
function updateTarget() {
  const index = run && !run.done && run.index < run.targets.length ? run.targets[run.index] : null;
  $('targetText').textContent = index === null ? 'Target: none' : `Target: ${names[index]} zone (${run.index + 1} of 3)`;
}
function resizeCanvas() {
  const rect = view.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const dpr = Math.min(3, window.devicePixelRatio || 1);
  const w = Math.max(1, Math.round(rect.width * dpr));
  const h = Math.max(1, Math.round(rect.height * dpr));
  if (view.width !== w || view.height !== h) { view.width = w; view.height = h; }
  draw(lastPosition);
}
function drawCover(video, targetContext, targetW, targetH) {
  const sw = video.videoWidth, sh = video.videoHeight;
  if (!sw || !sh) return;
  const aspect = targetW / targetH;
  let srcW = sw, srcH = sh;
  if (sw / sh > aspect) srcW = sh * aspect;
  else srcH = sw / aspect;
  targetContext.save();
  if (mirror) { targetContext.translate(targetW, 0); targetContext.scale(-1, 1); }
  targetContext.drawImage(video, (sw - srcW) / 2, (sh - srcH) / 2, srcW, srcH, 0, 0, targetW, targetH);
  targetContext.restore();
}
function draw(p) {
  const rect = view.getBoundingClientRect();
  if (!rect.width || !rect.height) return;
  const w = rect.width, h = rect.height;
  const dpr = view.width / w;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  const video = $('video');
  if (input === 'camera' && video.readyState >= 2) drawCover(video, ctx, w, h);
  else { ctx.fillStyle = '#0c1523'; ctx.fillRect(0, 0, w, h); }
  if (calibrating && detectorKind === 'colour') {
    ctx.strokeStyle = '#9ae9d4'; ctx.lineWidth = 2;
    ctx.strokeRect(w / 2 - 18, h / 2 - 18, 36, 36);
    return;
  }
  if (!input) return;
  const zoneNames = mode === 'learn' ? ['1/3', '2/3', '3/3'] :
    mode === 'create' ? ['LOW', 'MID', 'HIGH'] : ['A', 'B', 'C'];
  for (let i = 0; i < 3; i++) {
    const target = run && !run.done && run.targets[run.index] === i;
    ctx.fillStyle = target ? 'rgba(154,233,212,.3)' : 'rgba(25,35,50,.3)';
    ctx.fillRect(i * w / 3, 0, w / 3, h);
    ctx.strokeStyle = target ? '#9ae9d4' : '#61768e'; ctx.lineWidth = target ? 3 : 1;
    ctx.strokeRect(i * w / 3 + 2, 2, w / 3 - 4, h - 4);
    ctx.fillStyle = '#fff'; ctx.font = 'bold 16px sans-serif'; ctx.textAlign = 'center';
    ctx.fillText(zoneNames[i], (i + .5) * w / 3, 24);
    if (target) { ctx.font = 'bold 12px sans-serif'; ctx.fillText('TARGET', (i + .5) * w / 3, 44); }
  }
  if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
    ctx.fillStyle = '#9ae9d4'; ctx.beginPath(); ctx.arc(p.x * w, p.y * h, 10, 0, Math.PI * 2); ctx.fill();
    ctx.strokeStyle = '#051018'; ctx.lineWidth = 2; ctx.stroke();
  }
}
function grabFrame() {
  ac.clearRect(0, 0, 160, 120);
  drawCover($('video'), ac, 160, 120);
}
async function preventSleep() {
  // A pending permission/grant may resolve after Stop, pagehide or a new camera session.
  // Releasing that late sentinel prevents a hidden wake lock and unnecessary battery drain.
  const generation = frameWatcherGeneration;
  try {
    if (!navigator.wakeLock?.request) return;
    const granted = await navigator.wakeLock.request('screen');
    if (!granted || typeof granted.release !== 'function') return;
    if (generation !== frameWatcherGeneration || !stream || document.hidden) {
      try { await granted.release(); } catch (_) { /* Best-effort cleanup. */ }
      return;
    }
    if (wakeLock && wakeLock !== granted) {
      try { Promise.resolve(wakeLock.release()).catch(() => {}); } catch (_) {}
    }
    wakeLock = granted;
  } catch (_) { /* Optional only. Tested iPhone behaviour unknown. */ }
}
function stopCamera() {
  if (zoneControl.active()) {
    zoneControl.finish(performance.now(), 'camera_stopped');
    refreshZoneControl();
  }
  if (deviceBench.active()) {
    deviceBench.finish(performance.now(), 'camera_stopped');
    refreshDeviceBench();
  }
  cancelProbe('Camera stopped: unfinished sample discarded.');
  frameWatcherGeneration++;
  cancelAnimationFrame(rafId); rafId = 0;
  if (stream) {
    for (const track of stream.getTracks()) {
      track.onended = track.onmute = track.onunmute = null;
      track.stop();
    }
  }
  stream = null;
  if (wakeLock) { wakeLock.release().catch(() => {}); wakeLock = null; }
  $('video').srcObject = null;
  input = null; reference = null; run = null;
  foreground.reset(); hand.stop(); backgroundCapture = false;
  $('captureBackground').hidden = detectorKind !== 'foreground';
  $('captureBackground').disabled = true;
  calibrating = false; interrupted = false; stale = false; mirror = false;
  lastPosition = null; frameNumber = 0; processedFrame = -1;
  lastFrameAt = 0; lastMediaTime = -1;
  tracker.reset();
  $('inputLabel').textContent = 'Not started';
  $('camera').disabled = false; $('start').disabled = true;
  $('calibrate').disabled = true; $('stop').disabled = true;
  for (const id of ['tapLeft', 'tapMiddle', 'tapRight']) $(id).hidden = true;
  updateTarget();
}
function cameraFailure(message, error) {
  if (zoneControl.active()) {
    zoneControl.finish(performance.now(), 'interrupted');
    refreshZoneControl();
  }
  deviceBench.noteInterruption(performance.now());
  refreshDeviceBench();
  stopCamera();
  lastError = (error || '') + ' ' + message;
  log('camera_error', { reason: message, name: error || null });
  setStatus(message);
  draw(null);
}
function beginFrameWatch(video) {
  const generation = frameWatcherGeneration;
  if (!video.requestVideoFrameCallback) return;
  function callback() {
    if (!stream || frameWatcherGeneration !== generation) return;
    lastFrameAt = performance.now();
    frameNumber++;
    video.requestVideoFrameCallback(callback);
  }
  video.requestVideoFrameCallback(callback);
}
function markInterrupted(message) {
  if (zoneControl.active()) {
    zoneControl.finish(performance.now(), 'interrupted');
    refreshZoneControl();
  }
  deviceBench.noteInterruption(performance.now());
  refreshDeviceBench();
  cancelProbe('Camera interrupted: unfinished sample discarded.');
  interrupted = true;
  stale = true;
  lastPosition = null;
  // Any interruption invalidates ALL camera calibrations; require deliberate re-arm.
  // Otherwise a resumed frame could count against stale reference/background data.
  reference = null;
  calibrating = detectorKind === 'colour';
  $('start').disabled = true;
  foreground.reset(); backgroundCapture = false;
  if (detectorKind === 'hand') hand.stop();
  if (detectorKind === 'foreground') $('captureBackground').disabled = false;
  if (run && !run.done) { log('challenge_interrupted', { runId: run.runId }); resetChallenge(); }
  tracker.reset();
  setStatus(message);
}
function onCameraLoop() {
  if (!stream) return;
  const video = $('video');
  const now = performance.now();
  fpsCounter++;
  if (now - fpsAt >= 1000) {
    updateDiagnostics(analysedFpsCounter * 1000 / (now - fpsAt),
      fpsCounter * 1000 / (now - fpsAt));
    fpsCounter = 0; analysedFpsCounter = 0; fpsAt = now;
  }
  if (!video.requestVideoFrameCallback && video.readyState >= 2 &&
      video.currentTime !== lastMediaTime) {
    lastMediaTime = video.currentTime;
    lastFrameAt = now;
    frameNumber++;
  }
  const track = stream.getVideoTracks()[0];
  if (!track || track.readyState !== 'live' || track.muted) {
    if (!interrupted) markInterrupted('Camera interrupted. Restart camera before continuing.');
  } else if (!lastFrameAt || now - lastFrameAt > 1500) {
    if (!stale) markInterrupted('Camera frames are stale. Stop and restart the camera.');
  } else if (interrupted || stale) {
    interrupted = false; stale = false; processedFrame = frameNumber;
    tracker.reset(); lastPosition = null;
    setStatus(detectorKind === 'hand' ? 'ML model invalidated. Stop and restart camera.' :
      detectorKind === 'colour' ? 'Camera resumed. Tap your object to recalibrate before starting.' :
      'Camera resumed. Recapture an empty background before starting.');
    if (run && !run.done) { resetChallenge(); }
  } else if (backgroundCapture && video.readyState >= 2 && frameNumber !== processedFrame) {
    processedFrame = frameNumber; grabFrame();
    const state = foreground.capture(ac.getImageData(0, 0, 160, 120).data, 160, 120);
    if (state.unstable) { setStatus('Background moved. Keep camera fixed and recapture.'); backgroundCapture = false; $('captureBackground').disabled = false; }
    else if (state.ready) {
      backgroundCapture = false; calibrating = false; $('start').disabled = false;
      $('captureBackground').disabled = false;
      setStatus('Empty scene learned. Place one object in view and start the challenge.');
      log('background_captured', { detector: 'foreground' });
    } else setStatus(`Capturing empty scene: ${state.progress} / ${state.target} fresh frames`);
  } else if (!calibrating && (reference || (detectorKind === 'foreground' && foreground.ready) ||
      (detectorKind === 'hand' && hand.ready)) && video.readyState >= 2 && frameNumber > 0 && frameNumber !== processedFrame) {
    processedFrame = frameNumber;
    grabFrame();
    const started = performance.now();
    const frame = detectorKind !== 'hand' ? ac.getImageData(0, 0, 160, 120).data : null;
    let p;
    try {
      p = detectorKind === 'foreground' ? foreground.detect(frame, 160, 120, now) :
        detectorKind === 'hand' ? hand.detect(analysis, now) :
        C.locate(frame, 160, 120, reference);
    } catch (err) { cameraFailure('Local hand model inference failed. Restart the camera.', err?.name); return; }
    if (p?.skipped) { draw(lastPosition); rafId = requestAnimationFrame(onCameraLoop); return; }
    analysedFpsCounter++;
    if (detectorKind === 'hand' && $('start').disabled) $('start').disabled = false;
    const elapsed = performance.now() - started;
    deviceBench.noteLatency(elapsed);
    detectionMs += elapsed;
    detectionCount++;
    if (probe.active) {
      const result = probe.add(p, elapsed);
      $('benchStatus').textContent = `Fresh frames: ${result.frames} / ${result.target}`;
      if (result.frames >= C.PROBE_FRAMES) finishProbe();
    }
    const observedForControl = p;
    if (p?.ambiguous) { setStatus(detectorKind === 'hand' ? 'Multiple hands detected. Show exactly one hand.' :
      'Multiple foreground regions detected. Remove the distractor.'); p = null; }
    if (zoneControl.active()) {
      zoneControl.add(observedForControl, now);
      if (!zoneControl.active()) refreshZoneControl();
    }
    lastPosition = p;
    if (run && !run.done) observe(p, now);
    else if (!run) setStatus(detectorKind === 'hand' ? (p ? 'One hand detected. Start a challenge.' : 'No single hand detected.') :
      (p ? 'Object detected. Start a challenge.' : 'Object not detected. Adjust light or recalibrate.'));
  }
  draw(stale || interrupted ? null : lastPosition);
  rafId = requestAnimationFrame(onCameraLoop);
}
async function startCamera() {
  if (startInProgress) return;
  detectorKind = $('detector').value;
  stopCamera();
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
    cameraFailure(inApp() ? 'This browser may block the camera. Open in Safari.' :
      'Camera unavailable. Use the hosted HTTPS site in Safari, or try touch mode.');
    return;
  }
  startInProgress = true; $('camera').disabled = true;
  const front = $('front').checked;
  const generation = frameWatcherGeneration;
  try {
    const acquired = await navigator.mediaDevices.getUserMedia({
      audio: false, video: { facingMode: { ideal: front ? 'user' : 'environment' }, width: { ideal: 640 }, height: { ideal: 480 } }
    });
    if (generation !== frameWatcherGeneration) {
      acquired.getTracks().forEach(track => track.stop());
      return;
    }
    stream = acquired;
    const video = $('video'); video.srcObject = stream;
    await video.play();
    // stopCamera may run while the play() promise is pending (pagehide/visibility/user stop).
    if (generation !== frameWatcherGeneration || stream !== acquired) {
      acquired.getTracks().forEach(track => track.stop());
      if (video.srcObject === acquired) video.srcObject = null;
      return;
    }
    input = 'camera'; mirror = front; calibrating = detectorKind === 'colour';
    if (detectorKind === 'hand') {
      setStatus('Loading self-hosted hand landmark model (no remote inference)...');
      if (!await hand.start()) throw Error('Hand model loading was cancelled');
      if (generation !== frameWatcherGeneration || stream !== acquired) { hand.stop(); return; }
    }
    $('captureBackground').hidden = detectorKind !== 'foreground';
    $('captureBackground').disabled = detectorKind !== 'foreground';
    lastFrameAt = performance.now(); lastMediaTime = -1;
    for (const track of stream.getVideoTracks()) {
      track.onended = () => cameraFailure('Camera disconnected. Enable it again.');
      track.onmute = () => markInterrupted('Camera interrupted (call, Siri, or another app).');
      track.onunmute = () => {
        interrupted = false; stale = false; lastFrameAt = 0; lastPosition = null;
        reference = null; foreground.reset(); backgroundCapture = false;
        calibrating = detectorKind === 'colour'; $('start').disabled = true;
        if (detectorKind === 'hand') hand.stop();
        tracker.reset(); setStatus(detectorKind === 'colour' ?
          'Camera resumed. Tap the object to recalibrate after a fresh frame.' :
          detectorKind === 'hand' ? 'Restart camera to reload the hand model.' :
          'Camera resumed. Capture a new empty background before testing.');
      };
    }
    beginFrameWatch(video);
    preventSleep();
    $('inputLabel').textContent = 'Live camera';
    $('stop').disabled = false; $('calibrate').disabled = detectorKind === 'hand';
    setStatus(detectorKind === 'colour' ?
      'Tap the middle of your brightly coloured object in the preview to calibrate.' :
      detectorKind === 'hand' ? 'Hand model loaded. Hold one index finger in view to control zones.' :
      'Remove objects from view. Keep the camera stationary, then capture the empty background.');
    log('camera_ready', { facing: front ? 'user' : 'environment', detector: detectorKind,
      model: detectorKind === 'hand' ? H.MODEL_ID : undefined });
    fpsAt = performance.now(); fpsCounter = 0; analysedFpsCounter = 0;
    onCameraLoop();
  } catch (e) {
    if (generation !== frameWatcherGeneration) return; // An old start must not cancel a newer stream.
    cameraFailure(detectorKind === 'hand' ?
      'Hand ML could not initialise. Verified local runtime/model assets may be missing. Colour and foreground modes remain available.' :
      (inApp() ? 'Camera may be blocked here; open in Safari.' :
      'Unable to start camera (' + (e?.name || 'error') + '). Check HTTPS and camera permissions.'), e?.name);
  } finally { startInProgress = false; if (!stream) $('camera').disabled = false; }
}
function calibrateAt(x, y) {
  if (input !== 'camera' || detectorKind !== 'colour' || !calibrating || interrupted || stale ||
      !$('video').videoWidth || !frameNumber || performance.now() - lastFrameAt > 1500) {
    setStatus('Wait for a fresh camera frame before calibrating.'); return;
  }
  grabFrame();
  const px = C.clamp(Math.floor(x * 160), 3, 156);
  const py = C.clamp(Math.floor(y * 120), 3, 116);
  const ref = C.sampleReference(ac.getImageData(0, 0, 160, 120).data, 160, 120, px, py, 3);
  if (!ref) { setStatus('Choose a brighter, more saturated object.'); return; }
  const candidate = C.calibrationCandidate(ac.getImageData(0, 0, 160, 120).data,
    160, 120, ref, x, y);
  if (!candidate) {
    setStatus('Could not isolate an object at your tap. Use a single object against a different background.');
    return;
  }
  reference = ref; calibrating = false; lastPosition = null;
  tracker.reset(); $('start').disabled = false;
  log('calibrated', { skinLike: C.skinLike(ref) });
  setStatus(C.skinLike(ref) ? 'Warning: this colour overlaps skin tones. Prefer blue or green.' :
    'Calibrated. Start the challenge.');
}
function handleTap(x, y) {
  if (input === 'camera' && calibrating) calibrateAt(x, y);
  else if (input === 'touch') {
    if (run && !run.done) hit(Math.min(2, Math.floor(x * 3)));
    draw({ x, y });
  }
}
function startChallenge() {
  if (probe.active || zoneControl.active()) {
    setStatus('Finish the operator-only camera diagnostic before starting a challenge.'); return;
  }
  if (!input || (input === 'camera' && (!(detectorKind === 'foreground' ? foreground.ready : detectorKind === 'hand' ? hand.ready : reference) ||
      backgroundCapture || interrupted || stale || !frameNumber || performance.now() - lastFrameAt > 1500))) {
    setStatus('Camera is not calibrated or current. Restart it if necessary.'); return;
  }
  resetChallenge();
  run = { targets: targetsFor[mode].slice(), index: 0, started: performance.now(),
    done: false, mode, input, runId: secureId() };
  tracker.reset();
  $('clock').textContent = '0 s';
  $('feedbackPanel').hidden = true;
  updateTarget();
  log('start', { mode, input, runId: run.runId, detector: input === 'camera' ? detectorKind : undefined,
    model: input === 'camera' && detectorKind === 'hand' ? H.MODEL_ID : undefined });
  setStatus(input === 'camera' ? (detectorKind === 'hand' ? 'Move your index finger into the target and hold briefly.' : 'Move the object into the target and hold briefly.') :
    'Select the highlighted zone.');
  draw(null);
}
function observe(p, now) {
  if (!run || run.done) return;
  const result = tracker.update(p, now);
  if (result.fired !== null) hit(result.fired);
  if (run && !run.done) $('clock').textContent = Math.round((now - run.started) / 1000) + ' s';
}
function hit(zone) {
  if (!run || run.done || zone !== run.targets[run.index]) return;
  run.index++;
  const effect = $('effect');
  if (mode === 'create') {
    effect.textContent = 'Scene setting: ' + ['Ocean', 'Sunset', 'Forest'][zone];
    effect.style.background = ['#15467b', '#924324', '#236642'][zone];
  } else if (mode === 'learn') {
    effect.textContent = 'Fraction: ' + (zone + 1) + '/3 · ' + Math.round((zone + 1) / 3 * 100) + '%';
    effect.style.background = 'linear-gradient(90deg,#236642 ' + ((zone + 1) / 3 * 100) + '%,#152b40 ' + ((zone + 1) / 3 * 100) + '%)';
  } else effect.textContent = 'Game: ' + run.index + ' targets captured';
  $('score').textContent = run.index + ' / 3';
  $('progress').style.width = (run.index / 3 * 100) + '%';
  $('progressBar').setAttribute('aria-valuenow', String(run.index));
  updateTarget();
  if (run.index < 3) { setStatus('Correct. Move to the next highlighted zone.'); return; }
  run.done = true;
  const elapsed = Math.round(performance.now() - run.started);
  $('clock').textContent = (elapsed / 1000).toFixed(1) + ' s';
  setStatus('Challenge complete. Optional feedback appears below.');
  log('complete', { mode: run.mode, input: run.input, runId: run.runId, elapsed,
    detector: run.input === 'camera' ? detectorKind : undefined,
    model: run.input === 'camera' && detectorKind === 'hand' ? H.MODEL_ID : undefined });
  $('feedbackPanel').hidden = false;
  updateTarget();
}
function shareURL() {
  const url = new URL(location.href);
  url.hash = ''; url.searchParams.delete('debug'); url.searchParams.delete('benchmark');
  return url.toString();
}
function cancelProbe(message) {
  if (probe.active) probe.cancel();
  if (!BENCHMARK) return;
  $('benchStart').disabled = false;
  $('benchCancel').disabled = true;
  if (message) $('benchStatus').textContent = message;
}
function finishProbe() {
  const sample = probe.finish();
  if (!sample) return;
  $('benchStart').disabled = false; $('benchCancel').disabled = true;
  probeSamples.push(sample);
  sample.detector = detectorKind;
  log('benchmark_sample', { sample });
  $('benchStatus').textContent = sample.complete ?
    '600 frames captured. Manual label is unverified; export record to preserve summary.' :
    'Sample incomplete. It is not suitable for the acceptance gate.';
  $('benchResults').textContent = JSON.stringify(probeSamples, null, 2);
}
function startProbe() {
  if (detectorKind === 'hand') {
    $('benchStatus').textContent = 'This object-colour benchmark is not valid for hand ML. Use the separate hand-control test protocol.';
    return;
  }
  if (!BENCHMARK || input !== 'camera' ||
      !(detectorKind === 'foreground' ? foreground.ready : detectorKind === 'hand' ? hand.ready : reference) ||
      backgroundCapture || calibrating || stale || interrupted ||
      !frameNumber || performance.now() - lastFrameAt > 1500) {
    $('benchStatus').textContent = 'Enable a fresh camera feed and calibrate first.';
    return;
  }
  if (zoneControl.active()) {
    $('benchStatus').textContent = 'Finish the zone-control trial before starting a benchmark.';
    return;
  }
  if (run && !run.done) resetChallenge();
  probe.start({ colour: $('benchColour').value, light: $('benchLight').value,
    background: $('benchBackground').value, expected: $('benchExpected').value });
  $('benchStart').disabled = true; $('benchCancel').disabled = false;
  $('benchStatus').textContent = 'Fresh frames: 0 / ' + C.PROBE_FRAMES;
}
function exportRecord() {
  if (!record) return;
  const safe = C.sanitizeLocalRecord(record);
  if (!safe) {
    $('recordStatus').textContent = 'Export blocked: local record did not pass validation.';
    return;
  }
  const out = { ...safe, exportedAt: new Date().toISOString() };
  if (!C.sanitizeRecord(out)) {
    $('recordStatus').textContent = 'Export blocked: event timestamps failed validation.';
    return;
  }
  const blob = new Blob([JSON.stringify(out, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url; anchor.download = 'animate-' + C.BUILD + '-' + record.id + '.json';
  document.body.appendChild(anchor); anchor.click();
  setTimeout(() => { anchor.remove(); URL.revokeObjectURL(url); }, 60000);
  $('recordStatus').textContent = 'Export requested. Check your browser downloads; you choose whether to send the file.';
}
function parseLedger(text) {
  const lines = text.replace(/^\uFEFF/, '').trim().split(/\r?\n/);
  if (!lines.length || lines[0].replace(/\s/g, '').toLowerCase() !== 'id,sessiondate,device') throw Error('Expected header id,sessionDate,device');
  const keys = [];
  for (const line of lines.slice(1)) {
    if (!line.trim()) continue;
    const [id, day, device, ...extra] = line.split(',').map(s => s.trim());
    if (extra.length || !/^[a-zA-Z0-9-]{8,80}$/.test(id) ||
        !/^\d{4}-\d{2}-\d{2}$/.test(day) || !['iPhone', 'Android', 'Other'].includes(device)) throw Error('Invalid ledger row');
    keys.push(id + '|' + day + '|' + device);
  }
  return keys;
}
function showAggregate() {
  $('aggregateOutput').textContent = JSON.stringify({
    ...C.summarize(importedRecords, importedLedger), unreadableFiles,
    privacy: 'Ledger loaded only in memory. Never commit participant exports or ledger to a public repository.'
  }, null, 2);
}
function refreshZoneControl() {
  if (!DEBUG) return;
  const summary = zoneControl.snapshot(performance.now());
  $('zoneControlStart').disabled = zoneControl.active();
  $('zoneControlFinish').disabled = !zoneControl.active();
  $('zoneControlExpected').disabled = zoneControl.active();
  $('zoneControlStatus').textContent = summary.status === 'not_started' ?
    'No operator-labelled control measured.' :
    summary.status === 'running' ?
      'Analysing fresh frames for one self-labelled static condition. Avoid switching scenes.' :
    summary.complete ? 'Data coverage recorded. Review the manually labelled counts; accuracy remains unverified.' :
    summary.status === 'insufficient_coverage' ?
      'INSUFFICIENT COVERAGE: frames, elapsed time or continuity were inadequate. Repeat this control.' :
      'Incomplete control (' + summary.status + '). Do not count as completed evidence.';
  $('zoneControlReport').textContent = JSON.stringify(summary, null, 2);
}

function refreshDeviceBench() {
  if (!DEBUG) return;
  const summary = deviceBench.snapshot(performance.now());
  $('deviceBenchStatus').textContent = summary.status === 'not_started' ?
    'Not measured. Start a camera first, then begin a 60-second sample.' :
    summary.status === 'running' ? 'Recording numeric measurements locally. No frames or personal identifiers are saved.' :
    summary.complete ? '60-second continuous camera sample recorded. This is NOT proof of recognition accuracy or demand.' :
    summary.status === 'insufficient_coverage' ?
      'INSUFFICIENT DATA: missing or frozen analysed frames, sparse windows or a sampling gap. Repeat this measurement.' :
      'Incomplete measurement (' + summary.status + '). Do not report this as a pass.';
  $('deviceBenchStart').disabled = deviceBench.active();
  $('deviceBenchFinish').disabled = !deviceBench.active();
  $('deviceBenchReport').textContent = JSON.stringify(summary, null, 2);
}

function updateDiagnostics(fps = 0, renderFps = 0) {
  if (!DEBUG) return;
  deviceBench.noteWindow(performance.now(), fps, renderFps);
  refreshDeviceBench();
  if (zoneControl.active()) refreshZoneControl();
  const track = stream?.getVideoTracks()?.[0];
  const settings = track?.getSettings?.() || {};
  $('dbgbox').hidden = false;
  const now = performance.now();
  $('diagnosticOutput').textContent = JSON.stringify({
    build: C.BUILD, userAgent: navigator.userAgent,
    analysedFps: +fps.toFixed(1), renderFps: +renderFps.toFixed(1), locateMsAvg: detectionCount ? +(detectionMs / detectionCount).toFixed(2) : null,
    video: [$('video').videoWidth, $('video').videoHeight],
    track: { width: settings.width, height: settings.height, fps: settings.frameRate, facing: settings.facingMode, muted: track?.muted },
    frameAgeMs: lastFrameAt ? Math.round(now - lastFrameAt) : null,
    frameCount: frameNumber, paused: interrupted || stale, mirror,
    recognizer: detectorKind, foreground: foreground.metrics(), hand: hand.metrics(), backgroundCapture,
    mlDisclaimer: detectorKind === 'hand' ? 'Hand landmarks only; no household object identity.' : null,
    reference: reference?.map(v => +v.toFixed(2)), lastPosition, lastError,
    secure: window.isSecureContext, videoCrop: '4:3 centre crop (no stretching)',
    storage: (() => { try { localStorage.setItem('_animate_test', '1'); localStorage.removeItem('_animate_test'); return 'ok'; } catch (_) { return 'blocked'; } })()
  }, null, 2);
}

if (BENCHMARK) {
  $('benchmarkPanel').hidden = false;
  $('benchStart').addEventListener('click', startProbe);
  $('benchCancel').addEventListener('click', () => cancelProbe('Sample cancelled; no data recorded.'));
}
$('enter').addEventListener('click', () => {
  if (!$('role').value || !$('adult').checked || !$('consent').checked) {
    $('introerr').textContent = 'Choose an intended use, confirm you are an adult, and consent first.';
    return;
  }
  const now = new Date();
  let id;
  try { id = secureId(); }
  catch (_) {
    $('introerr').textContent = 'Secure participant ID unavailable. Open ANIMATE in Safari over a trusted HTTPS connection.';
    return;
  }
  record = { version: C.SCHEMA_VERSION, build: C.BUILD, id,
    created: now.toISOString(), createdDay: C.localDay(now), lastDay: C.localDay(now),
    device: deviceCategory(), role: $('role').value, events: [] };
  log('enrol'); showExperiment();
});
for (const button of document.querySelectorAll('[data-mode]')) button.addEventListener('click', () => { if (!startInProgress) chooseMode(button.dataset.mode); });
$('detector').addEventListener('change', () => {
  if (startInProgress) { $('detector').value = detectorKind; return; }
  stopCamera(); detectorKind = $('detector').value;
  foreground.reset();
  $('captureBackground').hidden = detectorKind !== 'foreground';
  $('calibrate').disabled = detectorKind === 'hand';
  setStatus('Recognition method changed. Enable camera again; previous calibration was discarded.');
});
$('captureBackground').addEventListener('click', () => {
  if (input !== 'camera' || detectorKind !== 'foreground' || interrupted || stale ||
      !lastFrameAt || performance.now() - lastFrameAt > 1500) {
    setStatus('Wait for live, fresh camera frames before capturing the empty scene.'); return;
  }
  cancelProbe('Background is being recaptured; benchmark discarded.');
  if (zoneControl.active()) {
    zoneControl.finish(performance.now(), 'interrupted');
    refreshZoneControl();
  }
  resetChallenge(); foreground.reset(); backgroundCapture = true;
  $('start').disabled = true; $('captureBackground').disabled = true;
  setStatus('Keep all moving objects out of view during empty-background capture.');
});
$('camera').addEventListener('click', startCamera);
$('stop').addEventListener('click', () => { stopCamera(); setStatus('Camera stopped.'); draw(null); });
$('sample').addEventListener('click', () => {
  if (startInProgress) return;
  stopCamera(); input = 'touch';
  $('inputLabel').textContent = 'Touch fallback'; $('start').disabled = false;
  for (const id of ['tapLeft', 'tapMiddle', 'tapRight']) $(id).hidden = false;
  setStatus('Touch fallback. This is not camera recognition.'); draw(null);
});
$('calibrate').addEventListener('click', () => {
  if (input !== 'camera') return;
  if (detectorKind !== 'colour') {
    if (detectorKind === 'foreground') $('captureBackground').click();
    return;
  }
  if (zoneControl.active()) {
    zoneControl.finish(performance.now(), 'interrupted');
    refreshZoneControl();
  }
  reference = null; resetChallenge(); calibrating = true;
  $('start').disabled = true; setStatus('Tap your coloured object in the preview.');
});
view.addEventListener('pointerdown', event => {
  const bounds = view.getBoundingClientRect();
  handleTap(C.clamp((event.clientX - bounds.left) / bounds.width, 0, .999),
    C.clamp((event.clientY - bounds.top) / bounds.height, 0, .999));
});
['tapLeft', 'tapMiddle', 'tapRight'].forEach((id, i) =>
  $(id).addEventListener('click', () => handleTap((i + .5) / 3, .5)));
$('start').addEventListener('click', startChallenge);
$('saveProblem').addEventListener('click', () => {
  const value = $('problem').value.trim().slice(0, 240);
  if (!value) { $('feedbackStatus').textContent = 'No response entered.'; return; }
  log('problem_response', { input, mode, answer: value });
  $('feedbackStatus').textContent = 'Response saved locally. No information was uploaded.';
  $('saveProblem').disabled = true;
});
$('share').addEventListener('click', async () => {
  if (!/^https?:$/.test(location.protocol)) { $('recordStatus').textContent = 'Deploy over HTTPS before sharing.'; return; }
  try {
    if (navigator.share) { await navigator.share({ title: 'ANIMATE experiment', url: shareURL() }); log('share_sheet_opened'); }
    else if (navigator.clipboard?.writeText) { await navigator.clipboard.writeText(shareURL()); log('link_copied'); }
    else { $('recordStatus').textContent = 'Copy the URL from your address bar.'; return; }
    $('recordStatus').textContent = 'Link shared or copied; recipient delivery is unverified.';
  } catch (_) { $('recordStatus').textContent = 'Sharing cancelled or unavailable.'; }
});
$('export').addEventListener('click', exportRecord);
$('reset').addEventListener('click', () => {
  if (!confirm('Delete your local ANIMATE records on this device? Previously exported copies are not deleted.')) return;
  stopCamera();
  deviceBench.reset(); refreshDeviceBench();
  zoneControl.reset(); refreshZoneControl();
  let deletion = { ok: false, removed: 0, failed: 1 };
  try { deletion = C.deleteLocalResearchData(localStorage); } catch (_) { /* Local storage can be blocked. */ }
  record = null;
  importedRecords = []; importedLedger = []; unreadableFiles = 0;
  $('aggregate').value = ''; $('ledger').value = '';
  $('aggregateOutput').textContent = 'No records imported.';
  probeSamples = []; $('benchResults').textContent = 'No completed samples.';
  $('lab').hidden = true; $('results').hidden = true;
  $('feedbackPanel').hidden = true; $('intro').hidden = false;
  $('consent').checked = false; $('adult').checked = false; $('saveProblem').disabled = false;
  $('introerr').textContent = deletion.ok ?
    'Local ANIMATE research records were deleted from this browser. Previously exported or shared copies are unaffected.' :
    'Local data was cleared from this session, but browser storage deletion could not be confirmed. Please clear ANIMATE website data in Safari settings.';
  setStatus('Choose camera or touch fallback.');
});
$('aggregate').addEventListener('change', async event => {
  importedRecords = []; unreadableFiles = 0;
  const files = [...event.target.files].slice(0, 100);
  unreadableFiles += Math.max(0, event.target.files.length - files.length);
  for (const file of files) {
    if (file.size > 2_000_000) { unreadableFiles++; continue; }
    try {
      const value = JSON.parse(await file.text());
      if (!C.sanitizeRecord(value) || !value.exportedAt) throw Error('invalid or unexported record');
      importedRecords.push(value);
    } catch (_) { unreadableFiles++; }
  }
  showAggregate();
});
$('ledger').addEventListener('change', async event => {
  importedLedger = [];
  const file = event.target.files[0];
  if (!file) { showAggregate(); return; }
  try { if (file.size > 200_000) throw Error('ledger is too large'); importedLedger = parseLedger(await file.text()); }
  catch (e) { $('aggregateOutput').textContent = 'Ledger rejected: ' + e.message; return; }
  showAggregate();
});
if (DEBUG) {
  $('dbgbox').hidden = false;
  refreshDeviceBench();
  refreshZoneControl();
  $('zoneControlStart').addEventListener('click', () => {
    if (!stream || input !== 'camera' || interrupted || stale || calibrating ||
        backgroundCapture || probe.active || (run && !run.done) ||
        !(detectorKind === 'foreground' ? foreground.ready :
          detectorKind === 'hand' ? hand.ready : reference) ||
        !lastFrameAt || frameNumber === 0 || performance.now() - lastFrameAt > 1500) {
      $('zoneControlStatus').textContent =
        'Control blocked: enable and calibrate a fresh live camera, with no active challenge.';
      return;
    }
    zoneControl.begin(performance.now(), $('zoneControlExpected').value, detectorKind);
    refreshZoneControl();
  });
  $('zoneControlFinish').addEventListener('click', () => {
    if (zoneControl.active()) zoneControl.finish(performance.now(), 'manual');
    refreshZoneControl();
  });
  $('zoneControlCopy').addEventListener('click', async () => {
    const summary = zoneControl.snapshot(performance.now());
    if (summary.status === 'not_started') {
      $('zoneControlStatus').textContent = 'No control counts exist to copy.';
      return;
    }
    try {
      await navigator.clipboard.writeText(JSON.stringify(summary, null, 2));
      $('zoneControlCopy').textContent = 'Control counts copied';
    } catch (_) {
      $('zoneControlStatus').textContent =
        'Clipboard unavailable. Select and copy the numeric counts manually.';
    }
  });
  $('deviceBenchStart').addEventListener('click', () => {
    if (!stream || input !== 'camera' || interrupted || stale ||
        !lastFrameAt || frameNumber === 0 || performance.now() - lastFrameAt > 1500) {
      $('deviceBenchStatus').textContent =
        'Measurement blocked: enable a live camera and analyse fresh frames first.';
      return;
    }
    deviceBench.begin(performance.now(), detectorKind);
    refreshDeviceBench();
  });
  $('deviceBenchFinish').addEventListener('click', () => {
    deviceBench.finish(performance.now(), 'manual');
    refreshDeviceBench();
  });
  $('deviceBenchCopy').addEventListener('click', async () => {
    if (deviceBench.snapshot(performance.now()).status === 'not_started') {
      $('deviceBenchStatus').textContent = 'No camera measurement exists to copy.';
      return;
    }
    try {
      await navigator.clipboard.writeText(JSON.stringify(deviceBench.snapshot(performance.now()), null, 2));
      $('deviceBenchCopy').textContent = 'Summary copied';
    } catch (_) {
      $('deviceBenchStatus').textContent = 'Clipboard unavailable. Select and copy the numeric report manually.';
    }
  });
}

$('dbgcopy').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText($('diagnosticOutput').textContent); $('dbgcopy').textContent = 'Copied'; }
  catch (_) { $('dbgcopy').textContent = 'Copy unavailable: select text manually'; }
});
window.addEventListener('error', e => { lastError = String(e.message); updateDiagnostics(); });
window.addEventListener('unhandledrejection', e => { lastError = String(e.reason); updateDiagnostics(); });
window.addEventListener('pagehide', stopCamera);
document.addEventListener('visibilitychange', () => {
  if (document.hidden && stream) { stopCamera(); setStatus('Camera paused on interruption. Enable again to continue.'); }
});
window.addEventListener('resize', resizeCanvas);
if (window.ResizeObserver) new ResizeObserver(resizeCanvas).observe(view);
$('description').textContent = descriptions[mode];
resizeCanvas();
restoreRecord();
