# TrustLint Commercial Guardrails

## Authorization Requirement

No scan may proceed without explicit written authorization from the asset owner. The operator must confirm ownership or provide documented permission for every endpoint before scanning begins.

## Data Handling

- Do not publish customer domains, scan results, or findings without written consent.
- Store scan data securely and delete it after the engagement period unless otherwise agreed.
- Do not share customer data with third parties.

## No Claims Beyond Evidence

- Report only what the tool observed. Do not infer, extrapolate, or speculate beyond the evidence.
- An unavailable or inconclusive result is not a confirmed vulnerability.
- Do not claim that TrustLint is a penetration test, compliance certification, or guarantee against incidents.

## No Production ALLOW/DENY Claims

The `validation_runner` module is offline research/validation only. It is not on the production CLI path and must not be presented as a production ALLOW/DENY engine.

## Escalation Language for Critical Findings

When a critical finding is reported:

> **Critical finding:** [description]. This requires immediate attention. We recommend remediating this issue before the next production deployment. Contact us if you need assistance with remediation.

## Customer-Facing Disclaimer

> TrustLint TLS Security Review is a screening tool, not a penetration test or compliance certification. Results are point-in-time and do not guarantee the absence of vulnerabilities. The operator must provide explicit written authorization for all endpoints before scanning begins. TrustLint does not perform exploitation, intrusion testing, or compliance certification.
