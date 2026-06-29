# Phase 26: Repository Hygiene & Artifact Audit

**Generated:** 2026-06-03T07:20:00Z
**Audit scope:** All non-excluded files in project root + subdirectories
**Excluded:** `.venv/`, `__pycache__/`, `.pytest_cache/`, `.git/`, `*.egg-info/`

---

## 1. Inventory Summary

| Directory | Files | Size | Purpose |
|---|---|---|---|
| `reports/` | ~70 | 6.7 MB | Generated probe results & audit reports |
| `experiments/` (code) | 12 | 111 KB | Experiment runner framework |
| `experiments/` (data) | ~90 | 656 KB | Generated experiment runs & campaign data |
| `docs/` | 54 | 449 KB | Documentation & phase reports |
| `scripts/` | 26 | 318 KB | CLI tools & validation scripts |
| `tests/` | 21 | 262 KB | Test suite |
| `datasets/` | 19 | 90 KB | Domain lists & expectations |
| `spl_v7/` | 9 | 103 KB | SPL Core (frozen) |
| `tls_policy_adapter/` | 4 | 14 KB | TLS policy adapter |
| `weakness_mapper/` | 6 | 19 KB | Weakness analysis |
| `frontier/` | 4 | 7 KB | Frontier extension |
| `decision_orchestrator/` | 4 | 31 KB | Decision orchestration |
| `configs/` | 3 | 2 KB | Pipeline configs |
| Root-level | 15 | 36 KB | Makefile, Dockerfile, README, etc. |
| **Total** | **~330** | **~8.8 MB** | |

---

## 2. Source Code — Active (Must Keep)

All source packages and scripts are **ACTIVE** — referenced by tests, docs, or production use.

| Package | Files | Status | Evidence |
|---|---|---|---|
| `spl_v7/` | 9 | **ACTIVE** | SPL Core; referenced by CI workflow (git diff check), Dockerfile, pyproject.toml |
| `tls_policy_adapter/` | 4 | **ACTIVE** | Referenced by scripts, tests, Dockerfile, pyproject.toml |
| `decision_orchestrator/` | 4 | **ACTIVE** | Referenced by scripts, tests, Dockerfile, pyproject.toml |
| `weakness_mapper/` | 6 | **ACTIVE** | Referenced by scripts, tests, Dockerfile, pyproject.toml |
| `frontier/` | 4 | **ACTIVE** | Referenced by Dockerfile, pyproject.toml |
| `scripts/*.py` | 18 | **ACTIVE** | Each script referenced by ≥1 test or ≥1 doc |
| `experiments/*.py` | 12 | **ACTIVE** | Referenced by scripts, tests, CI workflow |
| `tests/*.py` | 21 | **ACTIVE** | Run by pytest, CI workflow |

---

## 3. Datasets — Classification

| File | Size | Classification | References | Notes |
|---|---|---|---|---|
| `datasets/reliability_benchmark_domains.txt` | 3 KB | **A. ACTIVE** | `scripts/run_reliability_campaign.py`, `docs/OPERATIONAL_RELIABILITY_REPORT.md` | Phase 25 frozen benchmark |
| `datasets/real_tls_seed_domains.txt` | 3 KB | **A. ACTIVE** | Makefile, `run_local_tls_validation.py`, docs | Foundation of mixed/train/holdout datasets |
| `datasets/real_tls_mixed_domains.txt` | 2 KB | **A. ACTIVE** | `run_real_tls_spl_decision_validation.py`, `run_local_tls_validation.py` | Mixed-domain validation |
| `datasets/real_tls_mixed_expected.json` | 5 KB | **A. ACTIVE** | `run_local_tls_validation.py` (EXPECTED_LABELS_FILE) | Expected labels for mixed domains |
| `datasets/real_tls_train_domains.txt` | 3 KB | **A. ACTIVE** | `run_real_tls_spl_decision_validation.py` | SPL decision validation training set |
| `datasets/real_tls_train_expectations.json` | 3 KB | **A. ACTIVE** | `run_real_tls_spl_decision_validation.py` | SPL training expectations |
| `datasets/real_tls_holdout_domains.txt` | 1 KB | **A. ACTIVE** | `run_real_tls_spl_decision_validation.py` | SPL holdout validation |
| `datasets/real_tls_holdout_expectations.json` | 2 KB | **A. ACTIVE** | `run_real_tls_spl_decision_validation.py` | SPL holdout expectations |
| `datasets/real_tls_decision_expectations.json` | 5 KB | **A. ACTIVE** | `run_real_tls_spl_decision_validation.py` | SPL decision expectations |
| `datasets/certifi_stress_domains.txt` | 1 KB | **A. ACTIVE** | `scripts/build_real_data_dataset.py` | Certifi stress test domains |
| `datasets/dogfood_domains.txt` | 1 KB | **A. ACTIVE** | `scripts/run_docker_dogfood.ps1`, docs | Dogfood testing |
| `datasets/adversarial_tls_domains.txt` | 3 KB | **A. ACTIVE** | `scripts/build_real_data_dataset.py`, `docs/ADVERSARIAL_VALIDATION_PLAN.md` | Adversarial test domains |
| `datasets/real_world_audit_domains.txt` | 2 KB | **A. ACTIVE** | `scripts/build_real_data_dataset.py`, audit reports | Real-world audit |
| `datasets/vps_dry_run_domains.txt` | 1 KB | **A. ACTIVE** | `scripts/run_vps_dry_run.ps1`, `.sh`, `verify_release.py` | VPS dry-run testing |
| `datasets/cli_golden_samples.json` | 13 KB | **A. ACTIVE** | `tests/test_cli_golden_acceptance.py` | CLI golden test fixtures |
| `datasets/ground_truth_domains.txt` | 1 KB | **A. ACTIVE** | `scripts/build_real_data_dataset.py` | Ground truth dataset source |
| `datasets/real_data_domains.txt` | 19 KB | **B. HISTORICAL** | Phase 22 source; referenced by `docs/REAL_DATA_VALIDATION_REPORT.md` | Preserved for traceability |
| `datasets/real_tls_benchmark_domains.txt` | 3 KB | **C. SUPERSEDED** | Only by `build_real_data_dataset.py` | Replaced by reliability_benchmark_domains.txt |
| `datasets/real_tls_benchmark_expectations.json` | 15 KB | **C. SUPERSEDED** | Not referenced by any active script | Superseded by mixed_expected |

**Total dataset weight:** 18 files, 90 KB

---

## 4. Documentation — Classification

### 4.1 Phase Reports (Active)

| File | Size | Status | Notes |
|---|---|---|---|
| `docs/REAL_DATA_VALIDATION_REPORT.md` | 24 KB | **A. ACTIVE** | Cross-referenced by Phase 24 closure report |
| `docs/MEASUREMENT_VALIDITY_AUDIT.md` | 22 KB | **A. ACTIVE** | Cross-referenced by Phase 24 closure report |
| `docs/CLASSIFICATION_ACCURACY_CLOSURE.md` | 11 KB | **A. ACTIVE** | Cross-referenced by Phase 25 operational report |
| `docs/OPERATIONAL_RELIABILITY_REPORT.md` | 17 KB | **A. ACTIVE** | Phase 25 deliverable |
| `docs/REPOSITORY_HYGIENE_AUDIT.md` | (this) | **A. ACTIVE** | Phase 26 deliverable |

### 4.2 Foundational Documentation (Active)

| File | Status | Evidence |
|---|---|---|
| `README.md` | **A. ACTIVE** | Project entry point; cross-references 20+ docs |
| `ARCHITECTURE.md` | **A. ACTIVE** | Referenced by multiple docs |
| `API.md` | **A. ACTIVE** | Referenced by docs |
| `INSTALL.md` | **A. ACTIVE** | Referenced by reprod audit, CLI usage, release checklist |
| `CONSTRAINTS.md` | **A. ACTIVE** | Project constraints doc |
| `PROJECT_MAP.md` | **A. ACTIVE** | Referenced by extension points doc |
| `PROJECT_STATUS.md` | **A. ACTIVE** | Project status |
| `PROMOTION_READINESS.md` (root) | **A. ACTIVE** | Referenced by docs |
| `RELEASE_CHECKLIST.md` (root) | **A. ACTIVE** | Referenced by reprod audit, hygiene report |
| `RELEASE_NOTES_0.1.0b0.md` | **A. ACTIVE** | Cross-referenced by release checklist, CLI usage, README |

### 4.3 Operational & Policy Docs (Active)

| File | Status | Evidence |
|---|---|---|
| `CLI_USAGE.md` | **A. ACTIVE** | Referenced by 5+ docs and README |
| `CLI_EXAMPLES.md` | **A. ACTIVE** | Referenced by release checklist, README |
| `CLI_GOLDEN_TESTING.md` | **A. ACTIVE** | Referenced by CLI output schema, README |
| `CLI_OUTPUT_SCHEMA.md` | **A. ACTIVE** | Cross-referenced by CLI examples, usage, golden testing |
| `OPERATING_PROFILES.md` | **A. ACTIVE** | Referenced by CLI usage, docker usage, README |
| `DECISION_ORCHESTRATION_POLICY.md` | **A. ACTIVE** | Referenced by adapter docs, CLI usage, README |
| `TLS_RISK_POLICY_ADAPTER.md` | **A. ACTIVE** | Cross-referenced by leakage audit, evidence contract, README |
| `CLI_CONFIDENCE_FALLBACK_POLICY.md` | **A. ACTIVE** | Cross-referenced by 5+ docs |
| `VERSIONING.md` | **A. ACTIVE** | Referenced by CLI usage, release checklist, README |
| `DOCKER_USAGE.md` | **A. ACTIVE** | Referenced by 7+ docs across the project |
| `VPS_DRY_RUN.md` | **A. ACTIVE** | Referenced by 5+ docs and README |
| `PRODUCTION_RUNBOOK.md` | **A. ACTIVE** | Operations reference |

### 4.4 Audit & Validation Docs (Active)

| File | Status | Evidence |
|---|---|---|
| `GROUND_TRUTH_ACCURACY_REPORT.md` | **B. HISTORICAL** | Not referenced by any code or doc |
| `CERTIFI_INTEGRATION_REPORT.md` | **A. ACTIVE** | Linked from test status |
| `CERTIFI_STRESS_TEST_REPORT.md` | **A. ACTIVE** | Referenced by docs |
| `FRONTIER_VALIDATION_REPORT.md` | **A. ACTIVE** | Referenced by CURRENT_PROJECT_STATUS.md |
| `TLS_PROBE_LIMITATION_AUDIT.md` | **A. ACTIVE** | Cross-referenced by KNOWN_LIMITATIONS.md |
| `PHASE5_PHASE6_METHOD_COMPARISON.md` | **A. ACTIVE** | Cross-referenced by leakage audit, KNOWN_LIMITATIONS |
| `REAL_DATA_VALIDATION_PLAN.md` | **A. ACTIVE** | Referenced by PROMOTION_READINESS.md |
| `REAL_TLS_DATA_CONTRACT.md` | **A. ACTIVE** | Referenced by CURRENT_PROJECT_STATUS, validation plan |
| `REAL_WORLD_AUDIT_DATASET.md` | **A. ACTIVE** | Referenced by real world audit report |
| `LOCAL_DOCKER_VALIDATION.md` | **B. HISTORICAL** | Not referenced by any code; superseded by DOCKER_USAGE.md |

### 4.5 Specialized / Less Referenced Docs

| File | Status | Evidence |
|---|---|---|
| `DOGFOOD_FEEDBACK_TEMPLATE.md` | **A. ACTIVE** | Referenced by TEST_SUITE_STATUS.md |
| `ADVERSARIAL_VALIDATION_PLAN.md` | **A. ACTIVE** | Referenced by its own content |
| `DATASET_ACQUISITION_GUIDE.md` | **A. ACTIVE** | Referenced by `tests/test_real_data_contract.py` |
| `VPS_DRY_RUN_REPORT_TEMPLATE.md` | **A. ACTIVE** | Referenced by LOCAL_BETA_FREEZE_MANIFEST, release checklist |
| `COLLAPSE_DETECTION.md` | **B. HISTORICAL** | Investigation artifact; not referenced by any doc |
| `DIFFICULTY_MODEL.md` | **B. HISTORICAL** | Investigation artifact; not referenced by any doc |
| `LOCAL_BETA_FREEZE_MANIFEST.md` | **A. ACTIVE** | Referenced by 5+ docs |
| `DECISION_SEMANTICS_AUDIT.md` | **A. ACTIVE** | Referenced by KNOWN_LIMITATIONS, CLI usage, README |
| `REPOSITORY_HYGIENE_REPORT.md` | **C. SUPERSEDED** | Superseded by this report |
| `PROJECT_ARTIFACT_INVENTORY.md` | **C. SUPERSEDED** | Superseded by this audit |
| `REPRODUCIBILITY_AUDIT.md` | **B. HISTORICAL** | Not referenced by code |
| `VALIDATION_LEAKAGE_AUDIT.md` | **B. HISTORICAL** | Not referenced by code |
| `ORCHESTRATION_SCORING_AUDIT.md` | **B. HISTORICAL** | Referenced by KNOWN_LIMITATIONS.md (×1) |
| `ARTIFACT_INTEGRITY_AUDIT.md` | **C. SUPERSEDED** | Superseded by this audit |
| `TEST_SUITE_STATUS.md` | **A. ACTIVE** | Referenced by README |
| `EXTENSION_POINTS.md` | **A. ACTIVE** | Referenced by PROJECT_MAP.md, CURRENT_PROJECT_STATUS.md |
| `KNOWN_LIMITATIONS.md` | **A. ACTIVE** | Referenced by 8+ docs and README |
| `CURRENT_PROJECT_STATUS.md` | **A. ACTIVE** | Cross-referenced by validation docs |

---

## 5. Generated Reports — Classification

### 5.1 JSON Probe Results (Generated Artifacts)

| File | Size | Classification | Rationale |
|---|---|---|---|
| `reports/real_data_validation/campaign_results.json` | 1,879 KB | **C. SUPERSEDED** | Phase 22 raw results; superseded by docs summary. Can regenerate from `real_data_domains.txt` |
| `reports/certifi_stress_test/certifi_results.json` | 881 KB | **D. TEMPORARY** | Certifi stress test results; reproducible |
| `reports/certifi_stress_test/baseline_platform.json` | 880 KB | **D. TEMPORARY** | Baseline comparison; reproducible |
| `reports/certifi_stress_test/full_results.json` | 286 KB | **D. TEMPORARY** | Full results; reproducible |
| `reports/certifi_stress_test/summary.json` | 15 KB | **D. TEMPORARY** | Summary; reproducible |
| `reports/adversarial_validation/adversarial_results.json` | 230 KB | **D. TEMPORARY** | Adversarial test results; reproducible |
| `reports/adversarial_validation/adversarial_summary.json` | 3 KB | **D. TEMPORARY** | Summary; reproducible |
| `reports/ground_truth_audit/probe_results.json` | 197 KB | **D. TEMPORARY** | Ground truth probe results; reproducible |
| `reports/ground_truth_audit/ground_truth.json` | 140 KB | **D. TEMPORARY** | Ground truth data; reproducible |
| `reports/ground_truth_audit/error_analysis.json` | 6 KB | **D. TEMPORARY** | Error analysis; reproducible |
| `reports/ground_truth_audit/confusion_matrix.json` | 6 KB | **D. TEMPORARY** | Confusion matrix; reproducible |
| `reports/certifi_validation/certifi_adversarial.json` | 232 KB | **D. TEMPORARY** | Certifi comparison; reproducible |
| `reports/certifi_validation/baseline_adversarial.json` | 232 KB | **D. TEMPORARY** | Baseline; reproducible |
| `reports/certifi_validation/certifi_real_world.json` | 168 KB | **D. TEMPORARY** | Real-world comparison; reproducible |
| `reports/certifi_validation/baseline_real_world.json` | 167 KB | **D. TEMPORARY** | Baseline; reproducible |
| `reports/certifi_validation/certifi_comparison.json` | 5 KB | **D. TEMPORARY** | Comparison summary; reproducible |
| `reports/real_world_audit/real_world_audit_results.json` | 164 KB | **D. TEMPORARY** | Audit results; reproducible |
| `reports/real_world_audit/real_world_audit_summary.json` | 5 KB | **D. TEMPORARY** | Audit summary; reproducible |
| `reports/generated/v71_graph_snapshot.json` | 140 KB | **D. TEMPORARY** | Graph snapshot; reproducible |
| `reports/generated/capability_report.json` | 10 KB | **D. TEMPORARY** | Capability report; reproducible |
| `reports/generated/dashboard.html` | 50 KB | **D. TEMPORARY** | Dashboard; reproducible |
| `reports/decision_path_audit/decision_path_traces.json` | 39 KB | **D. TEMPORARY** | Decision paths; reproducible |
| `reports/decision_path_audit/decision_path_breakdown.json` | 30 KB | **D. TEMPORARY** | Breakdown; reproducible |
| `reports/decision_path_audit/decision_path_summary.json` | 4 KB | **D. TEMPORARY** | Summary; reproducible |
| `reports/dogfood/dogfood_results.json` | 50 KB | **D. TEMPORARY** | Dogfood results; reproducible |
| `reports/local_real_validation/operating_profile_results.json` | 407 KB | **D. TEMPORARY** | Profile benchmark; reproducible |
| `reports/local_real_validation/benchmark_probe_cache.json` | 115 KB | **D. TEMPORARY** | Probe cache; reproducible |
| `reports/local_real_validation/decision_orchestration_results.json` | 114 KB | **D. TEMPORARY** | Decision orchestration; reproducible |
| `reports/local_real_validation/tls_probe_results.json` | 57 KB | **D. TEMPORARY** | TLS probe results; reproducible |
| `reports/local_real_validation/tls_probe_results.jsonl` | 45 KB | **D. TEMPORARY** | JSONL variant; reproducible |
| `reports/local_real_validation/spl_decision_validation_results*.json` (×3) | 57+55+55 KB | **D. TEMPORARY** | SPL decision validation; reproducible |
| `reports/local_real_validation/tls_policy_adapter_results.json` | 42 KB | **D. TEMPORARY** | Adapter results; reproducible |
| `reports/local_real_validation/classification_accuracy.json` | 2 KB | **D. TEMPORARY** | Accuracy; reproducible |
| `reports/reliability_campaign/campaigns.json` | 616 KB | **D. TEMPORARY** | Phase 25 raw campaign data; reproducible |
| `reports/reliability_campaign/domain_stability_detail.json` | 140 KB | **D. TEMPORARY** | Stability detail; reproducible |
| `reports/reliability_campaign/stability_analysis.json` | 43 KB | **D. TEMPORARY** | Stability analysis; reproducible |
| `reports/reliability_campaign/reliability_scorecard.md` | 3 KB | **A. ACTIVE** | Scorecard summary (lightweight) |
| `reports/measurement_audit_*.json` (×4) | 2-29 KB | **B. HISTORICAL** | Phase 23 measurement audit data |
| `reports/security_gap_audit/security_gap_summary.json` | 9 KB | **D. TEMPORARY** | Security gap audit; reproducible |
| `reports/spl_integration_audit/spl_integration_summary.json` | 9 KB | **D. TEMPORARY** | SPL integration audit; reproducible |

**Total generated JSON weight:** ~6,500 KB (6.4 MB)

### 5.2 Experiment Run Data (Generated Artifacts)

| Path | Files | Size | Classification |
|---|---|---|---|
| `experiments/raw_runs/` | 24 | 138 KB | **D. TEMPORARY** |
| `experiments/backward_check/` | 22 | 126 KB | **D. TEMPORARY** |
| `experiments/replication/runs/` | 44 | 259 KB | **D. TEMPORARY** |
| `experiments/replication/runs/campaign_011/` | 23 | 138 KB | **D. TEMPORARY** |
| `experiments/replication/aggregate_results.json` | 1 | 4 KB | **D. TEMPORARY** |
| `experiments/replication_smoke/` | 2 | 3 KB | **D. TEMPORARY** |

**Total experiment run data weight:** ~668 KB

---

## 6. Storage Analysis

### 6.1 Largest Files

| File | Size | % of repo |
|---|---|---|
| `reports/real_data_validation/campaign_results.json` | 1,879 KB | 21.3% |
| `reports/certifi_stress_test/certifi_results.json` | 881 KB | 10.0% |
| `reports/certifi_stress_test/baseline_platform.json` | 880 KB | 10.0% |
| `reports/reliability_campaign/campaigns.json` | 616 KB | 7.0% |
| `reports/local_real_validation/operating_profile_results.json` | 407 KB | 4.6% |
| `reports/certifi_stress_test/full_results.json` | 286 KB | 3.2% |
| `reports/certifi_validation/certifi_adversarial.json` | 232 KB | 2.6% |
| `reports/certifi_validation/baseline_adversarial.json` | 232 KB | 2.6% |
| `reports/adversarial_validation/adversarial_results.json` | 230 KB | 2.6% |
| Top 9 files | **5,643 KB** | **64.1%** |

### 6.2 Duplicated Data

| Pattern | Locations | Dedup Potential |
|---|---|---|
| TLS probe results | `reports/local_real_validation/tls_probe_results.json` + `.jsonl` | JSON and JSONL are redundant; keep JSONL only |
| Certifi stress results | `certifi_results.json` + `baseline_platform.json` + `full_results.json` | Similar data in 3 files |
| Ground truth audit | `probe_results.json` + `ground_truth.json` + `error_analysis.json` | 3 files, similar probe data |

### 6.3 Recoverable Space Estimate

| Category | Size | Classification | Recovery Potential |
|---|---|---|---|
| Experiment run data (raw_runs, backward_check, replication campaigns) | 668 KB | TEMPORARY | High |
| Certifi stress test results | 2,062 KB | TEMPORARY | High |
| Real data validation raw results | 1,879 KB | SUPERSEDED | Medium (historical value) |
| Local real validation generated JSON | 1,000 KB | TEMPORARY | High |
| Certifi validation comparisons | 811 KB | TEMPORARY | High |
| Ground truth probe results | 350 KB | TEMPORARY | High |
| Adversarial validation results | 253 KB | TEMPORARY | High |
| Real world audit results | 184 KB | TEMPORARY | High |
| Decision path audit traces | 97 KB | TEMPORARY | High |
| Dogfood results | 58 KB | TEMPORARY | High |
| Superseded docs (REPOSITORY_HYGIENE_REPORT.md, PROJECT_ARTIFACT_INVENTORY.md, ARTIFACT_INTEGRITY_AUDIT.md) | ~80 KB | SUPERSEDED | High |
| Historical docs (LOCAL_DOCKER_VALIDATION.md, COLLAPSE_DETECTION.md, DIFFICULTY_MODEL.md, GROUND_TRUTH_ACCURACY_REPORT.md, VALIDATION_LEAKAGE_AUDIT.md, REPRODUCIBILITY_AUDIT.md) | ~100 KB | HISTORICAL | Low (keep for traceability) |
| **Estimated recoverable** | **~7,300 KB** | | **83% of repo** |
| **Essential to keep** | **~1,500 KB** | | Source + tests + docs + datasets |

---

## 7. Safe Deletion Candidates

These files appear safe to remove. **Nothing should be deleted automatically** — this is a recommendation.

### 7.1 High Confidence (Temporary Generated Data)

| # | Path | Size | Reason |
|---|---|---|---|
| 1 | `reports/certifi_stress_test/` (4 files) | 2,062 KB | Generated; reproducible from `certifi_stress_domains.txt` |
| 2 | `reports/adversarial_validation/` (2 files) | 233 KB | Generated; reproducible from `adversarial_tls_domains.txt` |
| 3 | `reports/ground_truth_audit/` (4 files) | 349 KB | Generated; reproducible from `ground_truth_domains.txt` |
| 4 | `reports/certifi_validation/` (7 files) | 808 KB | Generated; reproducible |
| 5 | `reports/real_world_audit/` (3 files) | 174 KB | Generated; reproducible from `real_world_audit_domains.txt` |
| 6 | `reports/dogfood/` (2 files) | 58 KB | Generated; reproducible from `dogfood_domains.txt` |
| 7 | `reports/decision_path_audit/` (4 files) | 97 KB | Generated; reproducible |
| 8 | `reports/security_gap_audit/` (1 file) | 9 KB | Generated; reproducible |
| 9 | `reports/spl_integration_audit/` (1 file) | 9 KB | Generated; reproducible |
| 10 | `reports/local_real_validation/` (most JSON files, excluding .md) | ~900 KB | Generated; reproducible |
| 11 | `reports/generated/` (3 files) | 200 KB | Generated; reproducible (dashboard.html, v71_graph_snapshot.json, capability_report.json) |
| 12 | `experiments/raw_runs/` (24 files) | 138 KB | Generated; reproducible |
| 13 | `experiments/backward_check/` (22 files) | 126 KB | Generated; reproducible |
| 14 | `experiments/replication/runs/` (44 files) | 259 KB | Generated; reproducible |
| 15 | `experiments/replication/runs/campaign_011/` (23 files) | 138 KB | Generated; reproducible |
| 16 | `experiments/replication/aggregate_results.json` | 4 KB | Generated; reproducible |
| 17 | `experiments/replication_smoke/` (2 files) | 3 KB | Generated; reproducible |
| 18 | `reports/reliability_campaign/campaigns.json` | 616 KB | Generated; reproducible from benchmark |
| 19 | `reports/reliability_campaign/domain_stability_detail.json` | 140 KB | Generated; reproducible |
| 20 | `reports/reliability_campaign/stability_analysis.json` | 43 KB | Generated; reproducible |
| 21 | `reports/measurement_audit_*.json` (4 files) | 41 KB | Phase 23 audit data |
| **Total high confidence** | **~6,389 KB** | | |

### 7.2 Medium Confidence (Superseded)

| # | Path | Size | Reason | Replacement |
|---|---|---|---|---|
| 22 | `reports/real_data_validation/campaign_results.json` | 1,879 KB | Raw Phase 22 results | Summary in docs/REAL_DATA_VALIDATION_REPORT.md |
| 23 | `docs/REPOSITORY_HYGIENE_REPORT.md` | ~20 KB | Superseded by this audit | `docs/REPOSITORY_HYGIENE_AUDIT.md` |
| 24 | `docs/PROJECT_ARTIFACT_INVENTORY.md` | ~30 KB | Superseded by this audit | `docs/REPOSITORY_HYGIENE_AUDIT.md` |
| 25 | `docs/ARTIFACT_INTEGRITY_AUDIT.md` | ~30 KB | Superseded by this audit | `docs/REPOSITORY_HYGIENE_AUDIT.md` |
| 26 | `datasets/real_tls_benchmark_domains.txt` | 3 KB | Only referenced by build script | `datasets/reliability_benchmark_domains.txt` |
| 27 | `datasets/real_tls_benchmark_expectations.json` | 15 KB | Not referenced by any script | — |
| **Total medium confidence** | **~1,977 KB** | | | |

### 7.3 Low Confidence (Historical — Keep for Traceability)

| # | Path | Size | Reason |
|---|---|---|---|
| 28 | `datasets/real_data_domains.txt` | 19 KB | Original Phase 22 dataset; valuable for traceability |
| 29 | `docs/COLLAPSE_DETECTION.md` | ~10 KB | Investigation findings; historical value |
| 30 | `docs/DIFFICULTY_MODEL.md` | ~10 KB | Investigation findings; historical value |
| 31 | `docs/GROUND_TRUTH_ACCURACY_REPORT.md` | ~10 KB | Early phase report; historical value |
| 32 | `docs/LOCAL_DOCKER_VALIDATION.md` | ~10 KB | Docker validation; superseded by DOCKER_USAGE.md |
| 33 | `docs/REPRODUCIBILITY_AUDIT.md` | ~15 KB | Audit findings; historical value |
| 34 | `docs/VALIDATION_LEAKAGE_AUDIT.md` | ~15 KB | Audit findings; historical value |
| **Total low confidence** | **~89 KB** | | |

---

## 8. Risks of Deletion

### 8.1 Generated Data Deletion Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Loss of historical probe results for comparison | LOW | Docs summarize findings; regeneration is possible |
| Loss of measurement audit control data | LOW | Docs contain the analysis; raw IP/cert data is in reports |
| Loss of campaign raw data for Phase 22/25 | MEDIUM | Campaign parameters are documented; datasets are frozen |
| Someone may reference a JSON path in documentation | LOW | Only internal docs reference them; can be updated |

### 8.2 Dataset Deletion Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Loss of `real_data_domains.txt` (1,132 domains) | MEDIUM | The dataset is the largest curated domain list; referenced by Phase 22 docs |
| Loss of `real_tls_benchmark_*` | LOW | Not referenced by any active script; superseded |

### 8.3 Doc Deletion Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Loss of superseded hygiene/artifact audit docs | LOW | This report replaces them |
| Loss of historical investigation docs | LOW | May contain unique findings not summarized elsewhere |

---

## 9. SPL Core Status

**SPL Core (`spl_v7/`):** UNCHANGED — 9 files, 103 KB, no modifications in >24 hours. Frozen as required.

---

## 10. Final Assessment

| Criterion | Status |
|---|---|
| ✓ Entire repository audited | ~330 files across all directories |
| ✓ No files deleted | Audit only — no deletions performed |
| ✓ Safe deletion candidates documented | 34 candidates identified across 3 confidence levels |
| ✓ Dependency evidence provided | Full reference map for all datasets, docs, reports |
| ✓ Cleanup opportunities quantified | ~7.3 MB reclaimable (83% of repo) |
| ✓ SPL Core unchanged | Verified — no modifications |

### Key Findings

1. **83% of the repository is generated/reproducible data.** The essential code, tests, docs, and datasets occupy only ~1.5 MB. The remaining ~7.3 MB is JSON probe results, experiment runs, and generated reports that can be regenerated from source datasets and scripts.

2. **The largest cleanup target is `reports/`** (6.7 MB). Within that, 4 directories account for 58% of storage: `certifi_stress_test/` (2.1 MB), `real_data_validation/` (1.9 MB), `certifi_validation/` (0.8 MB), and `reliability_campaign/` (0.8 MB).

3. **Documentation has healthy cross-referencing.** Most docs are actively referenced by code, tests, or other docs. Only a handful of investigation docs are orphaned.

4. **No data duplication issues.** The JSON/JSONL pair for probe results is the only clear redundancy. The various experiment run directories contain different campaign data.

5. **If cleanup were performed**, the repository would shrink from ~8.8 MB to ~1.5 MB without losing any functional capability. All probe results can be regenerated, all experiment runs re-executed, and all reports rebuilt on demand.
