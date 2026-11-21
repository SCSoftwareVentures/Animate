/* ANIMATE — same-origin HTML response transformation investigation.
   This tool is diagnostic only: it never grants camera approval, submits data,
   reads cookies/local storage, executes response markup, or contacts third parties.
   Source bytes are already public; no private identifiers are expected/recorded. */
(async () => {
  'use strict';
  const EXPECTED = __EXPECTED_HTML_BASE64__;
  const output = document.getElementById('diagnosticResult');
  const copy = document.getElementById('copyDiagnostic');
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  const hex = bytes => Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
  const sha256 = async bytes => hex(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)));
  const decodeExpected = encoded => Uint8Array.from(atob(encoded), ch => ch.charCodeAt(0));
  const count = (str, pattern) => (str.match(pattern) || []).length;
  const sanitize = value => String(value)
    .replace(/https?:\/\/[^\s"'<>]+/gi, '[URL]')
    .replace(/(?:token|secret|session|password|api[_-]?key|authorization)\s*[:=]\s*[^ \n"'<>]{1,160}/gi, '[REDACTED_FIELD]')
    .replace(/[A-Za-z0-9_+/-]{28,}/g, '[LONG_VALUE]')
    .replace(/[\u0000-\u001f\u007f]/g, ' ')
    .slice(0, 180);
  const reports = [];
  const publish = () => {
    const result = {
      audit: 'ANIMATE_HTML_BYTE_DELIVERY_DIAGNOSTIC',
      decision: 'DIAGNOSTIC_ONLY_CAMERA_NOT_CLEARED',
      checkedPaths: reports.length,
      files: reports
    };
    output.textContent = JSON.stringify(result, null, 2);
    copy.disabled = false;
    copy.onclick = () => {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(output.textContent).catch(() => output.focus());
      } else output.focus();
    };
  };
  try {
    if (!(location.protocol === 'https:' || location.hostname === 'localhost' ||
          location.hostname === '127.0.0.1')) throw Error('Insecure origin');
    if (location.pathname !== '/operator-preview/inspect.html') {
      throw Error('Unexpected verifier location');
    }
    if (!crypto?.subtle?.digest) throw Error('Web Crypto unavailable');
    if (navigator.serviceWorker?.controller) throw Error('Service worker interception possible');
    for (const [path, encoded] of Object.entries(EXPECTED)) {
      const expected = decodeExpected(encoded);
      const url = new URL('/' + path, location.origin);
      url.searchParams.set('probe', String(Date.now()) + '-html');
      const data = { path, status: 'NOT_CHECKED' };
      reports.push(data);
      try {
        const response = await fetch(url, {
          method: 'GET', credentials: 'same-origin', redirect: 'error',
          cache: 'no-store', mode: 'same-origin'
        });
        data.httpStatus = response.status;
        data.mime = (response.headers.get('content-type') || '').split(';')[0].slice(0, 80);
        if (response.status !== 200 || response.redirected ||
            new URL(response.url).origin !== location.origin) {
          data.status = 'UNEXPECTED_RESPONSE';
          continue;
        }
        const actual = new Uint8Array(await response.arrayBuffer());
        if (actual.length > 250000) {
          data.status = 'UNEXPECTEDLY_LARGE_RESPONSE';
          continue;
        }
        data.expectedBytes = expected.length;
        data.receivedBytes = actual.length;
        data.expectedSha256 = await sha256(expected);
        data.receivedSha256 = await sha256(actual);
        if (data.expectedSha256 === data.receivedSha256) {
          data.status = 'EXACT_MATCH';
          continue;
        }
        data.status = 'HTML_RESPONSE_MODIFIED';
        let prefix = 0;
        while (prefix < expected.length && prefix < actual.length &&
               expected[prefix] === actual[prefix]) prefix++;
        let suffix = 0;
        while (suffix < expected.length - prefix &&
               suffix < actual.length - prefix &&
               expected[expected.length - 1 - suffix] === actual[actual.length - 1 - suffix]) suffix++;
        data.commonPrefixBytes = prefix;
        data.commonSuffixBytes = suffix;
        data.replacedExpectedBytes = expected.length - prefix - suffix;
        data.insertedReceivedBytes = actual.length - prefix - suffix;
        data.firstDifference = prefix;
        const text = decoder.decode(actual);
        const baselineText = decoder.decode(expected);
        // Count only markup-type indicators and show a bounded, redacted sample:
        // no full HTML export and no execution of fetched markup.
        data.markupIndicators = {
          netlifyMarker: /(?:powered by netlify|pre.launch toolbar|\.netlify\/scripts|data-netlify|netlify-hud)/i.test(text),
          additionalScriptTags: count(text, /<script\b/gi) - count(baselineText, /<script\b/gi),
          additionalIframeTags: count(text, /<iframe\b/gi) - count(baselineText, /<iframe\b/gi),
          additionalHtmlComments: count(text, /<!--/g) - count(baselineText, /<!--/g)
        };
        const rawSegment = decoder.decode(actual.slice(prefix, Math.min(actual.length, prefix + 240)));
        data.sanitizedChangedExcerpt = sanitize(rawSegment);
      } catch (error) {
        data.status = 'REQUEST_ERROR';
        data.failure = (error?.name || 'Error').slice(0, 80);
      }
    }
  } catch (error) {
    reports.push({ path: 'preflight', status: 'GATE_ERROR',
      failure: (error?.message || 'unknown').slice(0, 120) });
  }
  publish();
})();
