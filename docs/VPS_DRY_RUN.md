# VPS Dry Run — spl-tls-analyze

## Overview

This guide describes how to run the `spl-tls-analyze` Dockerized CLI on a
low-cost VPS for a controlled, non-public, file-based dry run.

**This is not production deployment.** No ports are exposed, no web server
is started, no API is created, no domain or HTTPS is required.

## VPS Requirements

| Resource | Recommended Minimum |
|----------|-------------------|
| vCPU     | 1                  |
| RAM      | 1 GB               |
| Disk     | 10 GB              |
| OS       | Ubuntu 22.04 LTS   |
| Docker   | 24+                 |

Low-cost options: Hetzner CX22 (~4 EUR/mo), DigitalOcean Basic Droplet
(~6 USD/mo), Linode Nanode 1 GB (~5 USD/mo), AWS t2.micro (free tier).

## OS Assumptions

- Ubuntu 22.04 LTS (or 24.04 LTS)
- `docker` and `git` installed
- User has `sudo` access

## Docker Install (if not present)

```bash
# Official Docker install script (Ubuntu)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

## Copy or Clone the Project

```bash
# Option A: Clone from git (if repo is accessible)
git clone <repo-url> spl-tls-analyze
cd spl-tls-analyze

# Option B: Copy archive from local machine
# On local machine:
#   cd spl_v7_project_with_frontier/spl_v7_project
#   python scripts/verify_release.py   # confirm clean
#   cd ..
#   tar czf spl-tls-analyze.tar.gz spl_v7_project
#   scp spl-tls-analyze.tar.gz user@vps-ip:~/
# On VPS:
#   tar xzf spl-tls-analyze.tar.gz
#   cd spl_v7_project
```

## Build the Docker Image

```bash
cd spl_v7_project_with_frontier/spl_v7_project
docker build -t spl-tls-analyze:0.3.0b0 .
```

## Run Single-Domain Analysis

```bash
docker run --rm spl-tls-analyze:0.3.0b0 google.com
docker run --rm spl-tls-analyze:0.3.0b0 expired.badssl.com --profile strict
docker run --rm spl-tls-analyze:0.3.0b0 wrong.host.badssl.com --verbose
```

## Run File-Based Dry Run Dataset

The project includes a small dry-run dataset at
`datasets/vps_dry_run_domains.txt` (15 domains):

```bash
docker run --rm \
  -v "$(pwd)/datasets:/app/datasets" \
  spl-tls-analyze:0.3.0b0 \
  /app/datasets/vps_dry_run_domains.txt
```

Expected output: roughly **8-10 ALLOW, 4-6 REVIEW, 1 DENY** depending on
network conditions and DNS resolution.

## Mount Reports Directory

```bash
mkdir -p reports/vps_dry_run

docker run --rm \
  -v "$(pwd)/datasets:/app/datasets" \
  -v "$(pwd)/reports:/app/reports" \
  spl-tls-analyze:0.3.0b0 \
  /app/datasets/vps_dry_run_domains.txt \
  --json-out /app/reports/vps_dry_run/results.json \
  --markdown-out /app/reports/vps_dry_run/report.md
```

## Retrieve Reports from VPS

```bash
# From local machine:
scp -r user@vps-ip:~/spl_v7_project_with_frontier/spl_v7_project/reports/vps_dry_run/ ./vps_dry_run_results/
```

## Run the Dry Run Script

The project includes an automated script:

```bash
chmod +x scripts/run_vps_dry_run.sh
./scripts/run_vps_dry_run.sh
```

This builds the image, runs the dataset, writes reports to
`reports/vps_dry_run/`, and prints a summary.

## Expected Results

Based on local dogfood testing (Phase 13-15):

| Category | Expected Count |
|----------|---------------|
| ALLOW    | 8              |
| REVIEW   | 6              |
| DENY     | 1              |

Note: `revoked.badssl.com` is excluded from the dry-run dataset because
the CLI lacks CRL/OCSP checking and would produce a misleading ALLOW.

## Clean Up

```bash
# Remove containers (should not be running, but safe to clean)
docker container prune -f

# Remove the image (if no longer needed)
docker rmi spl-tls-analyze:0.3.0b0

# Remove project files (from VPS)
rm -rf ~/spl_v7_project_with_frontier
```

## Security Notes

- The container runs as non-root (`appuser`).
- No ports are exposed — the container has no `EXPOSE` directive.
- The CLI only makes outbound TLS connections to the probed domains.
- The container has no inbound listeners.
- Output files in mounted volumes are owned by UID 1000 (appuser).
- Do not run against domains you do not own or have permission to probe.
- Do not run large-scale or aggressive scans.

## Not Production Deployment

This VPS dry run is for **controlled, non-public testing only**. It is not:

- A production security scanner
- A monitoring service
- A public API
- A web dashboard
- A VPS deployment

The Docker image contains only the `spl-tls-analyze` CLI. No ports, no
services, no web server, no API. See `docs/KNOWN_LIMITATIONS.md` and
`docs/DOCKER_USAGE.md`.

## Compare Results to Local

To compare VPS results against local results, run the same dataset locally:

```bash
docker run --rm \
  -v "$(pwd)/datasets:/app/datasets" \
  -v "$(pwd)/reports:/app/reports" \
  spl-tls-analyze:0.3.0b0 \
  /app/datasets/vps_dry_run_domains.txt \
  --json-out /app/reports/vps_dry_run_local/results.json
```

Then diff the JSON output:

```bash
diff reports/vps_dry_run/results.json reports/vps_dry_run_local/results.json
```

Some differences are expected due to:
- DNS resolution differences (VPS vs local network)
- Network latency / timeout differences
- OpenSSL version differences in the Docker image
