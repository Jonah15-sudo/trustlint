# TrustLint Threat Model

## Overview

TrustLint is a TLS risk analysis tool that probes domains for certificate validity, protocol configuration, and revocation status. This document describes the security boundaries, trust assumptions, and known risks.

## Trust Boundaries

### 1. Network Boundary
- **TrustLint runs on the operator's machine** — it is NOT a network service
- All TLS probes originate from the operator's network
- No inbound network ports are opened (dashboard binds to 127.0.0.1 by default)

### 2. Data Boundary
- Probe results are stored locally in JSON/JSONL files
- No data is sent to external services (except OCSP responders for revocation checks)
- Dashboard data is redacted — internal graph topology is never exposed via API

### 3. Code Boundary
- `trustlint/` package is the public API — no imports from `scripts/`
- `scripts/` are CLI wrappers that import from `trustlint/`
- Security controls live in `trustlint/security/` — enforced at every outbound request

## Threat Actors

| Actor | Capability | Mitigation |
|-------|-----------|------------|
| Malicious domain owner | Craft TLS responses to exploit parser bugs | Input validation, timeout limits, response size caps |
| Network attacker | MITM TLS connections | OCSP stapling verification, chain validation |
| SSRF attacker | Trick TrustLint into scanning internal services | OutboundNetworkPolicy blocks private IPs, loopback, link-local, metadata endpoints |
| XSS attacker | Inject scripts into dashboard | HTML escaping, CSP headers, frame-ancestors 'none' |

## SSRF Protection

### Layers
1. **TargetScanPolicy** — blocks scanning of private/internal IPs
2. **OutboundNetworkPolicy** — blocks outbound HTTP to restricted IPs
3. **SafeHttpClient** — enforces timeouts, response size limits, no redirects

### Known Gaps
- DNS resolution failure causes `validate_url` to silently pass (documented trade-off)
- OCSP responders are contacted over the network — a compromised OCSP responder could return false revocation status
- `--allow-private-targets` weakens target restrictions for authorized internal scans only

## Dashboard Security

- Binds to 127.0.0.1 by default (localhost only)
- Optional bearer token authentication
- CORS restricted to specified origins
- Security headers: CSP, X-Frame-Options, X-Content-Type-Options, Cache-Control
- API responses are redacted — no internal graph details exposed
- Swagger/ReDoc disabled in production

## Supply Chain

- Zero runtime dependencies (core package)
- Optional dependencies: `certifi`, `confluent-kafka`, `numpy`, `plotly`, `networkx`, `fastapi`, `uvicorn`
- SBOM generated via `cyclonedx-py` — see `sbom.json`
- Dependency lock file: `requirements-lock.txt`

## Out of Scope

- Protecting against compromised DNS resolvers
- Validating OCSP responder certificates (trusts platform CA store)
- Protecting against side-channel attacks on TLS probing
- Real-time monitoring or alerting
