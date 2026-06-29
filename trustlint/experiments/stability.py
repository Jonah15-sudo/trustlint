from __future__ import annotations

import json
import os
import math
from collections import defaultdict
from typing import Any, Dict, List, Tuple


def _mean(vals: List[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _stdev(vals: List[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = _mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def _cohens_d(a: List[float], b: List[float]) -> float:
    if len(a) < 2 or len(b) < 2:
        return 0.0
    ma, mb = _mean(a), _mean(b)
    sa, sb = _stdev(a), _stdev(b)
    p = math.sqrt((sa ** 2 + sb ** 2) / 2)
    return 0.0 if p == 0 else (mb - ma) / p


def _ci95(vals: List[float]) -> Tuple[float, float]:
    n = len(vals)
    if n < 2:
        return (0.0, 0.0)
    m = _mean(vals)
    s = _stdev(vals)
    margin = 1.96 * s / math.sqrt(n)
    return (round(m - margin, 4), round(m + margin, 4))


class WeaknessStabilityAnalyzer:
    """Measures cross-campaign stability of weakness frequency, variance, and reproducibility."""

    def __init__(self, weakness_names: List[str]) -> None:
        self.weakness_names = weakness_names

    def analyze(self, baseline_counts: List[Dict[str, int]],
                ofe_counts: List[Dict[str, int]]) -> Dict[str, Any]:
        report: Dict[str, Any] = {}
        for name in self.weakness_names:
            a_vals = [c.get(name, 0) for c in baseline_counts]
            b_vals = [c.get(name, 0) for c in ofe_counts]
            diffs = [b - a for a, b in zip(a_vals, b_vals)]
            mean_a, mean_b = _mean([float(v) for v in a_vals]), _mean([float(v) for v in b_vals])

            variance_a = _stdev([float(v) for v in a_vals]) ** 2
            variance_b = _stdev([float(v) for v in b_vals]) ** 2

            improvements = sum(1 for d in diffs if d < 0)
            regressions = sum(1 for d in diffs if d > 0)
            n = len(diffs)

            report[name] = {
                "mean_baseline": round(mean_a, 2),
                "mean_ofe": round(mean_b, 2),
                "variance_baseline": round(variance_a, 2),
                "variance_ofe": round(variance_b, 2),
                "mean_difference": round(_mean([float(d) for d in diffs]), 2),
                "effect_size": round(_cohens_d([float(v) for v in a_vals], [float(v) for v in b_vals]), 4),
                "ci_95": list(_ci95([float(d) for d in diffs])),
                "improvement_campaigns": improvements,
                "regression_campaigns": regressions,
                "unchanged_campaigns": n - improvements - regressions,
                "replication_rate": round(improvements / n, 4) if n else 0.0,
                "status": "repeated" if (improvements / n >= 0.7 if n else False)
                    else "uncertain" if (improvements / n >= 0.3 if n else False)
                    else "not_repeated",
                "variance_change": "reduced" if variance_b < variance_a * 0.9
                    else "increased" if variance_b > variance_a * 1.1
                    else "stable",
            }
        return report


class ConfidenceStabilityAnalyzer:
    """Cross-campaign confidence, calibration, and collapse behavior."""

    def analyze(self, baseline_metrics: Dict[str, List[float]],
                ofe_metrics: Dict[str, List[float]]) -> Dict[str, Any]:
        report: Dict[str, Any] = {}
        for key in baseline_metrics:
            a, b = baseline_metrics[key], ofe_metrics[key]
            diffs = [bb - aa for aa, bb in zip(a, b)]
            effect = _cohens_d(a, b)
            report[key] = {
                "baseline_mean": round(_mean(a), 4),
                "ofe_mean": round(_mean(b), 4),
                "mean_difference": round(_mean(diffs), 4),
                "std_difference": round(_stdev(diffs), 4),
                "effect_size": round(effect, 4),
                "ci_95": list(_ci95(diffs)),
                "improvement_campaigns": sum(1 for d in diffs if d < 0),
                "regression_campaigns": sum(1 for d in diffs if d > 0),
            }
        report["delta_correlation"] = self._delta_correlation(baseline_metrics, ofe_metrics)
        return report

    def _delta_correlation(self, a: Dict[str, List[float]], b: Dict[str, List[float]]) -> Dict[str, float]:
        corrs: Dict[str, float] = {}
        for key in a:
            diffs_a = [bb - aa for aa, bb in zip(a[key], a[key])]
            diffs_b = [bb - aa for aa, bb in zip(a[key], b[key])]
            if len(set(diffs_a)) < 2 or len(set(diffs_b)) < 2:
                corrs[key] = 0.0
                continue
            ma, mb = _mean(diffs_a), _mean(diffs_b)
            num = sum((x - ma) * (y - mb) for x, y in zip(diffs_a, diffs_b))
            den = math.sqrt(sum((x - ma) ** 2 for x in diffs_a)) * math.sqrt(sum((y - mb) ** 2 for y in diffs_b))
            corrs[key] = round(num / den, 4) if den != 0 else 0.0
        return corrs
