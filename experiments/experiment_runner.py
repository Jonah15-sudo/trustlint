from __future__ import annotations

import json
import os
import random
from typing import Any, Dict, List, Optional

from spl_v7.causal import OnlineCausalGraphLearner
from spl_v7.frontier import FrontierExplorer
from spl_v7.kafka_pipeline import EvidencePipeline, MemoryKafkaAdapter, PipelineConfig
from spl_v7.schema import EvidenceArtifact, EvidenceTransportMeta
from spl_v7.verification import compute_artifact_hash

from experiments.dsl_helpers import build_experiment_dsl
from experiments.metrics import MetricsCollector
from frontier.session import ExplorationSession, ExplorationReport, compute_difficulty
from weakness_mapper.extractor import Weakness, WeaknessExtractor
from weakness_mapper.registry import WeaknessRegistry


TRAINING_SOURCES = ["collector-a", "collector-b", "collector-c"]
TRAINING_ITEMS_PER_SOURCE = 30
OFE_SIGNAL_COUNT = 15

CURRICULA = [
    ("standard", {"valid": True, "expiry_days": 7, "headers": {"hsts": False, "csp": True}, "label": True, "label_weight": 1.0}),
    ("expired", {"valid": False, "expiry_days": -3, "headers": {"hsts": False, "csp": False}, "label": True, "label_weight": 2.0}),
    ("clean", {"valid": True, "expiry_days": 180, "headers": {"hsts": True, "csp": True}, "label": False, "label_weight": 1.0}),
    ("mixed", {"valid": True, "expiry_days": 14, "headers": {"hsts": True, "csp": False}, "label": True, "label_weight": 1.0}),
    ("timeout_risk", {"valid": True, "expiry_days": 2, "headers": {"hsts": False, "csp": False}, "label": True, "label_weight": 1.0}),
]

CURRICULA_STEPS = 5
WEAKNESS_FEATURE_NAMES = ["partial_flag", "http_error_flag", "hsts_missing"]


def _make_pipeline() -> EvidencePipeline:
    program = build_experiment_dsl()
    return EvidencePipeline(
        feature_program=program,
        causal_graph=OnlineCausalGraphLearner(
            independence_min_support=5.0,
            redundancy_threshold=0.85,
            source_min_support=2.0,
            min_corroborating_sources=2,
        ),
        config=PipelineConfig(backend="memory", emit_graph_snapshot=False),
        adapter=MemoryKafkaAdapter(),
    )


def _generate_training_data() -> List[Dict[str, Any]]:
    artifacts: List[Dict[str, Any]] = []
    for source in TRAINING_SOURCES:
        for i in range(TRAINING_ITEMS_PER_SOURCE):
            risky = i < 15
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
                    "valid": bool(risky),
                    "expiry_days": expiry_days,
                    "headers": {"hsts": hsts, "csp": csp},
                    "label": risky,
                    "label_weight": label_weight,
                },
                transport_meta=EvidenceTransportMeta(
                    status=status, latency_ms=latency, bytes_received=512,
                ),
            )
            artifact.integrity.hash = compute_artifact_hash(artifact)
            artifacts.append(artifact.to_dict())
    return artifacts


def _generate_ofe_signals(seed_offset: int = 0) -> List[EvidenceArtifact]:
    artifacts: List[EvidenceArtifact] = []
    for i in range(OFE_SIGNAL_COUNT):
        signals = {
            "contradiction_density": min(1.0, 0.3 + ((i + seed_offset) * 7 % 10) / 10.0),
            "topology_drift": min(1.0, 0.2 + ((i + seed_offset) * 13 % 10) / 10.0),
            "symbol_entropy": min(1.0, 0.4 + ((i + seed_offset) * 3 % 10) / 10.0),
            "pattern_frequency": min(1.0, 0.1 + ((i + seed_offset) * 5 % 10) / 10.0),
            "anomaly_score": min(1.0, 0.5 + ((i + seed_offset) * 11 % 10) / 10.0),
        }
        artifact = FrontierExplorer.wrap_structural_signals(
            signals, source="ofe", label=False,
        )
        artifacts.append(artifact)
    return artifacts


def _train_pipeline(pipeline: EvidencePipeline, training_data: List[Dict[str, Any]]) -> None:
    for d in training_data:
        pipeline.ingest(d)
    while pipeline.process_one(timeout=0.01) is not None:
        pass


def _inject_ofe_signals(pipeline: EvidencePipeline, signals: List[EvidenceArtifact]) -> None:
    for signal in signals:
        pipeline.ingest(signal.to_dict())
        pipeline.process_one(timeout=0.05)


def _run_curriculum(
    pipeline: EvidencePipeline,
    seed_data: Dict[str, Any],
    explorer: FrontierExplorer,
    steps: int,
) -> tuple[ExplorationSession, List[bool], List[float]]:
    seed = EvidenceArtifact(
        source="collector-a",
        type="tls",
        data=dict(seed_data),
        transport_meta=EvidenceTransportMeta(status="ok", latency_ms=90, bytes_received=512),
    )
    seed.integrity.hash = compute_artifact_hash(seed)

    frontier_info = explorer.analyze_frontier()
    session = ExplorationSession(seed)
    curriculum = explorer.generate_curriculum(seed, steps=steps)

    ground_truth: List[bool] = []
    difficulties: List[float] = []

    for challenge in curriculum:
        expected_label = bool(challenge.artifact.data.get("label", False))
        ground_truth.append(expected_label)

        pipeline.ingest(challenge.artifact.to_dict())
        result = pipeline.process_one(timeout=0.05)

        difficulty = compute_difficulty(
            challenge.mutation_summary, challenge.step, steps, frontier_info["frontier_pressure"],
        )
        difficulties.append(difficulty)
        challenge.difficulty = difficulty
        session.add_challenge(challenge, result)

    return session, ground_truth, difficulties


class ExperimentRunner:
    def __init__(self, raw_dir: str = "experiments/raw_runs") -> None:
        self.raw_dir = raw_dir
        os.makedirs(raw_dir, exist_ok=True)

    def run(self, campaign_seed: int = 0) -> Dict[str, Any]:
        rng = random.Random(campaign_seed)
        m = MetricsCollector()

        training_data = _generate_training_data()
        rng.shuffle(training_data)
        ofe_signals = _generate_ofe_signals(seed_offset=campaign_seed * 100 + 42)

        pipeline_a = _make_pipeline()
        pipeline_b = _make_pipeline()
        explorer_a = FrontierExplorer(pipeline_a)

        _train_pipeline(pipeline_a, training_data)
        _train_pipeline(pipeline_b, training_data)
        _inject_ofe_signals(pipeline_b, ofe_signals)

        all_a_results: List[Optional[Dict[str, Any]]] = []
        all_b_results: List[Optional[Dict[str, Any]]] = []
        all_ground_truth: List[Optional[bool]] = []
        all_difficulties: List[float] = []

        a_conf_sequences: List[List[float]] = []
        b_conf_sequences: List[List[float]] = []
        all_a_weaknesses: List[Weakness] = []
        all_b_weaknesses: List[Weakness] = []

        for name, seed_data in CURRICULA:
            session_a, gt_a, diff_a = _run_curriculum(pipeline_a, seed_data, explorer_a, CURRICULA_STEPS)
            session_a.save(os.path.join(self.raw_dir, f"A_{name}_session.json"))

            report_a = ExplorationReport(session_a).save_json(
                os.path.join(self.raw_dir, f"A_{name}_report.json"),
                explorer_a.analyze_frontier(),
            )

            for i, ch in enumerate(session_a.challenges):
                result = {
                    "causal_probability": ch.get("predicted_probability", 0.0),
                    "decision": ch.get("decision", False),
                }
                all_a_results.append(result)
                all_ground_truth.append(gt_a[i] if i < len(gt_a) else None)
                all_difficulties.append(diff_a[i] if i < len(diff_a) else 0.0)

            a_conf_sequences.append(session_a.confidence_progression)
            all_a_weaknesses.extend(WeaknessExtractor.extract(session_a.to_dict(), report_a))

            explorer_b = FrontierExplorer(pipeline_b)
            session_b, gt_b, diff_b = _run_curriculum(pipeline_b, seed_data, explorer_b, CURRICULA_STEPS)
            session_b.save(os.path.join(self.raw_dir, f"B_{name}_session.json"))

            report_b = ExplorationReport(session_b).save_json(
                os.path.join(self.raw_dir, f"B_{name}_report.json"),
                explorer_b.analyze_frontier(),
            )

            for i, ch in enumerate(session_b.challenges):
                result = {
                    "causal_probability": ch.get("predicted_probability", 0.0),
                    "decision": ch.get("decision", False),
                }
                all_b_results.append(result)

            b_conf_sequences.append(session_b.confidence_progression)
            all_b_weaknesses.extend(WeaknessExtractor.extract(session_b.to_dict(), report_b))

        accuracy_a = m.accuracy(all_a_results, all_ground_truth)
        accuracy_b = m.accuracy(all_b_results, all_ground_truth)

        failure_a = m.failure_rate(all_a_results)
        failure_b = m.failure_rate(all_b_results)

        calib_a = m.confidence_calibration(all_a_results, all_ground_truth)
        calib_b = m.confidence_calibration(all_b_results, all_ground_truth)

        weakness_counts_a: Dict[str, int] = {}
        for name in WEAKNESS_FEATURE_NAMES:
            weakness_counts_a[name] = sum(
                1 for w in all_a_weaknesses
                if w.category == "feature_instability" and w.feature == name
            )
        weakness_counts_b: Dict[str, int] = {}
        for name in WEAKNESS_FEATURE_NAMES:
            weakness_counts_b[name] = sum(
                1 for w in all_b_weaknesses
                if w.category == "feature_instability" and w.feature == name
            )

        weakness_freq_a = m.weakness_frequency(all_a_weaknesses, WEAKNESS_FEATURE_NAMES, len(all_a_weaknesses))
        weakness_freq_b = m.weakness_frequency(all_b_weaknesses, WEAKNESS_FEATURE_NAMES, len(all_b_weaknesses))

        collapse_a = m.collapse_frequency(a_conf_sequences)
        collapse_b = m.collapse_frequency(b_conf_sequences)

        diff_dist_a = m.difficulty_distribution(all_a_results, all_difficulties, all_ground_truth)
        diff_dist_b = m.difficulty_distribution(all_b_results, all_difficulties, all_ground_truth)

        all_a_confs = [r.get("causal_probability", 0.0) for r in all_a_results if r is not None]
        all_b_confs = [r.get("causal_probability", 0.0) for r in all_b_results if r is not None]
        boundary_a = m.capability_boundary_position(all_a_confs, all_difficulties[:len(all_a_confs)])
        boundary_b = m.capability_boundary_position(all_b_confs, all_difficulties[:len(all_b_confs)])

        weakness_deltas: List[Dict[str, Any]] = []
        for item_a in weakness_freq_a:
            name = item_a["weakness"]
            item_b = next((x for x in weakness_freq_b if x["weakness"] == name), {})
            weakness_deltas.append({
                "weakness": name,
                "a_frequency": item_a["frequency"],
                "b_frequency": item_b.get("frequency", 0),
                "a_percent": item_a["percent_of_total"],
                "b_percent": item_b.get("percent_of_total", 0.0),
                "absolute_difference": round(item_b.get("frequency", 0) - item_a["frequency"], 1),
                "percentage_point_difference": round(item_b.get("percent_of_total", 0.0) - item_a["percent_of_total"], 1),
                "interpretation": "improvement" if item_b.get("frequency", 0) < item_a["frequency"]
                    else "regression" if item_b.get("frequency", 0) > item_a["frequency"]
                    else "unchanged",
            })

        total_weak_a = len(all_a_weaknesses)
        total_weak_b = len(all_b_weaknesses)

        registry_a = WeaknessRegistry(os.path.join(self.raw_dir, "A_weakness_registry.json"))
        registry_a.clear()
        registry_a.add_weaknesses(all_a_weaknesses, "A")
        registry_b = WeaknessRegistry(os.path.join(self.raw_dir, "B_weakness_registry.json"))
        registry_b.clear()
        registry_b.add_weaknesses(all_b_weaknesses, "B")

        return {
            "metadata": {
                "experiment": "OFE Experimental Campaign",
                "condition_a": "SPL Baseline (TLS only)",
                "condition_b": "SPL + OFE structural signals",
                "training_items": len(training_data),
                "ofe_signals": len(ofe_signals),
                "curricula": [n for n, _ in CURRICULA],
                "total_challenges": len(all_a_results),
            },
            "baseline": {
                "accuracy": accuracy_a,
                "failure_rate": failure_a,
                "calibration": calib_a,
                "weakness_frequency": weakness_freq_a,
                "total_weaknesses": total_weak_a,
                "weakness_counts": weakness_counts_a,
                "collapse": collapse_a,
                "difficulty_distribution": diff_dist_a,
                "capability_boundary": boundary_a,
            },
            "ofe": {
                "accuracy": accuracy_b,
                "failure_rate": failure_b,
                "calibration": calib_b,
                "weakness_frequency": weakness_freq_b,
                "total_weaknesses": total_weak_b,
                "weakness_counts": weakness_counts_b,
                "collapse": collapse_b,
                "difficulty_distribution": diff_dist_b,
                "capability_boundary": boundary_b,
            },
            "comparison": {
                "accuracy": m.compute_deltas(accuracy_a["accuracy"], accuracy_b["accuracy"]),
                "calibration_error": m.compute_deltas(calib_a["calibration_error"], calib_b["calibration_error"], lower_is_better=True),
                "error_rate": m.compute_deltas(failure_a["error_rate"], failure_b["error_rate"], lower_is_better=True),
                "collapse_rate": m.compute_deltas(collapse_a["collapse_rate"], collapse_b["collapse_rate"], lower_is_better=True),
                "total_weaknesses": m.compute_deltas(float(total_weak_a), float(total_weak_b), lower_is_better=True),
                "weakness_level": weakness_deltas,
                "difficulty_distribution": {
                    bucket: m.compute_deltas(
                        diff_dist_a[bucket]["accuracy"],
                        diff_dist_b[bucket]["accuracy"],
                        a_label="A_accuracy",
                        b_label="B_accuracy",
                    )
                    for bucket in diff_dist_a
                },
                "capability_boundary": {
                    "a_fraction_below": boundary_a["fraction_below"],
                    "b_fraction_below": boundary_b["fraction_below"],
                    "delta_fraction_below": round(boundary_b["fraction_below"] - boundary_a["fraction_below"], 4),
                },
            },
        }
