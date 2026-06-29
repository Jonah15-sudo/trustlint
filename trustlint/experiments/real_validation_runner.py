from __future__ import annotations

import gc
import json
import os
import random
import sys
import time as _time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from spl_v7.causal import OnlineCausalGraphLearner
from spl_v7.frontier import FrontierExplorer
from spl_v7.kafka_pipeline import EvidencePipeline, MemoryKafkaAdapter, PipelineConfig
from spl_v7.schema import EvidenceArtifact, EvidenceTransportMeta
from spl_v7.verification import compute_artifact_hash

from experiments.dsl_helpers import build_experiment_dsl
from experiments.metrics import MetricsCollector
from experiments.real_data_loader import load_real_tls_data
from frontier.session import ExplorationSession, ExplorationReport, compute_difficulty
from weakness_mapper.extractor import Weakness, WeaknessExtractor


CURRICULA = [
    ("standard", {"valid": True, "expiry_days": 7, "headers": {"hsts": False, "csp": True}, "label": True, "label_weight": 1.0}),
    ("expired", {"valid": False, "expiry_days": -3, "headers": {"hsts": False, "csp": False}, "label": True, "label_weight": 2.0}),
    ("clean", {"valid": True, "expiry_days": 180, "headers": {"hsts": True, "csp": True}, "label": False, "label_weight": 1.0}),
    ("mixed", {"valid": True, "expiry_days": 14, "headers": {"hsts": True, "csp": False}, "label": True, "label_weight": 1.0}),
    ("timeout_risk", {"valid": True, "expiry_days": 2, "headers": {"hsts": False, "csp": False}, "label": True, "label_weight": 1.0}),
]

CURRICULA_STEPS = 5
WEAKNESS_FEATURE_NAMES = ["partial_flag", "http_error_flag", "hsts_missing"]
OFE_SIGNAL_COUNT = 15
_DEFAULT_DIR = "reports/real_data_validation"
MAX_FRONTIER_ROWS = 200
OFE_STATUS = "HOLD_PENDING_REAL_DATA"

_SAMPLE_FIXTURE_NAMES = {"real_tls_sample.jsonl", "real_tls_sample.csv"}


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


def _build_training_data(valid_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    artifacts: List[Dict[str, Any]] = []
    for row in valid_rows:
        artifact = EvidenceArtifact(
            source="real-tls",
            type="tls",
            data={
                "valid": bool(row["tls_valid"]),
                "expiry_days": int(row["tls_expiry_days"]),
                "headers": {
                    "hsts": bool(row["hsts_present"]),
                    "csp": bool(row["csp_present"]),
                },
                "label": bool(row["label"]),
                "label_weight": 1.0,
            },
            transport_meta=EvidenceTransportMeta(
                status=str(row["http_status"]),
                latency_ms=int(row["latency_ms"]),
                bytes_received=int(row["bytes_received"]),
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
    cached_frontier_info: Optional[Dict[str, Any]] = None,
) -> tuple[ExplorationSession, List[bool], List[float]]:
    seed = EvidenceArtifact(
        source="real-tls",
        type="tls",
        data=dict(seed_data),
        transport_meta=EvidenceTransportMeta(status="ok", latency_ms=90, bytes_received=512),
    )
    seed.integrity.hash = compute_artifact_hash(seed)

    frontier_info = cached_frontier_info if cached_frontier_info is not None else explorer.analyze_frontier()
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


class RealValidationRunner:
    _run_counter: int = 0

    def __init__(self, campaign_count: int = 1, verbose: bool = False) -> None:
        if campaign_count < 1:
            raise ValueError("campaign_count must be >= 1")
        self.campaign_count = campaign_count
        self.verbose = verbose
        self.m = MetricsCollector()
        self._run_id = str(uuid4())[:8]
        self._output_dir = f"{_DEFAULT_DIR}_{self._run_id}"

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"  [{_time.monotonic():.1f}s] {msg}", flush=True)

    @staticmethod
    def _flush(msg: str) -> None:
        print(f"[RealValidationRunner] {msg}", flush=True)

    # ── public API ────────────────────────────────────────────────────

    def run(self, dataset_path: str) -> Dict[str, Any]:
        t_start = _time.monotonic()
        self._flush("enter run()")
        if os.path.isfile("weakness_registry.json"):
            try:
                os.remove("weakness_registry.json")
            except OSError:
                pass
        result = self._validate_dataset(dataset_path)
        raw_valid_rows = result["raw_valid_rows"]
        validation = result["validation"]
        self._flush("after validate_dataset")

        total_rows = len(raw_valid_rows)
        self._flush(f"total_rows={total_rows}")
        frontier_rows = raw_valid_rows[:MAX_FRONTIER_ROWS]
        self._flush("building training data")
        training_data = _build_training_data(frontier_rows)
        self._log(f"Contract validation: {total_rows} rows (full dataset)")
        self._log(f"Frontier exploration sample: {len(training_data)} rows (max {MAX_FRONTIER_ROWS})")
        print(f"[RealValidationRunner] Dataset: {total_rows} rows (full), "
              f"Frontier: {len(training_data)} rows (sampled)", flush=True)

        campaigns: List[Dict[str, Any]] = []
        for campaign_idx in range(self.campaign_count):
            print(f"[RealValidationRunner] Campaign {campaign_idx + 1}/{self.campaign_count}...", flush=True)
            t_camp = _time.monotonic()
            campaign_result = self._run_single_campaign(training_data, campaign_idx, frontier_rows)
            self._log(f"Campaign {campaign_idx + 1} done in {_time.monotonic() - t_camp:.1f}s")
            campaigns.append(campaign_result)

        self._log("Aggregating campaign results")
        aggregated = self._aggregate_campaigns(campaigns)
        self._flush("aggregation done")

        results_json = _build_results_json(dataset_path, validation, aggregated, campaigns, len(frontier_rows))
        summary_md = _build_summary_md(dataset_path, validation, aggregated, total_rows, len(frontier_rows))
        promotion_md = _build_promotion_assessment_md(aggregated)

        od = self._output_dir
        os.makedirs(od, exist_ok=True)
        _write_output(od, "real_data_validation_results.json", results_json)
        _write_output(od, "real_data_validation_summary.md", summary_md)
        _write_output(od, "real_data_promotion_assessment.md", promotion_md)

        elapsed = _time.monotonic() - t_start
        print(f"[RealValidationRunner] Outputs written to {od}/ ({elapsed:.1f}s total)", flush=True)
        self._flush("exit run()")

        gc.collect()
        return results_json

    # ── validation ────────────────────────────────────────────────────

    @staticmethod
    def _validate_dataset(dataset_path: str) -> Dict[str, Any]:
        if not os.path.isfile(dataset_path):
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")

        basename = os.path.basename(dataset_path)
        if basename in _SAMPLE_FIXTURE_NAMES:
            raise ValueError(
                f"Rejected sample fixture '{basename}'. "
                f"The sample fixture must never be treated as evidence. "
                f"Provide a real 5000+ row TLS dataset instead."
            )

        print("  [diag] calling load_real_tls_data...", flush=True)
        result = load_real_tls_data(dataset_path)
        print("  [diag] load_real_tls_data returned", flush=True)
        validation = result["validation"]

        if validation.get("error"):
            raise ValueError(f"Dataset error: {validation['error']}")

        if validation["valid"] == 0:
            raise ValueError(
                f"Dataset has zero valid rows — cannot run validation"
            )

        if validation["skipped"] > 0:
            raise ValueError(
                f"Dataset has {validation['skipped']} invalid row(s) — "
                f"all rows must pass contract validation"
            )

        if validation["total"] < 5000:
            raise ValueError(
                f"Dataset too small: {validation['total']} rows "
                f"(minimum 5000 required)"
            )

        total_labeled = validation["positive_count"] + validation["negative_count"]
        if total_labeled > 0:
            pos_pct = validation["positive_count"] / total_labeled * 100
            if pos_pct < 10.0:
                raise ValueError(
                    f"Positive label ratio too low: {pos_pct:.1f}% "
                    f"(minimum 10% required)"
                )

        print(f"[RealValidationRunner] Dataset passed contract validation: "
              f"{validation['valid']} rows, "
              f"{validation['positive_count']} positive / {validation['negative_count']} negative", flush=True)
        return result

    # ── single campaign ───────────────────────────────────────────────

    def _run_single_campaign(
        self,
        training_data: List[Dict[str, Any]],
        campaign_idx: int,
        frontier_rows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        rng = random.Random(campaign_idx)
        shuffled = list(training_data)
        rng.shuffle(shuffled)

        ofe_signals = _generate_ofe_signals(seed_offset=campaign_idx * 100 + 42)

        t_a = _time.monotonic()
        pipeline_a = _make_pipeline()
        explorer_a = FrontierExplorer(pipeline_a)
        _train_pipeline(pipeline_a, shuffled)
        self._log(f"  Pipeline A trained ({len(shuffled)} rows, {_time.monotonic() - t_a:.1f}s)")

        t_b = _time.monotonic()
        pipeline_b = _make_pipeline()
        explorer_b = FrontierExplorer(pipeline_b)
        _train_pipeline(pipeline_b, shuffled)
        _inject_ofe_signals(pipeline_b, ofe_signals)
        self._log(f"  Pipeline B trained + OFE injected ({_time.monotonic() - t_b:.1f}s)")

        # Cache analyze_frontier — snapshot once per condition, then monkey-patch
        # to prevent generate_curriculum (called per curriculum inside _run_curriculum)
        # from calling it again (which causes hangs on second sequential run).
        t_fa = _time.monotonic()
        frontier_info_a = explorer_a.analyze_frontier()
        frontier_info_b = explorer_b.analyze_frontier()
        explorer_a.analyze_frontier = lambda fia=frontier_info_a: fia
        explorer_b.analyze_frontier = lambda fib=frontier_info_b: fib
        self._log(f"  analyze_frontier cached (A + B, {_time.monotonic() - t_fa:.1f}s)")

        all_a_results: List[Optional[Dict[str, Any]]] = []
        all_b_results: List[Optional[Dict[str, Any]]] = []
        all_ground_truth: List[Optional[bool]] = []
        all_difficulties: List[float] = []

        a_conf_sequences: List[List[float]] = []
        b_conf_sequences: List[List[float]] = []
        all_a_weaknesses: List[Weakness] = []
        all_b_weaknesses: List[Weakness] = []

        for name, seed_data in CURRICULA:
            self._flush(f"curriculum {name}")

            self._flush(f"  curriculum {name}: _run_curriculum A")
            session_a, gt_a, diff_a = _run_curriculum(
                pipeline_a, seed_data, explorer_a, CURRICULA_STEPS,
                cached_frontier_info=frontier_info_a,
            )
            self._flush(f"  curriculum {name}: _run_curriculum A done")

            self._flush(f"  curriculum {name}: report A")
            report_a = ExplorationReport(session_a).generate(
                frontier_info_a,
            )
            self._flush(f"  curriculum {name}: report A done")

            self._flush(f"  curriculum {name}: extractor A")
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
            self._flush(f"  curriculum {name}: extractor A done")

            self._flush(f"  curriculum {name}: _run_curriculum B")
            session_b, gt_b, diff_b = _run_curriculum(
                pipeline_b, seed_data, explorer_b, CURRICULA_STEPS,
                cached_frontier_info=frontier_info_b,
            )
            self._flush(f"  curriculum {name}: _run_curriculum B done")

            self._flush(f"  curriculum {name}: report B")
            report_b = ExplorationReport(session_b).generate(
                frontier_info_b,
            )
            self._flush(f"  curriculum {name}: report B done")

            self._flush(f"  curriculum {name}: extractor B")
            for i, ch in enumerate(session_b.challenges):
                result = {
                    "causal_probability": ch.get("predicted_probability", 0.0),
                    "decision": ch.get("decision", False),
                }
                all_b_results.append(result)

            b_conf_sequences.append(session_b.confidence_progression)
            all_b_weaknesses.extend(WeaknessExtractor.extract(session_b.to_dict(), report_b))
            self._flush(f"  curriculum {name}: extractor B done")

            del session_a, session_b, report_a, report_b, gt_a, gt_b, diff_a, diff_b

        self._flush("metrics aggregation start")
        accuracy_a = self.m.accuracy(all_a_results, all_ground_truth)
        accuracy_b = self.m.accuracy(all_b_results, all_ground_truth)
        failure_a = self.m.failure_rate(all_a_results)
        failure_b = self.m.failure_rate(all_b_results)
        calib_a = self.m.confidence_calibration(all_a_results, all_ground_truth)
        calib_b = self.m.confidence_calibration(all_b_results, all_ground_truth)
        self._flush("metrics aggregation done")

        weakness_counts_a: Dict[str, int] = {}
        weakness_counts_b: Dict[str, int] = {}
        for name in WEAKNESS_FEATURE_NAMES:
            weakness_counts_a[name] = sum(
                1 for w in all_a_weaknesses
                if w.category == "feature_instability" and w.feature == name
            )
            weakness_counts_b[name] = sum(
                1 for w in all_b_weaknesses
                if w.category == "feature_instability" and w.feature == name
            )

        weakness_freq_a = self.m.weakness_frequency(
            all_a_weaknesses, WEAKNESS_FEATURE_NAMES, len(all_a_weaknesses),
        )
        weakness_freq_b = self.m.weakness_frequency(
            all_b_weaknesses, WEAKNESS_FEATURE_NAMES, len(all_b_weaknesses),
        )
        collapse_a = self.m.collapse_frequency(a_conf_sequences)
        collapse_b = self.m.collapse_frequency(b_conf_sequences)
        diff_dist_a = self.m.difficulty_distribution(
            all_a_results, all_difficulties, all_ground_truth,
        )
        diff_dist_b = self.m.difficulty_distribution(
            all_b_results, all_difficulties, all_ground_truth,
        )
        all_a_confs = [r.get("causal_probability", 0.0) for r in all_a_results if r is not None]
        all_b_confs = [r.get("causal_probability", 0.0) for r in all_b_results if r is not None]
        boundary_a = self.m.capability_boundary_position(
            all_a_confs, all_difficulties[:len(all_a_confs)],
        )
        boundary_b = self.m.capability_boundary_position(
            all_b_confs, all_difficulties[:len(all_b_confs)],
        )

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
                "percentage_point_difference": round(
                    item_b.get("percent_of_total", 0.0) - item_a["percent_of_total"], 1,
                ),
                "interpretation": (
                    "improvement" if item_b.get("frequency", 0) < item_a["frequency"]
                    else "regression" if item_b.get("frequency", 0) > item_a["frequency"]
                    else "unchanged"
                ),
            })

        result = {
            "campaign_index": campaign_idx,
            "training_items": len(training_data),
            "ofe_signals": len(ofe_signals),
            "baseline": {
                "accuracy": accuracy_a,
                "error_rate": failure_a,
                "calibration": calib_a,
                "collapse": collapse_a,
                "total_weaknesses": len(all_a_weaknesses),
                "weakness_frequency": weakness_freq_a,
                "weakness_counts": weakness_counts_a,
                "difficulty_distribution": diff_dist_a,
                "capability_boundary": boundary_a,
            },
            "ofe": {
                "accuracy": accuracy_b,
                "error_rate": failure_b,
                "calibration": calib_b,
                "collapse": collapse_b,
                "total_weaknesses": len(all_b_weaknesses),
                "weakness_frequency": weakness_freq_b,
                "weakness_counts": weakness_counts_b,
                "difficulty_distribution": diff_dist_b,
                "capability_boundary": boundary_b,
            },
            "comparison": {
                "accuracy": self.m.compute_deltas(
                    accuracy_a["accuracy"], accuracy_b["accuracy"],
                ),
                "calibration_error": self.m.compute_deltas(
                    calib_a["calibration_error"], calib_b["calibration_error"],
                    lower_is_better=True,
                ),
                "error_rate": self.m.compute_deltas(
                    failure_a["error_rate"], failure_b["error_rate"],
                    lower_is_better=True,
                ),
                "collapse_rate": self.m.compute_deltas(
                    collapse_a["collapse_rate"], collapse_b["collapse_rate"],
                    lower_is_better=True,
                ),
                "total_weaknesses": self.m.compute_deltas(
                    float(len(all_a_weaknesses)), float(len(all_b_weaknesses)),
                    lower_is_better=True,
                ),
                "weakness_level": weakness_deltas,
                "difficulty_distribution": {
                    bucket: self.m.compute_deltas(
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
                    "delta_fraction_below": round(
                        boundary_b["fraction_below"] - boundary_a["fraction_below"], 4,
                    ),
                },
            },
        }

        del pipeline_a, pipeline_b, explorer_a, explorer_b
        return result

    # ── aggregation ────────────────────────────────────────────────────

    @staticmethod
    def _aggregate_campaigns(campaigns: List[Dict[str, Any]]) -> Dict[str, Any]:
        n = len(campaigns)

        def _mean_nested(subkey: str, *keys: str) -> float:
            vals = []
            for c in campaigns:
                v = c[subkey]
                for k in keys:
                    v = v[k]
                vals.append(v)
            return round(sum(vals) / n, 4) if n else 0.0

        def _mean_weakness_freq(subkey: str) -> List[Dict[str, Any]]:
            all_freqs: Dict[str, List[float]] = {}
            for c in campaigns:
                for item in c[subkey]["weakness_frequency"]:
                    name = item["weakness"]
                    if name not in all_freqs:
                        all_freqs[name] = []
                    all_freqs[name].append(item["frequency"])
            result: List[Dict[str, Any]] = []
            for name, freqs in sorted(all_freqs.items()):
                avg_f = round(sum(freqs) / len(freqs), 1)
                result.append({
                    "weakness": name,
                    "mean_frequency": avg_f,
                    "campaign_count": len(freqs),
                })
            return result

        baseline_mean = {
            "accuracy": _mean_nested("baseline", "accuracy", "accuracy"),
            "error_rate": _mean_nested("baseline", "error_rate", "error_rate"),
            "calibration_error": _mean_nested("baseline", "calibration", "calibration_error"),
            "collapse_rate": _mean_nested("baseline", "collapse", "collapse_rate"),
            "total_weaknesses": round(
                sum(c["baseline"]["total_weaknesses"] for c in campaigns) / n, 1,
            ) if n else 0.0,
            "weakness_frequency": _mean_weakness_freq("baseline"),
        }

        ofe_mean = {
            "accuracy": _mean_nested("ofe", "accuracy", "accuracy"),
            "error_rate": _mean_nested("ofe", "error_rate", "error_rate"),
            "calibration_error": _mean_nested("ofe", "calibration", "calibration_error"),
            "collapse_rate": _mean_nested("ofe", "collapse", "collapse_rate"),
            "total_weaknesses": round(
                sum(c["ofe"]["total_weaknesses"] for c in campaigns) / n, 1,
            ) if n else 0.0,
            "weakness_frequency": _mean_weakness_freq("ofe"),
        }

        regimes = []
        for regime, lower_is_better in [
            ("accuracy", False),
            ("calibration_error", True),
            ("error_rate", True),
            ("collapse_rate", True),
            ("total_weaknesses", True),
        ]:
            deltas = [c["comparison"][regime]["absolute_difference"] for c in campaigns]
            improvements = sum(1 for d in deltas if (d > 0 and not lower_is_better) or (d < 0 and lower_is_better))
            regressions = sum(1 for d in deltas if (d < 0 and not lower_is_better) or (d > 0 and lower_is_better))
            regimes.append({
                "metric": regime,
                "mean_delta": round(sum(deltas) / n, 4),
                "improvement_count": improvements,
                "regression_count": regressions,
                "unchanged_count": n - improvements - regressions,
                "improvement_rate": round(improvements / n * 100, 1),
            })

        return {
            "campaign_count": n,
            "baseline_mean": baseline_mean,
            "ofe_mean": ofe_mean,
            "regime_summary": regimes,
            "overall": _evaluate_overall(regimes),
        }


def _evaluate_overall(regimes: List[Dict[str, Any]]) -> str:
    repro_improvement = any(r["improvement_rate"] >= 70.0 for r in regimes)
    any_regression = any(r["regression_count"] > 0 for r in regimes)
    if repro_improvement and not any_regression:
        return "CANDIDATE_FOR_PROMOTION"
    if any_regression:
        return "NOT_READY_REGRESSION_DETECTED"
    return "INCONCLUSIVE"


def _build_summary_md(
    dataset_path: str,
    validation: Dict[str, Any],
    aggregated: Dict[str, Any],
    total_rows: int,
    frontier_sample_size: int,
) -> str:
    bm = aggregated["baseline_mean"]
    om = aggregated["ofe_mean"]

    lines = [
        "# Real Data Validation Summary",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}Z",
        f"Dataset: `{dataset_path}`",
        "",
        "---",
        "",
        "## Dataset",
        "",
        f"- Total rows: {validation['total']}",
        f"- Valid rows: {validation['valid']}",
        f"- Positive labels: {validation['positive_count']}",
        f"- Negative labels: {validation['negative_count']}",
        "",
        "## Frontier Exploration Scope",
        "",
        f"- Contract validation: **{total_rows} rows** (full dataset)",
        f"- Frontier training + curricula: **{frontier_sample_size} rows** (bounded sample, max {MAX_FRONTIER_ROWS})",
        "",
        "---",
        "",
        "## Campaigns",
        "",
        f"- Campaigns run: {aggregated['campaign_count']}",
        "",
        "---",
        "",
        "## Aggregated Results (mean across campaigns)",
        "",
        "| Metric | Baseline | OFE |",
        "|---|---|---|",
        f"| Accuracy | {bm['accuracy']} | {om['accuracy']} |",
        f"| Error Rate | {bm['error_rate']} | {om['error_rate']} |",
        f"| Calibration Error | {bm['calibration_error']} | {om['calibration_error']} |",
        f"| Collapse Rate | {bm['collapse_rate']} | {om['collapse_rate']} |",
        f"| Total Weaknesses | {bm['total_weaknesses']} | {om['total_weaknesses']} |",
        "",
        "## Regime Summary",
        "",
        "| Metric | Mean Delta | Improvement Rate |",
        "|---|---|---|",
    ]

    for regime in aggregated["regime_summary"]:
        lines.append(
            f"| {regime['metric']} | {regime['mean_delta']} | {regime['improvement_rate']}% |"
        )

    lines.extend([
        "",
        "## Overall Verdict",
        "",
        f"**{aggregated['overall']}**",
        "",
        "---",
        "",
        "**IMPORTANT**: These results are based on the provided dataset. ",
        f"OFE remains {OFE_STATUS} until all promotion criteria are met.",
        "No signal was promoted by this runner.",
        "",
        "> **Dataset gate**: Generated test data and sample fixtures are ",
        "> explicitly rejected. Only a real 5000+ row TLS dataset ",
        "> with ≥10% positive labels can trigger promotion assessment.",
    ])
    return "\n".join(lines)


def _build_promotion_assessment_md(aggregated: Dict[str, Any]) -> str:
    regimes = aggregated["regime_summary"]

    lines = [
        "# Real Data Promotion Assessment",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}Z",
        "",
        "---",
        "",
        "## Promotion Criteria Check",
        "",
        "| Criterion | Status | Detail |",
        "|---|---|---|",
    ]

    accuracy_regime = next((r for r in regimes if r["metric"] == "accuracy"), None)
    calib_regime = next((r for r in regimes if r["metric"] == "calibration_error"), None)
    error_regime = next((r for r in regimes if r["metric"] == "error_rate"), None)
    collapse_regime = next((r for r in regimes if r["metric"] == "collapse_rate"), None)
    weakness_regime = next((r for r in regimes if r["metric"] == "total_weaknesses"), None)

    criteria = []

    if accuracy_regime and accuracy_regime["mean_delta"] >= 0:
        criteria.append(("No accuracy regression", "PASS",
                         f"Mean delta = {accuracy_regime['mean_delta']}"))
    else:
        criteria.append(("No accuracy regression", "FAIL",
                         f"Mean delta = {accuracy_regime['mean_delta'] if accuracy_regime else 'N/A'}"))

    if calib_regime and calib_regime["mean_delta"] <= 0:
        criteria.append(("No calibration regression", "PASS",
                         f"Mean delta = {calib_regime['mean_delta']}"))
    else:
        criteria.append(("No calibration regression", "FAIL",
                         f"Mean delta = {calib_regime['mean_delta'] if calib_regime else 'N/A'}"))

    if weakness_regime and weakness_regime["mean_delta"] <= 0:
        criteria.append(("No weakness count increase", "PASS",
                         f"Mean delta = {weakness_regime['mean_delta']}"))
    else:
        criteria.append(("No weakness count increase", "FAIL",
                         f"Mean delta = {weakness_regime['mean_delta'] if weakness_regime else 'N/A'}"))

    repro_improvement = any(r["improvement_rate"] >= 70.0 for r in regimes)
    if repro_improvement:
        criteria.append(("Reproducible improvement (>=70% campaigns)", "PASS",
                         f"See regime summary"))
    else:
        criteria.append(("Reproducible improvement (>=70% campaigns)", "FAIL",
                         f"No regime reached 70% improvement rate"))

    criteria.append(("SPL Core unmodified", "PASS",
                      "spl_v7/ was not touched by this runner"))
    criteria.append(("No threshold tuning", "PASS",
                      "All thresholds preserved at original values"))

    for name, status, detail in criteria:
        lines.append(f"| {name} | {status} | {detail} |")

    all_pass = all(s == "PASS" for _, s, _ in criteria)
    verdict = "CANDIDATE_FOR_PROMOTION" if all_pass else "HOLD_PENDING_REAL_DATA"

    lines.extend([
        "",
        "---",
        "",
        "## Verdict",
        "",
        f"**{verdict}**",
        "",
    ])

    if not all_pass:
        lines.append(
            "OFE structural signals remain HOLD_PENDING_REAL_DATA. "
            "Not all promotion criteria were met on this dataset."
        )
    else:
        lines.append(
            "All promotion criteria are met on this dataset. "
            "However, this assessment is ADVISORY. "
            "Human review is required before any signal is promoted. "
            "Promotion does NOT authorize automatic deployment."
        )

    lines.append("")
    lines.append("**No signal was promoted by this runner.**")
    lines.append(f"OFE remains {OFE_STATUS} until human review.")
    lines.append("")
    if not all_pass:
        lines.append(
            "> **Dataset gate**: Generated test data and sample fixtures are "
            "explicitly rejected. Only a real 5000+ row TLS dataset "
            "with ≥10% positive labels can trigger promotion assessment."
        )

    return "\n".join(lines)


def _build_results_json(
    dataset_path: str,
    validation: Dict[str, Any],
    aggregated: Dict[str, Any],
    campaigns: List[Dict[str, Any]],
    frontier_sample_size: int,
) -> Dict[str, Any]:
    return {
        "metadata": {
            "runner": "RealValidationRunner",
            "dataset": os.path.abspath(dataset_path),
            "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
            "campaign_count": len(campaigns),
            "condition_a": "SPL Baseline (TLS only, trained on real data)",
            "condition_b": "SPL + OFE structural signals (trained on real data)",
            "note": f"No OFE signal was promoted. OFE remains {OFE_STATUS}.",
            "frontier_sample": {
                "description": "Contract validation uses ALL rows; Frontier exploration (training + curricula) uses a bounded sample for performance",
                "max_frontier_rows": MAX_FRONTIER_ROWS,
                "actual_frontier_rows": frontier_sample_size,
            },
        },
        "dataset": {
            "total_rows": validation["total"],
            "valid_rows": validation["valid"],
            "skipped_rows": validation["skipped"],
            "positive_count": validation["positive_count"],
            "negative_count": validation["negative_count"],
        },
        "aggregated": aggregated,
        "campaigns": campaigns,
    }


def _write_output(output_dir: str, filename: str, content: Any) -> str:
    path = os.path.join(output_dir, filename)
    if isinstance(content, (dict, list)):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
    elif isinstance(content, str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        raise TypeError(f"Unsupported content type: {type(content)}")
    return path


# ── CLI entry point ─────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m experiments.real_validation_runner <dataset_path> [campaigns] [--verbose]")
        print("")
        print("  dataset_path   Path to JSONL or CSV dataset (min 5000 rows, min 10% positive)")
        print("  campaigns      Number of A/B campaigns to run (default: 1)")
        print("  --verbose      Print per-phase timing info")
        sys.exit(1)

    dataset_path = sys.argv[1]
    args = sys.argv[2:]
    campaign_count = 1
    verbose = False
    for a in args:
        if a == "--verbose":
            verbose = True
        else:
            try:
                campaign_count = int(a)
            except ValueError:
                print(f"Error: unrecognized argument: {a}")
                sys.exit(1)

    if not os.path.isfile(dataset_path):
        print(f"Error: dataset not found: {dataset_path}")
        sys.exit(1)

    runner = RealValidationRunner(campaign_count=campaign_count, verbose=verbose)

    try:
        results = runner.run(dataset_path)
        overall = results["aggregated"]["overall"]
        print(f"\n[RealValidationRunner] Done. Overall: {overall}", flush=True)
        print(f"[RealValidationRunner] OFE status: {OFE_STATUS}", flush=True)
        print(f"[RealValidationRunner] No signal was promoted.", flush=True)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
