# Project Artifact Inventory — spl-tls-analyze v0.1.0b0

**Generated:** 2026-06-03
**Source of truth:** `spl_v7_project_with_frontier/spl_v7_project/`
**Total artifacts:** 475 (including compiled cache), ~210 source/documentation/data files

---

## Artifact Classification Legend

| Badge | Meaning |
|-------|---------|
| 🟢 **RUNTIME** | Required for CLI or library operation |
| 🟡 **BUILD** | Build/configuration metadata |
| 🔵 **TEST** | Test code or test fixtures |
| 🟣 **DOC** | Documentation |
| 🟠 **DATA** | Domain data, expectations, golden samples |
| 🔴 **GENERATED** | Produced by a script or workflow; not source |
| ⚪ **CACHE** | Bytecode, pytest cache, egg-info (reproducible) |

---

## 1. Root Directory

| File | Size | Badge | Role | Active |
|------|------|-------|------|--------|
| `pyproject.toml` | 770 B | 🟡 | Package build definition; entry point, deps, pytest config | ✅ |
| `Dockerfile` | 730 B | 🟡 | Docker image definition (CLI-only, non-root) | ✅ |
| `Makefile` | 828 B | 🟡 | Dev workflow shortcuts (install, test, docker-*) | ✅ |
| `.dockerignore` | 85 B | 🟡 | Docker build context exclusions | ✅ |
| `.gitignore` | 90 B | 🟡 | Git tracking exclusions | ✅ |
| `.env.example` | 140 B | 🟡 | Environment variable template | ✅ |
| `docker-compose.kafka.yml` | 656 B | 🟡 | Kafka + Zookeeper compose for broker path testing | ✅ |
| `README.md` | 7,159 B | 🟣 | Project overview, quickstart, profiles | ✅ |
| `requirements.txt` | 144 B | 🟡 | **ORPHANED** — duplicates `pyproject.toml` spl-core extras | ❌ |
| `PROJECT_MAP.md` | 7,785 B | 🟣 | Project mapping and navigation | ✅ |
| `PROJECT_STATUS.md` | 2,627 B | 🟣 | Current status summary | ✅ |
| `RELEASE_CHECKLIST.md` | 1,302 B | 🟣 | **DUPLICATE** — also in `docs/` | ⚠️ |
| `REPLICATION_REPORT.md` | 3,995 B | 🟣 | **DUPLICATE** — also in `reports_smoke/` | ⚠️ |
| `PROMOTION_READINESS.md` | 4,800 B | 🟣 | **DUPLICATE** — also in `reports_smoke/` | ⚠️ |
| `real_tls_dataset_NOT_FOUND.md` | 3,530 B | 🟣 | Explains missing real TLS dataset | ✅ |
| `v71_graph_snapshot.json` | 143,810 B | 🔴 | Generated causal graph snapshot (demo run) | ❌ |
| `capability_report.json` | ~395 lines | 🔴 | Generated weakness/capability report | ❌ |
| `dashboard.html` | 51,020 B | 🔴 | Generated dashboard HTML | ❌ |

---

## 2. `.github/workflows/` — CI Pipeline

| File | Size | Badge | Role | Active |
|------|------|-------|------|--------|
| `ci.yml` | 3,065 B | 🟡 | GitHub Actions: install dev, compileall, pytest, dataset gate, archive hygiene, promotion guard | ✅ |

---

## 3. `configs/` — Pipeline Configuration

| File | Size | Badge | Role | Active |
|------|------|-------|------|--------|
| `pipeline.memory.json` | 346 B | 🟡 | In-memory backend config (default) | ✅ |
| `pipeline.kafka.json` | 495 B | 🟡 | Kafka backend config (broker, topics, constraints) | ✅ |
| `features.dsl` | 740 B | 🟡 | Feature DSL definitions (10 features) | ✅ |

---

## 4. `datasets/` — Domain Lists and Expectations

| File | Size | Badge | Role | Active |
|------|------|-------|------|--------|
| `cli_golden_samples.json` | 5,608 B | 🟠 | 12 mocked TLS probe samples for golden fixtures | ✅ |
| `dogfood_domains.txt` | 259 B | 🟠 | 31 domains for dogfood testing | ✅ |
| `vps_dry_run_domains.txt` | 74 B | 🟠 | 15 domains for VPS dry run | ✅ |
| `real_tls_benchmark_domains.txt` | 260 B | 🟠 | Benchmark domain list | ✅ |
| `real_tls_benchmark_expectations.json` | 74,578 B | 🟠 | Expected benchmark decisions | ✅ |
| `real_tls_decision_expectations.json` | 15,883 B | 🟠 | SPL decision expectations | ✅ |
| `real_tls_holdout_domains.txt` | 55 B | 🟠 | Holdout domain list | ✅ |
| `real_tls_holdout_expectations.json` | 2,856 B | 🟠 | Expected holdout results | ✅ |
| `real_tls_mixed_domains.txt` | 78 B | 🟠 | Mixed TLS domains | ✅ |
| `real_tls_mixed_expected.json` | 53,056 B | 🟠 | Mixed TLS expectations | ✅ |
| `real_tls_seed_domains.txt` | 39 B | 🟠 | Validation seed domains | ✅ |
| `real_tls_train_domains.txt` | 96 B | 🟠 | Training domain list | ✅ |
| `real_tls_train_expectations.json` | 8,706 B | 🟠 | Training expectations | ✅ |

---

## 5. `examples/`

| File | Size | Badge | Role | Active |
|------|------|-------|------|--------|
| `demo.py` | 2,560 B | 🔵 | Full pipeline demo (DSL → causal → dashboard) | ✅ |
| `real_tls_sample.jsonl` | 1,373 B | 🟠 | Sample TLS evidence data (JSONL) | ✅ |

---

## 6. `spl_v7/` — Core Library Package

| File | Size | Badge | Role | Exports | Active |
|------|------|-------|------|---------|--------|
| `__init__.py` | 1,030 B | 🟢 | Package exports (19 symbols) | See below | ✅ |
| `causal.py` | 44,623 B | 🟢 | `OnlineCausalGraphLearner` — causal graph learning | `OnlineCausalGraphLearner` | ✅ |
| `dashboard.py` | 9,231 B | 🟢 | `create_app()` (FastAPI), `build_dashboard_html()` | `create_app`, `build_dashboard_html` | ✅ |
| `dsl.py` | 13,048 B | 🟢 | `FeatureDSLParser`, `FeatureDSLProgram` | `FeatureDSLProgram`, `FeatureDSLParser`, `compile_feature_dsl` | ✅ |
| `frontier.py` | 12,737 B | 🟢 | `FrontierExplorer`, `FrontierChallenge` | `FrontierExplorer`, `FrontierChallenge` | ✅ |
| `kafka_pipeline.py` | 10,596 B | 🟢 | `EvidencePipeline`, `PipelineConfig`, `MemoryKafkaAdapter` | `EvidencePipeline`, `PipelineConfig` | ✅ |
| `schema.py` | 4,773 B | 🟢 | Evidence data types | `EvidenceArtifact`, `EvidenceIntegrity`, `EvidenceTransportMeta`, `evidence_schema` | ✅ |
| `utils.py` | 2,666 B | 🟢 | Utility functions | — | ✅ |
| `verification.py` | 6,754 B | 🟢 | Source verification | `SourceProfile`, `SourceRegistry`, `EvidenceProvenanceVerifier`, `compute_artifact_hash`, `compute_artifact_signature` | ✅ |

### `spl_v7/__init__.py` Exports

```
EvidenceArtifact, EvidenceIntegrity, EvidenceTransportMeta, evidence_schema
FeatureDSLProgram, FeatureDSLParser, compile_feature_dsl
OnlineCausalGraphLearner
EvidencePipeline, PipelineConfig
SourceProfile, SourceRegistry, EvidenceProvenanceVerifier
compute_artifact_hash, compute_artifact_signature
create_app, build_dashboard_html
FrontierExplorer, FrontierChallenge
```

**Note:** `__init__.py` eagerly imports `dashboard.py`, which requires `numpy`, `networkx`, `plotly`, `fastapi` at top level.

---

## 7. `frontier/` — Frontier Exploration Package

| File | Size | Badge | Role | Exports | Active |
|------|------|-------|------|---------|--------|
| `__init__.py` | 253 B | 🟢 | Package exports (4 symbols) | See below | ✅ |
| `metrics.py` | 2,439 B | 🟢 | `compute_difficulty()`, `CollapseDetector` | `compute_difficulty`, `CollapseDetector` | ✅ |
| `session.py` | 2,898 B | 🟢 | `ExplorationSession` | `ExplorationSession` | ✅ |
| `reports.py` | 2,073 B | 🟢 | `ExplorationReport` | `ExplorationReport` | ✅ |

### `frontier/__init__.py` Exports

```
compute_difficulty, ExplorationSession, ExplorationReport, CollapseDetector
```

---

## 8. `weakness_mapper/` — Weakness & Capability Mapping Package

| File | Size | Badge | Role | Exports | Active |
|------|------|-------|------|---------|--------|
| `__init__.py` | 435 B | 🟢 | Package exports (5 symbols) | See below | ✅ |
| `extractor.py` | 7,124 B | 🟢 | `WeaknessExtractor` | `WeaknessExtractor` | ✅ |
| `registry.py` | 4,305 B | 🟢 | `WeaknessRegistry` | `WeaknessRegistry` | ✅ |
| `cluster.py` | 2,281 B | 🟢 | `WeaknessClusterer` | `WeaknessClusterer` | ✅ |
| `boundaries.py` | 2,026 B | 🟢 | `CapabilityBoundaryDetector` | `CapabilityBoundaryDetector` | ✅ |
| `reporter.py` | 3,292 B | 🟢 | `CapabilityReporter` | `CapabilityReporter` | ✅ |

### `weakness_mapper/__init__.py` Exports

```
WeaknessExtractor, WeaknessRegistry, WeaknessClusterer, CapabilityBoundaryDetector, CapabilityReporter
```

---

## 9. `tls_policy_adapter/` — TLS Risk Policy Adapter Package

| File | Size | Badge | Role | Exports | Active |
|------|------|-------|------|---------|--------|
| `__init__.py` | 1,844 B | 🟢 | Package exports (15 symbols) | See below | ✅ |
| `schema.py` | 6,875 B | 🟢 | Type definitions, `TLSPolicyEvidence`, `RISK_MAP` | Type definitions | ✅ |
| `risk_policy.py` | 2,257 B | 🟢 | `classify_risk()`, `classify_risk_from_probe()` | `classify_risk`, `classify_risk_from_probe`, `SEVERITY_RANK` | ✅ |
| `evidence_adapter.py` | 3,101 B | 🟢 | `enrich_evidence()`, `AdapterBenchmarkResult` | `enrich_evidence`, `enrich_evidence_artifact`, `EnrichedEvidence`, `AdapterBenchmarkResult` | ✅ |

### `tls_policy_adapter/__init__.py` Exports

```
TLSClassification, TLSSeverity, TLSRiskCategory, TLSFailureFamily
TLSPolicyEvidence, RISK_MAP, SEVERITY_ORDER
classify_risk, classify_risk_from_probe, SEVERITY_RANK
enrich_evidence, enrich_evidence_artifact, EnrichedEvidence, AdapterBenchmarkResult
```

---

## 10. `decision_orchestrator/` — Decision Orchestration Package

| File | Size | Badge | Role | Exports | Active |
|------|------|-------|------|---------|--------|
| `__init__.py` | 1,066 B | 🟢 | Package exports (11 symbols) | See below | ✅ |
| `schema.py` | ~2,500 B | 🟢 | `OrchestratorInput`, `OrchestratorOutput` TypedDicts | Type definitions | ✅ |
| `policy.py` | ~9,300 B | 🟢 | `decide()`, `orchestrate()` — core orchestration rules | `decide`, `orchestrate`, `OperatingProfile` | ✅ |
| `reporter.py` | ~14,500 B | 🟢 | `generate_report()`, `BenchmarkRunResult` | `generate_report`, `save_results`, `BenchmarkRunResult` | ✅ |

### `decision_orchestrator/__init__.py` Exports

```
FinalDecision, FinalRisk, DecisionSource
OrchestratorInput, OrchestratorOutput, SEVERITY_ORDER, SEVERITY_RANK, OperatingProfile
decide, orchestrate
generate_report, BenchmarkRunResult
```

---

## 11. `experiments/` — Experimentation Package

### Source Files

| File | Size | Badge | Role | Active |
|------|------|-------|------|--------|
| `__init__.py` | 337 B | 🟢 | Package exports: `build_experiment_dsl`, `MetricsCollector`, `ExperimentReport` | ✅ |
| `dsl_helpers.py` | 2,371 B | 🟢 | `build_experiment_dsl()` | ✅ |
| `metrics.py` | 5,105 B | 🟢 | `MetricsCollector` (accuracy, precision, recall, F1) | ✅ |
| `experiment_runner.py` | 10,616 B | 🟢 | `ExperimentRunner` (5 curricula) | ✅ |
| `replication.py` | 6,714 B | 🟢 | Replication study logic | ✅ |
| `replication_report.py` | 11,398 B | 🟢 | `ReplicationReport` (Markdown generator) | ✅ |
| `promotion_readiness.py` | ~6,600 B | 🟢 | PROMOTE/HOLD/REJECT classification | ✅ |
| `report.py` | 10,180 B | 🟢 | `ExperimentReport` | ✅ |
| `stability.py` | 4,932 B | 🟢 | Stability analysis | ✅ |
| `status.py` | 957 B | 🟢 | `check_ofe_status()`, `check_dataset_gate()` | ✅ |
| `real_data_loader.py` | 6,722 B | 🟢 | Real TLS data loading | ✅ |
| `real_validation_runner.py` | 36,701 B | 🟢 | `RealValidationRunner` (also runnable as script) | ✅ |

### Experiment Output Data

| Directory | Files | Badge | Role | Active |
|-----------|-------|-------|------|--------|
| `backward_check/` | 24 JSON | 🟠 | A/B comparison fixture data | ✅ |
| `raw_runs/` | 24 files | 🟠 | Raw experiment run outputs | ✅ |
| `replication/` | 47 files | 🟠 | Multi-campaign replication data | ✅ |
| `replication_smoke/` | 26 files | 🟠 | Smoke-test replication data | ✅ |

---

## 12. `scripts/` — CLI Entry Points & Utility Scripts

### Python Scripts (all have `if __name__ == "__main__"`)

| File | Size | Badge | Role | Console Entry | Active |
|------|------|-------|------|:-------------:|--------|
| `__init__.py` | 38 B | 🟢 | Package marker | — | ✅ |
| `spl_tls_analyze.py` | 23,553 B | 🟢 | **Main CLI** — TLS analysis entry point | ✅ `spl-tls-analyze` | ✅ |
| `verify_release.py` | 19,546 B | 🟢 | Release verification (14 checks) | ❌ | ✅ |
| `run_local_tls_validation.py` | 29,355 B | 🟢 | Local TLS probe & validation | ❌ | ✅ |
| `run_decision_orchestration_benchmark.py` | 16,821 B | 🟢 | Decision orchestration benchmark | ❌ | ✅ |
| `run_dogfood_cli.py` | 5,452 B | 🟢 | Dogfood test runner | ❌ | ✅ |
| `run_frontier_validation.py` | 7,686 B | 🟢 | Frontier validation | ❌ | ✅ |
| `run_ofe_experiment.py` | 1,627 B | 🟢 | OFE experiment runner | ❌ | ✅ |
| `run_real_tls_spl_decision_validation.py` | — | 🔴 | SPL decision validation (planned, never committed) | ❌ | ❌ |
| `run_replication.py` | 3,338 B | 🟢 | Replication study runner | ❌ | ✅ |
| `run_stratified_benchmark.py` | — | 🔴 | Stratified benchmark (planned, never committed) | ❌ | ❌ |
| `run_tls_policy_adapter_benchmark.py` | — | 🔴 | TLS policy adapter benchmark (planned, never committed) | ❌ | ❌ |
| `run_weakness_mapper.py` | 2,806 B | 🟢 | Weakness mapper | ❌ | ✅ |
| `validate_real_tls_data.py` | 6,998 B | 🟢 | Real TLS data validation | ❌ | ✅ |

### Shell Scripts (Unix)

| File | Size | Badge | Role | Active |
|------|------|-------|------|--------|
| `run_tests.sh` | 161 B | 🟡 | Run full test suite + compileall | ✅ |
| `run_demo.sh` | 99 B | 🟡 | Run demo pipeline | ✅ |
| `run_dashboard.sh` | 213 B | 🟡 | Start FastAPI dashboard | ✅ |
| `run_kafka.sh` | 111 B | 🟡 | Start Kafka + Zookeeper | ✅ |
| `run_vps_dry_run.sh` | 3,310 B | 🟡 | VPS dry run (Docker-based) | ✅ |

### PowerShell Scripts (Windows)

| File | Size | Badge | Role | Active |
|------|------|-------|------|--------|
| `generate_golden_fixtures.ps1` | 3,666 B | 🟡 | Generate golden test fixtures from samples | ✅ |
| `run_docker_dogfood.ps1` | 2,938 B | 🟡 | Dogfood test inside Docker | ✅ |
| `run_vps_dry_run.ps1` | 4,172 B | 🟡 | VPS dry run (PowerShell) | ✅ |

---

## 13. `tests/` — Test Suite

### Test Files (21 files, all have `if __name__ == "__main__"`)

| File | Size | Badge | Role | Active |
|------|------|-------|------|--------|
| `test_causal.py` | 716 B | 🔵 | OnlineCausalGraphLearner tests | ✅ |
| `test_cli_golden_acceptance.py` | 13,696 B | 🔵 | Golden acceptance: CLI output vs fixtures | ✅ |
| `test_cross_source_intervention.py` | 3,438 B | 🔵 | Cross-source intervention accuracy | ✅ |
| `test_decision_orchestrator.py` | 56,312 B | 🔵 | Decision orchestration (comprehensive) | ✅ |
| `test_docker_docs.py` | 3,583 B | 🔵 | Docker documentation consistency | ✅ |
| `test_dsl.py` | 884 B | 🔵 | FeatureDSL tests | ✅ |
| `test_experiments.py` | 16,355 B | 🔵 | Experiment framework | ✅ |
| `test_frontier.py` | 3,966 B | 🔵 | FrontierExplorer tests | ✅ |
| `test_frontier_contract.py` | 6,238 B | 🔵 | Frontier contract tests | ✅ |
| `test_frontier_hardening.py` | 8,637 B | 🔵 | Frontier hardening/robustness | ✅ |
| `test_independence_stability.py` | 2,649 B | 🔵 | Independence stability | ✅ |
| `test_package_entry.py` | 6,501 B | 🔵 | CLI entry point and import tests | ✅ |
| `test_pipeline.py` | 1,558 B | 🔵 | Pipeline integration | ✅ |
| `test_real_data_contract.py` | 7,401 B | 🔵 | Real data contract | ✅ |
| `test_real_validation_runner.py` | 20,880 B | 🔵 | RealValidationRunner tests | ✅ |
| `test_replication.py` | 13,239 B | 🔵 | Replication study tests | ✅ |
| `test_spl_decision_validation.py` | 33,584 B | 🔵 | SPL decision validation | ✅ |
| `test_spl_tls_analyze.py` | 25,392 B | 🔵 | Main CLI tests | ✅ |
| `test_tls_policy_adapter.py` | 26,419 B | 🔵 | TLS Policy Adapter tests | ✅ |
| `test_v71_hardening.py` | 4,476 B | 🔵 | v7.1 hardening tests | ✅ |
| `test_weakness_mapper.py` | 12,603 B | 🔵 | Weakness Mapper tests | ✅ |

### Test Fixtures: `tests/fixtures/cli_golden/`

| Directory | Files | Badge | Role | Active |
|-----------|-------|-------|------|--------|
| `console/` | 13 `.txt` | 🔵 | Golden console output fixtures (12 scenarios + batch) | ✅ |
| `json/` | 13 `.json` | 🔵 | Golden JSON output fixtures | ✅ |
| `markdown/` | 13 `.md` | 🔵 | Golden Markdown output fixtures | ✅ |

Fixture files cover: `valid_tls`, `expired_cert`, `self_signed_cert`, `wrong_host_cert`, `untrusted_chain`, `incomplete_chain`, `dns_failure`, `connection_error`, `timeout`, `tls_handshake_failure`, `deprecated_tls`, `unknown_ssl_error`, `_batch_summary`.

---

## 14. `reports/` — Generated Reports

### `reports/dogfood/`

| File | Size | Badge | Role | Active |
|------|------|-------|------|--------|
| `DOGFOOD_REPORT.md` | 7,734 B | 🔴 | Dogfood test report | ❌ generated |
| `dogfood_results.json` | 50,927 B | 🔴 | Dogfood result data | ❌ generated |

### `reports/local_real_validation/`

| File | Size | Badge | Role | Active |
|------|------|-------|------|--------|
| `DECISION_ORCHESTRATION_REPORT.md` | 7,740 B | 🔴 | Orchestration behavior report | ❌ generated |
| `DECISION_ORCHESTRATION_SEMANTICS_REPORT.md` | 7,740 B | 🔴 | Semantics audit report | ❌ generated |
| `MIXED_TLS_VALIDATION_REPORT.md` | 5,370 B | 🔴 | Mixed TLS validation | ❌ generated |
| `OPERATING_PROFILE_COMPARISON.md` | 3,176 B | 🔴 | Profile comparison | ❌ generated |
| `PHASE6_BASELINE_COMPARISON.md` | 8,137 B | 🔴 | Phase 6 comparison | ❌ generated |
| `REAL_DATA_LOCAL_REPORT.md` | 7,129 B | 🔴 | Real data local report | ❌ generated |
| `SPL_DECISION_VALIDATION_REPORT.md` | 3,394 B | 🔴 | SPL decision validation | ❌ generated |
| `SPL_DECISION_VALIDATION_REPORT_holdout.md` | 3,917 B | 🔴 | Holdout report | ❌ generated |
| `SPL_DECISION_VALIDATION_REPORT_observation.md` | 2,921 B | 🔴 | Observation report | ❌ generated |
| `SPL_DECISION_VALIDATION_REPORT_proxy-trained.md` | 2,962 B | 🔴 | Proxy-trained report | ❌ generated |
| `STRATIFIED_BENCHMARK_REPORT.md` | 8,755 B | 🔴 | Stratified benchmark | ❌ generated |
| `TLS_POLICY_ADAPTER_REPORT.md` | 7,286 B | 🔴 | Policy adapter report | ❌ generated |
| `VALIDATION_MODE_COMPARISON.md` | 3,742 B | 🔴 | Validation mode comparison | ❌ generated |
| `benchmark_probe_cache.json` | 117,300 B | 🔴 | Probe cache | ❌ generated |
| `classification_accuracy.json` | 1,915 B | 🔴 | Classification accuracy | ❌ generated |
| `decision_orchestration_results.json` | 116,564 B | 🔴 | Orchestration results | ❌ generated |
| `operating_profile_results.json` | 416,479 B | 🔴 | Operating profile results (largest file) | ❌ generated |
| `spl_decision_validation_results.json` | 57,984 B | 🔴 | SPL decision validation | ❌ generated |
| `spl_decision_validation_results_holdout.json` | 18,861 B | 🔴 | Holdout results | ❌ generated |
| `spl_decision_validation_results_observation.json` | 56,174 B | 🔴 | Observation results | ❌ generated |
| `spl_decision_validation_results_proxy-trained.json` | 56,199 B | 🔴 | Proxy-trained results | ❌ generated |
| `tls_policy_adapter_results.json` | 43,256 B | 🔴 | Policy adapter results | ❌ generated |
| `tls_probe_results.json` | 58,524 B | 🔴 | Probe results | ❌ generated |
| `tls_probe_results.jsonl` | 46,338 B | 🔴 | Probe results (line-delimited JSON) | ❌ generated |

### `reports/local_real_validation/stratified_runs/`

| Files | Size | Badge | Role | Active |
|-------|------|-------|------|--------|
| `run_01.json` … `run_10.json` | ~38 KB each | 🔴 | Stratified benchmark run data | ❌ generated |

---

## 15. `reports_smoke/` — Smoke Test Reports

| File | Size | Badge | Role | Active |
|------|------|-------|------|--------|
| `PROMOTION_READINESS.md` | 3,924 B | 🔴 | Smoke promotion readiness | ❌ generated |
| `REPLICATION_REPORT.md` | 3,845 B | 🔴 | Smoke replication report | ❌ generated |

---

## 16. `docs/` — Documentation (40 Markdown files)

| File | Size | Badge | Role | Active |
|------|------|-------|------|--------|
| `API.md` | 2,863 B | 🟣 | API reference | ✅ |
| `ARCHITECTURE.md` | 862 B | 🟣 | System architecture | ✅ |
| `CLI_CONFIDENCE_FALLBACK_POLICY.md` | 2,588 B | 🟣 | CLI fallback policy | ✅ |
| `CLI_EXAMPLES.md` | 2,430 B | 🟣 | CLI usage examples | ✅ |
| `CLI_GOLDEN_TESTING.md` | 1,507 B | 🟣 | Golden testing methodology | ✅ |
| `CLI_OUTPUT_SCHEMA.md` | 2,728 B | 🟣 | CLI output schema | ✅ |
| `CLI_USAGE.md` | 2,752 B | 🟣 | CLI usage guide | ✅ |
| `COLLAPSE_DETECTION.md` | 1,299 B | 🟣 | Collapse detection in Frontier | ✅ |
| `CONSTRAINTS.md` | 1,746 B | 🟣 | Pipeline constraints | ✅ |
| `CURRENT_PROJECT_STATUS.md` | 1,304 B | 🟣 | Current status snapshot | ✅ |
| `DATASET_ACQUISITION_GUIDE.md` | 1,399 B | 🟣 | Dataset acquisition guide | ✅ |
| `DECISION_ORCHESTRATION_POLICY.md` | 5,440 B | 🟣 | Decision orchestration policy | ✅ |
| `DECISION_SEMANTICS_AUDIT.md` | 9,187 B | 🟣 | Decision semantics audit | ✅ |
| `DIFFICULTY_MODEL.md` | 2,291 B | 🟣 | Difficulty model for Frontier | ✅ |
| `DOCKER_USAGE.md` | 1,780 B | 🟣 | Docker usage instructions | ✅ |
| `DOGFOOD_FEEDBACK_TEMPLATE.md` | 883 B | 🟣 | Dogfood feedback template | ✅ |
| `DOGFOOD_FINDINGS.md` | 3,826 B | 🟣 | Dogfood test findings | ✅ |
| `EXTENSION_POINTS.md` | 1,141 B | 🟣 | Developer extension points | ✅ |
| `FRONTIER_VALIDATION_REPORT.md` | 1,637 B | 🟣 | Frontier validation report | ✅ |
| `INSTALL.md` | 2,216 B | 🟣 | Installation guide | ✅ |
| `KNOWN_LIMITATIONS.md` | 1,389 B | 🟣 | Known limitations | ✅ |
| `LOCAL_BETA_FREEZE_MANIFEST.md` | 3,230 B | 🟣 | Beta freeze manifest | ✅ |
| `LOCAL_DOCKER_VALIDATION.md` | 720 B | 🟣 | Local Docker validation | ✅ |
| `OPERATING_PROFILES.md` | 1,199 B | 🟣 | Operating profiles documentation | ✅ |
| `ORCHESTRATION_SCORING_AUDIT.md` | 3,372 B | 🟣 | Orchestration scoring audit | ✅ |
| `PHASE5_PHASE6_METHOD_COMPARISON.md` | 4,288 B | 🟣 | Phase 5 vs Phase 6 comparison | ✅ |
| `PRODUCTION_RUNBOOK.md` | 3,422 B | 🟣 | Production runbook | ✅ |
| `REAL_DATA_VALIDATION_PLAN.md` | 3,050 B | 🟣 | Real data validation plan | ✅ |
| `REAL_TLS_DATA_CONTRACT.md` | 3,614 B | 🟣 | Real TLS data contract | ✅ |
| `REAL_TLS_EVIDENCE_CONTRACT.md` | 2,522 B | 🟣 | Real TLS evidence contract | ✅ |
| `RELEASE_CHECKLIST.md` | 1,537 B | 🟣 | Release checklist | ✅ |
| `RELEASE_NOTES_0.1.0b0.md` | 4,615 B | 🟣 | Release notes | ✅ |
| `REPRODUCIBILITY_AUDIT.md` | 2,673 B | 🟣 | Reproducibility audit | ✅ |
| `TEST_SUITE_STATUS.md` | 1,573 B | 🟣 | Test suite status | ✅ |
| `TLS_PROBE_LIMITATION_AUDIT.md` | 8,369 B | 🟣 | TLS probe limitation audit | ✅ |
| `TLS_RISK_POLICY_ADAPTER.md` | 6,063 B | 🟣 | TLS risk policy adapter | ✅ |
| `VALIDATION_LEAKAGE_AUDIT.md` | 2,902 B | 🟣 | Validation leakage audit | ✅ |
| `VERSIONING.md` | 977 B | 🟣 | Versioning strategy | ✅ |
| `VPS_DRY_RUN.md` | 2,273 B | 🟣 | VPS dry run documentation | ✅ |
| `VPS_DRY_RUN_REPORT_TEMPLATE.md` | 2,178 B | 🟣 | VPS dry run report template | ✅ |
| `ARTIFACT_INTEGRITY_AUDIT.md` | new | 🟣 | Artifact integrity audit (this report) | ✅ |
| `PROJECT_ARTIFACT_INVENTORY.md` | new | 🟣 | Project artifact inventory (this report) | ✅ |

---

## 17. Build/Cache Artifacts (Excluded from Source Inventory)

| Path | Contents | Badge | Regenerable |
|------|----------|-------|:-----------:|
| `spl_tls_analyze.egg-info/` | 6 files: PKG-INFO, requires.txt, SOURCES.txt, entry_points.txt, top_level.txt | ⚪ | ✅ `pip install -e .` |
| `spl_v7.egg-info/` | 5 files: PKG-INFO, requires.txt, SOURCES.txt, top_level.txt | ⚪ | ✅ `pip install -e .` |
| `__pycache__/` (7 directories) | CPython 3.14 bytecode (`.pyc` files) | ⚪ | ✅ `python -m compileall` |
| `.pytest_cache/` | Pytest cache data | ⚪ | ✅ `pytest` |

---

## 18. Generation Agent Summary

| Agent | Script | Produces |
|-------|--------|----------|
| `examples/demo.py` | Pipeline demo | `dashboard.html`, `v71_graph_snapshot.json` |
| `scripts/run_weakness_mapper.py` | Weakness mapping | `capability_report.json` |
| `scripts/run_local_tls_validation.py` | Local TLS validation | `reports/local_real_validation/*` |
| `scripts/run_decision_orchestration_benchmark.py` | Orchestration benchmark | `reports/local_real_validation/DECISION_ORCHESTRATION_*` |
| `scripts/run_tls_policy_adapter_benchmark.py` | Adapter benchmark (planned, never committed) | — |
| `scripts/run_stratified_benchmark.py` | Stratified benchmark (planned, never committed) | — |
| `scripts/run_real_tls_spl_decision_validation.py` | SPL decision validation (planned, never committed) | — |
| `scripts/run_dogfood_cli.py` | Dogfood test | `reports/dogfood/*` |
| `scripts/run_replication.py` | Replication study | `experiments/replication/*` |
| `scripts/generate_golden_fixtures.ps1` | Golden fixtures | `tests/fixtures/cli_golden/{console,json,markdown}/*` |
| `scripts/verify_release.py` | Release verification | Console output (no artifact) |

---

## 19. Summary Tables

### By Badge

| Badge | Category | File Count | Approx Size |
|-------|----------|:----------:|:-----------:|
| 🟢 **RUNTIME** | Source code | 42 `.py` files | ~350 KB |
| 🟡 **BUILD** | Config/build | 10 files | ~7 KB |
| 🔵 **TEST** | Tests + fixtures | 60 files | ~300 KB |
| 🟣 **DOC** | Documentation | 42 `.md` files | ~110 KB |
| 🟠 **DATA** | Domain data | 13 files | ~170 KB |
| 🔴 **GENERATED** | Reports, cache | 75+ files | ~1.5 MB |
| ⚪ **CACHE** | Bytecode, egg-info | ~300 files | ~2 MB |

### By Active Status

| Status | Count | Notes |
|--------|:-----:|-------|
| ✅ Active | ~200 | Source, build, test, docs, data |
| ❌ Stale/Generated | ~80 | Reports, generated artifacts |
| ⚠️ Duplicate | 3 | Root-level docs that duplicate `docs/` or `reports_smoke/` |

### By Variant (Complete vs Slim)

| Metric | Complete | Slim |
|--------|:--------:|:----:|
| Source `.py` files | 69 | 27 |
| Test files | 21 | 0 |
| Scripts | 14 | 0 |
| Core library packages | 7 | 3 |
| Build successful? | ✅ | ❌ |
| CLI works? | ✅ | ❌ |
