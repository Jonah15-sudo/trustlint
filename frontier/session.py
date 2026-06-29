from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from spl_v7.utils import clamp, stable_hash
from spl_v7.schema import EvidenceArtifact

from frontier.metrics import compute_difficulty, CollapseDetector
from frontier.reports import ExplorationReport


class ExplorationSession:
    def __init__(self, seed_artifact: EvidenceArtifact) -> None:
        self.session_id: str = stable_hash(seed_artifact.evidence_id, datetime.now(timezone.utc).isoformat())[:16]
        self.seed_artifact: Dict[str, Any] = seed_artifact.to_dict()
        self.created_at: str = datetime.now(timezone.utc).isoformat()
        self.challenges: List[Dict[str, Any]] = []

    def add_challenge(self, challenge: Any, result: Optional[Mapping[str, Any]] = None) -> None:
        record: Dict[str, Any] = {
            "step": int(getattr(challenge, "step", 0)),
            "challenge_id": str(getattr(challenge, "challenge_id", "")),
            "difficulty": float(getattr(challenge, "difficulty", 0.0)),
            "focus": list(getattr(challenge, "focus", [])),
            "mutation_summary": dict(getattr(challenge, "mutation_summary", {})),
        }
        if result is not None:
            record["predicted_probability"] = float(result.get("causal_probability", result.get("predicted_probability", 0.0)))
            record["decision"] = bool(result.get("decision", False))
            record["features"] = dict(result.get("features", {}))
            if result.get("train_result"):
                record["loss"] = float(result["train_result"].get("loss", 0.0))
        self.challenges.append(record)

    @property
    def confidence_progression(self) -> List[float]:
        return [c.get("predicted_probability", 0.0) for c in self.challenges]

    @property
    def difficulty_progression(self) -> List[float]:
        return [c.get("difficulty", 0.0) for c in self.challenges]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "seed_artifact": self.seed_artifact,
            "challenges": list(self.challenges),
        }

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "ExplorationSession":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        seed = EvidenceArtifact.from_dict(data.get("seed_artifact", {}))
        session = cls(seed)
        session.session_id = data.get("session_id", session.session_id)
        session.created_at = data.get("created_at", session.created_at)
        session.challenges = list(data.get("challenges", []))
        return session



