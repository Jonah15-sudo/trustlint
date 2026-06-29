# OFE Signal Promotion Readiness

Generated: 2026-05-31 11:04

Based on 12-campaign replication study (25 challenges per campaign).

**⚠ ALL DATA IS SYNTHETIC — No real TLS data has been used.**
**No OFE signal is approved for production integration until validated on real data.**

---

## Classification Criteria

| Classification | Definition |
|---|---|
| **PROMOTE** | Signal shows reproducible improvement across ≥70% of campaigns AND effect size |d| ≥ 0.2 OR improvement in ≥50% of campaigns with |d| ≥ 0.5 **AND validated on real TLS data** |
| **HOLD_PENDING_REAL_DATA** | Promising synthetic evidence (≥70% replication rate) but not yet validated on real data |
| **HOLD** | Evidence mixed (30–70% replication rate) OR effect size negligible despite high replication |
| **REJECT** | No evidence of improvement (≤30% replication) OR consistent regression across campaigns |

---

## Signal Classifications


### Accuracy Δ

**Classification: REJECT**

| Metric | Baseline | OFE | Δ |
|--------|----------|-----|------|

| Mean Δ | -0.0567 | — | — |
| Replication Rate | 8% | — | — |
| Cohen's d | -0.8967 (large) | — | — |

**Justification:** 1 campaign(s) showed improvement out of 12. Effect size is large. No evidence of reproducible improvement — reject.

### Calibration Error Δ

**Classification: REJECT**

| Metric | Baseline | OFE | Δ |
|--------|----------|-----|------|

| Mean Δ | +0.0086 | — | — |
| Replication Rate | 0% | — | — |
| Cohen's d | +0.9733 (large) | — | — |

**Justification:** 0 campaign(s) showed improvement out of 12. Effect size is large. No evidence of reproducible improvement — reject.

### Error Rate Δ

**Classification: REJECT**

| Metric | Baseline | OFE | Δ |
|--------|----------|-----|------|

| Mean Δ | +0.0000 | — | — |
| Replication Rate | 0% | — | — |
| Cohen's d | -0.8967 (large) | — | — |

**Justification:** 0 campaign(s) showed improvement out of 12. Effect size is large. No evidence of reproducible improvement — reject.

### Collapse Rate Δ

**Classification: REJECT**

| Metric | Baseline | OFE | Δ |
|--------|----------|-----|------|

| Mean Δ | +0.0333 | — | — |
| Replication Rate | 0% | — | — |
| Cohen's d | +0.4393 (small) | — | — |

**Justification:** 0 campaign(s) showed improvement out of 12. Effect size is small. No evidence of reproducible improvement — reject.

### Weakness Count Δ

**Classification: REJECT**

| Metric | Baseline | OFE | Δ |
|--------|----------|-----|------|

| Mean Δ | +1.6667 | — | — |
| Replication Rate | 0% | — | — |
| Cohen's d | +1.0037 (large) | — | — |

**Justification:** 0 campaign(s) showed improvement out of 12. Effect size is large. No evidence of reproducible improvement — reject.

### Weakness: partial_flag

**Classification: HOLD_PENDING_REAL_DATA**

| Metric | Baseline | OFE | Δ |
|--------|----------|-----|------|

| Mean Frequency | 5.0 | 0.8 | -4.2 |
| Replication Rate | 100% | — | — |
| Cohen's d | -15.1383 (large) | — | — |

**Justification:** 12 campaign(s) showed improvement out of 12. Consistent reduction under synthetic replication, but no real TLS data has been tested. Must replicate on real data before promotion. See `docs/REAL_DATA_VALIDATION_PLAN.md`.

### Weakness: http_error_flag

**Classification: HOLD_PENDING_REAL_DATA**

| Metric | Baseline | OFE | Δ |
|--------|----------|-----|------|

| Mean Frequency | 5.0 | 0.0 | -5.0 |
| Replication Rate | 100% | — | — |
| Cohen's d | +0.0000 (negligible) | — | — |

**Justification:** 12 campaign(s) showed improvement out of 12. Consistent reduction under synthetic replication, but no real TLS data has been tested. Must replicate on real data before promotion. See `docs/REAL_DATA_VALIDATION_PLAN.md`.

### Weakness: hsts_missing

**Classification: REJECT**

| Metric | Baseline | OFE | Δ |
|--------|----------|-----|------|

| Mean Frequency | 0.0 | 0.0 | +0.0 |
| Replication Rate | 0% | — | — |
| Cohen's d | +0.0000 (negligible) | — | — |

**Justification:** 0 campaign(s) showed improvement out of 12. No evidence of improvement — reject.

---

## Summary

| Classification | Count |
|---|---|
| **PROMOTE** | 0 |
| **HOLD_PENDING_REAL_DATA** | 2 |
| **HOLD** | 0 |
| **REJECT** | 6 |

**Overall verdict:** No OFE signal is approved for production integration. 2 signals show promising synthetic replication but require real-data validation before promotion. Aggregate metrics (accuracy, calibration, error rate, collapse rate, weakness count) all reject. See `docs/REAL_DATA_VALIDATION_PLAN.md` for the validation protocol.
