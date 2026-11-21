# ANIMATE — Single-view source review and buyer handoff index

**Draft-review status, 21 November 2026.** Prepared to make an existing body of work easier to audit without silently merging the work into `main` or claiming production readiness. The canonical review entrypoint is the **single full-diff draft pull request against `main`** created from the verified engineering head plus these documentation changes.

## How to establish what is actually delivered

1. Open the canonical full-diff draft PR; record its **40-character head SHA**, parent `main` SHA and the full changed-file inventory. Earlier stacked PRs are historical sub-diffs. No branch has been merged by this review.
2. Require a successful **exact-head** GitHub Actions CI result and inspect its test steps, not only a badge or a previous-commit pass. The immediately preceding source commit `31e12be76731e87beab99b32e8f49757e0983981` passed [CI #41](https://github.com/SCSoftwareVentures/Animate/actions/runs/44871344311), including 75 core tests and 51 simulated-camera checks. This documentation update must pass a separate workflow.
3. Review `site/index.html`, `site/app.js`, `site/core.js` and the camera-specific modules. The app is a colour/foreground zone-control prototype with an optional, **undistributed** hand-landmark engine. It is not a general-purpose object recogniser and does not deliver three distinct functional products.
4. Review `tests/`, `tools/build_baseline_preview.py`, `tools/build_zero_cost_preview.py`, `tools/audit_iphone_evidence.py`, `tools/audit_runtime_rights.py` and `.github/workflows/`. The six-file model-free baseline and seven-file static ZIP may be built **offline**; neither bundle proves HTTPS privacy, camera usability or model licensing clearance.
5. Review [the acquisition dossier](ACQUISITION_REVIEW_DOSSIER.md) and required external evidence before making price, transferability or release representations.

## Evidence inventory

| Claim | Current supported evidence | Verdict |
| --- | --- | --- |
| Source exists and runs under automated conditions | Exact-SHA JS/browser/security/CI tests on a draft branch | **Engineering only**, conditional on final-head success |
| Browser colour and foreground target scoring | Deterministic virtual-camera tests and local source | **Not physically validated** |
| Pinned MediaPipe hand inference | Chromium/Linux WebKit synthetic-image inference on transient, checksum-pinned assets | **Runtime tested; redistribution blocked** |
| Operator result collection | RAM-only performance/zone controls and manually exported self-labelled JSON | **Unverified self-reports** |
| Secure private iPhone preview at $0 | Offline ZIP, proposed provider/HTTPS audits | **Blocked: no proven authenticated host** |
| Physical iPhone Safari camera accuracy and comfort | No physical device samples | **Not measured** |
| Product-market fit, switching benefit and competition | Proposed protocol; no independently recruited paying users | **Not established** |
| Qualified source-code acquirer or market sale value | No validated offers, purchasers or transaction terms | **Not established** |

## Required next owner decisions — no automatic action

**Before a physical iPhone test:** Approve a genuinely authenticated, no-charge HTTPS host only after confirming full-site denial for unauthorised users. Verify its actual price/limits and privacy terms, then approve a limited private trial. Never use a publicly served GitHub Pages URL, opaque/secret link or client-side password screen as equivalent access control.

**Before ML distribution:** Approve the exact runtime/weights licence and release-matched notices/corresponding source plan; obtain legal input if needed. The current publish gate intentionally blocks redistribution.

**Before listing the software for acquisition:** Review exclusive IP ownership and branding, establish which third-party code is transferable, select a concrete buyer segment, gather external demand evidence if economically viable, and approve accurate buyer-facing claims and sale terms. Public GitHub source visibility may materially affect exclusivity.

**Before merging:** Explicit owner instruction and successful current-head verification. Draft PR creation, test execution and documentation updates are *not* approval to merge or deploy.

## Buyer handoff scope today

What can be inspected: source code, automated tests, CI logs, privacy/security controls, detailed uncertainty and known blockers, and a zero-model offline ZIP build procedure.

What cannot be promised: a hosted product, model usage rights, a signed provenance certificate, audited customer data, production support, retained user traffic, profitable economics, an IP ownership legal opinion, or a saleable price.

**Budget:** no additional spending is authorised; this index requires no account, paid service, hosting, domain, research recruitment or mobile app installation.


## Latest verification and gated follow-up

The latest verified engineering candidate is draft [PR #28](https://github.com/SCSoftwareVentures/Animate/pull/28), exact commit \`59f0db2e433d99fd6f27e3fa0bb77c140c7292be\`, [CI #54 SUCCESS](https://github.com/SCSoftwareVentures/Animate/actions/runs/44883462371). Subsequent host-canary and commercial-preregistration changes live in a **separate unmerged draft successor** and require their own exact-head CI. See [HOSTING_RESEARCH_AND_OWNER_RUNBOOK.md](HOSTING_RESEARCH_AND_OWNER_RUNBOOK.md) and [COMMERCIAL_TEST_REGISTRATION.md](COMMERCIAL_TEST_REGISTRATION.md) for the next blocked evidence gates. No deployment or customer contact has been authorised.


## Netlify private screenshot side-channel — verified security blocker

An actual $0 authenticated, isolated Netlify Drop deployment was tested: all 64 anonymous production and immutable-deploy GET/HEAD access probes returned 401, yet a provider-generated deployment screenshot URL returned a publicly cacheable image containing the **private harmless test marker**. This does not constitute source-code/participant-data leakage because only the harmless canary was uploaded. [HOSTING_SCREENSHOT_SIDE_CHANNEL_GATE.md](HOSTING_SCREENSHOT_SIDE_CHANNEL_GATE.md) documents the failure and the offline neutral-root thumbnail experiment. **No ANIMATE deployment or iPhone camera test is authorised or validated.**
