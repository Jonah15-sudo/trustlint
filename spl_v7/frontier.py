from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional

from .kafka_pipeline import EvidencePipeline
from .schema import EvidenceArtifact, EvidenceTransportMeta
from .utils import clamp, stable_hash
from .verification import compute_artifact_hash


_WORD_RE = re.compile(r"[A-Za-z0-9]+")


@dataclass(slots=True)
class FrontierChallenge:
    challenge_id: str
    step: int
    difficulty: float
    focus: list[str]
    artifact: EvidenceArtifact
    mutation_summary: Dict[str, Any] = field(default_factory=dict)
    frontier_report: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "step": self.step,
            "difficulty": self.difficulty,
            "focus": list(self.focus),
            "artifact": self.artifact.to_dict(),
            "mutation_summary": dict(self.mutation_summary),
            "frontier_report": dict(self.frontier_report),
        }


class FrontierExplorer:
    """Generates harder benchmark cases without changing the SPL core.

    The explorer operates as a sidecar layer:
      - SPL remains the decision engine.
      - OFE-style structural signals are wrapped as ordinary evidence.
      - The curriculum generator mutates evidence around weak frontier zones.
    """

    def __init__(self, pipeline: EvidencePipeline, signal_source: str = "ofe", max_focus: int = 3) -> None:
        self.pipeline = pipeline
        self.signal_source = signal_source
        self.max_focus = max(1, int(max_focus))

    @staticmethod
    def wrap_structural_signals(
        signals: Mapping[str, Any],
        *,
        source: str = "ofe",
        evidence_type: str = "structural_signal",
        tags: Optional[Iterable[str]] = None,
        label: Optional[bool] = None,
        transport_status: str = "ok",
    ) -> EvidenceArtifact:
        data: Dict[str, Any] = {"signals": dict(signals)}
        if label is not None:
            data["label"] = bool(label)
        artifact = EvidenceArtifact(
            source=source,
            type=evidence_type,
            data=data,
            transport_meta=EvidenceTransportMeta(status=transport_status),
            tags=list(tags or ("frontier", "ofe", "structural-signal")),
        )
        artifact.integrity.hash = compute_artifact_hash(artifact)
        return artifact

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {token.lower() for token in _WORD_RE.findall(text or "")}

    @staticmethod
    def _leaf_paths(value: Any, prefix: tuple[Any, ...] = ()) -> list[tuple[tuple[Any, ...], Any]]:
        leaves: list[tuple[tuple[Any, ...], Any]] = []
        if isinstance(value, Mapping):
            for key, item in value.items():
                leaves.extend(FrontierExplorer._leaf_paths(item, prefix + (key,)))
            return leaves
        if isinstance(value, list):
            for index, item in enumerate(value):
                leaves.extend(FrontierExplorer._leaf_paths(item, prefix + (index,)))
            return leaves
        return [(prefix, value)]

    @staticmethod
    def _set_path(container: Any, path: tuple[Any, ...], new_value: Any) -> None:
        current = container
        for segment in path[:-1]:
            current = current[segment]
        current[path[-1]] = new_value

    @staticmethod
    def _path_text(path: tuple[Any, ...]) -> str:
        return ".".join(str(segment) for segment in path)

    @staticmethod
    def _path_score(path: tuple[Any, ...], value: Any, focus_tokens: set[str]) -> float:
        key_tokens = FrontierExplorer._tokenize(FrontierExplorer._path_text(path))
        leaf_tokens = FrontierExplorer._tokenize(str(path[-1]) if path else "")
        tokens = key_tokens | leaf_tokens
        score = 0.0
        if focus_tokens:
            overlap = len(tokens & focus_tokens)
            score += overlap * 2.5
            if overlap:
                score += 1.0
        if isinstance(value, bool):
            score += 1.8
        elif isinstance(value, (int, float)):
            score += 1.5
        elif isinstance(value, str):
            score += 0.8
        elif isinstance(value, Mapping) or isinstance(value, list):
            score += 0.1
        return score

    @staticmethod
    def _mutate_scalar(key: str, value: Any, intensity: float, focus_hit: bool) -> tuple[Any, str]:
        intensity = clamp(intensity)
        key_tokens = FrontierExplorer._tokenize(key)
        if isinstance(value, bool):
            should_flip = focus_hit or intensity >= 0.5
            return (not value if should_flip else value), ("flipped_bool" if should_flip else "preserved_bool")

        if isinstance(value, int) and not isinstance(value, bool):
            magnitude = max(1, int(round(max(abs(value), 1) * (0.20 + 0.55 * intensity))))
            if key_tokens & {"count", "age", "days", "expiry", "risk", "score", "threshold", "latency"}:
                delta = -magnitude if value >= 0 else magnitude
            else:
                delta = magnitude if value >= 0 else -magnitude
            return value + delta, f"int_adjusted_{delta:+d}"

        if isinstance(value, float):
            if 0.0 <= value <= 1.0:
                shifted = value + (0.5 - value) * (0.35 + 0.65 * intensity)
                return clamp(shifted), "normalized_toward_midpoint"
            direction = -1.0 if value >= 0.0 else 1.0
            scale = max(abs(value), 1.0)
            delta = direction * scale * (0.12 + 0.28 * intensity)
            return value + delta, f"float_adjusted_{delta:+.3f}"

        if isinstance(value, str):
            if not value:
                return value, "empty_string"
            if focus_hit or intensity >= 0.7:
                return f"borderline::{value}", "string_borderline"
            return value, "preserved_string"

        return value, f"preserved_{type(value).__name__}"

    def analyze_frontier(self) -> Dict[str, Any]:
        snapshot = self.pipeline.causal_graph.snapshot()
        weights = snapshot.get("weights", {})
        edges = snapshot.get("edges", [])

        ranked_features: list[Dict[str, Any]] = []
        for name, meta in weights.items():
            stability = float(meta.get("weighted_stability", 0.0))
            corroboration = float(meta.get("cross_source_corroboration", 0.0))
            independence = float(meta.get("independence", 0.0))
            intervention = clamp(abs(float(meta.get("intervention_effect", 0.0))))
            reliability = clamp(0.35 * stability + 0.25 * corroboration + 0.20 * independence + 0.20 * (1.0 - intervention))
            weakness = clamp(1.0 - reliability)
            ranked_features.append(
                {
                    "feature": name,
                    "reliability": reliability,
                    "weakness": weakness,
                    "stability": stability,
                    "corroboration": corroboration,
                    "independence": independence,
                    "intervention_effect": intervention,
                    "redundancy_partner": meta.get("redundancy_partner"),
                }
            )
        ranked_features.sort(key=lambda item: (item["weakness"], item["reliability"]), reverse=True)

        ranked_edges = sorted(edges, key=lambda edge: float(edge.get("confidence", 0.0)))
        frontier_pressure = 0.0
        if ranked_features:
            frontier_pressure = sum(item["weakness"] for item in ranked_features[: min(3, len(ranked_features))]) / min(3, len(ranked_features))
        if ranked_edges:
            edge_pressure = 1.0 - float(ranked_edges[0].get("confidence", 0.0))
            frontier_pressure = clamp(0.7 * frontier_pressure + 0.3 * edge_pressure)

        return {
            "frontier_pressure": frontier_pressure,
            "weakest_features": ranked_features[: self.max_focus],
            "weakest_edges": ranked_edges[: self.max_focus],
            "snapshot": snapshot,
        }

    def _mutate_data(self, data: Mapping[str, Any], focus_features: list[str], intensity: float) -> tuple[Dict[str, Any], Dict[str, Any]]:
        mutated = copy.deepcopy(dict(data))
        leaves = self._leaf_paths(mutated)
        focus_tokens = set()
        for feature in focus_features:
            focus_tokens |= self._tokenize(feature)

        ranked = []
        for path, value in leaves:
            path_text = self._path_text(path)
            if path_text.endswith("label") or path_text.endswith("target"):
                continue
            ranked.append((self._path_score(path, value, focus_tokens), path, value))
        ranked.sort(key=lambda item: (item[0], self._path_text(item[1])), reverse=True)

        changed_paths: list[str] = []
        mutations: list[Dict[str, Any]] = []
        max_mutations = min(max(1, len(ranked)), max(1, min(3, len(ranked))))
        for score, path, value in ranked[:max_mutations]:
            key = self._path_text(path)
            focus_hit = bool(self._tokenize(key) & focus_tokens)
            new_value, mutation_kind = self._mutate_scalar(key, value, intensity, focus_hit)
            if new_value != value:
                self._set_path(mutated, path, new_value)
                changed_paths.append(key)
                mutations.append(
                    {
                        "path": key,
                        "before": value,
                        "after": new_value,
                        "kind": mutation_kind,
                        "score": score,
                    }
                )

        if not changed_paths and ranked:
            _, path, value = ranked[0]
            key = self._path_text(path)
            new_value, mutation_kind = self._mutate_scalar(key, value, max(intensity, 0.5), True)
            self._set_path(mutated, path, new_value)
            changed_paths.append(key)
            mutations.append(
                {
                    "path": key,
                    "before": value,
                    "after": new_value,
                    "kind": mutation_kind,
                    "score": ranked[0][0],
                }
            )

        return mutated, {
            "focus_features": focus_features,
            "focus_tokens": sorted(focus_tokens),
            "changed_paths": changed_paths,
            "mutations": mutations,
            "mutation_count": len(changed_paths),
        }

    def generate_curriculum(self, seed_artifact: EvidenceArtifact, steps: int = 3) -> list[FrontierChallenge]:
        if steps <= 0:
            return []

        baseline = EvidenceArtifact.from_dict(seed_artifact.to_dict())
        frontier_report = self.analyze_frontier()
        focus_features = [item["feature"] for item in frontier_report["weakest_features"]] or ["frontier_pressure"]

        curriculum: list[FrontierChallenge] = []
        current = baseline
        for step in range(1, steps + 1):
            intensity = clamp(0.28 + 0.18 * step + frontier_report["frontier_pressure"] * 0.15)
            mutated_data, summary = self._mutate_data(current.data, focus_features, intensity)
            challenge = EvidenceArtifact(
                source=current.source,
                type=current.type,
                data=mutated_data,
                transport_meta=EvidenceTransportMeta.from_dict(current.transport_meta.to_dict()),
                tags=list(dict.fromkeys([*current.tags, "frontier", "challenge"])),
            )
            challenge.integrity.hash = compute_artifact_hash(challenge)
            challenge_id = stable_hash(current.evidence_id, str(step), ",".join(focus_features), str(intensity))[:16]
            curriculum.append(
                FrontierChallenge(
                    challenge_id=challenge_id,
                    step=step,
                    difficulty=intensity,
                    focus=focus_features,
                    artifact=challenge,
                    mutation_summary=summary,
                    frontier_report={
                        "frontier_pressure": frontier_report["frontier_pressure"],
                        "weakest_features": frontier_report["weakest_features"],
                    },
                )
            )
            current = challenge
        return curriculum

    def evaluate_and_generate(self, seed_artifact: EvidenceArtifact, steps: int = 3) -> Dict[str, Any]:
        curriculum = self.generate_curriculum(seed_artifact, steps=steps)
        return {
            "frontier": self.analyze_frontier(),
            "curriculum": [challenge.to_dict() for challenge in curriculum],
        }
