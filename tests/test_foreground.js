// Deterministic tests of an opt-in colour-independent foreground tracker.
// Synthetic fixtures: no accuracy claims about actual phone video or objects.
const assert = require('node:assert/strict');
const { createForegroundDetector } = require('../site/foreground.js');
const W = 160, H = 120;
let passed = 0;
function t(name, fn) { fn(); passed++; console.log('ok -', name); }
function frame(blobs = [], background = [90, 90, 90], offset = 0) {
  const data = new Uint8ClampedArray(W * H * 4);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = (y * W + x) * 4;
    const inside = blobs.find(b => (x - b.x * W) ** 2 + (y - (b.y ?? .5) * H) ** 2 <= (b.radius || 12) ** 2);
    const color = inside ? (inside.colour || [180, 180, 180]) : background;
    data[i] = color[0] + offset; data[i+1] = color[1] + offset;
    data[i+2] = color[2] + offset; data[i+3] = 255;
  }
  return data;
}
function learn(d, img = frame()) { for (let i = 0; i < d.targetFrames; i++) d.capture(img, W, H); assert(d.ready); }
t('requires several fresh empty-scene frames and never detects before calibration', () => {
  const d = createForegroundDetector(); assert.throws(() => d.detect(frame(),W,H,1));
  for (let i = 0; i < 11; i++) assert.equal(d.capture(frame(), W,H).ready, false);
  assert.equal(d.capture(frame(),W,H).ready,true);
});
t('tracks a grey low-saturation object; colour method cannot isolate it', () => {
  const d=createForegroundDetector();learn(d);
  for(const x of [.17,.5,.83]) {
    const p=d.detect(frame([{x,colour:[190,190,190]}]),W,H,x*100);
    assert(p && Math.abs(p.x-x)<.025, 'x='+x);
  }
});
t('distinguishes two equal moving objects as ambiguous', () => {
  const d=createForegroundDetector();learn(d);
  const p=d.detect(frame([{x:.17},{x:.83}]),W,H,1);
  assert(p?.ambiguous);
});
t('ignores an empty scene, one stray changed pixel, and unchanged video frames', () => {
  const d=createForegroundDetector();learn(d);
  assert.equal(d.detect(frame(),W,H,1),null);
  const noise=frame();const i=(50*W+30)*4;noise[i]=255;noise[i+1]=255;noise[i+2]=255;
  assert.equal(d.detect(noise,W,H,2),null);
  assert.equal(d.detect(frame([{x:.5}]),W,H,2),null);
});
t('rejects large foreground change instead of treating moving background as an object', () => {
  const d=createForegroundDetector();learn(d);
  const large=frame([{x:.5,radius:65}]);
  assert.equal(d.detect(large,W,H,1),null);
});
t('modest uniform exposure shift is compensated', () => {
  const d=createForegroundDetector();learn(d);
  const p=d.detect(frame([{x:.5,colour:[185,185,185]}], [90,90,90], 13),W,H,1);
  assert(p && Math.abs(p.x-.5)<.03);
});
t('major lighting change fails closed', () => {
  const d=createForegroundDetector();learn(d);
  assert.equal(d.detect(frame([{x:.5}], [90,90,90],70), W,H,1),null);
});
t('movement during background capture invalidates the reference', () => {
  const d=createForegroundDetector();d.capture(frame(),W,H);
  const res=d.capture(frame([{x:.5,radius:45}]),W,H);
  assert.equal(res.unstable,true);assert.equal(d.ready,false);assert.equal(d.progress,0);
});
t('camera size change invalidates incoming frame rather than silently distorting',()=>{
  const d=createForegroundDetector();learn(d);
  assert.throws(()=>d.detect(frame(),80,H,1));
});
t('resets background and metric state on camera stop',()=>{
  const d=createForegroundDetector();learn(d);d.detect(frame([{x:.5}]),W,H,1);
  assert(d.metrics().framesDetected>0);d.reset();assert(!d.ready);assert.equal(d.metrics().framesDetected,0);
});
t('invalid frame data and invalid config are rejected',()=>{
  assert.throws(()=>createForegroundDetector({captureFrames:0}));
  const d=createForegroundDetector();assert.throws(()=>d.capture(new Uint8Array(3),W,H));
});
console.log(`\nPASS ${passed} foreground tests`);
