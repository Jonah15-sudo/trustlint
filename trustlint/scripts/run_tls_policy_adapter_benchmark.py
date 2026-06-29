"""TLS Policy Adapter Benchmark Runner.

The real implementation is in tls_policy_adapter.benchmark.
This file is a thin wrapper for backward compatibility.
"""

from tls_policy_adapter.benchmark import run_benchmark, main

__all__ = [
    "run_benchmark",
    "main",
]
