from __future__ import annotations

import os
import json
import math
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from experiments.experiment_runner import ExperimentRunner
from experiments.metrics import MetricsCollector

from weakness_mapper.extractor import Weakness, WeaknessExtractor

_CAMPAIGN_COUNT_DEFAULT = 12


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _stdev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1))


def _cohens_d(a_values: List[float], b_values: List[float]) -> float:
    if len(a_values) < 2 or len(b_values) < 2:
        return 0.0
    ma, mb = _mean(a_values), _mean(b_values)
    sa, sb = _stdev(a_values), _stdev(b_values)
    pooled = math.sqrt((sa ** 2 + sb ** 2) / 2)
    if pooled == 0:
        return 0.0
    return (mb - ma) / pooled


def _ci95(values: List[float]) -> Tuple[float, float]:
    n = len(values)
    if n < 2:
        return (0.0, 0.0)
    m = _mean(values)
    s = _stdev(values)
    se = s / math.sqrt(n)
    margin = 1.96 * se
    return (round(m - margin, 4), round(m + margin, 4))


METRIC_SPECS: List[Dict[str, Any]] = [
    {"key": "accuracy_delta", "label": "Accuracy Δ", "lower_is_better": False},
    {"key": "calibration_delta", "label": "Calibration Error Δ", "lower_is_better": True},
    {"key": "error_rate_delta", "label": "Error Rate Δ", "lower_is_better": True},
    {"key": "collapse_rate_delta", "label": "Collapse Rate Δ", "lower_is_better": True},
    {"key": "weakness_count_delta", "label": "Weakness Count Δ", "lower_is_better": True},
]

WEAKNESS_NAMES = ["partial_flag", "http_error_flag", "hsts_missing"]


def _extract_deltas(result: Dict[str, Any]) -> Dict[str, float]:
    c = result["comparison"]
    return {
        "accuracy_delta": c["accuracy"]["absolute_difference"],
        "calibration_delta": c["calibration_error"]["absolute_difference"],
        "error_rate_delta": c["error_rate"]["absolute_difference"],
        "collapse_rate_delta": c["collapse_rate"]["absolute_difference"],
        "weakness_count_delta": c["total_weaknesses"]["absolute_difference"],
    }


def _extract_weakness_counts(result: Dict[str, Any]) -> Dict[str, Tuple[int, int]]:
    c = result["comparison"]
    out: Dict[str, Tuple[int, int]] = {}
    for wl in c["weakness_level"]:
        name = wl["weakness"]
        out[name] = (wl["a_frequency"], wl["b_frequency"])
    return out


def _extract_accuracy(result: Dict[str, Any], side: str) -> float:
    return result[side]["accuracy"]["accuracy"]


def _extract_calibration(result: Dict[str, Any], side: str) -> float:
    return result[side]["calibration"]["calibration_error"]


def _extract_collapse_rate(result: Dict[str, Any], side: str) -> float:
    return result[side]["collapse"]["collapse_rate"]


def _extract_weakness_count(result: Dict[str, Any], side: str) -> int:
    return result[side]["total_weaknesses"]


class ReplicationRunner:
    def __init__(self, campaign_count: int = _CAMPAIGN_COUNT_DEFAULT, raw_dir: str = "experiments/replication") -> None:
        self.campaign_count = campaign_count
        self.raw_dir = raw_dir
        os.makedirs(raw_dir, exist_ok=True)

    def run_all(self) -> Dict[str, Any]:
        runner = ExperimentRunner(raw_dir=os.path.join(self.raw_dir, "runs"))
        campaigns: List[Dict[str, Any]] = []

        for seed in range(self.campaign_count):
            print(f"\nCampaign {seed + 1}/{self.campaign_count} (seed={seed})...")
            result = runner.run(campaign_seed=seed)
            campaigns.append(result)

            seed_dir = os.path.join(self.raw_dir, "runs", f"campaign_{seed:03d}")
            os.makedirs(seed_dir, exist_ok=True)
            with open(os.path.join(seed_dir, "experiment_results.json"), "w") as f:
                json.dump(result, f, indent=2, ensure_ascii=True)

        aggregate = self._aggregate(campaigns)
        return aggregate

    def _aggregate(self, campaigns: List[Dict[str, Any]]) -> Dict[str, Any]:
        n = len(campaigns)

        deltas_by_metric: Dict[str, List[float]] = defaultdict(list)
        weakness_data_by_name: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
        a_vals: Dict[str, List[float]] = defaultdict(list)
        b_vals: Dict[str, List[float]] = defaultdict(list)

        for c in campaigns:
            for key in [s["key"] for s in METRIC_SPECS]:
                deltas_by_metric[key].append(_extract_deltas(c).get(key, 0.0))

            wc = _extract_weakness_counts(c)
            for name in WEAKNESS_NAMES:
                weakness_data_by_name[name].append(wc.get(name, (0, 0)))

            a_vals["accuracy"].append(_extract_accuracy(c, "baseline"))
            b_vals["accuracy"].append(_extract_accuracy(c, "ofe"))
            a_vals["calibration"].append(_extract_calibration(c, "baseline"))
            b_vals["calibration"].append(_extract_calibration(c, "ofe"))
            a_vals["collapse_rate"].append(_extract_collapse_rate(c, "baseline"))
            b_vals["collapse_rate"].append(_extract_collapse_rate(c, "ofe"))
            a_vals["weakness_count"].append(float(_extract_weakness_count(c, "baseline")))
            b_vals["weakness_count"].append(float(_extract_weakness_count(c, "ofe")))

        metric_summaries: List[Dict[str, Any]] = []
        for spec in METRIC_SPECS:
            key = spec["key"]
            vals = deltas_by_metric[key]
            mean_d = _mean(vals)
            std_d = _stdev(vals)
            ci_lo, ci_hi = _ci95(vals)
            d = _cohens_d(
                a_vals.get(key.replace("_delta", "").replace("calibration", "calibration").replace("error_rate", "accuracy"),
                          [0.0]),
                b_vals.get(key.replace("_delta", "").replace("calibration", "calibration").replace("error_rate", "accuracy"),
                          [0.0]),
            )
            improvement_count = sum(
                1 for v in vals
                if (v < 0 if spec["lower_is_better"] else v > 0)
            )
            regression_count = sum(
                1 for v in vals
                if (v > 0 if spec["lower_is_better"] else v < 0)
            )
            replication_rate = improvement_count / n if n else 0.0

            metric_summaries.append({
                "metric": spec["label"],
                "key": key,
                "lower_is_better": spec["lower_is_better"],
                "campaign_count": n,
                "mean_delta": round(mean_d, 4),
                "std_delta": round(std_d, 4),
                "ci_95_lo": ci_lo,
                "ci_95_hi": ci_hi,
                "cohens_d": round(d, 4),
                "improvement_count": improvement_count,
                "regression_count": regression_count,
                "replication_rate": round(replication_rate, 4),
                "reproducibility": "repeated" if replication_rate >= 0.7
                    else "uncertain" if replication_rate >= 0.3
                    else "not_repeated",
            })

        weakness_summaries: List[Dict[str, Any]] = []
        for name in WEAKNESS_NAMES:
            pairs = weakness_data_by_name[name]
            a_freqs = [p[0] for p in pairs]
            b_freqs = [p[1] for p in pairs]
            diffs = [b - a for a, b in pairs]
            mean_diff = _mean(diffs)
            std_diff = _stdev(diffs)
            improvements = sum(1 for d in diffs if d < 0)
            regressions = sum(1 for d in diffs if d > 0)
            a_floats = [float(v) for v in a_freqs]
            b_floats = [float(v) for v in b_freqs]
            es = _cohens_d(a_floats, b_floats)
            weakness_summaries.append({
                "weakness": name,
                "campaign_count": n,
                "mean_a_frequency": round(_mean(a_freqs), 2),
                "mean_b_frequency": round(_mean(b_freqs), 2),
                "mean_difference": round(mean_diff, 2),
                "std_difference": round(std_diff, 2),
                "effect_size": round(es, 4),
                "campaigns_with_improvement": improvements,
                "campaigns_with_regression": regressions,
                "replication_rate": round(improvements / n, 4) if n else 0.0,
                "reproducibility": "repeated" if (improvements / n >= 0.7 if n else False)
                    else "uncertain" if (improvements / n >= 0.3 if n else False)
                    else "not_repeated",
                "note": "effect_size may be 0.0 if baseline or OFE values have zero variance across campaigns" if es == 0.0 and n >= 2 else "",
            })

        return {
            "metadata": {
                "experiment": "OFE Replication Campaign",
                "campaign_count": n,
                "challenges_per_campaign": campaigns[0]["metadata"]["total_challenges"] if campaigns else 0,
            },
            "metric_summaries": metric_summaries,
            "weakness_summaries": weakness_summaries,
        }
