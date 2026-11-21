#!/usr/bin/env python3
"""Offline unit regression for ANIMATE rights-evidence preflight; no network or binary assets."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_runtime_rights import audit_archive


def archive_bytes(name="@mediapipe/tasks-vision", version="1.2.3", extras=None):
    extras = extras or {}
    values = {"package/package.json": json.dumps({
        "name": name, "version": version, "license": "Apache-2.0"
    }).encode("utf-8")}
    values.update({key: value.encode("utf-8") for key, value in extras.items()})
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as archive:
        for path, payload in values.items():
            member = tarfile.TarInfo(path)
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
    return stream.getvalue()


def check(label, condition):
    if not condition:
        raise AssertionError(label)
    print("PASS " + label, flush=True)


def inspect(data, **kwargs):
    return audit_archive(data, expected_digest=hashlib.sha256(data).hexdigest(), **kwargs)


def main():
    data = archive_bytes()
    report = inspect(data)
    check("declared SPDX metadata does not approve redistribution",
          report["packageLicenseMetadata"] == "Apache-2.0" and
          report["redistribution"] == "BLOCKED")
    check("missing LICENSE and NOTICE are identified separately",
          len(report["outstanding"]) >= 3 and
          "No top-level LICENSE" in report["outstanding"][0] and
          "No top-level NOTICE" in report["outstanding"][1])
    check("no licence notice file is invented",
          not report["licenseFilesInExactArchive"] and not report["noticeFilesInExactArchive"])
    try:
        audit_archive(data)
    except ValueError as error:
        check("nonpinned archive digest rejected", "digest" in str(error))
    else:
        raise AssertionError("Expected pinned digest rejection")

    wrong = archive_bytes(name="another-package")
    try:
        inspect(wrong)
    except ValueError as error:
        check("wrong package identity rejected", "name/version" in str(error))
    else:
        raise AssertionError("Expected package name rejection")

    wrong_version = archive_bytes(version="1.2.2")
    try:
        inspect(wrong_version)
    except ValueError as error:
        check("nearby release cannot substitute", "name/version" in str(error))
    else:
        raise AssertionError("Expected release version rejection")

    nested = archive_bytes(extras={"package/wasm/LICENSE": "Some other licence"})
    nested_result = inspect(nested)
    check("nested licence is not mistaken for top-level runtime notice",
          not any(n.count("/") == 1 for n in nested_result["licenseFilesInExactArchive"]) and
          nested_result["redistribution"] == "BLOCKED")

    declared_files = archive_bytes(extras={
        "package/LICENSE": "Apache licence text",
        "package/NOTICE": "Attribution text"
    })
    result = inspect(declared_files, reviewed_sha="a" * 64)
    check("presence of text and a digest alone never grants legal release",
          result["redistribution"] == "BLOCKED" and
          any("human review" in x for x in result["outstanding"]))

    check("rights audit output excludes external participant data",
          "participant" not in json.dumps(result).lower())
    print("PASS 9/9 runtime rights audit unit tests", flush=True)


if __name__ == "__main__":
    main()
