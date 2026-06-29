# Versioning — spl-tls-analyze

## Current Version

**0.3.2b0** (local beta)

PEP 440 pre-release format: major.minor.patch + beta pre-release tag.

## Version Meaning

| Component | Meaning |
|-----------|---------|
| `0` (major) | Pre-1.0 — no API stability guarantee for any component except the documented JSON output schema |
| `2` (minor) | Incremented for feature additions that maintain backward compatibility with CLI output schema |
| `0` (patch) | Incremented for bug fixes, documentation, or internal refactoring |
| `b0` (beta) | Local beta — not production-ready, not published to PyPI |

## What This Version Means

1. **Local beta** — The CLI is functional and tested but has not been
   validated in production environments.

2. **No production readiness** — See `docs/KNOWN_LIMITATIONS.md` for
   the full list of limitations that prevent production use.

3. **CLI output schema is stable** — The JSON output format documented
   in `docs/CLI_OUTPUT_SCHEMA.md` is considered stable within the same
   minor version. New fields may be added, but existing fields will not
   be removed or renamed without a minor version bump.

4. **Console output is NOT stable** — Console text formatting may change
   between patch versions. Golden acceptance tests in
   `tests/test_cli_golden_acceptance.py` track console formatting but
   the format is not versioned.

5. **CLI exit codes are stable** — Exit codes 0–4 follow the documented
   contract and will not change without a major version bump.

6. **SPL Core is protected** — The `spl_v7/` package is never modified
   by the CLI, adapter, or orchestrator. Its versioning is independent
   of `spl-tls-analyze`.

7. **OFE remains HOLD_PENDING_REAL_DATA** — The Orchestrated Feature
   Evaluator is implemented but never promoted. This status will not
   change within the 0.2.x series.

8. **SPL integration via `--spl`** — The CLI can load the SPL evidence
   pipeline with the `--spl` flag. SPL Core remains unmodified. See
   `docs/SPL_INTEGRATION_FEASIBILITY_AUDIT.md`.

## Release Cadence

There is no fixed release schedule. Versions are tagged when the project
maintainer determines a milestone is complete.

## Future Roadmap

- **0.3.0** — Extended probe capabilities (multi-IP, IPv6)
- **1.0.0** — Production readiness candidate (requires real-world validation)

These are aspirational. No commitment is made to any specific timeline.
