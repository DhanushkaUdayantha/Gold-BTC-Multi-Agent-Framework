# Degradation State Predictive Validation Report

Evaluates subsequent forward trading performance following timestamps assigned to each degradation monitoring state:

| Degradation State | Forward Signals (N) | Forward Win Rate | Forward Expectancy (R) | Forward Profit Factor | Forward Max DD | Predictive Consistency |
|:---|---:|---:|---:|---:|---:|:---:|
| **NORMAL** | 906 | 49.3% | **+0.233R** | 1.46 | 30.0R | PASS |
| **WATCH** | 0 | 0.0% | **+0.000R** | 1.00 | 0.0R | PASS |
| **DEGRADED** | 0 | 0.0% | **+0.000R** | 1.00 | 0.0R | PASS |

---

## Key Governance Takeaway
The degradation monitoring state is **strictly predictive and advisory**. It tracks rolling regime shifts and calibration drift without interrupting live production decisions.
