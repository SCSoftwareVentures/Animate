#!/usr/bin/env python3
"""WebKit proof: local same-origin HTML differences are reported but never cleared."""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, expect


class MutatingFixture(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        p = urlsplit(self.path).path
        if self.server.inject_html and p in ("/", "/index.html", "/operator-preview/index.html"):
            actual_path = "index.html" if p in ("/", "/index.html") else p.lstrip("/")
            data = (Path(self.directory) / actual_path).read_bytes() + b"\n<!-- NETLIFY-EDGE-TEST-ONLY /.netlify/scripts/hud -->\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()


def verify_browser(site, injected):
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(MutatingFixture, directory=str(site)))
    server.inject_html = injected
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        origin = f"http://127.0.0.1:{server.server_port}"
        with sync_playwright() as playwright:
            browser = playwright.webkit.launch(headless=True)
            try:
                context = browser.new_context(
                    viewport={"width": 390, "height": 844},
                    device_scale_factor=3, is_mobile=True, has_touch=True)
                page = context.new_page()
                outside, errors = [], []
                page.on("request", lambda request: outside.append(request.url)
                        if not request.url.startswith(origin + "/") else None)
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(origin + "/operator-preview/inspect.html", wait_until="load")
                expect(page.locator("#diagnosticResult")).to_contain_text(
                    '"decision": "DIAGNOSTIC_ONLY_CAMERA_NOT_CLEARED"', timeout=20000)
                result = json.loads(page.locator("#diagnosticResult").inner_text())
                assert result["checkedPaths"] == 2, result
                assert result["decision"] == "DIAGNOSTIC_ONLY_CAMERA_NOT_CLEARED"
                assert not outside, outside
                assert not errors, errors
                if injected:
                    assert all(f["status"] == "HTML_RESPONSE_MODIFIED" for f in result["files"]), result
                    assert all(f["markupIndicators"]["netlifyMarker"] for f in result["files"]), result
                    assert all(f["insertedReceivedBytes"] > 0 for f in result["files"]), result
                    assert all("NETLIFY-EDGE-TEST-ONLY" in f["sanitizedChangedExcerpt"]
                               for f in result["files"]), result
                    print("PASS injected HTML detected and exact camera gate remains blocked")
                else:
                    assert all(f["status"] == "EXACT_MATCH" for f in result["files"]), result
                    print("PASS clean HTML bytes match while diagnostic never grants camera approval")
                context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", required=True, type=Path)
    args = parser.parse_args()
    site = args.site_dir.resolve()
    if not (site / "operator-preview" / "inspect.html").is_file():
        raise SystemExit("BLOCKED: missing reviewed diagnostic")
    verify_browser(site, injected=False)
    verify_browser(site, injected=True)


if __name__ == "__main__":
    main()
