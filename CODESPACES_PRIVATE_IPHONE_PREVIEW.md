# ANIMATE — owner-only GitHub Codespaces iPhone preview (zero-additional-spend candidate)

**22 November 2026. Draft-only engineering preparation. NOT PROVISIONED.**
No live Codespace has been started or billed, no source merged, no hosting deployment performed, no Netlify project modified, and no physical iPhone camera test completed.

## Why this alternative exists

Netlify's **Free Private / all-deploy SSO** blocked unauthenticated website and asset requests in 100/100 most recent probes, but in authenticated Safari Netlify appended a **198-byte script** to **both** reviewed HTML files. Both failed SHA-256, correctly leaving the camera security gate at **FAIL** (5/7 files despite 14/14 GET/HEAD header checks and 4/4 absent paths). Its separate deployment screenshots remain public. Do not bypass HTML integrity by stripping the injected script, changing expected hashes or relaxing CSP.

The GitHub Codespaces approach directly serves the previously Git-verified **model-free** 10-file package using a minimal Python origin; no Netlify edge post-processing, no data collection, no model files, no paid hosting, and no public website publishing. The *Github private port forwarding gateway* authenticates the owner and exposes an HTTPS \`*.app.github.dev\` URL while running. This is a proposed different trust boundary; it is not proven until a real Codespace and external anonymous/private checks pass.

Official GitHub primary sources (verified Nov 2026):
- Private forwarded ports are private **by default**, accessible only to the Codespace creator authenticated to GitHub (three-hour authentication cookies): https://docs.github.com/en/codespaces/reference/security-in-github-codespaces
- HTTPS forwarded URL / Codespaces UI port privacy: https://docs.github.com/en/codespaces/developing-in-a-codespace/forwarding-ports-in-your-codespace
- Every personal account receives monthly included compute and storage; usage is restricted once exhausted **unless** the owner has set up a payment method and spending: https://docs.github.com/en/codespaces/troubleshooting/troubleshooting-included-usage
- Create a Codespace for a specific repository/branch in browser: https://docs.github.com/en/codespaces/developing-in-a-codespace/creating-a-codespace-for-a-repository

## Exact draft preview and defence in depth

The only review-approved code is on branch:
\`engineering/animate-codespaces-private-preview-20261122\`
within \`SCSoftwareVentures/Animate\` (public repository; existing application source is already public).

- \`.devcontainer/devcontainer.json\` uses an official pre-built Python 3.12 image with no custom install hooks, no automatic preview startup or deployment. Only port 8765 is labelled and pre-forwarded; GitHub's default **Private** port visibility must be verified in the Ports tab.
- \`python tools/run_codespaces_private_preview.py\` runs **only** with actual \`CODESPACES=true\`, the correct Codespace-name and forwarding-domain variables, exact \`GITHUB_REPOSITORY\` and *this* reviewed draft branch. It will refuse other environments/branches.
- It stages the **source-proven model-free** 10-file camera-gate ZIP into temporary files. The build checks committed source bytes; the generated ZIP is hash-checked before extraction. The app includes only neutral root, six model-free files under \`/operator-preview/\`, two verifier files and a policy \`_headers\` file.
- A read-only exact-route HTTP server sends the reviewed CSP, Permissions Policy, HSTS, no-store and other headers on both GET and HEAD. It serves **only nine reviewed static files**, never \`_headers\`, receipts, source files, model binaries, environment or other repository contents, directory listings, path traversal and encoded aliases. The root is neutral/inert. No API, cookies, token reader, session storage, camera recorder, analytics or external submission route exists.
- The server listens on fixed port 8765 and prints warnings. It **does not itself authenticate users**: GitHub PRIVATE forwarded-port authentication is a required separate enforcement boundary. If an operator makes the forwarded port Public or Organization, **STOP immediately**; do not use the camera.
- The existing browser verifier must report **PASS / 7 of 7 SHA-256 / 14 of 14 GET+HEAD headers / 4 of 4 forbidden paths / no failures or HTML diagnostics** before any physical iPhone camera permission.
- Automated Python HTTP tests and Linux WebKit exercises are only CI evidence; a real Codespace authenticated/unauthenticated HTTP check and iPhone camera session are still needed. GitHub's proxy could also change headers/content, so live verification stays mandatory.

## Owner iPhone-only workflow (single setup, no ZIPs)

**Cost and permission gate first.** The owner must inspect GitHub's [Codespaces usage](https://github.com/settings/billing) or [Codespaces](https://github.com/codespaces) on iPhone for remaining **included** compute and storage. **Do not add a payment method, accept paid usage, upgrade, choose a larger machine or continue after the free quota is exhausted.** Codespaces can consume included compute while running and storage while it exists, even when stopped. The assistant has not independently verified the owner's remaining allowance. Creation/start is an external resource action requiring separate owner authorisation.

After approval to create:
1. In iPhone Safari, open [ANIMATE's reviewed draft branch](https://github.com/SCSoftwareVentures/Animate/tree/engineering/animate-codespaces-private-preview-20261122). Choose **Code → Codespaces → Create codespace on this branch** (2-core/default only). If the mobile view is difficult, switch Safari to **Request Desktop Website**; no separate computer is required.
2. In browser-based Codespaces terminal, run exactly: \`python tools/run_codespaces_private_preview.py\`. The process must print \`PRIVATE PORT REQUIRED\` and the source commit and remain running; it does **not** start before the owner invokes it.
3. In Codespaces **Ports** tab verify **port 8765 / Port Visibility: Private**. Do not select Public or Organization. Open the forwarded \`https://<codespace>-8765.app.github.dev\` link while signed in to GitHub. The exact link is generated by GitHub; do not guess a name.
4. In that same authenticated Safari session open the forwarded origin path \`/operator-preview/verify.html\`. Capture only a nonpersonal results screenshot. The result must show \`PASS\`, 7/7 SHA-256, 14/14 headers, 4/4 absent paths, \`htmlDiagnostics: []\`. **FAIL means camera OFF.**
5. In a separate **signed-out Safari Private Browsing** session test the forwarded URL root, \`/operator-preview/index.html\` and \`/operator-preview/app.js\`. They must not disclose application bytes. Authentication prompt, 401 or 403 is acceptable. A success page/content is **FAIL**; close port immediately. The operator should not share private authentication cookies or GitHub tokens.
6. Only after the assistant reviews the real verified response and private-port controls may the owner open \`/operator-preview/index.html?debug=1\`, request camera permission, and perform the already-documented owner-only camera lifecycle/colour/foreground/safe negative-control tests. **Do not infer hand-ML capability:** MediaPipe model/WASM distribution remains blocked pending legal review.
7. After the short test, stop the server with Control-C in browser terminal (or stop the Codespace from https://github.com/codespaces); remove the forwarded port and delete the Codespace only when explicitly authorised. There are no customer/test records to upload. Do not leave the Codespace running unnecessarily.

## Hard stop conditions

- The GitHub owner lacks remaining quota, or a payment/upgrade is required.
- Codespace belongs to wrong repository/branch, is unable to start without new spending, or port is not Private.
- Failed external unauthenticated check, unexpected proxy-injected HTML, incorrect hashes/headers, missing WebCrypto, unexpected redirects/HTML, or model/WASM binaries.
- User intends to involve other participants, deploy or publish commercial product, distribute ML assets, or merge draft without new authorization.

**Zero additional spending is a constraint, not a claim that a live Codespace is free for this specific account.** Netlify can remain Private and unchanged; avoid more ZIP uploads to Netlify. Commercial-demand and acquisition validation remain separate prerequisites for sale.
