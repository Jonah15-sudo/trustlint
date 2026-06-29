# Artifact Integrity Audit — spl-tls-analyze v0.1.0b0

**Date:** 2026-06-03
**Scope:** Package definitions, build artifacts, Docker context, distribution paths, orphaned files.
**Variants audited:**
- `spl_v7_project_with_frontier/spl_v7_project/` (complete)
- `spl_v7_project/` (slim)

---

## 1. Package Declaration Verification

### 1.1 Declared vs Actual Packages

`pyproject.toml` declares 7 packages under `[tool.setuptools]`:

| Package | Complete Variant | Slim Variant |
|---------|:----------------:|:------------:|
| `decision_orchestrator` | ✅ | ✅ |
| `scripts` | ✅ | **❌ MISSING** |
| `spl_v7` | ✅ | **❌ MISSING** |
| `tls_policy_adapter` | ✅ | **❌ MISSING** |
| `weakness_mapper` | ✅ | **❌ MISSING** |
| `frontier` | ✅ | ✅ |
| `experiments` | ✅ | ✅ |

**Complete variant:** 7/7 packages present.
**Slim variant:** 3/7 packages present. Installation fails with:

```
error: Multiple top-level packages discovered in a flat-layout: [...]
```

### 1.2 `__init__.py` Export Agreement

Every package's `__init__.py` exports only symbols that actually exist in its submodules. Verified for:

| Package | `__init__.py` exports | All exports resolvable? |
|---------|----------------------|:----------------------:|
| `spl_v7` | 19 symbols | ✅ |
| `frontier` | 4 symbols | ✅ |
| `weakness_mapper` | 5 symbols | ✅ |
| `tls_policy_adapter` | 15 symbols | ✅ |
| `decision_orchestrator` | 11 symbols | ✅ |
| `experiments` | 3 symbols | ✅ |
| `scripts` | package marker only | ✅ |

### 1.3 Cross-Package Import Verification

| Import Chain | Resolves? |
|---|---|
| `scripts.spl_tls_analyze` → `scripts.run_local_tls_validation` | ✅ |
| `scripts.spl_tls_analyze` → `tls_policy_adapter` | ✅ |
| `scripts.spl_tls_analyze` → `decision_orchestrator` | ✅ |
| `tls_policy_adapter.evidence_adapter` → `tls_policy_adapter.schema` | ✅ |
| `decision_orchestrator.policy` → `decision_orchestrator.schema` | ✅ |
| `spl_v7.__init__` → `spl_v7.dashboard` | ✅ (but requires `numpy`, `networkx`, `plotly`, `fastapi`) |
| `frontier.session` → `spl_v7.utils`, `spl_v7.schema` | ✅ |
| `experiments.experiment_runner` → `spl_v7.*` | ✅ |

---

## 2. Console Entry Point Verification

### 2.1 Entry Point Declaration

**File:** `pyproject.toml` line 24-25
```toml
[project.scripts]
spl-tls-analyze = "scripts.spl_tls_analyze:main"
```

**Installed entry point** (from `spl_tls_analyze.egg-info/entry_points.txt`):
```
[console_scripts]
spl-tls-analyze = scripts.spl_tls_analyze:main
```

### 2.2 Entry Point Validation

| Check | Complete | Slim |
|---|---|---|
| Module `scripts.spl_tls_analyze` exists | ✅ | ❌ |
| Function `main()` exists in module | ✅ (line 565) | N/A |
| Function `main()` returns `int` | ✅ | N/A |
| `pyproject.toml` entry matches module path | ✅ | ✅ (file missing) |
| Egg-info matches pyproject.toml | ✅ | N/A |

### 2.3 Script Executability

All 14 scripts in `scripts/` have `if __name__ == "__main__"` blocks. They are designed to be run as `python scripts/<name>.py`. However:

| Script | Run via `python` | Run via console script | Notes |
|---|---|---|---|
| `spl_tls_analyze.py` | ✅ | ✅ `spl-tls-analyze` | Main CLI |
| `verify_release.py` | ✅ | ❌ no entry point | Must use `python scripts/verify_release.py` |
| All `run_*.py` scripts | ✅ | ❌ no entry points | 10 scripts, no console entries |
| `validate_*.py` | ✅ | ❌ no entry point | Data validation script |

---

## 3. Docker Build Context Analysis

### 3.1 Dockerfile Structure

```
FROM python:3.10-slim                     # Base: 120 MB
ENV PYTHONDONTWRITEBYTECODE=1             # Good practice
ENV PYTHONUNBUFFERED=1                    # Good practice
WORKDIR /app
COPY pyproject.toml README.md ./          # Build metadata
COPY decision_orchestrator/ ...           # Source packages (7 of 7)
COPY datasets/ ./datasets                 # Domain data
RUN pip install --no-cache-dir .          # Install (no extras!)
RUN adduser --disabled-password appuser   # Non-root
USER appuser
ENTRYPOINT ["spl-tls-analyze"]
CMD ["--help"]
```

### 3.2 Files Copied into Docker Image

| Source Dir | Copied? | Needed? |
|---|---|---|
| `pyproject.toml` | ✅ | Build metadata |
| `README.md` | ✅ | readme field in pyproject |
| `decision_orchestrator/` | ✅ | Runtime |
| `scripts/` | ✅ | Entry point + CLI |
| `tls_policy_adapter/` | ✅ | Runtime |
| `spl_v7/` | ✅ | Runtime |
| `weakness_mapper/` | ✅ | Runtime |
| `frontier/` | ✅ | Runtime |
| `experiments/` | ✅ | Runtime |
| `datasets/` | ✅ | Domain data files |
| `tests/` | **❌ NOT COPIED** | Needed for `docker-test` |
| `examples/` | **❌ NOT COPIED** | Demo |
| `docs/` | **❌ NOT COPIED** | Not needed at runtime |
| `Makefile` | **❌ Ignored by .dockerignore** | Not needed |

### 3.3 `.dockerignore` Exclusions (from Docker build context)

| Ignored Item | Impact |
|---|---|
| `.git/`, `.github/` | No git metadata in image |
| `__pycache__/`, `*.pyc`, `.pytest_cache/` | No bytecode (correct) |
| `.venv/`, `venv/` | No virtual envs (correct) |
| `*.egg-info/`, `build/`, `dist/` | No build artifacts (correct) |
| `.env`, `.env.example` | No secrets/env files (correct) |
| `reports/`, `reports_smoke/` | No stale reports (correct) |
| `dashboard.html` | Generated HTML not needed |
| `v71_graph_snapshot.json`, `capability_report.json` | Generated artifacts |
| `docker-compose.kafka.yml`, `Makefile` | Not needed at runtime |
| Project markdown docs (PROJECT_MAP.md, etc.) | Not needed at runtime |
| `Dockerfile`, `.dockerignore` | Not needed in image |

**Conclusion:** The Docker build context excludes everything it should. Only runtime source, data, and metadata are included.

### 3.4 Missing Pieces

| File/Dir | Missing from Image? | Impact |
|---|---|---|
| `tests/` | **NOT COPIED** | `docker run --rm spl-v7:local python -m pytest tests/` fails |
| `examples/demo.py` | **NOT COPIED** | Cannot run demo inside Docker |
| `docs/` | **NOT COPIED** | Cannot read docs inside container (expected) |

---

## 4. docker-test Workflow Analysis

### 4.1 Makefile Target

```makefile
docker-test:
    docker run --rm spl-v7:local python -m pytest tests/ -v --tb=short
```

### 4.2 Verification

| Step | Expectation | Actual | Status |
|---|---|---|---|
| Docker build succeeds | Image built | ✅ Succeeds | ✅ |
| `tests/` directory in image | Tests available | **❌ Not copied** (not in Dockerfile) | ❌ |
| `pytest` installed in image | Runs tests | **❌ Not installed** (`pip install .` has no `[dev]` extra) | ❌ |
| `spl-core` deps available | `import spl_v7` works | **❌ Not installed** (`pip install .` has no `[spl-core]` extra) | ❌ |

**Result: `make docker-test` always fails because:**
1. `tests/` is not copied into the Docker image
2. `pytest` is not installed (no `[dev]` extra)
3. `numpy`/`networkx`/`plotly`/`fastapi` are not installed (no `[spl-core]` extra)

The Dockerfile's `pip install --no-cache-dir .` installs only the base package with `dependencies = []`.

### 4.3 Fix Options

| Option | Change |
|---|---|
| A. Fix Dockerfile + make | Copy `tests/`, install `.[dev]` or `.[spl-core,dev]` |
| B. Fix make target only | Run `pip install pytest` + copy tests in Dockerfile |
| C. Document as known limitation | Update `docs/DOCKER_USAGE.md` and Makefile to note this |

---

## 5. `spl_v7_project/` (Slim Variant) Classification

### 5.1 What Exists

The slim variant contains:
- Build metadata (`pyproject.toml`, `Dockerfile`, `Makefile`, `.dockerignore`, `.gitignore`)
- CI config (`.github/workflows/ci.yml`)
- Pipeline configs (`configs/`)
- Datasets (`datasets/`)
- Documentation (`docs/` — 39 of 40 files)
- Decision Orchestrator (`decision_orchestrator/`)
- Frontier (`frontier/`)
- Experiments (`experiments/`)
- Generated outputs (`v71_graph_snapshot.json`, `capability_report.json`, `dashboard.html`)
- Empty `reports/dogfood/` directory

### 5.2 What is Missing

| Missing | Count | Criticality |
|---|---|---|
| `scripts/` (CLI entry point) | 26 files | **BLOCKING** |
| `spl_v7/` (core library) | 8 files + pyc | **BLOCKING** |
| `tls_policy_adapter/` | 4 files + pyc | **BLOCKING** |
| `weakness_mapper/` | 6 files + pyc | **BLOCKING** |
| `tests/` (test suite) | 75 files | High |
| `reports/local_real_validation/` | 31 files | Low (generated) |
| `reports_smoke/` | 2 files | Low (generated) |
| Example data (`examples/real_tls_sample.jsonl`) | 1 file | Medium |
| `.env.example` | 1 file | Low |

### 5.3 Classification: **DEPRECATED**

**Rationale:**
1. **Cannot build or install.** `pip install .` fails because 4 of 7 declared packages are missing. The CLI entry point `scripts.spl_tls_analyze:main` has no target module.
2. **Cannot run tests.** `testpaths = ["tests"]` has no target directory.
3. **100% subset.** Every file in `spl_v7_project/` exists in the complete variant with identical content. There are zero unique files.
4. **Empty `reports/dogfood/`** directory suggests no local validation was run.
5. The project was likely a pruning attempt that left the critical source directories behind.

**Recommendation:** Remove the top-level `spl_v7_project/` directory. It serves no purpose and will confuse new contributors who try to install from it.

---

## 6. Orphaned File Audit

### 6.1 `requirements.txt` (144 bytes)

| Property | Value |
|---|---|
| Location | Root |
| Contents | numpy, plotly, networkx, fastapi, uvicorn; optional confluent-kafka |
| Referenced by | **Nothing** |
| Duplicates | `[project.optional-dependencies] spl-core` in `pyproject.toml` |
| Status | **ORPHANED** |

**Recommendation:** Either:
- Remove `requirements.txt` (duplicates `pyproject.toml` extras)
- Or update it to reference `pyproject.toml` and add a comment:
  ```
  # This file is informational only. Use: pip install ".[spl-core]"
  ```

### 6.2 `dashboard.html` (51 KB)

| Property | Value |
|---|---|
| Location | Root |
| Contents | Generated HTML dashboard from `spl_v7.dashboard.build_dashboard_html()` |
| Source | Generated by `examples/demo.py` |
| Git-tracked? | No (in `.gitignore`: line `dashboard.html`) |
| Status | **GENERATED ARTIFACT (should not be tracked)** |

**Recommendation:** If tracked, remove from git. If untracked, add to `.dockerignore` (already done) and ignore in CI.

### 6.3 `v71_graph_snapshot.json` (144 KB)

| Property | Value |
|---|---|
| Location | Root |
| Contents | Causal graph snapshot from demo pipeline run |
| Source | Generated |
| Status | **GENERATED ARTIFACT (large, should not be tracked)** |

**Recommendation:** Already in `.dockerignore`. Consider adding to `.gitignore` if not already.

### 6.4 `capability_report.json` (10 KB — slim) / (~395 lines — complete)

| Property | Value |
|---|---|
| Location | Root |
| Contents | Weakness/capability mapping report |
| Source | Generated by `scripts/run_weakness_mapper.py` |
| Status | **GENERATED ARTIFACT** |

**Recommendation:** Add to `.gitignore` and `.dockerignore` (already in `.dockerignore`).

### 6.5 `reports/` and `reports_smoke/` Directories

| Directory | Source | Status |
|---|---|---|
| `reports/dogfood/` | Generated by dogfood run | Generated |
| `reports/local_real_validation/` | Generated by validation runs | Generated |
| `reports_smoke/` | Generated by smoke tests | Generated |

These are gitignored via `.gitignore`: `reports/real_data_validation/` and `reports/local_real_validation/` — but not the parent `reports/` directory. The `.gitignore` pattern only covers subdirectories, not `reports/` itself.

**Recommendation:** Ensure all generated reports are explicitly gitignored.

### 6.6 `.env.example` (140 bytes)

| Property | Value |
|---|---|
| Location | Root |
| Contents | SPL_V7_CONFIG, SPL_V7_FEATURE_DSL, SPL_V7_DASHBOARD_HOST, SPL_V7_DASHBOARD_PORT |
| Referenced by | Various scripts |
| Status | **ACTIVE** (template for `.env`) |

Not orphaned — legitimate template file.

### 6.7 `examples/real_tls_sample.jsonl` (1.4 KB)

| Log | Value |
|---|---|
| Location | `examples/` |
| Contents | Sample TLS evidence data in JSONL format |
| Used by | `examples/demo.py` |
| Status | **ACTIVE** |

Not orphaned.

### 6.8 Legacy/Redundant Files

| File | Issue |
|---|---|
| `PROMOTION_READINESS.md` (root) | Duplicates `reports_smoke/PROMOTION_READINESS.md` (slightly different content) |
| `REPLICATION_REPORT.md` (root) | Duplicates `reports_smoke/REPLICATION_REPORT.md` (slightly different content) |
| `RELEASE_CHECKLIST.md` (root) | Duplicates `docs/RELEASE_CHECKLIST.md` (same content, different sizes) |

**Recommendation:** Deduplicate root-level docs that have copies in `docs/` or `reports_smoke/`. The root copies are likely remnants from before the docs/reports directories were created.

### 6.9 Orphaned Shell Scripts (Windows Incompatibility)

| Script | Windows Compatible? | Notes |
|---|---|---|
| `scripts/run_dashboard.sh` | ❌ (bash) | No `.ps1` equivalent |
| `scripts/run_demo.sh` | ❌ (bash) | No `.ps1` equivalent |
| `scripts/run_kafka.sh` | ❌ (bash) | No `.ps1` equivalent |
| `scripts/run_tests.sh` | ❌ (bash) | No `.ps1` equivalent |
| `scripts/run_vps_dry_run.sh` | ❌ (bash) | Has `.ps1` equivalent ✅ |
| `scripts/run_docker_dogfood.ps1` | ✅ (PowerShell) | No `.sh` equivalent |
| `scripts/run_vps_dry_run.ps1` | ✅ (PowerShell) | Has `.sh` equivalent ✅ |
| `scripts/generate_golden_fixtures.ps1` | ✅ (PowerShell) | No `.sh` equivalent |

**Status:** Some scripts lack cross-platform equivalents. Not orphaned per se, but a completeness gap.

---

## 7. Integrity Summary

| Check | Status | Details |
|---|---|---|
| All declared packages exist (complete) | ✅ | 7 of 7 |
| All declared packages exist (slim) | **❌** | 3 of 7 |
| Console entry point valid (complete) | ✅ | `spl-tls-analyze` resolves to `scripts.spl_tls_analyze:main` |
| Console entry point valid (slim) | **❌** | Target module missing |
| Docker build context complete | ✅ | All runtime files included |
| docker-test works | **❌** | Tests not copied, pytest not installed |
| `__init__.py` exports match submodules | ✅ | All 7 packages verified |
| Cross-package imports resolve | ✅ | Verified all import chains |
| Duplicate files found | ⚠️ | 3 root docs duplicate `docs/` or `reports_smoke/` |
| Orphaned files found | ⚠️ | `requirements.txt`, generated artifacts in root |
| Generated artifacts in version control | ⚠️ | `dashboard.html`, `v71_graph_snapshot.json`, `capability_report.json` |

---

## 8. Issues Requiring Action

### Critical

| # | Issue | File | Fix |
|---|---|---|---|
| 1 | Slim variant `spl_v7_project/` cannot build | `spl_v7_project/pyproject.toml` | Remove directory (deprecated) |
| 2 | `docker-test` always fails | `Makefile` line 24-25 | Copy `tests/` into Dockerfile or update docs |

### High

| # | Issue | File | Fix |
|---|---|---|---|
| 3 | `requirements.txt` is orphaned | `requirements.txt` | Remove or add comment referencing `pyproject.toml` |
| 4 | Root-level generated artifacts tracked | `dashboard.html`, `v71_graph_snapshot.json`, `capability_report.json` | Add to `.gitignore` |
| 5 | Duplicate documentation at root | `PROMOTION_READINESS.md`, `REPLICATION_REPORT.md`, `RELEASE_CHECKLIST.md` | Remove root copies, keep `docs/` versions |

### Medium

| # | Issue | File | Fix |
|---|---|---|---|
| 6 | Missing cross-platform shell scripts | `scripts/run_dashboard.sh` etc. | Add `.ps1` equivalents or use Python entry points |
| 7 | `reports/dogfood/` empty in slim variant | `spl_v7_project/reports/dogfood/` | Remove empty directory (entire slim variant deprecated) |

### Low

| # | Issue | File | Fix |
|---|---|---|---|
| 8 | Generated report patterns not fully gitignored | `.gitignore` | Add `reports/*` glob to gitignore |
