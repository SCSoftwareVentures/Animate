# ANIMATE — Optional iPhone-only GitHub Codespaces preview

**State: engineering proposal only; NOT launched, owner-approved, hosted, cost-cleared or physically tested.** This option is intended to remove the need for a separate laptop or server. It still uses a cloud Codespace on the owner's GitHub account, which **may incur compute/storage charges** and requires explicit owner approval. A GitHub account/plan may not offer Codespaces, and Safari camera behaviour behind its forwarding proxy has **not been verified**.

## What this option does

A new optional `.devcontainer/devcontainer.json` provides a Python environment. It neither opens a port nor starts ANIMATE automatically. The local server `tools/serve_codespaces_baseline.py` can **only** run after an operator explicitly acknowledges the private port, opts in through `ANIMATE_OWNER_PREVIEW_APPROVED=YES`, supplies the exact forwarded hostname, and stages the checksum-verified six-file model-free candidate. The server listens on `127.0.0.1:8765` inside Codespaces. GitHub's separate port-forwarding proxy would supply external HTTPS and GitHub user access controls **only when the port is configured PRIVATE**.

**There is no application-level login in this server.** The server cannot independently verify that GitHub's proxy really has a Private visibility setting; its CLI flag is a human acknowledgement, not a security measurement. A Public forwarded port must NEVER be used with this setup. Do not treat an unguessable Codespaces URL as authentication.

The server is deliberately unavailable outside the GitHub Codespaces environment and denies non-matching `Host` headers. It uses the existing strict CSP, restricted Permissions-Policy, no-store and no-referrer headers, and a six-file allowlist. The required hand-ML selection is removed, no Google MediaPipe model/runtime binaries are downloaded or distributed, and no POST collection endpoint is enabled.

## Decisions required before creating any Codespace

The owner must independently approve **Codespaces usage, charges/quotas, provider privacy and access controls, and an operator-only trial**. Codespaces is third-party cloud compute, not an automatic feature of the ChatGPT iPhone app. Check GitHub billing, whether Codespaces is available to your account, and whether its private forwarded HTTPS origin grants iOS Safari camera permissions. There is no promise of zero cost or Safari compatibility.

If owner approval has not been given, **STOP here**. Do not create a Codespace, enable a port, request camera permission, share a URL or upload project files.

## Manual iPhone steps — only after separate owner approval

1. In iPhone Safari, open the ANIMATE GitHub repository and select the **engineering branch containing this proposal**. In the **Code → Codespaces** interface, check actual eligibility and pricing. Creating a Codespace is a chargeable external action; it must be done by the owner. If the mobile UI does not expose Codespaces adequately, do not claim the setup works.
2. Once explicitly approved and a Codespace has been created, inspect the Codespaces **Ports** view. If port 8765 is present, set its visibility to **Private**. If absent, add port 8765 manually, set **Private**, then copy its exact forwarded host. Do not choose Public or Organisation visibility for a personal operator test. The `.devcontainer` file requests Private but does not prove it is enforced.
3. From the Codespaces integrated terminal, run only the model-free packager (the output is placed outside the Git checkout):

   ```sh
   stage_dir=$(mktemp -d)
   python tools/build_baseline_preview.py --output "$stage_dir/candidate"
   ```

4. Recheck that port 8765 is **Private**, and confirm the forwarded hostname actually ends in `.app.github.dev` and matches the form `<CODESPACE_NAME>-8765.app.github.dev`. An alternative GitHub hostname will be **rejected** pending engineering review, not bypassed. Start the server manually; the hostname is obtained from the owner-visible Ports tab, **not from an untrusted message**:

   ```sh
   ANIMATE_OWNER_PREVIEW_APPROVED=YES python tools/serve_codespaces_baseline.py \
     --site-dir "$stage_dir/candidate/site" \
     --forwarded-host "$CODESPACE_NAME-8765.app.github.dev" \
     --acknowledge-private-port
   ```

5. Before allowing the camera or entering data, verify from the Codespaces Ports interface that **no unauthenticated viewer can access the forwarded port**. Check the HTTPS certificate, origin, headers, six-file integrity and denial of model/manifest paths. The current hosted-preview auditor expects a particular authentication response policy and has not yet been run against Codespaces; redirects to GitHub login may be reported as **unverified**, not automatically as a passing auth check. **Do not claim secure live hosting before an independent live review.**
6. Only after a separate operator privacy and HTTPS approval, open the resulting URL **directly in iPhone Safari**, not an embedded webview. Try touch-only navigation first; then request camera access. Record actual permission prompts, cold start, page visibility/mute, control stability, iPhone thermal behaviour, and the debug-only 60-second coverage-validated performance sample. The [device metric protocol](IPHONE_DEVICE_METRICS_PROTOCOL.md) states how to report failures and what the measurements do not prove.
7. When finished, terminate the server using Ctrl+C, close the forwarded port, **stop and, when appropriate, delete the Codespace** to stop potential billing and remove preview infrastructure. Downloaded reports, local Safari data and provider logs may persist separately; check retention and remove them under the approved policy.

## Engineering evidence vs. actual preview proof

The new local tests verify that manual approval is required, the generated candidate is integrity checked, port visibility defaults are *requested* as Private, the server binds only to loopback, Host validation denies unexpected values, no POST collection occurs, and model/manifest URLs fail.

These tests **do not** verify whether Codespaces can be opened effectively from the user's specific iPhone, the account's billing rights, GitHub's live Private port enforcement, the forwarded Host header, provider-added policies/telemetry or physical Safari camera behaviour. Those are conditions to assess **before** calling this preview functional.

**No model redistribution approval** is implied by this no-ML route. The exact MediaPipe 1.2.3 licensing issue remains open.

See also [IPHONE_PREVIEW_DECISION_GATE.md](IPHONE_PREVIEW_DECISION_GATE.md), [COMMERCIAL_EVIDENCE_GATE.md](COMMERCIAL_EVIDENCE_GATE.md), and the consolidated acquisition review dossier.
