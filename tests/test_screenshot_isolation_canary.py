#!/usr/bin/env python3
"""No-network checks for screenshot side-channel canary packaging."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_screenshot_isolation_canary import (
    EXPECTED, PRIVATE_PREFIX, RECEIPT_NAME, ZIP_NAME, SAFE_ROOT,
    build_thumbnail_test, make_assets, validate_archive,
)


class ThumbnailIsolationTests(unittest.TestCase):
    def test_neutral_root_keeps_fake_private_marker_in_separate_path_only(self):
        with tempfile.TemporaryDirectory(prefix="animate-thumbnail-gate-") as d:
            out = Path(d) / "package"
            receipt = build_thumbnail_test(out)
            self.assertEqual({p.name for p in out.iterdir()}, {ZIP_NAME, RECEIPT_NAME})
            self.assertEqual(receipt["kind"], "OFFLINE_UNDEPLOYED_SCREENSHOT_EXPOSURE_CANARY")
            self.assertEqual(receipt["privateTestPage"], "/private-canary/")
            for key in ("landingPageHasMarker", "modelPresent", "appCodePresent",
                        "cameraPresent", "participantDataPresent", "deploymentPerformed",
                        "screenshotConfidentialityVerified", "hostingApprovedForAnimate",
                        "costApproved"):
                self.assertIs(receipt[key], False, key)
            self.assertIs(receipt["privateTestPageHasMarker"], True)
            archive = out / ZIP_NAME
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), receipt["zipSha256"])
            with zipfile.ZipFile(archive) as bundle:
                files = {n: bundle.read(n) for n in bundle.namelist()}
            self.assertEqual(set(files), EXPECTED)
            self.assertNotIn(RECEIPT_NAME, files)
            marker = receipt["canaryMarker"].encode()
            self.assertEqual(files["index.html"], SAFE_ROOT)
            self.assertNotIn(marker, files["index.html"])
            self.assertNotIn(b"<script", files["index.html"])
            self.assertNotIn(b"camera", files["index.html"].lower())
            self.assertIn(marker, files[PRIVATE_PREFIX + "index.html"])
            self.assertIn(marker, files[PRIVATE_PREFIX + "app.js"])
            self.assertIn(marker, files[PRIVATE_PREFIX + "core.js"])
            for name, body in files.items():
                self.assertEqual(hashlib.sha256(body).hexdigest(), receipt["assetSha256"][name])
                self.assertNotIn(b"getUserMedia", body)
                self.assertNotIn(b"hand_landmarker.task", body)
            self.assertEqual(validate_archive(archive, files), receipt["assetSha256"])
            with self.assertRaisesRegex(ValueError, "new directory"):
                build_thumbnail_test(out)
            with self.assertRaisesRegex(ValueError, "outside"):
                build_thumbnail_test(ROOT / "unsafe-screenshot-output")

    def test_fails_when_private_marker_enters_landing_page(self):
        files = make_assets("a" * 32)
        self.assertNotIn(b"a" * 32, files["index.html"])
        self.assertIn(b"a" * 32, files[PRIVATE_PREFIX + "index.html"])
        self.assertNotEqual(files["index.html"], files[PRIVATE_PREFIX + "index.html"])

    def test_independent_builds_generate_independent_markers(self):
        with tempfile.TemporaryDirectory(prefix="animate-thumbnail-gate-") as d:
            a = build_thumbnail_test(Path(d) / "a")
            b = build_thumbnail_test(Path(d) / "b")
            self.assertNotEqual(a["canaryMarker"], b["canaryMarker"])
            self.assertNotEqual(a["zipSha256"], b["zipSha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
