from __future__ import annotations

import json
from pathlib import Path

from spl_v7.causal import OnlineCausalGraphLearner
from spl_v7.dashboard import build_dashboard_html
from spl_v7.dsl import compile_feature_dsl
from spl_v7.kafka_pipeline import EvidencePipeline, PipelineConfig, MemoryKafkaAdapter
from spl_v7.schema import EvidenceArtifact, EvidenceTransportMeta
from spl_v7.verification import compute_artifact_hash


ROOT = Path(__file__).resolve().parents[1]
DSL_TEXT = (ROOT / "configs" / "features.dsl").read_text(encoding="utf-8")


def make_sample(source: str, i: int) -> EvidenceArtifact:
    risky = i % 2 == 1
    expiry_days = 5 if risky else 90
    hsts = not risky
    csp = not risky or i % 7 == 0
    status = "timeout" if risky and i % 11 == 0 else "ok"
    latency = 1800 if risky else 90
    label_weight = 2.0 if source in {"collector-a", "collector-b"} else 1.0
    artifact = EvidenceArtifact(
        source=source,
        type="tls",
        data={
            "valid": True,
            "expiry_days": expiry_days,
            "headers": {"hsts": hsts, "csp": csp},
            "label": risky,
            "label_weight": label_weight,
        },
        transport_meta=EvidenceTransportMeta(status=status, latency_ms=latency, bytes_received=512),
    )
    artifact.integrity.hash = compute_artifact_hash(artifact)
    return artifact


def main() -> None:
    program = compile_feature_dsl(DSL_TEXT)
    learner = OnlineCausalGraphLearner(
        independence_min_support=5.0,
        redundancy_threshold=0.85,
        source_min_support=2.0,
        min_corroborating_sources=2,
    )
    pipeline = EvidencePipeline(
        feature_program=program,
        causal_graph=learner,
        config=PipelineConfig(backend="memory", emit_graph_snapshot=False),
        adapter=MemoryKafkaAdapter(),
    )

    for source in ["collector-a", "collector-b", "collector-c"]:
        for i in range(48):
            pipeline.ingest(make_sample(source, i).to_dict())

    outputs = []
    while True:
        result = pipeline.process_one(timeout=0.01)
        if result is None:
            break
        outputs.append(result)

    snapshot = pipeline.state()
    graph = snapshot["graph"]
    html = build_dashboard_html(graph)
    out = ROOT / "dashboard.html"
    out.write_text(html, encoding="utf-8")

    constraints = graph["constraint_tests"]
    print("Processed events:", len(outputs))
    print("Learner accuracy:", graph["accuracy"])
    print("Weighted accuracy:", graph["weighted_accuracy"])
    print("Independence passed:", constraints["independence"]["passed"])
    print("Cross-source features:", len(constraints["cross_source_corroboration"]["features"]))
    print("Stability passed:", constraints["stability"]["passed"])
    print("Source verification passed:", constraints["source_verification"]["passed"])
    print("Top intervention:", constraints["intervention_approximation"]["features"][0])
    graph_out = ROOT / "v71_graph_snapshot.json"
    graph_out.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Dashboard written to:", out.resolve())
    print("Graph snapshot written to:", graph_out.resolve())


if __name__ == "__main__":
    main()
