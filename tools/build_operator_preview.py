#!/usr/bin/env python3
"""Build a source-verified, no-ML, owner-only *candidate* with neutral root.

No hosting API, public release, upload, purchase, ML/model files or personal
data. A Netlify Private configuration, not this archive, performs authentication.
A publicly readable deployment screenshot may still exist on the hosting CDN.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import zipfile

from build_baseline_preview import build as build_baseline, validate_site
from build_zero_cost_preview import MAX_TOTAL_BYTES, headers_text
from build_screenshot_isolation_canary import SAFE_ROOT
from vendor_hand_model import ROOT, SITE_FILES

ZIP_NAME = "animate-operator-only-preview.zip"
RECEIPT_NAME = "LOCAL_ONLY_OPERATOR_PREVIEW_RECEIPT.json"
PREFIX = "operator-preview/"
APP_ENTRY = "/" + PREFIX + "index.html?debug=1"
EXPECTED = frozenset({"index.html", "_headers"} | {PREFIX + f for f in SITE_FILES})


def approved_bytes(baseline_site):
    """Use only exact, provenance-verified baseline assets, with neutral root."""
    if not validate_site(baseline_site):
        raise ValueError("Unverified model-free baseline")
    content = {"index.html": SAFE_ROOT, "_headers": headers_text().encode("utf-8")}
    for name in SITE_FILES:
        content[PREFIX + name] = (baseline_site / name).read_bytes()
    if set(content) != EXPECTED:
        raise ValueError("Unexpected operator preview member")
    if (b"ANIMATE" in content["index.html"] or
            b"operator-preview" in content["index.html"] or
            b"<script" in content["index.html"]):
        raise ValueError("Root cannot disclose app path, app name, or load scripts")
    html = content[PREFIX + "index.html"]
    if b'id="baselineDisclosure"' not in html or b'<option value="hand"' in html:
        raise ValueError("Only disclosed no-ML application may be staged")
    return content


def check_zip(archive_path, digests):
    """Exact eight regular files with proven, bounded contents and headers."""
    archive_path = Path(archive_path)
    if (not archive_path.is_file() or archive_path.is_symlink() or
            archive_path.stat().st_size > MAX_TOTAL_BYTES or set(digests) != EXPECTED):
        raise ValueError("Invalid operator preview ZIP or manifest")
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        if len(members) != len(EXPECTED) or {member.filename for member in members} != EXPECTED:
            raise ValueError("ZIP has missing/duplicate/unapproved members")
        if sum(member.file_size for member in members) > MAX_TOTAL_BYTES:
            raise ValueError("ZIP uncompressed contents exceed size limit")
        for member in members:
            if member.is_dir() or stat.S_ISLNK(member.external_attr >> 16):
                raise ValueError("ZIP includes link or directory")
            content = archive.read(member)
            if hashlib.sha256(content).hexdigest() != digests[member.filename]:
                raise ValueError("Operator preview member does not match hash: " + member.filename)
        if archive.read("index.html") != SAFE_ROOT:
            raise ValueError("Root is not the reviewed neutral landing page")
        if archive.read("_headers") != headers_text().encode("utf-8"):
            raise ValueError("Netlify security headers diverge from reviewed policy")
        for member in members:
            path = member.filename.lower()
            if any(part in path for part in (
                "vendor/", ".task", ".wasm", ".env", "ledger", "manifest", "receipt",
                "participant", ".map"
            )):
                raise ValueError("Forbidden private/model content: " + member.filename)
    return True


def build_operator_preview(output_dir):
    output = Path(output_dir).resolve(strict=False)
    repository = ROOT.resolve()
    if output == repository or output.is_relative_to(repository) or repository.is_relative_to(output):
        raise ValueError("Output must be outside Git checkout")
    if not output.parent.is_dir() or output.exists() or output.is_symlink():
        raise ValueError("Output directory must be new with an existing parent")
    temp = Path(tempfile.mkdtemp(prefix=".animate-owner-preview-", dir=output.parent))
    try:
        baseline_dir = temp / "baseline"
        manifest = build_baseline(baseline_dir)
        content = approved_bytes(baseline_dir / "site")
        digests = {name: hashlib.sha256(data).hexdigest() for name, data in content.items()}
        zip_path = temp / ZIP_NAME
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as bundle:
            for name, data in sorted(content.items()):
                bundle.writestr(name, data)
        check_zip(zip_path, digests)
        receipt = {
            "kind": "OFFLINE_UNDEPLOYED_MODEL_FREE_OWNER_PREVIEW",
            "sourceCommit": manifest["sourceCommit"],
            "zipFile": ZIP_NAME,
            "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
            "fileSha256": digests,
            "operatorEntry": APP_ENTRY,
            "landingPageSha256": digests["index.html"],
            "containsMediaPipeAssets": False,
            "containsParticipantData": False,
            "containsPersonalSecrets": False,
            "containsServerAuthentication": False,
            "ownerOnlyHostingVerified": False,
            "screenshotConfidentialityVerified": False,
            "physicalIphoneTested": False,
            "deploymentPerformed": False,
            "commercialDemandVerified": False,
            "deploymentApproved": False,
            "extraSpendingApproved": False,
            "requiredGates": [
                "Use ONLY existing Free/Private team-SSO Netlify project; never Make public",
                "Confirm signed-out requests deny root AND every nested app asset",
                "Confirm authenticated app has exact reviewed SHA-256 bytes and headers",
                "Do not treat neutral deploy screenshot as confidential image storage",
                "Inspect provider site/screenshot derivative risk before owner camera trials",
                "Do not recruit anyone; keep all camera frames locally on the operator's iPhone",
                "Stop/delete deployment and clear local Safari records after authorised tests",
            ],
            "warning": (
                "Not an authentication system and not approved for deployment. "
                "The public deploy screenshot URL remains unprotected by Netlify SSO; "
                "all served app code is already in a public repository, but the preview "
                "must contain no secret keys, private data or unlicensed MediaPipe binaries."
            ),
        }
        (temp / RECEIPT_NAME).write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        shutil.rmtree(baseline_dir)
        os.replace(temp, output)
        return receipt
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = build_operator_preview(args.output_dir)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise SystemExit("BLOCKED: " + str(error))
    print(json.dumps(result, indent=2, sort_keys=True))
    print("PASS: offline owner preview ZIP only; no upload, deployment or spending")


if __name__ == "__main__":
    main()
