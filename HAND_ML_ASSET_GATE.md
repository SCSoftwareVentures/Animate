# ANIMATE v0.7 — hand ML model and runtime gate

## Pinned asset evidence

- The Hand Landmarker float16 `/1/` bundle is 7,819,105 bytes. The Google Cloud generation `1682480004222387` and immutable model record both match Google's SDK SHA-256 pin `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`. The linked model record declares Apache-2.0 for the exact bundle. The bundle contains detector and landmark TensorFlow Lite models and labels. The model card describes real and synthetic training data separately. Keep the model attribution, Apache-2.0 text, applicable upstream notices, and model metadata with any operator-approved redistribution. [Google SDK pin](https://github.com/google/flutter-mediapipe/blob/af530908232a08d6040028681e8ea4993534306b/packages/mediapipe-task-vision/lib/models.dart#L72-L78) · [Task documentation](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker#models) · [Immutable model record](https://huggingface.co/litert-community/MediaPipe-HandLandmarker-Full/tree/74806d5014cdd5bd6ce94a80a0e4e93ae4cf2f9b) · [Apache-2.0 redistribution terms](https://www.apache.org/licenses/LICENSE-2.0#redistribution)
- The `@mediapipe/tasks-vision@1.2.3` tarball matches the npm registry SHA-512 and Google's sample lockfile. The ESM bundle, classic and module loaders, and their two WASM binaries total 30,160,730 bytes. With the model the payload totals 37,979,835 bytes before transport compression. [npm registry record](https://registry.npmjs.org/@mediapipe%2Ftasks-vision/1.2.3) · [Google sample lockfile](https://github.com/google-ai-edge/mediapipe-samples-web/blob/776b1878bd972de5ec85f96a4588cba840f5a1cc/pnpm-lock.yaml#L237-L238)
- The runtime package declares Apache-2.0. Its tarball omits `LICENSE` and `NOTICE`. The upstream maintainer confirmed Apache 2.0 and acknowledged the packaging issue. The four npm JS/WASM loader and binary digests differ from the tagged source manifest. The embedded OpenCV and OpenCV contrib revisions resolve to upstream source. The WASM banner references Eigen 3.4.0 while a nearby notice-bearing prerelease lists 3.3.90. That prerelease has byte-identical loader JS and different WASM bytes. The release-matched notice set and corresponding source for applicable file-level obligations remain unresolved, so public vendoring and publishing remain blocked. [Upstream issue](https://github.com/google-ai-edge/mediapipe/issues/6403) · [Tagged source manifest](https://github.com/google-ai-edge/mediapipe/blob/1b9800ed7baddd397b888eaaaf0c841fe0358241/third_party/wasm_files.bzl#L13-L35) · [OpenCV revision](https://github.com/opencv/opencv/commit/e4f78fbcf1a773fbed69e14500e8b734963eb585) · [OpenCV contrib revision](https://github.com/opencv/opencv_contrib/commit/b67a855188a3d683813731010f6d39ac614733a4) · [Adjacent prerelease NOTICE](https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.2.2-rc.20261111/NOTICE)

## Private test bundle

The staging command verifies the npm archive SHA-256 and all six payload digests. It copies the exact app files and runtime/model payloads into a new directory outside Git checkouts. The stage has no publish metadata. GitHub Actions uses the same path on its ephemeral runner, serves only loopback assets during inference, and removes the inputs and stage after the job step. It fetches the exact Google test fixture with a pinned hash and stores no fixture in the repository. [Google test fixture pin](https://github.com/google-ai-edge/mediapipe/blob/a84de5639a255fbb5eb801dcd311350e6479e91e/third_party/external_files.bzl#L1272-L1276)

```sh
stage=$(mktemp -d)
python tools/vendor_hand_model.py --stage-test --site-dir "$stage/site" \
  --runtime-archive "$runtime_archive" --model-file "$model_file"
python tests/test_real_hand_browser.py --site "$stage/site" --fixture "$fixture"
```

The private test covers real positive and blank-frame inference, loader lifecycle and fail-closed cases. It reports cold and same-page load time, first and steady inference latency, and Linux renderer proportional memory. The [iPhone bench runbook](SAFARI_DEVICE_TEST.md) covers separate HTTPS camera and device checks.

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

- Operator reviews and records redistribution terms and attribution for the exact model and runtime. Set the reviewed licence/attribution SHA-256 only after that review. The installer and publish checker enforce the reviewed pin.
- `python tests/check_release.py --publish` passes and a full GitHub CI run passes.
- A physical iPhone produces stable hand tracking at **≥15 inferred FPS** as an initial *hypothesis*, with false task completion rate measured in negative controls; no claimed threshold passes without evidence.
- If stable iPhone performance or model licensing cannot be demonstrated, do not ship the ML mode. Use touch and existing baselines for controlled private testing only.

## Technical references checked while planning

- Google AI Edge MediaPipe Hand Landmarker Web documentation: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
- Google AI Edge Web setup guide: https://developers.google.com/edge/mediapipe/solutions/setup_web
- Google MediaPipe code licence: https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE
- Runtime package: https://www.npmjs.com/package/@mediapipe/tasks-vision
