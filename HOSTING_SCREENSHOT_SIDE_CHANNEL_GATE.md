# ANIMATE — hosting screenshot side-channel: verified finding and constrained alternatives

**21 November 2026. Release status: BLOCKED for confidential ANIMATE code or protected content.**
No project upgrade, payment, model redistribution, customer outreach or ANIMATE deployment is approved or made by this protocol.

## Primary evidence: Netlify Private is not complete artifact privacy

On the owner-approved, isolated Netlify Free test project \`animate-security-test\`, deploy \`6b015f338ed0027d28aff839\` held the harmless non-app host-auth canary. Netlify connected project API reported \`requiresSSOTeamLogin=true\` for **all deploys**, a Ready production deploy, six published assets and one \`_headers\` rule.

An external **unauthenticated** HTTP client checked the primary project domain and immutable deploy domain: 64/64 GET/HEAD requests on root, named app paths, selected aliases/query variants and model/environment probes returned HTTP **401**. This proves only the tested asset URL cases; it is not exhaustive authentication bypass coverage.

Separately the Netlify deploy metadata contained a URL shaped \`https://d33wubrfki0l68.cloudfront.net/<deploy-id>/screenshot_<timestamp>.webp\`. An unauthenticated GET to that URL returned **200 image/webp** with \`Cache-Control: public,max-age=86400,must-revalidate\`. The picture **visibly contained the harmless canary page and marker**, showing the provider's capture service could read the private page and its resulting image was not protected by the site's team-login gate. Only fake test text was exposed. Do not share or host private content merely because the dashboard says Private.

This is a **verified path-specific leak**; it does not establish whether the screenshot is indexed/discoverable, whether arbitrary outsiders can enumerate screenshot names, or that any customer data was leaked.

## Screenshot disable / substitution research

Netlify's own support response (2021) described automatic headless-browser screenshots after deployment and said disabling the generation was not supported **at that time**. No current documented Free-plan switch to prevent or restrict *deploy screenshot metadata* has been independently verified. Netlify does document **custom project cover images** for its dashboard, but these must not be confused with or assumed to revoke immutable deploy-specific screenshot URLs. Netlify's March 2026 agent-run screenshot notes say a *protected agent-run preview* should show the sign-in page; our actual **Netlify Drop deployment** screenshot showed the protected content. Do not transfer that agent-run guarantee to manually uploaded deployments.

References:
- https://answers.netlify.com/t/does-each-deploy-preview-stay-available-forever/12601/32
- https://docs.netlify.com/manage/projects/customize-project-name-and-cover-image/
- https://www.netlify.com/changelog/2026-03-03-agent-runs-deploy-preview-screenshot/
- https://docs.netlify.com/manage/security/secure-access-to-sites/project-visibility/

## Engineering experiment: isolate the root page

\`tools/build_screenshot_isolation_canary.py\` creates an OFFLINE **eight-file harmless ZIP** and separate local-only SHA-256 receipt. It includes:
- a deliberately bland, uninstrumented \`/index.html\` page containing **no marker, app, script or secrets**;
- exactly six fake **no-camera, no-ML** files nested under \`/private-canary/\`, including \`/private-canary/index.html\` with a random synthetic marker;
- one \`_headers\` file applying the existing restrictive reviewed Netlify policy to all paths.

**This is NOT screenshot-protection technology.** It only tests whether auto-generated screenshot captures of the *root page* can avoid exposing a **different**, authenticated, harmless subpage. Headless capture could later target a subpath, and the provider can still access stored file bytes. Never place secrets or unredistributable model binaries in this test.

### Owner-only live verification (separate upload action required)

1. Confirm the existing Netlify project is still **Private / SSO required for all deploys**. Do not click Make public or Upgrade.
2. With explicit permission, manually upload only \`hosting-thumbnail-isolation-canary.zip\` to the existing \`animate-security-test\` project. Do not upload its local receipt or the ANIMATE app.
3. Read the new deployed SHA-256 hashes and marker from the independent receipt; check \`/\` and \`/private-canary/\` on the authenticated owner session. The root must have NO marker; the nested path must show it. Audit real served CSP/permissions/no-store/HSTS without weakening browser policy.
4. From a completely unauthenticated outside session test GET/HEAD at the main and immutable URLs, including \`/private-canary/\`, nested JS/CSS and aliases. Expect explicit 401/403, no successful redirect or app bytes.
5. Retrieve the **new** deployment screenshot URL without credentials and inspect the image. If the image contains the *private synthetic marker*, this isolation experiment fails. If it contains only the neutral page, it proves **only that this particular deploy screenshot captured the root**; the screenshot URL itself still exists and is public.
6. Keep the ANIMATE release gate **blocked** until privacy review determines that all screenshot-capturable content, including possible private paths and provider-internal metadata, is nonconfidential or until the provider independently confirms full screenshot suppression/access protection.

The independently staged ZIP must **never include** ANIMATE source or participant data. CI unit tests check root-byte identity, unique random fake marker isolation, exact members and digests, zero app/ML/camera and immutability of output directories. CI does not upload a file or confirm provider behavior.

## Alternative: Cloudflare Pages Free with Cloudflare Access

Cloudflare documentation describes free Pages static deployment (dashboard Direct Upload accepts a ZIP) and Cloudflare Zero Trust Free. **Cloudflare Access preview protection alone does not secure the production \`<project>.pages.dev\` URL.** To protect both, follow their documented two-application setup, explicitly applying Access rules to the production hostname AND wildcard preview hostname. Audit branch aliases and immutable preview URLs too.

- https://developers.cloudflare.com/pages/configuration/preview-deployments/
- https://developers.cloudflare.com/pages/platform/known-issues/#enable-access-on-your-pagesdev-domain
- https://developers.cloudflare.com/pages/get-started/direct-upload/
- https://developers.cloudflare.com/cloudflare-one/setup/

**Major $0/onboarding qualification:** Cloudflare's own Zero Trust Free setup instructions say users must enter payment details even when the selected plan is Free, though it says the Free plan will not charge. No Cloudflare account, payment method, live Pages host, authenticated HTTP audit or no-screenshot evidence has been verified for ANIMATE. Do not infer that Cloudflare universally disables project thumbnails; perform an independent canary probe before trusting it. Do NOT onboard a paid or metered feature or card without explicit owner consent.

## Decision

- **Netlify existing production screenshot confidentiality: FAIL (confirmed).** Website HTTP-auth checks: limited PASS; do not combine these into a full security PASS.
- **Netlify root-isolation workaround: BUILT IN DRAFT; offline tests only.** A neutral screenshot could reduce visual information disclosure but cannot prove deployment thumbnails are disabled or restricted.
- **Cloudflare Pages + Access: DOCUMENTED CANDIDATE ONLY.** Needs an approved account, Free-plan acceptance, two strict policy configurations and live screenshot/asset testing.
- **Physical iPhone Safari and commercial outreach: BLOCKED** until operator approval and broader hosted privacy verification. Full MediaPipe rights gate remains independently blocked.

Do not declare the root isolation a verified secure-host result after seeing a single sanitized screenshot. Record negative evidence and reject any assumption that a private site means its derivative images are private.


## Bounded transition from canaries to one actual operator preview (not yet deployed)

See [OPERATOR_IPHONE_PREVIEW_ACCEPTANCE.md](OPERATOR_IPHONE_PREVIEW_ACCEPTANCE.md). The next executable candidate reuses the **tested script-free neutral root** and nests the existing, source-verified six-file model-free ANIMATE baseline under \`/operator-preview/\`. It contains no unapproved MediaPipe binaries, secrets or participant records. The whole project remains Netlify Free/Private team SSO; even so, screenshots remain publicly retrievable and this is NOT a hosting screenshot confidentiality fix. No more repeated canary iterations are justified without new evidence. Separately approved owner-only camera testing may be considered only after reviewing the residual risk and passing the fresh live hosted audit; **never silently treat a passed neutral screenshot as security clearance for private app content**.
