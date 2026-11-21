#!/usr/bin/env python3
"""Build offline authenticated HTML delivery diagnostic without changing ANIMATE.

Extends exact source-proven camera gate ZIP by two inert diagnostic resources.
Does not deploy, clear a camera gate, alter Netlify account or access external data.
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

from build_iphone_camera_gate import (
    build_camera_gate, validate_archive as validate_camera_gate,
    ZIP_NAME as CAMERA_ZIP, RECEIPT_NAME as CAMERA_RECEIPT,
    EXPECTED as CAMERA_FILES, VERIFY_HTML, VERIFY_JS
)
from build_zero_cost_preview import MAX_TOTAL_BYTES, headers_text
from build_screenshot_isolation_canary import SAFE_ROOT
from vendor_hand_model import ROOT

ZIP_NAME = "animate-html-delivery-diagnostic.zip"
RECEIPT_NAME = "LOCAL_ONLY_HTML_DIAGNOSTIC_RECEIPT.json"
DIAG_HTML = "operator-preview/inspect.html"
DIAG_JS = "operator-preview/inspect.js"
EXPECTED = frozenset(CAMERA_FILES | {DIAG_HTML, DIAG_JS})
TEMPLATE = ROOT / "tools" / "operator_html_diff_template.js"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def render_diagnostic(files, commit):
    reviewed = subprocess.run(
        ["git", "show", f"{commit}:tools/operator_html_diff_template.js"],
        cwd=ROOT, capture_output=True, check=True).stdout
    if reviewed != TEMPLATE.read_bytes():
        raise ValueError("Unreviewed HTML diagnostic template")
    text = reviewed.decode("utf-8")
    if text.count("__EXPECTED_HTML_BASE64__") != 1:
        raise ValueError("HTML diagnostic template placeholder mismatch")
    source_bytes = {
        "index.html": base64.b64encode(files["index.html"]).decode("ascii"),
        "operator-preview/index.html": base64.b64encode(
            files["operator-preview/index.html"]).decode("ascii")
    }
    script = text.replace("__EXPECTED_HTML_BASE64__",
                          json.dumps(source_bytes, sort_keys=True, separators=(",", ":"))
                          ).encode("utf-8")
    sri = "sha384-" + base64.b64encode(hashlib.sha384(script).digest()).decode("ascii")
    html = (
        '<!doctype html>\n<html lang="en-AU"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        'script-src \'self\'; connect-src \'self\'; style-src \'self\'; '
        'form-action \'none\'; base-uri \'none\'; object-src \'none\'">'
        '<meta name="referrer" content="no-referrer">'
        '<title>ANIMATE — Diagnose delivered HTML bytes</title>'
        f'<script defer src="inspect.js" integrity="{sri}" crossorigin="anonymous"></script>'
        '</head><body><main>'
        '<h1>ANIMATE — HTML response diagnostic</h1>'
        '<p>Compares the two hosted HTML files against the already approved source.'
        ' Reports only short sanitized differences; it does not send anything,'
        ' use the camera, read browser storage or grant camera clearance.</p>'
        '<p><strong>This page is diagnostic only. FAIL on the existing integrity'
        ' checker still blocks camera use.</strong></p>'
        '<pre id="diagnosticResult" tabindex="0" role="status" aria-live="polite">'
        'Inspecting current site responses...</pre>'
        '<button type="button" id="copyDiagnostic" disabled>Copy diagnostic result</button>'
        '</main></body></html>\n'
    ).encode("utf-8")
    return html, script


def validate_archive(archive_path, manifest):
    path = Path(archive_path)
    if (not path.is_file() or path.is_symlink() or
            path.stat().st_size > MAX_TOTAL_BYTES or set(manifest) != EXPECTED):
        raise ValueError("Invalid diagnostic archive")
    with zipfile.ZipFile(path) as bundle:
        entries = bundle.infolist()
        if len(entries) != len(EXPECTED) or {m.filename for m in entries} != EXPECTED:
            raise ValueError("Unapproved or duplicate diagnostic asset")
        if sum(e.file_size for e in entries) > MAX_TOTAL_BYTES:
            raise ValueError("Diagnostic archive oversized")
        for m in entries:
            if m.is_dir() or stat.S_ISLNK(m.external_attr >> 16):
                raise ValueError("Forbidden archive file type")
            if sha(bundle.read(m)) != manifest[m.filename]:
                raise ValueError("Diagnostic archive file hash mismatch")
            if any(s in m.filename.lower() for s in (
                ".wasm", ".task", "vendor/", ".env", "receipt", "ledger",
                "participant", "secrets", ".map"
            )):
                raise ValueError("Forbidden diagnostic content")
        if bundle.read("index.html") != SAFE_ROOT or (
                bundle.read("_headers") != headers_text().encode("utf-8")):
            raise ValueError("Neutral root or header gate changed")
        html = bundle.read(DIAG_HTML)
        script = bundle.read(DIAG_JS)
        pin = b"sha384-" + base64.b64encode(hashlib.sha384(script).digest())
        if pin not in html:
            raise ValueError("Diagnostic JavaScript integrity pin mismatch")
        if b"__EXPECTED_HTML_BASE64__" in script:
            raise ValueError("Uncompiled diagnostic")
        if b"getUserMedia(" in script or b"localStorage" in script or b"sendBeacon" in script:
            raise ValueError("Disallowed camera, storage or telemetry")
    return True


def build_html_diagnostic(target_dir):
    target = Path(target_dir).resolve(strict=False)
    repo = ROOT.resolve()
    if target == repo or target.is_relative_to(repo) or repo.is_relative_to(target):
        raise ValueError("Must build outside repository checkout")
    if not target.parent.is_dir() or target.exists() or target.is_symlink():
        raise ValueError("Output folder must be new")
    scratch = Path(tempfile.mkdtemp(prefix=".animate-html-diagnostic-", dir=target.parent))
    try:
        base = scratch / "base"
        receipt = build_camera_gate(base)
        with zipfile.ZipFile(base / CAMERA_ZIP) as bundle:
            files = {n: bundle.read(n) for n in bundle.namelist()}
        if sha((base / CAMERA_ZIP).read_bytes()) != receipt["zipSha256"]:
            raise ValueError("Baseline ZIP changed unexpectedly")
        if not validate_camera_gate(base / CAMERA_ZIP, receipt["fileSha256"]):
            raise ValueError("Unverified camera-gate base")
        html, script = render_diagnostic(files, receipt["sourceCommit"])
        files.update({DIAG_HTML: html, DIAG_JS: script})
        archive = scratch / ZIP_NAME
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as out:
            for name, data in sorted(files.items()):
                out.writestr(name, data)
        hashes = {name: sha(data) for name, data in files.items()}
        validate_archive(archive, hashes)
        output_receipt = {
            "kind": "OFFLINE_UNDEPLOYED_ANIMATE_HTML_DIFF_DIAGNOSTIC",
            "sourceCommit": receipt["sourceCommit"],
            "zipFile": ZIP_NAME,
            "zipSha256": sha(archive.read_bytes()),
            "fileSha256": hashes,
            "parentCameraGateZipSha256": receipt["zipSha256"],
            "diagnosticPath": "/operator-preview/inspect.html",
            "approvedAppFilesUnchanged": True,
            "cameraGateRemainsBlocked": True,
            "noMLModelOrWASM": True,
            "noPersonalData": True,
            "deployed": False,
            "spendingApproved": False,
            "warning": (
                "Do not use diagnostic output to bypass strict HTML SHA-256. "
                "Inspect the exact modification and resolve provider transformation. "
                "This ZIP does not perform any remote deployment."
            )
        }
        (scratch / RECEIPT_NAME).write_text(
            json.dumps(output_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        shutil.rmtree(base)
        os.replace(scratch, target)
        return output_receipt
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = build_html_diagnostic(args.output_dir)
    except (OSError, ValueError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        raise SystemExit("BLOCKED: " + str(error))
    print(json.dumps(receipt, indent=2, sort_keys=True))
    print("PASS: offline diagnostic package; no upload, provider configuration or camera test")


if __name__ == "__main__":
    main()
