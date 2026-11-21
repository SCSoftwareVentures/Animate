# ANIMATE — Integration and release gates

Status: **engineering only; not approved for publication, recruitment or sale.**

## Source import and review

The v0.7 source from the engineering handoff is on `engineering/animate-v07-hardening` in draft PR #1. The import preserves `.github/workflows/`, `site/`, `tests/`, `tools/`, and the public-repository exclusions. Current CI evidence lives in the draft PR.

Never add participant exports, research ledgers, individual contact information, model downloads with unresolved redistribution rights, credentials or generated databases to this public repository. The .gitignore is defence in depth, not a substitute for an independent diff and repository-history review.

## P0 verification

- `node --check site/core.js && node --check site/foreground.js && node --check site/hand_ml.js && node --check site/app.js`
- `node tests/test_core.js && node tests/test_foreground.js && node tests/test_hand_ml.js`
- `python tests/check_release.py`
- `python tests/offline_browser.py && python tests/test_hand_browser.py`
- `python tests/e2e.py` on a GitHub Actions runner (HTTPS-origin/CSP equivalent must be independently checked)
- Check browser console errors, model-loader timeout and late-init races; prove camera interruption invalidates calibration and prevents completion scoring.
- Verify PR scope; do not merge unless all required checks pass and a human approves.

## Hard release blocks

- The optional MediaPipe runtime and model are absent from the checkout. See [the asset review](HAND_ML_ASSET_GATE.md) for independently checked digests, licensing evidence, and runtime findings.
- Review attribution, redistribution terms, and the exact runtime used in the app before bundling it.
- `python tests/check_release.py --publish` **must fail** while assets are missing; the build is not publishable.
- Real iPhone Safari camera, thermal/performance, accessibility, false-completion and consent testing have not been performed.
- Only the owner can approve public deployment or participant recruitment.

## Expected v0.7 changes

A bounded timeout during hand-ML startup; closing late-loaded engines; avoiding repeated-start leaks; invalidating all calibration after interruption; and additional automated regression tests.

Do not treat synthetic browser tests or client-generated exported JSON as proof of real-world accuracy or demand.
