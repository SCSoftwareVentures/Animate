#!/usr/bin/env python3
"""Safety regressions for preview staging and GitHub Pages manual publication guards."""
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_baseline_preview import BASELINE_BANNER, build, validate_site
from vendor_hand_model import SITE_FILES, REVIEWED_LICENSE_SHA256


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    print("PASS " + name, flush=True)


def must_refuse(name, operation):
    try:
        operation()
    except (ValueError, OSError):
        print("PASS " + name, flush=True)
    else:
        raise AssertionError(name)


def main():
    with TemporaryDirectory(prefix="animate-preview-test-") as tmp:
        target = Path(tmp) / "candidate"
        manifest = build(target)
        site = target / "site"
        check("baseline candidate is made outside the checkout", target.is_dir() and validate_site(site))
        check("candidate contains only the six non-model app files",
              {p.name for p in site.iterdir()} == set(SITE_FILES) and
              not any("vendor" in p.as_posix() for p in site.rglob("*")))
        html = (site / "index.html").read_text()
        check("ML selection removed and limitation explicitly disclosed",
              '<option value="hand"' not in html and html.count(BASELINE_BANNER) == 1)
        check("baseline retains same-origin CSP and touch controls",
              'connect-src &#39;self&#39;' not in html and "connect-src 'self'" in html and
              'id="sample"' in html and 'id="consent"' in html)
        check("all candidate files have verifiable SHA-256 manifest values",
              manifest["sourceCommit"] and len(manifest["sourceCommit"]) == 40 and
              manifest["containsMediaPipeAssets"] is False and
              json.loads((target / "MANIFEST.json").read_text()) == manifest and
              all(hashlib.sha256((site / name).read_bytes()).hexdigest() == digest
                  for name, digest in manifest["files"].items()))
        must_refuse("existing target is never overwritten", lambda: build(target))
        must_refuse("cannot stage model-free candidate inside source checkout",
                    lambda: build(ROOT / "unapproved-baseline-preview"))
        (site / "vendor").mkdir()
        must_refuse("unexpected model/vendor directory causes validation failure",
                    lambda: validate_site(site))

    # This is a static contract for GitHub Actions. It cannot replace GitHub
    # repository permission or environment protection configuration.
    yaml = (ROOT / ".github/workflows/publish.yml").read_text()
    check("public release is manual-only", "  workflow_dispatch:" in yaml and
          "\n  push:" not in yaml and "\n  pull_request:" not in yaml)
    check("manual publication requires explicit consent + owner approval variable",
          "inputs.confirm_public_deployment == true" in yaml and
          "vars.ANIMATE_PUBLIC_RELEASE_APPROVED == 'true'" in yaml)
    check("public release requires SHA match against owner-controlled variable",
          "vars.ANIMATE_APPROVED_COMMIT_SHA" in yaml and
          '\"$REQUESTED_SHA\" != \"$APPROVED_SHA\"' in yaml and
          '\"$REQUESTED_SHA\" != \"$GITHUB_SHA\"' in yaml)
    check("publish checker remains mandatory before deploy",
          "run: python tests/check_release.py --publish" in yaml and
          "needs: prepare" in yaml and
          "if: github.ref == 'refs/heads/main'" in yaml)
    check("ML model release is blocked while exact rights approval is absent",
          REVIEWED_LICENSE_SHA256 is None)
    print("PASS 12/12 no-model preview and public-release guard tests", flush=True)


if __name__ == "__main__":
    main()
