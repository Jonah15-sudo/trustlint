# OFE Experimental Campaign — Comparison Report

**Generated:** 2026-05-31T09:30:09.068076+00:00

## Protocol

- Condition A: SPL Baseline (TLS only)
- Condition B: SPL + OFE structural signals
- Training items: 90
- OFE signals injected: 15
- Curricula: standard, expired, clean, mixed, timeout_risk
- Total challenges evaluated: 25

---

## 1. What improved?

- No improvements detected.

## 2. What did not improve?

- **Accuracy**: Δ = +0.0000 (A: 0.84, B: 0.84)
- **Error Rate**: Δ = +0.0000 (A: 0.0, B: 0.0)
- **Collapse Rate**: Δ = +0.0000 (A: 0.2, B: 0.2)
- **Total Weaknesses**: Δ = +0.0000 (A: 18.0, B: 18.0)

## 3. What regressed?

- **Calibration Error**: Δ = +0.0040 (A: 0.3345, B: 0.3385)

## 4. Which weaknesses changed?

| Weakness | A Freq | B Freq | A %total | B %total | Δ Freq | Δ %pct | Interpretation |
|---|---|---|---|---|---|---|---|
| hsts_missing | 0 | 0 | 0.0% | 0.0% | +0 | +0.0% | unchanged |
| http_error_flag | 5 | 0 | 27.8% | 0.0% | -5 | -27.8% | improvement |
| partial_flag | 5 | 1 | 27.8% | 5.6% | -4 | -22.2% | improvement |

### Statistical Notes

- **hsts_missing**: A count = 0 / 18 total weaknesses; B count = 0 / 18 total weaknesses. Insufficient evidence.
- **http_error_flag**: A count = 5 / 18 total weaknesses; B count = 0 / 18 total weaknesses. reduction detected (Δ = -5.0000).
- **partial_flag**: A count = 5 / 18 total weaknesses; B count = 1 / 18 total weaknesses. reduction detected (Δ = -4.0000).

## 5. Which capability boundaries changed?

- **A fraction below confidence threshold (0.5)**: 0.2800
- **B fraction below threshold**: 0.2800
- **Delta**: +0.0000
- A boundary crossings: difficulty=0.5966 (up), difficulty=0.5972 (down), difficulty=0.6027 (up), difficulty=0.6367 (down), difficulty=0.6368 (up), difficulty=0.6765 (down), difficulty=0.6769 (up), difficulty=0.7166 (down), difficulty=0.7169 (up), difficulty=0.7565 (down), difficulty=0.7569 (up)
- B boundary crossings: difficulty=0.5966 (up), difficulty=0.5972 (down), difficulty=0.6046 (up), difficulty=0.6366 (down), difficulty=0.6368 (up), difficulty=0.6764 (down), difficulty=0.6769 (up), difficulty=0.7166 (down), difficulty=0.7169 (up), difficulty=0.7564 (down), difficulty=0.7569 (up)

### Difficulty Distribution

| Bucket | Range | A Accuracy | B Accuracy | Δ |
|---|---|---|---|---|
| high_07_10 | 0.7-1.0 | 1.0000 | 1.0000 | +0.0000 |
| low_00_03 | 0.0-0.3 | 0.0000 | 0.0000 | +0.0000 |
| mid_03_05 | 0.3-0.5 | 0.0000 | 0.0000 | +0.0000 |
| mid_05_07 | 0.5-0.7 | 0.7333 | 0.7333 | +0.0000 |

## 6. What evidence supports the conclusions?

**Sample sizes:**
- Training: 90 TLS items + 15 OFE signals
- Evaluation: 25 challenge predictions per condition
- Weaknesses: 18 (A), 18 (B)
- Collapse sequences: 5 per condition
- Calibration samples: 25 (A), 25 (B)

**Absolute differences (B - A):**
- Accuracy: +0.0000 (+0.00%)
- Calibration error: +0.0040 (+1.20%)
- Error rate: +0.0000
- Collapse rate: +0.0000
- Weakness count: +0.0000

## 7. What uncertainty remains?

1. **Sample size uncertainty.** The experiment uses a single training run per condition. Results may vary with different random seeds or dataset splits.
2. **OFE signal design.** Structural signals were generated synthetically. Real OFE signals from production data may produce different outcomes.
3. **DSL coupling.** The experiment DSL includes OFE-aware features. A different DSL design could change the comparison.
4. **Binary metrics.** Accuracy and collapse are binary-sampled. Continuous metrics (calibration, confidence) may show different patterns at higher resolution.
5. **Single run.** No confidence intervals are computed. Repeated runs with varied random seeds are needed for statistical significance testing.
6. **Label assignment.** All OFE signals received label=False. Different label assignments could change the graph update dynamics.

---

## Summary

Weakness frequencies shifted between conditions in this campaign. However, differences are small and may not generalize. Replication with larger datasets is recommended.