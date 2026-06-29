# Real TLS Evidence Contract

Defines how local TLS probe classifications map into SPL evidence artifacts for decision validation.

## Overview

Each domain probe produces a structured classification. That classification is converted into an `EvidenceArtifact` that the SPL pipeline can consume. The pipeline evaluates features via the DSL, computes a probability via the causal graph, and produces a decision.

## Evidence Artifact Structure

```python
@dataclass
class EvidenceArtifact:
    source: str = "real-tls"
    type: str = "tls"
    data: dict = {
        "valid": bool,          # TLS handshake succeeded with valid cert
        "expiry_days": int,     # Days until/after certificate expiry (positive=future, negative=past)
        "headers": {            # Security header presence
            "hsts": bool,
            "csp": bool,
        },
    }
    transport_meta: EvidenceTransportMeta = {
        "status": str,          # "ok" | "timeout" | "error" | "partial"
        "latency_ms": float,
        "bytes_received": int,
        "error_type": str,      # TLS classification label
    }
```

## Category Mappings

### VALID_TLS

| Field | Value |
|-------|-------|
| `data.valid` | `True` |
| `data.expiry_days` | Certificate validity days remaining (`>0`) |
| `data.headers.hsts` | `False` (not parsed from HTTP) |
| `data.headers.csp` | `False` (not parsed from HTTP) |
| `transport_meta.status` | `"ok"` |
| `transport_meta.error_type` | `None` |
| Expected severity | Low |
| Expected confidence | Moderate (`0.3-0.7` — depends on graph state) |
| Relevance | Security-relevant (baseline) |
| Policy | `ACCEPTABLE_TLS` |

### DEPRECATED_TLS_VERSION

Added in Phase 3.5. When a TLS handshake succeeds but uses TLS 1.0 or TLS 1.1,
the evidence adapter reclassifies from `VALID_TLS` to `DEPRECATED_TLS_VERSION`.

This classification is injected at the evidence adapter layer (`_resolve_classification`
in `run_real_tls_spl_decision_validation.py`), not in the probe or SPL Core.

| Field | Value |
|-------|-------|
| `data.valid` | `True` (handshake succeeded) |
| `data.expiry_days` | Certificate validity days remaining |
| `data.headers.*` | `False` |
| `transport_meta.status` | `"ok"` |
| `transport_meta.error_type` | `"DEPRECATED_TLS_VERSION"` |
| Expected severity | Medium |
| Expected confidence | Moderate (`0.3-0.7`) |
| Relevance | Security-relevant |
| Policy | `SECURITY_RISK` |

### EXPIRED_CERT

| Field | Value |
|-------|-------|
| `data.valid` | `False` |
| `data.expiry_days` | Days since expiry (`<0`) |
| `data.headers.*` | `False` |
| `transport_meta.status` | `"error"` |
| `transport_meta.error_type` | `"EXPIRED_CERT"` |
| Expected severity | High |
| Expected confidence | Moderate (`0.4-0.7`) |
| Relevance | Security-relevant |
| Policy | `SECURITY_RISK` |

### SELF_SIGNED_CERT

| Field | Value |
|-------|-------|
| `data.valid` | `False` |
| `data.expiry_days` | `0` (unknown) |
| `data.headers.*` | `False` |
| `transport_meta.status` | `"error"` |
| `transport_meta.error_type` | `"SELF_SIGNED_CERT"` |
| Expected severity | High |
| Expected confidence | Moderate (`0.4-0.7`) |
| Relevance | Security-relevant |
| Policy | `SECURITY_RISK` |

### WRONG_HOST_CERT

| Field | Value |
|-------|-------|
| `data.valid` | `False` |
| `data.expiry_days` | Certificate validity days remaining |
| `data.headers.*` | `False` |
| `transport_meta.status` | `"error"` |
| `transport_meta.error_type` | `"WRONG_HOST_CERT"` |
| Expected severity | High |
| Expected confidence | Moderate (`0.4-0.7`) |
| Relevance | Security-relevant |
| Policy | `SECURITY_RISK` |

### UNTRUSTED_CHAIN

| Field | Value |
|-------|-------|
| `data.valid` | `False` |
| `data.expiry_days` | Certificate validity days remaining |
| `data.headers.*` | `False` |
| `transport_meta.status` | `"error"` |
| `transport_meta.error_type` | `"UNTRUSTED_CHAIN"` |
| Expected severity | High |
| Expected confidence | Moderate (`0.4-0.7`) |
| Relevance | Security-relevant |
| Policy | `SECURITY_RISK` |

### INCOMPLETE_CHAIN

| Field | Value |
|-------|-------|
| `data.valid` | `False` |
| `data.expiry_days` | Certificate validity days remaining |
| `data.headers.*` | `False` |
| `transport_meta.status` | `"error"` |
| `transport_meta.error_type` | `"INCOMPLETE_CHAIN"` |
| Expected severity | High |
| Expected confidence | Moderate (`0.4-0.7`) |
| Relevance | Security-relevant |
| Policy | `SECURITY_RISK` |

### CHAIN_TRUST_FAILURE (Ambiguous Category)

When OpenSSL reports `"unable to get local issuer certificate"`, the root cause may be:
- **INCOMPLETE_CHAIN**: Server did not send the intermediate certificate; client cannot build the chain.
- **UNTRUSTED_CHAIN**: Chain is complete but the root CA is not in the local trust store.

**Current limitation**: The local probe cannot distinguish these two cases reliably without additional probing (e.g., trying bundled intermediate stores). When the error is ambiguous, the probe classifies as `UNTRUSTED_CHAIN` and documents it.

| Field | Value |
|-------|-------|
| `data.valid` | `False` |
| `transport_meta.status` | `"error"` |
| `transport_meta.error_type` | `"UNTRUSTED_CHAIN"` (default) |
| Relevance | Security-relevant (ambiguous operational subclass) |
| Policy | `SECURITY_RISK` |

### DNS_FAILURE

| Field | Value |
|-------|-------|
| `data.valid` | `False` |
| `data.expiry_days` | `0` |
| `data.headers.*` | `False` |
| `transport_meta.status` | `"error"` |
| `transport_meta.error_type` | `"DNS_FAILURE"` |
| Expected severity | Medium |
| Expected confidence | Low (`<0.4` — no TLS data to evaluate) |
| Relevance | Availability-relevant |
| Policy | `AVAILABILITY_RISK` |

### CONNECTION_ERROR

| Field | Value |
|-------|-------|
| `data.valid` | `False` |
| `data.expiry_days` | `0` |
| `data.headers.*` | `False` |
| `transport_meta.status` | `"error"` |
| `transport_meta.error_type` | `"CONNECTION_ERROR"` |
| Expected severity | Low to medium |
| Expected confidence | Low (`<0.4`) |
| Relevance | Availability-relevant |
| Policy | `AVAILABILITY_RISK` |

### TIMEOUT

| Field | Value |
|-------|-------|
| `data.valid` | `False` |
| `data.expiry_days` | `0` |
| `data.headers.*` | `False` |
| `transport_meta.status` | `"timeout"` |
| `transport_meta.error_type` | `"TIMEOUT"` |
| Expected severity | Low |
| Expected confidence | Very low (`<0.2`) |
| Relevance | Availability-relevant |

**Policy**: `AVAILABILITY_RISK`

**Justification**: Timeout indicates the server did not respond within the probe window.
This is a network availability issue, not a TLS security concern. The root cause could be:
- Firewall blocking the connection
- Server overloaded or down
- Network congestion
- Incorrect IP routing

There is no evidence of TLS misconfiguration, expired certificates, or cryptographic weakness.
Mapping to `SECURITY_RISK` would conflate a network issue with a security concern.
Mapping to `AMBIGUOUS_FAILURE` would overstate the ambiguity — timeouts are primarily
availability issues unless accompanied by other evidence.

The probe's timeout threshold is 10 seconds. Some legitimate but slow servers may
trigger this. This is documented as a limitation.

### TLS_HANDSHAKE_FAILURE

| Field | Value |
|-------|-------|
| `data.valid` | `False` |
| `data.expiry_days` | `0` (unknown) |
| `data.headers.*` | `False` |
| `transport_meta.status` | `"error"` |
| `transport_meta.error_type` | `"TLS_HANDSHAKE_FAILURE"` |
| Expected severity | Medium |
| Expected confidence | Low to moderate (`0.3-0.6`) |
| Relevance | Ambiguous (could be security or availability) |
| Policy | `AMBIGUOUS_FAILURE` |

### UNKNOWN_SSL_ERROR

| Field | Value |
|-------|-------|
| `data.valid` | `False` |
| `data.expiry_days` | `0` |
| `data.headers.*` | `False` |
| `transport_meta.status` | `"error"` |
| `transport_meta.error_type` | `"UNKNOWN_SSL_ERROR"` |
| Expected severity | Medium |
| Expected confidence | Low (`<0.3`) |
| Relevance | Ambiguous (unrecognized failure mode) |
| Policy | `AMBIGUOUS_FAILURE` |

## DSL Feature Impact

The experiment DSL evaluates these evidence fields into features:

| DSL Feature | Source | Range | Direction |
|-------------|--------|-------|-----------|
| `tls_valid` | `data.valid` | 0/1 | Higher = safer |
| `tls_expiry_urgency` | `data.expiry_days` (normalized 0-30) | 0-1 | Higher = more urgent |
| `hsts_missing` | `data.headers.hsts` (inverted) | 0/1 | 1 = missing |
| `csp_missing` | `data.headers.csp` (inverted) | 0/1 | 1 = missing |
| `timeout_flag` | transport status == "timeout" | 0/1 | 1 = timeout |
| `partial_flag` | transport status == "partial" | 0/1 | 1 = partial |
| `http_error_flag` | transport status == "error" | 0/1 | 1 = error |
| `source_latency_pressure` | latency_ms (normalized 0-3000) | 0-1 | Higher = slower |
| `surface_tension` | Composite of above features | 0-1 | Higher = more tension |

## OFE Signals (Optional)

When OFE signals are injected, additional DSL features are available:

| DSL Feature | Source | Range | Direction |
|-------------|--------|-------|-----------|
| `ofe_contradiction_density` | Structural signal from OFE | 0-1 | Higher = more contradictory |
| `ofe_topology_drift` | Structural signal from OFE | 0-1 | Higher = more drift |
| `ofe_symbol_entropy` | Structural signal from OFE | 0-1 | Higher = more entropy |

OFE remains `HOLD_PENDING_REAL_DATA`. These features are observational only.

## Policy Mapping Summary

| Classification | Policy Label | Rationale |
|---|---|---|
| VALID_TLS | ACCEPTABLE_TLS | Standard valid TLS |
| DEPRECATED_TLS_VERSION | SECURITY_RISK | Weak protocol version |
| EXPIRED_CERT | SECURITY_RISK | Certificate no longer valid |
| SELF_SIGNED_CERT | SECURITY_RISK | No trust anchor |
| WRONG_HOST_CERT | SECURITY_RISK | Hostname mismatch |
| UNTRUSTED_CHAIN | SECURITY_RISK | Unknown CA |
| INCOMPLETE_CHAIN | SECURITY_RISK | Missing intermediate |
| DNS_FAILURE | AVAILABILITY_RISK | Domain not resolvable |
| CONNECTION_ERROR | AVAILABILITY_RISK | TCP connection failed |
| TIMEOUT | AVAILABILITY_RISK | No response within window |
| TLS_HANDSHAKE_FAILURE | AMBIGUOUS_FAILURE | Could be security or availability |
| UNKNOWN_SSL_ERROR | AMBIGUOUS_FAILURE | Unrecognized failure |

## Validation Modes

Three validation modes are supported by the runner:

### Observation Mode (`--mode observation`)
- No training. Cold-start causal graph with no edges.
- All probe results evaluated without prior knowledge.
- Provides the baseline for SPL behavior with zero leakage.
- Typical conformance: ~36%.

### Proxy-Trained Mode (`--mode proxy-trained`)
- Trains on all probe results with proxy labels (`label = classification != "VALID_TLS"`).
- Evaluates on the same probe results without labels.
- Shows whether SPL *can* learn from TLS probe features.
- **Leakage**: Training and evaluation use the same data. Not a generalization estimate.
- Typical conformance: ~95%.

### Holdout Mode (`--mode holdout`)
- Trains on a separate training set (43 domains) with external clean/dirty labels.
- Evaluates on a disjoint holdout set (18 unseen domains).
- No leakage — train/eval sets are completely separate.
- External labels provide `label` (bool) and `label_weight` (float) from `_load_train_expectations()`.
- Provides a preliminary generalization estimate between observation and proxy-trained bounds.
- Typical conformance: ~94% (Phase 4 specific split), ~70% (Phase 5 stratified benchmark).

### Mode Comparison

| Mode | Training | Eval | Leakage | Conformance | What It Measures |
|------|----------|------|---------|-------------|-------------------|
| observation | None | All domains | None | 36.1% | Cold-start baseline |
| proxy-trained | Same domains with proxy labels | Same domains | Yes (documented) | 95.1% | Upper bound — learning capacity |
| holdout (Phase 4) | 43 separate domains with external labels | 18 unseen domains | None | 94.4% | Preliminary generalization estimate |
| stratified holdout (Phase 5) | 83 domains with external labels | 37 unseen domains per run (avg) | None | 70.3% (10-run mean) | Expanded benchmark — all non-VALID_TLS categories show 0% conformance, indicating the Phase 4 result was a specific split artifact |
| adapter-only (Phase 6) | None | 120 domains | N/A (rule-based) | 95.8% | Deterministic classification-to-risk mapping. No learning, no SPL. |
| spl-observation (Phase 6.5) | None | 120 domains | None | ~36% | Cold-start baseline, matches Phase 3.5 observation. |
| spl-proxy-trained (Phase 6.5) | All 120 with proxy labels | All 120 domains | **Yes** (same dataset, documented) | 95.8% | Upper bound on learning capacity. NOT a generalization estimate. |
| spl-holdout (Phase 6.5) | 83 stratified with external labels | ~37 unseen per run | None | 70.3% | Re-validates Phase 5 finding. Only generalization estimate. |

## Limitations

1. **No HSTS/CSP confirmation**: The probe does not parse HTTP response headers; `headers.*` values are assumed defaults.
2. **No label**: Probe results do not include ground-truth labels; SPL cannot train from probe results alone.
3. **Chain ambiguity**: `INCOMPLETE_CHAIN` vs `UNTRUSTED_CHAIN` produces the same OpenSSL error in most cases.
4. **Single IP**: Only the first A record is probed; no IPv6.
5. **Ephemeral probes**: No CRL/OCSP checking.
6. **TLS version probing**: Deprecated TLS detection is **not guaranteed** by the current probe. The default SSL context may negotiate TLS 1.2+ even when the server supports TLS 1.0, preventing deprecated TLS reclassification. Some servers may reject old versions before version negotiation is visible.
7. **Risk labels are post-hoc**: The policy label is a post-hoc mapping from the SPL decision (bool) and probe classification (str). SPL's native output is decision + probability only.
8. **Holdout generalization (Phase 4)**: Limited by dataset size (18 holdout domains). Categories with only 1 sample (SELF_SIGNED_CERT, WRONG_HOST_CERT, INCOMPLETE_CHAIN) cannot be tested in holdout mode.
9. **Stratified benchmark (Phase 5)**: The expanded 120-domain benchmark revealed that the Phase 4 holdout result (94.4%) was not stable across different train/holdout splits. The Phase 5 stratified benchmark (10 runs, 70.3% mean) shows that SPL's actual generalization performance is dominated by VALID_TLS detection. All non-VALID_TLS categories show 0% conformance — the causal graph with binary clean/dirty labels cannot distinguish risk sub-categories on unseen holdout data from the expanded set.

### Phase 6 — TLS Risk Policy Adapter

A sidecar module (`tls_policy_adapter/`) maps explicit TLS probe classifications into structured risk evidence without modifying SPL Core. The adapter encodes deterministic policy rules (classification → risk category, severity, failure family, action hint) that SPL cannot learn from binary clean/dirty labels alone.

Key principles:
- **Sidecar**: The adapter sits between the probe and SPL, not inside SPL Core.
- **Deterministic**: All mappings are rule-based. No learning, no training, no thresholds.
- **OFE-independent**: OFE remains `HOLD_PENDING_REAL_DATA`.
- **Benchmark comparison**: The adapter's structured output is compared against SPL-only decisions in the benchmark report.

See `docs/TLS_RISK_POLICY_ADAPTER.md` for the full design document.
See `reports/local_real_validation/PHASE6_BASELINE_COMPARISON.md` for the corrected multi-baseline comparison.

### Phase 6.5 — Adapter Evaluation Integrity Audit

An audit of the Phase 6 benchmark methodology. Key finding: Phase 6's original "SPL-only" (95.8%) used **proxy-trained** mode (train and evaluate on all 120 domains), not holdout. This was not comparable to Phase 5's stratified holdout (70.3%).

Corrections:
- All baselines are now clearly separated: adapter-only, SPL observation, SPL holdout, SPL proxy-trained.
- Only SPL holdout measures generalization (70.3%).
- Proxy-trained mode is labeled as "upper bound, NOT generalization."
- Phase 5 (70.3%) remains the correct generalization warning.

See `docs/PHASE5_PHASE6_METHOD_COMPARISON.md` for the methodology audit.
See `docs/TLS_PROBE_LIMITATION_AUDIT.md` for analysis of the 5 probe-level mismatches.

### Phase 7 -- Decision Orchestration Policy

A decision orchestration layer (`decision_orchestrator/`) consumes both adapter output
and SPL output to produce transparent final decisions. The orchestrator applies 7
deterministic rules evaluated in priority order:

1. CRITICAL severity -> DENY (adapter guardrail)
2. MEDIUM availability risk -> REVIEW
3. HIGH severity security risk -> REVIEW
4. AMBIGUOUS/UNKNOWN -> REVIEW
5. VALID_TLS + SPL high confidence -> ALLOW
6. VALID_TLS + SPL low confidence -> REVIEW
7. Fallback -> REVIEW

OFE remains observational only (`ofe_observed` flag set, never affects decisions).
Safe vs unsafe mismatch classification distinguishes conservative REVIEW vs missed risk.

See `docs/DECISION_ORCHESTRATION_POLICY.md` for the full design document.
See `reports/local_real_validation/DECISION_ORCHESTRATION_REPORT.md` for benchmark results.
