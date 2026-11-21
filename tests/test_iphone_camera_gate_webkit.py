#!/usr/bin/env python3
"""Test SHA-256/header Safari verifier against a local HTTP fixture in WebKit.

A local server supplies the exact _headers policy. This tests browser logic,
not Netlify's real authenticated responses or physical iOS Safari.
"""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_iphone_camera_gate import EXPECTED, VERIFY_HTML
from build_zero_cost_preview import headers_text


class HeaderFixture(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def end_headers(self):
        for raw in headers_text().splitlines()[1:]:
            name, value = raw.strip().split(": ", 1)
            if self.server.omit_header and name == self.server.omit_header:
                continue
            self.send_header(name, value)
        super().end_headers()

    def do_GET(self):
        if self.server.tamper_js and urlsplit(self.path).path == "/operator-preview/app.js":
            data = ((Path(self.directory) / "operator-preview" / "app.js").read_bytes() +
                    b"\n// unexpected altered served bytes\n")
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()


def test_case(site, tamper_js=False, omit_header=None):
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(HeaderFixture, directory=str(site)))
    server.tamper_js = tamper_js
    server.omit_header = omit_header
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        origin = "http://127.0.0.1:%d" % server.server_port
        with sync_playwright() as playwright:
            browser = playwright.webkit.launch(headless=True)
            try:
                context = browser.new_context(
                    viewport={"width": 390, "height": 844},
                    device_scale_factor=3, is_mobile=True, has_touch=True
                )
                page = context.new_page()
                errors, external = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("request", lambda request: external.append(request.url)
                        if not request.url.startswith(origin + "/") else None)
                page.goto(origin + "/" + VERIFY_HTML, wait_until="load", timeout=20000)
                page.wait_for_function(
                    "() => { const t = document.getElementById('result').textContent; "
                    "return t.startsWith('{') && t.includes('checkedFiles'); }",
                    timeout=20000
                )
                result = json.loads(page.locator("#result").inner_text())
                if external:
                    raise AssertionError("Verifier attempted external network calls: " + str(external))
                if errors:
                    raise AssertionError("Verifier caused JS errors: " + str(errors))
                if result["expectedFiles"] != 7 or result["expectedGetAndHeadHeaders"] != 14:
                    raise AssertionError("Missing approved application audit coverage: " + str(result))
                if not tamper_js and not omit_header:
                    assert result["result"] == "PASS", result
                    assert result["checkedFiles"] == 7, result
                    assert result["checkedGetAndHeadHeaders"] == 14, result
                    assert result["confirmedAbsentPaths"] == 4, result
                    assert result["failures"] == [], result
                    print("PASS unmodified source/hash/header fixture gets browser gate PASS", flush=True)
                elif tamper_js:
                    assert result["result"] == "FAIL", result
                    assert any("app.js" in x and "SHA-256 mismatch" in x for x in result["failures"]), result
                    print("PASS altered app script fails cryptographic gate", flush=True)
                elif omit_header:
                    assert result["result"] == "FAIL", result
                    assert any(omit_header in x for x in result["failures"]), result
                    print("PASS missing security header fails browser gate", flush=True)
                context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, required=True)
    args = parser.parse_args()
    site = args.site_dir.resolve()
    if (not site.is_dir() or
            {p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file()} != EXPECTED):
        raise SystemExit("BLOCKED: invalid unpacked camera-gate ZIP")
    test_case(site)
    test_case(site, tamper_js=True)
    test_case(site, omit_header="Permissions-Policy")


if __name__ == "__main__":
    main()
