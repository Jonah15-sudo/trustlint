"""TrustLint CLI — TLS risk analysis command-line interface.

This module is the official CLI implementation for TrustLint.
It wraps the public Python API from trustlint.analyzer and adds
CLI-specific functionality (argument parsing, formatting, output).

Entry point defined in pyproject.toml:
    trustlint = "scripts.spl_tls_analyze:main"
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TextIO

from trustlint.analyzer import (
    analyze_batch as _analyze_batch,
    analyze_domain as _analyze_domain,
    compute_exit_code as _compute_exit_code,
    get_classifications as _get_classifications,
    get_version as _get_version,
    load_domains_from_file,
    validate_domain_name,
    compute_summary as _compute_summary,
    resolve_classification,
    _RECOMMENDED_ACTIONS,
)
from trustlint.infrastructure.tls_probe import probe_domain

# Re-export constants
_RECOMMENDED_ACTIONS_DICT = _RECOMMENDED_ACTIONS

TOOL_NAME = "trustlint"
__version__ = "1.0.0"

__all__ = [
    # Public API
    "main",
    "parse_args",
    "resolve_targets",
    "analyze_domain",
    "analyze_batch",
    "analyze",
    "compute_exit_code",
    "compute_summary",
    "get_version",
    "get_classifications",
    "load_domains_from_file",
    "validate_domain_name",
    # Formatting
    "format_structured_text",
    "format_json_output",
    "format_markdown_output",
    "format_batch_summary",
    "_progress_indicator",
    "_write_atomic",
    "_build_evidence_artifact",
    "_get_recommended_action",
    "_run_health_check",
    "_format_results",
    # Constants
    "_RECOMMENDED_ACTIONS_DICT",
    "_RECOMMENDED_ACTIONS",
    "TOOL_NAME",
    "__version__",
    "DEPRECATED_TLS_VERSIONS",
    "MAX_INPUT_FILE_SIZE",
    "MAX_DOMAINS",
    "MAX_DOMAIN_LENGTH",
    "REPORT_DIR",
    "DEFAULT_CA_STORE",
    "setup_logging",
    # Stdlib re-exports for backward compatibility
    "sys",
    "logger",
]

logger = logging.getLogger(TOOL_NAME)

# ── Constants ───────────────────────────────────────────────────────────────
MAX_INPUT_FILE_SIZE = 10 * 1024 * 1024
MAX_DOMAINS = 10_000
MAX_DOMAIN_LENGTH = 253
REPORT_DIR = "reports/local_real_validation"
DEFAULT_CA_STORE = "platform"

DEPRECATED_TLS_VERSIONS = frozenset({"tlsv1", "tlsv1.0", "tlsv1.1", "tls1", "tls1.0", "tls1.1"})


# ── Logging ─────────────────────────────────────────────────────────────────

def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the CLI."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


# ── Argument Parsing ────────────────────────────────────────────────────────

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="TrustLint — TLS risk analysis with OCSP revocation detection",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Domain(s) or file path(s) to analyze",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        dest="markdown",
        help="Output results as Markdown",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress progress output",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of concurrent workers (default: 1)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Connection timeout in seconds (default: 10.0)",
    )
    parser.add_argument(
        "--ca-store",
        choices=["platform", "certifi"],
        default="platform",
        help="CA trust store to use (default: platform)",
    )
    parser.add_argument(
        "--profile",
        choices=["balanced", "conservative", "strict"],
        default="balanced",
        help="Decision operating profile (default: balanced)",
    )
    parser.add_argument(
        "--allow-private-targets",
        action="store_true",
        help="Allow scanning private/internal IPs (dangerous)",
    )
    parser.add_argument(
        "--list-classifications",
        action="store_true",
        help="List all classification types and exit",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Write output to file instead of stdout",
    )
    # Backward-compatible aliases
    parser.add_argument(
        "--json-out",
        type=str,
        dest="json_out",
        help="Write JSON output to file (backward-compatible alias for --json + --output)",
    )
    parser.add_argument(
        "--markdown-out",
        type=str,
        dest="markdown_out",
        help="Write Markdown output to file (backward-compatible alias for --markdown + --output)",
    )
    parser.add_argument(
        "--spl-unsafe",
        action="store_true",
        dest="spl_unsafe",
        help="Enable SPL pipeline (backward-compatible, now always available)",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=0.0,
        dest="rate_limit",
        help="Rate limit in seconds between requests (backward-compatible, currently unused)",
    )
    parsed = parser.parse_args(argv)
    # Add singular 'target' alias for backward compatibility
    if parsed.targets:
        parsed.target = parsed.targets[0]
    else:
        parsed.target = ""
    return parsed


def _normalize_args(args: argparse.Namespace) -> argparse.Namespace:
    """Normalize parsed args for backward compatibility."""
    # Add singular 'target' alias for 'targets'
    if not hasattr(args, "target") and hasattr(args, "targets"):
        if args.targets:
            args.target = args.targets[0]
        else:
            args.target = ""
    return args


# ── Formatting ──────────────────────────────────────────────────────────────

def _progress_indicator(current: int = 0, total: int = 0, domain: str = "", quiet: bool = False) -> None:
    """Show progress indicator for a domain."""
    if not quiet:
        sys.stderr.write(f"  Analyzing {domain}...\n")
        sys.stderr.flush()


def _write_atomic(path: str, content: str) -> None:
    """Write content to a file atomically using a temp file."""
    dir_name = os.path.dirname(path) or "."
    with tempfile.NamedTemporaryFile(
        mode="w", dir=dir_name, suffix=".tmp", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        tmp_path = f.name
    os.replace(tmp_path, path)


def format_structured_text(result: Dict[str, Any]) -> str:
    """Format a single domain result as structured text."""
    domain = result.get("domain", "unknown")
    final = result.get("final", {})
    tls_probe = result.get("tls_probe", {})
    policy = result.get("policy_adapter", {})
    spl = result.get("spl", {})

    lines = []
    lines.append(f"Domain: {domain}")
    lines.append(f"  Decision: {final.get('decision', 'UNKNOWN')}")
    lines.append(f"  Risk: {final.get('risk', 'UNKNOWN')}")
    lines.append(f"  Source: {final.get('source', 'unknown')}")

    classification = tls_probe.get("classification", "UNKNOWN")
    lines.append(f"  Classification: {classification}")

    if tls_probe.get("tls_version"):
        lines.append(f"  TLS Version: {tls_probe['tls_version']}")
    if tls_probe.get("resolved_ip"):
        lines.append(f"  Resolved IP: {tls_probe['resolved_ip']}")
    if tls_probe.get("handshake_time_ms"):
        lines.append(f"  Handshake Time: {tls_probe['handshake_time_ms']}ms")

    if tls_probe.get("deprecated_tls_check"):
        lines.append(f"  Deprecated TLS Check: {tls_probe['deprecated_tls_check']}")
    if tls_probe.get("deprecated_tls_detected"):
        lines.append(f"  Deprecated TLS Detected: {tls_probe['deprecated_tls_detected']}")

    if tls_probe.get("ocsp_performed"):
        lines.append(f"  OCSP Status: {tls_probe.get('ocsp_status', 'unknown')}")
        if tls_probe.get("ocsp_error"):
            lines.append(f"  OCSP Error: {tls_probe['ocsp_error']}")

    if tls_probe.get("cert_is_expired"):
        lines.append("  WARNING: Certificate is expired")
    if tls_probe.get("chain_complete") is False:
        lines.append("  WARNING: Certificate chain is incomplete")

    lines.append(f"  [TLS Probe]")
    lines.append(f"  Classification: {classification}")
    if tls_probe.get("tls_version"):
        lines.append(f"  TLS Version: {tls_probe['tls_version']}")
    if tls_probe.get("resolved_ip"):
        lines.append(f"  Resolved IP: {tls_probe['resolved_ip']}")
    if tls_probe.get("handshake_time_ms"):
        lines.append(f"  Handshake Time: {tls_probe['handshake_time_ms']}ms")

    if tls_probe.get("deprecated_tls_check"):
        lines.append(f"  [Deprecated TLS Check]")
        lines.append(f"  Deprecated TLS Check: {tls_probe['deprecated_tls_check']}")
        lines.append(f"  Deprecated TLS Detected: {tls_probe.get('deprecated_tls_detected', False)}")

    lines.append(f"  [Policy Adapter]")
    lines.append(f"  Risk Category: {policy.get('risk_category', 'UNKNOWN')}")
    lines.append(f"  Severity: {policy.get('severity', 'UNKNOWN')}")

    lines.append(f"  [SPL]")
    if spl.get("decision") is not None:
        lines.append(f"  SPL Decision: {spl['decision']}")
        lines.append(f"  SPL Confidence: {spl.get('confidence', 0.0)}")
    else:
        lines.append(f"  SPL: unavailable (adapter-only mode)")

    lines.append(f"  [Decision Reasoning]")
    lines.append(f"  Reason: {final.get('primary_reason', 'N/A')}")
    lines.append(f"  Recommended Action: {final.get('recommended_action', 'N/A')}")

    if final.get("fallback_used"):
        lines.append(f"  Fallback Used: Yes")

    warnings = tls_probe.get("warnings", [])
    if warnings:
        lines.append("  [Limitations]")
        for w in warnings:
            lines.append(f"    - {w}")

    supporting = final.get("supporting_reasons", [])
    if supporting:
        lines.append("  [Recommended Action]")
        for r in supporting:
            lines.append(f"    - {r}")

    return "\n".join(lines)


def format_batch_summary(results: List[Dict[str, Any]], errors: Optional[List[Any]] = None) -> str:
    """Format batch summary as structured text."""
    if errors is None:
        errors = []
    summary = _compute_summary(results, errors)

    lines = []
    lines.append("=== BATCH SUMMARY ===")
    lines.append(f"Total domains: {summary['total_domains']}")
    lines.append(f"  ALLOW: {summary.get('allow', 0)}")
    lines.append(f"  REVIEW: {summary.get('review', 0)}")
    lines.append(f"  DENY: {summary.get('deny', 0)}")
    lines.append(f"  Highest risk: {summary.get('highest_risk', 'NONE')}")
    lines.append(f"  Probe limited: {summary.get('probe_limited', 0)}")
    lines.append(f"  Probe errors: {summary.get('probe_errors', 0)}")
    lines.append(f"  Fallback used: {summary.get('fallback', 0)}")

    deny_domains = [r.get("domain", "?") for r in results if r.get("final", {}).get("decision") == "DENY"]
    if deny_domains:
        lines.append(f"\n  Immediate Action Required:")
        for d in deny_domains:
            lines.append(f"    - {d}")

    review_domains = [r.get("domain", "?") for r in results if r.get("final", {}).get("decision") == "REVIEW"]
    if review_domains:
        lines.append(f"\n  Manual Review:")
        for d in review_domains:
            lines.append(f"    - {d}")

    if errors:
        lines.append(f"\n  Failed Domains: {len(errors)}")
        for err in errors:
            if isinstance(err, dict):
                lines.append(f"    - {err.get('domain', '?')}: [{err.get('error_code', '?')}] {err.get('error_message', '?')}")
            else:
                lines.append(f"    - {err}")

    # Probe limitations section
    probe_limited_domains = [r.get("domain", "?") for r in results if r.get("tls_probe", {}).get("is_probe_limited")]
    if probe_limited_domains:
        lines.append(f"\n  Probe Limitations:")
        for d in probe_limited_domains:
            lines.append(f"    - {d}")

    return "\n".join(lines)


def format_json_output(results: List[Dict[str, Any]], errors: Optional[List[Any]] = None) -> str:
    """Format results as JSON."""
    if errors is None:
        errors = []
    # Handle backward-compatible profile string argument
    if errors and isinstance(errors, str):
        errors = []
    summary = _compute_summary(results, errors)

    # Compute spl_active from results
    spl_active = any(r.get("spl_active", False) for r in results)

    output = {
        "metadata": {
            "tool": TOOL_NAME,
            "version": __version__,
            "production_ready": False,
            "scope": "local-only",
            "spl_active": spl_active,
            "profile": results[0].get("profile", "balanced") if results else "balanced",
        },
        "summary": summary,
        "results": results,
    }
    if errors:
        output["errors"] = errors
    return json.dumps(output, indent=2, default=str)


def format_markdown_output(results: List[Dict[str, Any]], errors: Optional[List[Any]] = None) -> str:
    """Format results as Markdown."""
    if errors is None:
        errors = []
    # Handle backward-compatible profile string argument
    if errors and isinstance(errors, str):
        errors = []
    summary = _compute_summary(results, errors)

    # Compute spl_active from results
    spl_active = any(r.get("spl_active", False) for r in results)

    lines = []
    lines.append(f"# TrustLint Analysis Report")
    lines.append(f"")
    lines.append(f"## Executive Summary")
    lines.append(f"")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    lines.append(f"**Tool:** {TOOL_NAME} v{__version__}")
    lines.append(f"**Production Ready:** No — Not production ready")
    lines.append(f"")
    lines.append(f"## Summary")
    lines.append(f"")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total domains | {summary['total_domains']} |")
    lines.append(f"| ALLOW | {summary.get('allow', 0)} |")
    lines.append(f"| REVIEW | {summary.get('review', 0)} |")
    lines.append(f"| DENY | {summary.get('deny', 0)} |")
    lines.append(f"| Highest risk | {summary.get('highest_risk', 'NONE')} |")
    lines.append(f"| Probe limited | {summary.get('probe_limited', 0)} |")
    lines.append(f"| Probe errors | {summary.get('probe_errors', 0)} |")
    lines.append(f"| Fallback used | {summary.get('fallback', 0)} |")
    lines.append(f"")

    if spl_active:
        lines.append(f"> **SPL Core active** — SPL pipeline was used for this analysis.")
        lines.append(f"")

    lines.append(f"## Full Per-Domain Results")
    lines.append(f"")

    for result in results:
        domain = result.get("domain", "unknown")
        final = result.get("final", {})
        tls_probe = result.get("tls_probe", {})
        decision = final.get("decision", "UNKNOWN")
        risk = final.get("risk", "UNKNOWN")
        classification = tls_probe.get("classification", "UNKNOWN")

        lines.append(f"### {domain}")
        lines.append(f"")
        lines.append(f"- **Decision:** {decision}")
        lines.append(f"- **Risk:** {risk}")
        lines.append(f"- **Classification:** {classification}")
        lines.append(f"- **Reason:** {final.get('primary_reason', 'N/A')}")
        lines.append(f"- **Recommended Action:** {final.get('recommended_action', 'N/A')}")

        if final.get("fallback_used"):
            lines.append(f"- **Fallback:** Fallback ALLOW (adapter policy)")
            lines.append(f"  - This domain was allowed via fallback")

        if tls_probe.get("tls_version"):
            lines.append(f"- **TLS Version:** {tls_probe['tls_version']}")
        if tls_probe.get("resolved_ip"):
            lines.append(f"- **Resolved IP:** {tls_probe['resolved_ip']}")
        if tls_probe.get("ocsp_performed"):
            lines.append(f"- **OCSP Status:** {tls_probe.get('ocsp_status', 'unknown')}")

        warnings = tls_probe.get("warnings", [])
        if warnings:
            lines.append(f"")
            lines.append(f"### Limitations")
            lines.append(f"")
            for w in warnings:
                lines.append(f"- {w}")

        lines.append(f"")

    lines.append(f"---")
    lines.append(f"")
    lines.append(f"*This report was generated by TrustLint v{__version__}. "
                 f"Results are based on local TLS probing and do not guarantee "
                 f"production readiness.*")
    lines.append(f"")

    if errors:
        lines.append(f"## Errors")
        lines.append(f"")
        for err in errors:
            if isinstance(err, dict):
                lines.append(f"- **{err.get('domain', '?')}:** [{err.get('error_code', '?')}] {err.get('error_message', '?')}")
            else:
                lines.append(f"- {err}")
        lines.append(f"")

    return "\n".join(lines)


# ── Analysis Functions ──────────────────────────────────────────────────────

def analyze_domain(
    domain: str,
    profile: str = "balanced",
    timeout: float = 10.0,
    ca_store: str = "platform",
    allow_private_targets: bool = False,
    spl_pipeline: Any = None,
) -> Dict[str, Any]:
    """Analyze a single domain (wrapper around trustlint.analyzer)."""
    return _analyze_domain(
        domain,
        profile=profile,
        timeout=timeout,
        ca_store=ca_store,
        allow_private_targets=allow_private_targets,
        spl_pipeline=spl_pipeline,
    )


def analyze_batch(
    domains: List[str],
    profile: str = "balanced",
    timeout: float = 10.0,
    ca_store: str = "platform",
    max_workers: int = 1,
    allow_private_targets: bool = False,
) -> Dict[str, Any]:
    """Analyze multiple domains (wrapper around trustlint.analyzer)."""
    return _analyze_batch(
        domains,
        profile=profile,
        timeout=timeout,
        ca_store=ca_store,
        max_workers=max_workers,
        allow_private_targets=allow_private_targets,
    )


def compute_exit_code(results: List[Dict[str, Any]]) -> int:
    """Compute exit code from results."""
    return _compute_exit_code(results)


def compute_summary(results: List[Dict[str, Any]], errors: Optional[List[str]] = None) -> Dict[str, Any]:
    """Compute summary statistics."""
    return _compute_summary(results, errors)


def get_version() -> str:
    """Return the version string."""
    return _get_version()


def get_classifications() -> List[str]:
    """Return list of all classification types."""
    return _get_classifications()


def resolve_targets(target: str) -> List[str]:
    """Resolve a target to a list of domains."""
    if os.path.isfile(target):
        return load_domains_from_file(target)
    return [target.strip()]


def _build_evidence_artifact(domain: str, probe_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build an evidence artifact from probe results."""
    from uuid import uuid4
    tls_info = probe_result.get("tls") or {}
    classification = probe_result.get("classification", "")
    cert_not_expired = tls_info.get("cert_is_expired") is not True
    chain_complete = tls_info.get("cert_chain_complete") is not False

    if classification in ("TIMEOUT",):
        status = "timeout"
    elif classification in ("CONNECTION_ERROR", "DNS_FAILURE"):
        status = "error"
    elif classification in ("TLS_HANDSHAKE_FAILURE",):
        status = "partial"
    else:
        status = "ok"

    return {
        "evidence_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": f"tls_probe:{domain}",
        "type": "tls_certificate",
        "data": {
            "valid": cert_not_expired and chain_complete,
            "expiry_days": tls_info.get("cert_expiry_days", 0) or 0,
            "headers": {
                "hsts": None,
                "csp": None,
                "hsts_checked": False,
                "csp_checked": False,
            },
        },
        "transport_meta": {
            "status": status,
            "latency_ms": float(tls_info.get("handshake_time_ms", 0) or 0),
        },
        "tags": [],
        "version": "v7",
    }


def _run_health_check() -> int:
    """Run a basic health check. Returns 0 if OK, 1 if issues found."""
    issues = 0
    try:
        import ssl
        if not hasattr(ssl, "PROTOCOL_TLS_CLIENT"):
            issues += 1
    except ImportError:
        issues += 1

    if sys.version_info < (3, 10):
        issues += 1

    return issues


def _get_recommended_action(classification: str, final_decision: str) -> str:
    """Get recommended action for a classification."""
    if final_decision == "ALLOW":
        return _RECOMMENDED_ACTIONS_DICT.get("VALID_TLS", "No action required.")
    return _RECOMMENDED_ACTIONS_DICT.get(
        classification,
        "Review the domain manually — no specific automated recommendation available.",
    )


def _format_results(
    results: List[Dict[str, Any]],
    errors: List[Dict[str, Any]],
    args: argparse.Namespace,
) -> str:
    """Format results based on output mode."""
    if args.json or args.json_out:
        return format_json_output(results, errors)
    elif args.markdown or args.markdown_out:
        return format_markdown_output(results, errors)
    else:
        parts = []
        for r in results:
            parts.append(format_structured_text(r))
        if errors:
            parts.append("\n=== Errors ===")
            for err in errors:
                parts.append(f"  [{err.get('error_code', '?')}] {err.get('domain', '?')}: {err.get('error_message', '?')}")
        if len(results) > 1:
            parts.append("")
            parts.append(format_batch_summary(results, errors))
        return "\n".join(parts)


# ── Public Python API (re-exported from scripts wrapper) ────────────────────

from trustlint.analyzer import analyze as _analyze_public  # noqa: E402

analyze = _analyze_public  # Public alias for single-domain analysis (with validation)


# ── Main Entry Point ────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    args = parse_args(argv)
    args = _normalize_args(args)

    if args.version:
        print(f"{TOOL_NAME} v{__version__}")
        return 0

    if args.list_classifications:
        print(f"{TOOL_NAME} — Registered TLS classifications: {len(_get_classifications())}")
        for cls in _get_classifications():
            print(cls)
        return 0

    if not args.targets:
        print("Error: No targets specified", file=sys.stderr)
        print("Usage: trustlint <domain> [domain ...]", file=sys.stderr)
        return 4

    setup_logging(verbose=args.verbose)

    # Resolve all targets to domains
    all_domains: List[str] = []
    for target in args.targets:
        try:
            resolved = resolve_targets(target)
            all_domains.extend(resolved)
        except (ValueError, FileNotFoundError) as e:
            print(f"Error: {e}", file=sys.stderr)
            return 4

    if not all_domains:
        print("Error: No valid domains to analyze", file=sys.stderr)
        return 4

    # Determine output file
    output_file = args.output or args.json_out or args.markdown_out

    # Analyze
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    if len(all_domains) == 1:
        try:
            r = analyze_domain(
                all_domains[0],
                profile=args.profile,
                timeout=args.timeout,
                ca_store=args.ca_store,
                allow_private_targets=args.allow_private_targets,
            )
            results.append(r)
        except Exception as e:
            from trustlint.infrastructure.error_codes import get_error_code
            code = get_error_code(e)
            errors.append({
                "domain": all_domains[0],
                "error_code": code.value,
                "error_message": str(e),
                "error_description": code.name,
            })
    else:
        batch_result = analyze_batch(
            all_domains,
            profile=args.profile,
            timeout=args.timeout,
            ca_store=args.ca_store,
            max_workers=args.workers,
            allow_private_targets=args.allow_private_targets,
        )
        results = batch_result.get("results", [])
        errors = batch_result.get("errors", [])

    # Format and output
    output = _format_results(results, errors, args)

    if output_file:
        _write_atomic(output_file, output)
    else:
        print(output)

    return compute_exit_code(results)


if __name__ == "__main__":
    sys.exit(main())
