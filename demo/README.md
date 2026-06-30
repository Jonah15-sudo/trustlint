# TrustLint Demo

## What TrustLint Does

TrustLint is a TLS risk analysis tool that inspects certificate validity, trust chain integrity, protocol versions, cipher suites, and OCSP revocation evidence for public-facing endpoints.

## What the Demo Proves

- TrustLint can classify TLS configurations into actionable risk categories.
- The tool produces structured output (JSON, Markdown, or console) suitable for technical review.
- Findings include specific remediation guidance for each issue detected.

## What It Does Not Prove

- TrustLint is not a penetration test or compliance certification.
- Results are a point-in-time screening, not a guarantee of security.
- The tool does not exploit vulnerabilities or attempt intrusion.
- An inconclusive result is not a confirmed vulnerability.

## Quick Start

See [../docs/DEMO_RUNBOOK.md](../docs/DEMO_RUNBOOK.md) for a reproducible 5-minute demo.

## Sample Report

See [SAMPLE_TLS_REVIEW.md](SAMPLE_TLS_REVIEW.md) for a polished sample client-facing report using fixture data.
