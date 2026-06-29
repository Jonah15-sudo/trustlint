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

### Core Package (`trustlint/`)
- **`__init__.py`**: Public Python API (re-exports from implementation).
- **`security/`**: SSRF protection, safe HTTP client, target scanning policy.

### CLI (`scripts/spl_tls_analyze.py`)
- Argument parsing, logging setup, output formatting.
- Thin orchestrator calling application-layer functions.
- Concurrency management via ThreadPoolExecutor.

### Application Layer
- **`analyze_domain()`**: Single-domain analysis pipeline.
- **`analyze()`**: Public API for single-domain analysis.
- **`analyze_batch()`**: Public API for batch analysis.

### Infrastructure Layer
- **`scripts/run_local_tls_validation.py`**: TLS handshake probing, DNS resolution.
- **`scripts/ocsp_checker.py`**: OCSP certificate revocation checking.

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

## Testing Strategy

- **Unit tests** (`tests/unit/`): No network, no external dependencies.
- **Security tests** (`tests/security/`): SSRF, target policy, dashboard hardening.
- **Integration tests** (`tests/`): End-to-end pipeline with mocked probes.
- **Network tests** (`@pytest.mark.network`): Opt-in, require internet access.

Run offline tests: `pytest -m "not network"`
