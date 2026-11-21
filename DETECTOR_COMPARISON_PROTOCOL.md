# v0.6 clarification

**Only the colour and foreground tracking baselines should be compared head-to-head on the same object scenes.** The new optional MediaPipe Hand Landmarker uses a different input (human index fingertip) and requires a separate comparison to touch controls. It cannot be credited with household-object recognition. Real model assets have not been integrated or tested.

---

# ANIMATE — controlled same-device tracker comparison (proposal)

**Do not recruit participants or publish the website until the privacy notice, operator contact, retention and withdrawal process are approved.** Start with the owner's iPhone only.

## Hypothesis

Can the experimental foreground-difference method reduce the colour tracker's missed detections on low-saturation objects while maintaining a tolerable false-control rate in the same surroundings?

## Predeclared conditions

Hold phone position, camera orientation, distance and target task fixed. Run both methods on each of:

- Objects: bright blue, grey/white and a red toy or household object.
- Light: bright, ordinary indoor and dim conditions.
- Background: plain neutral and normal cluttered surroundings.
- Negative control: no intended object, but moving hand/shadow and static background in separate runs.

Use method order alternation (colour first in half the trials; foreground first in the remainder) to limit simple ordering effects. Background mode requires capturing 12 fresh frames with the scene empty; record its setup overhead. This adds setup steps, so measure total time to first successful zone separately from FPS/inference time.

## Measurements

- Fresh analysed frames per method, elapsed setup time, completion time, device type/iOS version, ambient conditions, false zone activations and reasons for rejected frames.
- Run `?debug=1&benchmark=1` on the approved HTTPS page; mark whether the designated object is present or absent. These labels are not video-level ground truth and 600 correlated frames are not 600 independent trials.
- Record *video-free* benchmark summaries only. Keep private ledger and exported data separate from source control. Reconcile build `0.5.0`, detector label, ID and date before interpreting results.
- Stop a comparison and recapture an empty background whenever the iPhone moves, the camera is interrupted or illumination shifts substantially.

## Decision rules

- **Adopt as optional fallback only** if it reliably improves the predeclared low-saturation cases without new unwanted completions from hands/shadows in owner-led tests.
- **Do not deploy to customers** if ordinary hands, background movement or shadows cause false zone activations, even if positive detection is better.
- **Do not claim artificial intelligence or general object identity** based on these tests. Advance to a pinned, licensed, locally hosted hand/object ML model only after legal/asset review and device benchmarking.
- Record each failed trial and use evidence from real devices; no after-the-fact threshold tuning to meet the decision gate.
