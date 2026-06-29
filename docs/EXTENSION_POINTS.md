# Extension Points — SPL v7.1

This document defines every official way to extend SPL v7.1 without modifying the protected core. All extensions use one of three patterns: **configuration**, **composition**, or **sidecar**.

---

## Extension Patterns

| Pattern | Mechanism | Risk | Example |
|---|---|---|---|
| Configuration | Constructor args, config objects | None | `SourceRegistry(profiles=...)` |
| Composition | Inject dependency at init | Low | `EvidencePipeline(verifier=...)` |
| Sidecar | Separate process/module, uses public API | Low | `FrontierExplorer` |

---

## 1. Source Registry — Configuration

**File:** `spl_v7/verification.py` — `SourceRegistry`, `SourceProfile`

Define custom collector profiles. Each source gets a trust weight, optional HMAC secret, and allowed type filter.

```python
from spl_v7.verification import SourceProfile, SourceRegistry, EvidenceProvenanceVerifier

registry = SourceRegistry([
    SourceProfile(
        source_id="collector-a",
        trust_weight=0.95,
        allowed_types=["tls", "dns"],
        require_signature=False,
    ),
    SourceProfile(
        source_id="internal-audit",
        trust_weight=0.98,
        allowed_types=["audit"],
        require_signature=True,
        shared_secret="prod-secret-2026",
    ),
    SourceProfile(
        source_id="unknown",
        trust_weight=0.25,
        allowed_types=[],
    ),
])

verifier = EvidenceProvenanceVerifier(registry)
pipeline = EvidencePipeline(program, causal_graph=learner, verifier=verifier)
```

**Contract:** Any `SourceProfile` with `enabled=True` is active. Sources not in the registry get `trust_weight=0.25` and `source_registered=False`.

---

## 2. Feature DSL Programs — Configuration

**File:** `spl_v7/dsl.py` — `FeatureDSLProgram`, `FeatureDSLParser`, `ExpressionCompiler`

Write feature programs in the restricted DSL. Each line defines a named feature with an expression.

```
# configs/features.dsl
feature tls_valid = data.valid
feature expiry_urgency = normalize(30 - data.expiry_days, 0, 30)
feature risk_score = clamp(0.0, 1.0, 0.6 * expiry_urgency + 0.4 * (not data.headers.hsts))
```

```python
from spl_v7.dsl import compile_feature_dsl

program = compile_feature_dsl(open("configs/features.dsl").read())
pipeline = EvidencePipeline(program, ...)
```

**Available functions:** `abs`, `min`, `max`, `round`, `sum`, `mean`, `stdev`, `entropy`, `sigmoid`, `safe_div`, `clamp`, `length`, `normalize`

**Restrictions:** No `**`, no `eval`, no imports, no attribute assignment, only direct function calls by name.

---

## 3. Pipeline Adapter — Composition

**File:** `spl_v7/kafka_pipeline.py` — `KafkaAdapter` (abstract base)

Implement a custom transport backend by subclassing `KafkaAdapter`.

```python
from spl_v7.kafka_pipeline import KafkaAdapter, PipelineMessage

class RedisAdapter(KafkaAdapter):
    def __init__(self, redis_client):
        self.client = redis_client

    def produce(self, topic: str, key: str | None, value: dict) -> None:
        self.client.lpush(f"spl:{topic}", json.dumps(value))

    def consume(self, topic: str, timeout: float = 0.1) -> PipelineMessage | None:
        raw = self.client.brpop(f"spl:{topic}", timeout=int(timeout))
        if raw is None:
            return None
        return PipelineMessage(topic=topic, key=key, value=json.loads(raw[1]))

    def close(self) -> None:
        self.client.close()
```

```python
pipeline = EvidencePipeline(program, causal_graph=learner, adapter=RedisAdapter(redis_client))
```

**Contract:** `produce()` must be non-blocking or have configurable timeout. `consume()` must return `None` on timeout/empty. `close()` must clean up resources.

---

## 4. Custom Verifier — Composition

**File:** `spl_v7/verification.py` — `EvidenceProvenanceVerifier`

Replace or wrap the default verifier. The verifier receives an `EvidenceArtifact` and returns a dict with at minimum a `score` key.

```python
from spl_v7.verification import EvidenceProvenanceVerifier
from spl_v7.schema import EvidenceArtifact

class ExtendedVerifier(EvidenceProvenanceVerifier):
    def verify(self, artifact: EvidenceArtifact) -> dict:
        base = super().verify(artifact)
        # Add custom checks
        base["geo_check"] = self._geo_validate(artifact)
        base["reputation_check"] = self._reputation_score(artifact.source)
        base["score"] = (base["score"] + base["reputation_check"]) / 2
        base["passed"] = base["score"] >= 0.60
        return base

pipeline = EvidencePipeline(program, causal_graph=learner, verifier=ExtendedVerifier(registry))
```

**Contract:** Return dict must include `"score"` (0–1 float) and `"passed"` (bool). All other keys are transparent to the pipeline but stored in the output record.

---

## 5. Dashboard State Provider — Composition

**File:** `spl_v7/dashboard.py` — `create_app(state_provider)`

Inject a custom state provider to serve live pipeline data.

```python
from spl_v7.dashboard import create_app

pipeline = EvidencePipeline(program, causal_graph=learner)

def my_state_provider():
    return pipeline.state()

app = create_app(state_provider=my_state_provider)
```

**Contract:** `state_provider` is a zero-arg callable returning a dict with at minimum `{"graph": {...}}`. Called on every `/` and `/api/snapshot` request.

---

## 6. OFE Structural Signal Bridge — Sidecar

**File:** `spl_v7/frontier.py` — `FrontierExplorer.wrap_structural_signals()`

OFE structural signals are wrapped as ordinary evidence and processed through the standard pipeline.

```python
from spl_v7.frontier import FrontierExplorer

explorer = FrontierExplorer(pipeline)

artifact = explorer.wrap_structural_signals(
    {
        "contradiction_density": 0.91,
        "topology_drift": 0.77,
        "symbol_entropy": 0.64,
    },
    source="ofe",
    evidence_type="structural_signal",
    label=True,
)

pipeline.ingest(artifact.to_dict())
result = pipeline.process_one()
```

**Contract:** The artifact is processed through the standard pipeline — same verification, same DSL compilation, same causal learning. SPL decides whether the signal matters. OFE never makes decisions.

---

## 7. Frontier Curriculum Generation — Sidecar

**File:** `spl_v7/frontier.py` — `FrontierExplorer.generate_curriculum()`

Generate progressive challenge chains to measure capability boundaries.

```python
from spl_v7.schema import EvidenceArtifact, EvidenceTransportMeta
from spl_v7.frontier import FrontierExplorer

explorer = FrontierExplorer(pipeline)
seed = EvidenceArtifact(
    source="collector-a",
    type="tls",
    data={"valid": True, "expiry_days": 7, "headers": {"hsts": False}, "label": True},
    transport_meta=EvidenceTransportMeta(status="ok"),
)

curriculum = explorer.generate_curriculum(seed, steps=5)

for challenge in curriculum:
    pipeline.ingest(challenge.artifact.to_dict())
    result = pipeline.process_one()
    # Record outcome
```

**Contract:** Each challenge is a valid `EvidenceArtifact` that can be ingested and processed. The explorer does not read or modify SPL internal state — it works from `snapshot()` output only.

---

## 8. Custom Functions — Configuration

**File:** `spl_v7/dsl.py` — `ExpressionCompiler(functions=...)`

Register custom safe functions in the DSL compiler.

```python
from spl_v7.dsl import ExpressionCompiler

def my_custom_metric(x: float, y: float) -> float:
    return (x - y) / max(x, y, 1e-12)

compiler = ExpressionCompiler(functions={
    **SAFE_FUNCTIONS,
    "custom_metric": my_custom_metric,
})

program = FeatureDSLProgram.from_text(dsl_text, compiler=compiler)
```

**Contract:** Functions must be pure (no I/O, no state), raise no exceptions, and accept/return basic Python types. Functions are called by name in DSL expressions.

---

## 9. Middleware / Decorator — Composition

Wrap the pipeline at the public API level for monitoring, logging, rate limiting, or custom metrics.

```python
class MonitoredPipeline:
    def __init__(self, pipeline: EvidencePipeline):
        self._pipeline = pipeline

    def ingest(self, evidence: dict) -> str:
        start = time.time()
        key = self._pipeline.ingest(evidence)
        self._record_latency("ingest", time.time() - start)
        return key

    def process_one(self, timeout=0.1):
        start = time.time()
        result = self._pipeline.process_one(timeout)
        self._record_latency("process_one", time.time() - start)
        if result:
            self._record_decision(result)
        return result
```

**Contract:** The wrapper must pass through all public methods of `EvidencePipeline`. No internal state access.

---

## Extension Prohibitions

The following are **not** extension points and must not be used as such:

| Prohibited | Reason |
|---|---|
| Modifying `spl_v7/*.py` files | Core is frozen |
| Accessing `_history`, `_labeled_history` | Private attributes, subject to change |
| Subclassing `OnlineCausalGraphLearner` | Learner is frozen |
| Monkey-patching core modules | Violates freeze |
| Importing exploration into core | Reverse dependency |
| Creating new memory/storage inside core | Must live in sidecar |
| Adding `**` or `eval` to DSL | Security boundary |

---

## Promotion Criteria

For any extension to move from Experimental to Supported:

1. **Measurable benefit:** Quantitative improvement in accuracy, stability, or coverage
2. **Reproducibility:** Results consistent across 3+ independent runs
3. **Stability:** No degradation in core constraint scores (stability, independence, corroboration)
4. **Test coverage:** Tests for the extension passing
5. **Documentation:** Updated PROJECT_MAP and extension point docs

Promotion is documented in `SUPPORTED_SIGNALS.md` (see Month 5).

---

## Decision Rule

> If a new feature requires touching multiple SPL core components: **STOP.**
>
> Design an adapter, bridge, or sidecar instead.

The goal is to add one capability without sacrificing two existing capabilities.
