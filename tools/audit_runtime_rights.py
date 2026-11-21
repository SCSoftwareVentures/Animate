#!/usr/bin/env python3
"""Offline rights-evidence preflight for the exact pinned MediaPipe npm runtime.

This inspects an already downloaded, checksum-verified archive. It does not
establish permission to redistribute a model/runtime and cannot approve release.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile

from vendor_hand_model import (
    PKG, RUNTIME_ARCHIVE_SHA256, RUNTIME_LIMIT, REVIEWED_LICENSE_SHA256,
    checked_bytes,
)


def audit_archive(data, expected_digest=RUNTIME_ARCHIVE_SHA256, reviewed_sha=REVIEWED_LICENSE_SHA256):
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_digest:
        raise ValueError("Runtime archive digest is not the pinned release SHA-256")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        members = {m.name: m for m in archive.getmembers() if m.isfile()}
        metadata_member = members.get("package/package.json")
        if metadata_member is None or metadata_member.size > 128_000:
            raise ValueError("Pinned runtime package metadata is missing or oversized")
        metadata_file = archive.extractfile(metadata_member)
        if metadata_file is None:
            raise ValueError("Cannot read runtime package metadata")
        metadata = json.loads(metadata_file.read(128_001))
        if not isinstance(metadata, dict) or metadata.get("name") != "@mediapipe/tasks-vision" or metadata.get("version") != "1.2.3":
            raise ValueError("Archive package name/version does not match the pinned runtime")
        raw_license = metadata.get("license")
        license_declaration = raw_license if isinstance(raw_license, str) and len(raw_license) <= 128 else "not declared"

        # Entries inside the exact archive, not similarly named files in other releases.
        names = sorted(members)
        licenses = [n for n in names if re.search(
            r"(?i)(?:^|/)(?:LICENSE|LICENCE|COPYING)(?:\.[a-z0-9_-]+)?$", n)]
        notices = [n for n in names if re.search(
            r"(?i)(?:^|/)(?:NOTICE|THIRD[_-]?PARTY[_-]?(?:LICENSES?|NOTICES?))"
            r"(?:\.[a-z0-9_-]+)?$", n)]
        release_license = [n for n in licenses if n.count("/") == 1]
        release_notice = [n for n in notices if n.count("/") == 1]

    missing = []
    if not release_license:
        missing.append("No top-level LICENSE/LICENCE/COPYING text in this exact npm archive")
    if not release_notice:
        missing.append("No top-level NOTICE/THIRD_PARTY notices in this exact npm archive")
    if reviewed_sha is None:
        missing.append("No operator-reviewed, release-matched attribution bundle SHA-256 approved")
    # These checks cannot prove that every native dependency's source/notice was supplied.
    missing.append("Exact WASM/native dependency file-level notice/source obligations still require human review")
    return {
        "runtime": PKG,
        "archiveSha256": digest,
        "packageLicenseMetadata": license_declaration,
        "licenseFilesInExactArchive": licenses,
        "noticeFilesInExactArchive": notices,
        "redistribution": "BLOCKED",
        "outstanding": missing,
        "interpretation": (
            "Metadata or test-only access does not confer legal approval to redistribute. "
            "No deployment, vendoring, licence override or notices from adjacent versions."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-archive", required=True, type=Path,
                        help="Already downloaded, pinned npm tarball (no new network fetches)")
    parser.add_argument("--expect-blocked", action="store_true",
                        help="CI passes only if the expected release block is reported")
    args = parser.parse_args()
    data = checked_bytes(args.runtime_archive, RUNTIME_LIMIT)
    report = audit_archive(data)
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)
    if report["redistribution"] != "BLOCKED":
        raise SystemExit("Unsafe: rights auditor must never auto-authorise redistribution")
    if not args.expect_blocked:
        raise SystemExit("Release BLOCKED: exact runtime rights/attribution still require approval")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, json.JSONDecodeError, tarfile.TarError) as error:
        raise SystemExit(str(error))
