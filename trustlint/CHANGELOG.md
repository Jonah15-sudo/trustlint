# Changelog

All notable changes to TrustLint will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

_No unreleased changes yet._

---

## [1.0.0] - 2026-XX-XX

### Added

- Initial public release of TrustLint.
- TLS/SSL certificate parsing and analysis (PEM and DER formats).
- Cipher suite detection and strength evaluation.
- Certificate chain validation and trust path analysis.
- Support for checking against known weak/deprecated protocols (SSLv2, SSLv3, TLS 1.0, TLS 1.1).
- CLI interface with structured JSON and human-readable output formats.
- Exit code system for scripted integration.
- Configurable output verbosity.
- Network-based endpoint scanning mode (`--url`).
- Local file analysis mode (`--file`).
- Self-signed certificate detection.
- Expiration checking with configurable thresholds.
- Basic policy rules for compliance checking.
- `--version` and `--help` flags.
- Test suite with unit and integration tests.

### Changed

- N/A (initial release).

### Deprecated

- N/A (initial release).

### Removed

- N/A (initial release).

### Fixed

- N/A (initial release).

### Security

- N/A (initial release).

---

[Unreleased]: https://github.com/<owner>/trustlint/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/<owner>/trustlint/releases/tag/v1.0.0
