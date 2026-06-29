"""TrustLint — TLS risk analysis library and CLI.

This module provides the public Python API for TrustLint.
For CLI usage, see the `trustlint` command.

Example:
    >>> from trustlint import analyze, analyze_batch
    >>> result = analyze("example.com")
    >>> print(result["final"]["decision"])
    "ALLOW"
"""

from __future__ import annotations

from typing import Any, Dict, List

# Re-export public API from the package-internal analyzer module.
# This does NOT depend on scripts/ — the implementation lives in
# trustlint/analyzer.py and imports heavy dependencies lazily.
from trustlint.analyzer import (
    analyze,
    analyze_batch,
    get_version,
    get_classifications,
)

__version__ = "1.0.0"

__all__ = [
    "analyze",
    "analyze_batch",
    "get_version",
    "get_classifications",
    "__version__",
]
