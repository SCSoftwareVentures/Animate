# ANIMATE — camera security gate, exact authenticated Safari check

**As of 21 November 2026: NOT CLEARED.** This branch prepares an auditable in-browser proof, not a new deployment, an iOS camera result or independent privacy certification. No purchases, merges, account changes, new provider trials, or recruitment.

## What is already independently observed

- Existing Netlify Free project \`animate-security-test\` is configured with team login required for **all deployments**. Anonymous main/deploy-domain probes after the model-free application upload returned **100/100 HTTP 401**, but that does not reveal the authenticated file bytes or security response headers.
- Provider-generated deployment screenshot remains publicly accessible from a separate CDN, even under site SSO. The current screenshot showed only the inert root. This is a **residual host metadata confidentiality exposure**, not a fixed vulnerability.
- The owner showed real iPhone Safari loading the app and completing a **touch-only challenge 3/3 in 4.9 displayed seconds**; this does not prove camera compatibility.

## Exactly what the browser verifier does

The new \`tools/build_iphone_camera_gate.py\` consumes the **already source-verified** model-free operator preview, preserves its inert \`/index.html\` and six unmodified \`/operator-preview/\` app assets, and adds:

- \`/operator-preview/verify.html\`: an inert page with a **SHA-384 Subresource Integrity** pin on its same-origin verifier script;
- \`/operator-preview/verify.js\`: source-verified static digest expectations embedded at packaging time. It runs only at \`/operator-preview/verify.html\`, requests exactly the reviewed root + six app assets with signed-in Safari credentials using same-origin no-cache GET and HEAD, computes browser WebCrypto SHA-256 and compares exact bytes against the build, and checks the actual response security headers. It also confirms four forbidden model/receipt paths respond 404 or 410.

It enforces the reviewed CSP, Permissions-Policy, X-Frame-Options, Cross-Origin-Resource-Policy, X-Content-Type-Options, Referrer-Policy, Cache-Control no-store and HSTS minimum. **Any missing or altered policy, asset hash, 401/login response, service worker interception, or unauthorised file yields FAIL.** The checker does not call camera APIs, read private Safari records or cookies, collect device identifiers, submit reports, use external network requests, or write any browser storage.

The reviewed \`/_headers\` rule is unchanged, and both verifier assets are packaged into a new **ten-file** ZIP. Receipt with exact hashes and Git provenance is never deployed. The visible result includes only aggregate status, file/header counts, and bounded failure reasons; never paste cookies, tokens, private exported records, or full URL session parameters.

## Validation chain

1. Commit exact source and audit templates to the stacked **draft** branch. Run all existing security and WebKit/Chromium camera suites; use the targeted local Python tamper tests.
2. Test the verifier **in real local WebKit** under a fixture that sends the same approved HTTP headers. A clean package must return PASS. Serving an altered \`app.js\` or omitting \`Permissions-Policy\` must return FAIL. These tests are **not** an authenticated Netlify or real-iPhone observation.
3. After success and explicit owner approval for *this precise replacement upload*, replace the current model-free preview ZIP in the **existing** protected Netlify project via iPhone Safari. Do not create another project or make it public. Audit the fresh deploy id, Free/Private SSO configuration and anonymous 401s **again**. Check the screenshot still contains only the inert root (but remains publicly accessible).
4. In owner signed-in iPhone Safari, open \`https://animate-security-test.netlify.app/operator-preview/verify.html\` **before enabling any camera**. The checker uses the owner's authenticated same-origin session, and MUST show **PASS**, \`checkedFiles: 7/7\`, \`checkedGetAndHeadHeaders: 14/14\`, \`confirmedAbsentPaths: 4/4\`, \`failures: []\`. A screenshot or copied **nonpersonal** result enables an independently recorded operator-observed pass. If login/redirect/missing header/missing browser API/hash mismatch occurs, keep the camera OFF and fix the actual cause in a new reviewed commit; never weaken the checks merely to force a pass.
5. A successful on-device pass **clears only the technical pre-camera byte/header gate** for this exact deployed model-free preview, subject to continued Private SSO and original screenshot-risk acceptance. It does not authorize public participant research, validate model/WASM rights, confirm full provider confidentiality, or certify iPhone camera performance. Camera permission and performance must be physically tested afterwards under the separate protocol.

## Constraints and proof limitations

- The browser's response report is **owner-observed on-device evidence**, not independent server-side attestation. The checker is pinned to the packaged source via SRI and the GitHub CI review artifact; a malicious hosting provider could theoretically replace both the page and code. This cannot be fully eliminated on Netlify without additional independent tooling.
- The public deploy screenshot URL **continues to exist**, independent of successful byte/header checks. This operator-only QA may proceed only because the package contains already-public, nonsecret source and a neutral root; it is not a licence to upload confidential user/business records.
- Do not merge, publish on public hosting, use ML models, ask for login cookies, enable paid services, upload evidence containing personal identifiers or contact other participants. The current Netlify account remains the Free plan and the same existing site.


## Physical iPhone authenticated verifier result — 21 Nov 2026, 9:21 PM Melbourne

Owner provided a screenshot of the live \`/operator-preview/verify.html\` result. The screenshot shows **\`result: FAIL\`**, **\`checkedFiles: 5\` of 7**, **14/14 GET/HEAD header requests checked with no reported header failures**, **4/4 forbidden paths absent**, and precisely two file SHA-256 mismatches: the neutral \`/index.html\` and app \`/operator-preview/index.html\`. The five non-HTML model-free files passed. This is **real on-device evidence of an HTML response transformation or mismatch**, not evidence of complete integrity or approval for camera.

Netlify officially documents server/edge HTML injection mechanisms, including snippet injection at serve time and its 2026 pre-launch/badge script. Such an injection is a plausible explanation, **not a proven root cause** from this screenshot. A project with team login/SSO may not display the badge, which further prevents automatically attributing this mismatch to the overlay. Other transformations, origin byte errors or deployment effects remain possible. Sources:
- https://docs.netlify.com/build/post-processing/snippet-injection/
- https://docs.netlify.com/manage/projects/powered-by-netlify-badge/
- https://docs.netlify.com/manage/projects/pre-launch-toolbar/

### Scoped diagnostic engineering

The downstream draft \`engineering/animate-safari-html-byte-diagnostics-20261121\` retains every original hash/header assertion. The embedded verifier now includes the **two Git-verified HTML byte references** in its SRI-pinned JS so it can report, **only upon an HTML hash mismatch**: expected and served byte lengths and hashes, first unequal byte offset, matching trailing byte count, a small bounded printable changed-region sample, and a boolean signature check for documented Netlify HUD injection markers. Reports remain local to the signed-in Safari page. No camera, external request, storage or telemetry is added.

CI must verify the original clean site still passes and a synthetic injected HTML document **fails** with helpful bounded diagnostics. If the hosted result shows an exact, harmless provider script insertion, evaluate whether the hosting provider can stop transformation without cost or weakening security. **Do not strip/ignore arbitrary injected HTML or mark these files PASS.** If Netlify's SSO-only Free plan unavoidably rewrites HTML, exact-byte authentication cannot be cleared on that host under the current gate; escalate the verified blocker instead of pretending the test passed.

**Current gate: FAIL / camera OFF.** No model/WASM distribution, deployment modification, merge, spending or participant recruitment authorised by this forensic investigation.
