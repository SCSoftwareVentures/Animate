#!/usr/bin/env python3
"""Fail-closed, zero-network tests for ANIMATE owner-only nested preview."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_operator_preview import (
    APP_ENTRY, EXPECTED, PREFIX, RECEIPT_NAME, ZIP_NAME,
    SAFE_ROOT, build_operator_preview, check_zip,
)
from build_zero_cost_preview import headers_text
from vendor_hand_model import SITE_FILES, REVIEWED_LICENSE_SHA256


class OperatorPreviewTests(unittest.TestCase):
    def test_exact_no_model_preview_neutral_root_and_receipt_outside_zip(self):
        with tempfile.TemporaryDirectory(prefix="animate-owner-zip-test-") as temp:
            output = Path(temp) / "candidate"
            receipt = build_operator_preview(output)
            self.assertEqual({p.name for p in output.iterdir()}, {ZIP_NAME, RECEIPT_NAME})
            self.assertEqual(receipt["kind"], "OFFLINE_UNDEPLOYED_MODEL_FREE_OWNER_PREVIEW")
            self.assertEqual(receipt["operatorEntry"], APP_ENTRY)
            self.assertEqual(APP_ENTRY, "/operator-preview/index.html?debug=1")
            self.assertEqual(len(receipt["sourceCommit"]), 40)
            for name in ("containsMediaPipeAssets", "containsParticipantData",
                         "containsPersonalSecrets", "containsServerAuthentication",
                         "ownerOnlyHostingVerified", "screenshotConfidentialityVerified",
                         "physicalIphoneTested", "deploymentPerformed",
                         "commercialDemandVerified", "deploymentApproved",
                         "extraSpendingApproved"):
                self.assertIs(receipt[name], False, name)
            self.assertIsNone(REVIEWED_LICENSE_SHA256)
            archive_path = output / ZIP_NAME
            self.assertEqual(hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                             receipt["zipSha256"])
            self.assertTrue(check_zip(archive_path, receipt["fileSha256"]))
            with zipfile.ZipFile(archive_path) as bundle:
                assets = {name: bundle.read(name) for name in bundle.namelist()}
            self.assertEqual(set(assets), EXPECTED)
            self.assertEqual(assets["index.html"], SAFE_ROOT)
            self.assertEqual(assets["_headers"], headers_text().encode())
            self.assertNotIn(RECEIPT_NAME, assets)
            self.assertNotIn("MANIFEST.json", assets)
            self.assertEqual(
                {name[len(PREFIX):] for name in assets if name.startswith(PREFIX)},
                set(SITE_FILES))
            self.assertNotIn(b"ANIMATE", assets["index.html"])
            self.assertNotIn(b"operator-preview", assets["index.html"])
            self.assertNotIn(b"<script", assets["index.html"])
            self.assertIn(b'id="baselineDisclosure"', assets[PREFIX + "index.html"])
            self.assertIn(b"Hand ML is unavailable", assets[PREFIX + "index.html"])
            self.assertNotIn(b'<option value="hand"', assets[PREFIX + "index.html"])
            self.assertIn(b'id="camera"', assets[PREFIX + "index.html"])
            self.assertIn(b'id="sample"', assets[PREFIX + "index.html"])
            for name, data in assets.items():
                self.assertEqual(hashlib.sha256(data).hexdigest(),
                                 receipt["fileSha256"][name])
                self.assertNotIn(b"hand_landmarker.task", data)
            with self.assertRaisesRegex(ValueError, "new"):
                build_operator_preview(output)
            with self.assertRaisesRegex(ValueError, "outside"):
                build_operator_preview(ROOT / "forbidden-owner-preview")

    def test_rejects_zip_injection_tamper_missing_duplicate_and_manifest_drift(self):
        with tempfile.TemporaryDirectory(prefix="animate-owner-zip-test-") as temp:
            original = Path(temp) / "candidate"
            receipt = build_operator_preview(original)
            with zipfile.ZipFile(original / ZIP_NAME) as bundle:
                source = {name: bundle.read(name) for name in bundle.namelist()}
            tampered = Path(temp) / "tampered.zip"

            def rewrite(additional=None, replacements=None, duplicate=None):
                replacements = replacements or {}
                with zipfile.ZipFile(tampered, "w", zipfile.ZIP_DEFLATED) as bundle:
                    for name, data in source.items():
                        bundle.writestr(name, replacements.get(name, data))
                    if additional:
                        bundle.writestr(*additional)
                    if duplicate:
                        bundle.writestr(duplicate, source[duplicate])

            rewrite(replacements={PREFIX + "app.js": b"unapproved"})
            with self.assertRaisesRegex(ValueError, "does not match"):
                check_zip(tampered, receipt["fileSha256"])
            rewrite(additional=("operator-preview/vendor/model.task", b"binary"))
            with self.assertRaisesRegex(ValueError, "missing/duplicate/unapproved"):
                check_zip(tampered, receipt["fileSha256"])
            rewrite(duplicate="index.html")
            with self.assertRaisesRegex(ValueError, "missing/duplicate/unapproved"):
                check_zip(tampered, receipt["fileSha256"])
            rewrite(replacements={"index.html": b"SECRET: operator"})
            with self.assertRaisesRegex(ValueError, "does not match"):
                check_zip(tampered, receipt["fileSha256"])
            rewrite(replacements={"_headers": b"/*\n Access-Control-Allow-Origin: *\n"})
            with self.assertRaisesRegex(ValueError, "does not match"):
                check_zip(tampered, receipt["fileSha256"])
            altered_manifest = dict(receipt["fileSha256"])
            altered_manifest.pop("_headers")
            with self.assertRaisesRegex(ValueError, "Invalid operator"):
                check_zip(original / ZIP_NAME, altered_manifest)

    def test_each_candidate_exactly_source_verified_and_no_foreign_path(self):
        with tempfile.TemporaryDirectory(prefix="animate-owner-zip-test-") as temp:
            a = build_operator_preview(Path(temp) / "first")
            b = build_operator_preview(Path(temp) / "second")
            self.assertEqual(a["sourceCommit"], b["sourceCommit"])
            self.assertEqual(a["fileSha256"], b["fileSha256"])
            self.assertEqual(a["zipSha256"], b["zipSha256"])
            self.assertNotIn("http", a["operatorEntry"])
            self.assertIn("No", a["warning"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
