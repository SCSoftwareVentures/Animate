# ANIMATE — iPhone-only preview decision gate (owner approval required)

**State: BLOCKED — no preview host selected, no external account connected, no model redistributed, and no deployment authorised.** This document records engineering acceptance criteria, not a grant to publish.

## Why the current bench route is insufficient

The existing [Safari bench protocol](SAFARI_DEVICE_TEST.md) requires a separate desktop or LAN host, command-line tooling, a private certificate authority and networking configuration. These are **not available in the owner's iPhone-only ChatGPT workflow**. WebKit-on-Linux tests and two-engine real-image inference are valuable, but **do not measure iOS Safari live camera behaviour**.

The ChatGPT conversation, GitHub code browser and downloaded HTML files are not equivalent to a trusted HTTPS origin capable of exercising iPhone camera permissions. GitHub Pages is a **public static website**; a secret-looking URL is not genuine access control. Do not enable Pages, connect a provider, generate a public URL, or send model binaries to hosting without owner approval.

## Minimum preview architecture

1. **Access** — Owner chooses and explicitly authorises a suitable HTTPS hosting service and account. A private/limited-access preview needs genuine server-side access control; robots.txt, a private link or obscured URL does not protect content.
2. **Immutable build** — Preview must identify the exact commit SHA and an audit manifest of its six text assets. Every staged ML/WASM byte must match the pinned SHA-256 set in `tools/vendor_hand_model.py`. Never silently substitute a CDN or download a latest version.
3. **Runtime rights** — Even a restricted HTTPS preview **delivers model and WASM bytes to a client**. Release-matched redistribution terms and all third-party notices must be reviewed **before any such preview with ML**. A green CI run, an Apache-2.0 metadata declaration or staged inference on an ephemeral runner is not publication permission.
4. **Privacy** — Camera frames stay inside the device. The HTML security policy permits only same-origin requests; verify hosting headers, access logs, IP data and any provider analytics before approving. Do not upload video frames, respondent reports, private ledgers or diagnostics. Prohibit participant recruitment until the privacy and withdrawal notice is approved.
5. **Revocability** — Preview must be terminable, its host-side secrets removed, and cached data handled as permitted by the provider. A prior download cannot be remotely deleted from an observer's device.
6. **No surprise costs** — Service signup, paid hosting, purchases and publication remain owner-controlled actions.

## Two distinct testing gates

### Gate A: No-model baseline (touch, colour, foreground)

The checkout contains only the six text assets. After approval of a host and a privacy/disclosure review, an operator-only, access-controlled HTTPS baseline may measure iPhone permission, canvas, colour/foreground camera, touch accessibility, pause/resume and local data deletion **without shipping any MediaPipe binary**. The Local ML menu must be clearly marked unavailable on this baseline. This cannot validate AI model performance.

### Gate B: Hand-ML preview

**Not yet authorised or prepared for distribution.** Requires resolved exact runtime/model notices, approved vendor bundle, integrity checks, operator permission for external hosting and the full release security review. Only then test actual fingertip tracking on physical iPhone Safari using [the bench protocol](SAFARI_DEVICE_TEST.md), recording false completions, latency, inferred FPS, reload/start failures, camera revocation, battery and thermal observations.

## Required owner decision before any external action

Approval must identify **provider/account, whether access is public or authenticated, exactly which build and assets may be distributed, acceptable cost, and when access should be revoked**. The assistant must not interpret general permission to continue coding as authorisation to deploy or pay.

## Current proof and limitations

- Automated Chromium and Linux WebKit on fixed test fixtures: **passed in the verified GitHub engineering branch**.
- Exact runtime/model pinned SHA-256: present in source; staging verifies them.
- Exact 1.2.3 release-matched native notices and corresponding source: **unresolved**.
- iPhone-only hosting path: **requires owner-approved provider; no deployment**.
- Physical iPhone recognition and demand: **no recorded test evidence**.

[Integration and release gates](INTEGRATION_AND_RELEASE_GATES.md) · [Runtime rights evidence](HAND_ML_ASSET_GATE.md)
