# Decision Semantics Audit

Defines what ALLOW, REVIEW, and DENY mean in the context of the Decision
Orchestration Policy, and how each outcome is classified during evaluation.

---

## 1. Decision Definitions

### ALLOW

The connection or domain is considered safe. No action is required.

**When it is produced:**
- The classification is VALID_TLS.
- SPL confidence is >= threshold (0.5 for balanced, 0.7 for conservative/strict).
- Adapter risk is ACCEPTABLE_TLS / NONE.

**What it means:**
- Both adapter and SPL agree the TLS state is acceptable.
- The system treats this as a pass.
- ALLOW is the expected outcome for ACCEPTABLE_TLS policy.

**When ALLOW is incorrect:**
- If the probe missed a risk (e.g., deprecated TLS classified as VALID_TLS).
- If SPL confidence is high but the domain is actually risky (e.g., proxy-trained
  SPL confidently ALLOWs a security risk because the graph learned wrong).

---

### REVIEW

The domain requires human or secondary review. It is neither fully accepted nor
fully denied.

**When it is produced:**
- Adapter reports MEDIUM availability risk (DNS_FAILURE, CONNECTION_ERROR, TIMEOUT).
- Adapter reports HIGH security risk (EXPIRED_CERT, SELF_SIGNED_CERT,
  UNTRUSTED_CHAIN, INCOMPLETE_CHAIN, DEPRECATED_TLS_VERSION).
- Classification is ambiguous (TLS_HANDSHAKE_FAILURE, UNKNOWN_SSL_ERROR).
- VALID_TLS but SPL confidence is below 0.5.
- Any unhandled classification combination (fallback).
- All profiles produce REVIEW for MEDIUM availability, AMBIGUOUS, and
  HIGH security risk (except strict which produces DENY for HIGH security).

**What it means:**
- The orchestrator has identified a concern but not enough information to DENY
  automatically.
- REVIEW is the default safe outcome for anything that is not clearly VALID_TLS
  with high SPL confidence.
- REVIEW is the expected outcome for AVAILABILITY_RISK, AMBIGUOUS_FAILURE,
  CHAIN_TRUST_FAILURE, and UNKNOWN_RISK policies.

**When REVIEW is acceptable:**
- For SECURITY_RISK expected DENY: REVIEW is a **safe mismatch** (conservative).
  The risk was flagged — it was not missed. A human reviewer would catch it.
- For AVAILABILITY_RISK expected REVIEW: REVIEW is an **exact match**.
- For AMBIGUOUS_FAILURE expected REVIEW: REVIEW is an **exact match**.

**When REVIEW is over-cautious:**
- For ACCEPTABLE_TLS expected ALLOW: REVIEW is **over-blocking**. The orchestrator
  flagged a domain that is actually safe. This happens when there is no SPL
  confidence (adapter-only mode) or SPL confidence is low.

**When REVIEW is a failure:**
- REVIEW is never a failure in the security sense (it does not let through a risk).
- It is a failure only in the availability sense if an ALLOW was expected and
  the delay degrades user experience.

---

### DENY

The domain must be blocked. No further action is needed.

**When it is produced:**
- **Rule 1** (all profiles): Adapter reports CRITICAL severity.
- **Strict profile only** (Rule 2): Adapter reports HIGH severity
  security risk (EXPIRED_CERT, SELF_SIGNED_CERT, UNTRUSTED_CHAIN,
  INCOMPLETE_CHAIN, DEPRECATED_TLS_VERSION).
- Currently, only WRONG_HOST_CERT maps to CRITICAL severity.

**What it means:**
- The orchestrator determined that immediate denial is required regardless of
  SPL output.
- DENY is a strong action. It should be reserved for cases where the risk is
  unambiguous and severe.
- DENY is the expected outcome for SECURITY_RISK and DEPRECATED_PROTOCOL_RISK
  policies.

**When DENY is acceptable:**
- WRONG_HOST_CERT expected SECURITY_RISK -> DENY: exact match.
- Any SECURITY_RISK expected DENY: exact match.

**When DENY is over-blocking:**
- ACCEPTABLE_TLS expected ALLOW -> DENY: over-blocking (severe usability concern).
  Currently never happens for ACCEPTABLE_TLS because the orchestrator has no rule
  that produces DENY for non-CRITICAL cases (except strict profile which may
  DENY HIGH security risks).

---

## 2. Policy-to-Expected Final Decision Mapping

| Policy Label | Expected Final | When to Expect It |
|---|---|---|
| ACCEPTABLE_TLS | ALLOW | VALID_TLS with no risk detected |
| SECURITY_RISK | DENY | Expired, self-signed, wrong-host, untrusted chain |
| DEPRECATED_PROTOCOL_RISK | DENY | TLS 1.0/1.1 detected |
| AVAILABILITY_RISK | REVIEW | DNS failure, connection error, timeout |
| AMBIGUOUS_FAILURE | REVIEW | Handshake failure (could be security or availability) |
| CHAIN_TRUST_FAILURE | REVIEW | Incomplete chain (operational, not security per se) |
| UNKNOWN_RISK | REVIEW | Unrecognized error |

---

## 3. Match Classification Definitions

### exact

The final decision matches the expected final decision exactly.

- ALLOW -> ALLOW
- REVIEW -> REVIEW
- DENY -> DENY

Treated as: **full success**.

### safe mismatch

The final decision is conservative — more restrictive than expected but not wrong.

- Expected DENY -> Got REVIEW

The risk was flagged. A human can review it. No security breach.

Treated as: **acceptable conservative behavior** — partial success.

### unsafe mismatch

The final decision allowed something that should have been caught.

- Expected DENY -> Got ALLOW
- Expected REVIEW -> Got ALLOW

The risk was completely missed. This is the most serious type of mismatch.

Treated as: **failure**.

### over-blocking

The final decision was too restrictive — blocked or flagged something safe.

- Expected ALLOW -> Got REVIEW
- Expected ALLOW -> Got DENY

Treated as: **usability concern** — not a security issue, but causes false
positives that erode trust.

### under-blocking

[Used for explicit distinction.] The final decision allowed something that
needed at least REVIEW.

- Expected DENY -> Got ALLOW (same as unsafe)
- Expected REVIEW -> Got ALLOW (same as unsafe)

Treated as: **failure** — same as unsafe mismatch, but using the term
"under-blocking" to contrast with "over-blocking".

### unknown

No expected policy is defined for this domain.

Treated as: **inconclusive** — cannot evaluate.

---

## 4. REVIEW Handling Summary

| Scenario | Expected | Got | Classification | Assessment |
|---|---|---|---|---|
| VALID_TLS, no SPL | ALLOW | REVIEW | over-blocking | Too cautious, but safe |
| EXPIRED_CERT, no SPL | DENY | REVIEW | safe mismatch | Acceptable — risk flagged |
| DNS_FAILURE, no SPL | REVIEW | REVIEW | exact | Correct |
| TLS_HANDSHAKE | REVIEW | REVIEW | exact | Correct |
| VALID_TLS, high SPL conf | ALLOW | ALLOW | exact | Correct |
| VALID_TLS, low SPL conf | ALLOW | REVIEW | over-blocking | Cautious, acceptable |
| SECURITY_RISK + SPL obs | DENY | REVIEW | safe mismatch | Orchestrator saved SPL |

---

## 5. Profile-Aware Semantics

Phase 8 introduces configurable operating profiles that change when ALLOW
and DENY are produced:

| Scenario | Balanced | Conservative | Strict |
|----------|:--------:|:------------:|:------:|
| VALID_TLS, SPL conf 0.6 | ALLOW | REVIEW | REVIEW |
| VALID_TLS, SPL conf 0.8 | ALLOW | ALLOW | ALLOW |
| HIGH security risk | REVIEW | REVIEW | DENY |
| CRITICAL | DENY | DENY | DENY |
| MEDIUM availability | REVIEW | REVIEW | REVIEW |
| AMBIGUOUS | REVIEW | REVIEW | REVIEW |

Profiles do not change what ALLOW/REVIEW/DENY mean — they change when each
decision is triggered. The match classification definitions (exact, safe,
unsafe, over-blocking, under-blocking) remain the same across profiles.

### Safety-Adjusted Conformance by Profile

| Profile | Adapter-only | SPL Obs | SPL Holdout | SPL Proxy |
|---------|:----------:|:-------:|:-----------:|:---------:|
| Conservative | 20.0% / 28.3% | 20.0% / 28.3% | 21.6% / 29.7% | 20.0% / 28.3% |
| Balanced | 20.0% / 28.3% | **90.0% / 96.7%** | 21.6% / 29.7% | 20.0% / 28.3% |
| Strict | 25.8% / 28.3% | 25.8% / 28.3% | 26.8% / 29.7% | 25.8% / 28.3% |

Safety-adjusted conformance is identical across profiles because all three
produce REVIEW (safe) for HIGH security risks in adapter-only mode. The
difference is in exact conformance: strict converts 7 safe mismatches into
exact matches via DENY.

---

## 6. Safety-Adjusted Conformance

Safety-adjusted conformance = (exact + safe) / total

This measures: "did the system handle this domain in a way that is at least safe?"

A safe mismatch (REVIEW instead of DENY) is counted as success for safety purposes
because no risk was missed. The domain was flagged, just not denied.

This gives a more useful picture than raw exact conformance because REVIEW is the
default for most non-VALID_TLS cases in adapter-only mode.

| Mode | Exact | Safe | Safety-Adjusted |
|---|---|---|---|
| Adapter-only | 20.0% | +8.3% | 28.3% |
| SPL observation | 90.0% | +6.7% | 96.7% |
| SPL holdout | 21.6% | +8.1% | 29.7% |
| SPL proxy | 20.0% | +8.3% | 28.3% |

---

## 7. Key Insight

The 95.8% adapter-only in Phase 6.5 measured **risk category matching**.
The 20.0% in Phase 7 measures **final decision matching**.

These are different metrics. The former asks "did the adapter classify the risk
correctly?" The latter asks "did the orchestrator produce the exact expected
final action?"

Both are valid. Neither is wrong. They answer different questions:
- Phase 6.5: Does the adapter understand the TLS risk?
- Phase 7: Does the orchestrator produce the expected final decision?

The Phase 6.5 comparison was category-level (ACCEPTABLE_TLS vs SECURITY_RISK).
The Phase 7 comparison is decision-level (ALLOW vs REVIEW vs DENY).
