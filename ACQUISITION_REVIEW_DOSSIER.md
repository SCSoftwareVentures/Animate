# ANIMATE — Acquisition diligence and current-source review

**Status: cumulative, draft, source-only acquisition-review candidate.** This is not a production deployment, valuation opinion, paid-customer business, verified physical-iPhone result, licence clearance, offer, or authority to sell or publish third-party assets.

## Definitive review baseline

The primary implementation prior to this review-documentation change is commit `31e12be76731e87beab99b32e8f49757e0983981` (GitHub Actions [#41](https://github.com/SCSoftwareVentures/Animate/actions/runs/44871344311): success). It is **69 commits ahead** of unchanged `main` (`951c00fb4232f690361b2e834a186b8ef917cc96`; one README). There were **22 open draft pull requests** at this audit. This is a significant source-discoverability problem for buyers. The full-diff draft review branch is created specifically to make all changes visible in a *single* comparison to `main`.

The source reviewed by an acquirer must be the **exact final head SHA shown on the cumulative PR**, together with its own full CI result, not merely the earlier #41 result. Do not mix and match historical draft results, deployment artefacts or cherry-picked checks. Previous stacked PRs remain open engineering history; no closure, merge, or publication is implied.

## Current engineering state — no exaggerated claims

| Component | Source and automated evidence | Missing external evidence |
| --- | --- | --- |
| Colour-zone baseline | HSV calibrated-colour tracker, dwell/ambiguity handling, three-zone challenges and repeatable browser tests | Physical iPhone task-success, latency, robustness, accessibility |
| Foreground baseline | Stationary-background difference tracker, calibration lifecycle and interruption fail-closed | Varied realistic scenes and independently observed accuracy |
| Optional hand landmark engine | Same-origin MediaPipe 1.2.3 adapter; SHA-pinned runtime/model staging for test-image inference on CI Chromium and Linux WebKit | Release-matched runtime/WASM notice obligations, approved distribution, real iPhone loading/accuracy |
| Operator diagnostics | RAM-only 60-second performance samples, 10-second absent/zone controls, self-labelled event proxies and bounded packet export | Independently recorded ground truth, physical-device provenance, unbiased trials |
| Integrity and privacy | Fixed-schema reports, incomplete-trial denominators, invalidation of rejected packet, content restrictions, restrictive CSP and local data deletion | Live hosted access test, privacy/legal review, consent and retention signoff |
| Model-free ZIP | Deterministic local ZIP/receipt, SHA-256 checks, no ML binaries or automatic upload | A proven zero-cost hosting route with site-level authentication across **all** assets |
| Automated tests | [CI #41](https://github.com/SCSoftwareVentures/Animate/actions/runs/44871344311) passed: 75 core, 51 synthetic-camera, 4 JS/Python contract, 22 operator-auditor, WebKit/security/rights/preview checks, and pinned test-image inference | Real mobile browser/device compatibility, field performance or independently verified demand |
| Commercial proof | Source and pre-registered validation protocols only | Customer demand, paid commitments, defensible willingness-to-pay, qualified acquisition buyer interest |

The three `Play`, `Create` and `Learn` presentations share fundamentally the same zone-control mechanics. They do not constitute three separately demonstrated products. A working camera demo by itself is not an AI object-recognition platform or evidence of differentiation.

## Security and redistribution gates

1. **No unreviewed binary distribution.** The model and runtime are staged only on temporary CI runners for exact test-image inference; they are not bundled in the code or no-ML preview. `HAND_ML_ASSET_GATE.md` and `tools/audit_runtime_rights.py` document unresolved release-matched notices and third-party/native WASM/source obligations. Do not treat npm `Apache-2.0` metadata as independent legal approval.
2. **No private preview without enforced HTTPS access restrictions.** The offline ZIP contains no password or site authentication. An administration dashboard showing `Private` does not demonstrate that signed-out visitors cannot fetch HTML, JavaScript, styles, or model assets. The site-level, $0 access-control and live request-denial checks remain **BLOCKED / NOT VERIFIED**. Never infer a private deployed site from a build receipt or simulated hosted audit.
3. **No CI-based publication permission.** `.github/workflows/publish.yml` requires manual owner-controlled release inputs and exact-sha variables, and the model licence/source gate remains blocked. There is no launched hosted product.
4. **Do not commit person-level research.** No participant exports, survey data, raw camera frames, session logs, credentials, private investigator notes or buyer contact details should be committed to this public GitHub repository. Audit all branches and any external history separately if exclusivity is important.

## Buyer transaction diligence

**Chain of title and transferability:** Confirm source authorship and ownership of original code, code generated with tools, any external contributions, third-party licences, trademarks and the ANIMATE name. No legal ownership opinion, assignment document or trademark clearance is established. The public repository already exposes source, which can affect exclusivity and competitive transfer value. A buyer must assess whether rights and history are transferable.

**Real-world engineering:** Independently repeat the exact head CI, inspect the model-free app, and test an authorised authenticated HTTPS build on a physical iPhone. Record negative controls, missed target activations, real elapsed latency, crash/permission recovery, frame coverage, accessibility and battery/heat observations. Simulated browser results do not substitute.

**Operating and commercial evidence:** There is no verified hosting service, production incident record, paid customer base, revenue, independently qualified user adoption, buyer acquisition commitment, or defensible market-based sale price. A product buyer may value a documented source prototype, but engineering investment alone does not determine sale value. No guaranteed exit or estimate is claimed.

**Restrictions:** No public deployment, provider account/credit change, paid service, owner contact, recruitment, asset redistribution, merge to main, repo transfer or visibility change occurs from this document or draft PR.

## Honest decision gates

- **Source review:** Eligible for internal technical inspection **only if the cumulative final-head PR CI succeeds** and a reviewer signs off its diff. Keep merged/released status as false.
- **Free physical iPhone preview:** BLOCKED pending verified full-site authentication, owner approval, HTTPS/CSP response audit, actual Safari camera behaviour and private handling of observations. A no-cost host is *not yet identified as satisfying every requirement*.
- **Model-based redistribution:** BLOCKED pending exact-version rights, corresponding notices and source obligations.
- **Measured product reliability:** UNVERIFIED without physical device trials under an advance protocol with all failures included.
- **Commercial competitiveness and buyer appeal:** UNVERIFIED without representative demand, competing alternatives and qualified buyer evidence.
- **Sale contract:** NOT PREPARED; ownership, asset schedule, warranties, privacy, intellectual property and transfer terms require owner and competent legal review.

Start with [the buyer review index](BUYER_REVIEW_INDEX.md), then the [model rights gate](HAND_ML_ASSET_GATE.md), [operator iPhone metrics](IPHONE_DEVICE_METRICS_PROTOCOL.md), [operator evidence audit](IPHONE_EVIDENCE_AUDIT_PROTOCOL.md) and [commercial evidence gate](COMMERCIAL_EVIDENCE_GATE.md).
