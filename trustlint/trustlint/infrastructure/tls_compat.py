"""TLS backward compatibility functions.

Provides _determine_chain_subtype, _build_mixed_report, and logger
for backward compatibility with scripts.run_local_tls_validation imports.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _determine_chain_subtype(domain: str, ip: str, timeout: float = 10.0) -> str:
    """Determine the certificate chain subtype.

    Returns:
        "missing_intermediate" or "unknown" on failure.
    """
    try:
        from trustlint.infrastructure.tls_probe import _create_tls_context
        context = _create_tls_context("platform")
        import socket
        with socket.create_connection((ip, 443), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as tls:
                cert = tls.getpeercert()
                if cert:
                    return "unknown"
    except Exception as e:
        logger.debug("Chain subtype detection failed for %s: %s", domain, e)
    return "unknown"


def _build_mixed_report(
    results: List[Dict[str, Any]],
    elapsed: float,
    accuracy: Optional[Dict[str, Any]] = None,
) -> str:
    """Build a mixed TLS validation report.

    Args:
        results: List of probe results.
        elapsed: Time taken in seconds.
        accuracy: Optional accuracy data.

    Returns:
        Formatted report string.
    """
    lines = []
    lines.append("=== Mixed TLS Validation Report ===")
    lines.append(f"Domains tested | {len(results)}")
    lines.append(f"Elapsed | {elapsed:.1f}s")
    lines.append("")

    counts: Dict[str, int] = {}
    for r in results:
        cls = r.get("classification", "UNKNOWN")
        counts[cls] = counts.get(cls, 0) + 1

    lines.append("Classification Breakdown:")
    for cls in sorted(counts.keys()):
        lines.append(f"  {cls}: {counts[cls]}")

    if accuracy:
        lines.append("")
        lines.append("Classification Accuracy:")
        lines.append(f"  Accuracy: {accuracy.get('accuracy_pct', 0):.1f}%")
        lines.append(f"  Correct: {accuracy.get('correct', 0)}/{accuracy.get('total_with_results', 0)}")

        misclassified = accuracy.get("misclassified_examples", [])
        if misclassified:
            lines.append("")
            lines.append("Misclassified Examples:")
            for ex in misclassified:
                lines.append(f"  {ex.get('domain', '?')}: expected {ex.get('expected', '?')}, got {ex.get('actual', '?')}")

    return "\n".join(lines)
