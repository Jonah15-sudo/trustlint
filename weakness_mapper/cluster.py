from __future__ import annotations

from typing import Any, Dict, List

from weakness_mapper.extractor import Weakness


class WeaknessCluster:
    __slots__ = ("cluster_id", "category", "feature", "weakness_ids",
                 "confidence_range", "difficulty_range", "reproducibility_count",
                 "session_ids")

    def __init__(self, cluster_id: str, weaknesses: List[Weakness]) -> None:
        self.cluster_id = cluster_id
        self.category = weaknesses[0].category if weaknesses else ""
        self.feature = weaknesses[0].feature if weaknesses else ""
        self.weakness_ids = [w.weakness_id for w in weaknesses]
        all_conf = [v for w in weaknesses for v in w.confidence_range if v is not None]
        all_diff = [v for w in weaknesses for v in w.difficulty_range if v is not None]
        self.confidence_range = [min(all_conf), max(all_conf)] if all_conf else [0.0, 0.0]
        self.difficulty_range = [min(all_diff), max(all_diff)] if all_diff else [0.0, 0.0]
        self.reproducibility_count = sum(w.reproducibility_count for w in weaknesses)
        sids: set = set()
        for w in weaknesses:
            sids.update(w.session_ids)
        self.session_ids = sorted(sids)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "category": self.category,
            "feature": self.feature,
            "weakness_ids": self.weakness_ids,
            "confidence_range": self.confidence_range,
            "difficulty_range": self.difficulty_range,
            "reproducibility_count": self.reproducibility_count,
            "session_ids": self.session_ids,
        }


class WeaknessClusterer:
    @staticmethod
    def cluster(weaknesses: List[Weakness]) -> List[WeaknessCluster]:
        if not weaknesses:
            return []

        grouped: Dict[str, List[Weakness]] = {}
        for w in weaknesses:
            key = f"{w.category}::{w.feature}"
            grouped.setdefault(key, []).append(w)

        clusters: List[WeaknessCluster] = []
        for idx, (key, group) in enumerate(sorted(grouped.items())):
            cluster = WeaknessCluster(cluster_id=f"cluster_{idx:04d}", weaknesses=group)
            clusters.append(cluster)

        return clusters
