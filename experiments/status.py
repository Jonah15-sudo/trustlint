from __future__ import annotations

"""
SPL v7.1 OFE status guard.

OFE structural signals remain HOLD_PENDING_REAL_DATA until a real TLS dataset
(5000+ rows, >=10% positive labels) passes validation via RealValidationRunner.

No promotion path may run from samples, fixtures, or generated data.
"""

OFE_STATUS: str = "HOLD_PENDING_REAL_DATA"

DATASET_GATE_NOTE: str = (
    "No real TLS dataset has been provided. "
    "OFE structural signals remain HOLD_PENDING_REAL_DATA. "
    "No promotion path may run from samples, fixtures, or generated data. "
    "Provide a real 5000+ row TLS dataset with >=10% positive labels "
    "via REAL_TLS_DATASET env var or direct path to RealValidationRunner."
)


def check_ofe_status() -> str:
    return OFE_STATUS


def check_dataset_gate(dataset_path: str | None = None) -> str:
    if dataset_path:
        return f"Dataset provided: {dataset_path}. OFE status pending validation."
    return DATASET_GATE_NOTE
