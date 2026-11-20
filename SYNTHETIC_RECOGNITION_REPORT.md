# ANIMATE v0.4 — synthetic recognition stress report

**Generated images only. NOT iPhone results or true household-object accuracy.**

- Positive generated frames: **1080**; centre-correct detections: **66.7%**.
- Negative generated frames without a same-colour background: **1080**; detections: **0%**.
- Separate same-hue-surface negative controls: **540** frames; false detections: **66.7%**.
- Frames generated with deterministic random pixel jitter, coloured 12-pixel disk, some solid-colour patches, and illumination scalings. They are artificial, spatially and temporally correlated, and must not be used for confidence intervals or product claims.

## Synthetic centre-correct detection by condition

| Colour | Bright plain | Bright cluttered | Normal plain | Normal cluttered | Dim plain | Dim cluttered |
|---|---:|---:|---:|---:|---:|---:|
| Blue | 100% | 100% | 100% | 100% | 0% | 0% |
| Green | 100% | 100% | 100% | 100% | 0% | 0% |
| Red | 100% | 100% | 100% | 100% | 0% | 0% |

**Interpretation:** Dim exposures and same-hue surfaces are not minor cosmetic edge cases; the existing colour detector is unsuitable for claims of general recognition. The synthetic matrix is informative for engineering risk only. It is a separate diagnostic from the 600-fresh-frame real-iPhone measurement that remains to be performed.

Regenerate with `node tests/recognition_matrix.js`. No test picture or participant data is stored.
