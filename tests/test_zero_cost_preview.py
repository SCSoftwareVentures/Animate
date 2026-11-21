#!/usr/bin/env python3
"""Offline, no-deployment security test for the zero-additional-cost preview ZIP."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_zero_cost_preview import (
    EXPECTED_ASSETS, OUTPUT_NAME, RECEIPT_NAME, build_package,
    checked_archive, headers_text,
)
from serve_safari_https import CSP_HEADER, SECURITY_HEADERS
from vendor_hand_model import SITE_FILES, REVIEWED_LICENSE_SHA256

count = 0


def check(label, condition):
    global count
    if not condition:
        raise AssertionError(label)
    count += 1
    print("PASS " + label, flush=True)


def must_refuse(label, operation):
    try:
        operation()
    except (ValueError, OSError, zipfile.BadZipFile):
        check(label, True)
    else:
        raise AssertionError(label)


def recompress(data, extra=None, replace=None):
    """Make untrusted ZIP fixtures without any Internet or file uploads."""
    extra = extra or {}
    replace = replace or {}
    output = {}
    for name, content in data.items():
        output[name] = replace.get(name, content)
    output.update(extra)
    return output


def rewrite_zip(path, entries):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, content in entries.items():
            bundle.writestr(name, content)


def main():
    with tempfile.TemporaryDirectory(prefix="animate-zero-cost-test-") as tmp:
        root = Path(tmp)
        output = root / "candidate"
        receipt = build_package(output)
        zip_path = output / OUTPUT_NAME
        manifest_path = output / RECEIPT_NAME
        check("offline generator creates only the archive and non-published receipt",
              {p.name for p in output.iterdir()} == {OUTPUT_NAME, RECEIPT_NAME})
        check("receipt records no deployment or cost authorisation",
              receipt["deploymentPerformed"] is False and
              receipt["potentialExtraChargeApproved"] is False and
              receipt["accessControlVerified"] is False and
              receipt["physicalIphoneTested"] is False)
        check("Netlify FREE plan and PRIVATE project are mandatory operator conditions",
              "FREE plan" in " ".join(receipt["requiredOperatorConditions"]) and
              "PRIVATE" in " ".join(receipt["requiredOperatorConditions"]))
        check("model redistribution remains blocked globally",
              REVIEWED_LICENSE_SHA256 is None and
              receipt["thirdPartyModelPresent"] is False)
        check("exact ZIP SHA-256 is verifiable without provider account",
              hashlib.sha256(zip_path.read_bytes()).hexdigest() == receipt["zipSha256"])
        check("receipt stays outside the served ZIP",
              manifest_path.is_file() and "LOCAL_ONLY_BUILD_RECEIPT.json" not in EXPECTED_ASSETS)
        with zipfile.ZipFile(zip_path) as bundle:
            content = {name: bundle.read(name) for name in bundle.namelist()}
        check("ZIP has precisely six reviewed app files plus Netlify _headers",
              set(content) == set(SITE_FILES) | {"_headers"})
        check("ZIP contains no models, WASM, env, ledger or participant JSON",
              all("vendor/" not in path and ".wasm" not in path and
                  ".task" not in path and ".json" not in path and
                  ".env" not in path and "ledger" not in path
                  for path in content))
        check("baseline hand-ML option was removed",
              b'<option value="hand"' not in content["index.html"] and
              b"baselineDisclosure" in content["index.html"])
        check("static header policy matches the previously verified HTTPS bench policy",
              CSP_HEADER in headers_text() and
              all(f"{name}: {value}" in headers_text()
                  for name, value in SECURITY_HEADERS.items()))
        check("preview sends HSTS while also preventing framing",
              "Strict-Transport-Security: max-age=86400" in headers_text() and
              "frame-ancestors 'none'" in headers_text())
        check("zip bytes match receipt's seven reviewed SHA-256 checks",
              checked_archive(zip_path, receipt["assetSha256"]))
        must_refuse("cannot silently replace an existing ZIP directory",
                    lambda: build_package(output))
        must_refuse("cannot generate archive inside the Git repository",
                    lambda: build_package(ROOT / "unsafe-netlify-preview"))
        must_refuse("cannot generate archive in the Git repository itself",
                    lambda: build_package(ROOT))
        altered = root / "altered.zip"
        rewrite_zip(altered, recompress(content, replace={"app.js":content["app.js"]+b"\n// injected"}))
        must_refuse("tampered JavaScript invalidates archive integrity",
                    lambda: checked_archive(altered, receipt["assetSha256"]))
        rewrite_zip(altered, recompress(content, extra={"research-ledger.csv": b"id,answer\n1,secret"}))
        must_refuse("unreviewed research data cannot be bundled",
                    lambda: checked_archive(altered, receipt["assetSha256"]))
        rewrite_zip(altered, recompress(content, extra={"vendor/hand_landmarker.task": b"model"}))
        must_refuse("unreviewed MediaPipe model cannot be bundled",
                    lambda: checked_archive(altered, receipt["assetSha256"]))
        rewrite_zip(altered, recompress(content, replace={"_headers": b"/*\n  Access-Control-Allow-Origin: *\n"}))
        must_refuse("weakened Netlify security headers invalidate ZIP",
                    lambda: checked_archive(altered, receipt["assetSha256"]))
        check("private preview ZIP has no billing or remote API implementation",
              not any(word in (ROOT / "tools/build_zero_cost_preview.py").read_text()
                      for word in ("urlopen(", "requests.post(", "deploy_site(", "create_account(", "payment_card")))
        check("receipt and source checks cannot claim validated iPhone performance",
              receipt["physicalIphoneTested"] is False and
              "camera" not in receipt["kind"].lower())
    print("PASS %d/%d zero-cost preview export tests" % (count, count), flush=True)


if __name__ == "__main__":
    main()
