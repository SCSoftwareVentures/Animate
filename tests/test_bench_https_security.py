#!/usr/bin/env python3
"""Real-origin HTTP header and provenance preflight for the HTTPS bench server.

Serves only ephemeral loopback HTTP inside CI: it does not create an HTTPS
preview, obtain a certificate, deploy a site, or test a physical iPhone.
"""
import argparse
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_baseline_preview import build
from serve_safari_https import BenchHandler, CSP_HEADER, bench_address, load_assets


passed = 0


def check(label, value):
    global passed
    if not value:
        raise AssertionError(label)
    passed += 1
    print("PASS " + label, flush=True)


def refuse(label, fn):
    try:
        fn()
    except (ValueError, OSError):
        check(label, True)
    else:
        raise AssertionError(label)


def request(port, method, path, hostname=None):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    headers = {"Host": hostname or "127.0.0.1:%d" % port}
    try:
        conn.request(method, path, headers=headers)
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        conn.close()


def main():
    with TemporaryDirectory(prefix="animate-bench-security-") as base:
        folder = Path(base) / "candidate"
        build(folder)
        site = folder / "site"
        assets = load_assets(site)
        check("exact generated six-file candidate is loadable without ML binary",
              set(assets) == {'/', *('/' + n for n in
                             ('index.html','core.js','foreground.js','hand_ml.js','app.js','styles.css'))})
        check("baseline HTML is transformed and does not offer the hand model",
              b'baselineDisclosure' in assets['/index.html'][1] and
              b'<option value="hand"' not in assets['/index.html'][1])
        refuse("untransformed source directory cannot be served as baseline",
               lambda: load_assets(ROOT / "site"))

        manifest_path = folder / "MANIFEST.json"
        original_manifest = manifest_path.read_text()
        metadata = json.loads(original_manifest)
        metadata['sourceCommit'] = '0' * 40
        manifest_path.write_text(json.dumps(metadata))
        refuse("wrong commit provenance fails closed", lambda: load_assets(site))
        manifest_path.write_text(original_manifest)

        metadata = json.loads(original_manifest)
        metadata['hostingApproved'] = True
        manifest_path.write_text(json.dumps(metadata))
        refuse("forged hosting approval marker is rejected", lambda: load_assets(site))
        manifest_path.write_text(original_manifest)

        index_path = site / 'index.html'
        index_bytes = index_path.read_bytes()
        index_path.write_bytes(index_bytes + b'<!-- injected marker -->')
        refuse("tampered baseline HTML is not served", lambda: load_assets(site))
        index_path.write_bytes(index_bytes)

        (site / 'vendor').mkdir()
        refuse("unknown vendor directory and model assets cannot be served", lambda: load_assets(site))
        (site / 'vendor').rmdir()

        # No TLS or device access: test the exact application-level handler only.
        server = ThreadingHTTPServer(('127.0.0.1', 0), BenchHandler)
        port = server.server_port
        server.allowed_hosts = {'127.0.0.1:%d' % port}
        server.assets = load_assets(site)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            status, headers, body = request(port, "GET", "/index.html?v=0.7.0")
            check("GET serves only allowlisted candidate bytes on an approved Host",
                  status == 200 and body == index_bytes and
                  headers.get('Content-Type') == 'text/html; charset=utf-8')
            check("HTTP CSP blocks embedding and unapproved network destinations",
                  headers.get('Content-Security-Policy') == CSP_HEADER and
                  "frame-ancestors 'none'" in CSP_HEADER and
                  "connect-src 'self'" in CSP_HEADER)
            check("browser permissions disable extraneous sensors and prohibit framing",
                  headers.get('Permissions-Policy') ==
                  'camera=(self), microphone=(), geolocation=(), payment=()' and
                  headers.get('X-Frame-Options') == 'DENY')
            check("response forbids caching, referrers and cross-origin use",
                  headers.get('Cache-Control') == 'no-store' and
                  headers.get('Referrer-Policy') == 'no-referrer' and
                  headers.get('Cross-Origin-Resource-Policy') == 'same-origin' and
                  headers.get('X-Content-Type-Options') == 'nosniff' and
                  'Access-Control-Allow-Origin' not in headers)
            status_head, head_headers, head_body = request(port, "HEAD", "/index.html")
            check("HEAD retains security policy without sending document body",
                  status_head == 200 and head_body == b'' and
                  head_headers.get('Content-Security-Policy') == CSP_HEADER and
                  head_headers.get('Content-Length') == str(len(index_bytes)))
            missing, miss_headers, _ = request(port, 'GET', '/vendor/mediapipe/models/hand_landmarker.task')
            check("model and runtime URL is inaccessible even by direct request",
                  missing == 404 and miss_headers.get('X-Frame-Options') == 'DENY')
            denied, denied_headers, _ = request(port, 'GET', '/', hostname='wrong.example')
            check("invalid Host is rejected with protective response headers",
                  denied == 400 and denied_headers.get('Content-Security-Policy') == CSP_HEADER)
            other, _, _ = request(port, 'GET', '/../site/index.html')
            check("path traversal cannot access files outside the static allowlist", other == 404)
            method, _, _ = request(port, 'POST', '/')
            check("HTTP POST is unsupported (no incoming report collection)", method == 501)
            try:
                bench_address('8.8.8.8')
            except argparse.ArgumentTypeError:
                check("public internet bind address is rejected", True)
            else:
                raise AssertionError("public bind should be rejected")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    print("PASS %d/%d HTTPS bench boundary tests" % (passed, passed), flush=True)


if __name__ == "__main__":
    main()
