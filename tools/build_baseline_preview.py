#!/usr/bin/env python3
"""Build a strictly model-free ANIMATE baseline for a future owner-approved preview.

This only writes an offline candidate outside the repository. It never deploys,
uploads, creates hosting accounts or distributes MediaPipe binaries.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from vendor_hand_model import ROOT, SITE_FILES

ORIGINAL_HAND_OPTION = '<option value="hand">Local ML: one hand / index fingertip (assets required)</option>'
BASELINE_BANNER = ('<p id="baselineDisclosure" class="fine muted" role="status">'
                   'Internal baseline only: colour, foreground and touch controls. '
                   'Hand ML is unavailable; no MediaPipe runtime or model is included.'
                   '</p>')


def sha256(path):
    with path.open("rb") as data:
        return hashlib.file_digest(data, "sha256").hexdigest()


def verify_committed_sources(source_dir, commit):
    """Prove packaged bytes are in the named Git commit, not dirty local changes."""
    for name in sorted(SITE_FILES):
        reviewed = subprocess.run(
            ["git", "show", f"{commit}:site/{name}"], cwd=ROOT,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        ).stdout
        if hashlib.sha256(reviewed).hexdigest() != sha256(source_dir / name):
            raise ValueError("Preview source differs from reviewed Git commit: " + name)


def validate_site(site):
    if not site.is_dir() or site.is_symlink():
        raise ValueError("Baseline preview site must be a real directory")
    entries = list(site.iterdir())
    if any(p.is_symlink() for p in entries) or {p.name for p in entries} != set(SITE_FILES):
        raise ValueError("Baseline preview must contain precisely six regular application files")
    if not all(p.is_file() for p in entries):
        raise ValueError("Directories or other objects forbidden in baseline site")
    html = (site / "index.html").read_text(encoding="utf-8")
    if (ORIGINAL_HAND_OPTION in html or '<option value="hand"' in html or
            html.count(BASELINE_BANNER) != 1 or
            'http-equiv="Content-Security-Policy"' not in html):
        raise ValueError("Baseline UI does not prove the ML option is absent and disclosed")
    for asset in SITE_FILES - {"index.html"}:
        if sha256(site / asset) != sha256(ROOT / "site" / asset):
            raise ValueError("Baseline application asset differs from reviewed source: " + asset)
    return True


def build(destination):
    destination = destination.resolve(strict=False)
    root = ROOT.resolve()
    if destination == root or destination.is_relative_to(root):
        raise ValueError("Baseline preview must remain outside Git checkout")
    if not destination.parent.is_dir() or destination.exists() or destination.is_symlink():
        raise ValueError("Output destination must be new with an existing parent")
    source_dir = ROOT / "site"
    entries = list(source_dir.iterdir())
    if (any(p.is_symlink() for p in entries) or
            {p.name for p in entries} != set(SITE_FILES) or
            not all(p.is_file() for p in entries)):
        raise ValueError("Source must contain only the six verified app assets; refuse vendor/ or unknown files")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            text=True, capture_output=True, check=True).stdout.strip()
    if len(commit) != 40 or any(x not in "0123456789abcdef" for x in commit):
        raise ValueError("Cannot verify exact source commit")
    verify_committed_sources(source_dir, commit)
    html = (source_dir / "index.html").read_text(encoding="utf-8")
    if html.count(ORIGINAL_HAND_OPTION) != 1 or html.count("</header>") != 1:
        raise ValueError("Unreviewed HTML cannot be transformed into an ML-free baseline")
    html = html.replace(ORIGINAL_HAND_OPTION, "")
    html = html.replace("</header>", BASELINE_BANNER + "\n  </header>")
    temp = Path(tempfile.mkdtemp(prefix=".animate-noml-", dir=destination.parent))
    try:
        site = temp / "site"
        site.mkdir(mode=0o700)
        for name in SITE_FILES:
            shutil.copyfile(source_dir / name, site / name)
        (site / "index.html").write_text(html, encoding="utf-8")
        validate_site(site)
        report = {
            "kind": "NON_DISTRIBUTED_INTERNAL_BASELINE_CANDIDATE",
            "sourceCommit": commit,
            "files": {name: sha256(site / name) for name in sorted(SITE_FILES)},
            "containsMediaPipeAssets": False,
            "hasHandMlMenuOption": False,
            "hostingApproved": False,
            "deviceValidationCompleted": False,
        }
        (temp / "MANIFEST.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, destination)
        return report
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path,
                        help="A NEW temporary directory OUTSIDE the repository; no deployment")
    args = parser.parse_args()
    result = build(args.output)
    print(json.dumps(result, indent=2))
    print("PASS: offline no-model preview candidate staged; hosting and publication remain blocked")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
