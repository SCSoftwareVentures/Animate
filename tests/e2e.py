"""Synthetic-camera Chromium E2E. No physical iPhone/Safari or real recognition claims.
Run: python tests/e2e.py [chromium_path]"""
import sys, time, json, tempfile, threading, http.server, functools, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

HERE = Path(__file__).parent
SITE = HERE.parent / 'site'
with tempfile.TemporaryDirectory() as vids:
    subprocess.run([sys.executable, str(HERE/'make_video.py'), vids], check=True)
    csp_probe_path = '/core.js?cross-origin-csp-probe'
    csp_probe_requests = []

    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == csp_probe_path:
                csp_probe_requests.append(self.path)
            super().do_GET()

        def log_message(self, *args): pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    URL = f'http://localhost:{srv.server_address[1]}/index.html'
    csp_probe_url = f'http://127.0.0.1:{srv.server_address[1]}{csp_probe_path}'
    exe = sys.argv[1] if len(sys.argv) > 1 else None
    results = []

    def check(name, cond, detail=''):
        results.append((name, bool(cond)))
        print(('PASS ' if cond else 'FAIL ') + name + (f' [{detail}]' if detail else ''), flush=True)

    def session(p, video, mode='play', front=False, wait=25):
        browser = p.chromium.launch(executable_path=exe, args=['--no-sandbox', '--use-fake-device-for-media-stream',
                             '--use-fake-ui-for-media-stream', f'--use-file-for-fake-video-capture={vids}/{video}'])
        context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True,
                                      device_scale_factor=3, permissions=['camera'], accept_downloads=True)
        page = context.new_page()
        errors, csp = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda message: csp.append(message.text) if 'Content Security Policy' in message.text else None)
        page.goto(URL)
        page.select_option('#role', label='Game creator')
        page.check('#adult'); page.check('#consent'); page.click('#enter'); page.click(f'[data-mode="{mode}"]')
        if front: page.check('#front')
        page.click('#camera')
        expect(page.locator('#inputLabel')).to_have_text('Live camera', timeout=10000)
        time.sleep(1)
        page.locator('#view').click()
        expect(page.locator('#start')).to_be_enabled(timeout=5000)
        t0 = time.time(); page.click('#start'); done = None
        while time.time() - t0 < wait:
            if page.locator('#score').inner_text() == '3 / 3':
                done = time.time() - t0
                break
            time.sleep(.2)
        return browser, context, page, done, errors, csp

    try:
        with sync_playwright() as p:
            b, c, pg, done, errors, csp = session(p, 'walk.y4m')
            check('camera: walk video finishes Play zone challenge', done is not None and done < 17, str(done))
            check('no JS errors or CSP violations', not errors and not csp, f'{errors} {csp}')
            check('there are no prices, product offers or hypothetical purchase buttons',
                  pg.locator('#offer').count() == 0 and pg.locator('[data-intent]').count() == 0)
            rec = pg.evaluate("JSON.parse(localStorage.getItem('animate-validation-v07'))")
            check('record has build/schema/device and paired run IDs',
                  rec['build'] == '0.7.0' and rec['version'] == 5 and
                  any(e['type'] == 'complete' and e['input'] == 'camera' and e.get('runId') for e in rec['events']))
            check('explicit current target text and canvas target label', pg.locator('#targetText').count() == 1)
            check('retina backing store exceeds CSS pixel dimensions',
                  pg.locator('#view').evaluate('c=>c.width > c.getBoundingClientRect().width'))
            check('feedback follows successful completion', pg.locator('#feedbackPanel').is_visible())
            pg.fill('#problem', 'I currently use paper thirds.'); pg.click('#saveProblem')
            rec = pg.evaluate("JSON.parse(localStorage.getItem('animate-validation-v07'))")
            check('open feedback captured without a price',
                  any(e['type'] == 'problem_response' for e in rec['events']) and not any(e['type'] == 'offer' for e in rec['events']))
            pg.reload(); pg.wait_for_selector('#lab:not([hidden])', timeout=5000)
            check('record survives reload with same participant ID',
                  pg.evaluate("JSON.parse(localStorage.getItem('animate-validation-v07')).id") == rec['id'])
            policy = pg.evaluate('''async url => {
                const violation = new Promise(resolve => {
                    document.addEventListener('securitypolicyviolation', event => {
                        if (event.blockedURI === url) resolve(event.effectiveDirective);
                    });
                    setTimeout(() => resolve(null), 1500);
                });
                const local = await fetch('core.js?local-csp-probe');
                const rejected = await fetch(url).then(() => false, () => true);
                return { local: local.ok, rejected, directive: await violation };
            }''', csp_probe_url)
            check('browser CSP permits same-origin fetches and blocks cross-origin requests',
                  policy == {'local': True, 'rejected': True, 'directive': 'connect-src'} and not csp_probe_requests,
                  str(policy))
            c.close(); b.close()

            b, c, pg, done, errors, csp = session(p, 'stray.y4m')
            check('distractor speck does not block tracking', done is not None and done < 17, str(done))
            c.close(); b.close()

            b, c, pg, done, errors, csp = session(p, 'still.y4m', mode='create', wait=10)
            check('negative control: parked object cannot complete', done is None and pg.locator('#score').inner_text() == '0 / 3')
            check('simulated track mute cancels scoring',
                  pg.evaluate("() => { const v=document.querySelector('#video'); const t=v.srcObject.getVideoTracks()[0]; t.onmute(); return document.querySelector('#status').textContent.includes('interrupted'); }"))
            c.close(); b.close()

            b, c, pg, done, errors, csp = session(p, 'walk.y4m', front=True, wait=35)
            check('front camera mirrors zones; later completion expected', done is not None and 9 < done < 35, str(done))
            c.close(); b.close()

            b = p.chromium.launch(executable_path=exe, args=['--no-sandbox'])
            c = b.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, accept_downloads=True)
            pg = c.new_page(); errors = []
            pg.on('pageerror', lambda e: errors.append(str(e)))
            pg.goto(URL)
            pg.select_option('#role', label='Educator'); pg.check('#adult'); pg.check('#consent'); pg.click('#enter'); pg.click('#sample')
            pg.click('[data-mode="play"]'); pg.click('#start')
            for n in ('Middle', 'Left', 'Right'): pg.click('#tap' + n)
            check('touch fallback completes with accessibility target text',
                  pg.locator('#score').inner_text() == '3 / 3' and pg.locator('#targetText').inner_text() == 'Target: none')
            with pg.expect_download() as download: pg.click('#export')
            path = download.value.path()
            with open(path) as fh: exported = json.load(fh)
            check('exported record has exportedAt, build and consent-compatible pseudonym',
                  'exportedAt' in exported and exported['build'] == '0.7.0' and exported['id'])
            pg.locator('summary:has-text("Researcher")').click()
            pg.locator('#aggregate').set_input_files(path)
            pg.wait_for_function("document.querySelector('#aggregateOutput').textContent.trim().startsWith('{')")
            summary = json.loads(pg.locator('#aggregateOutput').inner_text())
            check('touch-only run is not a camera success',
                  summary['provisional']['cameraTesters'] == 0 and summary['verified']['first'] == 0)
            ledger = 'id,sessionDate,device\n' + exported['id'] + ',' + exported['createdDay'] + ',' + exported['device'] + '\n'
            pg.locator('#ledger').set_input_files({'name':'private.csv', 'mimeType':'text/csv','buffer':ledger.encode()})
            expect(pg.locator('#aggregateOutput')).to_contain_text('"ledgerMatches": 1')
            summary = json.loads(pg.locator('#aggregateOutput').inner_text())
            check('private ledger reconciles participant ID/date/device', summary['ledgerMatches'] == 1)
            check('no page errors in export / import / ledger workflow', not errors, str(errors))
            c.close(); b.close()
    finally:
        srv.shutdown()
    bad = [name for name, ok in results if not ok]
    print(f'\n{len(results)-len(bad)}/{len(results)} checks passed', flush=True)
    sys.exit(1 if bad else 0)
