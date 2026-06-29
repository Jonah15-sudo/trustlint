from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Mapping, Optional

from weakness_mapper.extractor import Weakness

RANGES_OVERLAP_THRESHOLD = 0.3


def _ranges_overlap(a: List[float], b: List[float], threshold: float = RANGES_OVERLAP_THRESHOLD) -> bool:
    if not a or not b:
        return False
    a_lo, a_hi = min(a), max(a)
    b_lo, b_hi = min(b), max(b)
    span = max(a_hi, b_hi) - min(a_lo, b_lo)
    if span == 0.0:
        return True
    overlap = max(0.0, min(a_hi, b_hi) - max(a_lo, b_lo))
    return (overlap / span) >= threshold


class WeaknessRegistry:
    def __init__(self, path: str = "weakness_registry.json") -> None:
        self.path = path
        self._weaknesses: Dict[str, Weakness] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.isfile(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry in data.get("weaknesses", []):
                w = Weakness.from_dict(entry)
                self._weaknesses[w.weakness_id] = w
        except (json.JSONDecodeError, IOError):
            self._weaknesses = {}

    def save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                {"weaknesses": [w.to_dict() for w in self._weaknesses.values()]},
                f,
                indent=2,
                ensure_ascii=False,
            )

    def search(
        self,
        category: str,
        feature: str,
        confidence_range: List[float],
        difficulty_range: List[float],
    ) -> Optional[Weakness]:
        for w in self._weaknesses.values():
            if w.category != category:
                continue
            if w.feature != feature:
                continue
            if not _ranges_overlap(w.confidence_range, confidence_range):
                continue
            if not _ranges_overlap(w.difficulty_range, difficulty_range):
                continue
            return w
        return None

    def add(self, weakness: Weakness) -> None:
        existing = self._weaknesses.get(weakness.weakness_id)
        if existing:
            existing.reproducibility_count += 1
            existing.last_seen = weakness.last_seen
            merged = list(set(existing.session_ids + weakness.session_ids))
            existing.session_ids = merged
            existing.confidence_range = [
                min(existing.confidence_range[0], weakness.confidence_range[0]),
                max(existing.confidence_range[1], weakness.confidence_range[1]),
            ]
            existing.difficulty_range = [
                min(existing.difficulty_range[0], weakness.difficulty_range[0]),
                max(existing.difficulty_range[1], weakness.difficulty_range[1]),
            ]
            return
        self._weaknesses[weakness.weakness_id] = weakness

    def add_weaknesses(self, weaknesses: List[Weakness], session_id: str) -> int:
        added = 0
        for w in weaknesses:
            existing = self.search(w.category, w.feature, w.confidence_range, w.difficulty_range)
            if existing:
                existing.reproducibility_count += 1
                existing.last_seen = w.last_seen
                if session_id not in existing.session_ids:
                    existing.session_ids.append(session_id)
                existing.confidence_range[0] = min(existing.confidence_range[0], w.confidence_range[0])
                existing.confidence_range[1] = max(existing.confidence_range[1], w.confidence_range[1])
                existing.difficulty_range[0] = min(existing.difficulty_range[0], w.difficulty_range[0])
                existing.difficulty_range[1] = max(existing.difficulty_range[1], w.difficulty_range[1])
            else:
                self._weaknesses[w.weakness_id] = w
                added += 1
        self.save()
        return added

    def get_all(self) -> List[Weakness]:
        return list(self._weaknesses.values())

    def get_by_category(self, category: str) -> List[Weakness]:
        return [w for w in self._weaknesses.values() if w.category == category]

    def clear(self) -> None:
        self._weaknesses.clear()
        self.save()
