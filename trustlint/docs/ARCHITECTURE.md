# SPL TLS Risk Analyzer — Architecture

## Summary

The product is a deterministic TLS risk analyzer. The data pipeline is:

```
Domain Input
  │
  ▼
[1] TLS Probe (scripts/run_local_tls_validation.py)
      • DNS resolution via socket.getaddrinfo()
      • TCP connection + TLS handshake via Python ssl
      • Certificate inspection (expiry, chain, hostname)
      • OCSP revocation check via AIA responder URLs
      • Secondary TLS 1.0 probe for deprecated protocol detection
      → ProbeResult (domain, classification, tls_info, ...)
  │
  ▼
[2] TLS Policy Adapter (tls_policy_adapter/)
      • Deterministic classification-to-risk mapping
      • 15 classification strings → risk category + severity + action hint
      • No learning, no expectations, no state
      → TLSPolicyEvidence (risk_category, severity, action_hint)
  │
  ▼
[3] Decision Orchestrator (decision_orchestrator/)
      • Rule-based decision logic (8 rules, first-match-wins)
      • 3 operating profiles: conservative, balanced, strict
      • Combines adapter evidence + optional SPL confidence
      → OrchestratorOutput (ALLOW/REVIEW/DENY, risk, reasons)
  │
  ▼
[4] Structured Output (scripts/spl_tls_analyze.py)
      • Console text (6-section structured report)
      • JSON (with schema)
      • Markdown (with executive summary)
```

### Components

| Module | Role | Dependencies |
|---|---|---|
| `scripts/run_local_tls_validation.py` | TLS probe engine | stdlib only |
| `scripts/collect_real_tls_data.py` | Batch data collection | stdlib only |
| `scripts/ocsp_checker.py` | OCSP revocation | stdlib only |
| `tls_policy_adapter/` | Risk classification mapping | stdlib only |
| `decision_orchestrator/` | ALLOW/REVIEW/DENY rules | stdlib only |
| `scripts/spl_tls_analyze.py` | CLI entry point | stdlib only |

### Decision Flow

```
classification ──→ classify_risk() ──→ TLSPolicyEvidence
                                              │
                                              ▼
                              decide(adapter_risk, severity, ...)
                              ┌─────────────────────────────────┐
                              │ 1. CRITICAL              → DENY │
                              │ 2. HIGH security risk    → REVIEW/DENY │
                              │ 3. MEDIUM availability   → REVIEW │
                              │ 4. AMBIGUOUS             → REVIEW │
                              │ 5. VALID_TLS + conf≥threshold→ALLOW│
                              │ 6. VALID_TLS + fallback  → ALLOW  │
                              │ 7. VALID_TLS + low conf  → REVIEW │
                              │ 8. Fallback              → REVIEW │
                              └─────────────────────────────────┘
                                      │
                                      ▼
                              OrchestratorOutput
```

## SPL Core — Research Archive

The `spl_v7/` directory contains the **SPL (Structured Provenance Learning)**
evidence pipeline — a causal graph learner originally designed to augment
TLS decisions with ML-based confidence scoring. It is:

- **Frozen** — no modifications since Phase 1
- **Optional** — loaded at runtime via `--spl` flag
- **Not evaluated on real data** — see `real_tls_dataset_NOT_FOUND.md`
- **Not production ready** — all ML components hold `HOLD_PENDING_REAL_DATA` status

### Components

| Module | Role |
|---|---|
| `spl_v7/schema.py` | Evidence artifact data model |
| `spl_v7/verification.py` | Source provenance and integrity |
| `spl_v7/dsl.py` | Safe feature expression DSL |
| `spl_v7/causal.py` | Online causal graph learner |
| `spl_v7/kafka_pipeline.py` | Evidence pipeline orchestration |
| `spl_v7/frontier.py` | Frontier explorer sidecar |
| `spl_v7/dashboard.py` | FastAPI + Plotly topology dashboard |

### Status

```
OFE structural signals:   HOLD_PENDING_REAL_DATA
SPL causal graph learner: HOLD_PENDING_REAL_DATA
Frontier explorer:        HOLD_PENDING_REAL_DATA
Weakness mapper:          HOLD_PENDING_REAL_DATA
```

See `experiments/status.py` and `SYNTHETIC_DATA_AUDIT.md` for details.

---

## Related Documentation

- `docs/CLI_USAGE.md` — Full CLI reference
- `docs/CLI_OUTPUT_SCHEMA.md` — JSON output schema
- `docs/OPERATING_PROFILES.md` — Profile definitions
- `docs/DECISION_ORCHESTRATION_POLICY.md` — Orchestrator design rules
- `docs/TLS_RISK_POLICY_ADAPTER.md` — Adapter mapping design
- `docs/KNOWN_LIMITATIONS.md` — All known limitations
- `EXTENSION_POINTS.md` — (archived) SPL extension interfaces
