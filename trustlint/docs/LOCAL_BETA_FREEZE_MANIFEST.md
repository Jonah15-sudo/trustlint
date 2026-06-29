# Local Beta Freeze Manifest

## Version

**0.3.2b0** (PEP 440 pre-release)

## Freeze Date

**2026-06-01**

## Test Count

**530 tests** across 21 test files. All pass.

Verified by:
```bash
python -m unittest discover -s tests -v
```

## Release Check Count

**14 checks** in `scripts/verify_release.py` (12 mandatory + 2 optional: Docker, VPS docs). All pass.

Verified by:
```bash
python scripts/verify_release.py
```

## Dogfood Result

**ALLOW=19 REVIEW=11 DENY=1** across 31 domains (balanced profile).

- 19 clean public domains ALLOW via balanced fallback
- 11 domains REVIEW (badssl risk cases + probe-limited DNS failures)
- 1 domain DENY (wrong.host.badssl.com — CRITICAL)
- 0 errors, 0 timeouts

## Package Name

**spl-tls-analyze**

## Console Command

```
spl-tls-analyze <domain> [<domain> ...] [options]
```

Entry point: `spl-tls-analyze = scripts.spl_tls_analyze:main`

## Supported Profiles

| Profile | Default | Fallback ALLOW | High Security Action |
|---------|---------|----------------|----------------------|
| balanced | **Yes** | Yes (clean VALID_TLS, no SPL) | REVIEW |
| conservative | No | No | REVIEW |
| strict | No | No | DENY |

## Stable Contracts

The following are guaranteed stable within the `0.3.0b0` release series:

### JSON Schema
- Output structure documented in [CLI_OUTPUT_SCHEMA.md](CLI_OUTPUT_SCHEMA.md)
- Field names, types, and nesting are stable
- New fields may be added but existing fields will not be removed or renamed

### Exit Codes
| Code | Meaning |
|------|---------|
| 0 | ALLOW |
| 1 | REVIEW |
| 2 | DENY |
| 3 | Error |
| 4 | Invalid arguments |

### CLI Command
- `spl-tls-analyze <domain> [<domain> ...]` is the stable invocation
- `--profile`, `--timeout`, `--quiet`, `--verbose`, `--json-out`, `--markdown-out` flags are stable

## Unstable / Non-Guaranteed Contracts

The following may change between beta versions without notice:

- **Console formatting** — text layout, section headers, alignment, color codes
- **Live probe behavior** — DNS resolution, handshake timing, transient failures are environmental
- **Deprecated TLS detection** — best-effort only, depends on OpenSSL negotiation
- **CRL/OCSP** — not implemented; no certificate revocation checking
- **Recommended action text** — deterministic per classification but wording may change
- **Supporting reasons text** — detail level and phrasing may change

## VPS Dry Run

A controlled VPS dry run is prepared (not a deployment):
- Guide: `docs/VPS_DRY_RUN.md`
- Dataset: `datasets/vps_dry_run_domains.txt` (15 domains)
- Script: `scripts/run_vps_dry_run.sh` (Linux) / `.ps1` (PowerShell)
- Report template: `docs/VPS_DRY_RUN_REPORT_TEMPLATE.md`

VPS dry run is **optional** — the CLI works locally and in Docker without
any VPS. See `docs/VPS_DRY_RUN.md` for full documentation.

## Docker

A Docker image is available for reproducible local execution:

```bash
docker build -t spl-tls-analyze:0.3.0b0 .
docker run --rm spl-tls-analyze:0.3.0b0 example.com
```

- No ports exposed
- No web server, no API, no dashboard
- Non-root user (`appuser`)
- CLI entry point only

Docker is **optional** — all functionality works directly with Python 3.10+.
See `docs/DOCKER_USAGE.md` for full documentation.

## Protected Boundaries

The following are explicitly protected and must not be modified:

### SPL Core (untouched)
- `spl_v7/` directory — never modified in any phase
- SPL evidence pipeline, DSL, and models are used as-is

### OFE Hold
- Optional field extraction is **observational only**
- Status: **HOLD_PENDING_REAL_DATA**
- Not used in any decision
- Not promoted or tuned

### No Production Readiness
- This is a local beta release
- Not published on PyPI
- Not intended for production security decisions
- ALLOW does not guarantee domain trustworthiness
