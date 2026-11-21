# ANIMATE — Offline audit of future physical-iPhone operator reports

**Status: code and synthetic regression fixtures only. No physical iPhone trial is claimed. No report has been received or independently verified.** This tool is for a future owner-approved device trial, not a means to bypass a private HTTPS preview or the MediaPipe licence gate.

## Why this exists

A 60-second diagnostic with a full timer but too few processed camera frames is not adequate evidence. Likewise, a 10-second negative control with no dwell events is uninformative if the object was never observed. This tool audits the *shape, limits and denominators* of the existing app's RAM-only reports; it never authenticates an iPhone or proves recognition accuracy.

The review packet contains only the approved exact-field app summaries. Its source SHA, iPhone claim, lighting conditions and statement of advance protocol registration are **operator declarations, not independently verified facts**. Even a packet receiving \`OPERATOR_PROXY_COMPLETE_UNVERIFIED\` establishes **zero independently verified recognition accuracy, real-device provenance, user demand or buyer interest**.

## Preconditions (none satisfied yet)

- Owner explicitly approves a physically tested, genuine access-controlled, $0 HTTPS preview. A provider dashboard marked Private alone is not enough.
- Confirm the deployment's exact commit SHA against the private operator build receipt, not just the visible \`0.7.0\` version.
- Obtain explicit permission for a camera test under the device protocol; no model/WASM distribution is permitted.
- Before testing, register one method (\`colour\` or \`foreground\`) and the lighting conditions \`bright\`, \`ordinary\`, \`dim\`. Each trial is one independent attempt. **Include failed or interrupted attempts**, even if subsequently repeated.

## Packet shape (future private use only)

One local JSON object with precisely:

- \`schema: "ANIMATE_IPHONE_OPERATOR_PACKET_V1"\`
- \`sourceCommit\`: 40-character lowercase Git SHA **as claimed by the operator**
- \`deviceClaim: "self-reported-physical-iphone"\`
- \`registeredBeforeTesting\`: boolean self-declaration; does not constitute a preregistration timestamp
- \`detector\`: \`colour\` or \`foreground\` (never mix methods)
- \`performanceTrials\`: list of \`{"lighting": "bright|ordinary|dim", "report": <60-second numeric summary>}\`
- \`zoneTrials\`: list of \`{"lighting": "bright|ordinary|dim", "report": <10-second control summary>}\`

The \`report\` value is the **unchanged** JSON copied from the app's respective debug report. Do not add participant IDs, names, device serials, user-agent strings, images, coordinates, browser console logs, analytics, notes, receipts or test metadata to this packet.

For the minimum reviewable packet, provide at least **three adequate 60-second performance trials**, covering all three lighting conditions, plus **three adequate 10-second controls per condition** (absent, left, middle, right), likewise across all three lighting conditions. All additional attempts, including incomplete ones, remain in the denominator. Insufficient coverage yields \`INSUFFICIENT_OPERATOR_PROXY_COVERAGE\`; it must not be discarded to improve results.

### Offline CLI (for a future authorised reviewer)

\`\`\`sh
python tools/audit_iphone_evidence.py /path/to/private/operator-packet.json
\`\`\`

This requires a Python-capable environment; **it is not executable within the user's iPhone-only ChatGPT app**. No other application, hosting service, device or paid account is presumed available. The tool has no network dependency and prints only an aggregate report, never the input source text. The CI test uses synthetic fixtures only. If the user later elects to share redacted operator reports in ChatGPT, that would be a separate voluntary disclosure.

## What the result means

- \`OPERATOR_PROXY_COMPLETE_UNVERIFIED\` means only that the claimed operator reports have the required shape, sampling coverage, and trial/lighting denominators.
- \`INSUFFICIENT_OPERATOR_PROXY_COVERAGE\` means the claimed trials are too few, incomplete, or lack one of the registered conditions. It is not a product pass.
- Malformed or contradictory individual reports are rejected entirely; they are not counted as successes.
- Count \`unexpectedDwellProxies\` as **reported dwell events**, not independently labelled false positives. The script does not produce an accuracy, sensitivity, specificity or false-alarm *rate*.
- Five explicit machine-readable verification/market fields remain \`false\` even for a complete packet. A tester can copy or forge JSON; SHA strings are not signatures. A physical iPhone, independent observers and buyer interviews remain separate prerequisites.

**Never commit actual operator packets to this public repository.** A successful CI run demonstrates only that the source validator resists synthetic adversarial fixtures.
