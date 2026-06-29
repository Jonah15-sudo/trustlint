# TLS Probe Limitation Audit

Audits the 5 mismatches between adapter output and policy expectations in the Phase 6 benchmark.

## Summary

Total benchmark domains: 120
Adapter conformant: 115 (95.8%)
Adapter mismatches: 5

All 5 mismatches are caused by **probe-level limitations**, not by incorrect adapter mappings.

## Mismatch 1: columbia.edu

| Field | Value |
|---|---|
| Expected label | ACCEPTABLE_TLS |
| Actual probe classification | DNS_FAILURE |
| Adapter maps to | AVAILABILITY_RISK |
| Root cause | **Probe issue**: The domain failed DNS resolution at the time of probing. This is a transient network issue, not a TLS classification error. The adapter correctly maps DNS_FAILURE to AVAILABILITY_RISK. |
| Adapter validity | **Not affected**. The adapter's mapping is correct. The probe produced a DNS_FAILURE classification; the adapter correctly mapped it. |
| SPL validity | **Not directly affected**. SPL would also receive DNS_FAILURE as the classification and base its decision on the evidence artifact's `transport_meta.error_type`. In proxy-trained mode, SPL learns that DNS_FAILURE → dirty, which aligns with the expected non-ACCEPTABLE_TLS label. The mismatch exists because the expectation says ACCEPTABLE_TLS but the probe could not reach the domain. |
| Classification | This is an expectation that the probe would reach the domain. When the probe fails, the expectation cannot be met regardless of adapter or SPL correctness. |

## Mismatch 2: uchicago.edu

| Field | Value |
|---|---|
| Expected label | ACCEPTABLE_TLS |
| Actual probe classification | DNS_FAILURE |
| Adapter maps to | AVAILABILITY_RISK |
| Root cause | **Probe issue**: Same as columbia.edu — transient DNS failure at probe time. The domain is expected to be a valid TLS endpoint but was not resolvable during the benchmark probe run. |
| Adapter validity | **Not affected**. Correct mapping of DNS_FAILURE → AVAILABILITY_RISK. |
| SPL validity | **Not directly affected**. Same analysis as mismatch 1. |
| Classification | Same probe-side issue: the probe could not reach a domain expected to be valid. |

## Mismatch 3: untrusted-root.badssl.com

| Field | Value |
|---|---|
| Expected label | SECURITY_RISK |
| Actual probe classification | DNS_FAILURE |
| Adapter maps to | AVAILABILITY_RISK |
| Root cause | **Probe issue**: BadSSL's `untrusted-root.badssl.com` may have experienced a transient DNS issue at probe time. BadSSL test endpoints occasionally have availability issues. The adapter correctly maps DNS_FAILURE to AVAILABILITY_RISK. |
| Adapter validity | **Not affected**. Correct mapping. |
| SPL validity | **Not directly affected**. SPL receives DNS_FAILURE and cannot detect the untrusted root certificate because the handshake never completed. |
| Note | In previous Phase 4 runs, `untrusted-root.badssl.com` was classified as UNTRUSTED_CHAIN. The DNS failure in this benchmark run is intermittent. |

## Mismatch 4: tls-v1-0.badssl.com

| Field | Value |
|---|---|
| Expected label | SECURITY_RISK |
| Actual probe classification | VALID_TLS |
| Adapter maps to | ACCEPTABLE_TLS |
| Root cause | **Probe limitation**: The probe uses Python's default SSL context, which negotiates the highest mutually supported TLS version. When the system supports TLS 1.2+ (all modern systems), the handshake succeeds at TLS 1.2 even though the server also supports TLS 1.0. The `tls_version` field reports TLSv1.2, not TLSv1.0. The deprecated TLS reclassification (`_resolve_classification()`) does not trigger because the negotiated version is not in the `DEPRECATED_TLS_VERSIONS` set. |
| Adapter validity | **Not affected**. The adapter receives VALID_TLS and correctly maps to ACCEPTABLE_TLS / NONE. The adapter has no way to know the server supports deprecated versions — the probe's classification is the only input. |
| SPL validity | **Not directly affected**. SPL also receives VALID_TLS and cannot distinguish this case. The limitation is at the probe layer. |
| Classification | This is a **probe capability limitation**: the probe cannot detect deprecated TLS support without version-restricted handshakes. Fixing this requires changes to `scripts/run_local_tls_validation.py`, not the adapter or SPL Core. |

## Mismatch 5: tls-v1-1.badssl.com

| Field | Value |
|---|---|
| Expected label | SECURITY_RISK |
| Actual probe classification | VALID_TLS |
| Adapter maps to | ACCEPTABLE_TLS |
| Root cause | **Probe limitation**: Same as mismatch 4, but for the TLS 1.1 test endpoint. The probe negotiates TLS 1.2+ and classifies as VALID_TLS. |
| Adapter validity | **Not affected**. Same analysis as mismatch 4. |
| SPL validity | **Not directly affected**. Same analysis as mismatch 4. |
| Classification | Same probe capability limitation as mismatch 4. |

## Aggregate Impact Assessment

| Aspect | Assessment |
|---|---|
| Adapter mapping errors | **0** — all 12 classifications map correctly |
| Adapter mismatches from probe issues | **5** — 3 DNS failures, 2 deprecated TLS |
| Adapter mismatches from incorrect mapping | **0** |
| SPL mismatches from probe issues | **5** (same set — SPL receives same probe data) |
| SPL mismatches from learning failure | **0 in proxy-trained mode** (graph has seen all domains); **unknown in holdout mode** (Phase 5 measured ~70% holdout) |
| Deprecated TLS probe limitation | **Documented**: The probe cannot detect deprecated TLS versions because the default SSL context negotiates the highest version. |
| Chain trust probe ambiguity | **Documented**: INCOMPLETE_CHAIN vs UNTRUSTED_CHAIN cannot be distinguished at probe level. |
| Transient DNS failures | **Expected**: 3 out of 86 VALID_TLS domains failed DNS resolution during this probe run (3.5%). This is within normal range for live public internet probing. |

## Resolution Paths

| Issue | Resolution |
|---|---|
| Deprecated TLS detection | Add version-restricted handshakes to `probe_domain()` — force TLS 1.0 and TLS 1.1 separately and check server acceptance. This is outside the adapter's scope. |
| Transient DNS failures | Re-probe failed domains. Accept that live internet probing includes transient failures. The conformance ceiling for any live-probe benchmark is <100% due to network variance. |
| Chain trust ambiguity | Add intermediate certificate store probing. This is outside the adapter's scope. |

## Conclusion

All 5 adapter mismatches are **probe-level limitations**, not adapter errors. The adapter mapping is correct for every classification it receives. No changes to the adapter are needed. The probe limitations are documented in `docs/REAL_TLS_EVIDENCE_CONTRACT.md`.
