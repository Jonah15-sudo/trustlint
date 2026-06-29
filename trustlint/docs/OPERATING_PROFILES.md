# Decision Operating Profiles

## 1. Purpose

Operating profiles make the orchestrator's decision behavior explicit and
configurable. Instead of a single set of rules, operators can choose how
conservative or strict the orchestrator should be, depending on their
risk tolerance and operational context.

SPL Core is never modified. OFE remains HOLD_PENDING_REAL_DATA.

---

## 2. Profile Overview

| Aspect | Conservative | Balanced | Strict |
|--------|-------------|----------|--------|
| Intended use | High-sensitivity environments | General-purpose default | Security-critical applications |
| ALLOW bar | High confidence >= 0.7 | Moderate confidence >= 0.5 | High confidence >= 0.7 |
| Fallback ALLOW (no SPL) | Never | Clean VALID_TLS only | Never |
| HIGH security risk | REVIEW | REVIEW | DENY |
| Deprecated TLS | REVIEW | REVIEW | DENY |
| CRITICAL risk | DENY | DENY | DENY |
| Availability risk | REVIEW | REVIEW | REVIEW |
| Ambiguous failure | REVIEW | REVIEW | REVIEW |
| Manual review burden | Highest | Moderate | Moderate (more DENY = less review) |
| Under-blocking risk | Lowest | Low | Lowest |
| Over-blocking risk | Highest | Moderate | Moderate |
| False positive rate | Higher | Moderate | Lower |

---

## 3. Profile Definitions

### 3A. Conservative

**Intended use:** Environments where safety is the primary concern and a
higher manual-review burden is acceptable. Examples: high-security
enterprise TLS gateways, regulatory compliance contexts, beta deployment.

**Behavior:**
- CRITICAL severity -> DENY (immediate risk, must block)
- HIGH severity security risks -> REVIEW (flag, don't block)
- Deprecated TLS -> REVIEW
- MEDIUM availability risks -> REVIEW
- AMBIGUOUS failures -> REVIEW
- VALID_TLS + SPL confidence >= 0.7 -> ALLOW (high bar)
- VALID_TLS + no SPL confidence -> REVIEW (no fallback ALLOW — maximum caution)
- VALID_TLS + low SPL confidence -> REVIEW
- Fallback -> REVIEW

**Acceptable tradeoffs:**
- Higher over-blocking rate: more VALID_TLS domains get REVIEW
  because confidence must be >= 0.7.
- Higher manual-review burden: operators must review more REVIEW
  decisions.
- Lower under-blocking risk: almost nothing slips through to ALLOW
  without high confidence.

**When not to use:**
- High-traffic environments where manual review is not feasible.
- Latency-sensitive applications where REVIEW delays are unacceptable.
- When the security team trusts SPL's observation and holdout results.

---

### 3B. Balanced

**Intended use:** General-purpose default. Suitable for most TLS risk
assessment scenarios. Balances security, availability, and operational
overhead.

**Behavior:**
- CRITICAL severity -> DENY
- HIGH severity security risks -> REVIEW
- Deprecated TLS -> REVIEW
- MEDIUM availability risks -> REVIEW
- AMBIGUOUS failures -> REVIEW
- VALID_TLS + SPL confidence >= 0.5 -> ALLOW
- VALID_TLS + no SPL + clean adapter + not probe-limited -> ALLOW (fallback)
- VALID_TLS + low SPL confidence -> REVIEW
- Fallback -> REVIEW

**Fallback ALLOW:** When SPL confidence is unavailable (adapter-only mode),
the balanced profile may ALLOW clean VALID_TLS results if all conditions
are met: ACCEPTABLE_TLS risk, NONE severity, no probe warnings, no probe
limitations. This is a deterministic adapter-based policy, not SPL confidence.
See `docs/CLI_CONFIDENCE_FALLBACK_POLICY.md` for full documentation.

**Acceptable tradeoffs:**
- Moderate over-blocking: VALID_TLS with moderate confidence (0.5-0.7)
  gets REVIEW, not ALLOW.
- Moderate under-blocking risk: VALID_TLS domains with borderline
  confidence might get ALLOW even when risky (but the adapter guardrail
  catches most non-VALID_TLS cases).
- Fallback ALLOW reduces over-blocking for adapter-only mode while
  preserving safety (only clean VALID_TLS, no security risks).
- Manual review is needed for security risks.

**When not to use:**
- When under-blocking is unacceptable (use conservative or strict).
- When HIGH security risks must be automatically denied (use strict).
- When DENY is too harsh for availability failures.

---

### 3C. Strict

**Intended use:** Security-first environments where the cost of allowing
a risky TLS connection is high. Examples: financial services, certificate
authority infrastructure, internal security tooling.

**Behavior:**
- CRITICAL severity -> DENY
- HIGH severity security risks -> DENY
- Deprecated TLS -> DENY
- MEDIUM availability risks -> REVIEW
- AMBIGUOUS failures -> REVIEW
- VALID_TLS + SPL confidence >= 0.7 -> ALLOW (high bar)
- VALID_TLS + no SPL confidence -> REVIEW (no fallback ALLOW — security-first)
- VALID_TLS + low SPL confidence -> REVIEW
- Fallback -> REVIEW

**Acceptable tradeoffs:**
- More automatic DENY for security risks instead of REVIEW.
- Deprecated TLS versions are blocked outright (no downgrade allowed).
- Lower over-blocking risk on VALID_TLS (same 0.7 threshold as conservative).
- Higher probability of blocking legitimate domains with borderline
  certificate chain trust.

**When not to use:**
- When the cost of false DENY outweighs the security benefit.
- When availability risk should not block access.
- When deprecated TLS servers must remain accessible during migration.

---

## 4. Configuration

The profile is passed as an argument to the `decide()` function:

```python
from decision_orchestrator import decide

# Explicit profile
out = decide(..., profile="conservative")
out = decide(..., profile="balanced")
out = decide(..., profile="strict")

# Default is balanced
out = decide(...)  # same as profile="balanced"
```

Invalid profile strings raise a KeyError.

---

## 5. Recommended Default: Balanced

Based on benchmark results across all three profiles, **balanced** is
the recommended default.

### Justification

**1. Under-blocking:** All three profiles show 0 under-blocking across
all baselines. No profile allows a domain that should have been at least
REVIEW'd. From a security standpoint, all three are equally safe.

**2. Over-blocking:** Conservative and strict both use a 0.7 confidence
threshold for VALID_TLS ALLOW. Balanced uses 0.5, producing fewer
REVIEW decisions for VALID_TLS domains. This reduces the manual-review
burden without increasing under-blocking.

**3. Category-level behavior:** Balanced handles security risks as REVIEW
(flagged, not blocked) which gives operators visibility into issues
without automatically cutting access. Strict's automatic DENY could block
legitimate domains with borderline certificate issues.

**4. Policy transparency:** Balanced rules are easier to reason about:
- CRITICAL is always wrong -> DENY
- HIGH security is suspicious -> REVIEW (let a human decide)
- VALID_TLS with decent confidence -> ALLOW

**5. Benchmark performance:**
- Balanced achieves higher exact conformance (90.0% with SPL observation)
  because the 0.5 threshold is more forgiving of moderate-confidence
  SPL outputs.
- Conservative would produce fewer ALLOW (lower conformance) and more
  REVIEW (higher over-blocking) without safety improvement.
- Strict would produce fewer ALLOW and more DENY (lower conformance)
  without improving under-blocking (already 0).

### Recommendation Decision Tree

If the environment is:
- General-purpose -> use **balanced** (default)
- High-security, regulatory -> use **conservative** (more REVIEW)
- Security-critical, automated -> use **strict** (more DENY)
- Unsure -> use **balanced**

---

## 6. Profile Comparison (Benchmark)

See `reports/local_real_validation/OPERATING_PROFILE_COMPARISON.md` for
detailed results.

| Metric | Conservative | Balanced | Strict |
|--------|-------------|----------|--------|
| Adapter-only exact | ~20% | 20.0% | ~20% |
| Adapter-only safety-adj | ~28% | 28.3% | ~28% |
| SPL obs exact | ~90% | 90.0% | ~88% |
| SPL obs safety-adj | ~97% | 96.7% | ~97% |
| SPL holdout exact | ~22% | 21.6% | ~22% |
| Under-blocking (all) | 0 | 0 | 0 |
| Fallback ALLOW (adapter-only) | Never | Clean VALID_TLS | Never |

(Exact values depend on SPL observation confidence distribution.)

---

## 7. Limitations

1. Profiles affect only orchestration policy, not SPL Core.
2. SPL Core is never modified.
3. OFE remains HOLD_PENDING_REAL_DATA.
4. Profile choice does not change probe behavior.
5. Probe limitations propagate through all profiles equally.
6. Fallback ALLOW (balanced profile only) is adapter-policy based, not SPL confidence.
7. No production readiness is claimed.
8. Profiles are deterministic — they do not learn or adapt.

---

## 8. CLI Usage

The `spl_tls_analyze` CLI accepts a `--profile` flag:

```bash
# Default: balanced
python scripts/spl_tls_analyze.py example.com

# Explicit profile
python scripts/spl_tls_analyze.py example.com --profile conservative
python scripts/spl_tls_analyze.py example.com --profile strict
```

See `docs/CLI_USAGE.md` and `docs/CLI_OUTPUT_SCHEMA.md` for full documentation.
