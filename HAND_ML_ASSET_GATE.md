# ANIMATE v0.6 — hand ML model and runtime gate

## Proposed pinned dependencies (subject to independent review)

- Runtime: Google's `@mediapipe/tasks-vision` npm package, **version `1.2.3`**, installed by npm with lifecycle scripts disabled; runtime JS/WASM copied locally into `site/vendor/mediapipe/`.
- Candidate trained model: Google's Hand Landmarker float16 model bundle, version `1`:
  `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task`
- Model hash: **NOT KNOWN OR VERIFIED HERE**. Need a third-party trusted source or independent publisher verification before locking. `--probe-model-hash` is just a downloaded-file digest, not an authenticity certificate.
- Licence: the MediaPipe open-source *code* carries Apache-2.0; licence/redistribution terms for **these exact model weights** require independent confirmation before bundling or resale. Do not infer one from the other.
- Asset bytes: unknown, because the assets were not downloaded. The previous proposed 10 MB ML asset budget remains **unverified**.
- Platform: MediaPipe Tasks Vision documents Web API `HandLandmarker.detectForVideo`; test exact behaviour under Safari iPhone, including WASM compilation with meta CSP before claiming support.

## Security and data boundaries

1. All weights, WASM and ESM loaded from the **same static origin**. No runtime CDN, remote inference, telemetry endpoint, or cross-origin fallback.
2. Default `connect-src 'self'`; `script-src 'self' 'wasm-unsafe-eval'` to permit same-origin resources and WASM compilation, without broad `unsafe-eval`. iOS compatibility not verified.
3. A single local index-finger tip is mapped to three zones. Multi-hand cases, invalid coordinates and stale camera data do not count as success. Throttled frames are not new evidence.
4. Every successful hand-camera run carries `detector: hand`, `model: mediapipe-hand-landmarker-float16-v1`, and build `0.6.0`. This is **client-side untrusted reporting** and is not proof that a real person or model generated the record.
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

No assertion is made that a licence inspection or full binary integrity review was completed by this package author.
