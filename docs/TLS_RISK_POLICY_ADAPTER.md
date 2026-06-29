# TLS Risk Policy Adapter

## Purpose

A sidecar module that maps explicit TLS probe classifications into structured risk evidence without modifying SPL Core. The adapter exists to separate *deterministic TLS policy knowledge* from *SPL learning behavior*.

## Why Phase 5 Failed

Phase 5's stratified benchmark (120 domains, 10 runs) showed 70.3% mean conformance with 0% conformance across all non-VALID_TLS categories. The root cause is not a probe or collection failure — it is a **label granularity failure**.

SPL's causal graph (`OnlineCausalGraphLearner`) learns from a single binary signal:

```
label = True (dirty)  /  False (clean)
```

This binary label conflates 10 distinct failure modes into one "problematic" bucket. A DNS failure, an expired certificate, and a TLS handshake error all produce the same training signal. The graph cannot learn that expired certs are a security concern while DNS failures are an availability concern — they all look the same to the learning algorithm.

When this binary-trained graph encounters an unseen domain in the holdout set, it can only answer "is this VALID_TLS or not?" based on surface features. It cannot distinguish *which kind* of risk the domain presents, so it defaults to `False` (ALLOW) for anything that does not match the training distribution's typical pattern.

## Why Binary Clean/Dirty Labels Are Insufficient

| Classification | Binary Label | Actual Risk | Policy Category |
|---|---|---|---|
| VALID_TLS | False (clean) | None | ACCEPTABLE_TLS |
| EXPIRED_CERT | True (dirty) | High | SECURITY_RISK |
| SELF_SIGNED_CERT | True (dirty) | High | SECURITY_RISK |
| WRONG_HOST_CERT | True (dirty) | Critical | SECURITY_RISK |
| DNS_FAILURE | True (dirty) | Medium | AVAILABILITY_RISK |
| TLS_HANDSHAKE_FAILURE | True (dirty) | Medium | AMBIGUOUS_FAILURE |

The graph receives the same label for entirely different risk profiles. It cannot learn category-specific behavior because the label signal is not category-specific.

## How the Adapter Works

The adapter sits *between* the TLS probe and any downstream consumer (such as SPL). It:

1. Takes a raw TLS probe result (classification + metadata)
2. Applies a deterministic mapping table (classification → risk category, severity, failure family, action hint)
3. Produces a structured `TLSPolicyEvidence` object with enriched risk fields
4. Optionally injects that evidence into the SPL evidence artifact as an additional field

The mapping is entirely deterministic. There is no learning, no training, no threshold tuning.

## TLS Classification to Risk Category Mapping

| Classification | Risk Category | Severity | Failure Family | Action Hint |
|---|---|---|---|---|
| VALID_TLS | ACCEPTABLE_TLS | NONE | NONE | NONE |
| EXPIRED_CERT | SECURITY_RISK | HIGH | CERTIFICATE_TRUST | RENEW_OR_DENY |
| SELF_SIGNED_CERT | SECURITY_RISK | HIGH | CERTIFICATE_TRUST | REVIEW_OR_DENY |
| WRONG_HOST_CERT | SECURITY_RISK | CRITICAL | CERTIFICATE_TRUST | DENY |
| UNTRUSTED_CHAIN | SECURITY_RISK | HIGH | CHAIN_TRUST | REVIEW_OR_DENY |
| INCOMPLETE_CHAIN | CHAIN_TRUST_FAILURE | HIGH | CHAIN_TRUST | REVIEW_OR_DENY |
| DNS_FAILURE | AVAILABILITY_RISK | MEDIUM | AVAILABILITY | REVIEW |
| CONNECTION_ERROR | AVAILABILITY_RISK | MEDIUM | AVAILABILITY | REVIEW |
| TIMEOUT | AVAILABILITY_RISK | MEDIUM | AVAILABILITY | REVIEW |
| TLS_HANDSHAKE_FAILURE | AMBIGUOUS_FAILURE | MEDIUM | AMBIGUOUS | INVESTIGATE |
| UNKNOWN_SSL_ERROR | UNKNOWN_RISK | LOW | UNKNOWN | INVESTIGATE |
| DEPRECATED_TLS_VERSION | DEPRECATED_PROTOCOL_RISK | HIGH | PROTOCOL_WEAKNESS | MODERNIZE_OR_DENY |

### Severity Definitions

| Severity | Meaning | Example |
|---|---|---|
| NONE | No risk detected | Valid TLS with trusted certificate |
| LOW | Minimal risk, informational | Unknown/unrecognized error pattern |
| MEDIUM | Notable risk, should be reviewed | Availability failure (DNS, timeout) |
| HIGH | Significant risk, likely requires action | Expired cert, self-signed, chain trust failure |
| CRITICAL | Immediate risk, must not be accepted | Wrong host certificate (active MITM indicator) |

### Failure Family Definitions

| Family | Description |
|---|---|
| NONE | No failure |
| CERTIFICATE_TRUST | Certificate validity or trust issue |
| CHAIN_TRUST | Certificate chain completeness or trust anchor issue |
| AVAILABILITY | Domain unreachable (DNS, connection, timeout) |
| PROTOCOL_WEAKNESS | Weak or deprecated TLS protocol version |
| AMBIGUOUS | Cannot determine failure root cause |
| UNKNOWN | Unrecognized failure mode |

## Chain Trust Ambiguity

The adapter documents but does not resolve the INCOMPLETE_CHAIN vs UNTRUSTED_CHAIN ambiguity:

- **INCOMPLETE_CHAIN**: Server did not send the intermediate certificate; the chain cannot be built.
- **UNTRUSTED_CHAIN**: The chain is complete but the root CA is not in the local trust store.

Both map to `CHAIN_TRUST_FAILURE` in the adapter. The adapter sets the failure family to `CHAIN_TRUST` for both. This is honest about the ambiguity rather than pretending the probe can distinguish them.

INCOMPLETE_CHAIN is mapped to `CHAIN_TRUST_FAILURE` (a dedicated risk category) rather than `SECURITY_RISK` because the incomplete chain is an operational misconfiguration rather than a security failure per se — the certificate itself is valid, but the chain delivery is broken.

## What the Adapter Is Allowed To Do

- Read TLS probe results (classification, metadata)
- Apply deterministic mapping tables
- Produce structured risk evidence
- Inject enriched evidence fields into the SPL evidence artifact
- Document mapping decisions and ambiguity
- Generate benchmark comparison reports

## What the Adapter Is Forbidden From Doing

- Modify SPL Core
- Change SPL decision logic
- Tune OFE or promote OFE
- Read expected labels, benchmark expectations, or holdout labels
- Use ground-truth data
- Learn or adapt from data
- Claim production readiness
- Replace SPL or its decision output
- Optimize thresholds to improve benchmark scores
- Remove difficult benchmark cases

## Relationship to SPL

```
TLS Probe → Adapter → Structured Risk Evidence → SPL Evidence Artifact → SPL Pipeline → Decision
                ↓
         Benchmark Comparison
         (adapter vs SPL)
```

The adapter does **not**:

- Replace SPL. SPL still produces the final decision.
- Promote OFE. OFE remains `HOLD_PENDING_REAL_DATA`.
- Modify SPL Core. No SPL source file is touched.
- Hide Phase 5 failure. The adapter's entire purpose is to demonstrate that deterministic policy mapping *would* improve non-VALID_TLS handling — exactly because SPL cannot do this with binary labels.

## What Cannot Be Concluded

- If the adapter shows 100% conformance on non-VALID_TLS categories, this is **not** evidence that SPL has learned anything. It is evidence that a deterministic rule-based mapping is sufficient to categorize TLS risk.
- The adapter is not a replacement for learned generalization. It is a *sidecar* that makes explicit what the current SPL causal graph must infer from binary labels.
- No production readiness is claimed. The adapter is an observational tool for policy analysis.

## Deprecated TLS Limitations

The current probe uses Python's default SSL context, which negotiates the highest mutually supported TLS version. When a server supports both TLS 1.0 and TLS 1.2, the probe will negotiate TLS 1.2 and classify the domain as VALID_TLS — even though the server accepts deprecated versions.

This is a probe-level limitation, not an adapter limitation. The adapter maps whatever classification it receives. If the probe classifies a deprecated-TLS-supporting server as VALID_TLS, the adapter will map it to `ACCEPTABLE_TLS / NONE`. This is correct behavior given the input — the limitation is in the probe, not the mapping.

See `docs/REAL_TLS_EVIDENCE_CONTRACT.md` for details on the probe limitation.

## Evaluation Integrity Note (Phase 6.5)

The original Phase 6 benchmark reported "SPL-only" conformance at 95.8%, which was comparable to the adapter-only result (also 95.8%). However, this "SPL-only" used **proxy-trained** mode (train and evaluate on all 120 domains), not holdout. This was corrected in Phase 6.5:

- **Adapter-only**: 95.8% — deterministic mapping, no learning.
- **SPL observation**: ~36% — cold-start graph, no training.
- **SPL holdout**: 70.3% — train on 83, evaluate on 37 unseen (generalization estimate).
- **SPL proxy-trained**: 95.8% — train and evaluate on same 120 domains (upper bound, NOT generalization).

Phase 5's stratified holdout (70.3%) remains the correct generalization warning. The adapter does not prove SPL generalization — it proves that deterministic classification-to-risk mapping is sufficient to handle non-VALID_TLS categories that SPL cannot learn from binary labels.

See `docs/PHASE5_PHASE6_METHOD_COMPARISON.md` for the full methodology audit.
See `reports/local_real_validation/PHASE6_BASELINE_COMPARISON.md` for the corrected multi-baseline comparison.

## Phase 7 -- Decision Orchestration

The adapter feeds into the Decision Orchestrator (`decision_orchestrator/`) which
combines adapter risk evidence with SPL decision/confidence to produce transparent
final decisions. The orchestrator uses adapter severity as a guardrail (CRITICAL->DENY)
while preserving SPL as the reasoning layer for VALID_TLS cases.

The adapter's role in the orchestrated pipeline:

- Provides deterministic risk category and severity that the orchestrator can trust
  for immediate policy enforcement (DENY on CRITICAL, REVIEW on HIGH/MEDIUM)
- Supplies structured evidence that supplements SPL's binary decision with
  risk-specific context
- Does not replace SPL -- the orchestrator defers to SPL for VALID_TLS + high confidence

See `docs/DECISION_ORCHESTRATION_POLICY.md` for the full design document.
See `reports/local_real_validation/DECISION_ORCHESTRATION_REPORT.md` for benchmark results.
