# ANIMATE v0.7 — hand ML model and runtime gate

## Pinned asset evidence

- The Hand Landmarker float16 `/1/` bundle is 7,819,105 bytes. The Google-hosted bytes match the SDK's pinned SHA-256 and the model record: `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`. Google's task documentation links to the exact model repository, which declares Apache-2.0 for the bundle. The linked older model-card PDF lists Apache 2.0 in its documentation table. Record redistribution and attribution review for the exact weights before bundling. [Google SDK pin](https://github.com/google/flutter-mediapipe/blob/af530908232a08d6040028681e8ea4993534306b/packages/mediapipe-task-vision/lib/models.dart#L72-L78) · [Task documentation](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker#models) · [Immutable model record](https://huggingface.co/litert-community/MediaPipe-HandLandmarker-Full/tree/74806d5014cdd5bd6ce94a80a0e4e93ae4cf2f9b)
- The `@mediapipe/tasks-vision@1.2.3` tarball matches the npm registry SHA-512 and Google's sample lockfile. The ESM bundle, classic and module loaders, and their two WASM binaries total 30,160,730 bytes. With the model the payload totals 37,979,835 bytes before transport compression. [npm registry record](https://registry.npmjs.org/@mediapipe%2Ftasks-vision/1.2.3) · [Google sample lockfile](https://github.com/google-ai-edge/mediapipe-samples-web/blob/776b1878bd972de5ec85f96a4588cba840f5a1cc/pnpm-lock.yaml#L237-L238)
- The runtime package declares Apache-2.0. Its tarball omits `LICENSE` and `NOTICE`, so the current asset installer refuses it. The upstream maintainer confirmed Apache 2.0 and acknowledged the packaging issue. The four npm JS/WASM loader and binary digests differ from the tagged source manifest. Map the exact prebuilt dependencies and carry their applicable notices and attribution before redistribution. [Upstream issue](https://github.com/google-ai-edge/mediapipe/issues/6403) · [Tagged source manifest](https://github.com/google-ai-edge/mediapipe/blob/1b9800ed7baddd397b888eaaaf0c841fe0358241/third_party/wasm_files.bzl#L13-L35)

## Chromium compatibility

- MediaPipe 1.2.3's WASM glue looks up a global `dbg` callback. The browser exposed ANIMATE's old diagnostics element under that name and runtime initialization threw. Renaming the element let the exact adapter initialize and produce real landmarks from a local test image under the existing CSP.
- The runtime attempted requests to Google's metrics endpoint. The site's `connect-src 'self'` blocked those attempts before any network request. Keep that policy and review telemetry, consent, and diagnostics with the chosen runtime before release. The probe left all assets outside the public checkout. [MediaPipe privacy notice](https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/tasks/web/vision/README.md#privacy-notice)

## Security and data boundaries

1. Load weights, WASM and ESM from the **same static origin**. Keep cross-origin inference, telemetry, CDN loads, and fallback blocked.
2. Default `connect-src 'self'`; `script-src 'self' 'wasm-unsafe-eval'` to permit same-origin resources and WASM compilation, without broad `unsafe-eval`. iOS compatibility not verified.
3. A single local index-finger tip is mapped to three zones. Multi-hand cases, invalid coordinates and stale camera data do not count as success. Throttled frames are not new evidence.
4. Successful hand-camera runs carry `detector: hand`, `model: mediapipe-hand-landmarker-float16-v1`, and build `0.7.0`. Treat these client-side fields as untrusted reporting.
5. The separate colour/foreground object benchmark cannot certify hand ML accuracy. A new ground-truth hand benchmark with physical testers is mandatory.

## Stop/publish criteria

- Operator confirms model licence and checks independent model integrity, packaged assets and source versions.
- `python tests/check_release.py --publish` passes and a full GitHub CI run passes.
- A physical iPhone produces stable hand tracking at **≥15 inferred FPS** as an initial *hypothesis*, with false task completion rate measured in negative controls; no claimed threshold passes without evidence.
- If stable iPhone performance or model licensing cannot be demonstrated, do not ship the ML mode. Use touch and existing baselines for controlled private testing only.

## Technical references checked while planning

- Google AI Edge MediaPipe Hand Landmarker Web documentation: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
- Google AI Edge Web setup guide: https://developers.google.com/edge/mediapipe/solutions/setup_web
- Google MediaPipe code licence: https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE
- Runtime package: https://www.npmjs.com/package/@mediapipe/tasks-vision
