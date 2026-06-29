# Phase 26.1 — Cleanup Manifest

**Generated:** 2026-06-03
**Source:** `docs/REPOSITORY_HYGIENE_AUDIT.md` Section 7.1

---

## Deletion Policy

- **Delete ONLY**: High-Confidence Temporary/Generated/Superseded artifacts
- **Excluded**: measurement_audit_*.json (classified B. HISTORICAL in §5.1)
- **Excluded**: real_data_validation/campaign_results.json (Medium Confidence §7.2)
- **Excluded**: .md files (narrative reports, kept for traceability)
- **Excluded**: stratified_runs/ directory (test asserts existence)
- **Excluded**: PHASE6_BASELINE_COMPARISON.md (test asserts existence)
- **Excluded**: STRATIFIED_BENCHMARK_REPORT.md (test references it)

---

## Deletion Candidates

### 1. reports/certifi_stress_test/ (4 files)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| `certifi_results.json` | D. TEMPORARY | Generated; reproducible from certifi_stress_domains.txt | HIGH | Regenerate via run_adversarial_validation.py |
| `baseline_platform.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |
| `full_results.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |
| `summary.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |

### 2. reports/adversarial_validation/ (2 JSON files — keep ADVERSARIAL_VALIDATION_REPORT.md)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| `adversarial_results.json` | D. TEMPORARY | Generated; reproducible from adversarial_tls_domains.txt | HIGH | Regenerate via run_adversarial_validation.py |
| `adversarial_summary.json` | D. TEMPORARY | Generated summary; reproducible | HIGH | Regenerate |

### 3. reports/ground_truth_audit/ (4 files)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| `probe_results.json` | D. TEMPORARY | Generated; reproducible from ground_truth_domains.txt | HIGH | Regenerate |
| `ground_truth.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |
| `error_analysis.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |
| `confusion_matrix.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |

### 4. reports/certifi_validation/ (9 JSON files)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| `certifi_adversarial.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |
| `baseline_adversarial.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |
| `certifi_real_world.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |
| `baseline_real_world.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |
| `certifi_comparison.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |
| `cnn_certifi.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |
| `cnn_baseline.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |
| `walmart_certifi.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |
| `walmart_baseline.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |

### 5. reports/real_world_audit/ (2 JSON files — keep REAL_WORLD_AUDIT_REPORT.md)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| `real_world_audit_results.json` | D. TEMPORARY | Generated; reproducible from real_world_audit_domains.txt | HIGH | Regenerate |
| `real_world_audit_summary.json` | D. TEMPORARY | Generated summary; reproducible | HIGH | Regenerate |

### 6. reports/dogfood/ (1 JSON file — keep DOGFOOD_REPORT.md)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| `dogfood_results.json` | D. TEMPORARY | Generated; reproducible from dogfood_domains.txt | HIGH | Regenerate via run_dogfood_cli.py |

### 7. reports/decision_path_audit/ (3 JSON files — keep DECISION_PATH_AUDIT_REPORT.md)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| `decision_path_traces.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate via decision_path_audit.py |
| `decision_path_breakdown.json` | D. TEMPORARY | Generated breakdown; reproducible | HIGH | Regenerate |
| `decision_path_summary.json` | D. TEMPORARY | Generated summary; reproducible | HIGH | Regenerate |

### 8. reports/security_gap_audit/ (1 JSON file)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| `security_gap_summary.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |

### 9. reports/spl_integration_audit/ (1 JSON file)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| `spl_integration_summary.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |

### 10. reports/local_real_validation/ (11 JSON/JSONL files — keep all .md + stratified_runs/)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| `operating_profile_results.json` | D. TEMPORARY | Generated benchmark; reproducible | HIGH | Regenerate via run_decision_orchestration_benchmark.py |
| `benchmark_probe_cache.json` | D. TEMPORARY | Generated probe cache; reproducible | HIGH | Regenerate |
| `decision_orchestration_results.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate |
| `tls_probe_results.json` | D. TEMPORARY | Generated probe results; reproducible | HIGH | Regenerate via run_local_tls_validation.py |
| `tls_probe_results.jsonl` | D. TEMPORARY | JSONL variant; reproducible | HIGH | Regenerate |
| `spl_decision_validation_results.json` | D. TEMPORARY | Generated; reproducible | HIGH | Regenerate via run_real_tls_spl_decision_validation.py |
| `spl_decision_validation_results_holdout.json` | D. TEMPORARY | Generated holdout; reproducible | HIGH | Regenerate |
| `spl_decision_validation_results_observation.json` | D. TEMPORARY | Generated observation; reproducible | HIGH | Regenerate |
| `spl_decision_validation_results_proxy-trained.json` | D. TEMPORARY | Generated proxy-trained; reproducible | HIGH | Regenerate |
| `tls_policy_adapter_results.json` | D. TEMPORARY | Generated adapter results; reproducible | HIGH | Regenerate via run_tls_policy_adapter_benchmark.py |
| `classification_accuracy.json` | D. TEMPORARY | Generated accuracy; reproducible | HIGH | Regenerate |

### 11. reports/generated/ (3 files)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| `v71_graph_snapshot.json` | D. TEMPORARY | Generated graph snapshot; reproducible | HIGH | Regenerate via examples/demo.py |
| `capability_report.json` | D. TEMPORARY | Generated capability report; reproducible | HIGH | Regenerate via run_weakness_mapper.py |
| `dashboard.html` | D. TEMPORARY | Generated dashboard HTML; reproducible | HIGH | Regenerate via examples/demo.py |

### 12. experiments/raw_runs/ (24 JSON files — keep comparison_report.md)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| All 24 `*.json` files | D. TEMPORARY | Generated experiment run data; reproducible | HIGH | Regenerate via run_ofe_experiment.py |

### 13. experiments/backward_check/ (22 JSON files)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| All 22 `*.json` files | D. TEMPORARY | Generated backward check data; reproducible | HIGH | Regenerate |

### 14. experiments/replication/runs/ (55 JSON files including campaign_*/)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| All JSON files in runs/ + campaign_*/ | D. TEMPORARY | Generated replication campaign data; reproducible | HIGH | Regenerate via run_replication.py |

### 15. experiments/replication/aggregate_results.json (1 file)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| `aggregate_results.json` | D. TEMPORARY | Generated aggregate; reproducible | HIGH | Regenerate via run_replication.py |

### 16. experiments/replication_smoke/ (24 JSON files)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| All JSON files in replication_smoke/ | D. TEMPORARY | Generated smoke test data; reproducible | HIGH | Regenerate |

### 17. reports/reliability_campaign/ (3 JSON files — keep reliability_scorecard.md)
| File | Classification | Reason | Confidence | Replacement |
|------|---------------|--------|------------|-------------|
| `campaigns.json` | D. TEMPORARY | Generated campaign data; reproducible | HIGH | Regenerate via run_reliability_campaign.py |
| `domain_stability_detail.json` | D. TEMPORARY | Generated stability detail; reproducible | HIGH | Regenerate |
| `stability_analysis.json` | D. TEMPORARY | Generated analysis; reproducible | HIGH | Regenerate |

---

## Safety Exclusions

The following were **removed** from the deletion list after safety verification:

| Path | Reason Excluded |
|------|----------------|
| `reports/measurement_audit_*.json` (4 files) | Classified B. HISTORICAL in §5.1; not D. TEMPORARY |
| `reports/real_data_validation/campaign_results.json` | Medium Confidence (§7.2); not High Confidence |
| `reports/local_real_validation/stratified_runs/` | `test_spl_decision_validation.py:710` asserts directory existence |
| `reports/local_real_validation/PHASE6_BASELINE_COMPARISON.md` | `test_tls_policy_adapter.py:440` asserts file existence |
| `reports/local_real_validation/STRATIFIED_BENCHMARK_REPORT.md` | `test_spl_decision_validation.py:753` references file |
| All .md narrative reports | Kept for traceability; contain analysis not reproducible from JSON alone |

---

## Verification Summary

- **Total candidates in audit**: 34 files/directories
- **High Confidence candidates**: 20 groups (excluding #21 measurement_audit)
- **Files to delete**: ~163 JSON/JSONL/HTML files
- **Estimated space recovery**: ~5.7 MB
- **Excluded after safety check**: 5 groups (measurement_audit, stratified_runs, 2 .md files, campaign_results.json)
- **No Active artifacts removed**: Verified
- **No SPL Core modifications**: Verified
