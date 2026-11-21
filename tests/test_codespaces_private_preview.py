#!/usr/bin/env python3
"""Adversarial standard-library tests of exact Codespaces preview origin."""
import contextlib
import hashlib
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_iphone_camera_gate import EXPECTED
from build_zero_cost_preview import headers_text
from run_codespaces_private_preview import (
    PORT, SECURITY_HEADERS, ROUTES, assert_real_codespace,
    make_handler, stage_verified_preview,
)


@contextlib.contextmanager
def running_server(site):
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(site))
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def request(port, method, path, headers=None):
    conn = HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request(method, path, headers=headers or {})
    response = conn.getresponse()
    body = response.read()
    data = response.status, dict(response.getheaders()), body
    conn.close()
    return data


class CodespacesPrivatePreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix="animate-codespaces-ci-")
        cls.site, cls.receipt = stage_verified_preview(cls.scratch.name)

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def test_exact_model_free_files_and_headers_no_readable_secrets(self):
        self.assertEqual({p.relative_to(self.site).as_posix()
                          for p in self.site.rglob("*") if p.is_file()}, EXPECTED)
        self.assertEqual(set(SECURITY_HEADERS), {
            line.strip().split(": ", 1)[0]
            for line in headers_text().splitlines()[1:]
        })
        self.assertEqual(ROUTES, {"/"} | {"/" + x for x in EXPECTED if x != "_headers"})
        self.assertEqual(PORT, 8765)
        with running_server(self.site) as port:
            for filename in sorted(EXPECTED - {"_headers"}):
                with self.subTest(filename=filename):
                    status, headers, body = request(port, "GET", "/" + filename)
                    self.assertEqual(status, 200)
                    self.assertEqual(hashlib.sha256(body).hexdigest(),
                                     self.receipt["fileSha256"][filename])
                    for name, value in SECURITY_HEADERS.items():
                        self.assertEqual(headers.get(name), value, (filename, name))
                    self.assertIn("no-store", headers["Cache-Control"])
                    status_h, headers_h, body_h = request(port, "HEAD", "/" + filename)
                    self.assertEqual(status_h, 200)
                    self.assertEqual(body_h, b"")
                    for name, value in SECURITY_HEADERS.items():
                        self.assertEqual(headers_h.get(name), value, (filename, name))
            status, _, body = request(port, "GET", "/")
            self.assertEqual(status, 200)
            self.assertEqual(hashlib.sha256(body).hexdigest(),
                             self.receipt["fileSha256"]["index.html"])

    def test_forbidden_paths_methods_and_bypass_variants_are_blocked(self):
        forbidden = [
            "/_headers", "/.git/config", "/.env", "/README.md",
            "/operator-preview/LOCAL_ONLY_IPHONE_GATE_RECEIPT.json",
            "/LOCAL_ONLY_IPHONE_GATE_RECEIPT.json",
            "/operator-preview/vendor/mediapipe/models/hand_landmarker.task",
            "/operator-preview/vendor/mediapipe/wasm/vision_wasm_internal.wasm",
            "/operator-preview/../_headers", "/operator-preview/%2e%2e/_headers",
            "/operator-preview//verify.html", "/operator-preview/",
            "/operator-preview/%76erify.html", "/operator-preview/verify%2Ejs",
            "/nonexistent", "//operator-preview/verify.html",
        ]
        with running_server(self.site) as port:
            for method in ("GET", "HEAD"):
                for path in forbidden:
                    with self.subTest(path=path, method=method):
                        code, headers, body = request(port, method, path)
                        self.assertEqual(code, 404, (method, path))
                        self.assertIn("no-store", headers["Cache-Control"])
                        self.assertNotIn(b"GitHub_TOKEN", body)
            code, _, _ = request(port, "POST", "/operator-preview/index.html")
            self.assertNotEqual(code, 200)

    def test_staged_site_rejects_extra_file_or_symlink(self):
        with tempfile.TemporaryDirectory(prefix="animate-host-extra-") as d:
            from shutil import copytree
            root = Path(d) / "site"
            copytree(self.site, root)
            (root / ".env").write_text("NO SECRET")
            with self.assertRaisesRegex(ValueError, "unexpected"):
                make_handler(root)
            (root / ".env").unlink()
            (root / "shortcut").symlink_to(root / "index.html")
            with self.assertRaisesRegex(ValueError, "symlinked"):
                make_handler(root)

    def test_launch_not_permitted_outside_real_selected_codespace(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "Requires GitHub Codespaces"):
                assert_real_codespace()
        codespace = {
            "CODESPACES": "true",
            "CODESPACE_NAME": "synthetic",
            "GITHUB_REPOSITORY": "other/repo",
            "GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN": "app.github.dev",
        }
        with patch.dict(os.environ, codespace, clear=True):
            with self.assertRaisesRegex(ValueError, "Requires GitHub Codespaces"):
                assert_real_codespace()

    def test_verifier_runs_against_staged_server_in_webkit_fixture(self):
        # This test case is also covered end-to-end in separate Playwright CI
        # on the same served files; no real Codespace is opened in CI.
        js = (self.site / "operator-preview" / "verify.js").read_bytes()
        self.assertIn(b"crypto.subtle.digest", js)
        self.assertIn(b"expectedSha256", js)
        self.assertNotIn(b"getUserMedia(", js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
