# ANIMATE v0.7.0 — Engineering hardening candidate

**Status: consolidated draft engineering candidate — not approved for public deployment, participant recruitment, model redistribution or sale as a released end-user product.**

**Start here for review:** [Acquisition and integration dossier](ACQUISITION_REVIEW_DOSSIER.md). A separate [no-charge iPhone preview option](ZERO_COST_IPHONE_PREVIEW.md) packages a model-free offline ZIP but does not deploy it or activate provider billing. The cumulative source is being reviewed as one proposed change against `main`; the earlier stacked draft PRs remain engineering history. Technical verification and commercial readiness are separate gates.

The preceding exact engineering commit `1c6b1eb145352e55f2a8ee02ef35bcf0b633314c` passed GitHub Actions run #25 (147 unit/security/licensing checks and 107 browser checks). **That is historical evidence, not verification of a later consolidated commit.** Inspect the consolidated PR's own CI status before approving any merge.

ANIMATE v0.7.0 is an engineering candidate with three tracking implementations:

1. **Colour (baseline):** HSV connected-component tracking of a calibrated, sufficiently saturated object. Not an ML model.
2. **Foreground (baseline):** stationary-camera difference tracking after collecting an empty background. Not an ML model and not object identity.
3. **Hand (new, optional):** same-origin MediaPipe **Hand Landmarker** adapter that turns one hand's index fingertip into a position. This is real ML *only when the reviewed MediaPipe runtime and trained model are installed*. It is **not household-object classification**, not a gesture recogniser, and not included as a functional model in this ZIP.

The checked-in runtime and model **are not bundled**, because the exact MediaPipe runtime redistribution and native/WASM notice requirements remain unresolved. GitHub Actions has staged checksum-pinned binaries **ephemerally for controlled test-image inference in both Chromium and Linux WebKit**; this does not constitute authorisation to redistribute them or evidence of physical iPhone compatibility. Selecting hand mode without these assets fails closed, closes the camera and preserves the first two trackers. No participants should receive this build.

## Implemented engineering

- `site/hand_ml.js`: local ESM runtime loader for MediaPipe Tasks Vision 1.2.3 and the official float16 Hand Landmarker model v1, index-fingertip extraction, bounded inference frequency, non-monotonic timestamp rejection, multi-hand fail-closed, stop/cancellation, and local-only diagnostics.
- `site/app.js`: hand mode wired into camera lifecycle, frame age and interruption gate, three-zone task scoring, independent `detector=hand` and `model` evidence labels. Touch results are never camera completions.
- `site/core.js`: build 0.7.0/schema 5, requires linked model provenance in hand results, and reports each tracker separately. Pseudonymous exported JSON is editable, **not** cryptographic proof of use.
- `site/index.html`: camera disclosure and a CSP allowing same-origin model/WASM fetch and `wasm-unsafe-eval` without arbitrary external domains. Real iOS Safari CSP/runtime compatibility is still unverified.
- `tools/vendor_hand_model.py`: stages exact SHA-256-verified runtime/model bytes for private tests outside the checkout. Reviewed installation also requires the pinned licence and attribution file.
- `tests/check_release.py`: refuses publication while reviewed ML assets are absent, or if present assets fail manifest verification. Detects unexpected published files and tracked sensitive research material.

## Reproducible local checks

```sh
node --check site/core.js && node --check site/foreground.js && node --check site/hand_ml.js && node --check site/app.js
node tests/test_core.js
node tests/test_foreground.js
node tests/test_hand_ml.js
python tests/check_release.py
python tests/offline_browser.py
python tests/test_hand_browser.py
# Full origin/CSP test, only in a suitable network-enabled build worker:
python tests/e2e.py /usr/bin/chromium
```

`TEST_RESULTS.md` records **historical pre-import**, not current GitHub CI, results. For latest scope and unresolved approvals see [ACQUISITION_REVIEW_DOSSIER.md](ACQUISITION_REVIEW_DOSSIER.md) and the consolidated review PR. The manual `publish.yml` is additionally blocked by explicit owner-controlled variables, exact reviewed-commit matching and `python tests/check_release.py --publish`. No deployment or owner approval has occurred.

## Remaining release obligations for real ML and physical iPhone validation

1. Inspect `HAND_ML_ASSET_GATE.md` and conduct an independent review of both the npm runtime and model-weights redistribution terms; record findings. Do **not** assume the runtime's Apache licence covers the separate model bundle.
2. Confirm and preserve the independently checked pinned model and runtime SHA-256 provenance. Controlled private CI staging and fixed-image inference are already implemented; do not mistake this for redistribution approval.
3. Use the private stage to run real inference tests. Complete the exact runtime notice and source review before approving redistribution or running the installer. See [the asset review](HAND_ML_ASSET_GATE.md).
4. Inspect `site/vendor/mediapipe/SHA256SUMS.txt` and `PROVENANCE.txt`, run `python tests/check_release.py --publish` and all the tests, including GitHub full-origin CI. Check the pinned model and WASM file paths against actual package layout.
5. On an operator-owned iPhone over private HTTPS, run the [Safari device checks](SAFARI_DEVICE_TEST.md) for startup, camera permissions, outages, accuracy, accessibility, and thermal behavior.
6. Record new integration/device/licence evidence on the consolidated review PR, retaining historical draft PRs for traceability. **Do not merge, deploy, recruit participants, redistribute model assets or charge customers** without owner approval and successful gates.

## Scope and risk

- Camera processing stays on-device. In the Chromium probe the CSP blocked the runtime's attempts to send telemetry to Google. See [the asset review](HAND_ML_ASSET_GATE.md).
- Real iPhone runtime loading, throughput, accuracy, stability and user demand remain unmeasured. A debug-only 60-second numeric sampling tool exists but has never been validated on a physical iPhone. A complete sample does not prove recognition accuracy or market demand.
- The `Learn`, `Play`, and `Create` presentations still share the same zone task and are not validated distinct products.
- The proposed privacy text and retention promise still need operator confirmation and any appropriate legal review before recruitment.

## v0.7 safety corrections

- Hand-ML loading has a bounded 12-second deadline; an engine delivered after cancellation/timeout is closed.
- Repeated model startup closes the previous WASM engine rather than leaking it.
- Muted, interrupted, or stale camera frames invalidate **all** calibrations and disable challenge scoring until explicit re-calibration or restart.
- Tests cover loader-timeout and delayed-completion races.
- Source import and GitHub Actions verification are tracked in draft PR #1.
