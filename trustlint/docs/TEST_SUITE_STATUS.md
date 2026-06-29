# Test Suite Status

## Current Count: 530 tests

As of Phase 16 (VPS Dry Run), the project contains **530 passing tests** across 21 test files.
Count verified by both `unittest discover` and `pytest`.

## Test Distribution by File

| Test File | Test Count | Scope |
|-----------|-----------|-------|
| `tests/test_causal.py` | 1 | OnlineCausalGraphLearner weight updates |
| `tests/test_cross_source_intervention.py` | 4 | Cross-source corroboration, intervention approximation |
| `tests/test_dsl.py` | 1 | Feature DSL parse and eval |
| `tests/test_experiments.py` | 34 | Accuracy, calibration, collapse, deltas, DSL builder, difficulty distribution, failure rate, weakness frequency, experiment report |
| `tests/test_frontier.py` | 2 | FrontierExplorer curriculum generation, structural signal bridge |
| `tests/test_frontier_contract.py` | 11 | Backward compat, metrics contract, reports contract |
| `tests/test_frontier_hardening.py` | 16 | Collapse detection, difficulty scoring, exploration session, exploration report |
| `tests/test_independence_stability.py` | 3 | Independence tests, stability gates |
| `tests/test_pipeline.py` | 1 | Memory pipeline end-to-end |
| `tests/test_real_data_contract.py` | 15 | Dataset contract validation, schema, format acceptance |
| `tests/test_real_validation_runner.py` | 18 | RealValidationRunner dataset validation, campaign logic, aggregation, structural output, SPL core protection |
| `tests/test_replication.py` | 29 | Replication campaigns, promotion readiness, statistics |
| `tests/test_spl_decision_validation.py` | 70 | **Phase 3.5/4/5** — leakage audit, modes, deprecated TLS, timeout policy, evidence contract, pipeline evaluation, holdout train/split/leakage, stratified benchmark |
| `tests/test_v71_hardening.py` | 5 | Causal graph, conditional independence, source verification, temporal stability |
| `tests/test_weakness_mapper.py` | 29 | WeaknessExtractor, WeaknessClusterer, WeaknessRegistry, CapabilityReporter, CapabilityBoundaryDetector |
| `tests/test_tls_policy_adapter.py` | 69 | **Phase 6/6.5** — classification coverage, severity mapping, valid/security/availability/deprecated TLS, ambiguous/chain trust, schema stability, expectations isolation, benchmark output, method comparison, probe limitation audit, baseline separation |
| `tests/test_decision_orchestrator.py` | 128 | **Phase 7/7.5/8/13** — 8 decision rules (incl. fallback), 18 confidence fallback tests, rule priority, OFE isolation, schema stability, mismatch classification, benchmark aggregation, report generation, save results, integration with adapter, safety scoring, probe-limited detection, REVIEW semantics, adapter guardrail, 16 profile tests |
| `tests/test_spl_tls_analyze.py` | 47 | **Phase 9/13** — CLI entry point, arg parsing, exit codes, mocked probe runs, recommended actions, structured text output, JSON/Markdown output, batch summary, schema stability, OFE isolation, 10 fallback tests (fallback allow, confidence source, console/json/md output, exit codes, batch count, DNS no-fallback) |
| `tests/test_cli_golden_acceptance.py` | 26 | **Phase 10/13** — Golden fixture snapshots (console, JSON, Markdown), console sections, JSON schema, exit codes, recommended actions, limitations, batch summary (+fallback count), batch snapshots |
| `tests/test_package_entry.py` | 11 | **Phase 11** — Console script entry point existence, main() through packaged module, JSON/Markdown output through package, batch through package, import paths for all modules |
| `tests/test_docker_docs.py` | 10 | **Phase 15** — Dockerfile integrity, .dockerignore, docs existence, no-ports/no-web, version tag, CLI entry point, non-root user |
| **Total** | **530** | |

## Is the Count Still 169?

**No — increased to 520.**

The test suite grew from the Phase 3 baseline of 169 to 520 through
Phases 3.5–14. No existing tests were removed, renamed, skipped, or excluded.

### New Tests (Phase 3.5 — Validation Hygiene & Leakage Audit)

| Test Class | Tests | What It Verifies |
|-----------|-------|------------------|
| `TestResolveClassification` | 8 | Deprecated TLS version detection (TLS 1.0, 1.1, 1.2, 1.3) |
| `TestDecisionToRiskLabel` | 8 | Post-hoc risk label mapping for security, availability, ambiguous, and unknown classifications |
| `TestClassificationToPolicy` | 8 | Completeness and correctness of CLASSIFICATION_TO_POLICY mapping |
| `TestProbeResultToEvidence` | 8 | Evidence artifact creation from probe results (valid, expired, timeout, DNS, proxy labels, integrity, tags) |
| `TestLoadDecisionExpectations` | 1 | Expectations loading from JSON |
| `TestComputePolicyConformance` | 4 | Conformance scoring correctness, mismatch detection, immutability of inputs |
| `TestPipelineRunEval` | 3 | Pipeline evaluation returns structured output for all domains with required fields and weakness flags |
| `TestObservationModeNoExpectations` | 1 | Pipeline works without expectations in observation mode |
| `TestDeprecatedTlsInEvidenceContract` | 3 | DEPRECATED_TLS_VERSION is in SECURITY set, not AVAILABILITY or AMBIGUOUS |
| `TestIncompleteVsUntrustedChain` | 3 | Both chain types map to SECURITY_RISK, both in security set, classified separately |
| `TestTimeoutClassificationPolicy` | 3 | TIMEOUT is in AVAILABILITY set, not SECURITY or AMBIGUOUS |

### New Tests (Phase 4 — Holdout Generalization Validation)

| Test Class | Tests | What It Verifies |
|-----------|-------|------------------|
| `TestLoadTrainExpectations` | 1 | Training expectations loading from JSON with label/weight format |
| `TestTrainPipelineWithLabels` | 3 | Training with external clean/dirty labels, label override of proxy labels, missing domain fallback |
| `TestTrainPipelineProxy` | 2 | Proxy-label training function, comparison between trained and cold-start pipelines |
| `TestHoldoutSplitIntegrity` | 3 | No domain in both train and holdout sets, train labels match train domains, holdout expectations match holdout domains |
| `TestHoldoutModeLeakage` | 3 | Holdout scoring after decisions, train expectations not used in eval scoring, train domains not scored with holdout |

### New Tests (Phase 6 — TLS Risk Policy Adapter)

| Test Class | Tests | What It Verifies |
|-----------|-------|------------------|
| `TestClassificationCoverage` | 6 | Every TLS classification maps to risk category, severity, failure family, action hint, policy reason; RISK_MAP matches classifications |
| `TestValidTlsMapping` | 4 | VALID_TLS → ACCEPTABLE_TLS / NONE / NONE family / NONE action |
| `TestSecurityRiskMapping` | 5 | EXPIRED_CERT, SELF_SIGNED_CERT, WRONG_HOST_CERT, UNTRUSTED_CHAIN map to SECURITY_RISK severity ≥ HIGH |
| `TestAvailabilityRiskMapping` | 3 | DNS_FAILURE, CONNECTION_ERROR, TIMEOUT → AVAILABILITY_RISK / MEDIUM |
| `TestDeprecatedTlsMapping` | 4 | DEPRECATED_TLS_VERSION → DEPRECATED_PROTOCOL_RISK / HIGH / PROTOCOL_WEAKNESS |
| `TestAmbiguousMapping` | 2 | TLS_HANDSHAKE_FAILURE → AMBIGUOUS_FAILURE; UNKNOWN_SSL_ERROR → UNKNOWN_RISK |
| `TestIncompleteVsUntrustedChain` | 4 | Both map to CHAIN_TRUST failure family; INCOMPLETE_CHAIN → CHAIN_TRUST_FAILURE (not SECURITY_RISK) |
| `TestAdapterDoesNotReadExpectations` | 3 | classify_risk and enrich_evidence work without expectations; unknown classification raises KeyError |
| `TestAdapterSchemaStability` | 4 | EnrichedEvidence has all required keys, string types, frozen dataclass, ascending severity order |
| `TestAdapterBenchmarkResultSchema` | 2 | Benchmark result dict has required keys, optional fields can be None |
| `TestRunnerStructuredOutput` | 2 | Runner script compiles, produces structured JSON with metadata/overall/results |
| `TestDesignDocumentExists` | 4 | Design doc exists, mentions sidecar, no production claims, states SPL Core not modified |
| `TestIsSeverityGte` | 5 | Severity comparison logic works correctly across all levels |
| `TestClassifyRiskFromProbe` | 4 | classify_risk_from_probe extracts and maps classification from probe result dict |

### Tests from prior development phases (now consolidated in the phase table above)

## What Is Unit Tested vs Integration Tested vs Manual

| Category | What | How |
|----------|------|-----|
| **Unit tested** | SPL Core (causal, pipeline, DSL, schema, verification), frontier explorer, weakness mapper, experiments, metrics, cross-source intervention, v7.1 hardening, decision validation contract, TLS risk policy adapter, decision orchestrator + fallback, spl_tls_analyze CLI + fallback, CLI golden acceptance, package entry point, Docker smoke tests | 530 automated tests via `unittest` |
| **Integration tested** | RealValidationRunner (full A/B campaigns), SPL decision validation runner (probe + pipeline + scoring) | Automated runs with synthetic/real data |
| **Manual** | Local TLS probe (probes live domains), mixed TLS accuracy verification, observation/proxy-trained report generation, OFE comparison | Run scripts directly |

## Official Full Verification Commands

### One-Command Release Verification (13 checks)
```bash
python scripts/verify_release.py
```

### Deeper Component Commands
```bash
# All tests (530)
python -m unittest discover -s tests -v

# Or with pytest
python -m pytest tests/ -q

# Compile check (syntax errors)
python -m compileall -q spl_v7 experiments scripts tests tls_policy_adapter decision_orchestrator

# Full CI-equivalent:
python -m unittest discover -s tests -v && python -m compileall -q spl_v7 experiments scripts tests tls_policy_adapter decision_orchestrator
```

## Test Execution Constraints

- The full suite completes in approximately 25-45s on a modern machine.
- No external network access is required for unit tests (all data is synthetic).
- No Docker or VPS is required.

## What Is NOT Covered by Tests

The following components are verified by compileall but do not have dedicated unit tests:

| Component | Verification Method |
|-----------|-------------------|
| `scripts/run_local_tls_validation.py` | compileall + manual run (Phase 1/2) |
| `scripts/run_real_tls_spl_decision_validation.py` | Unit tested (60 tests) + manual runs |
| `scripts/run_stratified_benchmark.py` | compileall + manual benchmark run (Phase 5) |
| `scripts/run_tls_policy_adapter_benchmark.py` | compileall + manual benchmark run (Phase 6) |
| `tls_policy_adapter/` | Unit tested (69 tests in `test_tls_policy_adapter.py`) + compileall |
| `scripts/run_decision_orchestration_benchmark.py` | compileall + manual benchmark run (Phase 7/8) |
| `decision_orchestrator/` | Unit tested (128 tests in `test_decision_orchestrator.py`) + compileall |
| `scripts/spl_tls_analyze.py` | Unit tested (47 tests in `test_spl_tls_analyze.py` + 26 golden acceptance tests in `test_cli_golden_acceptance.py`) + compileall |
| `datasets/cli_golden_samples.json` | 26 acceptance tests via `test_cli_golden_acceptance.py` |
| `datasets/vps_dry_run_domains.txt` | Manual run — dry-run dataset (15 domains) |
| `tests/fixtures/cli_golden/` | 26 snapshot comparisons via `test_cli_golden_acceptance.py` |
| `tests/test_package_entry.py` | 11 tests via pytest |
| `scripts/verify_release.py` | Manual run — no automated tests |
| `scripts/run_docker_dogfood.ps1` | Manual run — requires Docker |
| `Dockerfile` | 10 smoke tests via `test_docker_docs.py` |
| `.dockerignore` | 10 smoke tests via `test_docker_docs.py` |
| `docs/DOCKER_USAGE.md` | 10 smoke tests via `test_docker_docs.py` |
| `docs/VPS_DRY_RUN.md` | File integrity via `verify_release.py` |
| `docs/VPS_DRY_RUN_REPORT_TEMPLATE.md` | File integrity via `verify_release.py` |
| `datasets/vps_dry_run_domains.txt` | File integrity via `verify_release.py` |
| `scripts/run_vps_dry_run.sh` | File integrity via `verify_release.py` |
| `scripts/run_vps_dry_run.ps1` | File integrity via `verify_release.py` |
| `scripts/validate_real_tls_data.py` | compileall |
| `scripts/run_frontier_validation.py` | compileall |
| `scripts/run_ofe_experiment.py` | compileall |
| `scripts/run_weakness_mapper.py` | compileall |
| `scripts/run_replication.py` | compileall |
| `scripts/run_demo.sh` | n/a (shell script) |
| `scripts/run_dashboard.sh` | n/a (shell script) |
| `scripts/run_kafka.sh` | n/a (shell script) |
| `scripts/run_tests.sh` | n/a (shell script) |

## Change History

| Date | Count | Change |
|------|-------|--------|
| v7.1 baseline | 169 | Initial count across all 14 test files |
| Before Phase 3 | 169 | Unchanged |
| Phase 3 | 169 | Unchanged — no SPL Core modifications; added runner, contract, expectations |
| Phase 3.5 | 217 | Added `tests/test_spl_decision_validation.py` (48 tests) — leakage audit, modes, deprecated TLS, timeout policy, evidence contract, pipeline evaluation |
| Phase 4 | 229 | Added 12 holdout mode tests — train expectations, pipeline training with labels, split integrity, holdout leakage |
| Phase 5 | 229+ | Expanded benchmark (120 domains), repeated stratified holdout (10 runs), deprecated TLS review, benchmark tests added. No new SPL Core tests — existing 229 tests still pass. |
| Phase 6 | 280 | Added `tls_policy_adapter/` module (4 files), `docs/TLS_RISK_POLICY_ADAPTER.md` design doc, 51 adapter tests, `scripts/run_tls_policy_adapter_benchmark.py` runner. SPL Core untouched, OFE remains HOLD_PENDING_REAL_DATA. |
| Phase 6.5 | 291+ | Evaluation integrity audit: `docs/PHASE5_PHASE6_METHOD_COMPARISON.md`, `docs/TLS_PROBE_LIMITATION_AUDIT.md`, updated runner with 4 baselines (adapter-only, observation, holdout, proxy-trained), corrected proxy-trained labeling, category-level comparison report. No adapter code changes needed — audit only. SPL Core untouched. |
| Phase 7 | 308+ | Added `decision_orchestrator/` module (4 files), `docs/DECISION_ORCHESTRATION_POLICY.md` design doc, 33 orchestrator tests, `scripts/run_decision_orchestration_benchmark.py` runner. Updated all docs. SPL Core untouched, OFE remains HOLD_PENDING_REAL_DATA. |
| Phase 7.5 | 404 | Decision semantics and scoring audit: `docs/DECISION_SEMANTICS_AUDIT.md`, `docs/ORCHESTRATION_SCORING_AUDIT.md`, updated reporter with safety metrics (safety_adjusted_pct, under_blocking, probe_limited), 41 new guardrail + safety-scoring tests. SPL Core untouched. |
| Phase 8 | 420 | Decision operating profiles: `OperatingProfile` type added, profile parameter in `decide()` (conservative/balanced/strict), profile validation (ValueError for invalid), `docs/OPERATING_PROFILES.md`, comparison report (`OPERATING_PROFILE_COMPARISON.md`), 16 profile tests, updated runner for all 3 profiles. SPL Core untouched, OFE remains HOLD_PENDING_REAL_DATA. |
| Phase 9 | 458 | Local CLI productization: `scripts/spl_tls_analyze.py` CLI with structured reports (TLS Probe, Policy Adapter, SPL, Decision Reasoning, Recommended Action, Limitations sections), deterministic recommended actions, nested JSON schema (`docs/CLI_OUTPUT_SCHEMA.md`), Markdown reports with executive summary, batch summary, quiet/verbose modes, `docs/CLI_USAGE.md`, 38 CLI tests with mocks. SPL Core untouched, OFE remains HOLD_PENDING_REAL_DATA. |
| Phase 10 | 483 | Golden sample acceptance testing: `datasets/cli_golden_samples.json` (12 representative cases covering all classifications), `tests/fixtures/cli_golden/` with 39 output snapshots (13 console, 13 JSON, 13 Markdown), `tests/test_cli_golden_acceptance.py` (25 tests: 3 fixture snapshots, 2 console sections, 2 JSON schema, 1 exit code, 1 recommended actions, 1 limitations, 1 profile, 1 OFE, 9 batch summary, 3 batch snapshots), `docs/CLI_GOLDEN_TESTING.md`. SPL Core untouched, OFE remains HOLD_PENDING_REAL_DATA. |
| Phase 11 | 494 | Local beta packaging: `pyproject.toml` updated with `spl-tls-analyze` package name, version `0.1.0b0`, console script entry point `spl-tls-analyze = scripts.spl_tls_analyze:main`, zero external dependencies, `docs/INSTALL.md`, `docs/VERSIONING.md`, `tests/test_package_entry.py` (11 tests: entry point existence, main() through package, JSON/Markdown output, batch, import paths), updated `scripts/verify_release.py` with 4 new packaging checks. SPL Core untouched, OFE remains HOLD_PENDING_REAL_DATA. |
| Phase 12 | 494 | Local beta dogfooding: `datasets/dogfood_domains.txt` (31 safe public domains across valid, TLS test, edge case, DNS failure categories), `scripts/run_dogfood_cli.py` runner, `reports/dogfood/dogfood_results.json` + `DOGFOOD_REPORT.md`, `docs/DOGFOOD_FINDINGS.md` (what worked, confusing outputs, over-blocking analysis, profile assessment, exit code practicality), `docs/DOGFOOD_FEEDBACK_TEMPLATE.md`. 31/31 domains probed, 0 errors. SPL Core untouched, OFE remains HOLD_PENDING_REAL_DATA. |
| Phase 13 | 520 | CLI confidence fallback policy: `docs/CLI_CONFIDENCE_FALLBACK_POLICY.md` design doc, orchestrator updated with `probe_limited` param and `ADAPTER_FALLBACK` decision source, `fallback_used`/`confidence_source` fields in output, CLI shows fallback in all formats, dogfood re-run (19 ALLOW / 11 REVIEW / 1 DENY — before was 0/30/1), 18 new fallback tests in orchestrator, 10 new CLI tests, 1 new golden batch test, updated all docs. Balanced profile only. SPL Core untouched, OFE remains HOLD_PENDING_REAL_DATA. |
| Phase 14 | 520 | **Local Beta Freeze:** `docs/RELEASE_NOTES_0.1.0b0.md`, `docs/LOCAL_BETA_FREEZE_MANIFEST.md`, `scripts/verify_release.py` updated (12 checks, version consistency check, "LOCAL BETA RELEASE VERIFICATION" header, negative fallback smoke test). All docs updated with freeze references. SPL Core untouched, OFE remains HOLD_PENDING_REAL_DATA. |
| Phase 15 | 530 | **Dockerized Local Beta:** Dockerfile rewritten (CLI-only, non-root, no ports), `.dockerignore`, `docs/DOCKER_USAGE.md`, `tests/test_docker_docs.py` (10 tests), `scripts/run_docker_dogfood.ps1`, `scripts/verify_release.py` updated (13 checks, optional Docker build check). All docs updated with Docker references. SPL Core untouched, OFE remains HOLD_PENDING_REAL_DATA. |
| Phase 16 | 530 | **VPS Dry Run:** `docs/VPS_DRY_RUN.md` guide, `docs/VPS_DRY_RUN_REPORT_TEMPLATE.md`, `datasets/vps_dry_run_domains.txt` (15 domains), `scripts/run_vps_dry_run.sh` (Linux) + `.ps1` (PowerShell), `scripts/verify_release.py` updated (14 checks, VPS doc integrity). All docs updated. Dockerfile remains CLI-only (no ports, no services). SPL Core untouched, OFE remains HOLD_PENDING_REAL_DATA. |
