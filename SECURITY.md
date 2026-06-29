# TrustLint Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in TrustLint, please report it responsibly:

- **Do NOT** open a public GitHub issue for security vulnerabilities.
- Email security reports to: [SECURITY_EMAIL_PLACEHOLDER]
- Include: description, steps to reproduce, potential impact, suggested fix.

## Security Controls

### Network Security
- **SSRF Protection**: All outbound HTTP requests (including OCSP) are validated through `OutboundNetworkPolicy` before execution.
- **Target Scanning Policy**: Private, loopback, link-local, multicast, and reserved IP ranges are rejected by default. Use `--allow-private-targets` for authorized internal scans only.
- **DNS Validation**: Resolved IP addresses are re-validated after DNS resolution to prevent DNS rebinding attacks.

### Dashboard Security
- **Local-only default**: Dashboard binds to `127.0.0.1` by default.
- **Security headers**: CSP, X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy.
- **Token authentication**: Set `TRUSTLINT_DASHBOARD_TOKEN` environment variable for production.
- **CORS restrictions**: Only localhost origins allowed by default.
- **API redaction**: `/api/snapshot` returns redacted data (no internal graph topology).
- **XSS prevention**: All dynamic content is HTML-escaped.

### Input Validation
- **File size limit**: 10 MB maximum input file size.
- **Domain count limit**: 10,000 maximum domains per batch.
- **Domain length limit**: 253 characters (DNS specification).
- **Domain format validation**: Strict regex-based domain name validation.

### Kafka Security (Production)
- **No anonymous access**: Production requires SASL authentication.
- **TLS encryption**: Client-broker communication encrypted.
- **ACL authorization**: Role-based access control.
- **No auto topic creation**: Topics must be explicitly created.
- See `docker-compose.production.example.yml` for reference configuration.

### Concurrency Safety
- Bounded thread pool via `concurrent.futures.ThreadPoolExecutor`.
- Deterministic output ordering (results match input order).
- Per-domain error isolation (one failure doesn't abort the batch).
- No shared mutable state between worker threads.

## Known Limitations

- SPL Core is experimental and should not be used for production security decisions.
- OCSP checking is best-effort (dependent on responder availability).
- Deprecated TLS detection is not guaranteed (depends on OpenSSL negotiation).
- No IPv6 support in current TLS probing.

## Development vs Production

| Feature | Development | Production |
|---------|------------|------------|
| Dashboard auth | Disabled | Token required |
| Dashboard binding | localhost | Behind TLS proxy |
| Kafka | Anonymous, plaintext | SASL + TLS + ACL |
| TLS targets | Private allowed | Public only |
| SPL Core | Experimental | Disabled |

## Supply Chain

- Dependencies are managed in `pyproject.toml`.
- No secrets are committed to the repository.
- Docker images use slim base images with non-root users.
- Build artifacts are excluded from version control.
