from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from spl_v7.utils import clamp


def compute_difficulty(
    mutation_summary: Mapping[str, Any],
    step: int,
    max_steps: int,
    frontier_pressure: float = 0.0,
) -> float:
    mutations: List[Dict[str, Any]] = list(mutation_summary.get("mutations", []))
    total = len(mutations)
    if total == 0:
        return clamp(step / max(max_steps, 1))

    contradiction_count = 0
    ambiguity_count = 0
    for m in mutations:
        kind = str(m.get("kind", ""))
        before = m.get("before")
        after = m.get("after")
        if kind == "flipped_bool":
            contradiction_count += 1
        elif kind == "normalized_toward_midpoint" and isinstance(before, (int, float)) and isinstance(after, (int, float)):
            ambiguity_count += 1

    contradiction_complexity = clamp(contradiction_count / total)
    ambiguity = clamp(ambiguity_count / total)
    evidence_density = clamp(mutation_summary.get("mutation_count", 0) / max(total, 1))
    step_progression = clamp(step / max(max_steps, 1))

    return clamp(
        0.30 * contradiction_complexity
        + 0.20 * evidence_density
        + 0.15 * ambiguity
        + 0.20 * step_progression
        + 0.15 * clamp(frontier_pressure)
    )


class CollapseDetector:
    @staticmethod
    def detect(
        confidences: List[float],
        drop_threshold: float = 0.20,
    ) -> Optional[Dict[str, Any]]:
        if len(confidences) < 3:
            return None

        best = max(confidences)
        best_idx = confidences.index(best)
        best_remaining = confidences[best_idx + 1:]
        if not best_remaining:
            return None

        min_after = min(best_remaining)
        drop = best - min_after
        if drop < drop_threshold:
            return None

        collapse_start = best_idx + 1
        collapse_end = best_idx + 1 + best_remaining.index(min_after)

        return {
            "detected": True,
            "drop_magnitude": round(drop, 4),
            "drop_threshold": drop_threshold,
            "peak_confidence": round(best, 4),
            "peak_step": best_idx,
            "nadir_confidence": round(min_after, 4),
            "nadir_step": collapse_end,
            "collapse_start_step": collapse_start,
            "collapse_end_step": collapse_end,
            "collapsed": bool(drop >= drop_threshold),
        }
