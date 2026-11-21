# ANIMATE — $0 additional-cost iPhone preview option (owner-only)

**Status: offline preview ZIP builder in draft review; nothing deployed. A dashboard marked Private is NOT proof that deployed website asset URLs require authentication. No upload is authorised.** The source checkout, CI runner and ChatGPT session have not opened a Netlify account or site. Do not confuse a technically packaged preview with an authorised, secure hosted experiment.

## Current verified provider conditions (21 November 2026)

An operator may choose **Netlify's credit-based Free plan** if the account explicitly shows the plan, fixed usage caps and **zero permitted extra charges**. Netlify documents hard limits on Free; when a usage limit is reached, hosted projects can **pause**, rather than automatically charge for more usage. Netlify's credit-based Free plan may permit **Private** project visibility in its management UI. This does **not establish** site-level HTTP access control for deployed content. Treat every deploy URL and asset as potentially public until independently denied to a signed-out browser. On new accounts, private-by-default depends on account settings and account creation date; **check each project's actual visibility before uploading**.

Primary provider documentation:
- https://www.netlify.com/pricing/
- https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/how-credits-work/
- https://docs.netlify.com/manage/accounts-and-billing/billing/resume-paused-projects/
- https://docs.netlify.com/manage/security/secure-access-to-sites/project-visibility/
- https://docs.netlify.com/manage/routing/headers/

**Stop if any of the following is required or selected:** paid plan, payment-card requirement the owner does not accept, trial that converts to paid, add-ons, auto recharge, credit purchase, paid team seats, paid domain, upgrade prompt, or a **Public** project. Do not trust a secret URL, HTML/JS password prompt, or robots.txt as access control. A Free plan is not automatically cost-free on legacy plans or if the operator separately opts into a paid product.

## Prepared deliverable (offline; no web requests)

From an approved checkout, this script builds an immutable local ZIP **outside the Git repository**:

```sh
mkdir -p /tmp/animate-preview-build
python tools/build_zero_cost_preview.py --output-dir /tmp/animate-preview-build/candidate
```

It creates exactly:

- `animate-model-free-private-preview.zip`: a *seven-file* static bundle with `index.html`, `app.js`, `core.js`, `foreground.js`, `hand_ml.js`, `styles.css`, and Netlify's `_headers` file
- `LOCAL_ONLY_BUILD_RECEIPT.json`: SHA-256 hashes, exact source commit and explicit statements that no host, costs, device tests or access-control approval exist. **Never upload this receipt as part of the served website**.

The model-free user interface removes the hand-ML selection and prominently discloses the limitation. There is **no MediaPipe runtime, model, WASM file, participant export, ledger, environment file, credential, tracking beacon or external image** in the ZIP. The `_headers` file declares CSP, same-origin camera permissions, frame blocking, no-referrer, no-store and HSTS; the hosted provider must still be verified to apply them in responses.

The builder is deliberately **not** a Netlify client: it makes no web requests and cannot deploy, log into an account, buy credits, create a project or set project visibility. Its generated ZIP is **not protected by itself**—security depends on provider-enforced Private access after explicit operator setup. A public upload would be an unacceptable privacy/security exposure.

## iPhone-only deployment decision — operator action only

1. Review Netlify's **current** Free billing terms and account limits on the iPhone. Confirm the account is on **credit-based Free** (not a paid or legacy account with unknown billing behaviour), with hard monthly limits and no possible automatic recharge. Cancel the process if a payment card, upgrade or cost is requested. The assistant must not create accounts or connect Netlify to GitHub without explicit approval.
2. If you separately authorise a Netlify account, verify that its **site-level access controls**, not merely management-dashboard Private visibility, can require authentication for all published assets at $0. If this requires a paid plan, the hosting path is **BLOCKED**. Never upload this ZIP merely to test whether access happens to be private.
3. Only after separately verified site-level authentication is configured for the complete site, use a *manual site deployment* (if the iPhone Netlify interface actually supports file selection) with the **ZIP only**, or an independently approved deployment integration. Do not turn on production auto-deploy from GitHub just to get a preview. No provider actions are carried out by this repository.
4. After deploying, test the HTTPS URL in a private/incognito browser session while **signed out**; it must not deliver HTML/CSS/JS to an unauthorised visitor. Log in as team owner only through the provider's official login. If this cannot be verified, stop; do not request camera permission or enter data.
5. Inspect whether every reviewed file is served unchanged and every protective HTTP header is enforced. The existing `tools/audit_hosted_preview.py` is a future operator-gated auditor, not proof of Netlify support: login redirects are deliberately marked *unverified*. Provider injections, headers, auth cookies, SSO and traffic logs need separate live review.
6. When all gates are explicitly satisfied, open the authorised URL **directly in iPhone Safari**, test touch-only controls, then the model-free colour/foreground camera. Use [the physical device protocol](IPHONE_DEVICE_METRICS_PROTOCOL.md); do not interpret synthetic/browser-engine results as physical-device results.
7. Shut down and delete the deployment/project at the end of the trial, as permitted, and check the provider's retained usage/request logs. An uploaded/downloaded static file cannot be remotely deleted from devices that already received it.

## Acceptance conditions before we call this a working iPhone preview

| Gate | Current status |
| --- | --- |
| Offline ZIP constructed and checksummed | Implemented in draft; full GitHub CI required on exact head |
| Free-plan hard monthly stop | Documented provider capability, **not independently checked for owner's account** |
| Site-level authentication for all deployed static URLs, not dashboard visibility | **Not configured or verified — deployment blocked** |
| HTTPS/browser security headers in real response | Required but **not tested against Netlify** |
| Camera permission, capture and performance in physical iPhone Safari | **Not measured** |
| Model redistribution legal clearance | **Blocked**; not relevant to model-free preview |
| Customer willingness to pay and acquisition interest | **Not measured** |

## Explicit financial and permission controls

**Total additional spending allowed: $0 AUD.** No use of Codespaces, Railway, Render, paid domains, subscriptions, billing top-ups, purchased credits or paid developer accounts. Do not permit any cloud plan to auto-upgrade or bill overages. If verifiable site-level protection for every asset is not available on the Free plan, report that Netlify is unusable under the $0 requirement. Never substitute project-dashboard privacy, an obscure URL or client-side credentials for site authentication.

This option supersedes the earlier **potentially billable Codespaces** proposal as the preferred route, without cancelling or merging historical PRs. Netlify/its CDN can still observe request metadata even if browser video frames remain local. Separate operator privacy approval is mandatory before using a real camera or recruiting anyone.

This is an engineering candidate—not a promise that Netlify Free currently enables all required mobile features, not a signed service agreement, not a published app and not evidence of demand.


## November 2026 provider research and harmless access-canary preflight

See [HOSTING_RESEARCH_AND_OWNER_RUNBOOK.md](HOSTING_RESEARCH_AND_OWNER_RUNBOOK.md) for updated provider-sourced evidence and an explicit canary-first route. Official Netlify documentation now confirms credit-based Free **Private project visibility is enforced through Netlify login**, but it has not been tested for this owner's account or for production/preview/path aliases. Netlify's edge-injected private pre-launch toolbar may modify hosted HTML, conflicting with ANIMATE's strict source-hash audit; **never weaken the CSP or HTML equality gate to make a provider pass**.

The repository now prepares \`tools/build_host_canary.py\` and its tests to generate a clearly labelled, **non-ANIMATE**, no-camera/static canary ZIP for future separately authorised access-control tests. No canary or ANIMATE app was deployed; do not publish or upload either ZIP without a new owner approval. Netlify's ZIP/folder web upload instructions recommend desktop/Chromium, so actual iPhone Safari-only deployment usability remains unverified. Cloudflare Pages Access is a fallback only if production and preview hostnames are both protected. Vercel Hobby is excluded because commercial projects are not permitted under its free plan.

A provider account and live HTTP/asset/header audit remain required before **any** physical iPhone camera evaluation; this update is NOT host approval.
