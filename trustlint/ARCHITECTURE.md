# TrustLint Architecture

## Overview

TrustLint is a TLS/domain risk analysis tool that probes targets, classifies risks, and produces structured decisions. The architecture separates concerns into distinct layers:

```
CLI (scripts/spl_tls_analyze.py)
  |
  v
Application Layer (analyze_domain, analyze, analyze_batch)
  |
  +---> Infrastructure Layer (TLS probing, OCSP checking)
  |       |
  |       +---> Security Layer (OutboundNetworkPolicy, TargetScanPolicy)
  |
  +---> Domain Layer (Decision Orchestrator, TLS Policy Adapter)
  |
  +---> Experimental Layer (SPL v7 Pipeline - isolated, opt-in only)
```

## Module Responsibilities

### Core Package (`trustlint/trustlint/`)
- **`__init__.py`**: Public Python API (re-exports from implementation).
- **`analyzer.py`**: Orchestration, public analysis API, result aggregation.
- **`security/`**: SSRF protection, safe HTTP client, target scanning policy.

### Infrastructure Layer (`trustlint/trustlint/infrastructure/`)
- **`tls_probe.py`**: DNS resolution, target policy enforcement, TLS context creation, handshake and certificate gathering, calling OCSP through the package-owned module.
- **`error_codes.py`**: Structured error code definitions (E1001-E9999).
- **`ocsp/`**: OCSP checking infrastructure.
  - **`client.py`**: OCSP URL extraction, request construction, response parsing, OCSP-specific timeout/error handling, OCSP-specific safe logging.

### CLI (`scripts/`)
- **`spl_tls_analyze.py`**: Argument parsing, logging setup, output formatting.
- **`run_local_tls_validation.py`**: Thin backward-compatible wrapper → `trustlint.infrastructure.tls_probe`.
- **`ocsp_checker.py`**: Thin backward-compatible wrapper → `trustlint.infrastructure.ocsp`.
- **`error_codes.py`**: Thin backward-compatible wrapper → `trustlint.infrastructure.error_codes`.

### Domain Layer
- **`decision_orchestrator/`**: Combines adapter + SPL outputs into final decisions.
- **`tls_policy_adapter/`**: Maps TLS classifications to risk categories.

### Experimental Layer (`spl_v7/`)
- **EvidencePipeline**: In-memory evidence processing (opt-in via `--spl-unsafe`).
- **Dashboard**: FastAPI topology visualization (hardened for production).
- **Kafka Pipeline**: Optional Kafka-based evidence transport.
- All SPL components emit warnings and are isolated from production decisions.

## Dependency Rules

1. **CLI depends on Application Layer** — never on infrastructure directly.
2. **Application Layer depends on Infrastructure + Domain** — never on CLI.
3. **Infrastructure Layer has no upward dependencies** — only stdlib + security layer.
4. **Security Layer has no upward dependencies** — standalone validation.
5. **Experimental Layer is isolated** — imported only when explicitly enabled.
6. **`scripts/` are thin wrappers** — the `trustlint` package does not depend on scripts.

## Data Flow

```
Target Domain
  |
  v
[TargetScanPolicy.validate_target()]  -- rejects private IPs
  |
  v
[DNS Resolution]  -- validates resolved IPs
  |
  v
[TLS Handshake]  -- extracts cert, protocol, cipher info
  |
  v
[OCSP Check]  -- validates OCSP URL via OutboundNetworkPolicy
  |
  v
[TLS Policy Adapter]  -- maps to risk category, severity
  |
  v
[Decision Orchestrator]  -- produces ALLOW/REVIEW/DENY
  |
  v
Structured Report (JSON/Markdown/Console)
```

## Security Boundaries

- **OutboundNetworkPolicy**: All HTTP requests pass through URL validation.
- **TargetScanPolicy**: All target IPs are validated against network restrictions.
- **Input Bounds**: File size, domain count, domain length are all bounded.
- **Dashboard Hardening**: Security headers, auth, CORS, XSS prevention.
- **Kafka Separation**: Development config is localhost-only; production requires encryption + auth.

## OCSP Module Architecture

The OCSP module (`trustlint.infrastructure.ocsp`) owns all OCSP-related functionality:

- **`client.py`**: OCSP URL extraction from certificates, OCSP request construction, response parsing, timeout/error handling, safe logging.
- **`__init__.py`**: Public API exports.

All outbound OCSP requests go through `SafeHttpClient` for SSRF protection. The OCSP URL is validated via `OutboundNetworkPolicy` before any request is made.

## Testing Strategy

- **Unit tests** (`tests/unit/`): No network, no external dependencies.
- **Security tests** (`tests/security/`): SSRF, target policy, dashboard hardening.
- **Architecture tests** (`tests/test_architecture_boundaries.py`): AST-based boundary enforcement.
- **Integration tests** (`tests/`): End-to-end pipeline with mocked probes.
- **Network tests** (`@pytest.mark.network`): Opt-in, require internet access.

Run offline tests: `pytest -m "not network and not slow"`
