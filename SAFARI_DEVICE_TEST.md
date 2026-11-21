# ANIMATE v0.7 internal iPhone Safari bench

> **Owner approval required.** These instructions assume a separate computer/LAN host, so they are **not executable inside the iPhone-only ChatGPT workflow**. Nothing is deployed. The included bench server refuses MediaPipe binary distribution, even on a private LAN, while exact-runtime rights and attribution remain unresolved. See [the iPhone-only preview decision gate](IPHONE_PREVIEW_DECISION_GATE.md).

Physical iPhone results are pending. Use an operator-owned bench device, an internal operator, and a private test network. Use the operator’s own hand and ordinary objects against a neutral background. Keep faces, documents, personal details, and research records out of view and out of the test. ANIMATE creates a local test record when an adult operator accepts the on-device disclosure. Leave feedback empty and keep the record on the device for the duration of the test.

## Prepare the HTTPS origin

1. Use a host and iPhone on the same isolated IPv4 LAN. Reserve or verify their addresses, including the iPhone's current Wi-Fi address. Limit inbound TCP port `8443` on the host to that iPhone. Bind to the host’s private LAN address and avoid public tunnels, port forwarding, or public hosting. Restrict internet egress on the bench network and keep the iPhone on that network during testing.
2. Use a short-lived server certificate from a bench CA the iPhone trusts. The certificate needs an IP subject alternative name matching the host address in the URL, and the server key and certificate must be outside the checkout and staged site. If a device owner manually installs a dedicated test root, enable its trust in **Settings → General → About → Certificate Trust Settings** and remove it after the session. Transfer only the CA certificate to the iPhone. Treat any certificate warning as a failed setup. [Apple certificate trust instructions](https://support.apple.com/en-us/102390)
3. Record the reviewed commit, then create a **model-free** candidate outside the checkout. The builder verifies the app files, removes the unapproved ML selection, and records a SHA-256 manifest outside the served directory. This requires a separate host, not available in the owner's iPhone-only workflow.

   ```sh
   bench_dir=$(mktemp -d /tmp/animate-safari.XXXXXX)
   python tools/build_baseline_preview.py --output "$bench_dir/baseline"
   ```

4. **Do not serve MediaPipe model/WASM files** on any preview (including a private LAN) while the exact-version redistribution notices and source obligations remain unresolved. Model staging in CI is test-only. See [the runtime/model gate](HAND_ML_ASSET_GATE.md).

5. **Only after explicit owner approval** of the host, certificate, privacy and network controls, set `host_ip`, `iphone_ip`, `bench_cert`, and `bench_key` and serve the signed **no-ML** baseline. The server verifies the builder manifest, exact commit and all staged bytes; requests for model binaries are not served. Its HTTP policy also prevents framing and suppresses extraneous sensor permissions.

   ```sh
   python tools/serve_safari_https.py --baseline-only \
     --site-dir "$bench_dir/baseline/site" --bind "$host_ip" \
     --client "$iphone_ip" --cert "$bench_cert" --key "$bench_key"
   ```

6. Open the printed HTTPS URL with `?debug=1` in Safari. Confirm `window.isSecureContext === true` using Safari Web Inspector or the app's diagnostics after starting a camera baseline. The wrapper serves the existing app CSP and only known static files. Check Safari Web Inspector for actual same-origin requests and any blocked cross-origin attempts. A CSP warning for blocked Google metrics is evidence of policy enforcement. Record any actual cross-origin request, uncaught exception, or successful camera startup despite a certificate problem as a failure.

## Device checks

**Not yet tested on an actual iPhone.** Only the no-ML baseline would be eligible for owner-authorised device testing. All hand-model candidate tests in the table are deferred until separate rights and hosting approval; they are not executable with the currently bundled bench server.

Start each independent test with a fresh challenge. Use the Play sequence of middle, left, and right for repeatable comparisons. For timing, start after the operator grants camera permission and the UI begins loading the model.

| Check | Procedure and expected result |
| --- | --- |
| Baselines and access | Try camera without permitting access, then allow it and retry. Verify a clear error on denial, touch remains available, and the camera indicator ends after Stop. Complete the touch task with VoiceOver and confirm target and progress are announced. Run colour with a saturated object and foreground with 12 fresh empty-scene frames, then complete their zone tasks. |
| Absent assets | Select Local ML on the baseline stage. Verify an initialization error, `Not started`, disabled Start, no scoring, and the camera indicator ending. Repeat, then run a baseline and the touch fallback. |
| First load and repeated startup | On a future separately reviewed ML candidate, close the tab and clear website data for the test origin before each of three cold loads. For three warm restarts, use Stop and Enable camera. Note the elapsed load time and ready or failure UI. Successful attempts reach `Live camera` with `hand.ready` true. A load failure leaves Start disabled and releases the camera. The app's hand-loader deadline is 12 seconds from the beginning of model loading, separate from permission or camera startup time. |
| One-hand positives | Complete the three-zone task with one index fingertip three times per condition. Use bright indirect light with a plain background, ordinary indoor light with clutter, and dim light with clutter. Include front and rear camera and check that mirror orientation matches the visible target. Record hit or miss, completion time, and any false hits. |
| Negative controls | Run three fresh or reset challenges each with no hand, two distinct hands in view, and a single hand held in the wrong zone. Keep each observation running for at least the typical completion time measured above. Expect zero completions and zero zone hits in those conditions. For two hands, watch for the ambiguity message and distinguish a frame that detected only one hand from a frame that reported ambiguity. |
| Interruption and re-arm | While a task is active, switch apps or lock and unlock the phone. Resume Safari and try to score before re-arming. Expect no scoring on interrupted or stale data. Re-enable camera and repeat calibration or foreground capture where applicable, and restart hand mode for a fresh engine. Repeat Stop/Enable and monitor the camera indicator. |
| Runtime, stability and heat | After the warm-up, run hand tracking for 10 minutes in the ordinary-light condition, pausing if Safari becomes unresponsive or the phone reports a thermal warning. Sample `analysedFps` and changes in `hand.inferenceCount` each minute, plus `hand.avgMs`, `hand.maxMs`, and `hand.errors`. Note drops, stutter or unexpected restarts. Treat ≥15 inferred FPS as the existing engineering hypothesis and record how often it holds. Record coarse battery change and observed heat without identifying device metadata. |
| Local state and recovery | Reload with local storage available, confirm the bench record restores, then use **Delete local record** and confirm the entry screen returns. Keep Share, Export, importing participant files, and feedback out of the bench run. |

## Record the outcome and close the bench

Keep only an internal engineering summary with commit, iPhone model, iOS and Safari versions, camera orientation, condition, variant, elapsed load and completion times, inferred FPS and latency, error or blocked request category, observed thermal symptoms, and pass/fail for each check. Preserve the number of attempts and failures for each condition. Avoid screenshots with camera frames, complete console downloads, record IDs, precise device identifiers, or notes about people.

Stop both the app camera and the HTTPS process. Clear the test origin's Safari website data, remove the temporary CA profile or trust grant, and remove the temporary inbound firewall rule. Keep stage and keys outside the repository and dispose of throwaway material after the review. Physical Safari compatibility, asset licensing, and public release approval remain independent gates. [Integration and release gates](INTEGRATION_AND_RELEASE_GATES.md)
