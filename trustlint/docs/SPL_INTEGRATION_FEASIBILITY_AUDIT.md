# SPL Integration Feasibility Audit

**Phase 18.6**

**Date:** 2026-06-03
**Project:** SPL v7.1 — spl-tls-analyze v0.1.0b0
**Status:** Audit only — no SPL Core changes, no feature additions, no policy changes.

---

## Executive Summary

SPL currently has **zero material participation** in CLI decisions (Phase 18.5 confirmed 0% SPL involvement, 100% adapter-only). This audit determines whether this was intentional, what SPL would require to participate, and whether participation would improve decision quality.

**Primary finding:** SPL was never connected to the CLI — this was an architectural choice, not a regression. The Phase 6.5 audit revealed SPL's best generalization estimate is **70.3%** (stratified holdout), while the adapter alone achieves **95.8%**. Reconnecting SPL would reduce decision quality, increase complexity, and require features the current TLS probe does not produce.

**Recommendation: Keep SPL disconnected (Scenario A).** The adapter already outperforms SPL on the task the CLI performs. SPL's value lies in future scenarios involving multi-source evidence, not single-source TLS probing.

---

## Stage 1 — Historical Trace

### Timeline

| Phase | What Happened | SPL State |
|-------|--------------|-----------|
| 1-4 | SPL Core built: causal graph, DSL, pipeline, schema, verification, dashboard | Active in pipeline, tested with demo/toy data |
| 5 | Stratified holdout benchmark: **70.3%** generalization. Revealed SPL cannot distinguish non-VALID_TLS sub-categories from binary labels alone | Active in experiment scripts |
| 6 | **TLS Policy Adapter** built — deterministic rule-based risk mapping. Adapter-only achieves **95.8%** conformance | Adapter is a *sidecar*, not a replacement for SPL |
| 6.5 | Audit: Phase 6's "SPL-only 95.8%" was **proxy-trained** (train+eval on same data). Corrected: 70.3% is the only generalization estimate. Adapter-only 95.8% is the relevant comparison for CLI decisions | SPL's generalization capacity confirmed at 70.3% |
| 7 | **Decision Orchestrator** built — composes adapter + SPL outputs. Designed to consume both. Orchestrator rules explicitly handle `spl_decision=None` | Orchestrator is SPL-aware but works without SPL |
| 8 | **Operating profiles** (conservative/balanced/strict) + **fallback ALLOW** concept designed but not yet implemented | SPL has a defined slot in the orchestrator, but CLI doesn't fill it |
| **9** | **CLI productization** (`spl_tls_analyze.py`). Script hardcodes `spl_decision=None`, `spl_confidence=0.0`. This is the **first phase where SPL becomes disconnected** from the decision path | **SPL disconnected. Never connected in CLI.** |
| 10-11 | Frontier Explorer, Weakness Mapper (sidecars) | SPL remains disconnected from CLI |
| 12 | Dogfood: without ADAPTER_FALLBACK, ALLOW=0, REVIEW=30, DENY=1. CLI impractical | SPL still disconnected |
| 13 | **ADAPTER_FALLBACK rule added** — balanced profile can ALLOW clean VALID_TLS without SPL. Fixes the 0-ALLOW problem without reconnecting SPL | Adapter provides its own fallback path |
| 14 | OFE experiments (simulated data only — HOLD_PENDING_REAL_DATA) | SPL used in experiments, not CLI |
| 15-17 | Replication campaigns, promotion readiness, real-world audit | SPL disconnected from CLI |
| 18.5 | Decision Path Audit: confirmed **0% SPL, 100% adapter**, 93% fallback | **Audit confirms zero SPL contribution** |

### Key Historical Insight

SPL was **never connected** to the CLI. It was not removed, broken, or disabled. The CLI (`spl_tls_analyze.py`) was written as an adapter-only tool from Phase 9 onward. The `spl_decision=None` hardcoding is the original design, not a regression.

The architectural decision was driven by Phase 5/6 findings: the adapter (95.8%) outperforms SPL holdout (70.3%) on the TLS risk classification task. Connecting SPL would make decisions *worse*, not better.

---

## Stage 2 — Code Path Analysis

### SPL-Related Code Paths

There are **four** distinct SPL code paths in the project:

#### Path 1: CLI → Orchestrator (active, spl_decision=None)
```
spl_tls_analyze.py → probe_domain() → classify_risk() → decide(..., spl_decision=None)
```
- **Status:** ACTIVE, always hit
- **SPL involvement:** Zero — `spl_decision=None` hardcoded at `spl_tls_analyze.py:145`
- **Reachability:** 100% of calls
- **Dead SPL paths in orchestrator:** Rule 5 (SPL confidence ≥ threshold → ALLOW) and Rule 7b (SPL low confidence → REVIEW) are **dead code** — they require `spl_decision is not None`

#### Path 2: CLI → SPL Pipeline (never invoked)
```
create EvidenceArtifact → ingest() → verify() → compile() → learn() → predict()
```
- **Status:** NEVER INVOKED from CLI
- **Location:** `spl_v7/kafka_pipeline.py`, `spl_v7/causal.py`
- **Only invoked from:** experiment scripts (`run_ofe_experiment.py`, `run_stratified_benchmark.py`, `run_replication.py`), tests
- **Reachability from CLI:** Zero — no import or call chain connects CLI to pipeline

#### Path 3: CLI → OFE → SPL (observational only, held)
```
FrontierExplorer → wrap_structural_signals() → EvidenceArtifact → pipeline.ingest()
```
- **Status:** HELD — OFE status is `HOLD_PENDING_REAL_DATA`
- **OFE signals are never produced or ingested**
- **Reachability from CLI:** Zero — OFE is not invoked in CLI path

#### Path 4: CLI → Adapter → SPL enrichment (partial, TLS artifact path)
```
evidence_adapter.enrich_evidence_artifact() → merges TLS evidence into EvidenceArtifact
```
- **Status:** EXISTS in code, but **not called from CLI**
- **Location:** `tls_policy_adapter/evidence_adapter.py`
- **Reachability from CLI:** Zero — the enrichment functions are only called in benchmark scripts

### Reachability Summary

| Path | Reachable from CLI? | SPL Active? | SPL Impact on Decisions |
|------|:-------------------:|:-----------:|:-----------------------:|
| Path 1 (orchestrator, None) | ✅ Always | ❌ | None |
| Path 2 (full pipeline) | ❌ Never invoked | ❌ | None |
| Path 3 (OFE) | ❌ Held | ❌ | None |
| Path 4 (enrichment) | ❌ Not called | ❌ | None |

### Conditions Required for SPL Participation

For SPL to produce a `spl_decision` and `spl_confidence` that the orchestrator can use:

1. **Evidence construction**: The CLI must construct an `EvidenceArtifact` from TLS probe results
2. **DSL compilation**: A `FeatureDSLProgram` must be loaded and compiled
3. **Pipeline instantiation**: An `EvidencePipeline` must be created with the DSL, learner, and verifier
4. **Evidence ingestion**: The artifact must be ingested via `pipeline.ingest()`
5. **Pipeline processing**: `pipeline.process_one()` must be called to produce a decision
6. **Result extraction**: The pipeline result's `spl_decision` and `spl_confidence` must be extracted and passed to the orchestrator's `decide()`
7. **State persistence**: The pipeline must be long-lived (SPL learns online; a fresh pipeline per domain learns nothing)

All seven conditions are **currently unmet** in the CLI path.

---

## Stage 3 — SPL Capability Audit

### What SPL Expects (EvidenceArtifact)

```python
@dataclass
class EvidenceArtifact:
    source: str      # "real-tls", "collector-a", etc.
    type: str        # "tls"
    data: dict = {
        "valid": bool,          # REQUIRED: TLS handshake succeeded
        "expiry_days": int,     # REQUIRED: days to/from expiry
        "headers.hsts": bool,   # REQUIRED: HSTS header present
        "headers.csp": bool,    # REQUIRED: CSP header present
        "label": bool,          # REQUIRED for training: known good/bad
        "label_weight": float,  # OPTIONAL: confidence in label
    }
    transport_meta: EvidenceTransportMeta = {
        "status": str,          # "ok" | "timeout" | "error" | "partial"
        "latency_ms": float,
        "bytes_received": int,
        "error_type": str,
    }
```

### What SPL Produces

| Output | Type | Description |
|--------|------|-------------|
| `predict()` | `bool` | Learned decision (True = DENY, False = ALLOW) |
| `predict_proba()` | `float` | Confidence score (0.0–1.0) |
| `snapshot()` | `dict` | Full causal graph state including constraint scores |

### What the Current TLS Pipeline Generates

| Field | Status | SPL-Compatible? |
|-------|--------|:--------------:|
| `data.valid` | ✅ Implicit (classification == "VALID_TLS") | Yes, can be derived |
| `data.expiry_days` | ✅ Present in probe result | Yes |
| `data.headers.hsts` | ❌ **Not parsed** (no HTTP response parsing) | No — assumed False |
| `data.headers.csp` | ❌ **Not parsed** (no HTTP response parsing) | No — assumed False |
| `data.label` | ❌ **Not available** (probe is observational) | No — requires external ground truth |
| `data.label_weight` | ❌ Not available | No |
| `transport_meta.status` | ✅ Partially (error categories map to ok/error) | Partial |
| `transport_meta.latency_ms` | ✅ Present | Yes |
| `transport_meta.error_type` | ✅ Present | Yes |

### Gap Analysis

| Missing Input | Severity | Workaround? |
|---------------|:--------:|-------------|
| `data.valid` | Low | Can be derived from classification string |
| `data.headers.hsts` | **High** | Not available without HTTP response parsing |
| `data.headers.csp` | **High** | Not available without HTTP response parsing |
| `data.label` | **Critical** | No ground truth labels from probes. External dataset required |
| `data.label_weight` | Medium | Can default to 1.0 but adds noise |

### Can SPL Operate Using Current TLS Evidence Alone?

**No.** Two critical gaps prevent SPL from operating on current TLS evidence:

1. **No labels**: The probe produces observational results only. SPL's `OnlineCausalGraphLearner.update()` requires a `target` (bool label) for supervised learning. Without labels, the graph never learns — `predict()` returns the bias (effectively random at init).

2. **No HTTP header parsing**: The DSL feature program (`REAL_TLS_EVIDENCE_CONTRACT.md`) defines features that depend on `data.headers.hsts` and `data.headers.csp`. Both are hardcoded to `False` because the probe does not parse HTTP responses. This reduces the feature space to essentially one feature: `data.valid` (derived binary) + `data.expiry_days` (numeric). The Phase 6.5 finding that SPL cannot distinguish risk sub-categories from binary labels alone is largely explained by this feature poverty.

---

## Stage 4 — Integration Feasibility

### Scenario A: SPL Remains Disconnected

| Dimension | Assessment |
|-----------|------------|
| **Complexity** | None — current state |
| **Architectural risk** | None |
| **Expected benefit** | Maintains current behavior. 93% ALLOW, 6% REVIEW, 1% DENY. Exit codes work. |
| **Required changes** | None |
| **Decision quality** | Adapter-only: 95.8% conformance |
| **Missing capability** | No learned confidence scoring, no anomaly detection, no multi-source evidence fusion |

### Scenario B: SPL as Confidence Layer

SPL provides `predict_proba()` only (confidence score 0-1). The orchestrator uses it in existing Rules 5 and 7. Adapter still makes the primary decision.

| Dimension | Assessment |
|-----------|------------|
| **Complexity** | **Medium-High** |
| | - Construct `EvidenceArtifact` from TLS probe results |
| | - Load DSL program, instantiate pipeline, maintain long-lived state |
| | - Must pre-train SPL on labeled data (external dataset required) |
| | - Confidence from a cold-start graph is meaningless (~0.5 for all inputs) |
| **Architectural risk** | Low (orchestrator already handles SPL input, pipeline is sidecar) |
| **Expected benefit** | **Low to negative** |
| | - Adapter already achieves 95.8% |
| | - SPL holdout achieves 70.3% — adding SPL confidence would reduce accuracy |
| | - Without HSTS/CSP features, SPL's confidence is based on 1-2 features only |
| | - SPL confidence from a probe-only feature set adds no signal the adapter doesn't already encode |
| **Required changes** | |
| | - Create `EvidenceArtifact` construction logic in CLI |
| | - Add HSTS/CSP response parsing to TLS probe (or accept empty defaults) |
| | - Obtain labeled TLS dataset for training |
| | - Implement pipeline lifecycle management in CLI |
| | - Wire pipeline output → orchestrator input |
| | - Add tests for the integrated path |

### Scenario C: SPL as Reasoning Layer

SPL provides `predict()` (learned decision). The orchestrator uses `spl_decision` as a direct input alongside adapter.

| Dimension | Assessment |
|-----------|------------|
| **Complexity** | **High** |
| | - All changes from Scenario B |
| | - Plus: must handle SPL/adapter disagreement (conflict resolution) |
| | - Plus: orchestrator rules assume SPL *augments* adapter, not replaces it |
| **Architectural risk** | Medium |
| | - SPL decision may contradict adapter (SPL: ALLOW, Adapter: DENY for expired cert) |
| | - Current orchestrator rules prioritize adapter severity over SPL decision |
| | - SPL's 70.3% generalization would override adapter's 95.8% in some paths |
| **Expected benefit** | **Negative** |
| | - SPL alone achieves 70.3% vs adapter 95.8% |
| | - Combining a weaker model with a stronger one via simple rule priority degrades overall |
| | - No feature currently available to SPL would improve adapter decisions |
| **Required changes** | All changes from Scenario B, plus conflict resolution strategy |

### Feasibility Comparison

| Aspect | Scenario A | Scenario B | Scenario C |
|--------|:----------:|:----------:|:----------:|
| Effort | None | 3-5 weeks | 4-6 weeks |
| Benefit | Current baseline | Likely negative | Likely negative |
| Risk | None | Low | Medium |
| Data required | None | Labeled TLS dataset | Labeled TLS dataset |
| Feature work | None | HSTS/CSP parsing | HSTS/CSP parsing |
| Test burden | None | +3-5 test files | +4-6 test files |

---

## Stage 5 — Cost vs Value Analysis

### Engineering Effort (Estimates)

| Task | Hours | Dependencies |
|------|:-----:|-------------|
| EvidenceArtifact construction in CLI | 8-12 | — |
| DSL program definition for TLS evidence | 4-8 | — |
| Pipeline lifecycle management (init, state, cleanup) | 16-24 | — |
| HSTS/CSP header parsing in TLS probe | 8-16 | HTTP client addition |
| Labeled dataset acquisition | 40-120 | External dataset provider |
| SPL pre-training pipeline | 16-24 | Labeled dataset |
| Integration wiring (pipeline → orchestrator) | 8-12 | All above |
| Conflict resolution design (Scenario C) | 8-12 | — |
| Testing (unit + integration + regression) | 24-40 | All above |
| Documentation | 8-12 | All above |
| **Total Scenario B** | **~140-260 hours** | |
| **Total Scenario C** | **~180-320 hours** | |

### Maintenance Burden

| Aspect | Annual cost |
|--------|:-----------:|
| Pipeline state management (memory, serialization) | 20-40 hours |
| Graph retraining / model refresh | 10-20 hours |
| Feature DSL maintenance | 5-10 hours |
| SPL Core constraint gate monitoring | 10-20 hours |
| **Total recurring** | **45-90 hours/year** |

### Testing Burden

| Area | Tests |
|------|:-----:|
| Evidence artifact construction | 10-15 |
| Pipeline integration | 15-20 |
| SPL/adapter agreement | 20-30 |
| Regression (guarantee no change to existing output) | 20-30 |
| **Total new tests** | **65-95** |

### Expected Practical Gain

The critical question: **Would reintroducing SPL improve real-world decision quality?**

**Answer: No, based on the following evidence:**

1. **Adapter-only conformance: 95.8%** (Phase 6) — The deterministic risk mapping correctly handles 12 classification categories × 7 risk categories × 5 severity levels. This is deterministic, zero-maintenance, and interpretable.

2. **SPL holdout conformance: 70.3%** (Phase 5 stratified benchmark, 10-run mean) — SPL's best generalization estimate. All non-VALID_TLS categories showed **0% conformance** in holdout mode — the causal graph with binary clean/dirty labels cannot distinguish risk sub-categories on unseen data.

3. **SPL cannot learn from current probe features alone** — Without HSTS/CSP headers and without ground-truth labels, SPL operates on a degenerate feature set (`data.valid` binary + `data.expiry_days` numeric). The adapter achieves 95.8% with only the classification string.

4. **The adapter already encodes all knowledge SPL would learn** — The adapter's `RISK_MAP` is the compressed representation of what SPL would take thousands of labeled examples to learn. An expired cert → HIGH security risk is a deterministic fact, not a statistical pattern.

5. **The real-world audit confirmed the adapter handles 100 production domains correctly** — The only anomalous results (cnn.com, walmart.com UNTRUSTED_CHAIN) are probe-side limitations (missing CA certificates in local trust store), not errors in either the adapter or SPL.

### When Would SPL Add Value?

SPL would add value in scenarios the adapter cannot handle deterministically:

- **Multi-source evidence fusion** — Combining TLS probe data with DNS records, HTTP headers, certificate transparency logs, and background intelligence feeds
- **Anomaly detection** — Identifying certificates that are technically valid but unusual for a given domain (e.g., unexpected CA, unusual key parameters)
- **Temporal pattern analysis** — Detecting configuration drift, approaching expiry, or sudden changes in certificate properties
- **Cross-domain correlation** — Identifying clusters of domains sharing anomalous certificate patterns (potential supply-chain compromise)

None of these scenarios are in scope for the current CLI tool.

---

## Stage 6 — Final Recommendation

### Option A: Keep SPL Disconnected

**Chosen.**

### Rationale

1. **SPL was intentionally never connected** — Phase 9's design chose adapter-only mode because Phase 5/6 data showed the adapter outperforms SPL on the TLS classification task.

2. **Reconnecting SPL would reduce decision quality** — Adapter achieves 95.8%, SPL holdout achieves 70.3%. The orchestrator rules that use `spl_decision` (Rules 5, 7b) would produce worse outcomes if SPL were connected.

3. **SPL cannot operate on current TLS evidence** — Two critical gaps (no labels, no HTTP header features) mean SPL would need an external labeled dataset and probe improvements before it could produce meaningful output.

4. **The ADAPTER_FALLBACK mechanism works** — Phase 18.5 confirmed the fallback correctly handles 93% of clean domains (ALLOW) while maintaining guardrails for all 11 non-VALID_TLS classifications (never ALLOW via fallback).

5. **Reconnection cost outweighs benefit** — 3-6 weeks engineering effort for a feature that would reduce decision quality is not justified.

### When to Revisit

Reconsider SPL integration if:

- A **multi-source evidence pipeline** is added (TLS + DNS + HTTP + CT logs)
- A **labeled TLS dataset** (5000+ rows, ≥10% positive labels, all 12 required fields per contract) becomes available
- The probe gains **HSTS/CSP header parsing** and **CRL/OCSP checking**
- A use case arises requiring **anomaly detection** beyond deterministic classification mapping

### Option Disposition

| Option | Disposition | Reason |
|--------|:-----------:|--------|
| **A. Keep SPL disconnected** | ✅ **Selected** | Adapter outperforms SPL on current task |
| B. Confidence layer | ❌ Rejected | Would reduce accuracy, high effort |
| C. Reasoning layer | ❌ Rejected | Would reduce accuracy, highest risk |
| D. Full participant | ❌ Rejected | Same objections, compounded |
| E. Insufficient evidence | ❌ Rejected | Phase 5/6.5/18.5 provide sufficient evidence |

---

## Summary of Findings

| Question | Answer |
|----------|--------|
| Why is SPL inactive? | Intentionally never connected to CLI (Phase 9 design decision) |
| Was this intentional? | Yes — driven by Phase 5/6 evidence that adapter outperforms SPL |
| What would SPL require to participate? | Labeled dataset, HSTS/CSP parsing, pipeline lifecycle mgmt, DSL definition |
| Architectural cost of reintroduction? | 3-6 weeks engineering, 65-95 new tests, 45-90 hours/year maintenance |
| Expected value of reintroduction? | Negative — would reduce decision quality from 95.8% to somewhere between 70.3-95.8% |
| Should SPL be reconnected? | **No** — not until multi-source evidence or anomaly detection use cases emerge |
