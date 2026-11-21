#!/usr/bin/env python3
"""Build a harmless offline access-control canary before ANY ANIMATE upload.

No site, camera, model, credentials, application code, or participant data.
Owner approval is still required even for deployment of this innocuous ZIP.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import tempfile
import zipfile

from build_zero_cost_preview import EXPECTED_ASSETS, MAX_TOTAL_BYTES, checked_archive, headers_text
from vendor_hand_model import ROOT, SITE_FILES

ZIP_NAME = "hosting-auth-canary-only.zip"
RECEIPT_NAME = "LOCAL_ONLY_CANARY_RECEIPT.json"


def harmless_files(marker):
    """Use the real candidate's asset paths, never its source or private data."""
    if len(marker) != 32 or any(c not in "0123456789abcdef" for c in marker):
        raise ValueError("Invalid canary marker")
    html = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Private hosting access test — no application</title>'
            '<link rel="stylesheet" href="styles.css">'
            '<script defer src="core.js"></script>'
            '<script defer src="foreground.js"></script>'
            '<script defer src="hand_ml.js"></script>'
            '<script defer src="app.js"></script></head>'
            '<body><main><h1>Private hosting access test only</h1>'
            '<p>Contains no application, camera, tracking, research or personal data.</p>'
            '<p id="status">Waiting for local scripts</p>'
            '<p>Marker: ' + marker + '</p></main></body></html>\n')
    content = {
        "index.html": html.encode("utf-8"),
        "styles.css": b"body{font:16px system-ui;margin:2rem;max-width:45rem}main{line-height:1.5}\n",
        "core.js": ("'use strict';\nwindow.canaryMarker = '" + marker + "';\n").encode(),
        "foreground.js": b"'use strict';\n// Harmless static placeholder.\n",
        "hand_ml.js": b"'use strict';\n// No ML runtime or model.\n",
        "app.js": ("'use strict';\nif (window.canaryMarker === '" + marker +
                   "') document.getElementById('status').textContent = 'Local JS loaded';\n").encode(),
        "_headers": headers_text().encode("utf-8"),
    }
    if set(content) != EXPECTED_ASSETS or set(content) - set(SITE_FILES | {"_headers"}):
        raise ValueError("Unexpected canary assets")
    return content


def build_canary(output_dir):
    dest = Path(output_dir).resolve(strict=False)
    repo = ROOT.resolve()
    if dest == repo or dest.is_relative_to(repo) or repo.is_relative_to(dest):
        raise ValueError("Canary output must remain outside the source repository")
    if not dest.parent.is_dir() or dest.exists() or dest.is_symlink():
        raise ValueError("Canary output directory must be new")
    temporary = Path(tempfile.mkdtemp(prefix=".canary-only-", dir=dest.parent))
    try:
        marker = secrets.token_hex(16)
        content = harmless_files(marker)
        digests = {name: hashlib.sha256(data).hexdigest() for name, data in content.items()}
        archive = temporary / ZIP_NAME
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            for name, data in sorted(content.items()):
                bundle.writestr(name, data)
        if archive.stat().st_size > MAX_TOTAL_BYTES:
            raise ValueError("Canary ZIP exceeds file-size limit")
        checked_archive(archive, digests)
        receipt = {
            "kind": "OFFLINE_UNDEPLOYED_HARMLESS_HOST_CANARY",
            "canaryId": marker,
            "zipFile": ZIP_NAME,
            "zipSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "assetSha256": digests,
            "appCodePresent": False,
            "modelPresent": False,
            "participantDataPresent": False,
            "deployed": False,
            "accessControlVerified": False,
            "costApproved": False,
            "userResearchApproved": False,
            "warning": (
                "This archive has no authentication. An owner may deploy only with explicit "
                "separate approval. A private dashboard label or login redirect alone does "
                "not independently prove every path is protected."
            ),
        }
        (temporary / RECEIPT_NAME).write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(temporary, dest)
        return receipt
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = build_canary(args.output_dir)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise SystemExit("BLOCKED: " + str(error))
    print(json.dumps(result, indent=2, sort_keys=True))
    print("PASS: harmless offline ZIP only; no upload, hosting, payment or deployment.")


if __name__ == "__main__":
    main()
