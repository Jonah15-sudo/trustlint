# TrustLint Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest release | Yes |
| Previous releases | No |

Only the latest released version receives security updates. Users are encouraged to upgrade promptly.

## Reporting a Vulnerability

If you discover a security vulnerability in TrustLint, please report it through [GitHub Security Advisories](https://github.com/trustlint/trustlint/security/advisories/new).

**Do not** open a public GitHub issue for security vulnerabilities.

### What to Include

- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact assessment
- Suggested fix (if available)

### What to Expect

- **Acknowledgment**: Within 48 hours of your report
- **Status update**: Within 7 days with an initial assessment
- **Resolution timeline**: Communicated after triage

We will work with you to understand and address the issue before any public disclosure.

## Scope

The following are in scope for security reports:

- Code execution vulnerabilities in the TrustLint package
- Injection attacks via domain input or file parsing
- Bypass of SSRF protections or target scanning restrictions
- Authentication or authorization issues in dashboard or API components
- Cryptographic issues in TLS probing or certificate validation logic

## Out of Scope

- Vulnerabilities in third-party dependencies (report these upstream)
- Issues requiring physical access to the target system
- Social engineering attacks
- Denial of service against TrustLint itself
- Issues in experimental or SPL Core features (marked as experimental)

## Security Considerations

### Network Security

- All outbound HTTP requests are validated through `OutboundNetworkPolicy`
- Private, loopback, link-local, multicast, and reserved IP ranges are rejected by default
- Resolved IP addresses are re-validated after DNS resolution to prevent DNS rebinding

### Input Validation

- Domain names are validated against a strict regex pattern
- Input file size is limited to 10 MB
- Batch processing is capped at 10,000 domains per run
- Domain length is limited to 253 characters per DNS specification

### Concurrency

- Thread pools are bounded via `concurrent.futures.ThreadPoolExecutor`
- Results maintain deterministic ordering matching input order
- Per-domain error isolation prevents single failures from aborting batches
- No shared mutable state exists between worker threads

## Disclosure Policy

We follow coordinated disclosure practices. Please allow reasonable time for a fix to be developed before public disclosure.

## Acknowledgments

We appreciate security researchers who report vulnerabilities responsibly.
