import warnings
warnings.warn(
    "SPL Core is a research module with no validated production uplift. "
    "Do not use in production decisions. "
    "See docs/SPL_VALIDATION_FINDINGS.md.",
    category=UserWarning,
    stacklevel=2,
)

from .schema import EvidenceArtifact, EvidenceIntegrity, EvidenceTransportMeta, evidence_schema
from .dsl import FeatureDSLProgram, FeatureDSLParser, compile_feature_dsl
from .causal import OnlineCausalGraphLearner
from .kafka_pipeline import EvidencePipeline, PipelineConfig
from .verification import SourceProfile, SourceRegistry, EvidenceProvenanceVerifier, compute_artifact_hash, compute_artifact_signature
from .dashboard import create_app, build_dashboard_html
from .frontier import FrontierExplorer, FrontierChallenge

__all__ = [
    "EvidenceArtifact",
    "EvidenceIntegrity",
    "EvidenceTransportMeta",
    "evidence_schema",
    "FeatureDSLProgram",
    "FeatureDSLParser",
    "compile_feature_dsl",
    "OnlineCausalGraphLearner",
    "EvidencePipeline",
    "PipelineConfig",
    "SourceProfile",
    "SourceRegistry",
    "EvidenceProvenanceVerifier",
    "compute_artifact_hash",
    "compute_artifact_signature",
    "create_app",
    "build_dashboard_html",
    "FrontierExplorer",
    "FrontierChallenge",
]
