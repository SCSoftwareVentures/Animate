# ANIMATE v0.6 — private engineering validation protocol

**Not permission to recruit, deploy, collect identifiable data or make commercial claims.** Operator must first approve the privacy notice and retention terms.

## Step 0 — integrity and functionality

- [ ] Confirm exact model runtime and weights licence, pinned hash, package size and immutable asset provenance.
- [ ] Run local test suite and full-origin browser CI; publish is blocked if ML assets absent.
- [ ] Inspect deployed origin network requests: only static resources from the same origin; no frame upload.
- [ ] Confirm the service is reachable by HTTPS Safari iPhone, not an in-app web view.

## Step 1 — real iPhone camera/hand ML performance

- [ ] Launch camera, restart 5×, switch front/rear, interrupt with incoming call/Siri, reauthorise, and confirm no false completion.
- [ ] Show **one hand**, vary lighting (bright/normal/dim), three backgrounds, move fingertip across left/middle/right. Record sampled frame count, hand detection rate, inference FPS and p95 latency; keep video on device.
- [ ] Negative control: no hands for at least 600 fresh frames; record false positives and accidental zone completions.
- [ ] Second negative control: two hands / a moving object but no hand; both must **not** count as a valid hand input.
- [ ] Repeat while holding an ordinary household object; hand detection **must not be reported as object recognition**.
- [ ] VoiceOver, landscape/notch safe-area, screen wake, thermals, battery and offline reload after assets cached must be assessed on phone. No test results are available yet.

## Step 2 — evidence interpretation

- Keep results segregated by `detector=colour`, `foreground`, `hand`, and `input=touch`.
- Hand model data are not object-recognition evidence and must not be pooled into the original HSV/foreground benchmark.
- Client exports are pseudonymous and editable; reconcile with a private study ledger before counting verified runs, and state that this is not cryptographic authentication.
- Do not use hypothetical price intent as demand; continue the staged interview/commitment validation only after technical feasibility and operator permission.

## Step 3 — decision gates

A subsequent version may proceed only after verified iPhone performance demonstrates a meaningful, repeatable hand-control experience, zero unreviewed external model dependencies, a viable privacy/legal position and a specific customer use case. Abandon or redesign ML mode if latency, recognition errors, phone compatibility or rights are unacceptable.
