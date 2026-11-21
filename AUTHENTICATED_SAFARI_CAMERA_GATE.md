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
