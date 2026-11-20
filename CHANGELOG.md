# v0.7.0 — ML lifecycle and interruption safety

- Bounded ML initialization deadline, clean cancellation, and no engine leaks across restarts.
- Camera interruption clears colour reference and disables scoring until re-calibration.
- New targeted regression tests.
- Real model weights, iPhone performance, model licensing and CI remain unverified.

# ANIMATE engineering changelog

## 0.6.0 (21 November 2026) — optional local hand ML adapter

- Built `site/hand_ml.js` with MediaPipe Tasks Vision 1.2.3 integration points and Hand Landmarker float16 model v1 path. The source package has **no model or runtime binary**: actual ML inference is therefore *not* shipped or verified.
- Added `hand` to the UI and tracker lifecycle with fail-closed behaviour on absent assets, stale camera streams, more than one hand, invalid coordinates and runtime errors; separate model provenance recorded in client evidence.
- Core schema bumped to 5 and build to 0.6.0; previous experiments remain in their separate localStorage namespace. Every tracker retains its own outcome counts.
- Implemented manual asset-pinning workflow and fail-closed publication gate. Pages would be blocked if the assets are absent or manifest integrity fails.
- Expanded regression tests for hand mapping, frame throttling, stop-during-init, untrusted model provenance, simulated hand flows and missing asset handling.
- Changed CSP from `connect-src 'none'` to `connect-src 'self'` and permits `wasm-unsafe-eval`, strictly for bundled models/WASM. No remote domains allowed.
- In this environment full-origin Chromium navigation was blocked by administrator; no CI, Safari, iPhone, licence or model binary verification completed. No public release.

## 0.5.0

Dual deterministic tracking baselines (colour and foreground), benchmark, evidence boundaries and synthetic checks. Consult prior package for historical results; they are not evidence of hand ML performance.
