#!/usr/bin/env python3
"""Browser smoke of neutral root plus nested model-free owner preview.

Linux WebKit with iPhone-like viewport is NOT physical iOS Safari or live HTTPS.
All requests stay on an ephemeral loopback port. No external network or deploy.
"""
import argparse
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def check(label, ok):
    if not ok:
        raise AssertionError(label)
    print("PASS " + label, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", required=True, type=Path)
    args = parser.parse_args()
    site = args.site_dir.resolve()
    required = { "index.html", "_headers", "operator-preview" }
    if not site.is_dir() or {p.name for p in site.iterdir()} != required:
        raise SystemExit("BLOCKED: not an exact unpacked operator preview")
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(site)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://localhost:%d" % server.server_port
    try:
        with sync_playwright() as playwright:
            browser = playwright.webkit.launch(headless=True)
            try:
                context = browser.new_context(
                    viewport={"width": 390, "height": 844},
                    device_scale_factor=3,
                    is_mobile=True,
                    has_touch=True,
                )
                page = context.new_page()
                errors = []
                external = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("request", lambda r: external.append(r.url)
                        if not r.url.startswith(base + "/") else None)
                page.goto(base + "/", wait_until="load")
                check("neutral root contains no ANIMATE application or script tags",
                      page.locator("h1").inner_text() == "Neutral hosting test"
                      and page.locator("script").count() == 0
                      and page.locator("a").count() == 0
                      and "ANIMATE" not in page.content())
                page.goto(base + "/operator-preview/index.html?debug=1", wait_until="load")
                check("nested HTML resolves same-directory CSS and JS",
                      page.evaluate("typeof AnimateCore !== 'undefined' && typeof AnimateHandML !== 'undefined'")
                      and page.locator("#lab").is_hidden())
                check("nested mode offers only colour and foreground ML-free options",
                      page.locator('#detector option[value="hand"]').count() == 0
                      and page.locator("#detector option").count() == 2
                      and page.locator("#baselineDisclosure").is_visible())
                check("operator-only nested debug instrumentation is available",
                      page.locator("#dbgbox").count() == 1
                      and page.locator("#dbgbox").is_visible())
                page.select_option("#role", label="Educator")
                page.check("#adult")
                page.check("#consent")
                page.click("#enter")
                page.click('[data-mode="play"]')
                page.click("#sample")
                page.click("#start")
                for zone in ("Middle", "Left", "Right"):
                    page.click("#tap" + zone)
                check("nested touch fallback completes deterministic three-zone test",
                      page.locator("#score").inner_text() == "3 / 3")
                check("operator preview never requests off-origin assets", not external)
                check("operator preview has no unhandled WebKit errors", not errors)
                context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
