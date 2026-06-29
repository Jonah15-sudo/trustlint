# VPS Dry Run Report

## Metadata

- **Date:** YYYY-MM-DD
- **VPS Provider:** (e.g., Hetzner, DigitalOcean, Linode, AWS)
- **VPS Specs:** (e.g., 1 vCPU, 1 GB RAM, 10 GB SSD)
- **OS Version:** (e.g., Ubuntu 22.04 LTS)
- **Docker Version:** (e.g., Docker 24.0.7)
- **Image Tag:** spl-tls-analyze:0.3.0b0
- **Dataset:** datasets/vps_dry_run_domains.txt (15 domains)

## Command Run

```
docker run --rm \
  -v "$(pwd)/datasets:/app/datasets" \
  -v "$(pwd)/reports:/app/reports" \
  spl-tls-analyze:0.3.0b0 \
  /app/datasets/vps_dry_run_domains.txt \
  --json-out /app/reports/vps_dry_run/results.json \
  --markdown-out /app/reports/vps_dry_run/report.md
```

## Results

| Metric | Value |
|--------|-------|
| Total domains | 15 |
| ALLOW | _ |
| REVIEW | _ |
| DENY | _ |
| Highest risk | _ |
| Probe-limited | _ |
| Probe errors | _ |
| Runtime | _ |

## Comparison to Local Dogfood Baseline

| Metric | Local (expected) | VPS (actual) | Drift |
|--------|-----------------|--------------|-------|
| ALLOW | 8 | _ | _ |
| REVIEW | 6 | _ | _ |
| DENY | 1 | _ | _ |

## Errors

_List any probe errors, timeouts, or unexpected behavior._

## Limitations Observed

_Note any VPS-specific limitations (DNS differences, network latency,
OpenSSL version, etc.)._

## Conclusion

_Summarize whether the Docker local beta behaves consistently on the VPS
and note any corrective actions needed._
