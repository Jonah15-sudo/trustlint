# SPL v7.1 Project Status

Generated state: production core scaffold with v7.1 hardening, CI/CD, and dataset gate.

## Implemented

- Neutral `EvidenceArtifact` schema.
- Safe feature DSL.
- Online causal graph learner.
- Kafka + memory pipeline.
- Topology dashboard.
- Constraint #1: Stability v2 with rolling windows, drift score, sign consistency, and prediction-volatility check.
- Constraint #1b: Independence v2 with pairwise redundancy plus conditional/partial-correlation approximation.
- Constraint #2: Cross-source corroboration.
- Constraint #2b: Multi-source verification/provenance with source registry, artifact digest, optional HMAC signature, transport sanity, and source trust attenuation.
- Constraint #3: intervention approximation production hack.
- Explicit causal graph report: `spl.causal_graph.v7.1`.
- Frontier Explorer sidecar layer for self-generating benchmark curricula.
- OFE structural-signal bridge registered as an internal source in the provenance layer.
- Structured configs, scripts, Dockerfile, Makefile, docs, and tests.
- Real Data Validation Runner (`experiments/real_validation_runner.py`).
- CI workflow (`.github/workflows/ci.yml`): pytest, compileall, runner structural tests, archive hygiene, dataset gate.
- Dataset gate: sample fixture explicitly rejected; generated data marked test-only.
- OFE status: `HOLD_PENDING_REAL_DATA`.

## Verification

```text
Ran 168 tests (all suites)
OK
```

`compileall` passes for all packages.

## Test Count

| Suite | Tests |
|---|---|
| `tests/test_real_validation_runner.py` | 18 |
| `tests/test_replication.py` | 33 |
| `tests/test_weakness_mapper.py` | 29 |
| Other tests | 88 |
| **Total** | **168** |

## CI/CD

- On push/PR to master: pytest full suite, compileall, runner structural tests, archive hygiene, signal promotion guard.
- Real-data validation runs only when `REAL_TLS_DATASET` env var is set.
- Without it, CI explicitly reports `REAL_TLS_DATASET not set — real-data validation SKIPPED`.

## Dataset Gate

- `RealValidationRunner._validate_dataset()` rejects filenames matching `real_tls_sample.jsonl` or `real_tls_sample.csv`.
- All output includes the note: `No OFE signal was promoted. OFE remains HOLD_PENDING_REAL_DATA.`
- `experiments/status.py` provides `OFE_STATUS`, `check_ofe_status()`, and `check_dataset_gate()`.

## Important honesty note

This is a production-ready core/scaffold: runnable, test-covered, structured, and configured. It is not proof of live production behavior under your real infrastructure, collectors, Kafka brokers, auth layer, and monitoring stack until deployed and load-tested there.
