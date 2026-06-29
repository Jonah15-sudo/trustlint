# Phase 5 vs Phase 6 Methodology Comparison

## The Core Question

Phase 6 reported SPL-only conformance at 95.8%. Phase 5 reported 70.3%. Both use the same 120-domain benchmark. Why the difference?

**Answer**: They measure different things. Phase 5 measured **holdout generalization** (train on 83, evaluate on 37 unseen). Phase 6 measured **proxy-trained conformance** (train and evaluate on all 120). These are fundamentally different modes with different leakage properties.

## Methodology Comparison Table

| Aspect | Phase 5 | Phase 6 (as shipped) |
|---|---|---|
| **Script** | `run_stratified_benchmark.py` | `run_tls_policy_adapter_benchmark.py` |
| **Dataset** | 120 benchmark domains | Same 120 benchmark domains |
| **Training mode** | Holdout (10 stratified splits) | Proxy-trained (full dataset) |
| **Training function** | `_train_pipeline_with_labels()` — external clean/dirty labels | `_train_pipeline()` — proxy labels from probe classification |
| **Training set** | ~83 domains per split | All 120 domains |
| **Evaluation set** | ~37 unseen holdout domains per split | Same 120 domains (trained and evaluated on same data) |
| **Label source** | External expectations: `label = (policy != "ACCEPTABLE_TLS")` | Proxy: `label = (classification != "VALID_TLS")` |
| **Labels before decisions?** | Only during training (separate train/eval) | Yes — labels are set during training, then same domains are evaluated |
| **Generalization?** | Yes — train/eval sets are disjoint | No — train/eval are the same set |
| **Leakage** | None (disjoint train/eval) | Yes — proxy labels inform the graph on the same domains later evaluated |
| **What it measures** | Can SPL generalize to unseen TLS domains? | Can SPL learn from TLS probe features on this dataset? |
| **Conformance** | 70.3% mean (10 runs) | 95.8% |
| **Non-VALID_TLS handling** | 0% — graph fails on unseen non-VALID_TLS | ~95% — graph correctly classifies non-VALID_TLS it was trained on |

## Why 95.8% Is Not Comparable to 70.3%

The Phase 6 SPL-only "comparison" column was **proxy-trained** — the same methodology that produced 95.1% in Phase 3.5. The adapter runner never performed a holdout evaluation. The full-dataset proxy-trained mode:

- **Trains** the causal graph on every domain's features with proxy labels
- **Evaluates** on the same domains without labels
- The graph has already seen every domain's feature patterns during training

This is a **learning capacity upper bound**, not a generalization estimate. The 70.3% from Phase 5's stratified holdout is the only generalization estimate. The two numbers should never be directly compared.

## What the Adapter Benchmark Should Have Reported

An honest Phase 6 report should have separated:

1. **Adapter-only** (95.8%) — deterministic classification mapping, no SPL
2. **SPL observation** (cold-start, no training) — ~36% (from Phase 3.5)
3. **SPL holdout** (train on 83, evaluate on 37) — ~70% (from Phase 5)
4. **SPL proxy-trained** (full dataset) — ~96% (what was reported as "SPL-only")

The adapter-only result (95.8%) is the relevant comparison because the adapter is designed to replace the *mapping function*, not SPL's learning. Comparing proxy-trained SPL against the adapter conflates two different tasks: learning from features vs. mapping classifications.

## Key Takeaway

**Phase 5 (70.3%) remains the correct generalization warning.** Phase 6's 95.8% is not a contradiction — it is a different mode. The adapter benchmark must clearly label its SPL mode as "proxy-trained (upper bound)" to avoid misleading comparisons.

## Corrected Phase 6 Report Structure

All subsequent Phase 6 reports must:

1. Label SPL proxy-trained results as "proxy-trained (not generalization)"
2. Include SPL observation and SPL holdout baselines for fair comparison
3. Compare adapter-only (deterministic mapping) against all SPL modes
4. Note that the adapter is a replacement for the *mapping function*, not SPL learning
5. Explicitly state: "The adapter does not prove SPL generalization. Phase 5 stratified holdout (70.3%) remains the best generalization estimate available."
