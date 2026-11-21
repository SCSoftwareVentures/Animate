# ANIMATE v0.6 — ML spike status and next acceptance gate

A browser-facing MediaPipe Hand Landmarker integration adapter and application lifecycle integration have been implemented, but the actual trained model and runtime are **not bundled** in this release. Therefore, genuine hand ML inference is unverified. This is **not** general household-object recognition.

1. Complete the binary acquisition, independent hash/provenance review and redistribution-rights check in `HAND_ML_ASSET_GATE.md`.
2. Run CI full-origin tests after vendoring local assets and confirm the actual library API works. Ensure runtime/test build reports model exact version and asset hash.
3. Run on real iPhone Safari with one/two hands, no hands, varying backgrounds and lighting. Collect inference FPS and frame-level false positives without uploading imagery.
4. Compare actual useful *hand control* against touch-control completion and reliability. Keep colour/foreground baseline comparisons separate because they are object-location heuristics, not hand input.
5. Only after real ML inference and iPhone feasibility are demonstrated should we consider a distinct household-object detector and the user-demand interview/pilot protocol.

**Open unknowns:** iOS media stream stability, ModelAssetPath/ESM/WASM layout for the pinned npm version, browser CSP compatibility, model redistribution rights, cold-start time, thermal throttling, battery life, frame latency, false acceptance rate and whether the interaction solves a customer problem.
