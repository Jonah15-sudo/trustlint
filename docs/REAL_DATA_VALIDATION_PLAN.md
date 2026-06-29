# Real Data Validation Plan

## Objective

Validate OFE structural signals against real TLS traffic data before any promotion decision. This plan defines the protocol, minimum requirements, and success/failure criteria.

---

## 1. Required Real TLS Dataset Format

Format: JSONL (one JSON object per row) or CSV with header row.
See `docs/REAL_TLS_DATA_CONTRACT.md` for the exact schema.

---

## 2. Minimum Sample Size

| Requirement | Minimum |
|---|---|
| Total TLS cases | 5,000 |
| Distinct sources | 3 |
| Positive labels (risky) | ≥500 |
| Negative labels (clean) | ≥500 |
| Labeled rows | 100% |

---

## 3. Required Fields

Each row must contain:

- `case_id` — unique identifier
- `timestamp` — ISO-8601 datetime
- `tls_valid` — boolean
- `tls_expiry_days` — integer
- `http_status` — string
- `partial_response` — boolean
- `timeout` — boolean
- `hsts_present` — boolean
- `csp_present` — boolean
- `latency_ms` — integer
- `bytes_received` — integer
- `label` — boolean (true = risky, false = clean)

---

## 4. Label Requirements

- Labels must be ground truth, not model output
- Labels must be binary (risky / clean)
- Label weights may be assigned per source (min 1.0, max 3.0)
- At least 10% of rows must be positive (risky)

---

## 5. Baseline vs OFE Protocol

### Condition A — SPL Baseline (TLS only)
1. Train pipeline on TLS training data
2. Run 5 exploration curricula (standard, expired, clean, mixed, timeout_risk)
3. Collect: accuracy, calibration, error rate, collapse rate, weakness counts

### Condition B — SPL + OFE structural signals
1. Train pipeline on same TLS training data
2. Inject OFE structural signals from `FrontierExplorer.wrap_structural_signals()`
3. Run 5 exploration curricula (same as Condition A)
4. Collect: accuracy, calibration, error rate, collapse rate, weakness counts

### Replication
- Run 12 independent A/B campaigns with different random seeds
- Each campaign uses the same dataset but different shuffle order and signal generation

---

## 6. Metrics to Collect

| Metric | Source | Notes |
|---|---|---|
| Accuracy | `MetricsCollector.accuracy()` | Per-condition and delta |
| Calibration Error | `MetricsCollector.confidence_calibration()` | ECE and mean calibration error |
| Error Rate | `MetricsCollector.failure_rate()` | Per-condition |
| Collapse Rate | `MetricsCollector.collapse_frequency()` | Across all confidence sequences |
| Weakness Count | `WeaknessExtractor.extract()` | Total per condition |
| partial_flag frequency | Weakness frequency breakdown | Feature-level |
| http_error_flag frequency | Weakness frequency breakdown | Feature-level |
| hsts_missing frequency | Weakness frequency breakdown | Feature-level |
| Difficulty distribution | `MetricsCollector.difficulty_distribution()` | Per-bucket accuracy |
| Capability boundary | `MetricsCollector.capability_boundary_position()` | Crossings and fraction below |

---

## 7. Promotion Criteria

A signal may be promoted to **PROMOTE** only if ALL of the following are met on real data:

1. **Reproducible improvement** on real data across ≥70% of campaigns
2. **No aggregate accuracy regression** — accuracy delta ≥ 0.0 (non-negative)
3. **No calibration regression** — calibration error delta ≤ 0 (non-positive or unchanged)
4. **No increase in total weakness count** — weakness count delta ≤ 0
5. **No SPL Core changes** — `spl_v7/` remains unchanged
6. **Effect size** Cohen's |d| ≥ 0.2 for the signal being promoted
7. **Minimum campaign count** — at least 12 replication campaigns

---

## 8. Rejection Criteria

A signal is rejected if ANY of the following occur on real data:

1. Reproducible regression (≥70% of campaigns show degradation)
2. Accuracy delta negative and replication rate ≥50%
3. Calibration error increased and replication rate ≥50%
4. Weakness count increased and replication rate ≥50%
5. Less than 12 campaigns completed

---

## 9. Data Quality Checks

Before running the validation protocol:

- [ ] All required fields present and non-null
- [ ] No duplicate `case_id` values
- [ ] Timestamps are chronologically ordered
- [ ] Label imbalance is within acceptable range (≥10% positive)
- [ ] No `label` leaks in feature fields
- [ ] At least 3 distinct source values
- [ ] No rows with impossible values (negative latency, expiry_days > 100 years)
- [ ] Schema matches `docs/REAL_TLS_DATA_CONTRACT.md`

---

## 10. Safety Rules

1. **No real data validation, no promotion.** OFE signals may not be promoted based on synthetic data alone.
2. **No SPL Core modification.** The validation runs through the existing pipeline without touching `spl_v7/`.
3. **No threshold tuning.** All detection thresholds (collapse drop=0.20, confidence threshold=0.5, etc.) remain at their current values.
4. **No cherry-picking.** All 5 curricula must be run per campaign. Partial selection is not permitted.
5. **Results are advisory.** Even PROMOTE classification does not authorize automatic deployment. Human review required.
6. **Re-run on new data.** Any promotion expires if the underlying TLS data distribution changes significantly.
