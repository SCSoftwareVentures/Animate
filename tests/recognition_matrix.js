/* Deterministic SYNTHETIC vision matrix. No phone, no human, no AI model, no actual camera.
   Ground truth here is mathematical (a generated disk with known centre), so these results
   deliberately must not be presented as iPhone accuracy measurements. */
'use strict';
const C = require('../site/core.js');
const W=160,H=120,N=W*H;
const palettes={blue:[40,110,235],green:[38,220,65],red:[230,35,45]};
const lights={bright:1,normal:.7,dim:.3};
const rounds=60;
let seed=91127;
const rnd=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
function frame({color, exposure, clutter, present, sameHueBackground=false}) {
  const d=new Uint8ClampedArray(N*4);
  const rgb=palettes[color];
  const cx=.15+rnd()*.7, cy=.25+rnd()*.5;
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){
    let shade=80;
    // A fairly large same-hue surface is designed to expose false-positive limitations.
    let px=[shade,shade,shade];
    if (sameHueBackground && x>=3 && x<52 && y>=2 && y<77) px=rgb;
    if (clutter && !sameHueBackground && ((x>12&&x<25&&y>12&&y<25)||(x>130&&x<145&&y>85&&y<99))) px=[50,100,165];
    if(present && (x-cx*W)**2+(y-cy*H)**2<=144) px=rgb;
    let off=(y*W+x)*4;
    const perturb=(rnd()-.5)*14;
    for(let k=0;k<3;k++)d[off+k]=Math.max(0,Math.min(255,px[k]*exposure+perturb));
    d[off+3]=255;
  }
  return {data:d,cx,cy};
}
const reports=[];
for(const color of Object.keys(palettes)) {
  const ref=C.rgb2hsv(...palettes[color]);
  for(const [light,exposure] of Object.entries(lights)) for(const background of ['plain','cluttered']) {
    let hits=0, fp=0, wrong=0, rejected=0;
    for(let i=0;i<rounds;i++) {
      const present=frame({color,exposure,clutter:background==='cluttered',present:true});
      const point=C.locate(present.data,W,H,ref);
      if(point && !point.ambiguous && Math.hypot(point.x-present.cx,point.y-present.cy)<.12) hits++;
      else if(point && !point.ambiguous) wrong++;
      else rejected++;
      const empty=frame({color,exposure,clutter:background==='cluttered',present:false});
      const neg=C.locate(empty.data,W,H,ref);
      if(neg&&!neg.ambiguous)fp++;
    }
    reports.push({color,light,background,framesPerLabel:rounds,
      centredHits:hits,falsePositives:fp,mislocated:wrong,misses:rejected,
      centredHitRate:+(hits/rounds).toFixed(3),falsePositiveRate:+(fp/rounds).toFixed(3)});
  }
}
const backgrounds=[];
for(const color of Object.keys(palettes)) {
  const ref=C.rgb2hsv(...palettes[color]);
  for(const light of ['bright','normal','dim']) {
    let fp=0;
    for(let i=0;i<rounds;i++){
      const scene=frame({color,exposure:lights[light],present:false,clutter:true,sameHueBackground:true});
      const p=C.locate(scene.data,W,H,ref);
      if(p&&!p.ambiguous)fp++;
    }
    backgrounds.push({color,light,frames:rounds,falsePositives:fp,rate:+(fp/rounds).toFixed(3)});
  }
}
const sum=arr=>arr.reduce((a,b)=>a+b,0);
const summary={testKind:'Deterministic synthetic image generation, not real-camera accuracy',
  build:C.BUILD, rows:reports.length, framesPerLabel:rounds,
  generatedPositiveFrames:sum(reports.map(x=>x.framesPerLabel)),
  generatedNegativeFrames:sum(reports.map(x=>x.framesPerLabel)),
  positiveCentredHitRate:+(sum(reports.map(x=>x.centredHits))/sum(reports.map(x=>x.framesPerLabel))).toFixed(3),
  negativeFalsePositiveRate:+(sum(reports.map(x=>x.falsePositives))/sum(reports.map(x=>x.framesPerLabel))).toFixed(3),
  sameHueSurfaceFalsePositiveRate:+(sum(backgrounds.map(x=>x.falsePositives))/sum(backgrounds.map(x=>x.frames))).toFixed(3),
  conditions:reports, sameHueSurface:backgrounds,
  caveat:'Highly artificial, correlated frames; confidence intervals and market/real-device accuracy claims are inappropriate.'};
console.log(JSON.stringify(process.argv.includes('--summary') ? {build:summary.build,rows:summary.rows,generatedPositiveFrames:summary.generatedPositiveFrames,generatedNegativeFrames:summary.generatedNegativeFrames,positiveCentredHitRate:summary.positiveCentredHitRate,negativeFalsePositiveRate:summary.negativeFalsePositiveRate,sameHueSurfaceFalsePositiveRate:summary.sameHueSurfaceFalsePositiveRate,testKind:summary.testKind} : summary,null,2));
