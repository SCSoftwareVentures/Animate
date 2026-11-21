#!/usr/bin/env python3
"""WebKit-on-Linux preflight for ANIMATE's browser lifecycle.

A real WebKit renderer checks the site over loopback with the production CSP.
This is NOT iOS Safari, camera hardware, trained-model inference or a real-user test.
"""
import argparse
import functools
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parent.parent / "site"


class SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def check(label, predicate):
    if not predicate:
        raise AssertionError(label)
    print("PASS " + label, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", type=Path, default=SITE)
    parser.add_argument("--baseline", action="store_true", help="Require ML-free operator baseline UI")
    args = parser.parse_args()
    if args.baseline and args.site_dir.resolve() == SITE.resolve():
        parser.error("--baseline requires a separately transformed --site-dir")
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        functools.partial(SilentHandler, directory=str(args.site_dir)),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = "http://localhost:%d/index.html" % server.server_port
    try:
        with sync_playwright() as playwright:
            browser = playwright.webkit.launch(headless=True)
            try:
                context = browser.new_context(
                    viewport={"width": 390, "height": 844},
                    device_scale_factor=3,
                    is_mobile=True,
                    has_touch=True,
                    accept_downloads=True,
                )
                page = context.new_page()
                errors = []
                external_requests = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on(
                    "request",
                    lambda request: external_requests.append(request.url)
                    if not request.url.startswith("http://localhost:%d/" % server.server_port)
                    else None,
                )
                page.goto(url, wait_until="load", timeout=20000)

                check("WebKit loads the application scripts on the real origin",
                      page.evaluate("typeof AnimateCore !== 'undefined' && typeof AnimateHandML !== 'undefined'"))
                check("the normal website CSP is present",
                      page.evaluate("""() => {
                        const policy = document.querySelector('meta[http-equiv="Content-Security-Policy"]');
                        return policy && policy.content.includes("connect-src 'self'") &&
                          policy.content.includes("default-src 'none'");
                      }"""))
                if args.baseline:
                    check("ML-free baseline hides hand tracking selection",
                          page.locator('#detector option[value="hand"]').count() == 0 and
                          page.locator('#detector option').count() == 2)
                    check("ML-free baseline discloses unavailability in accessible UI",
                          page.locator('#baselineDisclosure').is_visible() and
                          "Hand ML is unavailable" in page.locator('#baselineDisclosure').inner_text())
                check("WebKit intro starts with explicit consent",
                      page.locator("#intro").is_visible() and page.locator("#lab").is_hidden())
                page.click("#enter")
                check("unconsented entry is rejected",
                      "Choose an intended use" in page.locator("#introerr").inner_text())

                page.evaluate("""() => {
                  localStorage.setItem('animate-validation-v05', 'old-data');
                  localStorage.setItem('animate-validation-v1', 'old-data');
                  localStorage.setItem('unrelated-key', 'keep');
                }""")
                page.select_option("#role", label="Educator")
                page.check("#adult")
                page.check("#consent")
                page.click("#enter")
                check("consented WebKit session has stable local record",
                      page.evaluate("""() => {
                        const r = JSON.parse(localStorage.getItem('animate-validation-v07'));
                        return r && r.build === '0.7.0' && r.role === 'Educator' && r.id;
                      }"""))

                page.click('[data-mode="play"]')
                page.click("#sample")
                page.click("#start")
                for zone in ("Middle", "Left", "Right"):
                    page.click("#tap" + zone)
                check("WebKit touch challenge completes the real three-zone UI",
                      page.locator("#score").inner_text() == "3 / 3" and
                      page.locator("#progressBar").get_attribute("aria-valuenow") == "3")
                page.fill("#problem", "I currently use paper cards.")
                page.click("#saveProblem")
                check("WebKit summary counts feedback without disclosing free text",
                      page.evaluate("""() => {
                        const r = JSON.parse(localStorage.getItem('animate-validation-v07'));
                        const result = AnimateCore.summarize([{
                          ...r, exportedAt: new Date().toISOString()
                        }]);
                        return result.provisional.feedbackRespondents === 1 &&
                          result.provisional.feedbackAfterCameraCompletion === 0 &&
                          result.byRole.Educator.acceptedExports === 1 &&
                          !JSON.stringify(result).includes('paper cards');
                      }"""))

                # A browser extension, debug session or old build could have written untrusted
                # fields into localStorage. Reload must strip those fields without losing feedback.
                page.evaluate("""() => {
                  const key = 'animate-validation-v07';
                  const raw = JSON.parse(localStorage.getItem(key));
                  raw.privateUnknown = {sessionSecret:'LOCAL_LEAK_CANARY'};
                  raw.events[0].hiddenData = {password:'EVENT_LEAK_CANARY'};
                  localStorage.setItem(key, JSON.stringify(raw));
                }""")
                page.reload(wait_until="load")
                check("WebKit restoration strips injected fields but preserves valid feedback",
                      page.evaluate("""() => {
                        const raw = localStorage.getItem('animate-validation-v07');
                        const r = JSON.parse(raw);
                        return !!r && !raw.includes('LOCAL_LEAK_CANARY') &&
                          !raw.includes('EVENT_LEAK_CANARY') &&
                          r.events.some(e => e.type === 'problem_response' &&
                            e.answer === 'I currently use paper cards.');
                      }"""))

                with page.expect_download(timeout=10000) as download_info:
                    page.click("#export")
                download = download_info.value
                check("WebKit downloads pseudonymous JSON only after explicit action",
                      download.suggested_filename.startswith("animate-0.7.0-") and
                      download.suggested_filename.endswith(".json"))
                export_data = json.loads(Path(download.path()).read_text())
                check("WebKit export keeps opted-in feedback but excludes injected storage fields",
                      not any(key in export_data for key in ('privateUnknown', 'hiddenData')) and
                      not any('hiddenData' in event for event in export_data['events']) and
                      any(event.get('answer') == 'I currently use paper cards.'
                          for event in export_data['events']))

                page.on("dialog", lambda dialog: dialog.accept())
                page.click("#reset")
                check("WebKit deletion removes all ANIMATE research versions but not other keys",
                      page.evaluate("""() => ({
                        current: localStorage.getItem('animate-validation-v07'),
                        v1: localStorage.getItem('animate-validation-v1'),
                        v05: localStorage.getItem('animate-validation-v05'),
                        unrelated: localStorage.getItem('unrelated-key')
                      })""") == {"current": None, "v1": None, "v05": None, "unrelated": "keep"})
                check("WebKit reset returns to disclosure screen with confirmed deletion",
                      page.locator("#intro").is_visible() and
                      page.locator("#lab").is_hidden() and
                      "were deleted" in page.locator("#introerr").inner_text())
                check("no unexpected third-party network requests", not external_requests)
                check("no JavaScript errors on WebKit", not errors)
                context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print("PASS %s WebKit-on-Linux preflight checks" % ("16/16 baseline" if args.baseline else "14/14"), flush=True)


if __name__ == "__main__":
    main()
