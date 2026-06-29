# Release Checklist

## Pre-Release Verification

- [ ] **No SPL Core modifications** — verify `spl_v7/` has no changes since baseline
- [ ] **No stale artifacts** — check for leftover `reports/`, `__pycache__/`, `*.pyc`
- [ ] **Full test suite passes** — `python -m unittest discover -s tests -v` — expect 557 tests
- [ ] **Compileall clean** — `python -m compileall -q spl_v7 experiments scripts tests tls_policy_adapter decision_orchestrator`
- [ ] **Golden acceptance tests pass** — `python -m pytest tests/test_cli_golden_acceptance.py -v`
- [ ] **Release verification script passes** — `python scripts/verify_release.py` (13 checks)
- [ ] **Version consistency** — version `0.3.0b0` consistent in pyproject.toml, VERSIONING.md, release notes, freeze manifest
- [ ] **Release notes exist** — `docs/RELEASE_NOTES_0.3.0b0.md` accurate
- [ ] **Freeze manifest exists** — `docs/LOCAL_BETA_FREEZE_MANIFEST.md` accurate
- [ ] **OFE remains HOLD_PENDING_REAL_DATA** — confirm in docs and orchestrator code
- [ ] **No production readiness claim** — verify all docs state local-only scope
- [ ] **README is accurate** — quickstart commands work from fresh checkout
- [ ] **CLI examples are accurate** — run through `docs/CLI_EXAMPLES.md` examples
- [ ] **Known limitations documented** — `docs/KNOWN_LIMITATIONS.md` is up to date
- [ ] **Package metadata complete** — verify `pyproject.toml` has name, version, entry point
- [ ] **Console entry point works** — run `spl-tls-analyze --help`
- [ ] **Editable install documented** — `docs/INSTALL.md` has working instructions
- [ ] **Versioning documented** — `docs/VERSIONING.md` is accurate
- [ ] **Dogfood report is current** — `reports/dogfood/DOGFOOD_REPORT.md` reflects latest CLI behavior
- [ ] **Dogfood findings documented** — `docs/DOGFOOD_FINDINGS.md` is up to date
- [ ] **Docker build works** — `docker build -t spl-tls-analyze:0.3.0b0 .`
- [ ] **Docker smoke tests pass** — `python -m pytest tests/test_docker_docs.py -v`
- [ ] **Docker usage docs** — `docs/DOCKER_USAGE.md` has accurate commands
- [ ] **Docker is optional** — image does not expose ports or run services
- [ ] **VPS dry-run guide exists** — `docs/VPS_DRY_RUN.md`
- [ ] **VPS dry-run dataset exists** — `datasets/vps_dry_run_domains.txt` (15 domains)
- [ ] **VPS dry-run script exists** — `scripts/run_vps_dry_run.sh`
- [ ] **VPS dry-run report template exists** — `docs/VPS_DRY_RUN_REPORT_TEMPLATE.md`
- [ ] **VPS dry-run is not a deployment** — no ports, no services, no API, no web server

## CI Gate

Before merging to master:

1. CI must show green for all steps
2. Full test suite passes
3. Compileall clean
4. Golden fixture snapshots match (no output drift)
5. SPL Core integrity check passes
6. OFE status confirms `HOLD_PENDING_REAL_DATA`
7. No production readiness claim in any doc
8. Docker docs integrity check passes (if Docker available)
9. VPS dry-run documentation checks pass (file integrity only)

## Post-Release

- [ ] Archive created (`.zip` excluding `.git`, `__pycache__`, `.pytest_cache`)
- [ ] Archive verified on clean machine using `scripts/verify_release.py`
- [ ] `real_tls_dataset_NOT_FOUND.md` included if dataset is still missing

## Key Constraints

- SPL Core is **never modified** in any phase.
- OFE remains **observational only** (`HOLD_PENDING_REAL_DATA`).
- The CLI is **local-only** — no dashboard, no public API, no VPS, no deployment.
- The package (`spl-tls-analyze` `0.3.0b0`) is **published on PyPI as a pre-release**.
- No synthetic data is claimed as real.
- Deprecated TLS detection is best-effort only.
