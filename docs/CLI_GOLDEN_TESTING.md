# CLI Golden Acceptance Testing

## Overview

Golden acceptance tests freeze the CLI's current behavior by comparing
output against committed snapshot files. Any change to CLI output — whether
intentional (new feature) or accidental (regression) — must be reviewed
through the golden testing process.

The golden samples cover all 12 TLS classifications with mocked probe
results and expected decisions, risks, exit codes, recommended actions, and
limitations.

## Files

| Path | Description |
|------|-------------|
| `datasets/cli_golden_samples.json` | 12 golden samples with mocked probe inputs and expected outputs |
| `tests/fixtures/cli_golden/console/*.txt` | Console output snapshots (one per sample + batch) |
| `tests/fixtures/cli_golden/json/*.json` | JSON output snapshots (one per sample + batch) |
| `tests/fixtures/cli_golden/markdown/*.md` | Markdown output snapshots (one per sample + batch) |
| `tests/test_cli_golden_acceptance.py` | 18 acceptance tests |

### Test Breakdown (18 tests)

| Test Class | Tests | Verifies |
|-----------|-------|----------|
| `TestGoldenFixtureSnapshots` | 3 | Console, JSON, Markdown match fixtures for all 12 samples |
| `TestGoldenConsoleSections` | 2 | All 6 required sections present; Limitations only when expected |
| `TestGoldenJsonSchema` | 2 | Metadata fields, summary/results structure |
| `TestGoldenExitCodes` | 1 | Exit code contract per sample |
| `TestGoldenRecommendedActions` | 1 | Recommended actions contain expected substrings |
| `TestGoldenLimitations` | 1 | Limitation text matches expectations |
| `TestGoldenProfilePreservation` | 1 | Profile name preserved in output |
| `TestGoldenOfeIsolation` | 1 | OFE always False in CLI output |
| `TestGoldenBatchSummary` | 9 | Batch counts (12/0/11/1/CRITICAL/4/1), section headers |
| `TestGoldenBatchSnapshot` | 3 | Batch console/JSON/Markdown match fixtures |

## Golden Dataset

`datasets/cli_golden_samples.json` contains 12 samples, one for each
classification:

| ID | Classification | Expected Decision | Expected Risk | Exit Code |
|----|---------------|-------------------|---------------|-----------|
| `valid_tls` | VALID_TLS | REVIEW | LOW | 1 |
| `expired_cert` | EXPIRED_CERT | REVIEW | HIGH | 1 |
| `self_signed_cert` | SELF_SIGNED_CERT | REVIEW | HIGH | 1 |
| `wrong_host_cert` | WRONG_HOST_CERT | DENY | CRITICAL | 2 |
| `untrusted_chain` | UNTRUSTED_CHAIN | REVIEW | HIGH | 1 |
| `incomplete_chain` | INCOMPLETE_CHAIN | REVIEW | HIGH | 1 |
| `dns_failure` | DNS_FAILURE | REVIEW | MEDIUM | 1 |
| `timeout` | TIMEOUT | REVIEW | MEDIUM | 1 |
| `connection_error` | CONNECTION_ERROR | REVIEW | MEDIUM | 1 |
| `tls_handshake_failure` | TLS_HANDSHAKE_FAILURE | REVIEW | MEDIUM | 1 |
| `deprecated_tls` | DEPRECATED_TLS_VERSION | REVIEW | HIGH | 1 |
| `unknown_ssl_error` | UNKNOWN_SSL_ERROR | REVIEW | LOW | 1 |

Each sample defines a `mocked_probe` with controlled TLS handshake data,
DNS status, and certificate details. Expected values include the final
orchestrated decision, adapter output, recommended action substring, and
optional limitation substring.

## When to Update Golden Fixtures

Update golden fixtures when CLI output changes intentionally:

- New output fields added to any format (console, JSON, Markdown)
- Recommended action text changes
- Decision behavior changes (new profile, new orchestrator rule)
- Output formatting changes (section ordering, indentation, labels)
- New golden sample added

Do NOT update fixtures to hide test failures caused by:
- Accidental changes to decision logic
- Formatting bugs
- Schema contract violations

## How to Update Golden Fixtures

### Prerequisites

```bash
PYTHONPATH=.
```

### Regenerate all fixtures

Run the generator script from the project root:

```powershell
python tests/_generate_golden_fixtures.ps1
```

This recreates all fixture files from `cli_golden_samples.json`.

### Or regenerate a single fixture

After changing a specific sample, manually update the corresponding
fixture file(s) in `tests/fixtures/cli_golden/`.

### Verify after update

```bash
python -m pytest tests/test_cli_golden_acceptance.py -v
```

All 25 tests must pass before committing fixture updates.

## Output Stability

Golden tests normalize timestamps before comparison:

- **JSON**: `generated_at` and `probe_timestamp` are replaced with
  `GENERATED_AT_PLACEHOLDER` in both fixture and actual output.
- **Markdown**: Same normalization applied to the `**Generated:**` line.
- **Console**: No timestamps in console output — no normalization needed.

All other output is compared literally (character-by-character). Any
difference in spacing, ordering, capitalization, or content causes a test
failure.

## How Golden Tests Work

1. Each test loads a sample from `cli_golden_samples.json`.
2. `analyze_domain()` is called with a mock `probe_domain()` that returns
   the sample's `mocked_probe` data — no live network calls.
3. The actual output (`format_structured_text`, `format_json_output`,
   `format_markdown_output`) is normalized and compared against the
   golden fixture file.
4. Additional tests verify individual fields (decision, risk, exit code,
   recommended action, limitations) independently of the snapshot comparison.

This two-layer approach catches both formatting drift (snapshots) and
semantic drift (field assertions).

## Running Golden Tests

```bash
# Run only golden acceptance tests
python -m pytest tests/test_cli_golden_acceptance.py -v

# Run all tests including golden tests
python -m pytest tests/ -v --tb=short
```

## Review Triggers

A review of golden fixtures is required when:

1. Adding or modifying orchestrator policy rules
2. Changing operating profile definitions
3. Adding new output formats
4. Modifying the JSON or Markdown schema
5. Adding new probe classifications
6. Changing recommended action text
7. Changing output section structure

## Design Decisions

1. **No live network calls**: Golden samples use fully mocked probe results.
   This makes tests deterministic and fast (~0.5s for all 25 tests).

2. **Timestamp normalization via regex**: Timestamps are replaced with a
   stable placeholder before comparison. The regex supports both
   `2026-06-01T12:00:00Z` (no fractional seconds) and
   `2026-06-01T12:00:00.123456+00:00Z` (with fractional seconds) formats.

3. **Snapshot + field assertions**: Snapshot comparisons catch formatting
   drift, while field assertions verify semantic correctness. Both are
   needed because snapshots alone would break on any whitespace change,
   while field assertions alone miss formatting bugs.

4. **Batch summary tested separately**: The batch summary over all 12
   golden samples is verified independently with expected counts
   (0 ALLOW / 11 REVIEW / 1 DENY / CRITICAL highest risk / 4 probe-limited
   / 1 probe error) plus section header presence.

## Limitations

1. Golden tests do not verify:
   - SPL Core behavior (mocked out)
   - OFE behavior (always False in CLI output)
   - Live network behavior (no real probes)
   - Profile-specific output beyond what the 12 samples cover

2. Fixture files are large (several KB each) and should not be reviewed
   as code. Reviewers should verify that fixture changes match the
   expected output format, not read the entire diff.

3. The generator PowerShell script is a development tool, not a test.
   It is not run in CI.

## Related Documentation

- `docs/CLI_USAGE.md` — CLI command-line usage and examples
- `docs/CLI_OUTPUT_SCHEMA.md` — Complete JSON output schema
- `docs/OPERATING_PROFILES.md` — Profile definitions and behavior
- `docs/DECISION_ORCHESTRATION_POLICY.md` — Orchestrator design and rules
