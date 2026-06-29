# Decision Orchestration Policy

## Purpose

A sidecar orchestrator that combines TLS Risk Policy Adapter output and SPL decision output into a transparent final decision without modifying SPL Core.

## Why Orchestration?

The Phase 5/6.5 findings show that no single layer fully handles TLS risk:

| Layer | Conformance | Limitation |
|---|---|---|
| **Adapter-only** | 95.8% | Deterministic mapping of probe classifications only |
| **SPL observation** | 25.8% | No training — cold-start graph cannot classify risk |
| **SPL holdout** | 70.3% | Cannot distinguish non-VALID_TLS sub-categories from binary labels |
| **SPL proxy-trained** | 95.8% | Upper bound — not a generalization estimate |

Each layer has complementary strengths:
- **Adapter**: Knows deterministic TLS policy facts (expired cert → high risk).
- **SPL**: Provides learned reasoning from evidence features, confidence scoring.
- **Neither alone**: Is sufficient for all cases.

The orchestrator composes these layers transparently.

## Architecture

```
TLS Probe → Adapter → Risk Evidence → SPL → SPL Decision + Confidence
                                   ↓
                   Decision Orchestrator
                                   ↓
                       Final Decision (ALLOW/REVIEW/DENY)
```

The orchestrator is a **sidecar**. It does not:
- Replace SPL
- Modify SPL Core
- Promote OFE
- Inject data back into SPL

It reads adapter and SPL outputs and applies documented policy rules.

## Orchestrator Input

| Field | Source | Description |
|---|---|---|
| `adapter_risk_category` | Adapter | e.g. SECURITY_RISK, AVAILABILITY_RISK |
| `adapter_severity` | Adapter | NONE, LOW, MEDIUM, HIGH, CRITICAL |
| `adapter_action_hint` | Adapter | e.g. DENY, REVIEW, RENEW_OR_DENY |
| `spl_decision` | SPL | True = DENY (decision triggered), False = ALLOW |
| `spl_confidence` | SPL | Causal probability (0.0–1.0) |
| `spl_policy_label` | SPL | ACCEPTABLE_TLS, SECURITY_RISK, etc. |
| `weakness_flags` | SPL (optional) | Any weakness flags from pipeline |
| `ofe_signals` | OFE (observational) | Observational only — do not affect decisions |

## Orchestrator Output

```python
{
    "final_decision": "ALLOW | REVIEW | DENY",
    "final_risk": "NONE | LOW | MEDIUM | HIGH | CRITICAL",
    "primary_reason": "Human-readable explanation",
    "supporting_reasons": [],
    "source": "ADAPTER | SPL | COMBINED | CONFIDENCE",
    "spl_decision": True/False,
    "spl_confidence": 0.0,
    "adapter_risk": "...",
    "adapter_severity": "...",
    "ofe_observed": True/False
}
```

## Operating Profiles

Phase 8 introduces configurable operating profiles that control decision thresholds
and security risk handling. Three profiles are defined:

| Profile | Allow Threshold | HIGH Security Action | Behavior |
|---------|:-:|:-:|---|
| **conservative** | 0.7 | REVIEW | Reviews uncertain TLS, strict confidence needed for ALLOW |
| **balanced** | 0.5 | REVIEW | Practical default, lower ALLOW threshold |
| **strict** | 0.7 | DENY | Denies HIGH security risks, strict confidence for ALLOW |

### Profile Configuration

```python
_ALLOW_THRESHOLDS = {
    "conservative": 0.7,
    "balanced": 0.5,
    "strict": 0.7,
}
_HIGH_SECURITY_ACTION = {
    "conservative": "REVIEW",
    "balanced": "REVIEW",
    "strict": "DENY",
}
```

- **Allow threshold**: Minimum SPL confidence required for VALID_TLS to produce ALLOW.
- **HIGH security action**: What to do when adapter reports HIGH severity security risk.
- **All profiles**: CRITICAL → DENY, MEDIUM availability → REVIEW, AMBIGUOUS → REVIEW.

The profile is passed to `decide()` as a string parameter. Invalid profiles raise
`ValueError`. The default profile is `"balanced"` for backward compatibility.

### Profile Comparison (Phase 8)

| Profile | Adapter-only | SPL Obs | SPL Holdout | SPL Proxy |
|---------|:-:|:-:|:-:|:-:|
| **conservative** | 20.0% / 28.3% | 20.0% / 28.3% | 21.6% / 29.7% | 20.0% / 28.3% |
| **balanced** | 20.0% / 28.3% | **90.0% / 96.7%** | 21.6% / 29.7% | 20.0% / 28.3% |
| **strict** | 25.8% / 28.3% | 25.8% / 28.3% | 26.8% / 29.7% | 25.8% / 28.3% |

Format: Exact% / Safety-Adjusted%. All profiles show 0 under-blocking across
all baselines. Safety-adjusted conformance is identical across profiles because
all three produce REVIEW for non-VALID_TLS cases in adapter-only mode.

Balanced has the highest SPL observation conformance (90.0%) because the 0.5
threshold allows 86 VALID_TLS domains to produce ALLOW. Strict shows slightly
higher exact conformance (+5.8pp) because it produces DENY for 7 HIGH security
risks instead of REVIEW (converting safe mismatches to exact matches).

**Recommended default: balanced** — it maximizes exact conformance on SPL
observation without increasing under-blocking (0 for all profiles).

### OFE Across Profiles

OFE signals are observational only in all profiles. The `ofe_observed` flag is
set to True when signals are provided, but the flag has no impact on the final
decision in any profile.

---

## Policy Rules

### Rule 1: Adapter CRITICAL → DENY

If adapter severity is CRITICAL, the orchestrator produces DENY regardless of SPL.

| Input | Output |
|---|---|
| WRONG_HOST_CERT (CRITICAL) | DENY |
| SPL says ALLOW with high confidence | Still DENY — adapter overrides |

This is a **policy guardrail**. CRITICAL classifications (only WRONG_HOST_CERT in the current schema) indicate active MITM or host mismatch. SPL may learn to generalize this, but the adapter provides a deterministic safety net.

### Rule 2: Adapter MEDIUM availability → REVIEW

| Input | Output |
|---|---|
| DNS_FAILURE (MEDIUM, AVAILABILITY_RISK) | REVIEW |
| TIMEOUT (MEDIUM, AVAILABILITY_RISK) | REVIEW |
| CONNECTION_ERROR (MEDIUM, AVAILABILITY_RISK) | REVIEW |

Availability risks are not automatic denies. The orchestrator flags them for REVIEW because the domain may be temporarily unreachable.

### Rule 3 (balanced only): Adapter fallback — clean VALID_TLS without SPL → ALLOW

If SPL confidence is unavailable (adapter-only mode) and ALL of the following
conditions are met under the **balanced** profile:
- classification is VALID_TLS
- adapter risk category is ACCEPTABLE_TLS
- adapter severity is NONE
- probe is NOT limited (no DNS failure, timeout, warning)

the orchestrator produces ALLOW via ADAPTER_FALLBACK.

| Input | Output |
|---|---|
| VALID_TLS + no SPL + ACCEPTABLE_TLS/NONE + not probe-limited (balanced) | ALLOW (ADAPTER_FALLBACK) |
| Same + conservative/strict profile | REVIEW (no fallback) |
| Same + probe-limited | REVIEW (cannot safely fallback) |

Fallback ALLOW is a **deterministic adapter-based policy**, not SPL confidence.
The decision_source is "ADAPTER_FALLBACK" and fallback_used is true in the output.

See `docs/CLI_CONFIDENCE_FALLBACK_POLICY.md` for the full design document.

### Rule 4: SPL high confidence VALID_TLS → ALLOW

If both adapter and SPL agree on ACCEPTABLE_TLS and SPL confidence is high (≥ 0.5), the orchestrator produces ALLOW.

| Input | Output |
|---|---|
| VALID_TLS + SPL allow + confidence ≥ 0.5 | ALLOW |

### Rule 5: SPL low confidence VALID_TLS → REVIEW

If adapter says ACCEPTABLE_TLS but SPL confidence is low (< 0.5), the orchestrator produces REVIEW instead of ALLOW.

| Input | Output |
|---|---|
| VALID_TLS + SPL allow + confidence 0.3 | REVIEW |

This prevents the orchestrator from silently allowing domains that SPL is uncertain about.

### Rule 6: Adapter HIGH severity security risk → DENY or REVIEW_HIGH

| Input | Output |
|---|---|
| EXPIRED_CERT (HIGH) | REVIEW_HIGH (maps to REVIEW) |
| SELF_SIGNED_CERT (HIGH) | REVIEW_HIGH (maps to REVIEW) |
| UNTRUSTED_CHAIN (HIGH) | REVIEW_HIGH (maps to REVIEW) |
| INCOMPLETE_CHAIN (HIGH) | REVIEW_HIGH (maps to REVIEW) |
| DEPRECATED_TLS_VERSION (HIGH) | REVIEW_HIGH (maps to REVIEW) |

Note: The orchestrator defaults to REVIEW rather than DENY for HIGH severity. This is conservative — it flags the issue for human review rather than automatically denying. The specific policy can be tightened (e.g., EXPIRED_CERT → DENY) by configuration.

### Rule 7: Adapter AMBIGUOUS → REVIEW

| Input | Output |
|---|---|
| TLS_HANDSHAKE_FAILURE (MEDIUM, AMBIGUOUS) | REVIEW |
| UNKNOWN_SSL_ERROR (LOW, UNKNOWN) | REVIEW |

Ambiguous failures cannot be classified as security or availability — they require investigation.

### Rule 8: Default fallback

If no rule matches (should not happen for valid classifications), default to REVIEW.

## OFE Handling

OFE signals are included in the orchestrator output as metadata only (`ofe_observed: True/False`). They do not affect the final decision. The orchestrator is designed so that when/if OFE is promoted in a future phase, the orchestration policy can be updated to consider OFE signals without changing the orchestrator's core logic — but this requires an explicit evidence-backed promotion decision.

**Current status**: `ofe_observed` is always `False`. OFE remains `HOLD_PENDING_REAL_DATA`.

## Safe vs Unsafe Mismatches

The orchestrator distinguishes:

| Category | Definition | Example |
|---|---|---|
| **Exact match** | Final decision matches expected policy exactly | Expected DENY, got DENY |
| **Safe mismatch** | Final decision is stricter than expected but not unsafe | Expected SECURITY_RISK, got REVIEW |
| **Unsafe mismatch** | Final decision is more permissive than expected risk | Expected SECURITY_RISK, got ALLOW |
| **Over-blocking** | Expected ALLOW but got DENY | Expected ACCEPTABLE_TLS, got DENY |

Safe mismatches are acceptable — they show the orchestrator is conservative. Unsafe mismatches are the primary concern — they show the orchestrator failed to detect a real risk. Over-blocking is a usability concern (false positives).

## Limitations

1. **Probe limitations propagate**: If the probe classifies a deprecated-TLS server as VALID_TLS, the orchestrator receives ACCEPTABLE_TLS and may produce fallback ALLOW — the same limitation as all other layers.
2. **No ground truth**: All evaluations use policy expectations, not ground-truth labels.
3. **Fallback ALLOW is not SPL confidence**: The balanced profile's fallback ALLOW is a deterministic adapter-based policy, not ML confidence. See `docs/CLI_CONFIDENCE_FALLBACK_POLICY.md`.
4. **OFE excluded**: OFE signals are observational only. They are not used in any decision rule.
5. **No SPL Core modification**: The orchestrator is a sidecar. It cannot learn or adapt without explicit updates to the policy rules.
6. **Not production-ready**: This is an observational design for policy analysis.

## CLI Access

The `spl_tls_analyze` CLI provides structured access to the orchestrator:

```bash
# Single domain with default profile (balanced)
python scripts/spl_tls_analyze.py example.com

# Batch analysis with strict profile
python scripts/spl_tls_analyze.py domains.txt --profile strict --json-out report.json
```

See `docs/CLI_USAGE.md` and `docs/CLI_OUTPUT_SCHEMA.md`.

## What the Orchestrator Does Not Do

- Replace SPL
- Modify SPL Core
- Promote OFE
- Claim production readiness
- Hide Phase 5/6.5 findings (SPL holdout: 70.3%, non-VALID_TLS: 0%)
- Convert all failures to DENY (many map to REVIEW)
