# ANIMATE — 21 Nov 2026 authenticated HTML byte-integrity failure

**Security status: BLOCKED. Do not enable camera, recruit participants, distribute ML or announce a passed release.**

## Live iPhone result and scope

The owner performed the reviewed \`/operator-preview/verify.html\` check on a physical iPhone in an authenticated Netlify Free/Private session. Screenshot showed:
- \`result: FAIL\`
- \`checkedFiles: 5\` of \`expectedFiles: 7\`
- \`checkedGetAndHeadHeaders: 14\` of \`expectedGetAndHeadHeaders: 14\`
- \`confirmedAbsentPaths: 4\` of \`expectedAbsentPaths: 4\`
- **SHA-256 mismatch** on \`index.html\` (the neutral root)
- **SHA-256 mismatch** on \`operator-preview/index.html\` (the model-free application document)

The JS/CSS assets passed exact SHA checks. The browser-reported headers and forbidden paths passed. This is not proof of malicious modification or proof that Netlify is harmless. It is evidence of **HTML-specific source-to-response byte transformation**, whose cause is presently unconfirmed.

## Hypotheses and independent documentation

Netlify officially supports HTML post-processing and snippet injection that occurs when pages are **served**, not in the uploaded ZIP. It also documents edge-injected private pre-launch UI. The documentation says the overlay is **not displayed for projects protected by team SSO**, so attributing the present mismatch to the toolbar alone would be speculation. Other possibilities include an optional snippet, HTML rewriting or server-side transformation. Source URLs:
- https://docs.netlify.com/build/post-processing/overview/
- https://docs.netlify.com/build/post-processing/snippet-injection/
- https://docs.netlify.com/manage/projects/pre-launch-toolbar/
- https://docs.netlify.com/manage/projects/powered-by-netlify-badge/
- https://www.netlify.com/blog/deprecation-of-post-processing-asset-optimization-feature/

Do NOT disable CSP, bypass Netlify SSO, ignore HTML hash differences, or downgrade full-source checks based on a presumed benign injector. Browser rendering and a header pass are insufficient.

## Single-purpose diagnostic engineering

\`tools/build_html_delivery_diagnostic.py\` generates a **12-file**, no-camera, zero-spend, model-free ZIP using the exact already approved 10-file camera-verifier preview with **no modifications** to any original file. It adds only:
- \`operator-preview/inspect.html\` — an inert local status page with an SRI-pinned script;
- \`operator-preview/inspect.js\` — an embedded copy of the two already-public source HTML byte sequences, for same-origin signed-in GET comparison in Safari.

The script computes SHA-256 of expected and received HTML, measures first-difference position and unchanged suffix, counts changes in script/iframe/comment tags, and reports a short redacted sample of the differing bytes. It uses no camera API, visitor tracking, storage, outbound requests, cookies or login tokens. It **never returns camera approval** even when HTML appears identical. The existing \`verify.html\` and \`verify.js\` remain strict, so the original FAIL persists until the actual source is corrected or approved byte identity is independently proven. The ZIP's receipt stays **outside** the deployment archive.

CI covers exact asset preservation, script SRI, ZIP member list/hash/size, no model/WASM/private data, tamper refusal and a Linux WebKit test with deliberately modified local HTML. These are not live Netlify or iOS validation.

## Operator instructions — separate approval before upload

1. After an exact-head successful CI run and explicit owner consent for another **same private project only** ZIP upload, replace current app ZIP by \`animate-html-delivery-diagnostic.zip\` on the existing Netlify project. The replacement adds only two inert diagnostic files; it does not create a new project or use another hosting provider.
2. Verify the project is still Free, Private and SSO-required for all deployments. Recheck fresh production+immutable anonymous URL denial and the derivative screenshot remains neutral. Do not upload the receipt or model.
3. In logged-in iPhone Safari, open \`https://animate-security-test.netlify.app/operator-preview/inspect.html\`. The report is **DIAGNOSTIC_ONLY_CAMERA_NOT_CLEARED**. Copy or screenshot only the small sanitised diagnostic result. It may reveal HTML markup already present in the intentionally public source; never include login/session credentials or any private research record.
4. Investigate actual differing markup. If the cause is an editable Netlify site-level post-processing/snippet setting, propose a **separately reviewed and authorised** non-spending fix and rerun the **original** strict security verifier. Do not whitelist arbitrary HTML differences or remove trusted security headers just to make the tests green.
5. **Only** an original authenticated \`verify.html\` result of PASS with 7/7 exact files, 14/14 headers and 4/4 forbidden absences after review, plus unchanged SSO and screenshot audit, can close the specific pre-camera technical gate. General provider screenshot confidentiality is still not proven.

Keep user iPhone-only, public-source model-free scope, all existing draft branches, and zero additional spend.
