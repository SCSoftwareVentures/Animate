'use strict';
const assert = require('node:assert/strict');
const {pointFromResult, createHandDetector} = require('../site/hand_ml.js');
let passed=0;
function check(name, fn){fn(); console.log('PASS',name);passed++;}
function hand(x,y){const h=Array.from({length:21},()=>({x:0.4,y:0.6})); h[8]={x,y};return h;}
check('no hand means no trigger',()=>assert.equal(pointFromResult({landmarks:[]}),null));
check('one hand fingertip maps to zone control',()=>assert.deepEqual(pointFromResult({landmarks:[hand(.8,.3)]}),{x:.8,y:.3,source:'index-fingertip'}));
check('two hands fail closed',()=>assert.deepEqual(pointFromResult({landmarks:[hand(.1,.3),hand(.8,.3)]}),{ambiguous:true}));
check('invalid or out-of-range landmark rejected',()=>{assert.equal(pointFromResult({landmarks:[hand(-.1,.5)]}),null);assert.equal(pointFromResult({landmarks:[hand(NaN,.5)]}),null);assert.equal(pointFromResult({landmarks:[{}]}),null);});
(async()=>{
 let closes=0, inference=0;
 const engine={detectForVideo:()=>{inference++;return {landmarks:[hand(.15,.5)]};},close:()=>closes++};
 const detector=createHandDetector({loader:async()=>engine,minIntervalMs:100});
 await detector.start();
 assert.equal(detector.ready,true);
 check('infer first frame',()=>assert.equal(detector.detect({},100).x,.15));
 check('throttle does not invent a measurement',()=>assert.deepEqual(detector.detect({},110),{skipped:true}));
 check('next genuine frame is processed',()=>{assert.equal(detector.detect({},210).x,.15); assert.equal(inference,2);});
 check('inference metrics separated',()=>{assert.equal(detector.metrics().inferenceCount,2);assert.equal(detector.metrics().model,'mediapipe-hand-landmarker-float16-v1');});
 check('backwards timestamp stops scoring',()=>assert.throws(()=>detector.detect({},205),/timestamp/));
 check('runtime closed after invalid timestamp',()=>{assert.equal(detector.ready,false);assert.equal(closes,1);});
 let obsoleteLoads=0;
 const cancelledBeforeLoad=createHandDetector({loader:()=>{
   obsoleteLoads++; return {detectForVideo:()=>({landmarks:[]}),close:()=>closes++};
 }});
 const cancelledBeforeLoadPromise=cancelledBeforeLoad.start();
 cancelledBeforeLoad.stop();
 assert.equal(await cancelledBeforeLoadPromise,false);
 check('same-turn cancellation prevents obsolete model initialization',()=>{
   assert.equal(obsoleteLoads,0);assert.equal(cancelledBeforeLoad.ready,false);
 });
 let resolve;
 const inFlight=createHandDetector({loader:()=>new Promise(r=>{resolve=r;})});
 const promise=inFlight.start();await Promise.resolve();inFlight.stop(); resolve({detectForVideo:()=>{},close:()=>closes++});
 assert.equal(await promise,false);assert.equal(inFlight.ready,false);assert.equal(closes,2);
 check('in-flight model initialization cancelled on stop',()=>assert.equal(inFlight.ready,false));
 const bad=createHandDetector({loader:async()=>({close:()=>{}})});
 await assert.rejects(()=>bad.start(),/Invalid local hand/);
 check('invalid model engine cannot be used',()=>assert.equal(bad.ready,false));
 const throws=createHandDetector({loader:async()=>({detectForVideo:()=>{throw Error('bad inference')},close:()=>closes++})});
 await throws.start();assert.throws(()=>throws.detect({},100),/bad inference/);
 check('inference error stops the ML detector',()=>assert.equal(throws.ready,false));
 // A hung loader must not hold an iPhone camera indefinitely.
 let late;
 const slow=createHandDetector({loader:()=>new Promise(r=>{late=r;}),loadTimeoutMs:25});
 await assert.rejects(()=>slow.start(),/timed out/);
 check('missing or hanging ML model times out and fails closed',()=>assert.equal(slow.ready,false));
 const beforeLate=closes;
 late({detectForVideo:()=>({landmarks:[]}),close:()=>closes++});
 await new Promise(resolve=>setTimeout(resolve,0));
 check('late model from timed-out attempt is closed, never activated',()=>{
   assert.equal(slow.ready,false);assert.equal(closes,beforeLate+1);
 });
 let reloadClose=0;
 const restart=createHandDetector({loader:async()=>({detectForVideo:()=>({landmarks:[]}),close:()=>reloadClose++})});
 await restart.start();await restart.start();
 check('restarting an active ML engine closes previous instance',()=>{
   assert.equal(restart.ready,true);assert.equal(reloadClose,1);
 });
 restart.stop();
 check('stopping restarted ML engine closes its final instance',()=>assert.equal(reloadClose,2));
 assert.throws(()=>createHandDetector({loadTimeoutMs:0}),/deadline/);
 check('zero model load deadline rejected',()=>{});
 console.log(`${passed}/${passed} hand-ML adapter tests passed`);
})().catch(e=>{console.error(e);process.exit(1)});
