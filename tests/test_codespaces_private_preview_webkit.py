#!/usr/bin/env python3
"""Actual Linux WebKit smoke for the same read-only Codespaces static handler.

No Codespace is created. No network requests leave ephemeral localhost.
This does not replace physical iOS Safari or a real private forwarded-port audit.
"""
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from run_codespaces_private_preview import make_handler, stage_verified_preview


def run():
    with tempfile.TemporaryDirectory(prefix="animate-codespaces-webkit-") as temp:
        site, receipt = stage_verified_preview(temp)
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(site))
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = "http://127.0.0.1:%s" % server.server_address[1]
        try:
            with sync_playwright() as pw:
                browser = pw.webkit.launch(headless=True)
                try:
                    context = browser.new_context(
                        viewport={"width": 390, "height": 844},
                        is_mobile=True, has_touch=True,
                        device_scale_factor=3,
                    )
                    page = context.new_page()
                    off_origin = []
                    errors = []
                    page.on("request", lambda r: off_origin.append(r.url)
                            if not r.url.startswith(base + "/") else None)
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    page.goto(base + "/operator-preview/verify.html", wait_until="load")
                    page.wait_for_function(
                        "() => document.querySelector('#result').textContent.includes('\"checkedFiles\"')"
                    )
                    data = json.loads(page.locator("#result").inner_text())
                    assert data["result"] == "PASS", data
                    assert data["checkedFiles"] == 7, data
                    assert data["checkedGetAndHeadHeaders"] == 14, data
                    assert data["confirmedAbsentPaths"] == 4, data
                    assert data["failures"] == [], data
                    assert data.get("htmlDiagnostics", []) == [], data
                    print("PASS real WebKit same-origin verifier: 7/7 assets 14/14 headers 4/4 absent", flush=True)

                    page.goto(base + "/operator-preview/index.html?debug=1")
                    assert page.locator("#baselineDisclosure").is_visible()
                    assert page.locator("#detector option[value='hand']").count() == 0
                    page.select_option("#role", label="Educator")
                    page.check("#adult")
                    page.check("#consent")
                    page.click("#enter")
                    page.click('[data-mode="play"]')
                    page.click("#sample")
                    page.click("#start")
                    for zone in ("Middle", "Left", "Right"):
                        page.click("#tap" + zone)
                    assert page.locator("#score").inner_text() == "3 / 3"
                    print("PASS real WebKit nested touch path in Codespaces-like origin", flush=True)

                    assert not off_origin, off_origin
                    assert not errors, errors
                    print("PASS no unexpected off-origin requests or unhandled WebKit errors", flush=True)
                    context.close()
                finally:
                    browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    run()
