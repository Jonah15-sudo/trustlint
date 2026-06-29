from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from frontier.session import CollapseDetector
from weakness_mapper.extractor import Weakness


class MetricsCollector:
    @staticmethod
    def accuracy(
        results: Sequence[Optional[Mapping[str, Any]]],
        ground_truth: Sequence[Optional[bool]],
    ) -> Dict[str, Any]:
        total = len(results)
        predictions: List[Dict[str, Any]] = []
        for r, label in zip(results, ground_truth):
            if r is not None and label is not None:
                predictions.append({"predicted": r.get("decision", False), "actual": label})

        n = len(predictions)
        correct = sum(1 for p in predictions if p["predicted"] == p["actual"])
        return {
            "total_processed": total,
            "total_predicted": n,
            "correct": correct,
            "accuracy": round(correct / n, 4) if n else 0.0,
            "sample_size": n,
        }

    @staticmethod
    def failure_rate(results: Sequence[Optional[Mapping[str, Any]]]) -> Dict[str, Any]:
        total = len(results)
        errors = sum(1 for r in results if r is None)
        return {
            "total": total,
            "errors": errors,
            "error_rate": round(errors / total, 4) if total else 0.0,
        }

    @staticmethod
    def confidence_calibration(
        results: Sequence[Optional[Mapping[str, Any]]],
        ground_truth: Sequence[Optional[bool]],
    ) -> Dict[str, Any]:
        paired: List[Dict[str, float]] = []
        for r, label in zip(results, ground_truth):
            if r is not None and label is not None:
                prob = r.get("causal_probability", 0.5)
                paired.append({
                    "confidence": float(prob),
                    "correct": 1.0 if bool(r.get("decision", False)) == bool(label) else 0.0,
                    "expected": 1.0 if label else 0.0,
                })

        n = len(paired)
        if n == 0:
            return {"sample_size": 0, "mean_confidence": 0.0, "calibration_error": 0.0, "ece": 0.0}

        mean_conf = sum(p["confidence"] for p in paired) / n
        accuracy = sum(p["correct"] for p in paired) / n
        calibration_error = sum(abs(p["confidence"] - p["expected"]) for p in paired) / n

        buckets = [(0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.0)]
        ece = 0.0
        for lo, hi in buckets:
            in_bucket = [p for p in paired if lo <= p["confidence"] < hi]
            if in_bucket:
                bucket_conf = sum(p["confidence"] for p in in_bucket) / len(in_bucket)
                bucket_acc = sum(p["correct"] for p in in_bucket) / len(in_bucket)
                ece += (len(in_bucket) / n) * abs(bucket_conf - bucket_acc)

        return {
            "sample_size": n,
            "mean_confidence": round(mean_conf, 4),
            "accuracy": round(accuracy, 4),
            "calibration_error": round(calibration_error, 4),
            "ece": round(ece, 4),
        }

    @staticmethod
    def weakness_frequency(
        all_weaknesses: Sequence[Weakness],
        weakness_names: Sequence[str],
        total_weaknesses: int,
    ) -> List[Dict[str, Any]]:
        counts: Dict[str, int] = {}
        for name in weakness_names:
            counts[name] = sum(
                1 for w in all_weaknesses
                if w.category == "feature_instability" and w.feature == name
            )
        result: List[Dict[str, Any]] = []
        for name, count in sorted(counts.items()):
            pct = round(count / total_weaknesses * 100, 1) if total_weaknesses else 0.0
            result.append({
                "weakness": name,
                "frequency": count,
                "percent_of_total": pct,
                "sample_size": total_weaknesses,
            })
        return result

    @staticmethod
    def collapse_frequency(
        confidence_sequences: Sequence[Sequence[float]],
        drop_threshold: float = 0.20,
    ) -> Dict[str, Any]:
        detected = 0
        drops: List[float] = []
        for seq in confidence_sequences:
            result = CollapseDetector.detect(list(seq), drop_threshold)
            if result:
                detected += 1
                drops.append(result["drop_magnitude"])
        return {
            "total_sequences": len(confidence_sequences),
            "collapse_count": detected,
            "collapse_rate": round(detected / len(confidence_sequences), 4) if confidence_sequences else 0.0,
            "mean_drop_magnitude": round(sum(drops) / len(drops), 4) if drops else 0.0,
        }

    @staticmethod
    def difficulty_distribution(
        results: Sequence[Optional[Mapping[str, Any]]],
        difficulties: Sequence[float],
        ground_truth: Sequence[Optional[bool]],
    ) -> Dict[str, Any]:
        buckets = {
            "low_00_03": (0.0, 0.3),
            "mid_03_05": (0.3, 0.5),
            "mid_05_07": (0.5, 0.7),
            "high_07_10": (0.7, 1.0),
        }
        distribution: Dict[str, Dict[str, Any]] = {}
        for label, (lo, hi) in buckets.items():
            bucket_data: List[Dict[str, Any]] = []
            for r, d, gt in zip(results, difficulties, ground_truth):
                if r is not None and gt is not None and lo <= d < hi:
                    bucket_data.append({
                        "difficulty": d,
                        "predicted": r.get("decision", False),
                        "actual": gt,
                        "correct": r.get("decision", False) == bool(gt),
                        "confidence": r.get("causal_probability", 0.0),
                    })
            n = len(bucket_data)
            correct = sum(1 for b in bucket_data if b["correct"])
            distribution[label] = {
                "range": f"{lo}-{hi}",
                "count": n,
                "correct": correct,
                "accuracy": round(correct / n, 4) if n else 0.0,
                "mean_confidence": round(sum(b["confidence"] for b in bucket_data) / n, 4) if n else 0.0,
            }
        return distribution

    @staticmethod
    def capability_boundary_position(
        confidences: Sequence[float],
        difficulties: Sequence[float],
        confidence_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        paired = sorted(zip(difficulties, confidences), key=lambda x: x[0])
        crossings: List[Dict[str, Any]] = []
        for i in range(1, len(paired)):
            d_prev, c_prev = paired[i - 1]
            d_curr, c_curr = paired[i]
            if (c_prev >= confidence_threshold) != (c_curr >= confidence_threshold):
                cross_d = d_prev + (d_curr - d_prev) * (confidence_threshold - c_prev) / (c_curr - c_prev)
                crossings.append({
                    "difficulty": round(cross_d, 4),
                    "direction": "down" if c_prev >= confidence_threshold else "up",
                })
        region_below = sum(1 for d, c in paired if c < confidence_threshold)
        region_above = sum(1 for d, c in paired if c >= confidence_threshold)
        return {
            "confidence_threshold": confidence_threshold,
            "sample_size": len(paired),
            "crossings": crossings,
            "points_below_threshold": region_below,
            "points_above_threshold": region_above,
            "fraction_below": round(region_below / len(paired), 4) if paired else 0.0,
        }

    @staticmethod
    def compute_deltas(
        a_value: float,
        b_value: float,
        a_label: str = "A",
        b_label: str = "B",
        lower_is_better: bool = False,
    ) -> Dict[str, Any]:
        abs_diff = round(b_value - a_value, 4)
        pct_diff = round(((b_value - a_value) / a_value) * 100, 2) if a_value != 0 else 0.0
        if lower_is_better:
            direction = "improvement" if abs_diff < 0 else "regression" if abs_diff > 0 else "unchanged"
        else:
            direction = "improvement" if abs_diff > 0 else "regression" if abs_diff < 0 else "unchanged"
        return {
            a_label: a_value,
            b_label: b_value,
            "absolute_difference": abs_diff,
            "percentage_difference": pct_diff,
            "direction": direction,
        }
