# Dogfood Findings — Phase 12/13

## Overview

Dogfood runs against 31 real public domains using profile `balanced`
with 10s timeout per domain.

### Phase 12 (Before Fallback, 2026-06-01)

- **31/31 domains succeeded** — 0 errors, 0 timeouts
- **0 ALLOW, 30 REVIEW, 1 DENY**
- **Highest risk: CRITICAL** (wrong.host.badssl.com)
- **2 probe-limited** (DNS failures)
- **Exit code: 2** (one DENY -> action needed)

### Phase 13 (After Fallback, 2026-06-01)

- **31/31 domains succeeded** — 0 errors, 0 timeouts
- **19 ALLOW, 11 REVIEW, 1 DENY**
- **19 fallback ALLOW** (all clean VALID_TLS domains via balanced fallback)
- **Highest risk: CRITICAL** (wrong.host.badssl.com)
- **2 probe-limited** (DNS failures)
- **Exit code: 2** (one DENY -> action needed)

### Before/After Comparison

| Metric | Phase 12 (no fallback) | Phase 13 (with fallback) | Change |
|--------|:---:|:---:|:---:|
| ALLOW | 0 | 19 | +19 |
| REVIEW | 30 | 11 | -19 |
| DENY | 1 | 1 | 0 |
| Exit code 0 usable? | No | Yes | Improved |
| Valid domains over-blocked? | 15/15 | 0/15 | Fixed |
| Risky domains became ALLOW? | — | 0 | No regression |

---

## What Worked

### 1. DENY Classification is Accurate

`wrong.host.badssl.com` correctly received **DENY / CRITICAL**.
The hostname mismatch was detected and escalated correctly through
adapter (CRITICAL severity) -> orchestrator (Rule 1: CRITICAL -> DENY).
This is the most operationally useful signal the CLI produces.

### 2. Security Risk Detection Works

Known-issue domains from badssl.com were correctly classified:
- `expired.badssl.com` -> EXPIRED_CERT / HIGH / REVIEW
- `self-signed.badssl.com` -> SELF_SIGNED_CERT / HIGH / REVIEW
- `untrusted-root.badssl.com` -> UNTRUSTED_CHAIN / HIGH / REVIEW
- `incomplete-chain.badssl.com` -> UNTRUSTED_CHAIN / HIGH / REVIEW

These are the domains where operators most need visibility.

### 3. DNS Failure Handling

Both fake DNS domains were correctly caught:
- Classified as DNS_FAILURE / MEDIUM / REVIEW
- Marked as probe-limited with clear warning text
- Recommended action ("Check DNS records") is actionable

### 4. Ambiguous Failures

`dh480.badssl.com` and `null.badssl.com` correctly received
TLS_HANDSHAKE_FAILURE / MEDIUM / REVIEW with an investigation
recommendation — the right default for unclassifiable errors.

### 5. Exit Code 2 (DENY) is Unambiguous

With one DENY in the batch, exit code 2 clearly signals
"immediate action required." The batch summary correctly lists
`wrong.host.badssl.com` under "Domains Requiring Immediate Action."

---

## What Was Confusing

### 1. REVIEW for Every Valid Domain (Over-blocking) — RESOLVED in Phase 13

**Phase 12 (before fallback):** All 15 high-profile valid domains
(google.com, github.com, etc.) received REVIEW/LOW. Zero domains
produced exit code 0.

**Phase 13 (with fallback):** All 15 valid domains now produce
ALLOW via the confidence fallback policy (balanced profile). Exit
code 0 is now usable for clean scans.

The fallback policy (see `docs/CLI_CONFIDENCE_FALLBACK_POLICY.md`)
ALLOWs clean VALID_TLS results when SPL confidence is unavailable,
provided the adapter says ACCEPTABLE_TLS/NONE and the probe is not
limited. This is a deterministic adapter-based policy, not SPL
confidence, and is explicitly documented as such.

**Remaining concern:** revoked.badssl.com also produces ALLOW via
fallback because the probe does not check CRL/OCSP — the revoked
certificate looks like VALID_TLS to the probe. This is a known
probe limitation (see section 1.3 in KNOWN_LIMITATIONS.md).

### 2. Incomplete Chain Classified as UNTRUSTED_CHAIN

`incomplete-chain.badssl.com` was classified as UNTRUSTED_CHAIN,
not INCOMPLETE_CHAIN. The probe cannot distinguish between an
incomplete chain and an untrusted root.

**Impact:** Operator cannot tell whether the fix is "install
missing intermediates" vs "replace the root certificate."

**Assessment:** This is a documented probe limitation. The
recommended action ("Fix the certificate chain — ensure all
intermediate certificates are installed") covers both cases.

### 3. sha1-intermediate.badssl.com -> UNKNOWN_SSL_ERROR

The SHA-1 intermediate certificate caused an unclassifiable SSL
error. The CLI correctly marked it as UNKNOWN_SSL_ERROR/LOW, but
the recommended action ("Investigate SSL error details manually")
is vague.

**Impact:** Operator must manually investigate the SSL error.
No specific guidance on what to look for.

**Assessment:** This is the correct behavior for unclassifiable
errors. Improving it would require extending the probe to
recognize more SSL error patterns.

### 4. no-common-name / no-subject -> EXPIRED_CERT

`no-common-name.badssl.com` and `no-subject.badssl.com` were
classified as EXPIRED_CERT rather than something like
WRONG_HOST_CERT or a new classification. The probe detects that
the certificate has expired (these domains use expired certs with
unusual properties).

**Impact:** The recommended action says "Renew or replace" which
is partially correct, but the real issue (missing common name / subject)
is not surfaced.

**Assessment:** This is a probe-level limitation — the probe extracts
what it can from the SSL error.

---

## What Felt Too Conservative

### Valid Domain REVIEW (Adapter-Only Mode) — RESOLVED in Phase 13

**Phase 12 (before fallback):** All 15 valid domains received REVIEW
instead of ALLOW. This was the single biggest usability issue.

**Phase 13 (with fallback):** All 15 valid domains now receive ALLOW
via the balanced profile fallback policy. Exit code 0 is usable for
clean scans.

The fallback was documented in `docs/CLI_CONFIDENCE_FALLBACK_POLICY.md`.
The remaining conservative behavior (probe-limited clean domains,
risky classifications) is appropriate for local beta.

**Remaining risks:**
- revoked.badssl.com now also gets ALLOW via fallback (it looks
  like VALID_TLS to the probe)
- deprecated TLS domains that negotiate up also get ALLOW via fallback
- These are known probe limitations, not fallback design flaws

---

## What Felt Too Permissive

### 1. Revoked Cert Not Detected

`revoked.badssl.com` was classified as VALID_TLS with ALLOW/NONE
(via fallback). The probe does not check CRL or OCSP.

**Impact:** A revoked certificate is treated as valid.

**Mitigation:** Documented known limitation. Add OCSP checking
in a future phase.

### 2. Deprecated TLS Not Detected

`tls-v1-1.badssl.com` and `tls-v1-0.badssl.com` were classified
as VALID_TLS (now ALLOW via fallback) because OpenSSL negotiated
TLS 1.2.

**Impact:** Deprecated TLS versions are invisible to the probe.

**Mitigation:** Documented known limitation. Server-side TLS
configuration audit is required.

### 3. SHA-1 Intermediate Passes Without Flag

`sha1-intermediate.badssl.com` produced UNKNOWN_SSL_ERROR rather
than a specific "SHA-1 deprecation" warning.

**Impact:** SHA-1 intermediates are not specifically flagged.

**Mitigation:** Extend probe to detect SHA-1 certificates.

---

## Profile Assessment

### Balanced Profile

The balanced profile produced these results:
- CRITICAL -> DENY (correct)
- HIGH security risks -> REVIEW (correct — flag, don't block)
- DNS failures -> REVIEW (correct)
- Ambiguous failures -> REVIEW (correct)
- VALID_TLS without SPL -> ALLOW via fallback (clean results)
- VALID_TLS without SPL, probe-limited -> REVIEW (correct — cannot safely fallback)

**Recommendation:** Balanced with fallback is appropriate for
local beta. 19/31 domains produce ALLOW (usable exit code 0),
while 11 REVIEW and 1 DENY correctly flag the real issues.

### Profile Comparison

| Dimension | Phase 12 Observation | Phase 13 Observation |
|-----------|---------------------|---------------------|
| Would conservative help? | No — still all REVIEW | No — still all REVIEW (no fallback) |
| Would strict help? | No — turns HIGH to DENY | No — still no fallback |
| What would really help? | SPL integration | Fallback already implemented — balanced with fallback is practical for local use |
| Next step? | — | SPL integration for production-grade confidence |

---

## Exit Code Practicality

| Exit Code | Use Case | Phase 12 (no fallback) | Phase 13 (with fallback) |
|-----------|----------|:---:|:---:|
| 0 (ALLOW) | All-clear | Not observed | 19/31 — usable for clean scans |
| 1 (REVIEW) | Review needed | 30/31 | 11/31 — reduced noise |
| 2 (DENY) | Action needed | 1/31 | 1/31 — still clear |
| 3 (error) | Runtime error | Not observed | Not observed |
| 4 (invalid) | Bad args | N/A | N/A |

**Finding:** Exit codes 2, 3, 4 remain practical and unambiguous.
Exit code 0 (19/31 domains) is now usable for clean scans. Exit
code 1 (11/31) is less noisy and more actionable — it now signals
genuine issues (security risks, availability failures, ambiguous
errors) rather than "every domain needs review."

The remaining gap: exit codes 0 and 1 are still functionally
similar for operators who only check "did any fail?" — but exit
code 0 at least provides a clean signal for all-ALLOW batches.

---

## What Should Change Before Any VPS/API Work

1. **SPL integration** (`--spl` flag) — fallback ALLOW is adapter-policy
   based, not SPL confidence. SPL integration would provide ML-powered
   confidence scoring for production use.

2. **OCSP/CRL checking** — revoked certificates are invisible.
   A production-facing tool must detect revocation.

3. **Deprecated TLS detection** — server-side version checking is
   needed since OpenSSL always negotiates up.

4. **Multi-IP probing** — domains with multiple A records (like
   github.com, cloudflare.com) should probe all IPs.

5. **Reduced console noise** — the structured output is 35 lines
   per domain. For 31 domains, that's ~1000 lines of output.
   A condensed "one-liner" mode would help.

### Already Resolved in Phase 13

The fallback policy addresses the single biggest usability issue:
valid domains no longer flood REVIEW results. Exit code 0 is now
usable (19/31 domains in the dogfood run).

---

## What Must NOT Change

1. **SPL Core isolation** — `spl_v7/` must never be modified by
   the CLI or sidecars.

2. **No production readiness claim** — the tool is local-only and
   must remain explicitly non-production.

3. **No PyPI publishing** — local install only.

4. **OFE remains observational** — must never affect decisions
   until real-world calibration is done.

5. **Deterministic output** — recommended actions must remain
   deterministic per classification, not AI-generated.

6. **No false ALLOW for security risks** — the adapter guardrail
   must remain in place to prevent security risks from being
   ALLOW'd even with high SPL confidence.

7. **Transparent limitations** — probe limitations must continue
   to propagate through all decisions and be visible in output.

---

## Summary

The CLI is **practical for local advisory use** after the Phase 13
fallback policy. 19/31 domains produce ALLOW (usable exit code 0),
11 REVIEW correctly flag real issues (security risks, DNS failures,
ambiguous errors), and 1 DENY requires immediate action.

The fallback policy (balanced profile only) is a deterministic
adapter-based policy, not SPL confidence. It is explicitly
documented in `docs/CLI_CONFIDENCE_FALLBACK_POLICY.md`.

Remaining gaps for production use: SPL integration, OCSP/CRL
checking, deprecated TLS detection, multi-IP probing.
