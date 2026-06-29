# SPL v7.1 Production Runbook

## 1. Install

```bash
python -m pip install -e .
```

Optional Kafka support:

```bash
python -m pip install -e '.[kafka]'
```

## 2. Test

```bash
./scripts/run_tests.sh
```

Expected local result for this package:

```text
Ran 17 tests
OK
```

## 3. Demo

```bash
./scripts/run_demo.sh
```

The demo writes:

- `dashboard.html`
- `v71_graph_snapshot.json`

## 4. Dashboard

```bash
./scripts/run_dashboard.sh
```

Health check:

```bash
curl http://localhost:8000/health
```

Snapshot API:

```bash
curl http://localhost:8000/api/snapshot
```

## 5. Kafka

Start local Kafka:

```bash
./scripts/run_kafka.sh
```

Install Kafka extras before using the real broker path:

```bash
python -m pip install -e '.[kafka]'
```

## 6. Source verification

For production, create a source registry and pass an `EvidenceProvenanceVerifier` into `EvidencePipeline`.

```python
from spl_v7.verification import SourceProfile, SourceRegistry, EvidenceProvenanceVerifier

registry = SourceRegistry([
    SourceProfile("collector-a", trust_weight=0.95, allowed_types=["tls"], require_signature=False),
    SourceProfile("collector-b", trust_weight=0.95, allowed_types=["tls"], require_signature=False),
])
verifier = EvidenceProvenanceVerifier(registry)
```

Collectors should provide `integrity.hash` generated over the neutral artifact payload. HMAC signatures are supported when a shared secret is configured.

## 7. Operational notes

- Use at least two independent collectors for production corroboration.
- Keep collectors dumb: no `direction`, no hard-coded risk weights.
- Set `emit_graph_snapshot=False` in high-throughput processing.
- Treat `intervention_approximation` as a production heuristic, not a scientific proof of causality.
- Monitor DLQ volume, unstable features, duplicate features, and single-source signals.
- Run adversarial DSL tests before accepting untrusted feature programs.
