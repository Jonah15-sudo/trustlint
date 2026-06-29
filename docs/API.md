# SPL v7.1 API Notes

The default FastAPI dashboard exposes:

- `GET /health` -> basic health check.
- `GET /` -> rendered topology dashboard.
- `GET /api/snapshot` -> graph, weights, edge constraints, provenance reports, and metadata.

The pipeline API is Python-native:

```python
from spl_v7 import EvidenceArtifact, EvidencePipeline, PipelineConfig, compile_feature_dsl
from spl_v7.verification import compute_artifact_hash

program = compile_feature_dsl(open("configs/features.dsl").read())
pipeline = EvidencePipeline(program, config=PipelineConfig(backend="memory"))

artifact = EvidenceArtifact(source="collector-a", type="tls", data={"risk": 1.0, "label": True})
artifact.integrity.hash = compute_artifact_hash(artifact)

pipeline.ingest(artifact.to_dict())
result = pipeline.process_one()
snapshot = pipeline.state()
causal_graph = snapshot["graph"]["causal_graph"]
```

For high-throughput processing:

```python
PipelineConfig(backend="kafka", emit_graph_snapshot=False)
```

Use `pipeline.state()` for periodic snapshots instead of generating a deep graph report on every message.
