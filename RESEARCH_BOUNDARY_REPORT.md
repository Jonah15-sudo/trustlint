# RESEARCH_BOUNDARY_REPORT.md

**Date:** 2026-06-09
**Purpose:** Define clear boundary between production and research code

---

## Current State Analysis

### Production Runtime Path

The CLI (`spl_tls_analyze.py`) has a clean production path:

```python
# Always loaded (production):
from scripts.run_local_tls_validation import probe_domain
from tls_policy_adapter import classify_risk
from decision_orchestrator import decide, OperatingProfile

# Only loaded when --spl-unsafe flag is used:
def _create_spl_pipeline():
    from spl_v7.dsl import FeatureDSLProgram
    from spl_v7.kafka_pipeline import EvidencePipeline
```

**Good news:** The research boundary already exists in the code. The `--spl-unsafe` flag gates all research functionality.

### Production Modules (Always Loaded)

| Module | Purpose | Lines | Status |
|--------|---------|-------|--------|
| `decision_orchestrator/` | Decision logic | ~800 | PRODUCTION |
| `tls_policy_adapter/` | Risk classification | ~600 | PRODUCTION |
| `scripts/run_local_tls_validation.py` | TLS probe | ~850 | PRODUCTION |
| `scripts/ocsp_checker.py` | OCSP verification | ~470 | PRODUCTION |
| `scripts/spl_tls_analyze.py` | CLI entry point | ~920 | PRODUCTION |

**Total production code:** ~3,640 lines

### Research Modules (Gated Behind --spl-unsafe)

| Module | Purpose | Lines | Status |
|--------|---------|-------|--------|
| `spl_v7/` | SPL Core (research) | ~100K | RESEARCH |
| `frontier/` | Exploration sidecar | ~150 | RESEARCH |
| `weakness_mapper/` | Weakness discovery | ~300 | RESEARCH |
| `experiments/` | Experiment runner | ~800 | RESEARCH |
| `orthogonal_engine/` | Orthogonal analysis | ~1,250 | RESEARCH |

**Total research code:** ~12,500 lines

---

## Boundary Violations

### Violation 1: Dockerfile Copies Research Modules

```dockerfile
COPY spl_v7 ./spl_v7
COPY weakness_mapper ./weakness_mapper
COPY frontier ./frontier
COPY experiments ./experiments
```

**Issue:** Production Docker image contains research code
**Risk:** Bloated image, attack surface
**Fix:** Remove research modules from Dockerfile

### Violation 2: frontier/ Imports spl_v7

```python
# frontier/metrics.py
from spl_v7.utils import clamp

# frontier/session.py
from spl_v7.utils import clamp, stable_hash
from spl_v7.schema import EvidenceArtifact
```

**Issue:** Research sidecar depends on research core
**Risk:** Import cascade, circular dependencies
**Fix:** Move spl_v7 utilities to standalone module

### Violation 3: scripts/ Contains Research Scripts

Research scripts in `scripts/`:
- `evaluate_spl_vs_baseline.py`
- `run_adversarial_validation.py`
- `run_frontier_validation.py`
- `run_real_tls_spl_decision_validation.py`
- `run_stratified_benchmark.py`
- `run_tls_policy_adapter_benchmark.py`
- `run_validation_evaluation.py`

**Issue:** Research scripts mixed with production scripts
**Risk:** Confusion about what's production
**Fix:** Move research scripts to `research/` directory

---

## Recommended Boundary

### Production (shipped in Docker, installed via pip)

```
trustlint/
├── decision_orchestrator/    # Decision logic
├── tls_policy_adapter/       # Risk classification
├── scripts/
│   ├── spl_tls_analyze.py    # Main CLI
│   ├── run_local_tls_validation.py  # TLS probe
│   └── ocsp_checker.py       # OCSP verification
├── configs/                  # Configuration files
├── datasets/                 # Domain data
├── tests/                    # Test suite
└── pyproject.toml            # Package metadata
```

### Research (not shipped, development only)

```
research/
├── spl_v7/                   # SPL Core
├── frontier/                 # Exploration sidecar
├── weakness_mapper/          # Weakness discovery
├── experiments/              # Experiment runner
├── orthogonal_engine/        # Orthogonal analysis
└── scripts/                  # Research scripts
```

---

## Remediation Plan

### Phase 1: Move Research Scripts

Move research-only scripts from `scripts/` to `research/scripts/`:
- `evaluate_spl_vs_baseline.py`
- `run_adversarial_validation.py`
- `run_frontier_validation.py`
- `run_real_tls_spl_decision_validation.py`
- `run_stratified_benchmark.py`
- `run_tls_policy_adapter_benchmark.py`
- `run_validation_evaluation.py`

### Phase 2: Clean Dockerfile

Remove research modules from Dockerfile:
- Remove `COPY spl_v7 ./spl_v7`
- Remove `COPY weakness_mapper ./weakness_mapper`
- Remove `COPY frontier ./frontier`
- Remove `COPY experiments ./experiments`

### Phase 3: Update pyproject.toml

Remove research modules from packages list:
- Remove `spl_v7`
- Remove `weakness_mapper`
- Remove `frontier`
- Remove `experiments`

### Phase 4: Document Boundary

Add `RESEARCH_BOUNDARY.md` documenting:
- What's production
- What's research
- How to use research modules
- How to add new research

---

## Impact Assessment

### What Changes

| Change | Impact | Risk |
|--------|--------|------|
| Move research scripts | Low | Low |
| Clean Dockerfile | Medium | Low |
| Update pyproject.toml | Medium | Low |
| Document boundary | Low | None |

### What Stays the Same

| Item | Reason |
|------|--------|
| Production CLI | Already works |
| TLS probe | Already works |
| Decision orchestrator | Already works |
| Policy adapter | Already works |
| Test suite | Already passes |

---

## Conclusion

The research boundary already exists in the code (gated by `--spl-unsafe`). The remediation is primarily:
1. Move research scripts to separate directory
2. Clean Docker image
3. Update package metadata
4. Document the boundary

**No functional changes required.** This is purely organizational.

---

**Status:** Ready for remediation
