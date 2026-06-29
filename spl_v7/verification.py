from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, Mapping, Optional

from .schema import EvidenceArtifact
from .utils import clamp


def canonical_json(value: Any) -> str:
    """Stable JSON representation used for provenance digests."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def artifact_provenance_payload(artifact: EvidenceArtifact) -> Dict[str, Any]:
    payload = artifact.to_dict()
    integrity = dict(payload.get("integrity") or {})
    integrity["hash"] = None
    integrity["signature"] = None
    payload["integrity"] = integrity
    return payload


def compute_artifact_hash(artifact: EvidenceArtifact) -> str:
    alg = (artifact.integrity.digest_alg or "sha256").lower()
    if alg != "sha256":
        # The project currently commits to sha256 for deterministic local
        # validation. Other algorithms should be added explicitly, not silently.
        alg = "sha256"
    return hashlib.sha256(canonical_json(artifact_provenance_payload(artifact)).encode("utf-8")).hexdigest()


def compute_artifact_signature(artifact: EvidenceArtifact, secret: str) -> str:
    digest = compute_artifact_hash(artifact)
    return hmac.new(secret.encode("utf-8"), digest.encode("utf-8"), hashlib.sha256).hexdigest()


@dataclass(slots=True)
class SourceProfile:
    source_id: str
    trust_weight: float = 1.0
    allowed_types: list[str] = field(default_factory=list)
    require_signature: bool = False
    shared_secret: Optional[str] = None
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if data.get("shared_secret"):
            data["shared_secret"] = "***"
        return data


class SourceRegistry:
    def __init__(self, profiles: Optional[Iterable[SourceProfile]] = None) -> None:
        self._profiles: Dict[str, SourceProfile] = {}
        for profile in profiles or []:
            self.register(profile)

    def register(self, profile: SourceProfile) -> None:
        self._profiles[profile.source_id] = profile

    def get(self, source_id: str) -> Optional[SourceProfile]:
        return self._profiles.get(source_id)

    @classmethod
    def default(cls) -> "SourceRegistry":
        return cls(
            [
                SourceProfile("collector", trust_weight=0.75, allowed_types=[]),
                SourceProfile("collector-a", trust_weight=0.95, allowed_types=[]),
                SourceProfile("collector-b", trust_weight=0.95, allowed_types=[]),
                SourceProfile("collector-c", trust_weight=0.85, allowed_types=[]),
                SourceProfile("ofe", trust_weight=0.90, allowed_types=["structural_signal", "frontier_signal"]),
                SourceProfile("unknown", trust_weight=0.35, allowed_types=[]),
            ]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {source: profile.to_dict() for source, profile in sorted(self._profiles.items())}


class EvidenceProvenanceVerifier:
    """
    Production-light provenance verifier.

    This is intentionally not a PKI system. It provides the hooks v7.1 needs:
    source registry checks, stable artifact digest validation, optional HMAC
    signature validation, transport sanity, and a single verification score that
    can be used by the learner as sample weight attenuation.
    """

    def __init__(self, registry: Optional[SourceRegistry] = None) -> None:
        self.registry = registry or SourceRegistry.default()

    def verify(self, artifact: EvidenceArtifact) -> Dict[str, Any]:
        profile = self.registry.get(artifact.source)
        source_registered = profile is not None and bool(profile.enabled)
        source_trust = clamp(profile.trust_weight if profile else 0.25)
        type_allowed = True
        if profile and profile.allowed_types:
            type_allowed = artifact.type in profile.allowed_types

        expected_hash = compute_artifact_hash(artifact)
        supplied_hash = artifact.integrity.hash
        digest_present = bool(supplied_hash)
        digest_valid = bool(digest_present and supplied_hash == expected_hash)
        if not digest_present:
            # Missing digests are allowed for local development, but penalized.
            digest_component = 0.35
        else:
            digest_component = 1.0 if digest_valid else 0.0

        signature_present = bool(artifact.integrity.signature)
        signature_valid = False
        signature_status = "absent"
        if profile and profile.shared_secret and signature_present:
            expected_sig = compute_artifact_signature(artifact, profile.shared_secret)
            signature_valid = hmac.compare_digest(str(artifact.integrity.signature), expected_sig)
            signature_status = "valid" if signature_valid else "invalid"
        elif profile and profile.require_signature:
            signature_status = "required_missing" if not signature_present else "unverified"
        elif signature_present:
            # Signature exists but no secret/public material is configured here.
            signature_status = "present_unverified"

        if profile and profile.require_signature:
            signature_component = 1.0 if signature_valid else 0.0
        else:
            signature_component = 0.75 if signature_present else 0.50

        transport_ok = artifact.transport_meta.status in {"ok", "partial"} and not artifact.transport_meta.error_type
        transport_component = 1.0 if transport_ok else 0.25
        source_component = 1.0 if source_registered and type_allowed else 0.25
        score = clamp(
            0.25 * source_component
            + 0.25 * digest_component
            + 0.15 * signature_component
            + 0.15 * transport_component
            + 0.20 * source_trust
        )
        return {
            "method": "registry_digest_signature_transport_v2",
            "source": artifact.source,
            "source_registered": source_registered,
            "source_trust": source_trust,
            "type_allowed": type_allowed,
            "digest_present": digest_present,
            "digest_valid": digest_valid,
            "expected_hash": expected_hash,
            "provenance_hash": supplied_hash or expected_hash,
            "artifact_hash": expected_hash,
            "signature_present": signature_present,
            "signature_valid": signature_valid,
            "signature_status": signature_status,
            "transport_ok": transport_ok,
            "score": score,
            "passed": score >= 0.60 and source_registered and type_allowed and transport_ok and (not digest_present or digest_valid),
        }
