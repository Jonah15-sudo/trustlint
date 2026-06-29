from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

WEAKNESS_TYPES = frozenset({
    "confidence_collapse",
    "feature_instability",
    "decision_oscillation",
    "difficulty_threshold",
    "low_confidence_region",
})

LOW_CONFIDENCE_CUTOFF = 0.30
DECISION_OSCILLATION_MIN_FLIPS = 2


def _weakness_id(category: str, feature: str, trigger: str) -> str:
    raw = f"{category}::{feature}::{trigger}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class Weakness:
    __slots__ = (
        "weakness_id", "category", "feature", "trigger_conditions",
        "confidence_range", "difficulty_range", "reproducibility_count",
        "first_seen", "last_seen", "session_ids",
    )

    def __init__(
        self,
        category: str,
        feature: str = "",
        trigger_conditions: Optional[Mapping[str, Any]] = None,
        confidence_range: Optional[List[float]] = None,
        difficulty_range: Optional[List[float]] = None,
        session_id: str = "",
    ) -> None:
        trigger_str = json.dumps(dict(trigger_conditions or {}), sort_keys=True)
        self.weakness_id = _weakness_id(category, feature, trigger_str)
        self.category = category
        self.feature = feature
        self.trigger_conditions = dict(trigger_conditions or {})
        self.confidence_range = list(confidence_range or [0.0, 0.0])
        self.difficulty_range = list(difficulty_range or [0.0, 0.0])
        self.reproducibility_count = 1
        now = _timestamp()
        self.first_seen = now
        self.last_seen = now
        self.session_ids = [session_id] if session_id else []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "weakness_id": self.weakness_id,
            "category": self.category,
            "feature": self.feature,
            "trigger_conditions": self.trigger_conditions,
            "confidence_range": self.confidence_range,
            "difficulty_range": self.difficulty_range,
            "reproducibility_count": self.reproducibility_count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "session_ids": self.session_ids,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Weakness":
        w = cls(
            category=d.get("category", ""),
            feature=d.get("feature", ""),
            trigger_conditions=d.get("trigger_conditions", {}),
            confidence_range=d.get("confidence_range", [0.0, 0.0]),
            difficulty_range=d.get("difficulty_range", [0.0, 0.0]),
        )
        w.weakness_id = d.get("weakness_id", w.weakness_id)
        w.reproducibility_count = d.get("reproducibility_count", 1)
        w.first_seen = d.get("first_seen", w.first_seen)
        w.last_seen = d.get("last_seen", w.last_seen)
        w.session_ids = list(d.get("session_ids", []))
        return w


class WeaknessExtractor:
    @staticmethod
    def extract(
        session_data: Mapping[str, Any],
        report_data: Mapping[str, Any],
    ) -> List[Weakness]:
        weaknesses: List[Weakness] = []
        session_id = session_data.get("session_id", "")
        challenges = list(session_data.get("challenges", []))
        confidences = [c.get("predicted_probability", 0.0) for c in challenges]
        difficulties = [c.get("difficulty", 0.0) for c in challenges]

        collapse = report_data.get("collapse_detection")
        if collapse and collapse.get("detected"):
            weaknesses.append(Weakness(
                category="confidence_collapse",
                trigger_conditions={
                    "drop_magnitude": collapse["drop_magnitude"],
                    "peak_step": collapse["peak_step"],
                    "nadir_step": collapse["nadir_step"],
                },
                confidence_range=[
                    collapse["nadir_confidence"],
                    collapse["peak_confidence"],
                ],
                difficulty_range=[
                    difficulties[collapse["nadir_step"]]
                    if collapse["nadir_step"] < len(difficulties) else 0.0,
                    difficulties[collapse["peak_step"]]
                    if collapse["peak_step"] < len(difficulties) else 0.0,
                ],
                session_id=session_id,
            ))

        for w in report_data.get("discovered_weaknesses", []):
            feat = w.get("feature", "")
            weakness_val = w.get("weakness", 0.0)
            reliability = w.get("reliability", 1.0)
            if reliability < 0.75:
                weaknesses.append(Weakness(
                    category="feature_instability",
                    feature=feat,
                    trigger_conditions={"weakness_score": weakness_val, "reliability": reliability},
                    confidence_range=[min(confidences), max(confidences)] if confidences else [0, 0],
                    difficulty_range=[min(difficulties), max(difficulties)] if difficulties else [0, 0],
                    session_id=session_id,
                ))

        decisions = [c.get("decision", False) for c in challenges if "decision" in c]
        flips = sum(1 for i in range(1, len(decisions)) if decisions[i] != decisions[i - 1])
        if flips >= DECISION_OSCILLATION_MIN_FLIPS:
            weaknesses.append(Weakness(
                category="decision_oscillation",
                trigger_conditions={"flip_count": flips, "total_decisions": len(decisions)},
                confidence_range=[min(confidences), max(confidences)] if confidences else [0, 0],
                difficulty_range=[min(difficulties), max(difficulties)] if difficulties else [0, 0],
                session_id=session_id,
            ))

        for i, (c, d) in enumerate(zip(confidences, difficulties)):
            if c < LOW_CONFIDENCE_CUTOFF:
                weaknesses.append(Weakness(
                    category="low_confidence_region",
                    trigger_conditions={"step": i, "confidence": round(c, 4)},
                    confidence_range=[c, c],
                    difficulty_range=[d, d],
                    session_id=session_id,
                ))

        for i in range(1, len(confidences)):
            drop = confidences[i - 1] - confidences[i]
            if drop > 0.15 and 0.0 < difficulties[i] <= 0.7:
                weaknesses.append(Weakness(
                    category="difficulty_threshold",
                    trigger_conditions={
                        "step": i,
                        "confidence_drop": round(drop, 4),
                        "from_difficulty": round(difficulties[i - 1], 4),
                        "to_difficulty": round(difficulties[i], 4),
                    },
                    confidence_range=[confidences[i], confidences[i - 1]],
                    difficulty_range=[difficulties[i - 1], difficulties[i]],
                    session_id=session_id,
                ))

        return weaknesses
