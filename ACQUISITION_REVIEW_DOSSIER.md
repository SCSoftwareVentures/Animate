# ANIMATE — Engineering and acquisition review dossier

**Review scope:** consolidated **draft** engineering snapshot. **Not a release, acquisition offer, valuation certificate or evidence of paying customers.** Do not distribute model assets, recruit participants, merge into `main` or deploy without separate owner approval.

## Why this consolidated branch exists

ANIMATE development has been conducted across a chain of dependent draft pull requests, beginning with the Codex source import and continuing through privacy, model-inference, hosting and physical-device measurement safeguards. A reviewer should not have to infer the combined implementation by following many individual diffs. This branch contains the cumulative source, documentation and tests as **one proposed review diff against `main`**.

Earlier PRs remain draft and independent. This consolidation does not silently merge them, approve licences, provide an external web preview or change repository visibility. The consolidated branch must pass its own full GitHub CI after the final documentation change.

## What is in scope

| Module / gate | Grounded engineering status | Limitation |
| --- | --- | --- |
| Colour baseline | HSV calibrated-object tracking, three-zone challenge, browser tests | Not object identity or ML |
| Foreground baseline | Background-difference tracking and stale-camera protections | Requires a suitable stationary scene; not object identity |
| Optional hand landmark adapter | MediaPipe Tasks Vision 1.2.3 / Hand Landmarker float16 v1 adapter; hash-pinned staged test-image inference in Chromium and Linux WebKit | No redistributable runtime/model bundle; no proven live iPhone performance |
| User research evidence | Pseudonymous exported JSON, bounded feedback, role cohorts, evidence denominators, strict dates and local data clearing | Client-editable records are not proof of independent participation, adoption or sales |
| Performance instrumentation | RAM-only 60-second camera sampling, analysed-frame throughput separate from animation FPS, gap/coverage rejection | Not independent accuracy, energy, temperature or demand measurement |
| Baseline preview packaging | Exactly six static assets, no-ML menu disclosure, SHA-256 manifest, temporary runner test | Not hosted; not authenticated in an actual production environment |
| Privacy and host safeguards | Constrained CSP, data-minimising projections, HTTPS bench boundary and simulated authenticated-host audit | Live host policy, logs, consent, access revocation and device tests remain unverified |
| CI | JavaScript unit tests, Chromium and WebKit synthetic suites, staged pinned-model inference, privacy/security/licensing gates | CI is not a physical iPhone, legal clearance or buyer acceptance test |

## Evidence index: verified, historical and still open

The immediately preceding engineering branch, `engineering/animate-device-coverage-integrity` (commit `1c6b1eb145352e55f2a8ee02ef35bcf0b633314c`), passed GitHub Actions **run #25**: 147/147 unit/licensing/security tests and 107/107 browser tests, including staged real-model test-image inference in Chromium and WebKit. These results apply **only to that exact commit**, not automatically to the new consolidated head. The consolidation PR requires a fresh verification before it may be labelled clean.

- **Exact-runtime legal rights:** `HAND_ML_ASSET_GATE.md`, `tools/audit_runtime_rights.py`, and GitHub issue [#10](https://github.com/SCSoftwareVentures/Animate/issues/10). The exact pinned `@mediapipe/tasks-vision@1.2.3` npm archive lacks top-level `LICENSE` and `NOTICE` files; metadata says Apache-2.0 but the appropriate native/WASM third-party and corresponding-source obligations remain unresolved. **Redistribution remains blocked**.
- **Owner-controlled iPhone preview:** `IPHONE_PREVIEW_DECISION_GATE.md`, optional manually gated [GitHub Codespaces path](IPHONE_CODESPACES_OPTION.md), `tools/audit_hosted_preview.py`, and issue [#5](https://github.com/SCSoftwareVentures/Animate/issues/5). The proposed Codespaces route requires explicit owner approval and may incur cloud charges; no Codespace or remotely reachable preview has been created, and the real hosted audit has not been authorised or executed. A URL alone is not access control.
- **Actual device data:** `IPHONE_DEVICE_METRICS_PROTOCOL.md` and `SAFARI_DEVICE_TEST.md`. No measured real iPhone camera recognition, heat, battery or false-completion evidence is recorded.
- **Demand and exit price:** `COMMERCIAL_EVIDENCE_GATE.md`. No qualified customer pilot, verified willingness-to-pay commitment, acquirer offer, or defensible exit valuation is recorded.

## Buyer diligence: what a prospective acquirer must inspect

**Source and ownership.** Inspect the source tree and commit/PR history, contributor permissions and the chain of title for all software and graphics. Commit history alone is not a legal assignment of intellectual property. Confirm ownership of contributions, rights to use the project name, any external assets, and whether existing public repository exposure affects the buyer's exclusivity expectations. **No source-code ownership, trademark clearance or transferability legal opinion is represented by this dossier.**

**Third-party rights.** Review applicable licences for dependencies, runtime/WASM, the trained model and any copied fixture or source content. Do not rely on the `Apache-2.0` npm metadata field alone. There is no permission to copy the CI-staged binary bundle into a sale deliverable until the exact obligations have been resolved.

**Security and privacy.** Review `tests/check_release.py`, `.github/workflows/publish.yml`, `tools/build_baseline_preview.py` and `tests/test_hosted_preview_audit.py`. Verify that no participant exports, credentials, research ledgers, persistent tracking data or unreviewed ML binaries are committed. Privacy notices and retention wording need owner/legal review before any public-facing pilot.

**Reproducibility.** Run the checkout's existing CI on the proposed acquisition branch. Compare the exact head SHA and workflow outcome. Verify there is no hidden manual production service or undocumented runtime required for the model-free baseline. Model-based operation requires independently reviewed assets and a separate, authorised distribution procedure.

**Operations and post-sale costs.** The current source is an experimental local-first web app, not a proven SaaS with production support. There is no verified hosted environment, paid-customer revenue, production incident history, usage analytics or market-tested support burden. Any projected operating costs, conversion or revenue model would be an estimate until evidenced.

**Commercial defensibility.** A technical demonstration does not show product-market fit, competitive dominance or attractiveness to a buyer. Choose a specific use case, gather independent user evidence and compare with actual alternatives before claiming differentiation. Acquisition interest must be independently documented rather than inferred from a working prototype.

## Hard go/no-go gates

1. **Current candidate:** source is suitable for further code review and offline testing, subject to successful current-head CI. Do not call it a completed product available for sale to end users.
2. **Model-free private iPhone pilot:** owner must separately choose and approve hosting, genuine access control, privacy terms, budget if any and external network activity. Validate the exact staged candidate and run physical Safari tests. A code-only PR is not deployment permission.
3. **ML distribution:** exact runtime and model rights, release-matched native/WASM notices and source obligations must be reviewed; `tests/check_release.py --publish` and fresh CI must pass. Model distribution is independently owner-controlled.
4. **Customer research:** separate owner consent to outreach, proper privacy/participant terms, pre-registered metrics and independent recruited participants. No invented market proof.
5. **Acquisition diligence:** chain of title, third-party component schedule, legal/transferability review and a qualified buyer assessment. No guaranteed exit or estimated selling price in this dossier.
6. **Integration:** owner authorisation required for merging, releasing, transferring repository ownership or changing repository visibility. Draft PR status must remain unchanged until approval.

## Change control for reviewers

Use the single consolidated draft PR to `main` as the **source review entrypoint**. Its GitHub CI status and file diff, not an old conversation or a staged local test, are the authoritative indicators of what has been verified. The original dependent PRs remain available as engineering history. If any underlying PR changes, compare and reconcile it with this branch and rerun the necessary checks before making a claim about the consolidated snapshot.

**This document itself makes no external contact, sends no research data, grants no rights and approves no release.**
