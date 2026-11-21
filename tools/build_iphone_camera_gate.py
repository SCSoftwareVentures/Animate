#!/usr/bin/env python3
"""Create a no-upload, source-verified iPhone camera integrity-gate candidate.

Uses the already reviewed neutral-root/model-free operator candidate and adds
only a same-origin authenticated verification HTML/JS pair. The verifier reads
its own static files/headers from Safari, does not use camera or submit data.
This builder makes no Netlify changes, charges, or uploads.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import zipfile

from build_operator_preview import (
    build_operator_preview, check_zip as check_preview, EXPECTED as APP_FILES,
    PREFIX, ZIP_NAME as BASE_ZIP, RECEIPT_NAME as BASE_RECEIPT
)
from build_zero_cost_preview import MAX_TOTAL_BYTES, headers_text
from build_screenshot_isolation_canary import SAFE_ROOT
from vendor_hand_model import ROOT, SITE_FILES

ZIP_NAME = "animate-verified-iphone-preview.zip"
RECEIPT_NAME = "LOCAL_ONLY_IPHONE_GATE_RECEIPT.json"
VERIFY_HTML = PREFIX + "verify.html"
VERIFY_JS = PREFIX + "verify.js"
EXPECTED = frozenset(set(APP_FILES) | {VERIFY_HTML, VERIFY_JS})
TEMPLATE = ROOT / "tools" / "operator_verify_template.js"


def hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


def assert_committed_template(commit):
    reviewed = subprocess.run(
        ["git", "show", f"{commit}:tools/operator_verify_template.js"],
        cwd=ROOT, capture_output=True, check=True
    ).stdout
    actual = TEMPLATE.read_bytes()
    if reviewed != actual:
        raise ValueError("Verifier template is unreviewed or modified")
    return actual.decode("utf-8")


def parse_header_policy():
    raw = headers_text()
    parts = raw.splitlines()
    if not parts or parts[0] != "/*":
        raise ValueError("Unexpected approved _headers layout")
    result = {}
    for line in parts[1:]:
        if not line.startswith("  ") or ": " not in line:
            raise ValueError("Unsupported header rule")
        key, value = line.strip().split(": ", 1)
        if key in result:
            raise ValueError("Duplicate header")
        result[key] = value
    mandatory = {
        "Content-Security-Policy", "Permissions-Policy",
        "X-Frame-Options", "Cross-Origin-Resource-Policy",
        "X-Content-Type-Options", "Referrer-Policy",
        "Cache-Control", "Strict-Transport-Security"
    }
    if set(result) != mandatory:
        raise ValueError("Unexpected deployed security-header set")
    return result


def render_verifier(base_content, source_commit):
    if set(base_content) != set(APP_FILES) or base_content["index.html"] != SAFE_ROOT:
        raise ValueError("Unreviewed base preview")
    if base_content["_headers"] != headers_text().encode():
        raise ValueError("Unreviewed hosting headers")
    template = assert_committed_template(source_commit)
    if (template.count("__EXPECTED_APP_HASHES__") != 1 or
            template.count("__EXPECTED_HTML_REFERENCE_BASE64__") != 1 or
            template.count("__EXPECTED_HEADERS__") != 1):
        raise ValueError("Verifier template placeholder integrity failed")
    source_hashes = {
        filename: hash_bytes(base_content[filename])
        for filename in sorted(set(APP_FILES) - {"_headers"})
    }
    script = template.replace(
        "__EXPECTED_APP_HASHES__", json.dumps(source_hashes, separators=(",", ":"), sort_keys=True)
    ).replace(
        "__EXPECTED_HTML_REFERENCE_BASE64__",
        json.dumps({name: base64.b64encode(base_content[name]).decode("ascii")
                    for name in ("index.html", PREFIX + "index.html")},
                   separators=(",", ":"), sort_keys=True)
    ).replace(
        "__EXPECTED_HEADERS__", json.dumps(parse_header_policy(), separators=(",", ":"), sort_keys=True)
    ).encode("utf-8")
    sri = base64.b64encode(hashlib.sha384(script).digest()).decode("ascii")
    html = (
        "<!doctype html>\n<html lang=\"en-AU\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; "
        "script-src 'self'; style-src 'self'; connect-src 'self'; "
        "base-uri 'none'; form-action 'none'; object-src 'none'\">"
        "<meta name=\"referrer\" content=\"no-referrer\">"
        "<title>ANIMATE — Private on-device camera preflight</title>"
        f"<script defer src=\"verify.js\" integrity=\"sha384-{sri}\" crossorigin=\"anonymous\"></script>"
        "</head><body><main><h1>ANIMATE — On-device security verification</h1>"
        "<p>Checks only static application files and HTTP headers using your current "
        "same-origin sign-in. Does not turn on the camera, collect footage, "
        "read local test records, send results, or access external websites.</p>"
        "<p><strong>Only proceed to camera testing after this report shows PASS, "
        "the hosting project remains Private, and the reviewer confirms the "
        "source SHA and deployment identity.</strong></p>"
        "<pre id=\"result\" role=\"status\" aria-live=\"polite\" tabindex=\"0\">Checking local files and headers...</pre>"
        "<button type=\"button\" id=\"copyResult\" disabled>Copy nonpersonal audit result</button>"
        "<p>FAIL is a hard stop: do not weaken CSP or authentication to force a pass.</p>"
        "</main></body></html>\n"
    ).encode("utf-8")
    return html, script, source_hashes, sri


def validate_archive(path, expected_hashes):
    path = Path(path)
    if (not path.is_file() or path.is_symlink() or
            path.stat().st_size > MAX_TOTAL_BYTES or set(expected_hashes) != EXPECTED):
        raise ValueError("Invalid audited camera-gate archive")
    with zipfile.ZipFile(path) as zip_file:
        files = zip_file.infolist()
        if len(files) != len(EXPECTED) or {entry.filename for entry in files} != EXPECTED:
            raise ValueError("Missing, extra or duplicate camera-gate archive member")
        if sum(entry.file_size for entry in files) > MAX_TOTAL_BYTES:
            raise ValueError("Oversized camera-gate package")
        for entry in files:
            if entry.is_dir() or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError("Unsafe archive member type")
            data = zip_file.read(entry)
            if hash_bytes(data) != expected_hashes[entry.filename]:
                raise ValueError("Camera-gate member hash mismatch: " + entry.filename)
            if any(part in entry.filename.lower() for part in (
                    "vendor/", ".task", ".wasm", ".env", "ledger",
                    "manifest", "receipt", "participant", ".map")):
                raise ValueError("Forbidden package asset: " + entry.filename)
        if zip_file.read("index.html") != SAFE_ROOT:
            raise ValueError("Neutral root changed")
        if zip_file.read("_headers") != headers_text().encode():
            raise ValueError("Security policy changed")
        html = zip_file.read(VERIFY_HTML)
        script = zip_file.read(VERIFY_JS)
        sri = "sha384-" + base64.b64encode(hashlib.sha384(script).digest()).decode("ascii")
        if sri.encode("ascii") not in html:
            raise ValueError("Verifier script SRI missing or mismatched")
        if (b"__EXPECTED_APP_HASHES__" in script or
                b"__EXPECTED_HTML_REFERENCE_BASE64__" in script or
                b"__EXPECTED_HEADERS__" in script):
            raise ValueError("Verifier template not compiled")
        if b"getUserMedia(" in script or b"localStorage" in script:
            raise ValueError("Verifier must not activate camera or read participant records")
    return True


def build_camera_gate(output_dir):
    target = Path(output_dir).resolve(strict=False)
    repo = ROOT.resolve()
    if target == repo or target.is_relative_to(repo) or repo.is_relative_to(target):
        raise ValueError("Output must stay outside repository")
    if not target.parent.is_dir() or target.exists() or target.is_symlink():
        raise ValueError("Output must be new with existing parent")
    scratch = Path(tempfile.mkdtemp(prefix=".animate-camera-security-", dir=target.parent))
    try:
        base_dir = scratch / "base"
        prior = build_operator_preview(base_dir)
        with zipfile.ZipFile(base_dir / BASE_ZIP) as bundle:
            existing = {name: bundle.read(name) for name in bundle.namelist()}
        if hash_bytes((base_dir / BASE_ZIP).read_bytes()) != prior["zipSha256"]:
            raise ValueError("Base package hash changed")
        if not check_preview(base_dir / BASE_ZIP, prior["fileSha256"]):
            raise ValueError("Base package not verified")
        html, script, hashes, sri = render_verifier(existing, prior["sourceCommit"])
        content = {**existing, VERIFY_HTML: html, VERIFY_JS: script}
        archive = scratch / ZIP_NAME
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for name, data in sorted(content.items()):
                bundle.writestr(name, data)
        digests = {name: hash_bytes(data) for name, data in content.items()}
        validate_archive(archive, digests)
        receipt = {
            "kind": "OFFLINE_UNDEPLOYED_VERIFIED_IPHONE_CAMERA_GATE",
            "sourceCommit": prior["sourceCommit"],
            "zipFile": ZIP_NAME,
            "zipSha256": hash_bytes(archive.read_bytes()),
            "fileSha256": digests,
            "appSha256": hashes,
            "verifierSriSha384": sri,
            "verificationPath": "/operator-preview/verify.html",
            "appPath": prior["operatorEntry"],
            "landingPageSha256": hash_bytes(SAFE_ROOT),
            "modelPresent": False,
            "participantDataPresent": False,
            "hostingAuthBuiltIn": False,
            "hostingScreenshotConfidentialityProved": False,
            "authenticatedLiveAuditCompleted": False,
            "physicalIphoneCameraTested": False,
            "deploymentPerformed": False,
            "deploymentApproved": False,
            "spendingApproved": False,
            "warning": (
                "No server-side authentication, no data upload, no Netlify deployment. "
                "The owner must separately upload under the existing private project "
                "and run this checker inside signed-in Safari. Public Netlify deploy "
                "screenshots remain an independent provider-side residual risk."
            )
        }
        (scratch / RECEIPT_NAME).write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        shutil.rmtree(base_dir)
        os.replace(scratch, target)
        return receipt
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        receipt = build_camera_gate(args.output_dir)
    except (OSError, ValueError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        raise SystemExit("BLOCKED: " + str(error))
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print("PASS: offline authenticated-camera-gate ZIP only; no remote action")


if __name__ == "__main__":
    main()
