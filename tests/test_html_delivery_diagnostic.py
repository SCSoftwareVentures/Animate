#!/usr/bin/env python3
"""Offline source and tamper tests for the signed-in Safari HTML diff diagnostic."""
import base64
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_html_delivery_diagnostic import (
    build_html_diagnostic, validate_archive,
    ZIP_NAME, RECEIPT_NAME, EXPECTED, DIAG_HTML, DIAG_JS
)
from build_iphone_camera_gate import (
    build_camera_gate, ZIP_NAME as CAMERA_ZIP,
    EXPECTED as CAMERA_FILES
)
from build_screenshot_isolation_canary import SAFE_ROOT
from build_zero_cost_preview import headers_text


class DeliveryDiagnosticTests(unittest.TestCase):
    def test_exact_original_preview_and_only_two_extra_diagnostic_assets(self):
        with tempfile.TemporaryDirectory(prefix="animate-html-forensics-") as d:
            first = Path(d) / "diagnostic"
            prior = Path(d) / "approved"
            receipt = build_html_diagnostic(first)
            build_camera_gate(prior)
            with zipfile.ZipFile(first / ZIP_NAME) as z:
                parts = {name: z.read(name) for name in z.namelist()}
            with zipfile.ZipFile(prior / CAMERA_ZIP) as z:
                baseline = {name: z.read(name) for name in z.namelist()}
            self.assertEqual(set(parts), EXPECTED)
            self.assertEqual(set(parts) - set(baseline), {DIAG_HTML, DIAG_JS})
            for name, expected in baseline.items():
                self.assertEqual(parts[name], expected, name)
            self.assertEqual(parts["index.html"], SAFE_ROOT)
            self.assertEqual(parts["_headers"], headers_text().encode("utf-8"))
            self.assertEqual(receipt["kind"], "OFFLINE_UNDEPLOYED_ANIMATE_HTML_DIFF_DIAGNOSTIC")
            self.assertEqual(receipt["diagnosticPath"], "/operator-preview/inspect.html")
            self.assertIs(receipt["approvedAppFilesUnchanged"], True)
            self.assertIs(receipt["cameraGateRemainsBlocked"], True)
            self.assertIs(receipt["deployed"], False)
            self.assertIs(receipt["spendingApproved"], False)
            self.assertTrue(validate_archive(first / ZIP_NAME, receipt["fileSha256"]))
            self.assertEqual(hashlib.sha256((first / ZIP_NAME).read_bytes()).hexdigest(),
                             receipt["zipSha256"])
            self.assertEqual(set(x.name for x in first.iterdir()), {ZIP_NAME, RECEIPT_NAME})
            script = parts[DIAG_JS]
            self.assertIn(base64.b64encode(parts["index.html"]), script)
            self.assertIn(base64.b64encode(parts["operator-preview/index.html"]), script)
            self.assertIn(b"DIAGNOSTIC_ONLY_CAMERA_NOT_CLEARED", script)
            self.assertNotIn(b"__EXPECTED_HTML_BASE64__", script)
            self.assertNotIn(b"getUserMedia(", script)
            self.assertNotIn(b"localStorage", script)
            self.assertNotIn(b"sendBeacon", script)
            self.assertNotIn(RECEIPT_NAME, parts)
            with self.assertRaisesRegex(ValueError, "new"):
                build_html_diagnostic(first)
            with self.assertRaisesRegex(ValueError, "outside"):
                build_html_diagnostic(ROOT / "forbidden-diagnostic")

    def test_archive_tamper_extra_and_duplicate_member_rejected(self):
        with tempfile.TemporaryDirectory(prefix="animate-html-forensics-") as d:
            receipt = build_html_diagnostic(Path(d) / "original")
            with zipfile.ZipFile(Path(d) / "original" / ZIP_NAME) as z:
                parts = {name: z.read(name) for name in z.namelist()}
            altered = Path(d) / "altered.zip"

            def pack(changed=None, extra=None, duplicate=None):
                with zipfile.ZipFile(altered, "w", zipfile.ZIP_DEFLATED) as z:
                    for name, data in parts.items():
                        z.writestr(name, (changed or {}).get(name, data))
                    if extra:
                        z.writestr(*extra)
                    if duplicate:
                        z.writestr(duplicate, parts[duplicate])

            pack(changed={DIAG_JS: b"unreviewed diagnostics"})
            with self.assertRaisesRegex(ValueError, "file hash mismatch"):
                validate_archive(altered, receipt["fileSha256"])
            pack(changed={"index.html": b"private root"})
            with self.assertRaisesRegex(ValueError, "file hash mismatch"):
                validate_archive(altered, receipt["fileSha256"])
            pack(extra=("operator-preview/vendor/unauthorized.task", b"x"))
            with self.assertRaisesRegex(ValueError, "Unapproved"):
                validate_archive(altered, receipt["fileSha256"])
            pack(duplicate=DIAG_HTML)
            with self.assertRaisesRegex(ValueError, "Unapproved"):
                validate_archive(altered, receipt["fileSha256"])
            with self.assertRaisesRegex(ValueError, "Invalid diagnostic archive"):
                validate_archive(Path(d) / "original" / ZIP_NAME, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
