# ANIMATE — one-shot owner-only iPhone preview acceptance plan

**21 November 2026. Engineering candidate only. Not deployed. No physical iPhone results.**

This document supersedes repeat canary experiments: the next test is **one actual model-free owner-only preview**, scoped to the already configured Netlify Free/Private \`animate-security-test\` project **only after a separate owner approval of the upload and residual screenshot risk**.

## Fixed decision boundaries

- Free account: Returnward Acquisitions, owner membership only; no spending, upgrades, new billing, custom domain, add-ons or preview-publication automation.
- Existing Netlify \`animate-security-test\` project: site-level SSO required across **all** deploys. Real external probes previously returned 401 for 64/64 requests on the first harmless canary and 56/56 on the second, across production and immutable deploy URLs. These are bounded results, not complete penetration tests.
- **Open confidentiality risk:** Netlify produced unauthenticated, publicly retrievable deploy screenshots even when the site required team SSO. The root-only neutral screenshot on the second harmless deploy did not show the nested fake marker; this verifies isolation for **that** root capture only. The provider may still capture private paths, metadata or contents. No documented Free switch disables the screenshot service. **Do not upload secrets, personal data, buyer records, unlicensed models, credentials, or proprietary material not already intentionally public.**
- The ANIMATE source is already public on GitHub; this package contains only source-verified public files transformed to remove hand-ML selection and add the limitation disclosure. Its URLs are intended for one operator, not a secret distribution channel.
- The independent model/WASM redistribution notice chain remains blocked. Package must contain zero hand-landmark model binaries or WASM. This preview measures colour, foreground and touch—not AI hand recognition.
- No participants, minors, outreach, buyer trials or payment experiments. This is **operator-only technical QA**, not a launch or commercial demand measurement.

## Candidate packaging

\`python tools/build_operator_preview.py --output-dir <new-path-outside-checkout>\` produces:
- \`animate-operator-only-preview.zip\` containing *exactly* eight files:
  - \`/index.html\` = hash-checked neutral, script-free root used in the tested screenshot-isolation canary
  - six exact committed, model-free app assets under \`/operator-preview/\`
  - top-level \`/_headers\` carrying reviewed CSP, same-origin camera permissions, no-store, no-referrer, frame protections and HSTS
- \`LOCAL_ONLY_OPERATOR_PREVIEW_RECEIPT.json\` kept **outside** the deployed ZIP; includes source commit, archived file and per-member SHA-256 values and explicit non-approval markers

Archive builder refuses extra members, duplicate ZIP names, oversized contents, symlinks, unverified source bytes, model/WASM/vendor material and a non-neutral root. It creates no remote resources. The repository's CI additionally uses a real Linux WebKit mobile viewport over a temporary local HTTP server to inspect both the neutral root and functioning nested app, consent, touch task and blocked third-party requests. It is **not** physical iPhone Safari.

CI \`pull_request\` attaches the no-secret ZIP as a *GitHub Actions artifact*, retained three days; the public-repository artifact must be treated as potentially accessible to other GitHub users and cannot hold confidential files. On an iPhone, download the successful run's artifact, extract its outer Actions ZIP, then upload only the inner \`animate-operator-only-preview.zip\` if separately approved. Do **not** upload the external receipt.

## Pre-upload owner go/no-go — must all be true

1. Owner separately authorises uploading only the model-free candidate, accepting the specifically disclosed **public deployment-screenshot residual risk**. General instruction to continue engineering is **not upload authorisation**.
2. Latest exact-head CI is SUCCESS, the archive hash is checked and the model/WASM rights gate remains fail-closed.
3. Netlify is still Free, no pending charged services, private and SSO-required for **all** deploy contexts; the only operator in the team is the owner. STOP if the UI says Public or tries to upgrade.
4. Since the deployment will replace the harmless test version, record the existing deploy id for rollback and do not upload research exports or receipts.
5. Review Netlify request logging/instrumentation and the static camera disclosure: browser frames must remain local; do not record faces, documents or participant data.

## After separately authorised upload (read-only probes first)

1. Confirm new deploy's ID, published timestamp, origin, immutable version, screenshot URL and Free/Private SSO configuration. Server-generated screenshot must show only the neutral root; screenshot retrieval must be audited anonymously. **If any app UI or non-public details appear in the screenshot, fail and roll back.**
2. Test unauthenticated **GET and HEAD**, main host and immutable deploy URL: \`/\`, \`/index.html\`, \`/operator-preview/\`, \`/operator-preview/index.html\`, all five JS/CSS nested assets, selected alias/query patterns, and vendor/model/environment/receipt paths. Any unexpected 2xx/3xx = FAIL.
3. In owner's logged-in Safari, verify \`https://animate-security-test.netlify.app/operator-preview/index.html?debug=1\` opens; check exact file SHA-256 and effective CSP/Permissions-Policy, HSTS, no-store and no third-party asset/network requests. CDN injections are a fail unless separately reviewed.
4. Only then use iPhone camera permissions. Test denial, front/rear start, user-initiated Stop, interruptions and app switching, retained frame clearance, touch fallback, colour calibration and 12-frame foreground capture. Use real numbers and fail counts as defined in [IPHONE_DEVICE_METRICS_PROTOCOL.md](IPHONE_DEVICE_METRICS_PROTOCOL.md). Collect no video images. A green Linux WebKit test cannot replace this observation.
5. Stop camera, delete local test record, clear Safari website data and revoke/delete the preview or restore harmless canary after the trial. **Ask separately before deletion or rollback**, as those are destructive remote actions.

## Pass/fail interpretation

- **Packaging/CI passed:** only the signed source and intended files are staged correctly.
- **Private-hosted technical preflight passed:** must include live nested-path guest denials, verified authenticated bytes/headers, screenshot inspection and provider/configuration review. This does not certify complete screenshot confidentiality.
- **Actual iPhone trial passed:** only if operator records observed camera permission/lifecycle performance and failures in real Safari.
- **Commercial readiness:** still separately blocked by exact MediaPipe rights and independent demand/buyer qualification; this preview alone proves neither.

No deployment, merge, account change, payment, participant contact or device test is performed by the code or documentation in this sprint.
