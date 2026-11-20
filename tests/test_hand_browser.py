"""Chromium app smoke tests WITHOUT navigation/network access.
Uses set_content, injected same bytes of core/app, a localStorage shim and canvas.captureStream
with a mocked getUserMedia. This validates UI logic and simulated video-frame processing,
NOT browser CSP enforcement, real camera permission, HTTPS delivery, or iPhone Safari.
Full-origin synthetic tests live in tests/e2e.py for GitHub Actions.
"""
import json
import sys
import shutil
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parent.parent / 'site'
checks = []

def check(name, ok, context=''):
    checks.append((name, bool(ok)))
    print(('PASS ' if ok else 'FAIL ') + name + ((' ' + context) if context else ''), flush=True)

def prepare(p, camera=False, benchmark=False, hand_mock=False, hand_hang=False):
    browser_path = os.environ.get('CHROMIUM_PATH') or shutil.which('chromium')
    options = {'executable_path': browser_path} if browser_path else {}
    browser = p.chromium.launch(**options, args=['--no-sandbox',
        '--autoplay-policy=no-user-gesture-required'])
    context = browser.new_context(viewport={'width':390,'height':844}, device_scale_factor=3,
        bypass_csp=True, accept_downloads=True, has_touch=True)
    page = context.new_page(); errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_content((SITE/'index.html').read_text())
    page.add_style_tag(content=(SITE/'styles.css').read_text())
    page.evaluate('''() => {
      const storage = new Map();
      Object.defineProperty(window,'localStorage',{configurable:true,value:{
        getItem:k=>storage.has(k)?storage.get(k):null,
        setItem:(k,v)=>storage.set(k,String(v)),
        removeItem:k=>storage.delete(k)
      }});
    }''')
    if benchmark:
        page.evaluate("""() => { const get=URLSearchParams.prototype.get;
          URLSearchParams.prototype.get=function(k){return k==='benchmark'?'1':get.call(this,k);}; }""")
    if camera:
        page.evaluate('''() => {
          Object.defineProperty(window,'isSecureContext',{configurable:true,value:true});
          const canvas = document.createElement('canvas'); canvas.width=320;canvas.height=240;
          const ctx = canvas.getContext('2d'); window.blobX=.5;
          function redraw(){
            ctx.fillStyle='rgb(120,120,125)';ctx.fillRect(0,0,320,240);
            if (window.showBlob !== false){ctx.fillStyle='rgb(217,33,33)';ctx.beginPath();ctx.arc(window.blobX*320,120,24,0,Math.PI*2);ctx.fill();}
          }
          redraw(); window.drawTimer=setInterval(redraw,66);
          window.pauseFrames=()=>clearInterval(window.drawTimer);
          const stream=canvas.captureStream(15);
          Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async()=>stream}});
        }''')
    page.add_script_tag(content=(SITE/'core.js').read_text())
    page.add_script_tag(content=(SITE/'foreground.js').read_text())
    page.add_script_tag(content=(SITE/'hand_ml.js').read_text())
    if hand_mock:
        page.evaluate("""() => {
          // Fake MediaPipe inference results only. Not a test of the actual model.
          const original = AnimateHandML.createHandDetector;
          AnimateHandML.createHandDetector = () => original({ minIntervalMs:95, loader:async()=>({
            detectForVideo:()=>{
              const landmarks = Array.from({length:21},()=>({x:.5,y:.5}));
              landmarks[8]={x:window.blobX,y:.5};
              return {landmarks:window.twoHands?[landmarks,landmarks]:[landmarks]};
            },close:()=>{}
          })});
        }""")
    if hand_hang:
        page.evaluate('''() => {
          const original = AnimateHandML.createHandDetector;
          AnimateHandML.createHandDetector = () => original({
            loader: () => new Promise(() => {}), loadTimeoutMs: 45
          });
        }''')
    page.add_script_tag(content=(SITE/'app.js').read_text())
    return browser, context, page, errors

def enrol(page, mode='play'):
    page.select_option('#role', label='Educator')
    page.check('#adult')
    page.check('#consent')
    page.click('#enter')
    page.click(f'[data-mode="{mode}"]')

def record(page):
    return page.evaluate("JSON.parse(localStorage.getItem('animate-validation-v07'))")

# Hand-ML integration is tested using fake landmark results, NOT actual model inference.
with sync_playwright() as p:
    b,c,pg,errs=prepare(p,camera=True,hand_mock=True)
    enrol(pg)
    pg.select_option('#detector','hand')
    pg.click('#camera')
    pg.wait_for_function("document.querySelector('#inputLabel').textContent === 'Live camera'")
    check('hand ML mode boots with injected local model shim',
          pg.locator('#start').is_enabled() and pg.evaluate('hand.ready'))
    pg.click('#start')
    pg.evaluate('window.twoHands=true')
    pg.wait_for_timeout(550)
    check('two-hand ambiguity never counts as a zone hit',pg.locator('#score').inner_text()=='0 / 3')
    pg.evaluate('window.twoHands=false')
    for index,x in enumerate([.5,.17,.83],start=1):
        pg.evaluate('(x)=>window.blobX=x',x)
        pg.wait_for_function('(n)=>document.querySelector("#score").textContent.startsWith(n+" /")',arg=index,timeout=6000)
    check('synthetic fingertip results can complete 3-zone flow',pg.locator('#score').inner_text()=='3 / 3')
    rec=record(pg)
    check('hand-ML starts and completions retain model provenance',
          any(e['type']=='start' and e.get('detector')=='hand' and e.get('model')=='mediapipe-hand-landmarker-float16-v1' for e in rec['events']) and
          any(e['type']=='complete' and e.get('detector')=='hand' and e.get('model')=='mediapipe-hand-landmarker-float16-v1' for e in rec['events']))
    check('no JS runtime errors with fake hand landmarks',not errs,str(errs))
    c.close();b.close()

with sync_playwright() as p:
    b,c,pg,errs=prepare(p,camera=True)
    enrol(pg)
    pg.select_option('#detector','hand');pg.click('#camera')
    pg.wait_for_function("document.querySelector('#status').textContent.includes('could not initialise')",timeout=8000)
    check('missing local ML model fails closed without completed task',
          pg.locator('#start').is_disabled() and pg.locator('#inputLabel').inner_text()=='Not started' and
          not any(e['type']=='complete' for e in record(pg)['events']))
    check('missing ML asset does not crash app',not errs,str(errs))
    c.close();b.close()

# A nonresponsive WASM/model load must fail closed, not strand a live camera.
with sync_playwright() as p:
    b,c,pg,errs=prepare(p,camera=True,hand_hang=True)
    enrol(pg)
    pg.select_option('#detector','hand');pg.click('#camera')
    pg.wait_for_function("document.querySelector('#status').textContent.includes('could not initialise')",timeout=5000)
    check('hung ML loading is bounded and the camera is released',
          pg.locator('#start').is_disabled() and pg.locator('#inputLabel').inner_text() == 'Not started'
          and pg.evaluate('hand.ready') is False)
    check('ML model hang does not create completion evidence',
          not any(e['type']=='complete' for e in record(pg)['events']))
    check('ML model hang causes no unhandled browser errors',not errs,str(errs))
    c.close();b.close()

# A camera interruption must not retain a previously valid colour calibration.
with sync_playwright() as p:
    b,c,pg,errs=prepare(p,camera=True)
    enrol(pg)
    pg.click('#camera')
    pg.wait_for_function("document.querySelector('#inputLabel').textContent === 'Live camera'")
    pg.wait_for_function('frameNumber > 3')
    pg.evaluate('calibrateAt(.5,.5)')
    check('control camera scene can calibrate before interruption',
          pg.evaluate('!!reference') and pg.locator('#start').is_enabled())
    pg.evaluate("markInterrupted('Synthetic interruption')")
    check('interruption invalidates colour reference and disables scoring',
          pg.evaluate('reference === null && calibrating && interrupted') and pg.locator('#start').is_disabled())
    pg.evaluate('startChallenge()')
    check('interrupted session cannot launch a challenge',pg.evaluate('run === null'))
    check('colour interruption regression causes no browser errors',not errs,str(errs))
    c.close();b.close()

bad=[name for name, ok in checks if not ok]
print(f"\n{len(checks)-len(bad)}/{len(checks)} offline browser checks passed",flush=True)
if bad: sys.exit(1)
