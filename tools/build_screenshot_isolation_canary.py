#!/usr/bin/env python3
"""Generate an offline non-app canary to test Netlify deployment screenshot paths.

A neutral root index must be the *only* page visible in the provider's
unauthenticated auto-generated deployment thumbnail. The test marker is confined
to /private-canary/ so screenshot generation can be audited without exposing IP.
This is NOT proof that host-generated images cannot leak other paths.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import tempfile
import zipfile

from build_host_canary import harmless_files
from build_zero_cost_preview import MAX_TOTAL_BYTES, headers_text
from vendor_hand_model import ROOT, SITE_FILES

ZIP_NAME = "hosting-thumbnail-isolation-canary.zip"
RECEIPT_NAME = "LOCAL_ONLY_THUMBNAIL_TEST_RECEIPT.json"
PRIVATE_PREFIX = "private-canary/"
SAFE_ROOT = (
    b"<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
    b"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
    b"<title>Neutral hosting test</title></head>"
    b"<body><h1>Neutral hosting test</h1>"
    b"<p>No application or private information appears on this landing page.</p>"
    b"</body></html>\n"
)
EXPECTED = frozenset({"index.html", "_headers"} | {
    PRIVATE_PREFIX + name for name in SITE_FILES
})


def make_assets(marker):
    private = harmless_files(marker)
    assets = {
        "index.html": SAFE_ROOT,
        "_headers": headers_text().encode("utf-8"),
    }
    for name in SITE_FILES:
        assets[PRIVATE_PREFIX + name] = private[name]
    if set(assets) != EXPECTED:
        raise ValueError("Unexpected assets")
    if marker.encode() in assets["index.html"] or b"<script" in assets["index.html"]:
        raise ValueError("Landing page must have no scripts or canary marker")
    return assets


def validate_archive(path, assets):
    expected_hashes = {
        name: hashlib.sha256(data).hexdigest() for name, data in assets.items()
    }
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_TOTAL_BYTES:
        raise ValueError("Unsafe thumbnail-test archive")
    with zipfile.ZipFile(path) as bundle:
        members = bundle.infolist()
        if len(members) != len(EXPECTED) or {x.filename for x in members} != EXPECTED:
            raise ValueError("Unexpected thumbnail archive contents")
        if sum(x.file_size for x in members) > MAX_TOTAL_BYTES:
            raise ValueError("Oversized thumbnail archive contents")
        for member in members:
            if member.is_dir() or stat.S_ISLNK(member.external_attr >> 16):
                raise ValueError("Unsafe archive member type")
            data = bundle.read(member)
            if hashlib.sha256(data).hexdigest() != expected_hashes[member.filename]:
                raise ValueError("Thumbnail archive hash mismatch: " + member.filename)
    return expected_hashes


def build_thumbnail_test(output_dir):
    dest = Path(output_dir).resolve(strict=False)
    repository = ROOT.resolve()
    if dest == repository or dest.is_relative_to(repository) or repository.is_relative_to(dest):
        raise ValueError("Thumbnail-test output must be outside the source repository")
    if not dest.parent.is_dir() or dest.exists() or dest.is_symlink():
        raise ValueError("Thumbnail-test output must be a new directory")
    temp = Path(tempfile.mkdtemp(prefix=".animate-thumbnail-test-", dir=dest.parent))
    try:
        marker = secrets.token_hex(16)
        assets = make_assets(marker)
        archive = temp / ZIP_NAME
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for name, data in sorted(assets.items()):
                bundle.writestr(name, data)
        hashes = validate_archive(archive, assets)
        receipt = {
            "kind": "OFFLINE_UNDEPLOYED_SCREENSHOT_EXPOSURE_CANARY",
            "canaryMarker": marker,
            "zipFile": ZIP_NAME,
            "zipSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "assetSha256": hashes,
            "landingPageHasMarker": False,
            "privateTestPage": "/private-canary/",
            "privateTestPageHasMarker": True,
            "modelPresent": False,
            "appCodePresent": False,
            "cameraPresent": False,
            "participantDataPresent": False,
            "deploymentPerformed": False,
            "screenshotConfidentialityVerified": False,
            "hostingApprovedForAnimate": False,
            "costApproved": False,
            "warning": (
                "This canary is neither ANIMATE nor secure storage. A provider may capture "
                "any route. A screenshot showing the neutral homepage is a partial "
                "mitigation, NOT proof of screenshot confidentiality or production safety."
            ),
        }
        (temp / RECEIPT_NAME).write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(temp, dest)
        return receipt
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = build_thumbnail_test(args.output_dir)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        raise SystemExit("BLOCKED: " + str(exc))
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print("PASS: local thumbnail-test ZIP only. No deployment or private content.")


if __name__ == "__main__":
    main()
