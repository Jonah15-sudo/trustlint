# ARCHITECTURE_CHALLENGE_REPORT.md

**Reviewer:** Hostile Principal Engineer
**Date:** 2026-06-09
**Verdict:** NOT READY FOR PRODUCTION

---

## CRITICAL FINDINGS

### 1. The Core Module Warns Against Production Use

```python
# spl_v7/__init__.py
warnings.warn(
    "SPL Core is a research module with no validated production uplift. "
    "Do not use in production decisions. "
    "See docs/SPL_VALIDATION_FINDINGS.md.",
    category=UserWarning,
    stacklevel=2,
)
```

**This is the most critical finding.** The `spl_v7` package — which is imported by the CLI and forms part of the decision pipeline — explicitly warns that it is NOT production-ready. The consolidation preserved this warning but shipped the module anyway.

**Impact:** Every import of `spl_v7` emits a warning. The CLI's `--spl-unsafe` flag enables this module. The entire SPL subsystem is unvalidated research code.

**Question:** Why does a "production-ready" release contain a module that tells you not to use it in production?

---

### 2. The Orthogonal Engine Is a Research Prototype

```python
# orthogonal_engine/orthogonal_flat_engine_v09_0_fixed.py
"""
THE ORTHOGONAL FLAT ENGINE (Prototype v0.9.0)
The Hyper-Sheet War — Multi-Sheet Sovereign Architecture
Tension Conservation Fix & Topological Uniqueness Enforcement
"""
```

This 1,252-line file implements:
- SL(2,Z) non-commutative matrix memory
- Braid strand holonomy
- Topological uniqueness enforcement
- "Womb IDs" and "birth tension"

**This has zero relationship to TLS analysis.** It is a research prototype for some other project that was bundled into this repository.

**Impact:** 1,252 lines of dead code shipping in a "production" release. No tests validate its behavior. No documentation explains its purpose.

---

### 3. Global Mutable State in the TLS Probe

```python
# scripts/run_local_tls_validation.py
PROBE_TIMEOUT = 10.0
RATE_LIMIT_SECONDS = 1.0
```

These are module-level globals that are mutated by `spl_tls_analyze.py`:

```python
# scripts/spl_tls_analyze.py
import scripts.run_local_tls_validation as probe_mod
original_timeout = probe_mod.PROBE_TIMEOUT
probe_mod.PROBE_TIMEOUT = timeout
try:
    raw = probe_domain(domain, ca_store=ca_store)
finally:
    probe_mod.PROBE_TIMEOUT = original_timeout
```

**This is not thread-safe.** If two threads probe simultaneously with different timeouts, they will corrupt each other's state. The `--workers` flag for concurrent probing is unsafe with this implementation.

**Impact:** Race condition in concurrent mode. Data corruption possible.

---

### 4. sys.path Manipulation Everywhere

```python
# scripts/spl_tls_analyze.py
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
```

```python
# tests/test_tls_probe.py
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
```

This pattern appears in at least 5 files. It indicates the package is not properly installed or structured.

**Impact:** Fragile import resolution. Different behavior depending on working directory. Breaks when installed via pip.

---

### 5. No Proper Package Structure

The `pyproject.toml` declares:

```toml
[tool.setuptools]
packages = [
  "decision_orchestrator",
  "scripts",
  "spl_v7",
  "tls_policy_adapter",
  "weakness_mapper",
  "frontier",
  "experiments",
]
```

But the CLI entry point is:

```toml
[project.scripts]
spl-tls-analyze = "scripts.spl_tls_analyze:main"
```

**`scripts` is not a package — it's a directory of standalone scripts.** Making it an entry point means `import scripts` is required, but `scripts/__init__.py` may not exist or may be empty. This is a packaging anti-pattern.

**Impact:** Broken imports when installed via pip. The package may not work outside the source directory.

---

### 6. Version Mismatch

- `pyproject.toml`: version = "0.3.2b0"
- `README.md`: Version 1.0.0-consolidated
- `FINAL_JUDGMENT.md`: Version 1.0.0-consolidated

**Three different versions in three different files.**

**Impact:** Confusion about what is actually being released. pip will install 0.3.2b0 but documentation says 1.0.0.

---

### 7. Inconsistent Architecture Between V1 and V3

V1 (trustlint_v2) had:
- Clean package structure (`trustlint/probe/`, `trustlint/policy/`, `trustlint/report/`)
- Frozen dataclasses for all models
- Zero global state
- Thread-safe by design

V3 (current) has:
- Flat module structure (`decision_orchestrator/`, `tls_policy_adapter/`, `scripts/`)
- TypedDict for schemas (mutable)
- Global mutable state
- sys.path hacks

**The consolidation chose the weaker architecture.**

---

## HIGH SEVERITY FINDINGS

### 8. The CLI Is Not a Proper CLI

The entry point is `scripts/spl_tls_analyze.py` — a script file, not a module. The `main()` function uses `sys.exit(main())` at the bottom. This is script-style programming, not package-style.

**Impact:** Cannot be imported cleanly. Cannot be tested in isolation. Cannot be extended.

---

### 9. No Dependency Injection

The `probe_domain()` function is called directly:

```python
from scripts.run_local_tls_validation import probe_domain
```

There's no interface, no abstraction, no way to substitute a mock probe for testing without patching.

**Impact:** Tight coupling. Testing requires monkey-patching. Cannot swap implementations.

---

### 10. Duplicate Documentation Blocks

In `run_local_tls_validation.py`, the `_build_seed_report` function contains:

```python
    lines.extend([
        "## Known Limitations",
        "",
         "1. **No persistent cert store** ...",
         ...
        "## SPL Decisions",
        "",
        "- No SPL Core modifications were made.",
        ...
    ])
```

This entire block appears **twice** in the same function (lines ~370-400 and ~420-450).

**Impact:** Duplicate content in generated reports. Indicates copy-paste development.

---

### 11. No Configuration Validation

The `configs/features.dsl` file is loaded without validation:

```python
with open(dsl_path, "r", encoding="utf-8") as f:
    dsl_text = f.read()
program = FeatureDSLProgram.from_text(dsl_text)
```

No schema validation. No syntax checking. No error handling beyond basic file-not-found.

**Impact:** Silent failures. Invalid configuration produces undefined behavior.

---

### 12. No Logging Configuration

The CLI sets up logging:

```python
def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
```

But the underlying modules use `print()` statements:

```python
# scripts/run_local_tls_validation.py
print(f"[{i + 1}/{len(domains)}] Probing {domain}...", end=" ", flush=True)
```

**Impact:** Mixed output streams. Cannot control verbosity programmatically. Logs and prints interleave.

---

## MEDIUM SEVERITY FINDINGS

### 13. No Type Checking Configuration

No `mypy.ini`, no `pyrightconfig.json`, no `[tool.mypy]` in pyproject.toml.

**Impact:** Type errors only caught at runtime. No CI type checking.

---

### 14. No Linting Configuration

No `ruff.toml`, no `.flake8`, no `[tool.ruff]` in pyproject.toml.

**Impact:** Code style inconsistencies. No automated code quality checks.

---

### 15. No Security Scanning

No `bandit` configuration. No `safety` checks. No dependency vulnerability scanning.

**Impact:** Unknown security posture. Dependencies not audited.

---

### 16. The Dockerfile Copies Everything

```dockerfile
COPY scripts ./scripts
COPY spl_v7 ./spl_v7
COPY weakness_mapper ./weakness_mapper
COPY frontier ./frontier
COPY experiments ./experiments
COPY datasets ./datasets
```

**All research modules, experiments, and datasets are copied into the production image.**

**Impact:** Bloated image. Attack surface includes research code. No multi-stage build.

---

### 17. No .dockerignore

The `.dockerignore` file exists but let me check its contents...

Actually, looking at the Dockerfile, it copies `datasets/` and `experiments/` into the production image. This is wrong.

**Impact:** Production container contains test data and research code.

---

### 18. No Health Check for Actual Functionality

The health check only verifies:
- Python version
- SSL module
- DNS resolution
- Package imports
- Config directory existence

It does NOT verify:
- TLS probing works
- Decision orchestration works
- Output formatting works

**Impact:** Health check passes even if core functionality is broken.

---

### 19. No API Stability Guarantees

No `__version__` in any package. No deprecation policy. No compatibility shims.

**Impact:** Breaking changes can ship without warning.

---

### 20. No Error Recovery

The CLI catches exceptions per-domain but has no retry logic:

```python
for domain in domains:
    try:
        r = analyze_domain(...)
        results.append(r)
    except Exception as e:
        errors.append(f"  {domain}: ERROR — {e}")
```

**Impact:** Transient network errors cause permanent failures. No retry mechanism.

---

## SUMMARY

| Severity | Count | Examples |
|----------|-------|---------|
| CRITICAL | 7 | Research module in production, global mutable state, version mismatch |
| HIGH | 5 | Script-style CLI, no dependency injection, duplicate docs |
| MEDIUM | 8 | No type checking, no linting, bloated Docker image |

**Overall Assessment:** This repository contains a useful TLS probe (`run_local_tls_validation.py`) and a clean decision orchestrator (`decision_orchestrator/`), but they are surrounded by research prototypes, experimental code, and packaging anti-patterns that make it unsuitable for production use.

**Recommendation:** Strip all research modules (spl_v7, orthogonal_engine, frontier, weakness_mapper, experiments). Fix the package structure. Fix the global mutable state. Align versions. Then re-evaluate.
