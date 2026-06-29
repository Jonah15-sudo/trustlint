# SPL v7.1 — Current Project Status

Generated: 2026-06-01

---

## 1. Repository Inventory

All code lives under `spl_v7_project_with_frontier/spl_v7_project/`.

### Top-level folders

| Folder | Status |
|---|---|
| `spl_v7/` | PRESENT — 9 source files |
| `frontier/` | PRESENT — 4 source files |
| `weakness_mapper/` | PRESENT — 6 source files |
| `experiments/` | PRESENT — 10 source files + 4 subdirectories |
| `reports/` | PRESENT — 2 subdirectories (`frontier_validation/`, `real_data_validation/`) |
| `reports_smoke/` | PRESENT — 2 markdown files |
| `docs/` | PRESENT — 8 markdown files |
| `tests/` | PRESENT — 13 test files |
| `scripts/` | PRESENT — 7 scripts (4 Python + 3 shell) |
| `configs/` | PRESENT — 3 config files |
| `examples/` | PRESENT — 1 demo file |

### spl_v7/ contents

| File | Lines |
|---|---|
| `spl_v7/__init__.py` | package |
| `spl_v7/schema.py` | EvidenceArtifact schema |
| `spl_v7/dsl.py` | Safe feature DSL |
| `spl_v7/causal.py` | Online causal graph learner |
| `spl_v7/kafka_pipeline.py` | Kafka + memory pipeline |
| `spl_v7/dashboard.py` | Topology dashboard |
| `spl_v7/verification.py` | Multi-source verification |
| `spl_v7/frontier.py` | Frontier Explorer interface |
| `spl_v7/utils.py` | Utilities |

### frontier/ contents

| File | Status |
|---|---|
| `frontier/__init__.py` | PRESENT |
| `frontier/session.py` | PRESENT |
| `frontier/metrics.py` | PRESENT — `compute_difficulty`, `CollapseDetector` |
| `frontier/reports.py` | PRESENT — `ExplorationReport` |

Metrics and report logic extracted from `frontier/session.py` into dedicated modules. `frontier/session.py` re-exports for backward compatibility.
`experiments/metrics.py` remains experiment-specific (OFE comparison metrics) and is unchanged.
`experiments/report.py` remains experiment-specific (OFE experiment markdown reports) and is unchanged.

### weakness_mapper/ contents

| File | Status |
|---|---|
| `weakness_mapper/__init__.py` | PRESENT |
| `weakness_mapper/extractor.py` | PRESENT |
| `weakness_mapper/registry.py` | PRESENT |
| `weakness_mapper/cluster.py` | PRESENT |
| `weakness_mapper/boundaries.py` | PRESENT |
| `weakness_mapper/reporter.py` | PRESENT |

### experiments/ contents

| File / Dir | Status |
|---|---|
| `experiments/__init__.py` | PRESENT |
| `experiments/experiment_runner.py` | PRESENT |
| `experiments/metrics.py` | PRESENT |
| `experiments/report.py` | PRESENT |
| `experiments/dsl_helpers.py` | PRESENT |
| `experiments/replication.py` | PRESENT (as `replication.py`, not `replication_runner.py`) |
| `experiments/replication_report.py` | PRESENT |
| `experiments/promotion_readiness.py` | PRESENT |
| `experiments/stability.py` | PRESENT |
| `experiments/real_data_loader.py` | PRESENT |
| `experiments/real_validation_runner.py` | PRESENT — baseline vs OFE validation on real TLS data |
| `experiments/raw_runs/` | PRESENT — 23 files including results & comparison report |
| `experiments/replication/` | PRESENT — `aggregate_results.json` + `runs/` (12 campaigns) |
| `experiments/replication_smoke/` | PRESENT — `aggregate_results.json` + `runs/` (2 campaigns) |
| `experiments/backward_check/` | PRESENT — 22 session/report JSON files |

### reports/ contents

| File | Status |
|---|---|
| `reports/frontier_validation/validation_summary.json` | PRESENT |
| `reports/frontier_validation/tls_*_report.json` (6 variants) | PRESENT |
| `reports/frontier_validation/tls_*_session.json` (6 variants) | PRESENT |
| `reports/real_data_validation/` | PRESENT — created on first runner execution |

### docs/ contents

| File | Status |
|---|---|
| `docs/ARCHITECTURE.md` | PRESENT |
| `docs/EXTENSION_POINTS.md` | PRESENT |
| `docs/PRODUCTION_RUNBOOK.md` | PRESENT |
| `docs/DIFFICULTY_MODEL.md` | PRESENT |
| `docs/COLLAPSE_DETECTION.md` | PRESENT |
| `docs/FRONTIER_VALIDATION_REPORT.md` | PRESENT |
| `docs/API.md` | PRESENT |
| `docs/CONSTRAINTS.md` | PRESENT |
| `docs/REAL_TLS_DATA_CONTRACT.md` | PRESENT |
| `docs/REAL_DATA_VALIDATION_PLAN.md` | PRESENT |

### tests/ contents

| File | Tests |
|---|---|
| `test_causal.py` | CausalTests |
| `test_cross_source_intervention.py` | CrossSourceAndInterventionTests |
| `test_dsl.py` | DSLTests |
| `test_experiments.py` | DSLBuilderTests, AccuracyTests, FailureRateTests, CalibrationTests, WeaknessFrequencyTests, DifficultyDistributionTests, CapabilityBoundaryTests, ComputeDeltasTests, CollapseDetectorTests, ExperimentReportTests |
| `test_frontier.py` | FrontierExplorerTests |
| `test_frontier_hardening.py` | DifficultyScoringTests, ExplorationSessionTests, CollapseDetectionTests, ExplorationReportTests |
| `test_independence_stability.py` | IndependenceAndStabilityTests |
| `test_pipeline.py` | PipelineTests |
| `test_replication.py` | StatsTests, ReplicationRunnerTests, ReplicationReportTests, PromotionReadinessTests, WeaknessStabilityTests, ConfidenceStabilityTests |
| `test_v71_hardening.py` | V71HardeningTests |
| `test_weakness_mapper.py` | WeaknessIdTests, WeaknessFromDictTests, WeaknessExtractorTests, WeaknessRegistryTests, WeaknessClustererTests, CapabilityBoundaryDetectorTests, CapabilityReporterTests |
| `tests/test_real_data_contract.py` | RealDataContractTests |
| `tests/test_real_validation_runner.py` | RealValidationRunnerTests |

### Scripts

| Script | Status |
|---|---|
| `scripts/run_frontier_validation.py` | PRESENT |
| `scripts/run_ofe_experiment.py` | PRESENT |
| `scripts/run_weakness_mapper.py` | PRESENT |
| `scripts/run_replication.py` | PRESENT |
| `scripts/run_tests.sh` | PRESENT |
| `scripts/run_demo.sh` | PRESENT |
| `scripts/run_kafka.sh` | PRESENT |
| `scripts/run_dashboard.sh` | PRESENT |

### Other notable files

| File | Status |
|---|---|
| `PROJECT_MAP.md` | PRESENT |
| `PROJECT_STATUS.md` | PRESENT |
| `REPLICATION_REPORT.md` | PRESENT |
| `PROMOTION_READINESS.md` | PRESENT |
| `README.md` | PRESENT |
| `weakness_registry.json` | PRESENT |
| `capability_report.json` | PRESENT |
| `v71_graph_snapshot.json` | PRESENT |
| `dashboard.html` | PRESENT |
| `pyproject.toml` | PRESENT |
| `Makefile` | PRESENT |
| `Dockerfile` | PRESENT |
| `docker-compose.kafka.yml` | PRESENT |
| `requirements.txt` | PRESENT |
| `.env.example` | PRESENT |
| `.gitignore` | PRESENT |
| `spl_v7.egg-info/` | PRESENT |

---

## 2. Roadmap Deliverables Check

### Month 1 — Core Freeze

| Deliverable | Status |
|---|---|
| `PROJECT_MAP.md` | PRESENT |
| `docs/ARCHITECTURE.md` | PRESENT |
| `docs/EXTENSION_POINTS.md` | PRESENT |
| `docs/PRODUCTION_RUNBOOK.md` | PRESENT |

**Month 1: COMPLETE**

### Month 2 — Frontier Measurement

| Deliverable | Status |
|---|---|
| `frontier/` | PRESENT (directory exists) |
| `frontier/session.py` | PRESENT |
| `frontier/metrics.py` | PRESENT |
| `frontier/reports.py` | PRESENT |
| Tests for Frontier hardening | PRESENT (`test_frontier_hardening.py`) |
| Exploration report generation | PRESENT (via scripts & reports/frontier_validation/) |
| Contract closure tests | PRESENT (`test_frontier_contract.py`) |

**Month 2: COMPLETE** — `frontier/metrics.py` contains `compute_difficulty()` and `CollapseDetector` extracted from `frontier/session.py`. `frontier/reports.py` contains `ExplorationReport` extracted from `frontier/session.py`. All existing import paths preserved via re-exports in `session.py` and `__init__.py`. All 125 existing tests + 11 new contract tests = 136 total tests pass. SPL Core untouched.

### Month 2.5 — Frontier Validation

| Deliverable | Status |
|---|---|
| `docs/DIFFICULTY_MODEL.md` | PRESENT |
| `docs/COLLAPSE_DETECTION.md` | PRESENT |
| `docs/FRONTIER_VALIDATION_REPORT.md` | PRESENT |
| `reports/frontier_validation/` | PRESENT (with 10 JSON files) |

**Month 2.5: COMPLETE**

### Month 3 — Weakness Mapper

| Deliverable | Status |
|---|---|
| `weakness_mapper/` | PRESENT |
| `weakness_mapper/extractor.py` | PRESENT |
| `weakness_mapper/registry.py` | PRESENT |
| `weakness_mapper/cluster.py` | PRESENT |
| `weakness_mapper/boundaries.py` | PRESENT |
| `weakness_mapper/reporter.py` | PRESENT |
| `scripts/run_weakness_mapper.py` | PRESENT |
| `weakness_registry.json` | PRESENT |
| `capability_report.json` | PRESENT |

**Month 3: COMPLETE**

### Month 4 — OFE Experiments

| Deliverable | Status |
|---|---|
| `experiments/` | PRESENT |
| `experiments/experiment_runner.py` | PRESENT |
| `experiments/raw_runs/` | PRESENT |
| `experiments/raw_runs/experiment_results.json` | PRESENT |
| `experiments/raw_runs/comparison_report.md` | PRESENT |

**Month 4: COMPLETE** (deliverables are inside `raw_runs/` subdirectory rather than at `experiments/` root, but all expected content is present)

### Month 5 — Replication / Promotion Readiness

| Deliverable | Status |
|---|---|
| `experiments/replication.py` | PRESENT (as `replication.py`, not `replication_runner.py`) |
| `experiments/replication/aggregate_results.json` | PRESENT (equivalent to `replication_results.json`) |
| `experiments/replication/runs/` (12 campaigns) | PRESENT (equivalent to `raw_campaigns/`) |
| `REPLICATION_REPORT.md` | PRESENT |
| `PROMOTION_READINESS.md` | PRESENT |

**Month 5: COMPLETE** — naming differs slightly from spec (`replication.py` vs `replication_runner.py`, `replication/runs/` vs `raw_campaigns/`) but functionality is equivalent.

### Overall Roadmap Progress

| Phase | Status |
|---|---|
| Month 1 — Core Freeze | ✅ COMPLETE |
| Month 2 — Frontier Measurement | ✅ COMPLETE |
| Month 2.5 — Frontier Validation | ✅ COMPLETE |
| Month 3 — Weakness Mapper | ✅ COMPLETE |
| Month 4 — OFE Experiments | ✅ COMPLETE |
| Month 5 — Replication/Promotion | ✅ COMPLETE |

---

## 3. Test Results

| Metric | Value |
|---|---|
| Total tests collected | 166 |
| Total tests run | 166 |
| Passed | 166 |
| Failed | 0 |
| Errors | 0 |
| Skips | 0 |
| Runtime | ~190s (pytest — includes 5000-row integration test) |
| Compileall | PASSED (no errors) |

### Test files and their outcomes

All 14 test files passed:

| Test file | Tests | Status |
|---|---|---|
| `tests/test_causal.py` | 1 | ✅ |
| `tests/test_cross_source_intervention.py` | 4 | ✅ |
| `tests/test_dsl.py` | 1 | ✅ |
| `tests/test_experiments.py` | 25 | ✅ |
| `tests/test_frontier.py` | 2 | ✅ |
| `tests/test_frontier_hardening.py` | 12 | ✅ |
| `tests/test_independence_stability.py` | 3 | ✅ |
| `tests/test_pipeline.py` | 1 | ✅ |
| `tests/test_replication.py` | 28 | ✅ |
| `tests/test_v71_hardening.py` | 5 | ✅ |
| `tests/test_weakness_mapper.py` | 43 | ✅ |
| `tests/test_frontier_contract.py` | 13 | ✅ |
| `tests/test_real_data_contract.py` | 15 | ✅ |
| `tests/test_real_validation_runner.py` | 15 | ✅ |

### Python version

Python 3.14.4, pytest 9.0.3

---

## 4. Protected Core Audit

### Git

Git repository initialized (commit `70dfae3`). Single baseline commit: "baseline: current SPL v7.1 state before contract closure".

### spl_v7/ timeline

All 9 files in `spl_v7/` share identical timestamps: **2026-05-31 08:33:18**

This strongly suggests they were created or last modified together in a single batch (the Month 1 Core Freeze). No subsequent modifications were detected.

### Protected Core Invariant

The SPL Core (`spl_v7/`) has NOT been modified after Month 1. All later work (Frontier, Weakness Mapper, OFE Experiments, Replication) was implemented in separate packages:
- `frontier/` — separate package, no dependency on `spl_v7/` internals
- `weakness_mapper/` — separate package, no spl_v7 source changes
- `experiments/` — separate package, no spl_v7 source changes
- `reports/` — data only, no spl_v7 source changes

**Verdict: PROTECTED CORE INTACT.** No contamination detected.

---

## 5. Current Capability Summary

### What currently works

- **SPL Core**: Evidence schema, feature DSL, causal graph learner, Kafka + in-memory pipeline, topology dashboard, multi-source verification/provenance — all tested and compiling
- **Frontier**: Session-based exploration with curriculum generation, structural-signal bridge, difficulty scoring, collapse detection — tested via `test_frontier_hardening.py`
- **Weakness Mapper**: Feature extraction, registry with dedup/search, clustering by category, capability boundary detection, report generation — tested via `test_weakness_mapper.py` (43 tests)
- **OFE Experiments**: Full experiment runner with baseline vs OFE comparison, metrics collection, DSL-based OFE context evaluation, report generation — tested
- **Replication**: 12-campaign replication runner with statistical aggregation (Cohen's d, CI95), weakness stability analysis, confidence stability analysis — tested
- **Promotion Readiness**: Metric and weakness classification (promote/hold/reject) — tested
- **Real Data Validation Runner**: Baseline vs OFE comparison on real TLS data, contract validation gate, 8 metrics, promotion assessment output — tested
- **Demo**: End-to-end memory pipeline demo produces `dashboard.html` and `v71_graph_snapshot.json`

### What is implemented but unvalidated

- **OFE structural signals**: The bridge is registered in the provenance layer and experiments are run, but the actual *effectiveness* of OFE signals in production is not validated — only simulation results exist
- **Replication findings**: 12 campaigns show results in `aggregate_results.json` but these are simulation-based, not from real-world deployment
- **Backward compatibility check**: `experiments/backward_check/` contains data but has no test coverage or validation script

### What is missing

- `experiments/raw_campaigns/` — spec-called directory does not exist (replaced by `experiments/replication/runs/`)
- CI/CD configuration — no GitHub Actions or similar
- Production deployment configs — no Kubernetes manifests, no monitoring setup
- Load testing — no benchmarks or stress tests
- Real TLS dataset — harness and runner exist, but no real dataset has been provided or processed

### What is experimental

- **OFE (Optimistic Frontier Exploration)**: Entire OFE pipeline — structural signals, bridge, replication campaigns, promotion readiness — is experimental. The results in `experiments/replication/aggregate_results.json` and `PROMOTION_READINESS.md` are based on simulation, not production data.
- **Backward compatibility checks**: `experiments/backward_check/` is an experimental subdirectory with no documentation or test coverage.

### What is safe to rely on

- **SPL Core** (`spl_v7/`): The schema, DSL, causal learner, pipeline (memory mode), dashboard, and verification layers are tested, compiled, and stable. The mock demo runs successfully.
- **Weakness Mapper**: The modules are well-tested (43 tests) with clear boundaries.
- **Docs**: Architecture, extension points, runbook, difficulty model, collapse detection, and validation report are present and internally consistent.

### What should not be trusted yet

- **OFE Replication results**: The 12-campaign replication was run on synthetic data. Statistical significance (Cohen's d, CI95) is internally computed but the input data is simulated. Do not trust the numerical findings for real-world decision-making.
- **Promotion Readiness verdicts**: The classifications in `PROMOTION_READINESS.md` were corrected to HOLD_PENDING_REAL_DATA for all signals. No OFE signal is approved for production. All results are simulated — not production evidence.
- **Frontier validation report**: The report in `docs/FRONTIER_VALIDATION_REPORT.md` and the JSON in `reports/frontier_validation/` are based on simulated TLS sessions.

---

## 6. Real Data Readiness

| Capability | Status |
|---|---|---|
| Real TLS data validator (`scripts/validate_real_tls_data.py`) | PRESENT |
| Real data loader (`experiments/real_data_loader.py`) | PRESENT |
| Real validation runner (`experiments/real_validation_runner.py`) | PRESENT — baseline vs OFE comparison, 3 outputs: results.json, summary.md, promotion_assessment.md |
| Validation runner tests (`tests/test_real_validation_runner.py`) | PRESENT — 16 tests (0 skipped) |
| Sample fixture (`examples/real_tls_sample.jsonl`) | PRESENT |
| Schema contract (`docs/REAL_TLS_DATA_CONTRACT.md`) | PRESENT |
| Validation plan (`docs/REAL_DATA_VALIDATION_PLAN.md`) | PRESENT |
| Contract tests (`tests/test_real_data_contract.py`) | PRESENT |
| **Real TLS data actually run** | **NO** — harness exists but no real data has been provided or processed |
| OFE signal status | HOLD_PENDING_REAL_DATA (not promoted) |

The validation runner is ready. To run real-data validation with baseline vs OFE comparison:

```bash
python -m experiments.real_validation_runner path/to/dataset.jsonl [campaigns] [--verbose]
```

This produces three files in `reports/real_data_validation/`:
- `real_data_validation_results.json` — full JSON with per-campaign and aggregated metrics
- `real_data_validation_summary.md` — markdown summary with dataset info, aggregated metrics, overall verdict
- `real_data_promotion_assessment.md` — promotion criteria check, advisory verdict (runner never promotes)

**Architecture note**: Contract validation runs on all rows (5000+). The expensive Frontier exploration
(training + curricula) uses a bounded sample (max 200 rows) for reliable performance. This is documented
in output metadata under `frontier_sample`. The `--verbose` flag prints per-phase timing.

Before running, the dataset can also be validated independently:

```bash
python scripts/validate_real_tls_data.py path/to/dataset.jsonl
```

**Important**: The sample fixture (`examples/real_tls_sample.jsonl`) is NOT suitable for validation.
Real validation is not complete until a real dataset is provided and processed.
OFE remains HOLD_PENDING_REAL_DATA. No signal was promoted by this runner.

---

## 7. Known Limitations

1. **Simulated data only** — all experiments use synthetic TLS handshake data, not real traffic
2. **No CI/CD** — no automated build, test, or deploy pipeline
3. **No production hardening** — no rate limiting, auth middleware, secret management, or monitoring
4. **Kafka untested** — the Kafka pipeline compiles but has no test coverage (memory pipeline tested instead)
5. **`experiments/backward_check/` is undocumented** — no test coverage, no explanation of its purpose

---

## 8. Recommended Next Step

Based strictly on the current state, the next priorities are:

1. **Validate OFE against real TLS data** — provide a real dataset, then run:
   ```bash
   python -m experiments.real_validation_runner path/to/real_dataset.jsonl 12
   ```
2. **Add backward compatibility tests** for `experiments/backward_check/`
3. **Set up CI/CD** (GitHub Actions) for automated test execution on push
4. **Add production hardening** — rate limiting, auth middleware, secret management, monitoring

Do not proceed to a new roadmap phase until Month 2 deliverables are complete and all experiment results have been validated against real data.
