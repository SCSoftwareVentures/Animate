# ANIMATE — private $0 iPhone preview hosting research and release gate

**21 November 2026. STATUS: RESEARCHED / NOT PROVISIONED / NOT DEPLOYED.** No account, billing setting, participant contact, external camera, web host or ML distribution is authorised by this document.

## Decision

**Preferred conditional option: Netlify credit-based Free with Private project visibility applied to BOTH production and previews.** Netlify's own 2026 documentation says this is available on Free, enforced with Netlify login, and limited to the team owner on Free. It describes 300 monthly credits, a hard stop without automatic recharge and permission to host commercial products on Free. These are **documented capabilities, not verification of the owner's account or live project**.

**Alternative: Cloudflare Pages Free plus Cloudflare Access.** The one-click Pages policy protects preview deployments but **not** the default production \`*.pages.dev\` domain. Follow Cloudflare's known-issues two-policy instructions to guard both the production hostname and wildcard preview hostnames. This adds configuration risk; no access policy has been established.

**Excluded:** Vercel Hobby (its free plan forbids commercial use); unauthenticated GitHub Pages; publicly readable secret/obscured URLs; front-end password screens. GitHub Codespaces has GitHub-authenticated private forwarded ports but is a metered compute/storage workflow, not the approved zero-charge iPhone-only route.

## Important untested blocker: provider HTML injection

Netlify says that its 2026 Free projects may receive CDN-edge-injected branding and that private projects can display a related pre-launch toolbar. A restrictive CSP may block rendering, but may **not** prevent the CDN from changing the actual HTML response. ANIMATE's hosted-preview auditor requires exact checked HTML, JS and CSS bytes, restrictive headers and no unauthorised access. **Do not weaken those checks or add \`unsafe-inline\` simply to get a hosted preview working.** If the provider cannot serve unmodified inspected bytes, it fails the gate. This must be tested, not guessed.

## Zero-application hosting canary — now prepared

\`tools/build_host_canary.py --output-dir <new-directory-outside-repo>\` creates only:
- \`hosting-auth-canary-only.zip\`: six harmless text assets at the same URL paths as the model-free app, plus reviewed \`_headers\`, with an independent random visible canary marker.
- \`LOCAL_ONLY_CANARY_RECEIPT.json\`: local hashes, marker, and explicit assertions that the site was **not deployed**, access was **not verified**, and no spend was approved. Never upload the receipt.

This canary is NOT ANIMATE and contains no camera, application logic, MediaPipe, recorded frames, research records or credentials. It is not protected by its own code. Its independent ZIP-and-hash checks run in GitHub CI without uploading, deploying, recruiting or spending.

## Future operator-only sequence; separate explicit approval required

1. Confirm Netlify's actual **credit-based Free** plan, no paid add-ons, no payment obligations/auto-upgrade. Do not choose a paid plan or buy credits. If the provider's iPhone Safari interface cannot accept the ZIP, stop rather than assume desktop tools are available.
2. Configure **Private** project visibility for **Production and previews**, not merely previews. Confirm the provider enforces login for every served path. Do not upload ANIMATE to discover whether this is true. If project visibility cannot be established before hosting any content, stop.
3. With separate authorisation for a *harmless* deployment, use the canary ZIP first. Test signed-out **Safari Private Browsing**: \`/\`, \`/index.html\`, \`/app.js\`, \`/core.js\`, \`/foreground.js\`, \`/hand_ml.js\`, \`/styles.css\` and a query variant must not expose file bytes. Signed-in Safari should load the canary. A provider login redirect alone is not independent proof of complete URL access control.
4. Independently audit status codes for GET and HEAD, root aliases, security headers, app-file byte hashes, auth session scope, provider instrumentation, server/CDN logs, account privacy and revocation. Our \`tools/audit_hosted_preview.py\` deliberately rejects unauthenticated redirects as inconclusive and requires the exact model-free ANIMATE candidate for its eventual live final gate; do not claim the canary bypasses this.
5. Only after separately approving the ANIMATE baseline upload and passing its protection audit may the owner test physical iPhone Safari \`?debug=1\`. Collect negative controls, normal/dim light, errors, real frame throughput, permission cancellation, Stop, app-switch, recovery, thermal effects and iOS camera indicator. Follow \`IPHONE_DEVICE_METRICS_PROTOCOL.md\`; preserve ALL failed trials.
6. Stop camera, revoke project/session access and remove preview after the authorised test. The provider may retain logs even without video upload. No child participants, buyer outreach, or external participant research is authorised by a private hosting decision.

**ML distribution remains blocked** until exact MediaPipe runtime/model licence and notices pass their independent gate. A model-free iPhone benchmark cannot establish hand-ML performance or consumer demand.

## Provider references verified 21 November 2026
- Netlify Free private access: https://docs.netlify.com/manage/security/secure-access-to-sites/project-visibility/
- Free hard cap and 300 credits: https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/credit-based-pricing-plans/
- Commercial projects allowed on Free: https://www.netlify.com/platform/
- 2026 private pre-launch script: https://docs.netlify.com/manage/projects/powered-by-netlify-badge/
- Netlify Drop may require desktop browser; iPhone usability unverified: https://docs.netlify.com/start/quickstarts/netlify-drop-quickstart/
- Cloudflare preview policy only: https://developers.cloudflare.com/pages/configuration/preview-deployments/
- Cloudflare production + preview dual configuration: https://developers.cloudflare.com/pages/platform/known-issues/
- Vercel Hobby non-commercial: https://vercel.com/docs/plans/hobby/
- GitHub private Codespaces ports: https://docs.github.com/en/codespaces/reference/security-in-github-codespaces
