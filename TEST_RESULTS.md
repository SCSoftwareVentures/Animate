# ANIMATE v0.7 engineering verification — 21 Nov 2026

## Reproduced locally in the isolated container

- Core unit suite: **34/34 passed** (`node tests/test_core.js`).
- Foreground tracker suite: **11/11 passed** (`node tests/test_foreground.js`).
- ML-adapter unit suite: **19/19 passed** (`node tests/test_hand_ml.js`), including five new checks for timeout, late return, restart cleanup and invalid timeout configuration.
- Offline Chromium baseline: **33/33 passed** (`python tests/offline_browser.py`).
- Offline Chromium hand/interruptions: **14/14 passed** (`python tests/test_hand_browser.py`), including seven new checks for hung model startup and invalidated colour calibration.
- Syntax checks: **passed** for app.js, core.js, foreground.js and hand_ml.js.
- `python tests/check_release.py`: **passed** for source scope and local repository hygiene (not a substitute for examining GitHub history).

## Not proven

- **Full-origin browser suite NOT VERIFIED:** invoking `python tests/e2e.py /usr/bin/chromium` reached a local server, but Playwright navigation failed with `net::ERR_BLOCKED_BY_ADMINISTRATOR`. It must be rerun on GitHub CI and its result inspected.
- **ML asset and licence gate remains BLOCKED:** no reviewed model file or runtime is bundled. `python tests/check_release.py --publish` is expected to refuse publication.
- **No real pretrained model inference**, iPhone Safari run, camera permission regression on a real phone, performance/accuracy evidence, VoiceOver assessment, privacy legal review, actual demand test or paying pilot.
- **GitHub source import pending:** PR #1 currently includes safety and integration documentation only. No CI success is claimed.

Synthetic-frame/browser results are engineering stress probes, not real-world performance rates or consumer demand evidence.
