# SPL Validation Findings

## Experiment 1: Observation Mode (Cold-Start Graph)

**Method:** SPL loaded with zero training data. OnlineCausalGraphLearner starts with
no edges. Each probe result is ingested as an EvidenceArtifact and processed once.

**Result:** 28.3% accuracy on 120 real TLS domains.

| Metric | Value |
|---|---|
| Accuracy | 28.3% |
| False positive rate | 100.0% |
| True negatives | 0 / 86 |
| Conclusion | Cold-start SPL flags every domain as risk — no decision-making value |

## Experiment 2: Proxy-Trained Evaluation

**Method:** SPL trained on probe results with proxy labels (label=True for any non-VALID_TLS
classification), then evaluated on the same dataset.

**Result:** 96.67% accuracy — identical to rule-based baseline.

| Metric | Baseline | SPL Proxy-Trained |
|---|---|---|
| Accuracy | 96.67% | 96.67% |
| Mismatches vs baseline | — | 0 / 120 |
| Conclusion | SPL learned nothing the rules didn't already encode |

## Experiment 3: Holdout Generalization (Not Yet Conducted)

**Status:** PENDING — requires 5000+ labeled real TLS samples with diverse HSTS/CSP profiles.

The `real_tls_collected.jsonl` dataset currently has 2,179 rows, with no HSTS/CSP diversity.
A 7-week collection plan is documented in `ROADMAP_REAL_TLS_DATA.md`.

## Key Findings

1. **The rule-based adapter is sufficient** — 96.67% accuracy with zero ML, zero dependencies.
2. **SPL adds no lift** — proxy-trained results are identical to baseline.
3. **Cold-start SPL is harmful** — 28.3% accuracy, 100% FPR, flags everything as risk.
4. **Holdout generalization cannot be assessed** until 5000+ diverse labeled samples exist.

## Recommendation

Do not use SPL Core for production decisions. All production TLS risk analysis should use
the deterministic `tls_policy_adapter` + `decision_orchestrator` pipeline.

See the full evaluation report at `reports/validation_evaluation/VALIDATION_EVALUATION_REPORT.md`
and the adversarial validation report at `reports/adversarial_validation_report.md`.
