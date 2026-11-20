# ANIMATE v0.7.0 — Engineering hardening candidate

**Status: not approved for public deployment or participant recruitment.**

# ANIMATE v0.7.0 — local hand-ML integration candidate

**Status: engineer-facing research package, NOT a deployed or fully functioning AI product.** The v0.6 application offers three intentionally distinct tracking implementations:

1. **Colour (baseline):** HSV connected-component tracking of a calibrated, sufficiently saturated object. Not an ML model.
2. **Foreground (baseline):** stationary-camera difference tracking after collecting an empty background. Not an ML model and not object identity.
3. **Hand (new, optional):** same-origin MediaPipe **Hand Landmarker** adapter that turns one hand's index fingertip into a position. This is real ML *only when the reviewed MediaPipe runtime and trained model are installed*. It is **not household-object classification**, not a gesture recogniser, and not included as a functional model in this ZIP.

The environment used to create this package could not retrieve external binary assets. The runtime and model are **not bundled**. Selecting hand mode without the reviewed assets fails closed, closes the camera and preserves the first two trackers. No participants should receive this build.

## Implemented engineering

- `site/hand_ml.js`: local ESM runtime loader for MediaPipe Tasks Vision 1.2.3 and the official float16 Hand Landmarker model v1, index-fingertip extraction, bounded inference frequency, non-monotonic timestamp rejection, multi-hand fail-closed, stop/cancellation, and local-only diagnostics.
- `site/app.js`: hand mode wired into camera lifecycle, frame age and interruption gate, three-zone task scoring, independent `detector=hand` and `model` evidence labels. Touch results are never camera completions.
- `site/core.js`: new build 0.6.0/schema 5, requires linked model provenance in hand results, and reports each tracker separately. Pseudonymous exported JSON is editable, **not** cryptographic proof of use.
- `site/index.html`: camera disclosure and a CSP allowing same-origin model/WASM fetch and `wasm-unsafe-eval` without arbitrary external domains. Real iOS Safari CSP/runtime compatibility is still unverified.
- `tools/vendor_hand_model.py`: optional operator-controlled asset-acquisition workflow with exact npm version, separately reviewed model SHA-256 requirement, redistribution-review attestation, local copying and SHA-256 manifest. This script was **not executed** here.
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

See `TEST_RESULTS.md` for exact results and caveats. The `publish.yml` job now uses `python tests/check_release.py --publish` and is manual-only from `main` (GitHub Actions itself has not run here).

## Completing real ML in Codex or another controlled cloud engineering task

1. Inspect `HAND_ML_ASSET_GATE.md` and conduct an independent review of both the npm runtime and model-weights redistribution terms; record findings. Do **not** assume the runtime's Apache licence covers the separate model bundle.
2. In a network-enabled engineering environment, run `python tools/vendor_hand_model.py --probe-model-hash`; compare the result against trusted provenance, not merely the same file downloaded twice.
3. Only once the model rights and a trusted model checksum are approved, run `python tools/vendor_hand_model.py --install --expected-model-sha256 <REVIEWED_SHA256> --license-reviewed`.
4. Inspect `site/vendor/mediapipe/SHA256SUMS.txt` and `PROVENANCE.txt`, run `python tests/check_release.py --publish` and all the tests, including GitHub full-origin CI. Check the pinned model and WASM file paths against actual package layout.
5. On a real iPhone using Safari over HTTPS, test fresh-load, latency, 3 scene/lighting conditions, multiple hands, camera permission and interruptions, storage, and battery heat. Compare *hand-control reliability* against touch, not against object classification.
6. Open a reviewable pull request. **Do not merge, deploy, recruit participants or charge customers** without owner approval and successful gates.

## Scope and risk

- Never ask participants to upload raw camera video; the page keeps video processing on-device. Downloading the runtime/model from the same static host is necessary, but the app does not send frames or telemetry.
- No current evidence of actual iPhone FPS, model loading, hand detection precision, stability or meaningful consumer demand.
- The `Learn`, `Play`, and `Create` presentations still share the same zone task and are not validated distinct products.
- The proposed privacy text and retention promise still need operator confirmation and any appropriate legal review before recruitment.
- Unrelated GitHub repositories were not accessed or edited, and no GitHub workflow was triggered or published during this change.

**Bottom line:** v0.6 delivers an ML adapter and guarded integration, *not* a pretrained model, completed ML inference on iPhone, or a sale-ready product.


## v0.7 safety corrections

- Hand-ML loading has a bounded 12-second deadline; an engine delivered after cancellation/timeout is closed.
- Repeated model startup closes the previous WASM engine rather than leaking it.
- Muted, interrupted, or stale camera frames invalidate **all** calibrations and disable challenge scoring until explicit re-calibration or restart.
- Tests cover loader-timeout and delayed-completion races.
- The repository upload and GitHub Actions verification remain independent gates.
