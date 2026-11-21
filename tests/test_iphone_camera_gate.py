#!/usr/bin/env python3
"""Offline acceptance and adversarial tamper tests for in-Safari camera gate."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_iphone_camera_gate as gate
from build_operator_preview import EXPECTED as BASE_FILES, PREFIX
from build_zero_cost_preview import headers_text
from build_screenshot_isolation_canary import SAFE_ROOT


class CameraSecurityGateTests(unittest.TestCase):
    def test_verified_camera_gate_contains_only_source_app_and_sri_checker(self):
        with tempfile.TemporaryDirectory(prefix="animate-camera-gate-unit-") as d:
            output = Path(d) / "candidate"
            receipt = gate.build_camera_gate(output)
            self.assertEqual(set(x.name for x in output.iterdir()),
                             {gate.ZIP_NAME, gate.RECEIPT_NAME})
            self.assertEqual(receipt["kind"], "OFFLINE_UNDEPLOYED_VERIFIED_IPHONE_CAMERA_GATE")
            self.assertEqual(receipt["verificationPath"], "/operator-preview/verify.html")
            self.assertEqual(len(receipt["sourceCommit"]), 40)
            for flag in ("modelPresent", "participantDataPresent", "hostingAuthBuiltIn",
                         "hostingScreenshotConfidentialityProved", "authenticatedLiveAuditCompleted",
                         "physicalIphoneCameraTested", "deploymentPerformed", "deploymentApproved",
                         "spendingApproved"):
                self.assertIs(receipt[flag], False, flag)
            archive = output / gate.ZIP_NAME
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), receipt["zipSha256"])
            self.assertTrue(gate.validate_archive(archive, receipt["fileSha256"]))
            with zipfile.ZipFile(archive) as bundle:
                files = {name: bundle.read(name) for name in bundle.namelist()}
            self.assertEqual(set(files), gate.EXPECTED)
            self.assertEqual(gate.EXPECTED, set(BASE_FILES) | {gate.VERIFY_HTML, gate.VERIFY_JS})
            self.assertNotIn(gate.RECEIPT_NAME, files)
            self.assertEqual(files["index.html"], SAFE_ROOT)
            self.assertEqual(files["_headers"], headers_text().encode())
            self.assertIn(b'id="baselineDisclosure"', files[PREFIX + "index.html"])
            self.assertNotIn(b'<option value="hand"', files[PREFIX + "index.html"])
            self.assertIn(b'id="camera"', files[PREFIX + "index.html"])
            self.assertIn(b'id="sample"', files[PREFIX + "index.html"])
            self.assertIn(b'getUserMedia', files[PREFIX + "app.js"])
            self.assertIn(b'crypto.subtle.digest', files[gate.VERIFY_JS])
            self.assertNotIn(b'getUserMedia(', files[gate.VERIFY_JS])
            self.assertNotIn(b'localStorage', files[gate.VERIFY_JS])
            self.assertNotIn(b'__EXPECTED_APP_HASHES__', files[gate.VERIFY_JS])
            self.assertNotIn(b'__EXPECTED_HEADERS__', files[gate.VERIFY_JS])
            sri = ("sha384-" + base64.b64encode(
                hashlib.sha384(files[gate.VERIFY_JS]).digest()).decode()).encode()
            self.assertIn(sri, files[gate.VERIFY_HTML])
            self.assertEqual(receipt["verifierSriSha384"], sri.decode()[7:])
            self.assertEqual(set(receipt["appSha256"]), set(BASE_FILES) - {"_headers"})
            for path, data in files.items():
                self.assertEqual(hashlib.sha256(data).hexdigest(), receipt["fileSha256"][path])
            with self.assertRaisesRegex(ValueError, "new"):
                gate.build_camera_gate(output)
            with self.assertRaisesRegex(ValueError, "outside"):
                gate.build_camera_gate(ROOT / "unsafe-camera-preview")

    def test_tampering_must_be_rejected(self):
        with tempfile.TemporaryDirectory(prefix="animate-camera-gate-unit-") as d:
            r = gate.build_camera_gate(Path(d) / "candidate")
            with zipfile.ZipFile(Path(d) / "candidate" / gate.ZIP_NAME) as zipped:
                files = {name: zipped.read(name) for name in zipped.namelist()}
            tampered = Path(d) / "altered.zip"

            def write(replaced=None, extra=None, duplicated=None):
                replaced = replaced or {}
                with zipfile.ZipFile(tampered, "w", zipfile.ZIP_DEFLATED) as bundle:
                    for name, data in files.items():
                        bundle.writestr(name, replaced.get(name, data))
                    if extra:
                        bundle.writestr(*extra)
                    if duplicated:
                        bundle.writestr(duplicated, files[duplicated])

            write(replaced={PREFIX + "app.js": b"malicious app"})
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                gate.validate_archive(tampered, r["fileSha256"])
            write(replaced={gate.VERIFY_JS: b"malicious verifier"})
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                gate.validate_archive(tampered, r["fileSha256"])
            write(extra=(PREFIX + "vendor/mediapipe/models/hand_landmarker.task", b"fake model"))
            with self.assertRaisesRegex(ValueError, "extra or duplicate"):
                gate.validate_archive(tampered, r["fileSha256"])
            write(duplicated=gate.VERIFY_HTML)
            with self.assertRaisesRegex(ValueError, "extra or duplicate"):
                gate.validate_archive(tampered, r["fileSha256"])
            write(replaced={"index.html": b"PRIVATE HOME"})
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                gate.validate_archive(tampered, r["fileSha256"])
            with self.assertRaisesRegex(ValueError, "Invalid audited"):
                gate.validate_archive(Path(d) / "candidate" / gate.ZIP_NAME, {})

    def test_verifier_source_is_git_committed(self):
        with tempfile.TemporaryDirectory(prefix="animate-camera-gate-unit-") as d:
            r = gate.build_camera_gate(Path(d) / "candidate")
            changed = Path(d) / "evil.js"
            changed.write_text("console.log('unreviewed injection')")
            with patch.object(gate, "TEMPLATE", changed):
                with self.assertRaisesRegex(ValueError, "unreviewed"):
                    gate.assert_committed_template(r["sourceCommit"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
