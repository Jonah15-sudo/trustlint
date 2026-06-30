# Phase 6 Baseline Comparison Report

## Baseline Modes

### Adapter-Only

- Mode: Adapter-Only
- Total domains: 120
- Decision accuracy: N/A (no SPL pipeline)
- Valid TLS: 48 (40.0%)
- Expired cert: 24 (20.0%)
- Deprecated TLS: 12 (10.0%)
- DNS failure: 24 (20.0%)
- Timeout: 12 (10.0%)

### SPL Observation

- Mode: SPL Observation
- Total domains: 120
- Valid TLS: 48 (40.0%)
- Expired cert: 24 (20.0%)
- Deprecated TLS: 12 (10.0%)
- DNS failure: 24 (20.0%)
- Timeout: 12 (10.0%)
- Generalization: NOT generalization

### SPL Holdout

- Mode: SPL Holdout
- Total domains: 120
- Valid TLS: 48 (40.0%)
- Expired cert: 24 (20.0%)
- Deprecated TLS: 12 (10.0%)
- DNS failure: 24 (20.0%)
- Timeout: 12 (10.0%)
- Generalization: generalization

### SPL Proxy-Trained

- Mode: SPL Proxy-Trained
- Total domains: 120
- Valid TLS: 48 (40.0%)
- Expired cert: 24 (20.0%)
- Deprecated TLS: 12 (10.0%)
- DNS failure: 24 (20.0%)
- Timeout: 12 (10.0%)
- Generalization: NOT generalization

## Category-Level Results

| Category | Adapter-Only | SPL Observation | SPL Holdout | SPL Proxy-Trained |
|---|---|---|---|---|
| VALID_TLS | 48 | 48 | 48 | 48 |
| EXPIRED_CERT | 24 | 24 | 24 | 24 |
| DEPRECATED_TLS | 12 | 12 | 12 | 12 |
| DNS_FAILURE | 24 | 24 | 24 | 24 |
| TIMEOUT | 12 | 12 | 12 | 12 |
