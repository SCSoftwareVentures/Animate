# ANIMATE v0.7 Codex import task

Target repository: https://github.com/SCSoftwareVentures/Animate
Target branch: engineering/animate-v07-hardening
Draft PR: https://github.com/SCSoftwareVentures/Animate/pull/1

1. Use the extracted contents of the accompanying ZIP. Do not commit the ZIP itself, research exports, identity-linked ledgers, credentials or the local test logs.
2. Preserve source directories `site/`, `tests/`, `tools/`, and `.github/workflows/` and the existing public-repo `.gitignore`.
3. Resolve branch conflicts by preserving restrictive privacy/deployment safeguards. Inspect every file added to the public repository.
4. Run all suites: `node tests/test_core.js`, `node tests/test_foreground.js`, `node tests/test_hand_ml.js`, `python tests/offline_browser.py`, `python tests/test_hand_browser.py`, `python tests/e2e.py` in Actions, and `python tests/check_release.py`.
5. Treat `python tests/check_release.py --publish` refusal as expected until independently reviewed model/runtime assets are available. Do not bypass the gate.
6. Fix any CI failures; update draft PR with verified evidence, exact run links, test counts, unresolved failures and security limitations. Do not automatically merge, deploy, or recruit participants.
7. Do not claim actual MediaPipe inference or any iPhone performance without model assets and real-device measurements. Ask before using third-party model binaries whose redistribution terms remain unreviewed.

Local evidence: core 34; foreground 11; ML adapter 19; offline baseline browser 33; targeted browser 14. These are *not GitHub CI results*. Full-origin browser suite was blocked by local networking restrictions, and no physical iPhone test was run.
