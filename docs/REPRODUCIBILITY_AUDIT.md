# Reproducibility Audit — spl-tls-analyze v0.1.0b0

**Date:** 2026-06-03
**Scope:** Installation, CLI execution, Docker build, release verification from a completely fresh environment.

---

## Reproducibility Checklist

- [x] 1. Fresh environment — no developer-specific state required
- [x] 2. Install from `pyproject.toml` succeeds (complete variant)
- [ ] 3. Install from `spl_v7_project/` (slim variant) fails — **missing source directories**
- [x] 4. CLI entry point works after clean install
- [x] 5. Docker image builds from clean context
- [ ] 6. Docker `make docker-test` fails — **`tests/` not copied into image**
- [x] 7. Release verification runs (requires `pytest`)
- [x] 8. Core CLI has zero third-party dependencies
- [ ] 9. `import spl_v7` fails without `[spl-core]` extras — **eager import of dashboard**

---

## Verification Results

### 1. Fresh Install from pyproject.toml

| Variant | Status | Notes |
|---------|--------|-------|
| `spl_v7_project_with_frontier/spl_v7_project/` | **PASS** | All packages present |
| `spl_v7_project/` (slim) | **FAIL** | `scripts/`, `spl_v7/`, `tls_policy_adapter/`, `weakness_mapper/`, `tests/` missing |

The slim variant's `pyproject.toml` references 7 packages but only 3 (`decision_orchestrator`, `frontier`, `experiments`) exist on disk. Installation fails with:

```
error: Multiple top-level packages discovered in a flat-layout: [...]
```

### 2. Install with Extras

The `pyproject.toml` declares `dependencies = []`. The CLI **does** work without extras because it only imports stdlib + first-party modules. However:

| Command | CLI Works | `import spl_v7` Works | Tests Work |
|---------|-----------|----------------------|------------|
| `pip install .` | YES | **FAIL** | NO |
| `pip install ".[spl-core]"` | YES | YES | NO |
| `pip install ".[dev]"` | YES | **FAIL** | YES |
| `pip install ".[spl-core,dev]"` | YES | YES | YES |

### 3. CLI Entry Point

```
> spl-tls-analyze --help
```

Works after `pip install .` — no extras needed. Confirmed exit codes 0/1/2/3/4.

### 4. Docker Build

```
> docker build -t spl-tls-analyze:test .
```

Builds successfully. The resulting image:
- Runs `spl-tls-analyze --help` by default
- Does NOT include `tests/` directory
- Does NOT include `spl-core` extras
- Importing `spl_v7` inside the container **will fail**

### 5. Release Verification

```
> python scripts/verify_release.py
```

**Requires `pytest`** (from `[dev]` extras). Of 14 checks:

| Check | Needs Extra | Status |
|-------|-------------|--------|
| Full test suite | `[dev]` | PASS |
| Compileall | None | PASS |
| Golden tests | `[dev]` | PASS |
| CLI smoke test | None | PASS |
| CLI negative smoke | None | PASS |
| SPL Core integrity | None | PASS |
| OFE status | None | PASS |
| Package metadata | None | PASS |
| Console entry point | None | PASS |
| Entry point tests | `[dev]` | PASS |
| Install documentation | None | PASS |
| Version consistency | None | PASS |
| Docker (optional) | `docker` CLI | SKIP if missing |
| VPS dry-run docs | None | PASS |

---

## Hidden Dependencies & Assumptions

### Environment Assumptions

| # | Assumption | Risk | Mitigation |
|---|-----------|------|------------|
| 1 | `__file__` resolves correctly for `PROJECT_ROOT` discovery | Breaks with frozen/zip imports | Use `importlib.resources` or set `PROJECT_ROOT` via env var |
| 2 | `python` is on PATH (Windows: `python.exe`) | Different `python3` on Linux | Document `python3` alias |
| 3 | Shell scripts (`run_tests.sh`, `run_demo.sh`) assume bash | Fail on Windows without WSL | Add PowerShell equivalents |
| 4 | Docker base image `python:3.10-slim` has OpenSSL | Very low (slim includes it) | — |
| 5 | `pip` is available (Python 3.10+ ships with it) | Very low | — |

### Path Assumptions

| # | Assumption | Location | Impact |
|---|-----------|----------|--------|
| 1 | `sys.path.insert(0, PROJECT_ROOT)` in multiple scripts | `scripts/spl_tls_analyze.py:30-32`, `tests/test_package_entry.py:17-18` | Only works for source installs; breaks if package is installed non-editable |
| 2 | `scripts/verify_release.py` assumes CWD is project root | `verify_release.py:27` | Fails if run from outside the project |
| 3 | Report directory `reports/local_real_validation` | `scripts/run_local_tls_validation.py:15` | Created implicitly — okay but could fail with read-only FS |

### Undocumented Setup Steps

| # | Missing Documentation | Location |
|---|---------------------|----------|
| 1 | Need for `pip install ".[dev]"` or `pip install ".[spl-core,dev]"` to run tests | `docs/INSTALL.md` only shows `pip install -e .` |
| 2 | `import spl_v7` fails without `[spl-core]` extras | Nowhere documented |
| 3 | `spl_v7/__init__.py` eagerly imports `dashboard.py` (requires numpy/networkx/plotly/fastapi) | `spl_v7/__init__.py:6` |
| 4 | `pip install .` alone is insufficient for `verify_release.py` | `docs/INSTALL.md` |
| 5 | Docker image does not include test suite | `docs/DOCKER_USAGE.md` mentions `pytest tests/` but tests aren't copied |
| 6 | No published PyPI package — must install from source | `docs/INSTALL.md` mentions this (good) |

### Software Dependencies

**Actual runtime imports (stdlib-only for CLI):**

```
scripts/spl_tls_analyze.py         → stdlib only
tls_policy_adapter/*               → stdlib only
decision_orchestrator/*            → stdlib only
weakness_mapper/*                  → stdlib only
frontier/*                         → stdlib only
experiments/*                      → stdlib only
scripts/run_local_tls_validation.py → stdlib (ssl, socket)
```

**Third-party packages needed (imported at top level):**

| Package | Imported By | Required For | Listed In pyproject? |
|---------|-------------|-------------|---------------------|
| `numpy` | `spl_v7/dashboard.py` | `import spl_v7` | `[spl-core]` |
| `networkx` | `spl_v7/dashboard.py` | `import spl_v7` | `[spl-core]` |
| `plotly` | `spl_v7/dashboard.py` | `import spl_v7` | `[spl-core]` |
| `fastapi` | `spl_v7/dashboard.py` | `import spl_v7` | `[spl-core]` |
| `uvicorn` | Not imported (CLI tool) | Dashboard server | `[spl-core]` |
| `confluent-kafka` | `spl_v7/kafka_pipeline.py` (lazy) | Kafka pipeline | `[kafka]` |
| `pytest` | Tests + `verify_release.py` | Testing | `[dev]` |

---

## Issues Requiring Action

### Critical

1. **`spl_v7/__init__.py` eagerly imports dashboard dependencies**
   - `spl_v7/__init__.py` line 6: `from .dashboard import create_app, build_dashboard_html`
   - `spl_v7/dashboard.py` line 6-10: top-level `import networkx`, `import numpy`, `import plotly`, `from fastapi import ...`
   - **Effect:** `import spl_v7` fails with `ModuleNotFoundError` if `spl-core` extras not installed
   - **Impact:** `test_package_entry.py:TestImportPaths.test_import_spl_v7` fails without `[spl-core]`
   - **Fix:** Either make dashboard imports lazy, or document mandatory extras

2. **`pyproject.toml` declares `dependencies = []`**
   - Technically correct for the CLI, but misleading
   - Install docs should clearly specify which extras are needed for which use case
   - **Fix:** Update install docs to show `pip install ".[spl-core,dev]"` for full functionality

3. **`spl_v7_project/` (slim variant) has stale `pyproject.toml`**
   - References packages that don't exist on disk (`scripts/`, `spl_v7/`, `tls_policy_adapter/`, `weakness_mapper/`)
   - **Effect:** Build fails; confused new user
   - **Fix:** Either remove the slim variant or update its `pyproject.toml`

### High

4. **Docker image does not copy `tests/`**
   - `make docker-test` (`docker run --rm spl-v7:local python -m pytest tests/`) fails
   - **Effect:** Verification inside Docker is broken
   - **Fix:** Either copy `tests/` in Dockerfile or update docs to skip docker-test

5. **`verify_release.py` requires `pytest` without documentation**
   - Not installed by `pip install .`
   - `docs/INSTALL.md` runs `python scripts/verify_release.py` after `pip install -e .`
   - **Effect:** User follows docs, verify_release fails
   - **Fix:** Document `pip install ".[dev]"` requirement

### Medium

6. **`requirements.txt` is unused**
   - Contains numpy, plotly, networkx, fastapi, uvicorn, confluent-kafka (commented)
   - No build tool references it
   - **Effect:** Confusing artifact; user might try `pip install -r requirements.txt`
   - **Fix:** Remove or add a comment referencing `[spl-core]` extras

7. **Scripts use `sys.path.insert(0, ...)` for module resolution**
   - `scripts/spl_tls_analyze.py:30-32`, `tests/test_package_entry.py:17-18`
   - Works for source installs but fragile for non-editable installs
   - **Effect:** Could break if PYTHONPATH is not set
   - **Fix:** Not blocking but worth documenting

---

## Verified Clean Install Procedure

The following procedure was verified to work from a completely fresh Python 3.10 environment:

```powershell
# 1. Clone/enter the complete project variant
cd spl_v7_project_with_frontier/spl_v7_project

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install with ALL extras (CLI + dashboard + tests)
pip install ".[spl-core,dev]"

# 4. Verify CLI works
spl-tls-analyze --help

# 5. Run release verification
python scripts/verify_release.py

# 6. Build Docker image
docker build -t spl-tls-analyze:test .
docker run --rm spl-tls-analyze:test --help
```

---

## Summary

| Requirement | Status | Notes |
|-------------|--------|-------|
| Fresh install succeeds | ⚠️ Partial | Only from complete variant; missing extras cause `import spl_v7` to fail |
| Package install succeeds | ✅ | With correct variant and extras |
| CLI executes | ✅ | Zero third-party deps; works on bare `pip install .` |
| Docker builds | ✅ | But image has no tests and no spl-core extras |
| Release verification runs | ⚠️ Requires `[dev]` | Fails on bare `pip install .` |
| Hidden assumptions documented | ✅ | See tables above |
