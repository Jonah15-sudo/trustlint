# Validation Leakage Audit

Audits the `scripts/run_real_tls_spl_decision_validation.py` runner for data leakage,
proxy-label contamination, and expectation-policy overlap.

---

## 1. Does the runner train on the same dataset it evaluates?

**Before Phase 3.5**: Yes. The runner probes all 61 domains, trains the pipeline on those
same probe results with proxy labels, then evaluates on the same probe results without
labels. The causal graph learns from the same data it later classifies.

**After Phase 3.5**: No. Three modes exist:

| Mode | Training | Evaluation | Leakage |
|------|----------|------------|---------|
| `observation` | None (cold-start graph) | All probe results | None — graph is not trained |
| `proxy-trained` | All probe results with proxy labels | Same probe results without labels | **Yes** — same data is used for both training and evaluation. This is documented as a limitation. |
| `holdout` (Phase 4) | Separate training set (43 domains) with external clean/dirty labels | Unseen holdout set (18 domains) | None — training and evaluation domains are disjoint; external labels are from a different data source |
| `stratified holdout` (Phase 5) | Expanded 83-domain training set with external clean/dirty labels | ~37 holdout domains per run (10 stratified splits) | None — train/eval are disjoint across all runs |

In `proxy-trained` mode, training leakage exists but is accepted because:
- The goal is to measure whether the SPL pipeline *can* learn from TLS probe features, not to measure generalization accuracy.
- No ground-truth labels are available; proxy labels are the only viable training signal.
- The report clearly labels results as `proxy-trained`.

## 2. Does the runner use expected labels during decision generation?

**Before Phase 3.5**: No. Expected labels from `--expectations` are loaded after probing
and are only used to compute policy conformance scores. Decision generation does not
read or depend on expectations.

**After Phase 3.5**: Same. Expectations are loaded but stored separately. They are passed
only to `_compute_policy_conformance()`, which is called after all decisions are generated.
The conformance function never modifies decisions or feeds back into the pipeline.

## 3. Does the runner use proxy labels that overlap with policy expectations?

Yes, this is the most subtle leakage path.

### Proxy label definition

```
proxy_label = not is_valid
```

Where `is_valid = (classification == "VALID_TLS")`.

- **VALID_TLS** → `proxy_label = False` (clean)
- **All other classifications** → `proxy_label = True` (problematic)

### Policy expectation overlap

| Classification | Proxy Label | Expected Policy |
|---|---|---|
| VALID_TLS | False (clean) | ACCEPTABLE_TLS |
| EXPIRED_CERT | True | SECURITY_RISK |
| SELF_SIGNED_CERT | True | SECURITY_RISK |
| WRONG_HOST_CERT | True | SECURITY_RISK |
| UNTRUSTED_CHAIN | True | SECURITY_RISK |
| INCOMPLETE_CHAIN | True | SECURITY_RISK |
| DNS_FAILURE | True | AVAILABILITY_RISK |
| CONNECTION_ERROR | True | AVAILABILITY_RISK |
| TLS_HANDSHAKE_FAILURE | True | AMBIGUOUS_FAILURE |
| TIMEOUT | True | AMBIGUOUS_FAILURE |
| UNKNOWN_SSL_ERROR | True | AMBIGUOUS_FAILURE |

### Analysis

The proxy label is a binary "clean vs. problematic" signal. It correctly separates
VALID_TLS (clean) from everything else (problematic), which aligns with ACCEPTABLE_TLS
vs. non-ACCEPTABLE_TLS policy categories.

**Contamination risk**: The proxy label does NOT distinguish between security risks,
availability risks, and ambiguous failures. All non-VALID_TLS classifications are treated
identically during training. This means the causal graph learns "anything with
error status is risky" — it cannot learn that expired certs are more severe than
DNS failures. This is a known limitation, not a leakage path.

**When is this a problem?** If the causal graph learned to associate specific
features (e.g., `http_error_flag=True`) with the proxy label, then using those
same features during evaluation on the same domains would produce decisions that
"match" the proxy label. This is circular for `proxy-trained` mode but harmless for
`observation` mode.

## 4. Does the runner leak expected outcomes into SPL evidence?

**Before Phase 3.5**: No. Expected outcomes are never injected into `EvidenceArtifact`
data or metadata. The SPL pipeline sees only:
- TLS probe features (valid, expiry_days, headers)
- Transport metadata (status, latency_ms, error_type)
- Proxy labels (in training mode only)

**After Phase 3.5**: Same. The evidence generation function `_probe_result_to_evidence`
has no access to expectations. The two data paths are:

```
Probe Result → EvidenceArtifact → Pipeline → Decision
Expectations File → Conformance Scoring (post-decision)
```

## 5. Can SPL decisions be generated without expected labels?

Yes. The `--expectations` flag is optional. Without it:

1. Runner probes all domains.
2. Runner creates evidence artifacts.
3. Pipeline produces decisions.
4. Report is generated without conformance analysis.

All modes (`observation`, `proxy-trained`) work without expectations.

## 6. What data is visible to SPL at decision time?

At the moment `pipeline.process_one()` runs, the evidence context contains:

| Field | Source | Description |
|---|---|---|
| `data.valid` | Probe | Whether TLS handshake + cert verification succeeded |
| `data.expiry_days` | Probe | Days until certificate expiry |
| `data.headers.hsts` | Default `False` | Not parsed from HTTP response |
| `data.headers.csp` | Default `False` | Not parsed from HTTP response |
| `transport_meta.status` | Probe | "ok" / "timeout" / "error" |
| `transport_meta.latency_ms` | Probe | Handshake duration |
| `transport_meta.bytes_received` | Default `0` | Not measured |
| `transport_meta.error_type` | Probe | Classification string |
| `source` | Fixed `"real-tls"` | Evidence source identifier |
| `tags` | Probe | Domain name, classification, probe tag |

The `data` dict explicitly excludes:
- `label` (in observation mode)
- `label_weight`
- Any policy expectation data
- Any expected classification

## 7. How does holdout mode differ?

Holdout mode (Phase 4) introduces a separate training set (`real_tls_train_domains.txt`, 43 domains)
with external clean/dirty labels (`real_tls_train_expectations.json`). The pipeline is trained on
these domains and evaluated on a disjoint holdout set (`real_tls_holdout_domains.txt`, 18 domains).

Key differences from proxy-trained mode:
- **Training data**: 43 domains with external labels (not probe-derived proxy labels)
- **Evaluation data**: 18 unseen holdout domains (disjoint from training)
- **Labels**: External `{"label": bool, "label_weight": float}` from `_load_train_expectations()`
- **Split integrity**: Verified by tests — no domain appears in both sets

This provides a preliminary generalization estimate. The conformance on the Phase 4
specific holdout split (94.4%) is between observation (36.1%) and proxy-trained (95.1%).
However, Phase 5's expanded stratified benchmark (120 domains, 10 runs, 70.3% mean)
revealed that this result was not stable — it was specific to that particular split.
On the expanded benchmark, all non-VALID_TLS categories show 0% conformance, indicating
the causal graph cannot reliably distinguish risk sub-categories from binary clean/dirty
training labels applied to larger, more diverse datasets.

## 8. Mode Comparison

| Property | Observation | Proxy-Trained | Holdout (Phase 4) | Stratified (Phase 5) |
|----------|------------|--------------|-------------------|---------------------|
| Training data | None | Probe results with proxy labels | 43 domains with external labels | 83 domains with external labels |
| Eval data | All probe results | Same probe results | 18 holdout domains | ~37 holdout x 10 runs |
| Graph state | Cold-start | Learned from proxy labels | Learned from external labels | Learned from external labels |
| Leakage | None | Yes (documented) | None | None |
| Expectations used? | Only scoring | Only scoring | Only scoring | Only scoring |
| Use case | Baseline | Learning capacity | Preliminary generalization | Stratified generalization |
| Result | 36.1% | 95.1% | 94.4% | 70.3% mean (0% non-VALID_TLS) |

## 9. Summary

| Question | Answer |
|---|---|
| Trains on eval data? | Only in `proxy-trained` mode (documented) |
| Expectations used during decision gen? | No |
| Proxy labels overlap with policy? | Yes — but only at "clean vs. problematic" level |
| Expected outcomes leaked into evidence? | No |
| Decisions possible without expectations? | Yes |
| Leakage in observation mode? | None |
| Leakage in holdout mode? | None — train/eval sets are disjoint; external labels from separate data source |
| Generalization measured? | Yes — Phase 4 holdout: 94.4% on 18 unseen domains. Phase 5 stratified: 70.3% mean (10 runs) on 37 unseen domains per run. The Phase 4 result was not stable across larger stratified splits. |

## 10. Recommendations

1. **Use `--mode observation` for primary results** — this mode has zero leakage.
2. **Use `--mode proxy-trained` only for research** — understand what SPL can learn from
   TLS features, but do not treat results as generalizable.
3. **Use `--mode holdout` for preliminary generalization estimates** — this mode has zero
   leakage, but results should be validated across multiple splits (use Phase 5's
   stratified approach for more reliable estimates).
4. **Document all limitations** in every report.
5. **Do not compare conformance across modes** — they measure different things.
6. **The Phase 4 holdout result (94.4%) is not a reliable generalization estimate**.
   Phase 5's expanded benchmark (70.3% on 10 stratified runs) provides more robust
   preliminary evidence about SPL's actual generalization capabilities.
7. **Phase 6 — TLS Risk Policy Adapter** is available as a sidecar to demonstrate
   that deterministic classification-to-risk mapping can handle non-VALID_TLS
   categories that SPL cannot learn from binary labels. The adapter does not
   modify SPL Core, does not change SPL decision logic, and does not promote OFE.
   See `docs/TLS_RISK_POLICY_ADAPTER.md` for design and
   `reports/local_real_validation/PHASE6_BASELINE_COMPARISON.md` for corrected results.

8. **Phase 6.5 — Evaluation Integrity Audit**: The original Phase 6 "SPL-only" result
   (95.8%) used proxy-trained mode (train and evaluate on same 120 domains), not
   holdout. This was not comparable to Phase 5's stratified holdout (70.3%).
   The audit corrected this by separating all baselines and explicitly labeling
   each mode. Phase 5 (70.3%) remains the correct generalization warning.
   See `docs/PHASE5_PHASE6_METHOD_COMPARISON.md` for the full methodology comparison.

9. **Phase 7 — Decision Orchestration Policy**: A decision orchestrator layer
   (`decision_orchestrator/`) combines adapter risk evidence and SPL decision output
   into transparent final decisions via 7 deterministic rules. The orchestrator does
   not modify SPL Core, does not tune OFE, and does not claim production readiness.
   OFE remains observational only (`ofe_observed` flag set, never affects decisions).
   Safe vs unsafe mismatch classification is defined for all policy outcomes.
   See `docs/DECISION_ORCHESTRATION_POLICY.md` for the design document and
   `reports/local_real_validation/DECISION_ORCHESTRATION_REPORT.md` for benchmark results.
