from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from weakness_mapper.extractor import Weakness
from weakness_mapper.registry import WeaknessRegistry
from weakness_mapper.boundaries import CapabilityBoundaryDetector


_REPRODUCIBLE_MIN = 2


class CapabilityReporter:
    def __init__(self, registry: WeaknessRegistry) -> None:
        self.registry = registry

    def generate(self, session_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        weaknesses = self.registry.get_all()
        boundaries = CapabilityBoundaryDetector.detect(weaknesses)

        weakest = self._sorted_by_reproducibility(
            [w for w in weaknesses if w.category in ("feature_instability", "confidence_collapse")],
        )

        strong_features = self._find_strong_features(weaknesses, session_data)
        strongest = [{"category": "stable_feature", "feature": f} for f in sorted(strong_features)]
        reproducible = [w.to_dict() for w in weaknesses if w.reproducibility_count >= _REPRODUCIBLE_MIN]
        collapse_regions = boundaries.get("confidence_collapse_zones", [])
        failure_regions = boundaries.get("recurring_failure_regions", [])

        return {
            "report_metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_weaknesses": len(weaknesses),
                "total_sessions_covered": self._count_sessions(weaknesses),
                "reproducible_count": len(reproducible),
            },
            "strongest_areas": strongest[:10],
            "weakest_areas": weakest[:10],
            "collapse_regions": collapse_regions,
            "reproducible_weaknesses": reproducible,
            "capability_boundaries": boundaries,
        }

    def save_json(self, path: str = "capability_report.json", session_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        report = self.generate(session_data)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        return report

    @staticmethod
    def _sorted_by_reproducibility(
        weaknesses: List[Weakness],
        reverse: bool = False,
    ) -> List[Dict[str, Any]]:
        sorted_w = sorted(weaknesses, key=lambda w: w.reproducibility_count, reverse=not reverse)
        return [w.to_dict() for w in sorted_w]

    @staticmethod
    def _find_strong_features(
        weaknesses: List[Weakness],
        session_data: Optional[List[Dict[str, Any]]],
    ) -> List[str]:
        weak_features: set = set()
        for w in weaknesses:
            if w.category == "feature_instability" and w.feature:
                weak_features.add(w.feature)

        if not session_data:
            return []

        all_features: set = set()
        for s in session_data:
            for c in s.get("challenges", []):
                all_features.update(c.get("features", {}).keys())

        strong = sorted(all_features - weak_features)
        return strong

    @staticmethod
    def _count_sessions(weaknesses: List[Weakness]) -> int:
        sids: set = set()
        for w in weaknesses:
            sids.update(w.session_ids)
        return len(sids)
