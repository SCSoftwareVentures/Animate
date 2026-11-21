# ANIMATE — Operator-labelled zone and negative-control trials

**Status: engineering test instrumentation only.** No physical iPhone trial, participant recruitment, verified recognition accuracy or market-demand observation has occurred. A future iPhone-accessible, access-controlled HTTPS preview requires separate owner approval. The optional MediaPipe hand model cannot be distributed until exact runtime/model rights are approved.

## Purpose

A successful three-zone task can be misleading: it does not reveal how often a tracker falsely activates while the target is absent or detects the wrong zone. In the `?debug=1` view, the optional **10-second absence and zone controls** count observations from fresh **analysed camera frames** under one manually declared, stationary condition.

This is a **diagnostic proxy, not independently verified ground truth**. The operator chooses the expected condition, so incorrect labels, target movement or an obstructed view can invalidate interpretation.

## Reproducible procedure after an approved physical-device preview exists

1. Use the reviewed HTTPS preview directly in iPhone Safari and record its build SHA outside public issue comments. Begin a consented operator-only session. Enable the relevant camera detector and calibrate it as instructed. Use a suitable tracked colour object for colour tracking; a stationary empty background is required for foreground tracking. Do not mix different detectors in the same results.
2. Open `?debug=1`, expand **Engineering diagnostics**, and find **10-second absence and zone controls**. Confirm no normal challenge or separate recognition benchmark is running.
3. For the **negative-control trial**, calibrate first, then remove the tracked target completely from the camera view. Select **No target visible** and start the measurement. Keep the camera scene steady for 10 seconds. Record all counts, including unexpected dwell events and ambiguous frames.
4. For a **positive zone-control trial**, select Left, Middle or Right, then keep one target physically within the corresponding visible third for a full 10 seconds. Repeat independently in all three zones. Avoid changing the target's location, illumination or camera orientation during a trial.
5. A valid observation must finish with `status: timed`, `complete: true`, and `coverage.adequate: true`. The sampling gate requires at least 80% of one-second periods represented, at least three analysed frames per required second and no gap exceeding 2.5 seconds. That threshold is a **data adequacy check only**.
6. An early manual stop, camera interruption, insufficient continuous frames, timestamp anomaly or lost camera permission is an incomplete trial. Do not exclude it from the count of attempted trials.
7. Review the numeric report before using **Copy control counts**. The report is RAM-only, not uploaded, and is not inserted into participant events. Never publish raw browser diagnostics, camera frames, identity details or exported participant reports in a public repository.
8. Pre-register the number of attempts, use cases and rejection criteria before looking at results. Repeat the negative controls and each positive zone at least three times in different lighting/backgrounds, and report all attempts, errors and failures.

## Reading the counters

- `expectedCondition`: the **operator's** claim (absent, left, middle, right), not independently captured ground truth
- `detectedFrames`, `undetectedFrames`, `ambiguousFrames`: detector outputs during fresh frames; a detected point is not proof of correct identity
- `correctZoneFrames` / `wrongZoneFrames`: point-zone agreement or disagreement relative to the manually declared zone
- `expectedDwellEvents` / `unexpectedDwellEvents`: dwell-trigger *proxies* that an active challenge could potentially use; these are **not actual successful or failed challenge completions**
- `coverage`: observed time buckets, sampling gaps, rejected time ordering and data adequacy; incomplete data is never automatically considered a success
- `independentlyVerified: false` and `userDemandMeasured: false`: explicit limits on the evidence

A false dwell activation in a labelled-absent scene is an important warning and merits reproduction, but does not by itself establish a statistically valid false-positive rate. A completed trial with no false dwell event is not a reliability certificate. For independent detection accuracy, obtain separately observed ground-truth video or an agreed external observation protocol **only with appropriate consent, privacy review and explicit approval**—never upload frames by default.

## Release boundary

This adds **no telemetry service, tracking pixel, third-party script, user account or automated external data transfer**. It does not authorise external hosting, model distribution, customer outreach or a product-acquisition claim.

Related: [physical iPhone performance protocol](IPHONE_DEVICE_METRICS_PROTOCOL.md), [commercial evidence gate](COMMERCIAL_EVIDENCE_GATE.md), [preview decision gate](IPHONE_PREVIEW_DECISION_GATE.md).
