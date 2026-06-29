from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional
from uuid import uuid4


EVIDENCE_SCHEMA_ID = "https://spl.ai/schema/evidence/v7"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class EvidenceTransportMeta:
    status: str = "ok"  # ok | timeout | error | partial
    latency_ms: float = 0.0
    bytes_received: int = 0
    http_status: Optional[int] = None
    timeout_ms: Optional[int] = None
    error_type: Optional[str] = None
    user_agent: Optional[str] = None
    content_type: Optional[str] = None
    redirected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvidenceTransportMeta":
        # Preserve dataclass defaults for missing keys. Passing None for every
        # absent field turns status/latency/bytes_received into None and weakens
        # downstream quality gates.
        return cls(**{k: data[k] for k in cls.__dataclass_fields__.keys() if k in data})


@dataclass(slots=True)
class EvidenceIntegrity:
    hash: Optional[str] = None
    signature: Optional[str] = None
    digest_alg: str = "sha256"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvidenceIntegrity":
        return cls(**{k: data[k] for k in cls.__dataclass_fields__.keys() if k in data})


@dataclass(slots=True)
class EvidenceArtifact:
    evidence_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=utc_now)
    source: str = "unknown"
    type: str = "generic"
    data: Dict[str, Any] = field(default_factory=dict)
    transport_meta: EvidenceTransportMeta = field(default_factory=EvidenceTransportMeta)
    integrity: EvidenceIntegrity = field(default_factory=EvidenceIntegrity)
    tags: list[str] = field(default_factory=list)
    version: str = "v7"

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["transport_meta"] = self.transport_meta.to_dict()
        payload["integrity"] = self.integrity.to_dict()
        return payload

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvidenceArtifact":
        transport_meta = data.get("transport_meta") or {}
        integrity = data.get("integrity") or {}
        return cls(
            evidence_id=data.get("evidence_id", str(uuid4())),
            timestamp=data.get("timestamp", utc_now()),
            source=data.get("source", "unknown"),
            type=data.get("type", "generic"),
            data=dict(data.get("data") or {}),
            transport_meta=EvidenceTransportMeta.from_dict(transport_meta),
            integrity=EvidenceIntegrity.from_dict(integrity),
            tags=list(data.get("tags") or []),
            version=data.get("version", "v7"),
        )


def evidence_schema() -> Dict[str, Any]:
    return {
        "$schema": EVIDENCE_SCHEMA_ID,
        "title": "SPL Evidence Artifact v7",
        "type": "object",
        "required": ["evidence_id", "timestamp", "source", "type", "data", "transport_meta"],
        "properties": {
            "evidence_id": {"type": "string", "format": "uuid"},
            "timestamp": {"type": "string", "format": "date-time"},
            "source": {"type": "string"},
            "type": {"type": "string"},
            "data": {"type": "object", "additionalProperties": True},
            "transport_meta": {
                "type": "object",
                "required": ["status"],
                "properties": {
                    "status": {"type": "string", "enum": ["ok", "timeout", "error", "partial"]},
                    "latency_ms": {"type": "number"},
                    "bytes_received": {"type": "integer"},
                    "http_status": {"type": ["integer", "null"]},
                    "timeout_ms": {"type": ["integer", "null"]},
                    "error_type": {"type": ["string", "null"]},
                    "user_agent": {"type": ["string", "null"]},
                    "content_type": {"type": ["string", "null"]},
                    "redirected": {"type": "boolean"},
                },
            },
            "integrity": {
                "type": "object",
                "properties": {
                    "hash": {"type": ["string", "null"]},
                    "signature": {"type": ["string", "null"]},
                    "digest_alg": {"type": "string"},
                },
            },
            "tags": {"type": "array", "items": {"type": "string"}},
            "version": {"type": "string"},
        },
    }
