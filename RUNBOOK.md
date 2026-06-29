# TrustLint Runbook

## Common Operations

### Run health check
```bash
trustlint --health
```
Expected: 7+ checks pass, 2 may fail (config/datasets directories).

### Analyze a single domain
```bash
trustlint example.com
```
Exit codes: 0=ALLOW, 1=REVIEW, 2=DENY, 3=error, 4=invalid args.

### Batch analysis
```bash
trustlint domains.txt --profile strict --json-out report.json --quiet
```

### List all classifications
```bash
trustlint --list-classifications
```

## Troubleshooting

### "No module named 'trustlint'"
```bash
pip install -e .
# or
pip install trustlint-1.0.0-py3-none-any.whl
```

### "probe_domain" import errors
The `probe_domain` function lives in `scripts/run_local_tls_validation.py` and is imported by `trustlint/analyzer.py`. If you see import errors, ensure the full repository is available (not just the `trustlint/` subdirectory).

### Dashboard won't start
```bash
# Install SPL Core extras
pip install trustlint[spl-core]

# Check if port is in use
lsof -i :8420

# Run with debug logging
python -c "import logging; logging.basicConfig(level=logging.DEBUG); from spl_v7.dashboard import run_dashboard; run_dashboard()"
```

### OCSP check fails
- OCSP responders may be unreachable from your network
- Check firewall rules for outbound HTTPS (port 443)
- Use `--ca-store certifi` if platform CA store is outdated

### SSRF protection blocks legitimate target
- Use `--allow-private-targets` for authorized internal scans only
- This flag weakens target restrictions — ensure you have authorization

## Monitoring

### Health endpoint
```bash
curl http://127.0.0.1:8420/health
# {"status": "ok"}
```

### Readiness endpoint
```bash
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8420/ready
# {"status": "ready"}
```

### API snapshot
```bash
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8420/api/snapshot
```

## Emergency Procedures

### Revoke access
```bash
unset TRUSTLINT_DASHBOARD_TOKEN
# Restart dashboard
```

### Check for compromised dependencies
```bash
pip audit
# Review sbom.json for known vulnerabilities
```

### Export audit trail
```bash
# Analysis results are in JSON/JSONL files
# Dashboard logs are in stderr
trustlint domains.txt --json-out audit-$(date +%Y%m%d).json
```

## Performance Tuning

### Batch scanning
```bash
# Sequential (default)
trustlint domains.txt

# Concurrent (4 workers)
trustlint domains.txt --workers 4

# With rate limiting
trustlint domains.txt --workers 4 --rate-limit 0.5
```

### Resource constraints
- Each probe uses ~10s timeout (configurable via `--timeout`)
- Memory: ~50MB per concurrent worker
- Network: one TCP connection per probe
