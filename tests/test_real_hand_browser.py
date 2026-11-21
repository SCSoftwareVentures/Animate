"""Exercise and time the real ANIMATE hand adapter in Chromium or WebKit.

Use a private staged site, exact local model/runtime bytes and an optional local
copy of Google's MediaPipe thumb_up.jpg. No asset downloads are made by this test.
The benchmark uses a repeated 160 × 120 canvas frame, without a physical camera.
"""
import argparse
from functools import partial
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
import threading

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))

FIXTURE_SHA256 = '5d673c081ab13b8a1812269ff57047066f9c33c07db5f4178089e8cb3fdc0291'
FIXTURE_BYTES = 80388
MODEL_PATH = '/vendor/mediapipe/models/hand_landmarker.task'
FIXTURE_PATH = '/__fixture.jpg'
DRIVER_PATH = '/__real_hand_probe.js'
CSP_PROBE_PATH = '/__cross_origin_csp_probe'
MISSING_MODEL_PATH = '/missing-model/'
TELEMETRY_URL = 'https://odml.pa.googleapis.com/v1/log'

DRIVER = b"""(() => {
  // This is the same inference interval and frame size used by the app.
  const detector = AnimateHandML.createHandDetector({minIntervalMs: 55});
  const violations = [];
  const blank = document.createElement('canvas');
  blank.width = 160;
  blank.height = 120;
  blank.getContext('2d').fillRect(0, 0, blank.width, blank.height);
  let frame = blank;
  let timestamp = 1;
  const step = 1000 / 15;
  document.addEventListener('securitypolicyviolation', event => {
    violations.push({directive: event.effectiveDirective, uri: event.blockedURI});
  });

  const isPoint = point => point?.source === 'index-fingertip' &&
    Number.isFinite(point.x) && point.x >= 0 && point.x <= 1 &&
    Number.isFinite(point.y) && point.y >= 0 && point.y <= 1;

  function timedDetection() {
    const began = performance.now();
    const point = detector.detect(frame, timestamp);
    const elapsedMs = performance.now() - began;
    timestamp += step;
    return {point: isPoint(point), empty: point === null, elapsedMs};
  }

  window.realHandProbe = {
    async prepare(useFixture) {
      if (useFixture) {
        const image = new Image();
        image.src = '__fixture.jpg';
        await image.decode();
        frame = document.createElement('canvas');
        frame.width = blank.width;
        frame.height = blank.height;
        frame.getContext('2d').drawImage(image, 0, 0, frame.width, frame.height);
      }
      updateDiagnostics();
      return JSON.parse(document.getElementById('diagnosticOutput').textContent).build;
    },
    async start() {
      const began = performance.now();
      const ready = await detector.start();
      timestamp = 1;
      return {ready, elapsedMs: performance.now() - began, metrics: detector.metrics()};
    },
    infer({frames, warmup}) {
      const before = detector.metrics().inferenceCount;
      const first = timedDetection();
      const throttled = detector.detect(frame, 20);
      const throttledCount = detector.metrics().inferenceCount;
      const warm = Array.from({length: warmup}, timedDetection);
      const steady = Array.from({length: frames}, timedDetection);
      const measured = [first, ...warm, ...steady];
      return {firstMs: first.elapsedMs, steadyMs: steady.map(f => f.elapsedMs),
        points: measured.filter(f => f.point).length, blanks: measured.filter(f => f.empty).length,
        throttled: throttled?.skipped === true && throttledCount === before + 1,
        actualCalls: detector.metrics().inferenceCount - before, errors: detector.metrics().errors};
    },
    stop() {
      detector.stop();
      return !detector.ready && detector.detect(frame, timestamp) === null;
    },
    async invalidTimestamp() {
      await detector.start();
      const blankRejected = detector.detect(blank, 1) === null;
      try {
        detector.detect(blank, 1);
      } catch (error) {
        return blankRejected && error.message === 'Invalid ML frame timestamp' &&
          !detector.ready && detector.detect(blank, 67) === null;
      } finally {
        detector.stop();
      }
      return false;
    },
    async missingModel() {
      try {
        await detector.start();
        return false;
      } catch {
        return !detector.ready && detector.detect(blank, 1) === null;
      } finally {
        detector.stop();
      }
    },
    async testCsp(url) {
      const violation = new Promise(resolve => {
        document.addEventListener('securitypolicyviolation', event => {
          if (event.blockedURI === url) resolve(event.effectiveDirective);
        });
        setTimeout(() => resolve(null), 2000);
      });
      const local = await fetch('core.js?real-hand-csp-probe');
      const blocked = await fetch(url).then(() => false, () => true);
      return {local: local.ok, blocked, directive: await violation};
    },
    violations: () => violations,
  };
})();
"""


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, files, **kwargs):
        self.files = files
        super().__init__(*args, **kwargs)

    def log_message(self, *_):
        pass

    def do_CONNECT(self):
        # Chromium's proxy uses this same loopback server, which never forwards.
        self.send_error(403)

    def do_GET(self):
        if not self.path.startswith('/') or self.path.startswith('//'):
            self.send_error(403)
            return
        path = self.path.partition('?')[0]
        if path == CSP_PROBE_PATH:
            self.server.csp_probe_received.set()
        if path.startswith(MISSING_MODEL_PATH):
            path = '/' + path.removeprefix(MISSING_MODEL_PATH)
            if path == MODEL_PATH:
                self.server.missing_model_requested.set()
                self.send_error(404)
                return
        asset = self.files.get(path)
        if asset is None:
            self.send_error(404)
            return
        body, mime = asset
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'public, max-age=3600')
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def site_files(site, fixture):
    from vendor_hand_model import PINNED_ASSET_SHA256, checked_bytes, validate_staged_site

    validate_staged_site(site)
    app = {'index.html': 'text/html; charset=UTF-8', 'styles.css': 'text/css',
           **dict.fromkeys(('app.js', 'core.js', 'foreground.js', 'hand_ml.js'), 'text/javascript')}
    files = {f'/{name}': ((site / name).read_bytes(), mime) for name, mime in app.items()}
    files['/'] = files['/index.html']
    files[DRIVER_PATH] = DRIVER, 'text/javascript'
    runtime_mime = {'.js': 'text/javascript', '.mjs': 'text/javascript', '.wasm': 'application/wasm',
                    '.task': 'application/octet-stream'}
    for relative, digest in PINNED_ASSET_SHA256.items():
        path = site / 'vendor' / 'mediapipe' / relative
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == digest, f'Staged asset digest changed: {relative}')
        files[f'/vendor/mediapipe/{relative}'] = data, runtime_mime[path.suffix]
    if fixture is not None:
        data = checked_bytes(fixture, FIXTURE_BYTES)
        require(hashlib.sha256(data).hexdigest() == FIXTURE_SHA256, 'Fixture SHA-256 does not match Google thumb_up.jpg')
        files[FIXTURE_PATH] = data, 'image/jpeg'
    return files


def renderer_memory(cdp):
    if cdp is None:
        return {'unavailable': 'WebKit does not expose Chromium CDP renderer process memory'}
    if sys.platform != 'linux':
        return {'unavailable': 'Linux /proc is required for renderer PSS'}
    processes = cdp.send('SystemInfo.getProcessInfo')['processInfo']
    pids = [int(process['id']) for process in processes if process['type'] == 'renderer']
    pss = []
    for pid in pids:
        try:
            lines = Path(f'/proc/{pid}/smaps_rollup').read_text().splitlines()
            pss.append(int(next(line.split()[1] for line in lines if line.startswith('Pss:'))))
        except (OSError, StopIteration, ValueError):
            return {'unavailable': 'Could not read PSS for every Chromium renderer', 'rendererCount': len(pids)}
    if not pss:
        return {'unavailable': 'Chromium reported zero renderer processes', 'rendererCount': 0}
    return {'rendererCount': len(pss), 'pssKiB': sum(pss)}


def open_probe(context, base_url, errors, requests, console):
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: requests.append(request.url))
    page.on('console', lambda message: console.append((message.type, message.text)))
    page.goto(f'{base_url}?debug=1')
    page.add_script_tag(url=base_url + DRIVER_PATH.lstrip('/'))
    return page


def check_inference(result, frames, expected_points):
    require(result['actualCalls'] == frames and result['errors'] == 0,
            f"Expected {frames} successful inference calls, got {result['actualCalls']} and {result['errors']} errors")
    require(result['throttled'], 'Throttled timestamp unexpectedly invoked inference')
    observed = result['points'] if expected_points else result['blanks']
    require(observed == frames, f'Expected {frames} valid frame results, got {observed}')


def run_trial(playwright, origin, csp_url, args, runtime_version, run_failure_checks):
    # The WebKit engine is a pre-device compatibility gate, not an iOS Safari surrogate.
    options = {'proxy': {'server': origin, 'bypass': '127.0.0.1,localhost'}}
    if args.chromium is not None:
        options['executable_path'] = args.chromium
    browser = getattr(playwright, args.browser).launch(**options)
    try:
        cdp = browser.new_browser_cdp_session() if args.browser == 'chromium' else None
        context = browser.new_context(service_workers='block')
        errors, requests, console = [], [], []
        page = open_probe(context, f'{origin}/', errors, requests, console)
        use_fixture = args.fixture is not None
        build = page.evaluate('useFixture => realHandProbe.prepare(useFixture)', use_fixture)
        require(build == '0.7.0', f'Unexpected diagnostics build: {build}')
        memory = {'beforeStart': renderer_memory(cdp)}
        benchmark = {'browserEngine': args.browser, 'browserVersion': browser.version, 'build': build, 'memory': memory}
        for phase in ('cold', 'warm'):
            start = page.evaluate('realHandProbe.start()')
            require(start['ready'] and start['metrics']['ready'], f'{phase} adapter start failed')
            require(start['metrics']['version'] == runtime_version and
                    start['metrics']['model'] == 'mediapipe-hand-landmarker-float16-v1',
                    'Adapter metrics do not identify the pinned runtime and model')
            memory[f'{phase}Ready'] = renderer_memory(cdp)
            result = page.evaluate('options => realHandProbe.infer(options)', {'frames': args.frames, 'warmup': args.warmup})
            check_inference(result, 1 + args.frames + args.warmup, use_fixture)
            measured = {**result, 'startMs': start['elapsedMs']}
            benchmark[phase] = measured
            memory[f'{phase}AfterInference'] = renderer_memory(cdp)
        require(page.evaluate('realHandProbe.stop()'), 'Stopped detector was still capable of inference')
        memory['afterStop'] = renderer_memory(cdp)

        policy = page.evaluate('url => realHandProbe.testCsp(url)', csp_url)
        require(policy == {'local': True, 'blocked': True, 'directive': 'connect-src'},
                f'Actual same-origin/CSP behavior failed: {policy}')

        if run_failure_checks:
            require(page.evaluate('realHandProbe.invalidTimestamp()'),
                    'Blank frame returned a hand or duplicate timestamp did not stop inference')
            missing = open_probe(context, f'{origin}{MISSING_MODEL_PATH}', errors, requests, console)
            require(missing.evaluate('realHandProbe.missingModel()'), 'Missing model did not fail closed')
            missing.close()

        violations = page.evaluate('realHandProbe.violations()')
        require(all(event['directive'] == 'connect-src' and event['uri'] in (csp_url, TELEMETRY_URL)
                    for event in violations), f'Unexpected CSP violations: {violations}')
        require(not errors, f'Uncaught browser page errors: {errors}')
        external = [url for url in requests if not url.startswith(f'{origin}/')]
        require(not external, f'Nonlocal page requests escaped CSP: {external}')
        benchmark['blockedTelemetryCount'] = sum(event['uri'] == TELEMETRY_URL for event in violations)
        benchmark['consoleCounts'] = {kind: sum(entry[0] == kind for entry in console)
                                     for kind in ('error', 'warning')}
        return benchmark
    finally:
        browser.close()


def stats(samples):
    ordered = sorted(samples)
    return {'n': len(ordered), 'median': round(statistics.median(ordered), 2),
            'p95': round(ordered[math.ceil(len(ordered) * 0.95) - 1], 2),
            'min': round(ordered[0], 2), 'max': round(ordered[-1], 2)}


def aggregate(trials, phase):
    runs = [trial[phase] for trial in trials]
    steady = [sample for run in runs for sample in run['steadyMs']]
    measured_ms = sum(steady)
    return {'startMs': stats([run['startMs'] for run in runs]),
            'firstInferenceMs': stats([run['firstMs'] for run in runs]),
            'steadyInferenceMs': stats(steady),
            'estimatedUnpacedCallsPerSecond': round(len(steady) * 1000 / measured_ms, 2) if measured_ms else None,
            'validFingertipFrames': sum(run['points'] for run in runs),
            'blankResults': sum(run['blanks'] for run in runs)}


def host_details():
    details = {'platform': platform.platform(), 'visibleLogicalCpus': os.cpu_count()}
    if sys.platform == 'linux':
        try:
            details['cpuModel'] = next(line.split(':', 1)[1].strip()
                                       for line in Path('/proc/cpuinfo').read_text().splitlines()
                                       if line.startswith('model name'))
        except (OSError, StopIteration):
            pass
        try:
            details['cgroupCpuQuotaAndPeriodMicros'] = Path('/sys/fs/cgroup/cpu.max').read_text().strip()
        except OSError:
            pass
    return details


def bounded_int(minimum, maximum):
    def convert(value):
        number = int(value)
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError(f'expected a number from {minimum} to {maximum}')
        return number
    return convert


def main():
    from vendor_hand_model import VERSION

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True, help='Private staged site with exact local runtime and model')
    parser.add_argument('--fixture', type=Path, help='Locally cached, SHA-256-pinned Google thumb_up.jpg; otherwise use blank frames')
    parser.add_argument('--browser', choices=('chromium', 'webkit'), default='chromium',
                        help='Browser engine; default chromium; WebKit is NOT iOS Safari')
    parser.add_argument('--chromium', help='Custom Chromium executable; not supported with --browser webkit')
    parser.add_argument('--trials', type=bounded_int(1, 10), default=3)
    parser.add_argument('--frames', type=bounded_int(1, 120), default=30, help='Measured frames per cold and warm run')
    parser.add_argument('--warmup', type=bounded_int(0, 20), default=5, help='Discarded frames per run after the separately timed first frame')
    args = parser.parse_args()
    if args.browser != 'chromium' and args.chromium:
        parser.error('--chromium executable override is incompatible with --browser webkit')
    files = site_files(args.site, args.fixture)
    with ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, files=files)) as server:
        server.csp_probe_received = threading.Event()
        server.missing_model_requested = threading.Event()
        threading.Thread(target=server.serve_forever, daemon=True).start()
        origin = f'http://127.0.0.1:{server.server_port}'
        csp_url = f'http://localhost:{server.server_port}{CSP_PROBE_PATH}'
        try:
            with sync_playwright() as playwright:
                trials = [run_trial(playwright, origin, csp_url, args, VERSION, trial == 0)
                          for trial in range(args.trials)]
        finally:
            server.shutdown()
        require(not server.csp_probe_received.is_set(), 'A CSP-blocked test request reached the loopback server')
        require(server.missing_model_requested.is_set(), 'Missing-model test did not reach the expected local endpoint')

    print(json.dumps({
        'status': 'pass', 'runtime': f'MediaPipe Tasks Vision {VERSION}', 'build': trials[0]['build'],
        'browserEngine': args.browser, 'browserVersion': trials[0]['browserVersion'],
        'playwright': version('playwright'), 'python': platform.python_version(),
        'host': host_details(),
        'input': 'Pinned Google thumb_up.jpg, repeated' if args.fixture else 'Blank frames only; no positive inference claim',
        'frameSize': [160, 120], 'virtualTimestampFramesPerSecond': 15,
        'trialCount': args.trials, 'steadyFramesPerPhasePerTrial': args.frames, 'warmupFramesPerPhase': args.warmup,
        'checks': ['Startup', 'Frame inference', 'Blank frame', 'Throttling', 'Same-page restart', 'Stop',
                   'Duplicate timestamp', 'Missing model', 'CSP network boundary'],
        'cold': aggregate(trials, 'cold'), 'warm': aggregate(trials, 'warm'),
        'blockedTelemetryCount': sum(trial['blockedTelemetryCount'] for trial in trials),
        'memorySamplesByTrial': [trial['memory'] for trial in trials],
        'consoleCountsByTrial': [trial['consoleCounts'] for trial in trials],
        'limitations': [
            'Cold starts use fresh browser processes with the host file cache intact. Start times exclude browser launch and fixture decoding.',
            'Warm starts replace the live detector in the same page and include its close time.',
            'Unpaced call throughput excludes capture, scheduling, UI, and the configured 55 ms throttle.',
            'Chromium memory is sampled aggregate renderer PSS, excluding browser, GPU, and network processes; WebKit CDP memory is unavailable.',
            'Immediate post-stop memory can include allocations pending reclamation and cannot establish a leak.',
            'Measurements are from headless ' + args.browser + ' on this Linux host. Live camera and iPhone Safari performance require physical-device testing.',
        ],
    }, indent=2))


if __name__ == '__main__':
    main()
