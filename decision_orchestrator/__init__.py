"""Decision Orchestration Policy — sidecar that combines adapter + SPL outputs.

Consumes TLS Risk Policy Adapter output and SPL decision output to produce
a transparent final decision (ALLOW / REVIEW / DENY) without modifying SPL Core.

Exports:
    FinalDecision, FinalRisk, DecisionSource: Literal types.
    OrchestratorInput: TypedDict for all input fields.
    OrchestratorOutput: TypedDict for the final output.
    decide: The core orchestration function.
    generate_report: Produce a structured benchmark report.
    SEVERITY_RANK: Dict for comparing severity levels.
"""

from decision_orchestrator.schema import (
    FinalDecision,
    FinalRisk,
    DecisionSource,
    OrchestratorInput,
    OrchestratorOutput,
    SEVERITY_ORDER,
    SEVERITY_RANK,
    OperatingProfile,
)
from decision_orchestrator.policy import decide, orchestrate
from decision_orchestrator.reporter import generate_report, save_results, BenchmarkRunResult

__all__ = [
    "FinalDecision",
    "FinalRisk",
    "DecisionSource",
    "OrchestratorInput",
    "OrchestratorOutput",
    "SEVERITY_ORDER",
    "SEVERITY_RANK",
    "OperatingProfile",
    "decide",
    "orchestrate",
    "generate_report",
    "BenchmarkRunResult",
]
