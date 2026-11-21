// node tests/test_core.js  (no dependencies)
const assert = require('node:assert/strict');
const C = require('../site/core.js');
const W = 160, H = 120;
let passed = 0;
const t = (name, fn) => { fn(); passed++; console.log('ok -', name); };

function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
function scene({ blobs = [], bg = [120, 120, 125], noise = 0, gain = 1, seed = 1 } = {}) {
  const d = new Uint8ClampedArray(W * H * 4), R = rng(seed);
  for (let i = 0; i < W * H; i++) { d[i*4] = bg[0]; d[i*4+1] = bg[1]; d[i*4+2] = bg[2]; d[i*4+3] = 255; }
  for (const b of blobs) for (let y = 0; y < H; y++) for (let x = 0; x < W; x++)
    if ((x - b.x * W) ** 2 + (y - b.y * H) ** 2 <= b.r ** 2) { const i = (y * W + x) * 4; d[i] = b.rgb[0]; d[i+1] = b.rgb[1]; d[i+2] = b.rgb[2]; }
  for (let i = 0; i < W * H; i++) for (let k = 0; k < 3; k++) d[i*4+k] = d[i*4+k] * gain + (noise ? (R() + R() + R() - 1.5) * noise * 2 : 0);
  return d;
}
const RED = [217, 33, 33], BLUE = [30, 70, 220], REF = C.rgb2hsv(...RED);
const obj = (x, o = {}) => ({ x, y: .5, r: 12, rgb: RED, ...o });

t('hsv conversion + hue wrap (v0.1 assertions kept)', () => {
  assert.deepEqual(C.rgb2hsv(255, 0, 0), [0, 1, 1]); assert.equal(C.hueDist(359, 1), 2);
});
t('locates object in each zone within 0.02', () => {
  for (const x of [.17, .5, .83]) { const p = C.locate(scene({ blobs: [obj(x)] }), W, H, REF); assert(p && Math.abs(p.x - x) < .02, 'x=' + x); }
});
t('rejects non-matching hue and low-saturation reference', () => {
  assert.equal(C.locate(scene({ blobs: [obj(.5, { rgb: BLUE })] }), W, H, REF), null);
  assert.equal(C.locate(scene({ blobs: [obj(.5)] }), W, H, [0, .1, 1]), null);
});
t('negative control: 300 random noisy walls never yield a detection', () => {
  const R = rng(3); let fp = 0;
  for (let k = 0; k < 300; k++) if (C.locate(scene({ bg: [R()*255, R()*255, R()*255], noise: 25, seed: k }), W, H, [R()*360, .8, .8])) fp++;
  assert.equal(fp, 0);
});
t('REGRESSION: a stray same-colour pixel/patch far away no longer loses the object', () => {
  for (const r of [0, 1, 3, 6]) { const p = C.locate(scene({ blobs: [obj(.17), obj(.875, { y: .17, r })] }), W, H, REF); assert(p && Math.abs(p.x - .17) < .02, 'stray r=' + r); }
});
t('two equal objects are flagged ambiguous', () => {
  const p = C.locate(scene({ blobs: [obj(.17), obj(.83)] }), W, H, REF); assert(p && p.ambiguous);
});
t('sensor noise sigma=30 still tracks (v0.1 failed at sigma=20)', () => {
  let ok = 0; for (let k = 0; k < 30; k++) if (C.locate(scene({ blobs: [obj(.5)], noise: 30, seed: k }), W, H, REF)) ok++; assert(ok >= 28, 'ok=' + ok);
});
t('hue drift of +/-20 deg tolerated, +/-30 rejected', () => {
  const shift = dh => { const [r, g, b] = (() => { const [h, s, v] = REF; const hh = ((h + dh) % 360 + 360) % 360, c = v*s, x = c*(1-Math.abs((hh/60)%2-1)), m = v-c; const a = hh<60?[c,x,0]:hh<120?[x,c,0]:hh<180?[0,c,x]:hh<240?[0,x,c]:hh<300?[x,0,c]:[c,0,x]; return a.map(q => (q+m)*255); })(); return [r, g, b]; };
  assert(C.locate(scene({ blobs: [obj(.5, { rgb: shift(20) })] }), W, H, REF));
  assert(C.locate(scene({ blobs: [obj(.5, { rgb: shift(-20) })] }), W, H, REF));
  assert.equal(C.locate(scene({ blobs: [obj(.5, { rgb: shift(30) })] }), W, H, REF), null);
});
t('object larger than 25% of frame is rejected (documented limit)', () => {
  assert.equal(C.locate(scene({ blobs: [obj(.5, { r: 50 })] }), W, H, REF), null);
});
t('sampleReference is robust to a single hot pixel; skinLike flags skin hues', () => {
  const d = scene({ blobs: [obj(.5)] }); const i = (60 * W + 80) * 4; d[i] = 255; d[i+1] = 255; d[i+2] = 255;
  const r = C.sampleReference(d, W, H, 80, 60, 3); assert(r && C.hueDist(r[0], 0) < 5 && r[1] > .8);
  assert(C.skinLike([20, .5, .8])); assert(!C.skinLike(C.rgb2hsv(...BLUE)));
});
t('zone tracker: needs 260 ms dwell, survives one dropped frame, no 10% dead band', () => {
  const z = C.createZoneTracker(); let fired = null, now = 0;
  for (let i = 0; i < 20; i++) { now += 33; const p = (i === 4) ? null : { x: .5 }; const r = z.update(p, now); if (r.fired !== null) { fired = r.fired; break; } }
  assert.equal(fired, 1);
  const z2 = C.createZoneTracker(); let f2 = null; now = 0;
  for (let i = 0; i < 20; i++) { now += 33; const r = z2.update({ x: .335 + (i % 2 ? .01 : -.01) }, now); if (r.fired !== null) { f2 = r.fired; break; } }
  assert(f2 !== null, 'object on a zone boundary must still resolve to a zone');
  const z3 = C.createZoneTracker(); now = 0; let f3 = null;
  for (let i = 0; i < 30; i++) { now += 33; const r = z3.update(i % 2 ? null : { x: .5 }, now); if (r.fired !== null) f3 = r.fired; }
  assert.equal(f3, 1, 'alternating detection (50% per-frame) must still fire');
  const z4 = C.createZoneTracker(); now = 0; let f4 = null;
  for (let i = 0; i < 30; i++) { now += 33; const r = z4.update(null, now); if (r.fired !== null) f4 = r.fired; }
  assert.equal(f4, null, 'no object -> never fires');
});
t('local-day maths (Melbourne-style midnight), not UTC', () => {
  assert.equal(C.dayDiff('2026-11-20', '2026-11-27'), 7); assert.equal(C.dayDiff('2026-12-30', '2027-01-02'), 3);
  assert.equal(C.localDay(new Date(2026, 10, 20, 9, 30)), '2026-11-20'); assert.equal(C.localDay(new Date(2026, 10, 20, 23, 59)), '2026-11-20');
});
const e = (type, time, extra = {}) => ({ type, time, ...extra });
const iso = min => new Date(Date.parse('2026-11-01T00:00:00.000Z') + min * 60000).toISOString();
const base = (id = 'participant-001', events = [], extra = {}) => ({
  version: C.SCHEMA_VERSION, build: C.BUILD, id,
  device: 'iPhone', created: iso(0), createdDay: '2026-11-01',
  exportedAt: iso(8 * 24 * 60), events, ...extra
});
const start = (runId = 'camera-run-001', mode = 'play', minute = 1, input = 'camera') =>
  e('start', iso(minute), { runId, mode, input, detector: input === 'camera' ? 'colour' : undefined });
const complete = (runId = 'camera-run-001', mode = 'play', minute = 2, input = 'camera') =>
  e('complete', iso(minute), { runId, mode, input, elapsed: 60000, detector: input === 'camera' ? 'colour' : undefined });

t('schema v0.5: matched start and complete counts one camera completion', () => {
  const r = base('participant-001', [start(), complete()]);
  const s = C.summarize([r]);
  assert.equal(s.acceptedRecords, 1);
  assert.equal(s.provisional.cameraTesters, 1);
  assert.equal(s.provisional.first, 1);
  assert.equal(s.verified.first, 0, 'no ledger, no verified success');
});
t('ADVERSARIAL: completion without matching start is rejected', () => {
  const s = C.summarize([base('participant-001', [start('another-run'), complete()])]);
  assert.equal(s.provisional.cameraTesters, 1);
  assert.equal(s.provisional.first, 0);
});
t('ADVERSARIAL: completion with wrong mode, wrong input or impossible order is rejected', () => {
  const bad = [start(), complete('camera-run-001', 'learn'),
    complete('camera-run-001', 'play', 0),
    e('complete', iso(2), {runId:'camera-run-001',mode:'play',input:'touch',elapsed:60000})];
  assert.equal(C.summarize([base('participant-001', bad)]).provisional.first, 0);
});
t('ADVERSARIAL: duplicate completions do not produce extra successes', () => {
  const r = base('participant-001', [start(), complete(), complete()]);
  assert.equal(C.recordMetrics(C.sanitizeRecord(r)).validCameraCompletions, 1);
});
t('ADVERSARIAL: huge nested event payload does not crash or count', () => {
  const veryLarge = 'x'.repeat(600000);
  const r = base('participant-001', [
    { type: 'complete', time: iso(2), runId:'camera-run-001', input:'camera',mode:'play', note:veryLarge },
    { type: 'start', time: iso(1), runId: {nested: veryLarge}, input:'camera', mode:'play' }
  ]);
  const s = C.summarize([null, r, {id:'x',events:[]}]);
  assert.equal(s.acceptedRecords, 1);
  assert.equal(s.provisional.first, 0);
});
t('ADVERSARIAL: oversized event array and invalid build are rejected', () => {
  const huge = base('participant-002', Array(C.MAX_EVENTS+1).fill(null));
  const old = base('participant-003', [], {build:'0.2.0'});
  assert.equal(C.summarize([huge, old]).rejectedRecords, 2);
});
t('only ledger matched records count as verified', () => {
  const r = base('participant-001', [start(), complete()]);
  const v = C.summarize([r], [C.ledgerKey(r)]);
  assert.equal(v.ledgerMatches, 1);
  assert.equal(v.verified.first, 1);
  const no = C.summarize([r], ['participant-001|2026-11-02|iPhone']);
  assert.equal(no.verified.first, 0);
});
t('7-day retention eligibility is fixed at export, not aggregation time', () => {
  const events = [start(), e('return', iso(24*60+1), {day:'2026-11-02',days:1})];
  const early = base('participant-001', events, {exportedAt:iso(2*24*60)});
  const later = base('participant-002', events);
  assert.equal(C.summarize([early]).provisional.returnUnobservable, 1);
  assert.equal(C.summarize([early]).provisional.returnEligible, 0);
  assert.equal(C.summarize([later]).provisional.returned, 1);
});
t('ADVERSARIAL: conflicting return day and day count is not accepted', () => {
  const r = base('participant-001', [start(), e('return',iso(24*60),{day:'2026-11-01',days:1})]);
  assert.equal(C.summarize([r]).provisional.returned, 0);
});
t('ADVERSARIAL: no export is unobservable and cannot be ledger-verified', () => {
  const r = base('participant-001', [start(), complete()], {exportedAt:undefined});
  const s = C.summarize([r], [C.ledgerKey(r)]);
  assert.equal(s.provisional.returnUnobservable, 1);
  assert.equal(s.verified.first, 0);
});
t('ADVERSARIAL: two-second silent gap cannot count as dwell', () => {
  const z = C.createZoneTracker();
  assert.equal(z.update({ x: .5 }, 0).fired, null);
  assert.equal(z.update({ x: .5 }, 2100).fired, null);
  assert.equal(z.update({ x: .5 }, 2200).fired, null);
  assert.equal(z.update({ x: .5 }, 2300).fired, null);
  assert.equal(z.update({ x: .5 }, 2400).fired, 1);
});
t('ADVERSARIAL: nonmonotonic times, ambiguous point and invalid coordinate do not fire', () => {
  const z = C.createZoneTracker();
  z.update({x:.5}, 1000);
  z.update({x:.5}, 950);
  assert.equal(z.update({x:.5,ambiguous:true}, 1000).fired,null);
  assert.equal(z.update({x:NaN}, 1100).fired,null);
  assert.equal(z.update({x:.5}, 1150).fired,null);
});

t('EVIDENCE: impossible Gregorian dates and noncanonical UTC timestamps are rejected', () => {
  for (const bad of [
    '2026-02-30T00:00:00.000Z', '2026-13-01T00:00:00.000Z',
    '2026-11-01T24:00:00.000Z', '2026-11-01T00:00:00+00:00'
  ]) {
    assert.equal(C.summarize([base('participant-date01', [], { created: bad })]).acceptedRecords, 0, bad);
  }
  assert.equal(C.summarize([base('participant-date02', [], {createdDay:'2026-02-30'})]).acceptedRecords, 0);
});
t('EVIDENCE: local enrollment day must align with created UTC date', () => {
  assert.equal(C.summarize([base('participant-date03', [], {createdDay:'2026-11-10'})]).acceptedRecords, 0);
  assert.equal(C.summarize([base('participant-date04', [], {createdDay:'2026-10-31'})]).acceptedRecords, 1,
    'legitimate UTC/local date-boundary offset must remain valid');
});
t('EVIDENCE: return-day claims inconsistent with event timestamps do not count', () => {
  const invalid = base('participant-date05', [start(),
    e('return', iso(24*60+1), {day:'2026-11-07', days:6})]);
  assert.equal(C.summarize([invalid]).provisional.returned, 0);
  const valid = base('participant-date06', [start(),
    e('return', iso(24*60+1), {day:'2026-11-02', days:1})]);
  assert.equal(C.summarize([valid]).provisional.returned, 1);
});

t('v0.4 probe validates manual condition labels and rejects invalid timings', () => {
  const p = C.createRecognitionProbe();
  assert.throws(() => p.start({colour:'white', light:'dim', background:'plain',expected:'present'}));
  p.start({ colour:'blue', light:'normal', background:'plain', expected:'present' });
  assert.throws(() => p.add(null, -1));
  assert.throws(() => p.add(null, Infinity));
  assert.equal(p.progress, 0);
  assert.equal(p.add({ x: .5, y: .5 }, 0.7).frames, 1);
  p.add({ ambiguous: true }, 0.3);
  p.add(null, 0.2);
  const s = p.finish();
  assert.equal(s.frames, 3);
  assert.equal(s.matched, 1);
  assert.equal(s.ambiguous, 1);
  assert.equal(s.complete, false);
  assert.equal(p.active, false);
  assert.equal(p.finish(), null);
});
t('v0.4 probe requires 600 unique samples for completed trial', () => {
  const p = C.createRecognitionProbe();
  p.start({ colour:'green',light:'bright',background:'cluttered',expected:'absent' });
  for (let i=0; i<C.PROBE_FRAMES; i++) p.add(null, 0.5);
  const s = p.finish();
  assert.equal(s.frames, C.PROBE_FRAMES);
  assert.equal(s.matched, 0);
  assert.equal(s.complete, true);
  assert.equal(s.avgMs, .5);
});
t('v0.4 probe result survives controlled sanitize and excludes nested untrusted fields', () => {
  const p = C.createRecognitionProbe();
  p.start({colour:'blue',light:'normal',background:'plain',expected:'present'});
  p.add({x:.5}, 0.1);
  const sample = p.finish();
  const r = base('participant-019', [e('benchmark_sample', iso(1), {sample:{...sample,detector:'foreground',secret:'ignored'}})]);
  const safe = C.sanitizeRecord(r);
  assert(safe && safe.events[0].sample);
  assert.equal(safe.events[0].sample.secret, undefined);
  assert.equal(safe.events[0].sample.matched, 1);
  const bad = base('participant-020', [e('benchmark_sample', iso(1), {sample:{...sample,detector:'foreground',matched:99}})]);
  assert.equal(C.sanitizeRecord(bad).events[0].sample, undefined);
});
t('v0.5 rejects mismatched detector labels in a start/complete pair', () => {
  const r=base('participant-081', [start(), {...complete(), detector:'foreground'}]);
  assert.equal(C.summarize([r]).provisional.first,0);
});
t('v0.5 separates verified outcomes by recognition method', () => {
  const r=base('participant-082',[start(), complete(),
    {...start('camera-run-002','play',3),detector:'foreground'},
    {...complete('camera-run-002','play',4),detector:'foreground'}]);
  const s=C.summarize([r],[C.ledgerKey(r)]);
  assert.equal(s.byDetector.colour.verifiedCompleted,1);
  assert.equal(s.byDetector.foreground.verifiedCompleted,1);
});
t('v0.5 unlabelled camera starts cannot inflate completion evidence', () => {
  const r=base('participant-083',[{...start(),detector:undefined},{...complete(),detector:undefined}]);
  assert.equal(C.summarize([r]).provisional.first,0);
});
t('v0.4 calibration must match a unique nearby blob, not a distant object', () => {
  const frame = scene({blobs:[obj(.5)]});
  const centre = C.calibrationCandidate(frame,W,H,REF,.5,.5);
  assert(centre && Math.abs(centre.x-.5)<.05);
  assert.equal(C.calibrationCandidate(frame,W,H,REF,.1,.5),null);
  assert.equal(C.calibrationCandidate(scene({blobs:[obj(.25),obj(.75)]}),W,H,REF,.25,.5),null);
  assert.equal(C.calibrationCandidate(frame,W,H,REF,Infinity,.5),null);
});


t('EVIDENCE: role segmentation preserves declared customer cohort without conflating completion and paid demand', () => {
  const educator = base('participant-role-01', [start(), complete()], {role:'Educator'});
  const parent = base('participant-role-02', [start(), complete()], {role:'Parent / family'});
  const summary = C.summarize([educator, parent], [C.ledgerKey(educator)]);
  assert.equal(summary.byRole.Educator.acceptedExports, 1);
  assert.equal(summary.byRole.Educator.verifiedExports, 1);
  assert.equal(summary.byRole.Educator.verified.first, 1);
  assert.equal(summary.byRole['Parent / family'].provisional.first, 1);
  assert.equal(summary.byRole['Parent / family'].verified.first, 0);
  assert.equal(summary.byRole.Educator.verified.returnEligible, 1);
});
t('EVIDENCE: missing role remains unclassified; unexpected or invented roles are rejected', () => {
  const absent = base('participant-role-03', [start(), complete()]);
  const forged = base('participant-role-04', [start(), complete()], {role:'Bank account manager'});
  const malicious = base('participant-role-05', [start(), complete()], {role:{toString:()=> 'Educator'}});
  const summary = C.summarize([absent, forged, malicious]);
  assert.equal(summary.acceptedRecords, 1);
  assert.equal(summary.rejectedRecords, 2);
  assert.equal(summary.byRole.Unspecified.acceptedExports, 1);
  assert.equal(summary.byRole.Educator.acceptedExports, 0);
});
t('EVIDENCE: each customer segment has its own independent denominator', () => {
  const a = base('participant-role-06', [start(), complete()], {role:'Educator'});
  const b = base('participant-role-07', [start('camera-run-002')], {role:'Educator'});
  const c = base('participant-role-08', [start(), complete()], {role:'Developer'});
  const summary = C.summarize([a,b,c],[C.ledgerKey(a),C.ledgerKey(b)]);
  assert.equal(summary.byRole.Educator.verified.cameraTesters, 2);
  assert.equal(summary.byRole.Educator.verified.first, 1);
  assert.equal(summary.byRole.Developer.verified.cameraTesters, 0);
  assert.equal(summary.verified.cameraTesters, 2);
});

t('EVIDENCE: completed camera challenge feedback is counted once and private text stays out of summaries', () => {
  const feedback = e('problem_response', iso(3), {
    mode:'play', input:'camera', answer:'I currently use paper manipulatives.'
  });
  const r=base('participant-feedback-01', [start(),complete(),feedback,feedback], {role:'Educator'});
  const normalized=C.sanitizeRecord(r);
  const saved=normalized.events.find(x=>x.type==='problem_response');
  assert.equal(saved.feedbackProvided,true);
  assert.equal(saved.answer,undefined,'do not propagate participant free-text into reports');
  const summary=C.summarize([r],[C.ledgerKey(r)]);
  assert.equal(summary.provisional.feedbackRespondents,1);
  assert.equal(summary.verified.feedbackRespondents,1);
  assert.equal(summary.verified.feedbackAfterCameraCompletion,1);
  assert.equal(summary.byRole.Educator.verified.feedbackRespondents,1);
  assert(!JSON.stringify(summary).includes('paper manipulatives'));
});
t('EVIDENCE: malformed, empty and over-limit feedback cannot inflate response counts', () => {
  const payloads=['   ', 'x'.repeat(241), {private:'somebody'}, null];
  for (const [i,answer] of payloads.entries()) {
    const r=base('participant-feedback-bad-'+i,[start(),complete(),
      e('problem_response',iso(3),{mode:'play',input:'camera',answer})]);
    const summary=C.summarize([r]);
    assert.equal(summary.provisional.feedbackRespondents,0,'case '+i);
    assert.equal(summary.provisional.feedbackAfterCameraCompletion,0,'case '+i);
  }
});
t('EVIDENCE: touch feedback and feedback preceding camera completion are not camera completion evidence', () => {
  const touch=base('participant-feedback-touch',[start('touch-run-001','play',1,'touch'),
    e('problem_response',iso(3),{mode:'play',input:'touch',answer:'A real alternative'})]);
  const before=base('participant-feedback-before',[start(),
    e('problem_response',iso(1.5),{mode:'play',input:'camera',answer:'Prior answer'}),
    complete()]);
  for (const r of [touch,before]) {
    const summary=C.summarize([r]);
    assert.equal(summary.provisional.feedbackRespondents,1);
    assert.equal(summary.provisional.feedbackAfterCameraCompletion,0);
  }
});

t('PRIVACY: browser restore projects unknown top-level and nested event fields away', () => {
  const raw = base('participant-local-restore-01', [
    start(), complete(),
    e('problem_response', iso(3), {mode:'play', input:'camera',
      answer:'Paper fraction cards', nested:{private:'UNEXPECTED_NESTED_SECRET'}})
  ], {role:'Educator', lastDay:'2026-11-02'});
  raw.unexpectedCredential = {secret:'UNEXPECTED_TOP_LEVEL_SECRET'};
  raw.events[0].nestedHuge = {password:'UNEXPECTED_START_SECRET'};
  const safe = C.sanitizeLocalRecord(raw);
  assert(safe);
  assert.equal(safe.lastDay,'2026-11-02');
  assert.equal(safe.role,'Educator');
  assert.equal(safe.events[2].answer,'Paper fraction cards');
  for (const mark of ['UNEXPECTED_NESTED_SECRET','UNEXPECTED_TOP_LEVEL_SECRET','UNEXPECTED_START_SECRET'])
    assert(!JSON.stringify(safe).includes(mark), mark);
  assert.deepEqual(C.sanitizeLocalRecord(safe), safe, 'normalised local storage must be stable');
  const aggregate = C.summarize([safe]);
  assert.equal(aggregate.provisional.feedbackRespondents, 1);
  assert(!JSON.stringify(aggregate).includes('Paper fraction cards'), 'aggregation must stay text-free');
});
t('PRIVACY: local export projection preserves only bounded diagnostic fields', () => {
  const raw = base('participant-local-restore-02', [
    e('camera_ready', iso(1), {facing:'user', detector:'colour', dangerous:'NEVER_EXPORT'}),
    e('calibrated', iso(2), {skinLike:true, secret:'NEVER_EXPORT'}),
    e('camera_error', iso(3), {reason:'Camera interrupted', name:'NotAllowedError',
      privateRecord:{identifier:'NEVER_EXPORT'}})
  ], {role:'Developer', lastDay:'2026-11-03'});
  const safe = C.sanitizeLocalRecord(raw);
  assert.deepEqual(safe.events[0].facing, 'user');
  assert.equal(safe.events[1].skinLike, true);
  assert.equal(safe.events[2].reason, 'Camera interrupted');
  assert.equal(safe.events[2].name, 'NotAllowedError');
  assert(!JSON.stringify({...safe,exportedAt:iso(8*24*60)}).includes('NEVER_EXPORT'));
});
t('PRIVACY: malformed local role and implausible last-day states fail closed or fall back', () => {
  const malformed = base('participant-local-restore-03', [], {role:{pretend:'Educator'}});
  assert.equal(C.sanitizeLocalRecord(malformed), null);
  const legacy = base('participant-local-restore-04', [], {lastDay:'2028-04-01'});
  const safe = C.sanitizeLocalRecord(legacy);
  assert(safe && !Object.hasOwn(safe,'role'), 'legacy record must not invent a role');
  assert.equal(safe.lastDay, safe.createdDay);
  assert.equal(C.summarize([safe]).byRole.Unspecified.acceptedExports, 1);
});

t('PRIVACY: deletion clears all historical ANIMATE keys, preserves unrelated site data', () => {
  const data = new Map([
    ['animate-validation-v1', 'old'], ['animate-validation-v05', 'old'],
    ['animate-validation-v07', 'latest'], ['animate-validation', 'old-root'],
    ['another-app-token', 'leave alone'], ['animate-demo-setting', 'leave alone']
  ]);
  const storage = {
    get length() { return data.size; },
    key(i) { return [...data.keys()][i] ?? null; },
    getItem(k) { return data.get(k) ?? null; },
    removeItem(k) { data.delete(k); }
  };
  const outcome = C.deleteLocalResearchData(storage);
  assert.deepEqual(outcome, {ok: true, removed: 4, failed: 0});
  assert.deepEqual([...data.keys()], ['another-app-token', 'animate-demo-setting']);
  assert.deepEqual(C.deleteLocalResearchData(storage), {ok: true, removed: 0, failed: 0});
});
t('PRIVACY: blocked storage reports failure instead of claiming deletion', () => {
  const denied = { get length() { throw Error('SecurityError'); } };
  const outcome = C.deleteLocalResearchData(denied);
  assert.equal(outcome.ok, false);
  assert.equal(outcome.removed, 0);
  assert(outcome.failed >= 1);
});
t('PRIVACY: partial deletion continues and reports remaining record', () => {
  const data = new Map([['animate-validation-v1', 'a'], ['animate-validation-v07', 'b'],
    ['unrelated', 'keep']]);
  const storage = {
    get length() { return data.size; },
    key(i) { return [...data.keys()][i] ?? null; },
    getItem(k) { return data.get(k) ?? null; },
    removeItem(k) { if (k === 'animate-validation-v1') throw Error('Denied');
      data.delete(k); }
  };
  const result = C.deleteLocalResearchData(storage);
  assert.deepEqual(result, {ok: false, removed: 1, failed: 1});
  assert(data.has('animate-validation-v1'));
  assert(!data.has('animate-validation-v07'));
  assert(data.has('unrelated'));
});

t('v0.7 authenticates hand event provenance within an export, not against an external issuer', () => {
  const model='mediapipe-hand-landmarker-float16-v1';
  const startHand={...start(),detector:'hand',model};
  const endHand={...complete(),detector:'hand',model};
  const r=base('participant-hand01',[startHand,endHand]);
  const summary=C.summarize([r],[C.ledgerKey(r)]);
  assert.equal(summary.byDetector.hand.verifiedCompleted,1);
  assert.equal(summary.byDetector.colour.verifiedCompleted,0);
});
t('v0.7 rejects model-less and mismatched hand completion',()=>{
  const model='mediapipe-hand-landmarker-float16-v1';
  const missing=base('participant-hand02',[{...start(),detector:'hand'}, {...complete(),detector:'hand'}]);
  assert.equal(C.summarize([missing]).provisional.cameraTesters,0);
  const mismatch=base('participant-hand03',[{...start(),detector:'hand',model}, {...complete(),detector:'hand',model:'faked-model'}]);
  assert.equal(C.summarize([mismatch]).byDetector.hand.provisionalCompleted,0);
});
t('v0.7 rejects hand results in the object-colour benchmark',()=>{
  const p=C.createRecognitionProbe();p.start({colour:'blue',light:'normal',background:'plain',expected:'present'});
  p.add({x:.5,y:.5},.2);const sample=p.finish();
  const r=base('participant-hand04',[e('benchmark_sample',iso(1),{sample:{...sample,detector:'hand'}})]);
  assert.equal(C.sanitizeRecord(r).events[0].sample,undefined);
});


t('DEVICE BENCH: 60-second sample separates analysed FPS from animation loop FPS', () => {
  const m=C.createDeviceBench();
  assert.equal(m.snapshot(0).status,'not_started');
  m.begin(1000,'colour');
  for(let second=1;second<=60;second++){
    m.noteWindow(1000+second*1000,18,60);
    m.noteLatency(12);
  }
  const result=m.snapshot(61000);
  assert.equal(result.status,'timed');assert.equal(result.complete,true);
  assert.equal(result.observedMs,60000);
  assert.equal(result.analysedFps.median,18);
  assert.equal(result.animationLoopFps.median,60);
  assert.equal(result.inferenceMs.p95,12);
  assert.equal(result.inferredFrames,60);
  assert.equal(result.sampleWindows,60);
  assert.equal(m.active(),false);
});
t('DEVICE BENCH: camera interruption fails incomplete and cannot later turn into a pass', () => {
  const m=C.createDeviceBench(5000);
  m.begin(100,'foreground');
  m.noteWindow(1100,16,59);m.noteLatency(4.5);
  m.noteInterruption(2300);
  m.noteWindow(6100,60,60);
  m.noteLatency(9);
  const result=m.snapshot(8000);
  assert.equal(result.status,'interrupted');
  assert.equal(result.complete,false);
  assert.equal(result.interruptions,1);
  assert.equal(result.observedMs,2200);
  assert.equal(result.inferredFrames,1);
});
t('DEVICE BENCH: explicit end is not a completed 60-second pass', () => {
  const m=C.createDeviceBench(2000);
  m.begin(0,'hand');
  m.noteLatency(9);
  const report=m.finish(700,'manual');
  assert.equal(report.complete,false);
  assert.equal(report.observedMs,700);
  assert.equal(report.detector,'hand');
  m.reset();
  assert.equal(m.snapshot(10000).detector,null);
  assert.equal(m.snapshot(10000).inferredFrames,0);
});
t('DEVICE BENCH: invalid, oversized or nonfinite samples cannot contaminate summary', () => {
  const m=C.createDeviceBench(3000);
  assert.throws(()=>m.begin(-5,'colour'));
  assert.throws(()=>m.begin(0,'unsupported'));
  assert.throws(()=>C.createDeviceBench(0));
  m.begin(0,'colour');
  m.noteWindow(1000,NaN,60);
  m.noteWindow(1000,9999,60);
  m.noteLatency(NaN);m.noteLatency(-1);
  m.noteWindow(1000,20,60);
  m.noteLatency(17);
  const r=m.finish(1000,'manual');
  assert.equal(r.sampleWindows,1);
  assert.equal(r.inferredFrames,1);
  assert.equal(r.inferenceMs.max,17);
});
t('DEVICE BENCH: numerically bounded report cannot contain identifiers or raw frames', () => {
  const m=C.createDeviceBench(1000);
  m.begin(0,'colour');
  for(let i=0;i<4500;i++)m.noteLatency(1+i%10);
  m.noteWindow(1000,28,60);
  const result=m.snapshot(1000);
  assert.equal(result.inferredFrames,4500);
  assert.equal(result.inferenceMs.samples,4096);
  assert.equal(result.unmeasuredLatencySamples,404);
  const serialized=JSON.stringify(result).toLowerCase();
  for (const forbidden of ['useragent','participantid','createdat','recordid','coordinates','video frame bytes']){
    assert(!serialized.includes('"' + forbidden + '":'));
  }
  assert(serialized.length < 1800);
});

console.log('\nPASS ' + passed + ' tests');
