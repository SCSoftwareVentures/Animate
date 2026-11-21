#!/usr/bin/env python3
"""Build an offline, UNDEPLOYED no-ML ZIP for a potential Netlify Free private project.

The operator must independently verify a credit-based FREE plan with a fixed
hard limit AND a PRIVATE project BEFORE uploading the ZIP. This script
never contacts Netlify, requests payment, opens accounts or deploys.
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

from build_baseline_preview import build, validate_site
from serve_safari_https import SECURITY_HEADERS
from vendor_hand_model import ROOT, SITE_FILES

OUTPUT_NAME = "animate-model-free-private-preview.zip"
RECEIPT_NAME = "LOCAL_ONLY_BUILD_RECEIPT.json"
MAX_TOTAL_BYTES = 2 * 1024 * 1024
EXPECTED_ASSETS = frozenset(SITE_FILES | {"_headers"})


def headers_text():
    """Netlify static _headers directives; PRIVATE project access is provider-side."""
    headers = {
        **SECURITY_HEADERS,
        "Strict-Transport-Security": "max-age=86400",
    }
    if any("\n" in v or "\r" in v or not v for v in headers.values()):
        raise ValueError("Untrusted security-header value")
    return "/*\n" + "".join(f"  {name}: {value}\n" for name, value in headers.items())


def checked_archive(path, digests):
    """Only seven static, bounded regular files; no model or research evidence."""
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_TOTAL_BYTES:
        raise ValueError("Missing, symlinked or oversized preview ZIP")
    with zipfile.ZipFile(path, "r") as bundle:
        members = bundle.infolist()
        if len(members) != len(EXPECTED_ASSETS) or {m.filename for m in members} != EXPECTED_ASSETS:
            raise ValueError("ZIP must contain only the six app assets and _headers")
        if not all(m.is_dir() is False and m.file_size <= MAX_TOTAL_BYTES and
                   not stat.S_ISLNK(m.external_attr >> 16) for m in members):
            raise ValueError("ZIP contains an unsafe file type")
        if sum(m.file_size for m in members) > MAX_TOTAL_BYTES:
            raise ValueError("ZIP content exceeds the preview budget")
        for member in members:
            content = bundle.read(member)
            if hashlib.sha256(content).hexdigest() != digests[member.filename]:
                raise ValueError("ZIP asset does not match its source SHA-256: " + member.filename)
        if bundle.read("_headers").decode("utf-8") != headers_text():
            raise ValueError("ZIP security headers differ from the approved policy")
    return True


def build_package(output_dir):
    dest = Path(output_dir).resolve(strict=False)
    repo_root = ROOT.resolve()
    if dest == repo_root or dest.is_relative_to(repo_root) or repo_root.is_relative_to(dest):
        raise ValueError("Deployment ZIP must be generated outside the repository")
    if not dest.parent.is_dir() or dest.exists() or dest.is_symlink():
        raise ValueError("Output directory must be new and outside the Git checkout")
    temp = Path(tempfile.mkdtemp(prefix=".animate-free-private-", dir=dest.parent))
    try:
        baseline_dir = temp / "baseline"
        manifest = build(baseline_dir)
        site = baseline_dir / "site"
        validate_site(site)

        header_bytes = headers_text().encode("utf-8")
        digests = dict(manifest["files"])
        digests["_headers"] = hashlib.sha256(header_bytes).hexdigest()

        zip_path = temp / OUTPUT_NAME
        with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for name in sorted(SITE_FILES):
                bundle.write(site / name, arcname=name)
            bundle.writestr("_headers", header_bytes)

        checked_archive(zip_path, digests)

        receipt = {
            "kind": "OFFLINE_UNDEPLOYED_MODEL_FREE_PREVIEW_ZIP",
            "sourceCommit": manifest["sourceCommit"],
            "zipFile": OUTPUT_NAME,
            "zipSha256": hashlib.sha256(zip_path.read_bytes()).hexdigest(),
            "assetSha256": digests,
            "thirdPartyModelPresent": False,
            "deploymentPerformed": False,
            "accessControlVerified": False,
            "siteLevelAuthenticationVerified": False,
            "unauthorisedAssetRequestsDenied": False,
            "hostingUploadApproved": False,
            "physicalIphoneTested": False,
            "potentialExtraChargeApproved": False,
            "requiredOperatorConditions": [
                "Provider account is on Netlify credit-based FREE plan with hard usage cap",
                "NO paid subscription, add-on, automatic top-up or credit purchase",
                "Dashboard Project visibility PRIVATE is insufficient alone: site-level authentication must protect actual deployed assets",
                "Unverified users must be denied index, JS and CSS asset URLs before any upload",
                "No demonstrably enforced site-level access at $0 means DO NOT DEPLOY",
                "Provider request/log/analytics privacy reviewed before using the camera",
            ],
            "warning": (
                "This archive has no built-in authentication. Upload only AFTER "
                "confirming enforced SITE-LEVEL authentication for every URL. A PRIVATE dashboard setting alone is not enough. A live "
                "provider can override headers, rewrite HTML or log requests."
            ),
        }
        receipt_path = temp / RECEIPT_NAME
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # The receipt stays OUTSIDE the served ZIP, never bundled with participant data.
        shutil.rmtree(baseline_dir)
        os.replace(temp, dest)
        return receipt
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="New local directory outside repo, containing ZIP and audit receipt")
    args = parser.parse_args()
    try:
        result = build_package(args.output_dir)
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        raise SystemExit("BLOCKED: " + str(error))
    print(json.dumps(result, indent=2, sort_keys=True))
    print("PASS: offline ZIP only. NO hosting, subscription, payment or deployment performed.")


if __name__ == "__main__":
    main()
