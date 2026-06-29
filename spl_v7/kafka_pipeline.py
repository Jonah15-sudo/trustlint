from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Mapping, Optional

from .causal import OnlineCausalGraphLearner
from .dsl import FeatureDSLProgram
from .schema import EvidenceArtifact
from .verification import EvidenceProvenanceVerifier


try:
    from confluent_kafka import Consumer, Producer  # type: ignore
    _KAFKA_AVAILABLE = True
except Exception:  # pragma: no cover
    Consumer = Producer = None  # type: ignore
    _KAFKA_AVAILABLE = False


@dataclass(slots=True)
class PipelineConfig:
    bootstrap_servers: str = "localhost:9092"
    group_id: str = "spl-v7"
    raw_topic: str = "spl.raw.evidence"
    features_topic: str = "spl.features"
    decisions_topic: str = "spl.decisions"
    dlq_topic: str = "spl.dlq"
    request_timeout_ms: int = 3000
    session_timeout_ms: int = 6000
    poll_interval_sec: float = 0.2
    produce_timeout_sec: float = 5.0
    max_batch_size: int = 100
    backend: str = "auto"  # auto | kafka | memory
    emit_graph_snapshot: bool = True


@dataclass(slots=True)
class PipelineMessage:
    topic: str
    key: Optional[str]
    value: Dict[str, Any]
    timestamp: float = field(default_factory=lambda: time.time())

    def to_json(self) -> str:
        return json.dumps(
            {
                "topic": self.topic,
                "key": self.key,
                "value": self.value,
                "timestamp": self.timestamp,
            },
            ensure_ascii=False,
        )


class InMemoryBus:
    def __init__(self) -> None:
        self.topics: Dict[str, "queue.Queue[PipelineMessage]"] = {}

    def _topic(self, name: str) -> "queue.Queue[PipelineMessage]":
        if name not in self.topics:
            self.topics[name] = queue.Queue()
        return self.topics[name]

    def produce(self, topic: str, message: PipelineMessage) -> None:
        self._topic(topic).put(message)

    def consume(self, topic: str, timeout: float = 0.1) -> Optional[PipelineMessage]:
        try:
            return self._topic(topic).get(timeout=timeout)
        except queue.Empty:
            return None


class KafkaAdapter:
    def produce(self, topic: str, key: Optional[str], value: Dict[str, Any]) -> None:
        raise NotImplementedError

    def consume(self, topic: str, timeout: float = 0.1) -> Optional[PipelineMessage]:
        raise NotImplementedError

    def close(self) -> None:
        return None


class MemoryKafkaAdapter(KafkaAdapter):
    def __init__(self) -> None:
        self.bus = InMemoryBus()

    def produce(self, topic: str, key: Optional[str], value: Dict[str, Any]) -> None:
        self.bus.produce(topic, PipelineMessage(topic=topic, key=key, value=value))

    def consume(self, topic: str, timeout: float = 0.1) -> Optional[PipelineMessage]:
        return self.bus.consume(topic, timeout=timeout)


class RealKafkaAdapter(KafkaAdapter):  # pragma: no cover
    def __init__(self, config: PipelineConfig) -> None:
        if not _KAFKA_AVAILABLE:
            raise RuntimeError("confluent_kafka is not installed")
        self.config = config
        self.producer = Producer(
            {
                "bootstrap.servers": config.bootstrap_servers,
                "message.timeout.ms": int(config.produce_timeout_sec * 1000),
                "enable.idempotence": True,
                "acks": "all",
            }
        )
        self.consumer = Consumer(
            {
                "bootstrap.servers": config.bootstrap_servers,
                "group.id": config.group_id,
                "enable.auto.commit": False,
                "auto.offset.reset": "earliest",
                "session.timeout.ms": config.session_timeout_ms,
                "request.timeout.ms": config.request_timeout_ms,
            }
        )
        self._subscribed: set[str] = set()

    def subscribe(self, topics: Iterable[str]) -> None:
        topic_list = list(topics)
        if topic_list:
            self.consumer.subscribe(topic_list)
            self._subscribed.update(topic_list)

    def produce(self, topic: str, key: Optional[str], value: Dict[str, Any]) -> None:
        payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.producer.produce(topic, key=key.encode("utf-8") if key else None, value=payload)
        self.producer.flush()

    def consume(self, topic: str, timeout: float = 0.1) -> Optional[PipelineMessage]:
        if topic not in self._subscribed:
            self.subscribe([topic])
        msg = self.consumer.poll(timeout)
        if msg is None:
            return None
        if msg.error():
            return None
        try:
            value = json.loads(msg.value().decode("utf-8"))
        except Exception:
            value = {"raw": msg.value().decode("utf-8", errors="replace")}
        return PipelineMessage(topic=msg.topic(), key=msg.key().decode("utf-8") if msg.key() else None, value=value)

    def commit(self) -> None:
        self.consumer.commit(asynchronous=False)

    def close(self) -> None:
        self.consumer.close()


class EvidencePipeline:
    def __init__(
        self,
        feature_program: FeatureDSLProgram,
        causal_graph: Optional[OnlineCausalGraphLearner] = None,
        config: Optional[PipelineConfig] = None,
        adapter: Optional[KafkaAdapter] = None,
        decision_threshold: float = 0.5,
        verifier: Optional[EvidenceProvenanceVerifier] = None,
    ) -> None:
        self.feature_program = feature_program
        self.causal_graph = causal_graph or OnlineCausalGraphLearner()
        self.config = config or PipelineConfig()
        self.decision_threshold = float(decision_threshold)
        self.verifier = verifier or EvidenceProvenanceVerifier()
        if adapter is not None:
            self.adapter = adapter
        else:
            if self.config.backend == "memory" or not _KAFKA_AVAILABLE:
                self.adapter = MemoryKafkaAdapter()
            else:
                self.adapter = RealKafkaAdapter(self.config)  # pragma: no cover

    def ingest(self, evidence: Mapping[str, Any]) -> str:
        artifact = EvidenceArtifact.from_dict(evidence)
        key = artifact.evidence_id
        self.adapter.produce(self.config.raw_topic, key=key, value=artifact.to_dict())
        return key

    def process_one(self, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        message = self.adapter.consume(self.config.raw_topic, timeout=timeout)
        if message is None:
            return None

        try:
            artifact = EvidenceArtifact.from_dict(message.value)
            verification_report = self.verifier.verify(artifact)
            context = {
                "data": artifact.data,
                "transport_meta": artifact.transport_meta.to_dict(),
                "integrity": artifact.integrity.to_dict(),
                "verification": verification_report,
                "source": artifact.source,
                "type": artifact.type,
                "tags": artifact.tags,
                "meta": message.value,
            }
            features = self.feature_program.evaluate(context)
            numeric_features = self._feature_vector(features)
            proba = self.causal_graph.predict_proba(numeric_features)
            decision = proba >= self.decision_threshold

            train_result = None
            if "label" in artifact.data:
                train_result = self.causal_graph.update(
                    numeric_features,
                    bool(artifact.data["label"]),
                    sample_weight=float(artifact.data.get("label_weight", 1.0)),
                    source_id=artifact.source,
                    verification_report=verification_report,
                )

            output = {
                "evidence_id": artifact.evidence_id,
                "timestamp": artifact.timestamp,
                "source": artifact.source,
                "type": artifact.type,
                "features": features,
                "numeric_features": numeric_features,
                "verification": verification_report,
                "causal_probability": proba,
                "decision": decision,
                "train_result": train_result,
                "graph_snapshot": self.causal_graph.snapshot(include_causal_graph=False) if self.config.emit_graph_snapshot else None,
            }
            self.adapter.produce(self.config.features_topic, key=artifact.evidence_id, value=output)
            self.adapter.produce(self.config.decisions_topic, key=artifact.evidence_id, value=output)
            if hasattr(self.adapter, "commit"):
                try:
                    self.adapter.commit()  # type: ignore[attr-defined]
                except Exception:
                    pass
            return output
        except Exception as exc:
            dlq = {
                "error": str(exc),
                "message": message.value,
                "message_key": message.key,
                "topic": message.topic,
            }
            self.adapter.produce(self.config.dlq_topic, key=message.key, value=dlq)
            return None

    def process_loop(self, stop_event: Optional[threading.Event] = None) -> None:
        stop_event = stop_event or threading.Event()
        while not stop_event.is_set():
            processed = self.process_one(timeout=self.config.poll_interval_sec)
            if processed is None:
                time.sleep(self.config.poll_interval_sec)

    def _feature_vector(self, features: Mapping[str, Any]) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for key, value in features.items():
            if isinstance(value, bool):
                out[key] = 1.0 if value else 0.0
            else:
                try:
                    out[key] = float(value)
                except Exception:
                    out[key] = 0.0
        return out

    def bus_type(self) -> str:
        return "kafka" if isinstance(self.adapter, RealKafkaAdapter) else "memory"

    def state(self) -> Dict[str, Any]:
        return {
            "bus": self.bus_type(),
            "config": {
                "raw_topic": self.config.raw_topic,
                "features_topic": self.config.features_topic,
                "decisions_topic": self.config.decisions_topic,
                "dlq_topic": self.config.dlq_topic,
            },
            "source_registry": self.verifier.registry.to_dict(),
            "graph": self.causal_graph.snapshot(),
        }
