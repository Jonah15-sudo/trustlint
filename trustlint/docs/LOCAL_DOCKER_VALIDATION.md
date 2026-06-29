# Local Docker Validation Guide

Run the full SPL v7.1 validation pipeline locally using Docker — no domain, VPS, Let's Encrypt, or cloud infrastructure required.

## Prerequisites

- Docker Engine 24+ (with BuildKit support)
- Python 3.11+ (for local non-Docker runs)
- Internet connection (for real TLS probing)

## Project Structure

```
spl_v7_project/
├── Dockerfile                        # Container image definition
├── datasets/real_tls_seed_domains.txt # Editable seed domain list
├── scripts/run_local_tls_validation.py # Local TLS probe runner
├── reports/local_real_validation/     # Probe output directory
├── docs/LOCAL_DOCKER_VALIDATION.md    # This file
├── Makefile                           # Convenience targets
├── requirements.txt
└── pyproject.toml
```

## 1. Build the Container

```bash
# From the spl_v7_project/ directory:
docker build -t spl-v7:local .

# Verify:
docker images spl-v7:local
```

Expected: image `spl-v7:local` with tag `local`.

## 2. Run the Test Suite (inside container)

```bash
# Run unit tests and compileall:
docker run --rm spl-v7:local python -m pytest tests/ -v --tb=short
docker run --rm spl-v7:local python -m compileall -q spl_v7 experiments scripts
```

Run specific test file:

```bash
docker run --rm spl-v7:local python -m pytest tests/test_real_validation_runner.py -v --tb=short
```

## 3. Run Local TLS Real-Data Validation

Probe the seed domain list, validate TLS certificates, and generate reports:

```bash
# Build the image first (see section 1), then:
docker build -t spl-v7:local .
docker run --rm -v "%CD%/reports:/app/reports" spl-v7:local python scripts/run_local_tls_validation.py datasets/real_tls_seed_domains.txt

# On Linux/macOS:
# docker run --rm -v "$(pwd)/reports:/app/reports" spl-v7:local python scripts/run_local_tls_validation.py datasets/real_tls_seed_domains.txt
```

Output is written to `reports/local_real_validation/` (on the host via bind mount).

## 4. Export Reports

Reports are automatically saved to `reports/local_real_validation/`:

- `REAL_DATA_LOCAL_REPORT.md` — Evidence report with findings
- `tls_probe_results.json` — Raw probe results (structured JSON)
- `tls_probe_results.jsonl` — Probe results in JSONL format (one JSON object per domain)

To copy reports from a container without a bind mount:

```bash
# Run without mount:
docker run --name spl-v7-run --rm spl-v7:local python scripts/run_local_tls_validation.py datasets/real_tls_seed_domains.txt

# Copy reports out:
docker cp spl-v7-run:/app/reports/local_real_validation ./reports/local_real_validation
```

## 5. Run Full Validation Pipeline (synthetic)

The full A/B campaign runner (`RealValidationRunner`) requires a 5000+ row dataset and is designed for batch analysis of pre-collected data:

```bash
docker run --rm -v "%CD%/reports:/app/reports" spl-v7:local python -m experiments.real_validation_runner /app/examples/real_tls_sample.jsonl 1 --verbose
```

Note: The sample fixture (`real_tls_sample.jsonl`) is rejected by the runner. Provide a real 5000+ row dataset to use this pipeline.

## 6. Local Non-Docker Run

If Python 3.11+ is installed:

```bash
# Install:
pip install -e .

# Run tests:
python -m pytest tests/ -v --tb=short
python -m compileall -q spl_v7 experiments scripts

# Run local TLS validation:
python scripts/run_local_tls_validation.py datasets/real_tls_seed_domains.txt
```

## Commands Quick Reference

| Action | Command |
|--------|---------|
| Build | `docker build -t spl-v7:local .` |
| Tests | `docker run --rm spl-v7:local python -m pytest tests/ -v --tb=short` |
| Compile check | `docker run --rm spl-v7:local python -m compileall -q spl_v7 experiments scripts` |
| Real TLS probe | `docker run --rm -v "%CD%/reports:/app/reports" spl-v7:local python scripts/run_local_tls_validation.py datasets/real_tls_seed_domains.txt` |
| Interactive shell | `docker run --rm -it --entrypoint bash spl-v7:local` |
| Cleanup | `docker rmi spl-v7:local` |

## Known Limitations

- Local TLS probes do not maintain a persistent certificate store.
- Rate limiting is conservative (1 second between probes by default).
- DNS failures and timeouts are expected for some domains — the runner handles them gracefully.
- The seed dataset is manually curated and should be reviewed/edited by the user.
- No production claims are made. This is a zero-budget evidence-gathering path.

## Success Criteria

- [ ] Container builds without errors
- [ ] Test suite passes (all tests green)
- [ ] `compileall` passes (no syntax/import errors)
- [ ] Real TLS seed dataset is processed (50-100 domains probed)
- [ ] Reports are generated in `reports/local_real_validation/`
- [ ] Failures (timeout, DNS, bad cert) are handled without crash
- [ ] No SPL Core modifications (spl_v7/ is untouched)
