# ANIMATE — Physical iPhone camera-performance measurement (operator-only)

**Status: measurement tool implemented in a draft branch, not yet tested on an actual iPhone.** No HTTPS preview host has been authorised, so these are future acceptance procedures, not completed device results.

## Purpose and limits

The `?debug=1` engineering view includes an explicit **Start 60-second sample** button. Use it only after ANIMATE has been served from a separately approved, authenticated HTTPS origin and Safari has granted the camera. The current **model-free baseline** supports colour or foreground; hand ML is still blocked from distribution pending exact runtime/model rights. Use the physical iPhone, not GitHub's simulated camera.

The sample collects numeric measurement windows only in RAM. It does **not** log camera frames, object coordinates, participant IDs, geolocation, device fingerprints, battery state or thermals. It does not automatically upload anything or create a participant research event. The operator must intentionally copy the summary to retain it. Reloading the page, closing the tab or pressing **Delete local record** clears the in-memory sample.

## Procedure after separately approved hosting

1. Verify the HTTPS site's origin, access restriction, approved build commit and absence of third-party requests. Open it **directly in Safari**, not within a messaging app's in-app browser.
2. Open the page with `?debug=1`. Disclose that this is an internal engineering experiment, then enable the colour or foreground camera. Calibrate an object with steady lighting; make sure a fresh frame is being analysed.
3. Expand **Engineering diagnostics**, then press **Start 60-second sample**. Keep the phone and conditions stable. The app measures the rate of frames **actually analysed**, not simply animation-loop FPS. Avoid covering the camera or switching tabs during the sample.
4. After 60 seconds, confirm the status is `timed`, `complete: true` **and** `coverage.sufficient: true`. The result is labelled `insufficient_coverage` if fewer than 80% of expected one-second windows contain analysed frames, there are too few measured detection calls, timestamps are rejected or a sampling gap exceeds 2.5 seconds. Camera mute, page interruption or early stop must yield `interrupted`, `camera_stopped` or `manual`, with `complete: false`. **A full timer without adequate continuous data is not a pass.**
5. Use **Copy numeric summary** only after reviewing it. Store it in the private engineering record; do not paste raw browser diagnostics, user-agent strings, record IDs, camera screenshots or participants' responses into public GitHub issues.
6. Separately note the *manually observed* environmental condition, iPhone model and iOS/Safari version (if you choose to disclose them privately), camera orientation, battery change/heat, permissions, interruptions, perceived lag, and whether the challenge actually completes. Those items are **not** measured automatically by this tool.
7. Repeat at least three stable sessions per relevant camera method, then also run explicit negative controls (object absent, multiple moving regions, camera permission denied, tab backgrounded, interrupted stream). Report attempts and failures, not just the best run.

## Interpretation

The numeric report includes:
- `analysedFps`: minimum, median, 95th percentile, maximum and number of one-second throughput observations
- `animationLoopFps`: separate rendering/animation-loop metric, **not** camera or recognition throughput
- `inferenceMs`: sampled location/detection call latency distribution. This excludes browser drawing, camera exposure and display latency
- `inferredFrames`: number of actual detection operations; a model's intentionally skipped/throttled frames do **not** count
- `interruptions`, `observedMs`, `status` and `complete`: track whether a full observation was recorded without an interruption
- `coverage.requiredWindows`, `coverage.positiveAnalysedWindows`, `coverage.largestGapMs`, `coverage.rejectedWindows` and `coverage.sufficient`: measure continuity rather than assuming a timer alone establishes usable footage. For a 60-second sample, the configured **80% minimum** is an *engineering data-adequacy threshold*, **not** proof that the tracker is accurate or that FPS is commercially acceptable.
- `recognitionAccuracyMeasured: false` and `commercialDemandMeasured: false`: machine-readable reminders that this test establishes neither ground-truth recognition accuracy nor buyer willingness to pay
- `unmeasuredLatencySamples`: values excluded once the fixed RAM cap is reached or a latency falls outside its supported range. Nonzero means the timing distribution is incomplete

**Do not interpret** a 60-second completed record, a simulated Chromium/WebKit CI pass or a high animation-loop FPS as proof of recognition accuracy, hand-ML product readiness, acceptable battery/thermal performance or willingness to pay. Those require independent physical-device trials and commercial validation.

## Release boundary

This instrument is for the model-free operator baseline until the MediaPipe redistribution gate is actually resolved. All code remains unmerged. Neither this tool nor these instructions create an external host, a public/private preview, model distribution permission or consent to recruit participants.

See [the owner-controlled preview decision gate](IPHONE_PREVIEW_DECISION_GATE.md), [the physical Safari protocol](SAFARI_DEVICE_TEST.md) and [exact runtime rights blocker](HAND_ML_ASSET_GATE.md).
