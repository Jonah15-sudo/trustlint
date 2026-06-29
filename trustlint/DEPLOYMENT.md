# TrustLint Deployment Guide

## Installation

### From PyPI (when published)
```bash
pip install trustlint
```

### From wheel
```bash
pip install trustlint-1.0.0-py3-none-any.whl
```

### From source
```bash
pip install -e .
```

### Optional dependencies
```bash
# CA store (Mozilla bundle)
pip install trustlint[ca-store]

# Kafka pipeline
pip install trustlint[kafka]

# SPL Core dashboard
pip install trustlint[spl-core]

# All extras
pip install trustlint[kafka,ca-store,spl-core]
```

## CLI Usage

```bash
# Single domain
trustlint example.com

# Batch from file
trustlint domains.txt --profile strict --json-out report.json

# Health check
trustlint --health

# List classifications
trustlint --list-classifications

# Version
trustlint --version
```

## Python API

```python
from trustlint import analyze, analyze_batch

# Single domain
result = analyze("example.com")
print(result["final"]["decision"])  # ALLOW, REVIEW, or DENY

# Batch
results = analyze_batch(["example.com", "google.com"])
print(results["summary"]["highest_risk"])
```

## Dashboard

```python
from spl_v7.dashboard import run_dashboard

# Local development (localhost only)
run_dashboard()

# Production (behind reverse proxy)
run_dashboard(host="0.0.0.0", port=8420, auth_token="your-secret-token")
```

### With environment variable
```bash
export TRUSTLINT_DASHBOARD_TOKEN="your-secret-token"
python -c "from spl_v7.dashboard import run_dashboard; run_dashboard()"
```

## Docker

### Development
```bash
docker compose -f docker-compose.kafka.yml up
```

### Production example
```bash
cp docker-compose.production.example.yml docker-compose.production.yml
# Edit docker-compose.production.yml with your settings
docker compose -f docker-compose.production.yml up -d
```

## Security Configuration

### SSRF Protection
- Default: all private/internal IPs blocked
- Allow internal scanning: `--allow-private-targets` (authorized scans only)
- OCSP requests use `SafeHttpClient` with outbound network policy

### Dashboard Security
- Default bind: 127.0.0.1 (localhost only)
- Auth: set `TRUSTLINT_DASHBOARD_TOKEN` env var
- CORS: restricted to specified origins
- Headers: CSP, X-Frame-Options, Cache-Control, etc.

## Reverse Proxy (Nginx)

```nginx
server {
    listen 443 ssl;
    server_name dashboard.example.com;

    location / {
        proxy_pass http://127.0.0.1:8420;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Resource Limits

| Limit | Value | Configurable |
|-------|-------|-------------|
| Max input file size | 10 MB | No |
| Max domains per batch | 10,000 | No |
| Max domain length | 253 chars | No |
| Probe timeout | 10s default | `--timeout` |
| Max response bytes | 1 MB | No |
