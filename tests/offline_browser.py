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

def prepare(p, camera=False, benchmark=False, hand_mock=False, debug=False):
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
    if debug:
        page.evaluate("""() => { const get=URLSearchParams.prototype.get;
          URLSearchParams.prototype.get=function(k){return k==='debug'?'1':get.call(this,k);}; }""")
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

with sync_playwright() as p:
    b, c, pg, errs = prepare(p)
    check('cannot enrol without consent and role', pg.locator('#intro').is_visible() and
          pg.locator('#enter').click() is None and pg.locator('#introerr').inner_text().startswith('Choose'))
    enrol(pg)
    check('pseudonymous enrollment has schema/build and coarse device',
          record(pg)['version']==5 and record(pg)['build']=='0.7.0' and record(pg)['device']=='Other')
    pg.click('#sample'); pg.click('#start')
    for n in ['Middle','Left','Right']: pg.click('#tap'+n)
    check('touch-only completes three-zone task',pg.locator('#score').inner_text()=='3 / 3')
    check('target text and aria progress report completion',
          pg.locator('#targetText').inner_text()=='Target: none' and
          pg.locator('#progressBar').get_attribute('aria-valuenow')=='3')
    pg.fill('#problem','I currently use paper fractions.');pg.click('#saveProblem')
    check('qualitative question saves without any price',
          any(e['type']=='problem_response' for e in record(pg)['events']) and
          pg.locator('#offer').count()==0)
    check('retina canvas enlarged at 3x pixel ratio',
          pg.locator('#view').evaluate('c=>c.width>c.getBoundingClientRect().width*2.5'))
    with pg.expect_download() as dl: pg.click('#export')
    path = dl.value.path()
    with open(path) as f: exported=json.load(f)
    check('JSON export has exportedAt and same record ID',
          bool(exported.get('exportedAt')) and exported['id']==record(pg)['id'])
    pg.locator('summary:has-text("Researcher")').click()
    pg.locator('#aggregate').set_input_files(path)
    pg.wait_for_function("document.querySelector('#aggregateOutput').textContent.trim().startsWith('{')")
    out=json.loads(pg.locator('#aggregateOutput').inner_text())
    check('touch fallback excluded from camera successes',out['provisional']['cameraTesters']==0 and out['verified']['first']==0)
    ledger=f"id,sessionDate,device\n{exported['id']},{exported['createdDay']},{exported['device']}\n"
    pg.locator('#ledger').set_input_files({'name':'ledger.csv','mimeType':'text/csv','buffer':ledger.encode()})
    pg.wait_for_function("document.querySelector('#aggregateOutput').textContent.includes('\"ledgerMatches\": 1')")
    out=json.loads(pg.locator('#aggregateOutput').inner_text())
    check('private in-memory ledger joins by ID/day/device',out['ledgerMatches']==1)
    bad=b'{"version":5,"build":"0.7.0","id":"badbadbad","events":['+b'null,'*500000+b'null]}'
    pg.locator('#aggregate').set_input_files({'name':'malformed.json','mimeType':'application/json','buffer':bad})
    pg.wait_for_function("document.querySelector('#aggregateOutput').textContent.includes('\"unreadableFiles\": 1')")
    out=json.loads(pg.locator('#aggregateOutput').inner_text())
    check('oversized/malformed JSON rejected without UI failure',out['unreadableFiles']==1)
    check('no JS runtime errors in touch/import/export',not errs,str(errs))
    c.close();b.close()

    b,c,pg,errs=prepare(p,camera=True)
    enrol(pg)
    pg.click('#camera');pg.wait_for_timeout(500)
    check('mock video stream starts and has dimensions',pg.locator('#inputLabel').inner_text()=='Live camera' and
          pg.evaluate('document.querySelector("#video").videoWidth')==320)
    pg.locator('#view').click(position={'x':145,'y':120})
    check('calibration accepts saturated object',pg.locator('#start').is_enabled())
    pg.click('#start')
    # On CI hosts, headless captureStream frames may be delayed under load.
    # Assert each genuine scored transition, not elapsed wall time, and fail if
    # the existing detector never earns its dwell threshold within the bound.
    for score, x in enumerate([.5,.17,.83], start=1):
        pg.evaluate('(x)=>window.blobX=x', x)
        pg.wait_for_function(
            '(n)=>document.querySelector("#score").textContent.startsWith(n+" /")',
            arg=score, timeout=6000
        )
    check('synthetic canvas camera completes correct sequence', pg.locator('#score').inner_text()=='3 / 3',
          pg.locator('#score').inner_text())
    rec=record(pg)
    check('synthetic camera success has linked run IDs',
          any(e['type']=='complete' and e['input']=='camera' and e.get('runId') for e in rec['events']))
    check('no JS runtime errors in mocked camera',not errs,str(errs))
    c.close();b.close()

    b,c,pg,errs=prepare(p,camera=True)
    enrol(pg)
    pg.click('#camera');pg.wait_for_timeout(500);pg.locator('#view').click(position={'x':145,'y':120})
    pg.evaluate('window.blobX=.83');pg.wait_for_timeout(250)
    pg.click('#start');pg.evaluate('window.pauseFrames()')
    pg.wait_for_timeout(1950)
    rec=record(pg)
    check('stale simulated camera feed fails closed',
          'stale' in pg.locator('#status').inner_text().lower() and
          pg.locator('#score').inner_text()=='0 / 3', pg.locator('#status').inner_text())
    check('interrupted challenge cannot become a camera completion',
          not any(e['type']=='complete' for e in rec['events']))
    c.close();b.close()

    b,c,pg,errs=prepare(p,camera=True,benchmark=True)
    enrol(pg)
    check('benchmark interface is available only in explicit query mode', pg.locator('#benchmarkPanel').is_visible())
    pg.click('#camera'); pg.wait_for_timeout(500)
    pg.locator('#view').click(position={'x':145,'y':120})
    pg.select_option('#benchColour','blue')
    pg.select_option('#benchExpected','absent')
    pg.click('#benchStart')
    pg.wait_for_timeout(200)
    check('benchmark samples only actual fresh video frames',
          'Fresh frames:' in pg.locator('#benchStatus').inner_text() and
          pg.locator('#benchCancel').is_enabled())
    pg.click('#benchCancel')
    check('cancelled benchmark does not create evidence',
          not any(e['type']=='benchmark_sample' for e in record(pg)['events']))
    pg.click('#benchStart')
    pg.evaluate('''() => { // Test-only acceleration of the result collection, not 600 real frames.
      probe.cancel();
      probe.start({colour:'blue',light:'normal',background:'plain',expected:'present'});
      for(let i=0;i<600;i++)probe.add({x:.5,y:.5},0.2);
      finishProbe();
    }''')
    check('completed manual benchmark is exported as tagged diagnostic, not purchase evidence',
          any(e['type']=='benchmark_sample' and e['sample']['frames']==600 for e in record(pg)['events']) and
          pg.locator('#benchResults').inner_text().count('"frames": 600')==1)
    check('benchmark test has no JavaScript errors', not errs, str(errs))
    c.close(); b.close()

    b,c,pg,errs=prepare(p,camera=True)
    enrol(pg)
    pg.evaluate('''() => {
      HTMLMediaElement.prototype.play = () => new Promise(resolve => { window.__releasePlay = resolve; });
      startCamera();
    }''')
    pg.wait_for_function("typeof window.__releasePlay === 'function'")
    pg.evaluate('''() => { stopCamera(); window.__releasePlay(); }''')
    pg.wait_for_timeout(100)
    check('async camera play cannot resurrect a stopped media stream',
          pg.evaluate("() => !stream && !input && document.querySelector('#inputLabel').textContent === 'Not started'") and
          not any(e['type']=='camera_ready' for e in record(pg)['events']))
    check('cancelled camera start has no JavaScript errors', not errs, str(errs))
    c.close();b.close()

    # A wake-lock grant can arrive after a user has stopped or dismissed the camera.
    # Never retain such a sentinel: otherwise mobile battery life is affected.
    b,c,pg,errs=prepare(p,camera=True)
    enrol(pg)
    pg.evaluate('''() => {
      window.__lateWakeReleased = false;
      Object.defineProperty(navigator, 'wakeLock', {configurable:true,value:{
        request:()=>new Promise(resolve=>{window.__grantWakeLock=resolve;})
      }});
    }''')
    pg.click('#camera')
    pg.wait_for_function("typeof window.__grantWakeLock === 'function'", timeout=5000)
    pg.click('#stop')
    pg.evaluate('''() => window.__grantWakeLock({
      release:()=>{window.__lateWakeReleased=true;return Promise.resolve();}
    })''')
    pg.wait_for_function("window.__lateWakeReleased === true", timeout=5000)
    check('a late wake-lock grant is released after camera stop',
          pg.evaluate("window.__lateWakeReleased && wakeLock === null && stream === null"))
    check('late wake-lock cleanup has no JavaScript runtime errors',not errs,str(errs))
    c.close();b.close()

    b,c,pg,errs=prepare(p,camera=True)
    enrol(pg)
    pg.select_option('#detector','foreground')
    pg.evaluate('window.showBlob=false')
    pg.click('#camera'); pg.wait_for_timeout(400)
    check('foreground method exposes empty-scene capture, not colour calibration',
          pg.locator('#captureBackground').is_visible() and pg.locator('#captureBackground').is_enabled() and
          pg.locator('#start').is_disabled())
    pg.click('#captureBackground')
    pg.wait_for_function('foreground.ready',timeout=5000)
    check('12 fresh frames required before foreground challenge unlocks',
          pg.locator('#start').is_enabled() and pg.evaluate('foreground.metrics().framesCaptured')==12)
    pg.evaluate('window.showBlob=true')
    pg.click('#start')
    for x in [.5,.17,.83]:
        pg.evaluate('(x)=>window.blobX=x',x)
        pg.wait_for_timeout(700)
    check('foreground camera completes synthetic zone challenge',
          pg.locator('#score').inner_text()=='3 / 3',pg.locator('#score').inner_text())
    rec=record(pg)
    check('foreground completion evidence is labelled and paired',
          any(e['type']=='start' and e.get('detector')=='foreground' for e in rec['events']) and
          any(e['type']=='complete' and e.get('detector')=='foreground' for e in rec['events']))
    metrics=pg.evaluate("""() => AnimateCore.summarize([{
      ...JSON.parse(localStorage.getItem('animate-validation-v07')),
      exportedAt: new Date().toISOString()
    }])""")
    check('aggregator attributes camera result to foreground only',
          metrics['byDetector']['foreground']['provisionalCompleted']==1 and
          metrics['byDetector']['colour']['provisionalCompleted']==0)
    check('no browser errors in foreground lifecycle',not errs,str(errs))
    c.close();b.close()

    b,c,pg,errs=prepare(p,camera=True)
    enrol(pg);pg.select_option('#detector','foreground');pg.evaluate('window.showBlob=false')
    pg.click('#camera');pg.wait_for_timeout(400)
    pg.click('#captureBackground');pg.wait_for_function('foreground.ready',timeout=5000)
    pg.evaluate('window.showBlob=true');pg.click('#start')
    pg.evaluate('window.pauseFrames()');pg.wait_for_timeout(1950)
    check('stale foreground video is interrupted and challenge cannot finish',
          not pg.evaluate('foreground.ready') and pg.locator('#score').inner_text()=='0 / 3' and
          not any(e['type']=='complete' for e in record(pg)['events']))
    check('no errors after frozen foreground camera',not errs,str(errs))
    c.close();b.close()


    b,c,pg,errs=prepare(p,camera=True,debug=True)
    enrol(pg)
    pg.locator('#dbgbox summary').click()
    pg.fill('#packetCommit','a'*40)
    pg.check('#packetPhysical')
    pg.check('#packetRegistered')
    pg.click('#packetBegin')
    check('operator evidence packet requires physical and preregistration self-claims',
          'Packet configured' in pg.locator('#packetStatus').inner_text() and
          pg.locator('#packetCommit').is_disabled())
    pg.click('#deviceBenchStart')
    check('debug device benchmark cannot start without live camera',
          'Measurement blocked:' in pg.locator('#deviceBenchStatus').inner_text() and
          json.loads(pg.locator('#deviceBenchReport').inner_text())['status']=='not_started')
    pg.click('#camera');pg.wait_for_timeout(550)
    pg.click('#deviceBenchStart')
    check('camera performance evidence is blocked before calibration',
          'Measurement blocked:' in pg.locator('#deviceBenchStatus').inner_text() and
          json.loads(pg.locator('#deviceBenchReport').inner_text())['status']=='not_started')
    pg.locator('#view').click(position={'x':145,'y':120})
    pg.click('#deviceBenchStart')
    pg.click('#start')
    check('participant challenge cannot begin during an active performance sample',
          'Finish the 60-second performance sample' in pg.locator('#status').inner_text() and
          json.loads(pg.locator('#deviceBenchReport').inner_text())['status']=='running' and
          not any(e['type']=='start' for e in record(pg)['events']))
    check('packet cannot be discarded while a performance measurement is running',
          pg.locator('#packetReset').is_disabled())
    pg.click('#zoneControlStart')
    check('zone controls cannot overlap an active camera performance measurement',
          'Control blocked: finish the 60-second' in pg.locator('#zoneControlStatus').inner_text() and
          json.loads(pg.locator('#zoneControlReport').inner_text())['status']=='not_started')
    pg.wait_for_timeout(1400)
    pg.click('#deviceBenchFinish')
    report=json.loads(pg.locator('#deviceBenchReport').inner_text())
    check('debug camera measures actual processed frames but marks early stop incomplete',
          report['status']=='manual' and not report['complete'] and
          report['observedMs'] > 1000 and report['sampleWindows'] >= 1 and
          report['inferenceMs']['samples'] > 0 and report['inferredFrames'] > 0)
    check('manual early finish cannot satisfy continuous camera coverage requirements',
          report['coverage']['sufficient'] is False and
          report['complete'] is False and
          report['recognitionAccuracyMeasured'] is False and
          report['commercialDemandMeasured'] is False)
    check('numeric device sample contains no participant IDs or raw image data',
          not any(k in report for k in ['userAgent','participantId','id','frameData','lastPosition']) and
          all('ANIMATE_LOCAL_DEVICE_PERFORMANCE_SAMPLE' not in json.dumps(e)
              for e in record(pg)['events']))
    pg.click('#deviceBenchStart')
    pg.click('[data-mode="create"]')
    mode_interrupt=json.loads(pg.locator('#deviceBenchReport').inner_text())
    check('changing mode interrupts the sample rather than preserving false completeness',
          mode_interrupt['status']=='interrupted' and not mode_interrupt['complete'] and
          json.loads(pg.locator('#packetSummary').inner_text())['performanceTrials']==2)
    pg.click('#deviceBenchStart')
    pg.click('#calibrate')
    calibration_interrupt=json.loads(pg.locator('#deviceBenchReport').inner_text())
    check('recalibrating interrupts active sample and preserves failure denominator',
          calibration_interrupt['status']=='interrupted' and
          json.loads(pg.locator('#packetSummary').inner_text())['performanceTrials']==3 and
          pg.locator('#start').is_disabled())
    pg.locator('#view').click(position={'x':145,'y':120})
    pg.select_option('#zoneControlExpected','absent')
    pg.click('#zoneControlStart')
    pg.click('#deviceBenchStart')
    check('camera performance measurements cannot overlap active zone controls',
          'Measurement blocked: finish the 10-second' in pg.locator('#deviceBenchStatus').inner_text() and
          json.loads(pg.locator('#deviceBenchReport').inner_text())['status']=='interrupted')
    pg.wait_for_timeout(450)
    pg.click('#zoneControlFinish')
    zone_report=json.loads(pg.locator('#zoneControlReport').inner_text())
    check('debug zone control samples fresh camera detections and marks early stop incomplete',
          zone_report['expectedCondition']=='absent' and
          zone_report['status']=='manual' and
          not zone_report['complete'] and
          zone_report['analysedFrames']>0)
    check('zone negative-control is a self-labelled proxy and never changes participant research events',
          zone_report['independentlyVerified'] is False and
          zone_report['userDemandMeasured'] is False and
          not any('ZONE_CONTROL' in json.dumps(e) for e in record(pg)['events']))
    with pg.expect_download() as packet_download:
        pg.click('#packetExport')
    with open(packet_download.value.path()) as fh:
        evidence_packet=json.load(fh)
    check('operator-only iPhone packet download contains only numeric reports and self-declarations',
          evidence_packet['schema']=='ANIMATE_IPHONE_OPERATOR_PACKET_V1' and
          evidence_packet['sourceCommit']=='a'*40 and
          evidence_packet['detector']=='colour' and
          len(evidence_packet['performanceTrials'])==3 and
          len(evidence_packet['zoneTrials'])==1 and
          [r['report']['status'] for r in evidence_packet['performanceTrials']] ==
              ['manual','interrupted','interrupted'] and
          evidence_packet['zoneTrials'][0]['report']['status']=='manual' and
          'userAgent' not in json.dumps(evidence_packet) and
          'participantId' not in json.dumps(evidence_packet))
    check('packet is separate from existing participant research record',
          not any('ANIMATE_IPHONE_OPERATOR_PACKET_V1' in json.dumps(e)
                  for e in record(pg)['events']))
    pg.evaluate("packetRecorder.invalidate(); refreshPacketSummary()")
    check('rejected trial invalidates entire evidence packet and blocks selective export',
          pg.locator('#packetExport').is_disabled() and
          pg.locator('#packetCopy').is_disabled() and
          json.loads(pg.locator('#packetSummary').inner_text())['integrityOk'] is False)
    pg.once('dialog',lambda dialog: dialog.accept())
    pg.click('#packetReset')
    check('reset clears blocked operator packet from memory',
          pg.locator('#packetExport').is_disabled() and
          json.loads(pg.locator('#packetSummary').inner_text())['integrityOk'] is True)
    check('debug device sampling and negative controls have no JavaScript errors',not errs,str(errs))
    c.close();b.close()


    # When foreground background capture is restarted mid-performance sample,
    # the attempt must be interrupted rather than silently included as clean data.
    b,c,pg,errs=prepare(p,camera=True,debug=True)
    enrol(pg)
    pg.locator('#dbgbox summary').click()
    pg.select_option('#detector','foreground')
    pg.click('#camera');pg.wait_for_timeout(400)
    pg.click('#captureBackground')
    pg.wait_for_function('foreground.ready',timeout=5000)
    pg.click('#deviceBenchStart')
    check('foreground camera can start performance measurement after background capture',
          json.loads(pg.locator('#deviceBenchReport').inner_text())['status']=='running')
    pg.click('#captureBackground')
    check('foreground recapture interrupts the live performance attempt',
          json.loads(pg.locator('#deviceBenchReport').inner_text())['status']=='interrupted' and
          not json.loads(pg.locator('#deviceBenchReport').inner_text())['complete'])
    check('foreground scene-recapture isolation does not cause browser errors',not errs,str(errs))
    c.close();b.close()

    # An explicitly labelled recognition benchmark must not overlap the
    # operator-only 60-second performance preflight.
    b,c,pg,errs=prepare(p,camera=True,benchmark=True,debug=True)
    enrol(pg)
    pg.locator('#dbgbox summary').click()
    pg.click('#camera');pg.wait_for_timeout(550)
    pg.locator('#view').click(position={'x':145,'y':120})
    pg.click('#deviceBenchStart')
    pg.click('#benchStart')
    check('recognition benchmark blocked during a 60-second performance sample',
          'Finish the active control or performance measurement' in
              pg.locator('#benchStatus').inner_text() and
          pg.locator('#benchCancel').is_disabled() and
          json.loads(pg.locator('#deviceBenchReport').inner_text())['status']=='running')
    pg.click('#deviceBenchFinish')
    pg.click('#benchStart')
    check('recognition benchmark can start only after performance sample ends',
          pg.locator('#benchCancel').is_enabled() and
          json.loads(pg.locator('#deviceBenchReport').inner_text())['status']=='manual')
    pg.click('#benchCancel')
    check('recognition benchmark isolation produces no JavaScript errors',not errs,str(errs))
    c.close();b.close()


    # iOS-style backgrounding must cancel camera requests even while the
    # permission promise is unresolved, and must not disturb a newer attempt.
    b,c,pg,errs=prepare(p,camera=True)
    enrol(pg)
    pg.evaluate("""() => {
      window.pendingMedia = [];
      navigator.mediaDevices.getUserMedia = () => new Promise(resolve => {
        const track = {readyState:'live',stop(){this.readyState='ended';}};
        const media = {getTracks:()=>[track], getVideoTracks:()=>[track]};
        window.pendingMedia.push({release:()=>resolve(media),track});
      });
    }""")
    pg.click('#camera')
    check('pending camera permission has no acquired media stream yet',
          pg.evaluate('startInProgress && stream === null && pendingMedia.length === 1'))
    pg.evaluate("""() => {
      Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
      document.dispatchEvent(new Event('visibilitychange'));
    }""")
    check('backgrounding cancels pending permission request without waiting for a stream',
          pg.evaluate('!startInProgress && stream === null && !document.querySelector("#camera").disabled'))
    pg.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>false})")
    pg.click('#camera')
    pg.evaluate('pendingMedia[0].release()')
    pg.wait_for_function('pendingMedia[0].track.readyState === "ended"')
    check('late permission result stops its track without unlocking newer camera request',
          pg.evaluate('pendingMedia.length === 2 && startInProgress && stream === null && document.querySelector("#camera").disabled'))
    pg.evaluate("window.dispatchEvent(new Event('pagehide'))")
    pg.evaluate('pendingMedia[1].release()')
    pg.wait_for_function('pendingMedia[1].track.readyState === "ended"')
    check('pagehide rejects second pending permission and restores camera controls',
          pg.evaluate('!startInProgress && stream === null && !document.querySelector("#camera").disabled'))
    pg.click('#camera')
    pg.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>true})")
    pg.evaluate('pendingMedia[2].release()')
    pg.wait_for_function('pendingMedia[2].track.readyState === "ended"')
    check('resolved permission fails closed if page became hidden without a visibility event',
          pg.evaluate('!startInProgress && stream === null && !document.querySelector("#camera").disabled'))
    check('pending camera permission lifecycle has no browser exceptions',not errs,str(errs))
    c.close();b.close()

    # The second async boundary is video.play(): Safari can background a tab
    # after permission succeeds but before playback resolves.
    b,c,pg,errs=prepare(p,camera=True)
    enrol(pg)
    pg.evaluate("""() => {
      const video = document.querySelector('#video');
      video.play = () => new Promise(resolve => { window.resumeVideoPlay=resolve; });
    }""")
    pg.click('#camera')
    pg.wait_for_function('typeof window.resumeVideoPlay === "function"')
    check('camera is acquired but video playback remains pending',
          pg.evaluate('startInProgress && stream !== null && input === null'))
    pg.evaluate("""() => {
      Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
      document.dispatchEvent(new Event('visibilitychange'));
    }""")
    pg.evaluate('window.resumeVideoPlay()')
    check('backgrounded pending video playback does not resurrect a stopped camera',
          pg.evaluate('''() => !startInProgress && stream === null && input === null &&
            document.querySelector("#video").srcObject === null &&
            !document.querySelector("#camera").disabled'''))
    check('delayed video-play cancellation has no browser exceptions',not errs,str(errs))
    c.close();b.close()


    # Regression for a strict terminal race: a performance trial already has
    # adequate 59-second coverage, then its camera track is ended just before
    # the 60th window. It must NOT be exported as a completed/timed sample.
    # The synthetic fixtures are an adversarial logic test, not measured FPS.
    b,c,pg,errs=prepare(p,camera=True,debug=True)
    enrol(pg)
    pg.locator('#dbgbox summary').click()
    pg.fill('#packetCommit','b'*40)
    pg.check('#packetPhysical')
    pg.check('#packetRegistered')
    pg.click('#packetBegin')
    pg.click('#camera')
    pg.wait_for_timeout(550)
    pg.locator('#view').click(position={'x':145,'y':120})
    pg.click('#deviceBenchStart')
    check('camera sample is initially active before terminal media-health race',
          json.loads(pg.locator('#deviceBenchReport').inner_text())['status']=='running')
    pg.evaluate("""() => {
      const now=performance.now();
      const start=now-60000;
      deviceBench.begin(start,'colour');
      for(let i=1;i<60;i++) {
        deviceBench.noteLatency(8);
        deviceBench.noteWindow(start+i*1000,18,60);
      }
      // Fake an ended track with no event delivery. A naive timer-first loop
      // would accept this dense fixture as a successful 60-second sample.
      const track=stream.getVideoTracks()[0];
      Object.defineProperty(track,'readyState',{
        configurable:true,get:()=> 'ended'
      });
      fpsAt=performance.now()-1500;
    }""")
    pg.wait_for_function("""() => {
      return JSON.parse(document.querySelector('#deviceBenchReport').textContent).status !== 'running';
    }""",timeout=5000)
    race=json.loads(pg.locator('#deviceBenchReport').inner_text())
    check('ended camera track preempts the apparently complete final performance window',
          race['status']=='interrupted' and race['complete'] is False and
          race['interruptions']>=1 and race['observedMs']==60000 and
          race['sampleWindows']==59)
    packet=pg.evaluate('packetRecorder.packet()')
    check('operator evidence packet retains failed terminal camera attempt as incomplete',
          len(packet['performanceTrials'])==1 and
          packet['performanceTrials'][0]['report']['status']=='interrupted' and
          packet['performanceTrials'][0]['report']['complete'] is False)
    check('terminal camera failure regression has no JavaScript exceptions',not errs,str(errs))
    c.close();b.close()

bad=[name for name, ok in checks if not ok]
print(f"\n{len(checks)-len(bad)}/{len(checks)} baseline offline browser checks passed",flush=True)
sys.exit(1 if bad else 0)
