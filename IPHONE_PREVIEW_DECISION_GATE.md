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

**Access-control clarification:** A cloud project marked Private in its management dashboard does not prove the deployed site and every JS/CSS URL deny unauthorised HTTP visitors. No ZIP upload is approved until a truly free site-level authentication method is independently validated; otherwise the $0 hosting route stays BLOCKED.

## Two distinct testing gates

### Gate A: No-model baseline (touch, colour, foreground)

The checkout contains only the six text assets. After approval of a host and a privacy/disclosure review, an operator-only, access-controlled HTTPS baseline may measure iPhone permission, canvas, colour/foreground camera, touch accessibility, pause/resume and local data deletion **without shipping any MediaPipe binary**. The Local ML menu must be clearly marked unavailable on this baseline. This cannot validate AI model performance.

### Gate A implementation — verified candidate only, never a deployment

The repository includes `tools/build_baseline_preview.py`, which creates an **offline, non-distributed candidate** in a new directory *outside the repository*. It copies exactly the six app assets, removes the Local ML selector, includes an accessible disclosure, and writes a SHA-256 source-commit manifest outside the served `site/` folder.

CI additionally runs the result through Linux WebKit with a real loopback origin, including consent, touch-control, pseudonymous export, and local deletion tests. CI destroys the temporary candidate at the end of the job. **No GitHub Pages, preview provider, public URL, downloadable distribution artifact or remote hosting is created.**

A future authorised preview must use the exact inspected candidate, genuine HTTPS and owner-approved access controls. Because baseline camera processing is still user-facing, its privacy notice and hosting traffic/log behaviour require approval before it is served to anyone. The staged candidate **cannot** validate hand ML or count as physical iPhone evidence.

The public GitHub Pages workflow remains manual and also requires an explicit confirmation, an owner-controlled repository approval variable, a three-way exact commit SHA match, and the unchanged `tests/check_release.py --publish` gate. Merely generating a baseline candidate does **not** meet the ML publish checker, does not set approval variables, and does not authorise publication.

### Local HTTPS bench delivery hardening (development only)

The alternate computer/LAN server `tools/serve_safari_https.py` is now restricted to the **six-file model-free baseline** emitted by `tools/build_baseline_preview.py`. It checks the baseline candidate's exact Git commit, external manifest, approved filenames and SHA-256 hashes, and refuses all model/WASM distribution. Direct requests for unlisted paths are not served. The HTTP response adds **`frame-ancestors 'none'`**, `X-Frame-Options: DENY`, `Permissions-Policy` with camera restricted to the origin, `Cross-Origin-Resource-Policy: same-origin`, no-store caching and no referrer leakage. An offline CI loopback test checks those headers, forged Host requests, unsigned staging and tampering. This is not a remotely accessible preview and does not implement hosted authentication.

**Important:** The bench server requires a separate machine and an operator-controlled TLS certificate; it cannot run from this iPhone-only ChatGPT environment. Do not use the old LAN procedure as an assumed deployment route. A true iPhone-only, revocable HTTPS preview still requires a separate owner-approved provider and privacy/access review. Physical Safari measurements remain absent.

### Hosted HTTPS preview preflight — prepared, but network auditing is disabled

The offline tested `tools/audit_hosted_preview.py` can verify a future **operator-approved, authenticated HTTPS origin**, without creating or deploying a site. Its normal CI exercises **in-memory adversarial responses only**: no DNS resolution, remote requests, cloud account, uploaded files or credentials are used in CI.

It is intentionally **not a way to launch a preview**. A live audit is disabled unless all of the following are present: an explicit `--allow-network-audit` opt-in, an exact approved public HTTPS hostname from `ANIMATE_APPROVED_PREVIEW_HOST`, an authenticated session cookie supplied securely through `ANIMATE_PREVIEW_AUTH_COOKIE`, and a locally verified six-file baseline candidate. Tokens must **never** appear in a URL, command line, GitHub issue, pull request or log. Do not set those values until the owner explicitly selects and authorises a hosting provider and preview scope.

When separately authorised, the audit is read-only and checks the following boundary:

- A visitor without credentials receives HTTP 401/403 on **each** of the six app assets, not just the home page. SSO redirects are treated as *unverified*, not as automatic proof of access control.
- The authenticated build matches the independently reviewed SHA-256 values of all six candidate files. The original builder manifest remains **outside** the served site.
- MediaPipe runtime/model/WASM paths, manifest, environment and research-ledger paths do not return content. Unexpected POST/upload endpoints fail.
- Responses have a restrictive HTTP Content Security Policy including `frame-ancestors 'none'`, no cross-origin permission, secure permissions/caching/referrer headers and an HSTS policy; TLS certificate validation and an explicitly approved public DNS hostname are mandatory.

The tool deliberately reports `deploymentApproved: false` and `physicalIphoneVerified: false` **even when the technical preflight passes**. It cannot prove host-provider access logs, identity-service configuration, consent/privacy compliance, revocation after shutdown, cellular/iPhone behaviour or consumer demand. These require separate owner review and physical evidence. An approval to continue engineering **does not** authorise calling the live network audit, provisioning an account, deploying any files or distributing MediaPipe binaries.

### Gate B: Hand-ML preview

**Not yet authorised or prepared for distribution.** Requires resolved exact runtime/model notices, approved vendor bundle, integrity checks, operator permission for external hosting and the full release security review. Only then test actual fingertip tracking on physical iPhone Safari using [the bench protocol](SAFARI_DEVICE_TEST.md), recording false completions, latency, inferred FPS, reload/start failures, camera revocation, battery and thermal observations.

## Explicit $0 owner-only private-preview option (proposed)

The preferred **no-additional-cost** path is now [ZERO_COST_IPHONE_PREVIEW.md](ZERO_COST_IPHONE_PREVIEW.md). Its code creates only an **offline, seven-file, model-free Netlify ZIP** with verified app bytes and security headers. It does not open an account, call provider APIs, deploy a URL or request a payment method. The original SHA-256 receipt remains outside the served ZIP.

Provider documentation indicates a **credit-based Netlify Free plan with a hard usage cap** and **Private** owner-only project visibility, but the particular account, public/private setting, hosted headers, billing behaviour and physical iPhone compatibility are **not verified**. Free-plan hard limits do not make a Public site acceptable. **Stop rather than pay, upload to a public project, or create a billed Codespace.** A live site requires an independently approved provider account, explicit privacy/access verification and owner-only manual deployment.

## Required owner decision before any external action

Approval must identify **provider/account, whether access is public or authenticated, exactly which build and assets may be distributed, acceptable cost, and when access should be revoked**. The assistant must not interpret general permission to continue coding as authorisation to deploy or pay.

## Current proof and limitations

- Automated Chromium and Linux WebKit on fixed test fixtures: **passed in the verified GitHub engineering branch**.
- Exact runtime/model pinned SHA-256: present in source; staging verifies them.
- Exact 1.2.3 release-matched native notices and corresponding source: **unresolved**.
- iPhone-only hosting path: **requires owner-approved provider; no deployment**.
- Physical iPhone recognition and demand: **no recorded test evidence**.

[Integration and release gates](INTEGRATION_AND_RELEASE_GATES.md) · [Runtime rights evidence](HAND_ML_ASSET_GATE.md)

## Hosted-preview access-control bypass probes (engineering gate)

A protected `/index.html` is **not** proof that `/` is protected. Reverse proxies, static hosting rewrites, CDNs and per-path access rules can differ. The owner-gated `tools/audit_hosted_preview.py` now requires an authenticated `/` to match the exact reviewed index and rejects unauthenticated successful or redirected requests for the root, all six named assets, HEAD requests, bounded query variants and selected percent-encoded/path-normalised aliases. The checks are offline simulated in CI and are **not** currently run against a real host.

This is a deliberately bounded preflight: a passing test would not certify all possible CDN edge nodes, Unicode/path decoding, arbitrary query strings, cache rules or access revocation. A future host must undergo a separate owner-approved live assessment of the provider's authenticating boundary and account/billing terms. Do not publish the no-ML ZIP to an unauthenticated site just to test these probes.

## Exact CSP and camera-permission response gate

The hosted-preview auditor must reject a response that merely *mentions* `connect-src 'self'` while also allowing external network targets or permissive inline scripts. Its offline preflight compares every CSP directive's complete source list against the exact reviewed baseline server policy; extra sources, duplicate directives, wildcard form targets, and weaker camera Permissions-Policy values fail. It also refuses contradictory `Cache-Control: public, no-store`. These are security-policy checks, **not a guarantee** that camera frames never leave an owner-approved host if the upstream site, browser or hosting provider itself is compromised. Physical iPhone testing and a live host review remain blocked until separately authorised.


## November 2026 operator-only model-free candidate

An authenticated Netlify Free project has been created and tested: 64/64 first-canary and 56/56 second-canary anonymous requests returned 401, but an unauthenticated CDN deployment screenshot revealed the first private harmless page; the second neutral root screenshot was public but contained no nested fake marker. The [operator-only acceptance plan](OPERATOR_IPHONE_PREVIEW_ACCEPTANCE.md) offers an exact-source six-file baseline nested under a neutral root, with **no** MediaPipe distribution, participant data or secrets. This does not establish complete screenshot confidentiality or constitute approval to upload the actual ANIMATE files; a separate owner decision and live header/asset audit are required before physical Safari camera use.
