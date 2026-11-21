#!/usr/bin/env python3
"""Offline, zero-network security tests for a future owner-approved HTTPS preview."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_hosted_preview import (
    AuditError, Evidence, FORBIDDEN_PATHS, ALTERNATE_PATHS, PROBE_SUFFIX, audit_responses,
    check_headers, validate_origin, validated_candidate,
)
from build_baseline_preview import build


NAMES = ("index.html", "core.js", "foreground.js",
         "hand_ml.js", "app.js", "styles.css")
EXPECTED = {"/" + n: ("reviewed-bytes:" + n).encode() for n in NAMES}
HEADERS = {
    "content-security-policy": (
        "default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; "
        "style-src 'self'; img-src 'self' data:; connect-src 'self'; "
        "object-src 'none'; frame-ancestors 'none'"
    ),
    "permissions-policy": "camera=(self), microphone=(), geolocation=(), payment=()",
    "x-frame-options": "DENY",
    "cross-origin-resource-policy": "same-origin",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "cache-control": "private, no-store",
    "strict-transport-security": "max-age=86400; includeSubDomains",
}


def fixture(changes=None):
    changes = changes or {}
    def fetch(method, path, authorized):
        key = (method, path, authorized)
        if key in changes:
            return changes[key]
        if method == "POST":
            return Evidence(405, HEADERS, b"")
        if path in FORBIDDEN_PATHS:
            return Evidence(404, HEADERS, b"")
        if method == "HEAD":
            return Evidence(403 if not authorized else 405, HEADERS, b"")
        if path in ALTERNATE_PATHS or path.endswith(PROBE_SUFFIX):
            return Evidence(404, HEADERS, b"")
        if not authorized:
            return Evidence(403, HEADERS, b"")
        if path == "/":
            return Evidence(200, HEADERS, EXPECTED["/index.html"])
        if path in EXPECTED:
            return Evidence(200, HEADERS, EXPECTED[path])
        raise AssertionError("Unexpected request " + repr(key))
    return fetch


class PreviewAuditTests(unittest.TestCase):
    def test_success_is_technical_only_and_requires_all_assets(self):
        report = audit_responses(EXPECTED, fixture())
        self.assertEqual(report["technicalPreflight"], "PASS")
        self.assertEqual(report["checkedStaticFiles"], 6)
        self.assertIs(report["deploymentApproved"], False)
        self.assertIs(report["privacyOperatorApproved"], False)
        self.assertIs(report["physicalIphoneVerified"], False)

    def test_rejects_unprotected_default_root(self):
        changes = {("GET", "/", False): Evidence(200, HEADERS, EXPECTED["/index.html"])}
        with self.assertRaisesRegex(AuditError, "Unauthorised or alternate request"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_root_rewrite_to_unreviewed_bytes(self):
        changes = {("GET", "/", True): Evidence(200, HEADERS, b"unexpected HTML")}
        with self.assertRaisesRegex(AuditError, "reviewed landing page"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_head_bypass_on_script(self):
        changes = {("HEAD", "/app.js", False): Evidence(200, HEADERS, b"")}
        with self.assertRaisesRegex(AuditError, "Unauthorised or alternate request"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_asset_query_parameter_auth_bypass(self):
        changes = {
            ("GET", "/app.js" + PROBE_SUFFIX, False):
                Evidence(200, HEADERS, EXPECTED["/app.js"])
        }
        with self.assertRaisesRegex(AuditError, "Unauthorised or alternate request"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_default_document_query_bypass(self):
        changes = {
            ("GET", "/" + PROBE_SUFFIX, False):
                Evidence(200, HEADERS, EXPECTED["/index.html"])
        }
        with self.assertRaisesRegex(AuditError, "Unauthorised or alternate request"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_percent_encoded_path_bypass(self):
        changes = {
            ("GET", "/%69ndex.html", False):
                Evidence(200, HEADERS, EXPECTED["/index.html"])
        }
        with self.assertRaisesRegex(AuditError, "Unauthorised or alternate request"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_alias_redirect_as_unverified_access(self):
        changes = {("GET", "/app%2Ejs", False): Evidence(302, {"location": "/login"}, b"")}
        with self.assertRaisesRegex(AuditError, "Unauthorised or alternate request"):
            audit_responses(EXPECTED, fixture(changes))

    def test_allows_unimplemented_head_and_missing_safe_aliases(self):
        changes = {("HEAD", "/app.js", False): Evidence(405, HEADERS, b""),
                   ("GET", "/%69ndex.html", False): Evidence(404, HEADERS, b"")}
        self.assertEqual(audit_responses(EXPECTED, fixture(changes))["technicalPreflight"], "PASS")

    def test_rejects_public_preview_with_no_authentication(self):
        changes = {("GET", "/index.html", False): Evidence(200, HEADERS, EXPECTED["/index.html"])}
        with self.assertRaisesRegex(AuditError, "Unauthorised or alternate request"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_authentication_on_html_only(self):
        changes = {("GET", "/styles.css", False): Evidence(200, HEADERS, EXPECTED["/styles.css"])}
        with self.assertRaisesRegex(AuditError, "Unauthorised or alternate request"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_auth_redirect_as_unverified_not_access_proof(self):
        changes = {("GET", "/index.html", False): Evidence(302, {"location": "/login"}, b"")}
        with self.assertRaisesRegex(AuditError, "redirected"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_modified_script(self):
        changes = {("GET", "/app.js", True): Evidence(200, HEADERS, b"tampered app")}
        with self.assertRaisesRegex(AuditError, "differs from reviewed"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_unavailable_authenticated_asset(self):
        changes = {("GET", "/core.js", True): Evidence(404, HEADERS, b"")}
        with self.assertRaisesRegex(AuditError, "Authenticated static file"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_frame_embedding(self):
        headers = dict(HEADERS)
        headers["content-security-policy"] = "default-src 'none'; script-src 'self'; connect-src 'self'"
        changes = {("GET", "/index.html", True): Evidence(200, headers, EXPECTED["/index.html"])}
        with self.assertRaisesRegex(AuditError, "CSP"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_wide_cors(self):
        headers = dict(HEADERS)
        headers["access-control-allow-origin"] = "*"
        changes = {("GET", "/index.html", True): Evidence(200, headers, EXPECTED["/index.html"])}
        with self.assertRaisesRegex(AuditError, "CORS"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_nonprivate_cache(self):
        headers = dict(HEADERS)
        headers["cache-control"] = "public, max-age=31536000"
        changes = {("GET", "/index.html", True): Evidence(200, headers, EXPECTED["/index.html"])}
        with self.assertRaisesRegex(AuditError, "cached"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_short_hsts(self):
        headers = dict(HEADERS)
        headers["strict-transport-security"] = "max-age=30"
        changes = {("GET", "/index.html", True): Evidence(200, headers, EXPECTED["/index.html"])}
        with self.assertRaisesRegex(AuditError, "HSTS"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_unnecessary_sensor_permission(self):
        headers = dict(HEADERS)
        headers["permissions-policy"] = "camera=*, microphone=*, geolocation=*"
        changes = {("GET", "/index.html", True): Evidence(200, headers, EXPECTED["/index.html"])}
        with self.assertRaisesRegex(AuditError, "Permissions"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_hand_ml_asset_returning_200(self):
        path = FORBIDDEN_PATHS[0]
        changes = {("GET", path, True): Evidence(200, HEADERS, b"model")}
        with self.assertRaisesRegex(AuditError, "exposes"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_public_model_when_signed_in_users_are_blocked(self):
        path = FORBIDDEN_PATHS[0]
        changes = {("GET", path, False): Evidence(200, HEADERS, b"accidentally public model")}
        with self.assertRaisesRegex(AuditError, "unauthorised visitor"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_public_manifest_when_signed_in_users_are_blocked(self):
        changes = {("GET", "/MANIFEST.json", False): Evidence(200, HEADERS, b"{}")}
        with self.assertRaisesRegex(AuditError, "unauthorised visitor"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_public_manifest(self):
        changes = {("GET", "/MANIFEST.json", True): Evidence(200, HEADERS, b"{}")}
        with self.assertRaisesRegex(AuditError, "exposes"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_report_post_endpoint(self):
        changes = {("POST", "/", True): Evidence(201, HEADERS, b"accepted")}
        with self.assertRaisesRegex(AuditError, "uploads"):
            audit_responses(EXPECTED, fixture(changes))

    def test_rejects_incorrect_static_inventory(self):
        with self.assertRaisesRegex(AuditError, "six-file"):
            audit_responses({"/index.html": b"only one"}, fixture())

    def test_hostname_must_be_public_https_origin_without_url_secrets(self):
        self.assertEqual(validate_origin("https://preview.customer.example.com"), "preview.customer.example.com")
        for unsafe in ("http://preview.customer.com", "https://preview.customer.com/secret",
                       "https://preview.customer.com/?key=123", "https://user:password@preview.customer.com",
                       "https://127.0.0.1", "https://localhost", "https://test.local",
                       "https://preview.customer.com:8443", "https://preview.customer.com/#key"):
            with self.subTest(unsafe=unsafe):
                with self.assertRaises(AuditError):
                    validate_origin(unsafe)

    def test_real_builder_manifest_and_source_commit_are_required(self):
        with tempfile.TemporaryDirectory(prefix="animate-hosted-audit-offline-") as tmp:
            from json import loads, dumps
            folder = Path(tmp) / "candidate"
            build(folder)
            static = validated_candidate(folder / "site")
            self.assertEqual(set(static), set(EXPECTED))
            manifest_file = folder / "MANIFEST.json"
            manifest = loads(manifest_file.read_text())
            manifest["sourceCommit"] = "0" * 40
            manifest_file.write_text(dumps(manifest))
            with self.assertRaises(ValueError):
                validated_candidate(folder / "site")


if __name__ == "__main__":
    unittest.main(verbosity=2)
