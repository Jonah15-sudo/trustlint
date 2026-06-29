from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from math import exp, sqrt
from typing import Any, Deque, Dict, Mapping, Optional, Sequence, Tuple

from .utils import clamp, safe_div, sigmoid


@dataclass(slots=True)
class CausalEdge:
    source: str
    target: str
    lag: int
    weight: float
    support: float
    confidence: float
    kind: str = "feature_to_decision"
    independence: float = 1.0
    weighted_stability: float = 1.0
    cross_source_corroboration: float = 0.0
    intervention_effect: float = 0.0
    redundancy_partner: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "lag": self.lag,
            "weight": self.weight,
            "support": self.support,
            "confidence": self.confidence,
            "kind": self.kind,
            "independence": self.independence,
            "weighted_stability": self.weighted_stability,
            "cross_source_corroboration": self.cross_source_corroboration,
            "intervention_effect": self.intervention_effect,
            "redundancy_partner": self.redundancy_partner,
        }


@dataclass(slots=True)
class OnlineStats:
    """Weighted online statistics for a feature against the target."""

    count: int = 0
    total_weight: float = 0.0
    mean: float = 0.0
    m2: float = 0.0
    cov: float = 0.0
    target_mean: float = 0.0
    target_m2: float = 0.0
    min_value: float = float("inf")
    max_value: float = float("-inf")

    def update(self, x: float, y: float, sample_weight: float = 1.0) -> None:
        weight = max(float(sample_weight), 0.0)
        if weight <= 0.0:
            return

        self.count += 1
        x_value = float(x)
        self.min_value = min(self.min_value, x_value)
        self.max_value = max(self.max_value, x_value)
        old_total = self.total_weight
        self.total_weight += weight
        ratio = weight / max(self.total_weight, 1e-12)

        dx = x_value - self.mean
        self.mean += ratio * dx
        dy = float(y) - self.target_mean
        self.target_mean += ratio * dy

        # Weighted Welford update.  This makes high-trust labels influence
        # variance/covariance more than weak or synthetic labels.
        self.m2 += weight * dx * (x_value - self.mean)
        self.target_m2 += weight * dy * (float(y) - self.target_mean)
        self.cov += weight * dx * (float(y) - self.target_mean)

    @property
    def effective_support(self) -> float:
        return self.total_weight

    @property
    def variance(self) -> float:
        if self.total_weight <= 1e-12:
            return 0.0
        return max(self.m2 / self.total_weight, 0.0)

    @property
    def target_variance(self) -> float:
        if self.total_weight <= 1e-12:
            return 0.0
        return max(self.target_m2 / self.total_weight, 0.0)

    @property
    def covariance(self) -> float:
        if self.total_weight <= 1e-12:
            return 0.0
        return self.cov / self.total_weight

    @property
    def correlation(self) -> float:
        denom = (self.variance * self.target_variance) ** 0.5
        return clamp(safe_div(self.covariance, denom, default=0.0), -1.0, 1.0)


@dataclass(slots=True)
class OnlinePairStats:
    """Weighted online statistics for feature-vs-feature independence tests."""

    count: int = 0
    total_weight: float = 0.0
    mean_x: float = 0.0
    mean_y: float = 0.0
    m2_x: float = 0.0
    m2_y: float = 0.0
    cov: float = 0.0
    mean_abs_delta: float = 0.0

    def update(self, x: float, y: float, sample_weight: float = 1.0) -> None:
        weight = max(float(sample_weight), 0.0)
        if weight <= 0.0:
            return

        self.count += 1
        self.total_weight += weight
        ratio = weight / max(self.total_weight, 1e-12)

        dx = float(x) - self.mean_x
        self.mean_x += ratio * dx
        dy = float(y) - self.mean_y
        self.mean_y += ratio * dy

        self.m2_x += weight * dx * (float(x) - self.mean_x)
        self.m2_y += weight * dy * (float(y) - self.mean_y)
        self.cov += weight * dx * (float(y) - self.mean_y)

        delta = abs(float(x) - float(y))
        self.mean_abs_delta += ratio * (delta - self.mean_abs_delta)

    @property
    def variance_x(self) -> float:
        if self.total_weight <= 1e-12:
            return 0.0
        return max(self.m2_x / self.total_weight, 0.0)

    @property
    def variance_y(self) -> float:
        if self.total_weight <= 1e-12:
            return 0.0
        return max(self.m2_y / self.total_weight, 0.0)

    @property
    def covariance(self) -> float:
        if self.total_weight <= 1e-12:
            return 0.0
        return self.cov / self.total_weight

    @property
    def correlation(self) -> float:
        denom = (self.variance_x * self.variance_y) ** 0.5
        return clamp(safe_div(self.covariance, denom, default=0.0), -1.0, 1.0)

    def redundancy_score(self, min_support: float = 5.0) -> float:
        if self.total_weight < min_support:
            return 0.0

        # Perfect duplicated constants have undefined correlation but are still
        # non-independent. Catch them explicitly through the equality channel.
        identical_constant = (
            self.variance_x < 1e-12
            and self.variance_y < 1e-12
            and self.mean_abs_delta < 1e-9
        )
        if identical_constant:
            return 1.0

        equality_redundancy = clamp(1.0 - self.mean_abs_delta)
        corr_redundancy = abs(self.correlation)
        return clamp(max(corr_redundancy, equality_redundancy * corr_redundancy))


@dataclass(slots=True)
class LabeledObservation:
    """One supervised event retained for temporal stability and conditional tests."""

    features: Dict[str, float]
    target: float
    sample_weight: float
    source_id: str
    verification_score: float
    provenance_hash: Optional[str]
    predicted_probability: float
    loss: float


@dataclass(slots=True)
class SourceQualityStats:
    """Aggregates provenance quality for a source without storing raw evidence."""

    count: int = 0
    total_weight: float = 0.0
    verification_total: float = 0.0
    registered_count: int = 0
    digest_valid_count: int = 0
    signature_valid_count: int = 0
    transport_ok_count: int = 0
    distinct_hashes: set[str] = field(default_factory=set)

    def update(self, report: Optional[Mapping[str, Any]], sample_weight: float, provenance_hash: Optional[str]) -> None:
        weight = max(float(sample_weight), 0.0)
        self.count += 1
        self.total_weight += weight
        if provenance_hash:
            self.distinct_hashes.add(str(provenance_hash))
        if not report:
            self.verification_total += 1.0 * weight
            self.registered_count += 1
            self.transport_ok_count += 1
            return
        score = float(report.get("score", report.get("verification_score", 0.0)))
        self.verification_total += clamp(score) * weight
        if bool(report.get("source_registered", False)):
            self.registered_count += 1
        if bool(report.get("digest_valid", False)):
            self.digest_valid_count += 1
        if bool(report.get("signature_valid", False)):
            self.signature_valid_count += 1
        if bool(report.get("transport_ok", False)):
            self.transport_ok_count += 1

    def report(self, source_id: str) -> Dict[str, Any]:
        denom = max(self.count, 1)
        weighted_denom = max(self.total_weight, 1e-12)
        return {
            "source": source_id,
            "events": self.count,
            "weighted_support": self.total_weight,
            "avg_verification_score": self.verification_total / weighted_denom,
            "registered_rate": self.registered_count / denom,
            "digest_valid_rate": self.digest_valid_count / denom,
            "signature_valid_rate": self.signature_valid_count / denom,
            "transport_ok_rate": self.transport_ok_count / denom,
            "distinct_provenance_hashes": len(self.distinct_hashes),
        }


class OnlineCausalGraphLearner:
    """
    A learned causal graph backed by online ML.

    v7 hardening added here:
      1. Independence test: feature edges are penalized when a feature is
         redundant with another feature/evidence channel.
      2. Weighted stability: sample_weight now affects support, variance, edge
         stability, and final confidence instead of only scaling the gradient.
      3. Cross-source corroboration: single-source evidence is useful but
         cannot receive full production trust until independent sources agree.
      4. Intervention approximation: counterfactual feature clamps estimate
         whether a learned edge has operational effect, not just correlation.

    Equations:
        p(y=1 | x_t, x_{t-1}) = sigmoid(b + w·x_t + u·x_{t-1})
        Δw_i = η (y - p) x_i - λ w_i
        Δu_i = η (y - p) x_{t-1,i} - λ u_i
    """

    def __init__(
        self,
        target_name: str = "decision",
        learning_rate: float = 0.08,
        l2: float = 0.0015,
        lag: int = 1,
        decision_threshold: float = 0.5,
        history_size: int = 128,
        independence_min_support: float = 5.0,
        redundancy_threshold: float = 0.85,
        source_min_support: float = 2.0,
        min_corroborating_sources: int = 2,
        stability_window: int = 32,
        drift_threshold: float = 0.35,
    ) -> None:
        self.target_name = target_name
        self.learning_rate = float(learning_rate)
        self.l2 = float(l2)
        self.lag = int(max(lag, 0))
        self.decision_threshold = float(decision_threshold)
        self.independence_min_support = float(independence_min_support)
        self.redundancy_threshold = float(redundancy_threshold)
        self.source_min_support = float(source_min_support)
        self.min_corroborating_sources = int(max(1, min_corroborating_sources))
        self.stability_window = int(max(8, stability_window))
        self.drift_threshold = float(clamp(drift_threshold, 0.05, 1.0))
        self.feature_names: list[str] = []
        self.current_weights: Dict[str, float] = {}
        self.lag_weights: Dict[str, float] = {}
        self.feature_stats: Dict[str, OnlineStats] = {}
        self.pair_stats: Dict[Tuple[str, str], OnlinePairStats] = {}
        self.source_feature_stats: Dict[str, Dict[str, OnlineStats]] = {}
        self.bias = 0.0
        self.sample_count = 0
        self.total_weight = 0.0
        self.total_loss = 0.0
        self.correct_count = 0
        self.weighted_correct = 0.0
        self.source_quality: Dict[str, SourceQualityStats] = {}
        self._history: Deque[Dict[str, float]] = deque(maxlen=history_size)
        self._labeled_history: Deque[LabeledObservation] = deque(maxlen=history_size)

    def _ensure_feature(self, name: str) -> None:
        if name not in self.feature_names:
            self.feature_names.append(name)
            self.current_weights[name] = 0.0
            self.lag_weights[name] = 0.0
            self.feature_stats[name] = OnlineStats()
            self.source_feature_stats[name] = {}

    def _vectorize(self, features: Mapping[str, Any]) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for name, value in features.items():
            self._ensure_feature(name)
            if isinstance(value, bool):
                out[name] = 1.0 if value else 0.0
            else:
                try:
                    out[name] = float(value)
                except Exception:
                    out[name] = 0.0
        return out

    def _pair_key(self, a: str, b: str) -> Tuple[str, str]:
        return (a, b) if a <= b else (b, a)

    def _update_pair_stats(self, current: Mapping[str, float], sample_weight: float) -> None:
        names = list(self.feature_names)
        for i, left in enumerate(names):
            for right in names[i + 1 :]:
                key = self._pair_key(left, right)
                stats = self.pair_stats.setdefault(key, OnlinePairStats())
                stats.update(
                    float(current.get(left, 0.0)),
                    float(current.get(right, 0.0)),
                    sample_weight,
                )

    @staticmethod
    def _source_key(source_id: Optional[str]) -> str:
        source = str(source_id or "unknown").strip()
        return source if source else "unknown"

    def _update_source_stats(
        self,
        current: Mapping[str, float],
        target: float,
        sample_weight: float,
        source_id: Optional[str],
    ) -> None:
        source = self._source_key(source_id)
        for name in self.feature_names:
            per_source = self.source_feature_stats.setdefault(name, {})
            stats = per_source.setdefault(source, OnlineStats())
            stats.update(float(current.get(name, 0.0)), target, sample_weight)

    def _predict_logit(self, current: Mapping[str, float], lagged: Optional[Mapping[str, float]] = None) -> float:
        z = self.bias
        for name in self.feature_names:
            z += self.current_weights.get(name, 0.0) * float(current.get(name, 0.0))
            if lagged is not None:
                z += self.lag_weights.get(name, 0.0) * float(lagged.get(name, 0.0))
        return z

    def predict_proba(self, features: Mapping[str, Any]) -> float:
        current = self._vectorize(features)
        lagged = self._history[-1] if self._history else None
        return sigmoid(self._predict_logit(current, lagged))

    def predict(self, features: Mapping[str, Any]) -> bool:
        return self.predict_proba(features) >= self.decision_threshold

    def update(
        self,
        features: Mapping[str, Any],
        target: bool | int | float,
        sample_weight: float = 1.0,
        source_id: Optional[str] = None,
        verification_report: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        current = self._vectorize(features)
        lagged = self._history[-1] if self._history else None
        y = 1.0 if bool(target) else 0.0
        raw_weight = max(float(sample_weight), 0.0)
        verification_score = clamp(float((verification_report or {}).get("score", 1.0)))
        weight = raw_weight * verification_score
        logit = self._predict_logit(current, lagged)
        proba = sigmoid(logit)
        error = (y - proba) * weight

        for name in self.feature_names:
            x = float(current.get(name, 0.0))
            prev = float(lagged.get(name, 0.0)) if lagged is not None else 0.0

            self.feature_stats[name].update(x, y, weight)

            grad_current = error * x - self.l2 * self.current_weights[name]
            grad_lag = error * prev - self.l2 * self.lag_weights[name]

            self.current_weights[name] += self.learning_rate * grad_current
            self.lag_weights[name] += self.learning_rate * grad_lag

        self._update_pair_stats(current, weight)
        self._update_source_stats(current, y, weight, source_id)
        source_key = self._source_key(source_id)
        provenance_hash = None
        if verification_report:
            provenance_hash = verification_report.get("provenance_hash") or verification_report.get("artifact_hash")
        self.source_quality.setdefault(source_key, SourceQualityStats()).update(
            verification_report,
            weight,
            str(provenance_hash) if provenance_hash else None,
        )

        self.bias += self.learning_rate * error
        self.sample_count += 1
        self.total_weight += weight
        loss = -(y * _safe_log(proba) + (1.0 - y) * _safe_log(1.0 - proba))
        self.total_loss += loss * (weight if weight > 0.0 else 1.0)
        correct = int((proba >= self.decision_threshold) == bool(y))
        self.correct_count += correct
        self.weighted_correct += correct * weight

        self._history.append(current)
        self._labeled_history.append(
            LabeledObservation(
                features=dict(current),
                target=y,
                sample_weight=weight,
                source_id=source_key,
                verification_score=verification_score,
                provenance_hash=str(provenance_hash) if provenance_hash else None,
                predicted_probability=proba,
                loss=loss,
            )
        )
        return {
            "predicted_probability": proba,
            "target": y,
            "error": error,
            "loss": loss,
            "samples_seen": self.sample_count,
            "sample_weight": weight,
            "raw_sample_weight": raw_weight,
            "verification_score": verification_score,
            "weighted_samples_seen": self.total_weight,
            "source_id": source_key,
        }

    def train_batch(self, rows: Sequence[Mapping[str, Any]]) -> None:
        for row in rows:
            features = dict(row.get("features", {}))
            target = row.get("target", False)
            self.update(
                features,
                target,
                float(row.get("sample_weight", 1.0)),
                source_id=row.get("source_id"),
                verification_report=row.get("verification_report"),
            )

    def independence_score(self, feature_name: str) -> Tuple[float, Optional[str], float]:
        max_redundancy = 0.0
        partner: Optional[str] = None
        for other in self.feature_names:
            if other == feature_name:
                continue
            report = self._conditional_redundancy_between(feature_name, other)
            redundancy = float(report["adjusted_redundancy"])
            if redundancy > max_redundancy:
                max_redundancy = redundancy
                partner = other
        independence = clamp(1.0 - max_redundancy)
        return independence, partner, max_redundancy

    def _feature_series(self, feature_name: str) -> Tuple[list[float], list[float]]:
        values: list[float] = []
        weights: list[float] = []
        for obs in self._labeled_history:
            if feature_name in obs.features:
                values.append(float(obs.features.get(feature_name, 0.0)))
                weights.append(float(obs.sample_weight))
        return values, weights

    def _conditional_redundancy_between(self, left: str, right: str) -> Dict[str, Any]:
        stats = self.pair_stats.get(self._pair_key(left, right))
        raw_redundancy = stats.redundancy_score(self.independence_min_support) if stats else 0.0
        raw_corr = stats.correlation if stats else 0.0
        mean_abs_delta = stats.mean_abs_delta if stats else 1.0
        support = stats.total_weight if stats else 0.0
        if support < self.independence_min_support:
            return {
                "raw_redundancy": raw_redundancy,
                "adjusted_redundancy": raw_redundancy,
                "raw_correlation": raw_corr,
                "partial_correlation": raw_corr,
                "best_conditioner": None,
                "mean_abs_delta": mean_abs_delta,
                "support": support,
            }

        # Exact copies should stay non-independent even if a third feature also
        # explains them. This catches duplicated collectors/features.
        exact_copy = mean_abs_delta < 1e-9 and raw_redundancy >= 0.95
        best_conditioner: Optional[str] = None
        best_partial = abs(raw_corr)
        for candidate in self.feature_names:
            if candidate in {left, right}:
                continue
            r_xz = self._history_correlation(left, candidate)
            r_yz = self._history_correlation(right, candidate)
            denom = sqrt(max((1.0 - r_xz * r_xz) * (1.0 - r_yz * r_yz), 1e-12))
            partial = clamp((raw_corr - r_xz * r_yz) / denom, -1.0, 1.0)
            if abs(partial) < best_partial:
                best_partial = abs(partial)
                best_conditioner = candidate

        if exact_copy:
            adjusted = 1.0
        elif best_conditioner is not None and best_partial < abs(raw_corr):
            # If a third feature explains the shared variance, reduce the
            # redundancy penalty. This is a production approximation of
            # conditional independence, not a proof.
            adjusted = clamp(min(raw_redundancy, best_partial))
        else:
            adjusted = raw_redundancy
        return {
            "raw_redundancy": raw_redundancy,
            "adjusted_redundancy": adjusted,
            "raw_correlation": raw_corr,
            "partial_correlation": best_partial if raw_corr >= 0 else -best_partial,
            "best_conditioner": best_conditioner,
            "mean_abs_delta": mean_abs_delta,
            "support": support,
        }

    def _history_correlation(self, left: str, right: str) -> float:
        xs: list[float] = []
        ys: list[float] = []
        ws: list[float] = []
        for obs in self._labeled_history:
            xs.append(float(obs.features.get(left, 0.0)))
            ys.append(float(obs.features.get(right, 0.0)))
            ws.append(float(obs.sample_weight))
        return _weighted_corr(xs, ys, ws)

    def weighted_stability(self, feature_name: str) -> float:
        return float(self.temporal_stability_report(feature_name)["score"])

    def _observations_for(self, feature_name: str) -> list[LabeledObservation]:
        return [obs for obs in self._labeled_history if feature_name in obs.features]

    def temporal_stability_report(self, feature_name: str) -> Dict[str, Any]:
        stats = self.feature_stats.get(feature_name, OnlineStats())
        legacy = _weighted_stability(
            abs(self.current_weights.get(feature_name, 0.0)) + abs(self.lag_weights.get(feature_name, 0.0)),
            stats.effective_support,
            stats.variance,
        )
        observations = self._observations_for(feature_name)
        if len(observations) < max(8, self.stability_window // 2):
            return {
                "feature": feature_name,
                "score": legacy,
                "mode": "weighted_welford_warmup",
                "support": stats.effective_support,
                "recent_correlation": stats.correlation,
                "baseline_correlation": stats.correlation,
                "drift_score": 0.0,
                "prediction_volatility": 0.0,
                "sign_consistency": 1.0,
                "passed": legacy >= 0.55,
            }

        window = min(self.stability_window, len(observations) // 2)
        baseline_obs = observations[-2 * window : -window]
        recent_obs = observations[-window:]
        baseline_corr = _weighted_corr(
            [obs.features.get(feature_name, 0.0) for obs in baseline_obs],
            [obs.target for obs in baseline_obs],
            [obs.sample_weight for obs in baseline_obs],
        )
        recent_corr = _weighted_corr(
            [obs.features.get(feature_name, 0.0) for obs in recent_obs],
            [obs.target for obs in recent_obs],
            [obs.sample_weight for obs in recent_obs],
        )
        drift_score = clamp(abs(recent_corr - baseline_corr) / 2.0)
        strong_flip = (
            baseline_corr * recent_corr < 0.0
            and abs(baseline_corr) > 0.08
            and abs(recent_corr) > 0.08
        )
        sign_consistency = 0.0 if strong_flip else 1.0 - drift_score
        losses = [obs.loss for obs in recent_obs]
        loss_mean = sum(losses) / max(len(losses), 1)
        loss_var = sum((loss - loss_mean) ** 2 for loss in losses) / max(len(losses), 1)
        prediction_volatility = clamp(sqrt(loss_var))
        prediction_stability = 1.0 / (1.0 + prediction_volatility)
        support_term = 1.0 - exp(-max(stats.effective_support, 0.0) / 25.0)
        variance_term = 1.0 / (1.0 + max(stats.variance, 0.0))
        temporal_consistency = clamp(1.0 - drift_score) * sign_consistency
        score = clamp(
            0.25 * legacy
            + 0.25 * support_term
            + 0.20 * temporal_consistency
            + 0.15 * prediction_stability
            + 0.15 * variance_term
        )
        return {
            "feature": feature_name,
            "score": score,
            "mode": "rolling_window_temporal_stability",
            "support": stats.effective_support,
            "window": window,
            "recent_correlation": recent_corr,
            "baseline_correlation": baseline_corr,
            "drift_score": drift_score,
            "prediction_volatility": prediction_volatility,
            "sign_consistency": sign_consistency,
            "temporal_consistency": temporal_consistency,
            "passed": score >= 0.60 and drift_score <= self.drift_threshold,
        }

    def stability_report(self) -> Dict[str, Any]:
        features = [self.temporal_stability_report(name) for name in self.feature_names]
        evaluated = [item for item in features if item["mode"] != "weighted_welford_warmup"]
        return {
            "method": "rolling_window_weighted_stability_v2",
            "window": self.stability_window,
            "drift_threshold": self.drift_threshold,
            "passed": all(item["passed"] for item in evaluated) if evaluated else False,
            "features": features,
        }

    def cross_source_corroboration(self, feature_name: str) -> Dict[str, Any]:
        per_source = self.source_feature_stats.get(feature_name, {})
        qualified = {
            source: stats
            for source, stats in per_source.items()
            if stats.effective_support >= self.source_min_support
        }
        if not qualified:
            return {
                "feature": feature_name,
                "score": 0.0,
                "distinct_sources": 0,
                "qualified_sources": [],
                "source_balance": 0.0,
                "agreement": 0.0,
                "consensus_strength": 0.0,
                "passed": False,
            }

        supports = {source: stats.effective_support for source, stats in qualified.items()}
        total_support = sum(supports.values()) or 1.0
        distinct_sources = len(qualified)
        source_diversity = clamp(distinct_sources / max(self.min_corroborating_sources, 1))

        if distinct_sources <= 1:
            source_balance = 0.0
        else:
            max_share = max(supports.values()) / total_support
            source_balance = clamp((1.0 - max_share) / max(1.0 - 1.0 / distinct_sources, 1e-12))

        edge_weight = self.current_weights.get(feature_name, 0.0) + self.lag_weights.get(feature_name, 0.0)
        global_sign = 1 if edge_weight >= 0 else -1
        signed_support = 0.0
        usable_support = 0.0
        qualified_sources: list[Dict[str, Any]] = []
        for source, stats in sorted(qualified.items()):
            corr = stats.correlation
            sign = 0
            if abs(corr) >= 0.03:
                sign = 1 if corr > 0 else -1
                signed_support += sign * stats.effective_support
                usable_support += stats.effective_support
            qualified_sources.append(
                {
                    "source": source,
                    "support": stats.effective_support,
                    "mean": stats.mean,
                    "target_mean": stats.target_mean,
                    "correlation": corr,
                    "sign": sign,
                }
            )

        if usable_support <= 1e-12:
            agreement = 0.5
            consensus_strength = 0.0
        else:
            agreement = clamp(0.5 + 0.5 * global_sign * signed_support / usable_support)
            consensus_strength = clamp(abs(signed_support) / usable_support)

        if distinct_sources < self.min_corroborating_sources:
            # Single-source evidence remains useful, but it cannot pass the
            # production corroboration gate by itself.
            score = clamp(0.25 + 0.20 * source_diversity)
        else:
            score = clamp(0.30 * source_diversity + 0.45 * consensus_strength + 0.25 * source_balance)

        return {
            "feature": feature_name,
            "score": score,
            "distinct_sources": distinct_sources,
            "qualified_sources": qualified_sources,
            "source_balance": source_balance,
            "agreement": agreement,
            "consensus_strength": consensus_strength,
            "passed": distinct_sources >= self.min_corroborating_sources and score >= 0.60,
        }

    def cross_source_corroboration_test(self) -> Dict[str, Any]:
        features = [self.cross_source_corroboration(name) for name in self.feature_names]
        evaluated = [item for item in features if item["distinct_sources"] > 0]
        return {
            "passed": all(item["passed"] for item in evaluated) if evaluated else False,
            "min_sources": self.min_corroborating_sources,
            "source_min_support": self.source_min_support,
            "features": features,
        }

    def intervention_effect(self, feature_name: str) -> Dict[str, Any]:
        if feature_name not in self.feature_names:
            return {"feature": feature_name, "effect": 0.0, "abs_effect": 0.0, "baseline_probability": 0.0}

        baseline = {
            name: self.feature_stats.get(name, OnlineStats()).mean
            for name in self.feature_names
        }
        stats = self.feature_stats.get(feature_name, OnlineStats())
        low = stats.min_value if stats.min_value != float("inf") else 0.0
        high = stats.max_value if stats.max_value != float("-inf") else 1.0
        if abs(high - low) < 1e-12:
            low, high = 0.0, 1.0

        low_sample = dict(baseline)
        high_sample = dict(baseline)
        low_sample[feature_name] = low
        high_sample[feature_name] = high
        p_low = sigmoid(self._predict_logit(low_sample, None))
        p_high = sigmoid(self._predict_logit(high_sample, None))
        baseline_probability = sigmoid(self._predict_logit(baseline, None))
        effect = p_high - p_low
        return {
            "feature": feature_name,
            "do_low": low,
            "do_high": high,
            "p_do_low": p_low,
            "p_do_high": p_high,
            "baseline_probability": baseline_probability,
            "effect": effect,
            "abs_effect": abs(effect),
            "direction": "positive" if effect > 0 else ("negative" if effect < 0 else "neutral"),
        }

    def intervention_approximation(self) -> Dict[str, Any]:
        effects = [self.intervention_effect(name) for name in self.feature_names]
        effects.sort(key=lambda item: item["abs_effect"], reverse=True)
        return {
            "method": "counterfactual_feature_clamp",
            "note": "Production approximation: clamps one learned feature at a time and measures probability shift; not a randomized causal trial.",
            "features": effects,
        }

    def independence_test(self) -> Dict[str, Any]:
        pairs: list[Dict[str, Any]] = []
        passed = True
        for (left, right), stats in sorted(self.pair_stats.items()):
            conditional = self._conditional_redundancy_between(left, right)
            redundancy = float(conditional["adjusted_redundancy"])
            independent = redundancy < self.redundancy_threshold
            passed = passed and independent
            pairs.append(
                {
                    "left": left,
                    "right": right,
                    "support": stats.total_weight,
                    "correlation": stats.correlation,
                    "partial_correlation": conditional["partial_correlation"],
                    "best_conditioner": conditional["best_conditioner"],
                    "mean_abs_delta": stats.mean_abs_delta,
                    "raw_redundancy": conditional["raw_redundancy"],
                    "redundancy": redundancy,
                    "conditional_independent": independent,
                    "independent": independent,
                }
            )
        return {
            "method": "pairwise_plus_partial_correlation_v2",
            "passed": passed,
            "min_support": self.independence_min_support,
            "redundancy_threshold": self.redundancy_threshold,
            "pairs": pairs,
        }



    def source_verification_report(self) -> Dict[str, Any]:
        sources = [stats.report(source) for source, stats in sorted(self.source_quality.items())]
        hash_to_sources: Dict[str, set[str]] = {}
        for source, stats in self.source_quality.items():
            for digest in stats.distinct_hashes:
                hash_to_sources.setdefault(digest, set()).add(source)
        shared_hashes = [
            {"provenance_hash": digest, "sources": sorted(list(sources_for_hash))}
            for digest, sources_for_hash in hash_to_sources.items()
            if len(sources_for_hash) > 1
        ]
        avg_score = 0.0
        if sources:
            total = sum(item["weighted_support"] for item in sources) or 1.0
            avg_score = sum(item["avg_verification_score"] * item["weighted_support"] for item in sources) / total
        return {
            "method": "source_registry_provenance_digest_v2",
            "passed": bool(sources) and avg_score >= 0.60,
            "avg_verification_score": avg_score,
            "sources": sources,
            "shared_provenance_hashes": shared_hashes,
            "anti_collusion_note": "Shared hashes are not automatically bad, but they are flagged so independent collectors do not silently double-count mirrored evidence.",
        }

    def causal_graph_report(self) -> Dict[str, Any]:
        edges = [edge.to_dict() for edge in self.edges()]
        adjacency: Dict[str, list[Dict[str, Any]]] = {}
        for edge in edges:
            adjacency.setdefault(edge["source"], []).append(
                {
                    "target": edge["target"],
                    "lag": edge["lag"],
                    "weight": edge["weight"],
                    "confidence": edge["confidence"],
                    "kind": edge["kind"],
                }
            )
        mechanisms = {
            name: {
                "equation": "p(target=1)=sigmoid(b + Σw_i*x_i + Σu_i*x_i[t-1])",
                "current_weight": self.current_weights.get(name, 0.0),
                "lag1_weight": self.lag_weights.get(name, 0.0),
                "stability": self.weighted_stability(name),
                "independence": self.independence_score(name)[0],
                "corroboration": self.cross_source_corroboration(name)["score"],
                "intervention_effect": self.intervention_effect(name)["abs_effect"],
            }
            for name in self.feature_names
        }
        return {
            "schema_version": "spl.causal_graph.v7.1",
            "graph_type": "online_feature_to_decision_with_temporal_lag",
            "target": self.target_name,
            "nodes": [{"id": name, "type": "feature"} for name in self.feature_names] + [{"id": self.target_name, "type": "target"}],
            "edges": edges,
            "adjacency": adjacency,
            "mechanisms": mechanisms,
            "constraints": {
                "stability": self.stability_report(),
                "independence": self.independence_test(),
                "cross_source_corroboration": self.cross_source_corroboration_test(),
                "source_verification": self.source_verification_report(),
                "intervention_approximation": self.intervention_approximation(),
            },
        }

    def edges(self, min_abs_weight: float = 1e-6) -> list[CausalEdge]:
        out: list[CausalEdge] = []
        for name in self.feature_names:
            current_weight = float(self.current_weights.get(name, 0.0))
            lag_weight = float(self.lag_weights.get(name, 0.0))
            stats = self.feature_stats.get(name, OnlineStats())
            independence, partner, _ = self.independence_score(name)
            stability = self.weighted_stability(name)
            corroboration = self.cross_source_corroboration(name)["score"]
            intervention = self.intervention_effect(name)["abs_effect"]
            support = stats.effective_support

            if abs(current_weight) >= min_abs_weight:
                out.append(
                    CausalEdge(
                        source=name,
                        target=self.target_name,
                        lag=0,
                        weight=current_weight,
                        support=support,
                        confidence=_edge_confidence(current_weight, support, independence, stability, corroboration, intervention),
                        kind="instantaneous",
                        independence=independence,
                        weighted_stability=stability,
                        cross_source_corroboration=corroboration,
                        intervention_effect=intervention,
                        redundancy_partner=partner,
                    )
                )
            if abs(lag_weight) >= min_abs_weight:
                out.append(
                    CausalEdge(
                        source=f"{name}[t-1]",
                        target=self.target_name,
                        lag=1,
                        weight=lag_weight,
                        support=support,
                        confidence=_edge_confidence(lag_weight, support, independence, stability, corroboration, intervention),
                        kind="temporal",
                        independence=independence,
                        weighted_stability=stability,
                        cross_source_corroboration=corroboration,
                        intervention_effect=intervention,
                        redundancy_partner=partner,
                    )
                )
        out.sort(key=lambda e: abs(e.weight) * e.confidence, reverse=True)
        return out

    def snapshot(self, include_causal_graph: bool = True) -> Dict[str, Any]:
        edges = [edge.to_dict() for edge in self.edges()]
        nodes = [{"id": name, "type": "feature"} for name in self.feature_names] + [{"id": self.target_name, "type": "target"}]
        snapshot = {
            "target": self.target_name,
            "bias": self.bias,
            "learning_rate": self.learning_rate,
            "l2": self.l2,
            "lag": self.lag,
            "samples_seen": self.sample_count,
            "weighted_samples_seen": self.total_weight,
            "accuracy": self.accuracy(),
            "weighted_accuracy": self.weighted_accuracy(),
            "avg_loss": self.average_loss(),
            "nodes": nodes,
            "edges": edges,
            "independence_test": self.independence_test(),
            "cross_source_corroboration_test": self.cross_source_corroboration_test(),
            "stability_test": self.stability_report(),
            "intervention_approximation": self.intervention_approximation(),
            "source_verification_test": self.source_verification_report(),
            "constraint_tests": {
                "stability": self.stability_report(),
                "independence": self.independence_test(),
                "cross_source_corroboration": self.cross_source_corroboration_test(),
                "source_verification": self.source_verification_report(),
                "intervention_approximation": self.intervention_approximation(),
            },
            "weights": {
                name: {
                    "current": self.current_weights.get(name, 0.0),
                    "lag1": self.lag_weights.get(name, 0.0),
                    "variance": self.feature_stats.get(name, OnlineStats()).variance,
                    "support": self.feature_stats.get(name, OnlineStats()).count,
                    "weighted_support": self.feature_stats.get(name, OnlineStats()).effective_support,
                    "independence": self.independence_score(name)[0],
                    "weighted_stability": self.weighted_stability(name),
                    "cross_source_corroboration": self.cross_source_corroboration(name)["score"],
                    "intervention_effect": self.intervention_effect(name)["abs_effect"],
                    "stability_report": self.temporal_stability_report(name),
                    "redundancy_partner": self.independence_score(name)[1],
                }
                for name in self.feature_names
            },
        }
        if include_causal_graph:
            snapshot["causal_graph"] = self.causal_graph_report()
        return snapshot

    def accuracy(self) -> float:
        if self.sample_count == 0:
            return 0.0
        return self.correct_count / self.sample_count

    def weighted_accuracy(self) -> float:
        if self.total_weight <= 1e-12:
            return 0.0
        return self.weighted_correct / self.total_weight

    def average_loss(self) -> float:
        if self.total_weight <= 1e-12:
            return 0.0
        return self.total_loss / self.total_weight

    def decision_surface(self, resolution: int = 40) -> Dict[str, Any]:
        """
        Build a topology surface over the most important two features.
        Used by the dashboard as a 3D risk surface.
        """
        if not self.feature_names:
            return {"x": [], "y": [], "z": []}

        ordered = sorted(
            self.feature_names,
            key=lambda n: (
                abs(self.current_weights.get(n, 0.0))
                + abs(self.lag_weights.get(n, 0.0))
            )
            * self.independence_score(n)[0]
            * self.weighted_stability(n)
            * max(self.cross_source_corroboration(n)["score"], 0.05)
            * (0.5 + self.intervention_effect(n)["abs_effect"]),
            reverse=True,
        )
        f1 = ordered[0]
        f2 = ordered[1] if len(ordered) > 1 else ordered[0]
        grid = []
        xs = [i / (resolution - 1) * 2.0 - 1.0 for i in range(resolution)]
        ys = [i / (resolution - 1) * 2.0 - 1.0 for i in range(resolution)]
        for y in ys:
            row = []
            for x in xs:
                sample = {name: 0.0 for name in self.feature_names}
                sample[f1] = x
                sample[f2] = y
                row.append(self.predict_proba(sample))
            grid.append(row)
        return {"x": xs, "y": ys, "z": grid, "feature_x": f1, "feature_y": f2}



def _weighted_corr(xs: Sequence[float], ys: Sequence[float], ws: Sequence[float]) -> float:
    if not xs or not ys or len(xs) != len(ys):
        return 0.0
    weights = [max(float(w), 0.0) for w in ws] if ws else [1.0] * len(xs)
    if len(weights) != len(xs):
        weights = [1.0] * len(xs)
    total = sum(weights)
    if total <= 1e-12:
        return 0.0
    mx = sum(float(x) * w for x, w in zip(xs, weights)) / total
    my = sum(float(y) * w for y, w in zip(ys, weights)) / total
    vx = sum(w * (float(x) - mx) ** 2 for x, w in zip(xs, weights)) / total
    vy = sum(w * (float(y) - my) ** 2 for y, w in zip(ys, weights)) / total
    if vx <= 1e-12 or vy <= 1e-12:
        return 0.0
    cov = sum(w * (float(x) - mx) * (float(y) - my) for x, y, w in zip(xs, ys, weights)) / total
    return clamp(cov / sqrt(vx * vy), -1.0, 1.0)

def _weighted_stability(weight_magnitude: float, weighted_support: float, variance: float) -> float:
    support_term = 1.0 - exp(-max(float(weighted_support), 0.0) / 20.0)
    variance_term = 1.0 / (1.0 + max(float(variance), 0.0))
    magnitude_term = min(1.0, abs(float(weight_magnitude)))
    return clamp(0.45 * variance_term + 0.35 * support_term + 0.20 * magnitude_term, 0.0, 1.0)


def _edge_confidence(
    weight: float,
    weighted_support: float,
    independence: float,
    stability: float,
    corroboration: float,
    intervention_effect: float,
) -> float:
    base = min(1.0, abs(weight))
    support_term = 1.0 - exp(-max(float(weighted_support), 0.0) / 20.0)
    intervention_term = clamp(abs(intervention_effect) * 2.0)
    return clamp(
        0.22 * base
        + 0.20 * support_term
        + 0.18 * clamp(stability)
        + 0.15 * clamp(independence)
        + 0.15 * clamp(corroboration)
        + 0.10 * intervention_term,
        0.0,
        1.0,
    )


def _safe_log(value: float) -> float:
    from math import log

    return log(max(min(value, 1.0 - 1e-12), 1e-12))
