from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional

from frontier.metrics import CollapseDetector


class ExplorationReport:
    def __init__(self, session: Any) -> None:
        self.session = session

    def generate(self, frontier_report: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        confidences = self.session.confidence_progression
        difficulties = self.session.difficulty_progression
        total = len(self.session.challenges)

        collapse = CollapseDetector.detect(confidences)

        weaknesses: List[Dict[str, Any]] = []
        if frontier_report:
            weaknesses = [
                {"feature": f.get("feature", ""), "weakness": f.get("weakness", 0.0), "reliability": f.get("reliability", 0.0)}
                for f in frontier_report.get("weakest_features", [])
            ]

        avg_difficulty = 0.0
        if difficulties:
            avg_difficulty = sum(difficulties) / len(difficulties)

        return {
            "session_id": self.session.session_id,
            "created_at": self.session.created_at,
            "total_challenges": total,
            "max_depth": total,
            "average_difficulty": round(avg_difficulty, 4),
            "difficulty_progression": [round(d, 4) for d in difficulties],
            "confidence_progression": [round(c, 4) for c in confidences],
            "confidence_min": round(min(confidences), 4) if confidences else 0.0,
            "confidence_max": round(max(confidences), 4) if confidences else 0.0,
            "confidence_drop": round(confidences[0] - confidences[-1], 4) if len(confidences) >= 2 else 0.0,
            "collapse_detection": collapse,
            "discovered_weaknesses": weaknesses,
        }

    def save_json(self, path: str, frontier_report: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        report = self.generate(frontier_report)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        return report
