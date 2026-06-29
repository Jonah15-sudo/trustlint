# SECURITY_CHALLENGE_REPORT.md

**Reviewer:** Adversarial Security Engineer
**Date:** 2026-06-09
**Verdict:** MULTIPLE SECURITY CONCERNS

---

## CRITICAL SECURITY FINDINGS

### 1. Certificate Verification Bypass in Chain Subtype Detection

```python
# scripts/run_local_tls_validation.py
def _determine_chain_subtype(domain: str, ip: str) -> str:
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((ip, DEFAULT_PORT), timeout=PROBE_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as tls:
                try:
                    chain = tls.get_verified_chain()
```

**`ssl.CERT_NONE` disables all certificate verification.** This is used to dump the certificate chain for analysis. While this is intentional for the probe, it means:

1. The code connects to arbitrary servers without verifying their identity
2. A MITM attacker can inject a fake certificate chain
3. The "chain_subtype" classification could be manipulated

**Impact:** Attacker can fake chain subtype classifications. The probe trusts any certificate chain when in this mode.

---

### 2. No Protection Against Certificate Pinning Bypass

The probe uses the system trust store:

```python
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.check_hostname = True
context.verify_mode = ssl.CERT_REQUIRED
context.load_default_certs()
```

But there's no option to use certificate pinning. If a domain has a pinned certificate that differs from the CA chain, the probe will report UNTRUSTED_CHAIN even though the pin is valid.

**Impact:** False positives on pinned certificates. Incorrect risk assessments.

---

### 3. No Protection Against DNS Rebinding

```python
def _resolve_domain(domain: str) -> Tuple[Optional[str], Optional[str]]:
    addrs = socket.getaddrinfo(domain, DEFAULT_PORT, socket.AF_INET, socket.SOCK_STREAM)
    if addrs:
        return addrs[0][4][0], None
```

The probe resolves DNS, then connects to the resolved IP. Between resolution and connection, the DNS record could change (DNS rebinding attack).

**Impact:** Attacker can make the probe connect to a different server than intended.

---

### 4. No Input Sanitization for Domain Names

```python
_DOMAIN_RE = re.compile(r"^([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")

def validate_domain_name(domain: str) -> Tuple[bool, str]:
    if not domain or len(domain) > 253:
        return False, "Domain is empty or exceeds 253 characters"
    if not _DOMAIN_RE.match(domain):
        return False, f"Invalid domain format: {domain!r}"
    return True, ""
```

The regex allows:
- Domains with hyphens (normal)
- Domains with digits (normal)
- But does NOT block:
  - IP addresses (e.g., `192.168.1.1`)
  - Localhost variations (e.g., `localhost.localdomain`)
  - Internal hostnames (e.g., `corp.internal`)

**Impact:** Can probe internal network hosts. Can probe IP addresses directly (bypassing DNS).

---

### 5. No Rate Limiting Enforcement

The `--rate-limit` flag is only applied in the main loop:

```python
if i < len(domains) - 1:
    _time.sleep(RATE_LIMIT_SECONDS)
```

But the flag defaults to 1.0 seconds. In batch mode with 1000 domains, that's 1000 seconds (~17 minutes).

More importantly, **there's no enforcement of minimum rate limits.** A user can set `--rate-limit 0` to scan as fast as possible.

**Impact:** Can be used for aggressive scanning. May violate acceptable use policies.

---

### 6. No Protection Against OCSP Stapling Forgery

The probe trusts the OCSP staple response:

```python
ocsp_result = check_ocsp(tls, domain)
info["ocsp_stapled"] = ocsp_result.get("ocsp_stapled", False)
info["ocsp_status"] = ocsp_result.get("ocsp_status")
```

If a server provides a forged OCSP staple, the probe trusts it.

**Impact:** Attacker can fake OCSP status by providing a forged staple.

---

### 7. No Protection Against TLS Downgrade Attacks

The probe negotiates whatever the server offers:

```python
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.check_hostname = True
context.verify_mode = ssl.CERT_REQUIRED
```

But there's no detection of TLS downgrade attacks (e.g., POODLE, DROWN).

**Impact:** Server can force a weak TLS version without detection.

---

### 8. No Secret Management

The codebase contains no secrets, but there's no secret management framework:

- No `.env` file handling
- No vault integration
- No credential rotation
- No secret scanning in CI

**Impact:** If secrets are added later, they may be committed accidentally.

---

### 9. No Dependency Vulnerability Scanning

No `safety`, no `pip-audit`, no Dependabot configuration.

**Impact:** Vulnerable dependencies may be introduced without detection.

---

### 10. No SBOM Generation

No Software Bill of Materials. No dependency tracking.

**Impact:** Cannot audit supply chain. Cannot track vulnerable components.

---

## HIGH SEVERITY FINDINGS

### 11. Export of Probe Results Without Sanitization

```python
json_path = os.path.join(REPORT_DIR, "tls_probe_results.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)
```

Probe results contain:
- IP addresses
- Certificate details
- OCSP responder URLs
- Error messages (which may contain sensitive information)

No sanitization. No redaction.

**Impact:** Sensitive information leaked in output files.

---

### 12. No TLS for OCSP Requests

The OCSP checker makes HTTP requests:

```python
# scripts/ocsp_checker.py (inferred)
# Uses http.client or urllib, not requests
```

OCSP requests are typically HTTP (not HTTPS). The response is signed, but the request itself is unencrypted.

**Impact:** OCSP requests can be intercepted. Request contents (which domain is being checked) are exposed.

---

### 13. No Protection Against Log Injection

```python
print(f"[{i + 1}/{len(domains)}] Probing {domain}...", end=" ", flush=True)
```

Domain names are printed directly. A malicious domain name could contain:
- Newline characters (`\n`)
- ANSI escape codes
- Control characters

**Impact:** Log injection. Terminal escape sequences. Fake log entries.

---

### 14. No File Permission Controls

Output files are created with default permissions:

```python
with open(args.json_out, "w", encoding="utf-8") as f:
    f.write(json_str)
```

No `os.umask()`. No explicit file permissions.

**Impact:** Output files may be world-readable. Sensitive probe results exposed.

---

### 15. No Protection Against Path Traversal in File Input

```python
def load_domains_from_file(path: str) -> List[str]:
    domains: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
```

No path validation. A user could pass `--file /etc/passwd` or `--file ../../../sensitive.txt`.

**Impact:** Can read arbitrary files (though this is a CLI tool, so the user has access anyway).

---

### 16. No Protection Against Prototype Pollution in JSON

```python
json.dump(results, f, indent=2, default=str)
```

`default=str` converts any object to string. This could mask errors.

**Impact:** Silent data corruption. Unexpected string representations.

---

### 17. No CORS Headers for Dashboard

The `spl_v7/dashboard.py` creates a FastAPI app:

```python
from spl_v7.dashboard import create_app
```

No CORS configuration. No authentication.

**Impact:** If the dashboard is exposed, it's vulnerable to CSRF.

---

### 18. No Authentication for Health Check

```bash
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD spl-tls-analyze --health --verbose || exit 1
```

Health check is unauthenticated. Anyone can trigger it.

**Impact:** Information disclosure. Resource exhaustion.

---

## MEDIUM SEVERITY FINDINGS

### 19. No Protection Against Unicode Domain Names

The domain validation regex only allows ASCII:

```python
_DOMAIN_RE = re.compile(r"^([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")
```

IDN (Internationalized Domain Names) are rejected. But punycode domains (e.g., `xn--...`) are accepted.

**Impact:** Cannot probe IDN domains. May miss phishing using IDN homographs.

---

### 20. No Protection Against Very Long Domain Names

```python
if not domain or len(domain) > 253:
    return False, "Domain is empty or exceeds 253 characters"
```

253 characters is the DNS limit, but the probe doesn't check individual label lengths (63 characters max).

**Impact:** May accept invalid domain names that DNS will reject.

---

### 21. No Protection Against Null Bytes

The regex doesn't check for null bytes:

```python
_DOMAIN_RE = re.compile(r"^([a-zA-Z0-9]...")
```

A domain like `example.com\0.evil.com` would pass validation but behave unexpectedly.

**Impact:** Potential injection in downstream processing.

---

## SUMMARY

| Severity | Count | Examples |
|----------|-------|---------|
| CRITICAL | 10 | Certificate verification bypass, DNS rebinding, no rate limiting |
| HIGH | 8 | No sanitization, log injection, no file permissions |
| MEDIUM | 3 | No IDN support, no label length check, no null byte protection |

**Overall Assessment:** The security posture is acceptable for a CLI tool run by a trusted user on their own machine. It is NOT acceptable for:
- Multi-user environments
- Automated pipelines
- Exposed services
- Untrusted input

**Recommendation:** Add input sanitization, add rate limiting enforcement, add file permissions, add secret scanning, add dependency vulnerability scanning, generate SBOM.
