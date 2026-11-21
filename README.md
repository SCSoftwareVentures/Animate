# ANIMATE v0.7.0 — Engineering hardening candidate

**Status: candidate source and tests only. The verified source is on a draft engineering branch, while `main` still contains a README only.** No merge, hosted preview, model redistribution, external recruitment, financial commitment or released consumer product has been authorised.

**Start buyer review here:** [Single cumulative source-and-evidence index](BUYER_REVIEW_INDEX.md), [acquisition diligence dossier](ACQUISITION_REVIEW_DOSSIER.md), and the draft full-diff pull request against `main`. Prior chained drafts remain engineering history; they are not merged and should not be individually mistaken for production releases.

**Last verified engineering baseline before this snapshot:** commit `31e12be76731e87beab99b32e8f49757e0983981`, [GitHub Actions #41](https://github.com/SCSoftwareVentures/Animate/actions/runs/44871344311): 75 core checks, 51 Chromium simulated-camera checks, 4 JavaScript-to-Python packet-contract checks, and all configured security, WebKit, and pinned-fixture inference steps passed. Those results belong **only to that SHA**, not automatically to this review-documentation commit. Review the cumulative PR's own exact-SHA CI before acceptance.

**Real-device, legal and commercial blockers:** No physical iPhone Safari camera trials, independently measured recognition accuracy, demonstrably authenticated $0 HTTPS preview, verified model/runtime redistribution clearance, verified user demand, qualified acquirer offer or supported exit valuation. The available model-free ZIP is unhosted and **not access-controlled**. No model assets are included in the public source or model-free ZIP.

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

## Operator-only evidence packet in iPhone Safari (draft)

The `?debug=1` screen includes a RAM-only collection tool for authorised physical-device trials. It requires explicit self-declarations, records complete and incomplete 60-second and 10-second samples separately, and can export a private JSON packet directly via Safari without an app, server, cloud API or computer. All provenance and accuracy claims remain unverified. This is not an approved deployment: [future operating protocol](IPHONE_EVIDENCE_AUDIT_PROTOCOL.md).

## Offline iPhone evidence audit (unverified operator reports)

The optional offline validator `tools/audit_iphone_evidence.py` rejects incomplete, contradictory or personally identifying data fields in future self-reported camera-trial packets. It counts all attempts and never certifies device authenticity or recognition accuracy. [Protocol and explicit limits](IPHONE_EVIDENCE_AUDIT_PROTOCOL.md).

## Integrated draft controls and $0 packaging

An operator-only zone probe now counts absent/expected/wrong-zone results under self-labelled conditions, with per-second frame coverage required; this is **not independently verified accuracy**. The $0 preview ZIP remains offline and has **no built-in authentication**. A hosting dashboard setting marked Private cannot certify private site asset delivery. No distribution is authorised.

## Scope and risk

- Camera processing stays on-device. In the Chromium probe the CSP blocked the runtime's attempts to send telemetry to Google. See [the asset review](HAND_ML_ASSET_GATE.md).
- Real iPhone runtime loading, throughput, accuracy, stability and user demand remain unmeasured. A debug-only 60-second numeric sampling tool exists but has never been validated on a physical iPhone. A complete sample does not prove recognition accuracy or market demand.
- The `Learn`, `Play`, and `Create` presentations still share the same zone task and are not validated distinct products.
- The proposed privacy text and retention promise still need operator confirmation and any appropriate legal review before recruitment.

## v0.7 safety corrections

- Hand-ML loading has a bounded 12-second deadline; an engine delivered after cancellation/timeout is closed.
- Repeated model startup closes the previous WASM engine rather than leaking it.
- Muted, interrupted, or stale camera frames invalidate **all** calibrations and disable challenge scoring until explicit re-calibration or restart.
- Short null/ambiguous detection frames preserve only bounded earlier progress, never add unobserved time toward confirmed zone dwell; sustained alternating dropouts fail closed.
- Tests cover loader-timeout and delayed-completion races.
- Source import and GitHub Actions verification are tracked in draft PR #1.
