# CLI Confidence Fallback Policy

## Problem Statement

Phase 12 dogfooding confirmed that adapter-only mode (no SPL pipeline) produces **100% REVIEW** for all non-DENY domains, including clean VALID_TLS results. Exit code 0 (ALLOW) never fires. This makes the CLI impractical for routine scanning — every domain requires manual investigation with no way to indicate "this looks clean."

The root cause: when SPL confidence is unavailable (`spl_decision=None`, `spl_confidence=0.0`), the orchestrator has no mechanism to ALLOW even the cleanest TLS result. It falls through to the VALID_TLS + low confidence rule which produces REVIEW.

## Design

### Principle

Fallback ALLOW is **not** SPL confidence. It is a deterministic, documented adapter-based local CLI policy. The orchestrator explicitly marks fallback decisions so consumers understand the confidence boundary.

### When Fallback Applies

Fallback ALLOW (balanced profile only) applies when **all** of the following are true:

1. `spl_decision` is `None` (no SPL available — adapter-only mode)
2. `classification` is `VALID_TLS`
3. `adapter_risk_category` is `ACCEPTABLE_TLS`
4. `adapter_severity` is `NONE`
5. `probe_limited` is `False` (no DNS failure, timeout, or warning)
6. Profile is `balanced`

### Per-Profile Behavior

#### conservative
- VALID_TLS without SPL confidence → **REVIEW**
- Risky TLS classifications → REVIEW or DENY based on severity
- **Purpose:** Maximum caution. No setting change needed from Phase 12.

#### balanced
- VALID_TLS without SPL confidence → **ALLOW** only if all 6 conditions above are met
- Risky TLS classifications must never become ALLOW
- **Purpose:** Practical local CLI default. Makes exit code 0 usable for clean scans.
- **Fallback ALLOW is not SPL confidence.** It signals: "the TLS adapter says this is clean, and we trust adapter-level assessment for local use."

#### strict
- VALID_TLS without SPL confidence → **REVIEW**
- Risky TLS classifications → DENY or REVIEW_HIGH based on severity
- **Purpose:** Security-first. No setting change needed from Phase 12.

### Risk Guardrails

The following classifications **never** become ALLOW through fallback, regardless of profile:

| Classification | Why |
|---|---|
| EXPIRED_CERT | Security risk — HIGH severity |
| SELF_SIGNED_CERT | Security risk — HIGH severity |
| WRONG_HOST_CERT | Security risk — CRITICAL severity |
| UNTRUSTED_CHAIN | Security risk — HIGH severity |
| INCOMPLETE_CHAIN | Security risk — HIGH severity |
| DEPRECATED_TLS_VERSION | Deprecated protocol — HIGH severity |
| DNS_FAILURE | Availability failure — MEDIUM severity |
| CONNECTION_ERROR | Availability failure — MEDIUM severity |
| TIMEOUT | Availability failure — MEDIUM severity |
| TLS_HANDSHAKE_FAILURE | Ambiguous — MEDIUM severity |
| UNKNOWN_SSL_ERROR | Ambiguous — LOW severity |

## Implementation

### Orchestrator Changes

The `decide()` function in `decision_orchestrator/policy.py` was updated:

- New parameter: `probe_limited: bool = False`
- New Rule 6 (balanced): VALID_TLS + no SPL + clean adapter + not probe-limited → ALLOW via `ADAPTER_FALLBACK`
- New output fields: `fallback_used` (bool), `confidence_source` (SPL | FALLBACK | UNAVAILABLE)
- `DecisionSource` literal type extended with `"ADAPTER_FALLBACK"`

### Rule Order (Updated)

**Balanced:**
1. CRITICAL → DENY
2. HIGH security risk → REVIEW
3. DEPRECATED_TLS → REVIEW
4. MEDIUM availability → REVIEW
5. AMBIGUOUS → REVIEW
6. VALID_TLS + SPL confidence >= 0.5 → ALLOW
7. **VALID_TLS + no SPL + clean adapter + not probe-limited → ALLOW (ADAPTER_FALLBACK)**
8. VALID_TLS + low SPL confidence → REVIEW
9. Fallback → REVIEW

### CLI Output Changes

Console output adds:
- `Fallback Used: Yes — SPL unavailable, adapter-based fallback policy applied`
- `Confidence Source: FALLBACK` in [SPL] section

JSON output adds:
- `spl.confidence_source: "FALLBACK"` 
- `final.fallback_used: true`

Markdown output adds:
- "Fallback ALLOW (adapter policy)" row in executive summary table
- "Domains Allowed via Fallback (Not SPL Confidence)" section

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Fallback ALLOW masks genuine misconfigurations | Only applies to clean VALID_TLS with no probe limitations |
| Users treat fallback ALLOW as production-ready | JSON includes `scope: "local-only"`, `production_ready: false`; all outputs carry disclaimer |
| Conservative/strict users expect ALLOW | Profiles documented explicitly; balanced is the only profile that uses fallback ALLOW |
| Probe-limited clean domains get REVIEW instead of ALLOW | Correct — limitation means we cannot safely fallback |

## Comparison with SPL Confidence

| Aspect | SPL Confidence ALLOW | Fallback ALLOW |
|---|---|---|
| Decision source | COMBINED or SPL | ADAPTER_FALLBACK |
| Confidence source | SPL | FALLBACK |
| Model required | SPL Core pipeline | No (adapter-only mode) |
| Generalization | ML-based (trained on real data) | Deterministic (rule-based) |
| Production readiness | N/A (Phase 9+ constraints) | Explicitly not production ready |
| Scope | Requires SPL integration | Local CLI only |

## Validation

- All 12 non-VALID_TLS classifications continue to produce REVIEW or DENY (never ALLOW)
- Balanced profile with clean VALID_TLS produces ALLOW via fallback
- Conservative and strict profiles with clean VALID_TLS still produce REVIEW
- Probe-limited clean domains (e.g. DNS failure) still produce REVIEW
- `confidence_source` and `fallback_used` are present in all output formats
- Exit code 0 fires for all-clean batches
