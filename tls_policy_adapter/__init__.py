"""TLS Risk Policy Adapter — a sidecar for structured risk evidence.

Maps raw TLS probe classifications into deterministic risk categories,
severities, failure families, and action hints. Does not modify SPL Core,
does not learn from data, does not read expectation files.

Exports:
    TLSClassification: Literal type of all valid classification strings.
    TLSSeverity: Literal type of severity levels.
    TLSRiskCategory: Literal type of risk categories.
    TLSFailureFamily: Literal type of failure families.
    TLSClassification: Literal type of all valid classification strings.
    TLSPolicyEvidence: Structured evidence dataclass.
    RISK_MAP: Deterministic classification-to-evidence mapping.
    SEVERITY_ORDER: Ordered list of severity levels.
    classify_risk: Map a single classification to TLSPolicyEvidence.
    enrich_evidence: Produce a dict of enriched fields for injection.
    EnrichedEvidence: TypedDict for enriched evidence dict.
    AdapterBenchmarkResult: TypedDict for per-domain benchmark comparison.
"""

from tls_policy_adapter.schema import (
    TLSClassification,
    TLSSeverity,
    TLSRiskCategory,
    TLSFailureFamily,
    TLSPolicyEvidence,
    RISK_MAP,
    SEVERITY_ORDER,
)
from tls_policy_adapter.classifications import (
    ALL_CLASSIFICATIONS,
    DEPRECATED_TLS_VERSIONS,
    DEPRECATED_TLS_CLASSIFICATION,
    CLASSIFICATION_SEVERITY,
    CLASSIFICATION_RISK_CATEGORY,
    CLASSIFICATION_TO_OVERALL_STATUS,
    get_classification_severity,
    get_classification_risk_category,
    is_valid_classification,
    is_deprecated_tls_version,
)
from tls_policy_adapter.risk_policy import (
    classify_risk,
    classify_risk_from_probe,
    SEVERITY_RANK,
)
from tls_policy_adapter.evidence_adapter import (
    enrich_evidence,
    enrich_evidence_artifact,
    EnrichedEvidence,
    AdapterBenchmarkResult,
)

__all__ = [
    "TLSClassification",
    "TLSSeverity",
    "TLSRiskCategory",
    "TLSFailureFamily",
    "TLSPolicyEvidence",
    "RISK_MAP",
    "SEVERITY_ORDER",
    "ALL_CLASSIFICATIONS",
    "DEPRECATED_TLS_VERSIONS",
    "DEPRECATED_TLS_CLASSIFICATION",
    "CLASSIFICATION_SEVERITY",
    "CLASSIFICATION_RISK_CATEGORY",
    "CLASSIFICATION_TO_OVERALL_STATUS",
    "get_classification_severity",
    "get_classification_risk_category",
    "is_valid_classification",
    "is_deprecated_tls_version",
    "classify_risk",
    "classify_risk_from_probe",
    "SEVERITY_RANK",
    "enrich_evidence",
    "enrich_evidence_artifact",
    "EnrichedEvidence",
    "AdapterBenchmarkResult",
]
