# Known Limitations

This document consolidates all known limitations across the project.

---

## 1. CLI / Probe Limitations

### 1.1 Deprecated TLS Detection (Secondary Probe)

The probe performs a **second TLS connection** after the primary handshake
succeeds. This second connection forces ``TLSVersion.TLSv1_1`` (if available
on the platform). If the server accepts the TLS 1.1 handshake the
classification is overridden to ``DEPRECATED_TLS_VERSION``.

**Impact:** Servers that support both TLS 1.3 and TLS 1.1 are now correctly
classified as ``DEPRECATED_TLS_VERSION`` instead of ``VALID_TLS``.

**Limitations:**
- The secondary probe only runs when the primary classification is
  ``VALID_TLS`` (domains with other errors are skipped).
- ``TLSv1_1`` must be available in the local OpenSSL build. If it is not,
  the ``deprecated_tls_check`` field is set to ``"unavailable_on_platform"``
  and a warning is emitted.
- The probe does not test TLS 1.0 separately (TLS 1.1 is the lowest
  version the probe can force).
- A server that only supports TLS 1.2+ and modern versions will correctly
  reject the secondary probe and remain ``VALID_TLS``.

### 1.2 DNS / Network Probe Instability

DNS failures, connection timeouts, and transient network errors are
classified as availability risks (AVAILABILITY_RISK). These are real
failures but may not reflect the target's security posture.

**Impact:** A temporary network issue produces a REVIEW result with no
security risk. The CLI marks these as probe-limited.

**Mitigation:** Re-run the probe for transient failures. Batch analysis
may show different results across runs.

### 1.3 OCSP Checking is Best-Effort

The probe checks revocation status via OCSP when possible:
- OCSP responder URLs are extracted from the certificate's AIA extension.
- A direct HTTP POST request is made to the responder (2s timeout).
- If the responder confirms revocation, the domain is classified as
  ``REVOKED_CERT`` (CRITICAL severity, DENY decision).
- If the responder is unreachable or times out, a ``VALID_TLS`` domain
  is reclassified as ``OCSP_UNREACHABLE`` (MEDIUM severity, REVIEW
  decision) rather than silently allowed.

**Impact:** Revoked certificates are detected when the OCSP responder is
reachable. Unreachable responders produce a REVIEW instead of ALLOW.

**Limitations:**
- OCSP stapling is **not** checked (not available in this Python build).
- The issuer certificate's SubjectPublicKeyInfo is obtained from the
  server's verified chain; servers that do not send intermediate
  certificates cannot be checked directly.
- OCSP response signatures are not validated (relies on responder
  reachability and well-formed response structure).
- Nonce handling is not implemented.

### 1.4 No Multi-IP Probing

If a domain resolves to multiple IP addresses, only the first address
returned by the system resolver is probed.

**Impact:** Different IPs may have different TLS configurations. A
single-IP probe may miss issues on other endpoints.

**Mitigation:** Use separate domain entries or DNS-level health checks.

### 1.5 No IPv6 Support

The current probe implementation only connects over IPv4. IPv6-only
domains will fail with a connection error.

**Impact:** IPv6-only domains cannot be analyzed.

**Mitigation:** Ensure dual-stack DNS or use an IPv6-capable probe.

### 1.6 Unsupported Probe Output Encoding

The `probe_domain` function is expected to return ASCII-safe output.
Non-ASCII characters in probe results (e.g., internationalized domain
names, non-English error messages) may cause encoding errors in the CLI.

**Impact:** Non-ASCII probe results may crash the CLI.

---

## 2. SPL / Pipeline Limitations

### 2.1 SPL is Not Run in CLI Mode

The CLI operates in adapter-only mode. SPL Core is not invoked during
`analyze_domain()`. This means:

- SPL confidence is always 0.0.
- VALID_TLS with balanced profile uses fallback ALLOW (adapter-policy
  based, not SPL confidence).
- Conservative and strict profiles still REVIEW for VALID_TLS without SPL.
- SPL weakness flags and causal graph reasoning are not available.

**Impact:** Fallback ALLOW reduces over-blocking for clean VALID_TLS
domains. No SPL-level reasoning in CLI output. Fallback ALLOW is not
production-grade confidence.

**Mitigation:** The fallback policy is documented in
`docs/CLI_CONFIDENCE_FALLBACK_POLICY.md`. A future phase may add a
`--spl` flag to run SPL observation mode for real confidence scoring.

### 2.2 SPL Generalization Limitations (Phase 5 / 6.5)

The SPL pipeline was benchmarked at 70.3% mean conformance across 10
stratified holdout splits. Non-VALID_TLS categories showed 0%
conformance because SPL defaults to `False` (ALLOW) for unseen
classifications.

**Impact:** SPL cannot distinguish risk sub-categories on domains it
has not seen during training. The orchestrator compensates with the
adapter guardrail, but SPL-level reasoning is unreliable for novel
classifications.

**Mitigation:** The adapter guardrail (Phase 6) and orchestrator
(Phase 7) provide a policy layer that compensates for SPL blind spots.
Do not rely on SPL alone for non-VALID_TLS domains.

### 2.3 OFE Remains HOLD_PENDING_REAL_DATA

The Orchestrated Feature Evaluator (OFE) is implemented but never
promoted. OFE signals are collected but do not affect any decision.
OFE is in permanent observation mode until real-world TLS data is
available for calibration.

**Impact:** OFE features (`ofe_signals`) are present in orchestrator
input but always ignored. `ofe_observed` is always `False` in CLI output.

---

## 3. Orchestrator Limitations

### 3.1 Chain Trust Ambiguity

The probe cannot distinguish between an incomplete certificate chain
and an untrusted chain. Both map to CHAIN_TRUST_FAILURE at the adapter
level, but INCOMPLETE_CHAIN is classified separately from UNTRUSTED_CHAIN.

**Impact:** A server with a valid chain that is missing intermediates
may be classified differently from one with an untrusted root, even
though the probe cannot reliably tell them apart.

**Mitigation:** Manual inspection is required for CHAIN_TRUST_FAILURE
results to determine the specific cause.

### 3.2 Profile Behavior is Deterministic

Operating profiles (conservative, balanced, strict) are hardcoded rules.
They do not learn, adapt, or improve over time. Switching profiles only
changes thresholds and default actions, not the underlying intelligence.

**Impact:** Profile choice does not improve detection accuracy — it only
changes the security/convenience tradeoff.

---

## 4. Testing Limitations

### 4.1 No Live Network Tests

All 483 unit tests use synthetic or mocked data. There are no tests
that probe live domains. Network behavior is verified only through
manual runs.

### 4.2 Golden Snapshots are Brittle

Golden acceptance tests compare output character-by-character. Any
formatting change (whitespace, ordering, new field) breaks snapshots.
Timestamp normalization is regex-based and may not cover all formats.

---

## 5. Project Status

### 5.1 Not Production Ready

This project is for **local evidence gathering and analysis only**. It
does not:

- Replace professional certificate management.
- Provide real-time monitoring.
- Guarantee detection of all TLS risks.
- Replace human review of security-critical domains.
- Offer a public API, web dashboard, or VPS deployment.
- Make any production readiness claim.

### 5.2 SPL Core is Never Modified

All phases since Phase 1 explicitly forbid modifying `spl_v7/`. The CLI,
adapter, and orchestrator are sidecars that consume SPL outputs without
altering the core pipeline.

### 5.3 Dogfood Findings

Two dogfood runs against 31 real public domains (see `docs/DOGFOOD_FINDINGS.md`)
confirmed these operational limitations:

- **Phase 12 (no fallback):** 0 ALLOW, 30 REVIEW, 1 DENY — 100% REVIEW rate.
- **Phase 13 (with fallback):** 19 ALLOW (fallback), 11 REVIEW, 1 DENY —
  exit code 0 is now usable.
- **Fallback ALLOW is not SPL confidence** — documented in
  `docs/CLI_CONFIDENCE_FALLBACK_POLICY.md`.
- **revoked.badssl.com** — OCSP checking now detects revocation when the
  responder is reachable. If the OCSP responder is unreachable the domain
  is reclassified as ``OCSP_UNREACHABLE`` (REVIEW) instead of ALLOW.
- **tls-v1-1/1-0.badssl.com not flagged** — confirmed deprecated TLS detection
  gap (OpenSSL negotiates TLS 1.2+). Now produce fallback ALLOW.
- **Markdown report is verbose** for large batches — 31 domains produce
  ~120 lines of report. Condensed output would help.

### 5.4 Local Beta Package

The package (`spl-tls-analyze` version `0.3.0b0`) is a local beta:
- Not published on PyPI — install from source only.
- No API stability guarantee for console output (JSON schema is stable).
- Zero external dependencies — the CLI uses stdlib only.
- Editable (`pip install -e .`) install is the primary distribution method.

### 5.5 Local Beta Freeze
The project is frozen at version `0.3.0b0` (local beta). See:

- `docs/RELEASE_NOTES_0.3.0b0.md` — release notes
- `docs/LOCAL_BETA_FREEZE_MANIFEST.md` — freeze manifest with stable/unstable contracts

### 5.6 No Ground Truth

All evaluations use policy expectations, not ground-truth labels. See
`docs/DECISION_SEMANTICS_AUDIT.md` for the distinction.

---

## 6. Docker Limitations

### 6.1 Docker is Optional

Docker support is provided for reproducible local execution. It is not
required — all CLI functionality works directly with Python 3.10+.

### 6.2 No Web Services

The Docker image runs the CLI command only:
- No ports exposed
- No web server
- No API
- No dashboard
- No VPS deployment layer

### 6.3 Network Differences

Docker's default bridge network may resolve DNS differently from the
host. For consistent DNS behavior, use `--network host`:

```bash
docker run --rm --network host spl-tls-analyze:0.3.0b0 example.com
```

### 6.4 Volume Mounting

Output files (`--json-out`, `--markdown-out`) written to mounted volumes
are owned by the container's `appuser` (UID 1000). On Linux, this may
require `chown` after extraction. On Windows, Docker Desktop handles
permission mapping automatically.

### 6.5 Image Size

The `python:3.10-slim` base image is approximately 120 MB. The final
image with the package and all source files may be 150-200 MB depending
on pip cache configuration.

---

## 7. VPS Dry Run Limitations

### 7.1 Controlled Testing Only

The VPS dry run is for **controlled, non-public, file-based testing only**:
- No ports exposed
- No web server or API
- No domain or HTTPS required
- No large-scale scanning
- No production deployment

### 7.2 Network-Dependent Results

VPS DNS resolution and network latency differ from local environments.
Results may drift from the local dogfood baseline (expected: 8 ALLOW /
6 REVIEW / 1 DENY for the 15-domain dataset).

### 7.3 Not a Deployment

The VPS dry run script (`scripts/run_vps_dry_run.sh`) is a one-shot batch
command. It does not:
- Start a long-running service
- Listen on any port
- Expose an API endpoint
- Require a reverse proxy or load balancer

---

## 8. Test Collection Errors (Pre-existing)

Eight test modules fail to collect under `pytest --collect-only`. These errors
exist on `master` and are **not regressions** introduced by repository-root
normalization. Master has 14 collection errors; the root normalization fixed
6 of them. The remaining 8 are pre-existing.

### 8.1 `tests/security/test_outbound_network_policy.py`

**Error:** `ModuleNotFoundError: No module named 'trustlint'`

**Root cause:** The test file imports `from trustlint.security.outbound_network_policy
import ...`. When pytest collects from `tests/security/`, the subdirectory lacks
`__init__.py`, causing pytest to manipulate `sys.path` in a way that disrupts
CWD-based discovery of the `trustlint/` package directory. The system Python's
editable install `MAPPING` may also point to a stale path.

**Affected legacy path:** `trustlint/tests/security/test_outbound_network_policy.py`
(now at `tests/security/test_outbound_network_policy.py` after flattening).

**Planned follow-up:** `hardening/test-collection-and-cli-recovery` branch.

### 8.2 `tests/security/test_target_policy.py`

**Error:** `ModuleNotFoundError: No module named 'trustlint'`

**Root cause:** Same as 8.1. The test imports `from trustlint.security.target_policy
import TargetScanPolicy`.

**Affected legacy path:** `trustlint/tests/security/test_target_policy.py`.

### 8.3 `tests/test_spl_decision_validation.py`

**Error:** `ModuleNotFoundError: No module named 'scripts.run_real_tls_spl_decision_validation'`

**Root cause:** The test imports from `scripts.run_real_tls_spl_decision_validation`,
a module that **never existed** in any committed branch. The file was likely
developed locally but never committed.

**Affected legacy path:** `trustlint/tests/test_spl_decision_validation.py`.

### 8.4 `tests/test_spl_tls_analyze.py`

**Error:** `ModuleNotFoundError: No module named 'scripts.spl_tls_analyze'`

**Root cause:** The test imports `from scripts.spl_tls_analyze import ...`. On master,
`scripts/spl_tls_analyze.py` does not exist in `trustlint/scripts/` (only
`error_codes.py`, `ocsp_checker.py`, `run_local_tls_validation.py`).

**Affected legacy path:** `trustlint/tests/test_spl_tls_analyze.py`.

### 8.5 `tests/test_cli_golden_acceptance.py`

**Error:** `ModuleNotFoundError: No module named 'scripts.spl_tls_analyze'`

**Root cause:** Same as 8.4.

**Affected legacy path:** `trustlint/tests/test_cli_golden_acceptance.py`.

### 8.6 `tests/test_package_entry.py`

**Error:** `ModuleNotFoundError: No module named 'scripts.spl_tls_analyze'`

**Root cause:** Same as 8.4.

**Affected legacy path:** `trustlint/tests/test_package_entry.py`.

### 8.7 `tests/unit/test_concurrency.py`

**Error:** `ModuleNotFoundError: No module named 'scripts.spl_tls_analyze'`

**Root cause:** Same as 8.4.

**Affected legacy path:** `trustlint/tests/unit/test_concurrency.py`.

### 8.8 `tests/unit/test_input_bounds.py`

**Error:** `ModuleNotFoundError: No module named 'scripts.spl_tls_analyze'`

**Root cause:** Same as 8.4.

**Affected legacy path:** `trustlint/tests/unit/test_input_bounds.py`.

---

## 9. References

- `docs/CLI_USAGE.md` — Limitations of CLI probe
- `docs/DECISION_SEMANTICS_AUDIT.md` — Ground truth vs policy expectations
- `docs/ORCHESTRATION_SCORING_AUDIT.md` — Scoring methodology
- `docs/PHASE5_PHASE6_METHOD_COMPARISON.md` — SPL generalization limits
- `docs/TLS_PROBE_LIMITATION_AUDIT.md` — Probe limitation details
- `docs/DECISION_ORCHESTRATION_POLICY.md` — OFE and SPL Core policy
