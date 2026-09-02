# AI Probability Calibration Report

**Generated:** 2026-09-01T16:06:33.419555+00:00
**Overall Classification:** MIXED
**Brier Score:** 0.2472  |  **ECE:** 0.0226  (2.3pp)
**Resolved signals:** 2049 / 2049

## Calibration Table
| Bucket | N | Predicted | Actual WR | Error (pp) | Classification |
| --- | --- | --- | --- | --- | --- |
| 0–10% | 0 | 5% | 0.0% | 5.0 | INSUFFICIENT_DATA |
| 10–20% | 0 | 15% | 0.0% | 15.0 | INSUFFICIENT_DATA |
| 20–30% | 0 | 25% | 0.0% | 25.0 | INSUFFICIENT_DATA |
| 30–40% | 603 | 35% | 40.5% | 5.5 | UNDERCONFIDENT |
| 40–50% | 1446 | 45% | 45.9% | 0.9 | WELL_CALIBRATED |
| 50–60% | 0 | 55% | 0.0% | 55.0 | INSUFFICIENT_DATA |
| 60–70% | 0 | 65% | 0.0% | 65.0 | INSUFFICIENT_DATA |
| 70–80% | 0 | 75% | 0.0% | 75.0 | INSUFFICIENT_DATA |
| 80–90% | 0 | 85% | 0.0% | 85.0 | INSUFFICIENT_DATA |
| 90–100% | 0 | 95% | 0.0% | 95.0 | INSUFFICIENT_DATA |

## Findings
- Overall calibration: MIXED
- Brier score: 0.2472 (no-skill baseline = 0.25; lower = better)
- Expected Calibration Error (ECE): 0.0226 (2.3pp average error)
- Worst-calibrated bucket: 30–40% (predicted 35%, actual 40.5%, error 5.5pp, n=603)

## Asset Brier Scores
- BTC/USD: 0.2476
- XAU/USD: 0.2467