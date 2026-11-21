#!/usr/bin/env python3
"""Offline fail-closed tests: the provider canary must not contain ANIMATE."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_host_canary import RECEIPT_NAME, ZIP_NAME, build_canary, harmless_files
from build_zero_cost_preview import EXPECTED_ASSETS, checked_archive, headers_text


class HostCanaryTests(unittest.TestCase):
    def test_package_is_innocuous_private_receipt_and_no_deployment(self):
        with tempfile.TemporaryDirectory(prefix="animate-host-canary-") as temp:
            output = Path(temp) / "candidate"
            receipt = build_canary(output)
            self.assertEqual({p.name for p in output.iterdir()}, {ZIP_NAME, RECEIPT_NAME})
            self.assertEqual(receipt["kind"], "OFFLINE_UNDEPLOYED_HARMLESS_HOST_CANARY")
            for key in ("appCodePresent", "modelPresent", "participantDataPresent",
                        "deployed", "accessControlVerified", "costApproved",
                        "userResearchApproved"):
                self.assertIs(receipt[key], False, key)
            archive = output / ZIP_NAME
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), receipt["zipSha256"])
            self.assertTrue(checked_archive(archive, receipt["assetSha256"]))
            with zipfile.ZipFile(archive) as bundle:
                self.assertEqual(set(bundle.namelist()), EXPECTED_ASSETS)
                self.assertNotIn(RECEIPT_NAME, bundle.namelist())
                self.assertEqual(bundle.read("_headers"), headers_text().encode())
                for path in ("index.html", "core.js", "app.js"):
                    self.assertIn(receipt["canaryId"].encode(), bundle.read(path))
                for path in bundle.namelist():
                    data = bundle.read(path).lower()
                    for forbidden in (b"getusermedia", b"camera_ready", b"localstorage",
                                      b"hand_landmarker.task", b"<script>", b"animate-validation-v07"):
                        self.assertNotIn(forbidden, data, path)
            with self.assertRaisesRegex(ValueError, "new"):
                build_canary(output)
            with self.assertRaisesRegex(ValueError, "outside"):
                build_canary(ROOT / "unsafe-host-canary")

    def test_invalid_markers_are_refused(self):
        for marker in ("", "a" * 31, "g" * 32, "A" * 32, "a" * 33):
            with self.subTest(marker=marker):
                with self.assertRaises(ValueError):
                    harmless_files(marker)

    def test_two_builds_have_distinct_markers_and_receipts(self):
        with tempfile.TemporaryDirectory(prefix="animate-host-canary-") as temp:
            first = build_canary(Path(temp) / "a")
            second = build_canary(Path(temp) / "b")
            self.assertNotEqual(first["canaryId"], second["canaryId"])
            self.assertNotEqual(first["zipSha256"], second["zipSha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
