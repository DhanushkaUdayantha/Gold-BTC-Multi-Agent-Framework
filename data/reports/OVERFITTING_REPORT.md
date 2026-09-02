# Overfitting / Multiple-Testing Audit Report

**Generated:** 2026-09-01T16:06:34.015106+00:00
**Risk Level:** 🔴 HIGH
**Total Comparisons:** 77  |  **Bonferroni α:** 0.0006

## Threshold Note
With 77 total comparisons, Bonferroni-corrected α = 0.0006. A result is significant only if p < 0.0006.

## Summary
| Metric | Value |
| --- | --- |
| Total Experiments | 9 |
| Filters Tested | 1 |
| Policies Tested | 0 |
| Sig @ α=0.05 | 0 |
| Sig @ Bonferroni | 0 |

## Findings
- Total comparisons made: 77 across 9 experiments
- Multiple-testing risk: HIGH
- Nominal α=0.05 threshold: 0 experiment(s) would pass
- Bonferroni α=0.0006 threshold: 0 experiment(s) pass
- WARNING: High multiple-testing risk. Any 'statistically significant' result may be a false positive. All findings require independent OOS confirmation.

## Recommendations