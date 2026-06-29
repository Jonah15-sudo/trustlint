# OFE Replication Report

Generated: 2026-05-31 11:03

Campaigns: 12
Challenges per campaign: 25
Protocol: Identical across all campaigns (same training sources, same curricula,
           same pipeline configuration). Variation introduced via campaign_seed
           controlling training data shuffle order and OFE signal generation.

---

## Executive Summary

12 independent A/B comparison campaigns were executed with different seeds,
training orders, and OFE signal values.

### Key Findings

| Metric | Mean Δ | 95% CI | Cohen's d | Reproducibility |
|--------|--------|--------|-----------|-----------------|

| Accuracy Δ | -0.0567 | [-0.0879, -0.0255] | -0.8967 | not_repeated |
| Calibration Error Δ | +0.0086 | [0.0072, 0.0100] | +0.9733 | not_repeated |
| Error Rate Δ | +0.0000 | [0.0000, 0.0000] | -0.8967 | not_repeated |
| Collapse Rate Δ | +0.0333 | [-0.0107, 0.0774] | +0.4393 | not_repeated |
| Weakness Count Δ | +1.6667 | [0.8194, 2.5139] | +1.0037 | not_repeated |

### Weakness-Level Findings

| Weakness | Mean A | Mean B | Mean Δ | Effect Size | Reproducibility |
|----------|--------|--------|--------|-------------|-----------------|

| partial_flag | 5.0 | 0.8 | -4.2 | -15.1383 | repeated |
| http_error_flag | 5.0 | 0.0 | -5.0 | +0.0000 | repeated |
| hsts_missing | 0.0 | 0.0 | +0.0 | +0.0000 | not_repeated |


---

## Q1: Is the OFE accuracy improvement reproducible?

Across 12 campaigns, the mean accuracy difference was -0.0567 (95% CI [-0.0879, -0.0255], Cohen's d=-0.8967). Improvement observed in 1/12 campaigns (8%).

### Verdict

> The accuracy effect is **not reproducible**. The effect size (d=-0.90) is consistent but small.



---

## Q2: Does OFE improve calibration reproducibility?

Across 12 campaigns, mean calibration error difference was +0.0086 (95% CI [0.0072, 0.0100], Cohen's d=+0.9733). Improvement (calibration error reduction) in 0/12 campaigns.

### Verdict

> Calibration improvement is **not reproducible**.



---

## Q3: Does OFE repair http_error_flag?

Across 12 campaigns, mean baseline frequency was 5.0, mean OFE frequency was 0.0, mean difference -5.0. Improvement in 12/12 campaigns (100%).

### Verdict

> http_error_flag repair **does replicate** — consistent reduction observed.



---

## Q4: Does OFE repair partial_flag?

Across 12 campaigns, mean baseline frequency was 5.0, mean OFE frequency was 0.8, mean difference -4.2. Improvement in 12/12 campaigns.

### Verdict

> partial_flag repair **does replicate** — consistent reduction observed.



---

## Q5: Are aggregate metrics stable across campaigns?

Of 2 aggregate metrics, 1 (50%) showed negligible mean change (|Δ| < 0.01). Error Rate Δ: mean Δ=+0.0000 (σ=0.0000, d=-0.8967) Collapse Rate Δ: mean Δ=+0.0333 (σ=0.0778, d=+0.4393)

### Verdict

> Aggregate metrics show **some variation** (50% stable).



---

## Q6: Which effects repeated, disappeared, or remain uncertain?

**Repeated** (2): partial_flag, http_error_flag. **Disappeared** (1): hsts_missing. **Uncertain** (0): none.

### Verdict

> Effects with replication evidence: partial_flag, http_error_flag. These require larger-scale confirmation.



---

## Q7: Is OFE signal promotion justified based on this evidence?

Replication campaign: 3 weakness categories tracked, 2 categories show reproducible improvement. Overall accuracy effect: -0.0567. 

### Verdict

> **Conditional.** Some weakness-level effects replicate under synthetic data, but aggregate metrics do not. Promotion would be premature without understanding why improvement does not propagate to system-level accuracy. **All results are based on synthetic data — real TLS validation is required before any promotion decision.**


## Reference: Promotion Readiness

See `PROMOTION_READINESS.md` for per-signal PROMOTE / HOLD / REJECT
classifications based on these results.


---
