from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from weakness_mapper.extractor import Weakness


class CapabilityBoundaryDetector:
    @staticmethod
    def detect(
        weaknesses: List[Weakness],
        sessions: Optional[List[Mapping[str, Any]]] = None,
    ) -> Dict[str, Any]:
        collapse_zones = []
        diff_thresholds = []
        recurring_failures = []

        for w in weaknesses:
            if w.category == "confidence_collapse":
                collapse_zones.append({
                    "feature": w.feature,
                    "confidence_range": w.confidence_range,
                    "difficulty_range": w.difficulty_range,
                    "reproducibility_count": w.reproducibility_count,
                    "trigger_conditions": w.trigger_conditions,
                })

            if w.category == "difficulty_threshold":
                diff_thresholds.append({
                    "feature": w.feature,
                    "difficulty_range": w.difficulty_range,
                    "confidence_range": w.confidence_range,
                    "trigger": w.trigger_conditions,
                })

            if w.category == "feature_instability" and w.reproducibility_count >= 2:
                recurring_failures.append({
                    "feature": w.feature,
                    "confidence_range": w.confidence_range,
                    "difficulty_range": w.difficulty_range,
                    "reproducibility_count": w.reproducibility_count,
                })

        high_confidence = [
            w.to_dict() for w in weaknesses
            if w.category == "feature_instability"
            and w.trigger_conditions.get("weakness_score", 1.0) > 0.5
        ]

        return {
            "confidence_collapse_zones": collapse_zones,
            "difficulty_thresholds": diff_thresholds,
            "recurring_failure_regions": recurring_failures,
            "high_confidence_features": high_confidence,
        }
