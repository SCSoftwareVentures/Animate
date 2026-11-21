/* Exact-byte iPhone camera preflight, with no camera, tracking or external requests.
   Generated only into the approved model-free operator preview.
   Do not weaken HTTP header requirements to make a provider pass. */
(async () => {
  'use strict';
  const FILES = __EXPECTED_APP_HASHES__;
  const HEADERS = __EXPECTED_HEADERS__;
  const REQUIRED_ABSENT = [
    '/operator-preview/vendor/mediapipe/models/hand_landmarker.task',
    '/operator-preview/vendor/mediapipe/wasm/vision_wasm_internal.wasm',
    '/operator-preview/LOCAL_ONLY_OPERATOR_PREVIEW_RECEIPT.json',
    '/MANIFEST.json'
  ];
  const reportEl = document.getElementById('result');
  const copy = document.getElementById('copyResult');
  const failures = [];
  let checkedFiles = 0, checkedHeaders = 0, checkedAbsent = 0;
  const record = value => failures.push(String(value).slice(0, 160));
  const normalized = value => String(value || '').trim().replace(/\s+/g, ' ').toLowerCase();
  const fail = (path, message) => record(path + ': ' + message);
  const render = () => {
    const result = {
      audit: 'ANIMATE_V07_ON_DEVICE_FILE_AND_HEADER_GATE',
      result: failures.length === 0 &&
        checkedFiles === Object.keys(FILES).length &&
        checkedHeaders === 2 * Object.keys(FILES).length &&
        checkedAbsent === REQUIRED_ABSENT.length ? 'PASS' : 'FAIL',
      checkedFiles, expectedFiles: Object.keys(FILES).length,
      checkedGetAndHeadHeaders: checkedHeaders,
      expectedGetAndHeadHeaders: 2 * Object.keys(FILES).length,
      confirmedAbsentPaths: checkedAbsent,
      expectedAbsentPaths: REQUIRED_ABSENT.length,
      failures
    };
    reportEl.textContent = JSON.stringify(result, null, 2);
    if (copy) {
      copy.disabled = false;
      copy.addEventListener('click', () => {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(reportEl.textContent).catch(() => {
            reportEl.focus();
          });
        } else {
          reportEl.focus();
        }
      }, { once: true });
    }
  };

  // Required headers are applied by the Netlify _headers file to all paths.
  function inspectHeaders(path, method, response) {
    for (const [name, expected] of Object.entries(HEADERS)) {
      const actual = response.headers.get(name);
      if (name === 'Strict-Transport-Security') {
        const m = /(?:^|;)\s*max-age=(\d+)(?:;|$)/i.exec(actual || '');
        if (!m || Number(m[1]) < 86400) fail(path, method + ' insufficient Strict-Transport-Security');
      } else if (name === 'Cache-Control') {
        if (!/(?:^|,)\s*no-store(?:\s*,|$)/i.test(actual || '') ||
            /(?:^|,)\s*public(?:\s*,|$)/i.test(actual || '')) {
          fail(path, method + ' unsafe Cache-Control');
        }
      } else if (normalized(actual) !== normalized(expected)) {
        fail(path, method + ' missing/changed ' + name);
      }
    }
  }

  try {
    if (!(location.protocol === 'https:' || location.hostname === 'localhost' ||
          location.hostname === '127.0.0.1')) throw Error('Not a secure origin');
    if (!crypto || !crypto.subtle || !crypto.subtle.digest) throw Error('Web Crypto digest unavailable');
    if (navigator.serviceWorker && navigator.serviceWorker.controller) {
      throw Error('An active service worker may intercept verification requests');
    }
    if (location.pathname !== '/operator-preview/verify.html') {
      throw Error('Not running at the approved verifier path');
    }
    for (const [path, expected] of Object.entries(FILES)) {
      const url = new URL('/' + path, location.origin);
      const nonce = String(Date.now()) + '-' + String(checkedFiles);
      url.searchParams.set('integrity_probe', nonce);
      try {
        const response = await fetch(url.href, {
          method: 'GET', credentials: 'same-origin', cache: 'no-store',
          redirect: 'error', mode: 'same-origin'
        });
        if (response.status !== 200 || response.redirected ||
            new URL(response.url).origin !== location.origin) {
          fail(path, 'GET was not authenticated 200 same-origin content');
          continue;
        }
        const bytes = await response.arrayBuffer();
        if (bytes.byteLength > 250000) {
          fail(path, 'GET unexpectedly large');
          continue;
        }
        const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),
          value => value.toString(16).padStart(2, '0')).join('');
        if (digest !== expected) fail(path, 'SHA-256 mismatch versus exact CI-reviewed asset');
        else checkedFiles++;
        inspectHeaders(path, 'GET', response);
        const head = await fetch(url.href, {
          method: 'HEAD', credentials: 'same-origin', cache: 'no-store',
          redirect: 'error', mode: 'same-origin'
        });
        if (head.status !== 200 || head.redirected) {
          fail(path, 'HEAD not authenticated 200');
        } else {
          inspectHeaders(path, 'HEAD', head);
          checkedHeaders++;
        }
        checkedHeaders++;
      } catch (error) {
        fail(path, 'GET/HEAD failed: ' + (error && error.name || 'Unknown'));
      }
    }
    for (const path of REQUIRED_ABSENT) {
      try {
        const response = await fetch(new URL(path, location.origin), {
          method: 'HEAD', credentials: 'same-origin',
          redirect: 'manual', cache: 'no-store', mode: 'same-origin'
        });
        if ([404, 410].includes(response.status)) checkedAbsent++;
        else fail(path, 'forbidden path returned HTTP ' + response.status);
      } catch (error) {
        fail(path, 'forbidden-path check failed: ' + (error && error.name || 'Unknown'));
      }
    }
  } catch (error) {
    record('Gate could not run: ' + (error && error.message || 'unknown'));
  }
  // There is no network send, storage, camera access, or automatic report upload.
  render();
})();
