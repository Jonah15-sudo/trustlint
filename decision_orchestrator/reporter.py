"""Benchmark reporting for the Decision Orchestration Policy.

Generates structured reports comparing orchestrated final decisions
against policy expectations with safety-oriented metrics.
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict

from decision_orchestrator.schema import OrchestratorOutput


class BenchmarkRunResult(TypedDict, total=False):
    """Aggregated benchmark results for one evaluation mode."""

    mode: str
    description: str
    total: int
    exact_matches: int
    safe_mismatches: int
    unsafe_mismatches: int
    under_blocking: int
    over_blocking: int
    probe_limited: int
    decision_distribution: Dict[str, int]
    risk_distribution: Dict[str, int]
    conformance_pct: float
    safety_adjusted_pct: float
    allow_rate: float
    review_rate: float
    deny_rate: float
    category_performance: Dict[str, Dict[str, Any]]
    mismatches: List[Dict[str, Any]]


# Known probe-limited indicators:
# - DNS_FAILURE on a domain expected to be ACCEPTABLE_TLS (transient DNS)
# - VALID_TLS on a domain expected to be SECURITY_RISK (deprecated TLS undetected)
# - VALID_TLS on a domain expected to be DEPRECATED_PROTOCOL_RISK
PROBE_LIMITED_CLASSIFICATION_PAIRS: set = {
    ("DNS_FAILURE", "ACCEPTABLE_TLS"),
    ("VALID_TLS", "SECURITY_RISK"),
    ("VALID_TLS", "DEPRECATED_PROTOCOL_RISK"),
}


def is_probe_limited(classification: str, expected_policy: Optional[str]) -> bool:
    """Check if a mismatch is caused by a probe-level limitation."""
    if expected_policy is None:
        return False
    return (classification, expected_policy) in PROBE_LIMITED_CLASSIFICATION_PAIRS


def classify_mismatch(
    expected_policy: Optional[str],
    final_decision: str,
    classification: str = "",
) -> str:
    """Classify the outcome as exact, safe, unsafe, under_blocking, or over_blocking.

    Expected policy mappings:
      ACCEPTABLE_TLS -> ALLOW
      SECURITY_RISK -> DENY (or REVIEW as safe)
      AVAILABILITY_RISK -> REVIEW (or ALLOW as under_blocking)
      AMBIGUOUS_FAILURE -> REVIEW
      DEPRECATED_PROTOCOL_RISK -> REVIEW/DENY
      CHAIN_TRUST_FAILURE -> REVIEW
      UNKNOWN_RISK -> REVIEW

    Returns one of: "exact", "safe", "unsafe", "under_blocking",
                    "over_blocking", "unknown"
    """
    if expected_policy is None:
        return "unknown"

    expected_decision: str
    if expected_policy == "ACCEPTABLE_TLS":
        expected_decision = "ALLOW"
    elif expected_policy in ("SECURITY_RISK", "DEPRECATED_PROTOCOL_RISK"):
        expected_decision = "DENY"
    elif expected_policy == "AVAILABILITY_RISK":
        expected_decision = "REVIEW"
    elif expected_policy == "AMBIGUOUS_FAILURE":
        expected_decision = "REVIEW"
    elif expected_policy == "CHAIN_TRUST_FAILURE":
        expected_decision = "REVIEW"
    elif expected_policy == "UNKNOWN_RISK":
        expected_decision = "REVIEW"
    else:
        return "unknown"

    if final_decision == expected_decision:
        return "exact"

    # Over-blocking: expected ALLOW but got REVIEW or DENY
    if expected_decision == "ALLOW":
        return "over_blocking"

    # Safe mismatch: expected DENY but got REVIEW (conservative)
    if expected_decision == "DENY" and final_decision == "REVIEW":
        return "safe"

    # Unsafe mismatch: expected DENY but got ALLOW (risk completely missed)
    if expected_decision == "DENY" and final_decision == "ALLOW":
        return "unsafe"

    # Under-blocking: expected REVIEW but got ALLOW
    if expected_decision == "REVIEW" and final_decision == "ALLOW":
        return "under_blocking"

    return "unknown"


def compute_benchmark_results(
    results: List[OrchestratorOutput],
    mode: str,
    description: str,
) -> BenchmarkRunResult:
    """Compute aggregated results from per-domain orchestrator outputs."""
    cat_total: Dict[str, int] = {}
    cat_exact: Dict[str, int] = {}
    cat_safe: Dict[str, int] = {}
    cat_unsafe: Dict[str, int] = {}
    cat_under: Dict[str, int] = {}
    cat_over: Dict[str, int] = {}

    dec_dist: Dict[str, int] = Counter()
    risk_dist: Dict[str, int] = Counter()
    mismatches: List[Dict[str, Any]] = []
    probe_limited = 0

    for r in results:
        domain = r.get("domain", "?")
        classification = r.get("classification", "?")
        expected = r.get("expected_policy")
        final = r.get("final_decision", "REVIEW")
        dec_dist[final] += 1
        risk_dist[r.get("final_risk", "LOW")] += 1

        mismatch_type = classify_mismatch(expected, final, classification)

        # Track probe-limited cases separately
        if mismatch_type != "exact" and is_probe_limited(classification, expected):
            probe_limited += 1

        cat = expected or "UNKNOWN"

        if mismatch_type == "exact":
            cat_exact[cat] = cat_exact.get(cat, 0) + 1
        elif mismatch_type == "safe":
            cat_safe[cat] = cat_safe.get(cat, 0) + 1
        elif mismatch_type == "unsafe":
            cat_unsafe[cat] = cat_unsafe.get(cat, 0) + 1
            mismatches.append({
                "domain": domain,
                "classification": classification,
                "expected": expected,
                "final_decision": final,
                "mismatch_type": "unsafe",
                "probe_limited": is_probe_limited(classification, expected),
            })
        elif mismatch_type == "under_blocking":
            cat_under[cat] = cat_under.get(cat, 0) + 1
            mismatches.append({
                "domain": domain,
                "classification": classification,
                "expected": expected,
                "final_decision": final,
                "mismatch_type": "under_blocking",
                "probe_limited": is_probe_limited(classification, expected),
            })
        elif mismatch_type == "over_blocking":
            cat_over[cat] = cat_over.get(cat, 0) + 1
            mismatches.append({
                "domain": domain,
                "classification": classification,
                "expected": expected,
                "final_decision": final,
                "mismatch_type": "over_blocking",
                "probe_limited": is_probe_limited(classification, expected),
            })

        cat_total[cat] = cat_total.get(cat, 0) + 1

    total = len(results)
    exact = sum(1 for r in results if classify_mismatch(r.get("expected_policy"), r.get("final_decision", "REVIEW"), r.get("classification", "")) == "exact")
    safe = sum(1 for r in results if classify_mismatch(r.get("expected_policy"), r.get("final_decision", "REVIEW"), r.get("classification", "")) == "safe")
    unsafe = sum(1 for r in results if classify_mismatch(r.get("expected_policy"), r.get("final_decision", "REVIEW"), r.get("classification", "")) == "unsafe")
    under = sum(1 for r in results if classify_mismatch(r.get("expected_policy"), r.get("final_decision", "REVIEW"), r.get("classification", "")) == "under_blocking")
    over = sum(1 for r in results if classify_mismatch(r.get("expected_policy"), r.get("final_decision", "REVIEW"), r.get("classification", "")) == "over_blocking")

    conformance_pct = round(exact / max(total, 1) * 100, 1)
    safety_adjusted_pct = round((exact + safe) / max(total, 1) * 100, 1)

    allow_ct = dec_dist.get("ALLOW", 0)
    review_ct = dec_dist.get("REVIEW", 0)
    deny_ct = dec_dist.get("DENY", 0)

    return BenchmarkRunResult(
        mode=mode,
        description=description,
        total=total,
        exact_matches=exact,
        safe_mismatches=safe,
        unsafe_mismatches=unsafe,
        under_blocking=under,
        over_blocking=over,
        probe_limited=probe_limited,
        decision_distribution=dict(dec_dist),
        risk_distribution=dict(risk_dist),
        conformance_pct=conformance_pct,
        safety_adjusted_pct=safety_adjusted_pct,
        allow_rate=round(allow_ct / max(total, 1) * 100, 1),
        review_rate=round(review_ct / max(total, 1) * 100, 1),
        deny_rate=round(deny_ct / max(total, 1) * 100, 1),
        category_performance={},
        mismatches=mismatches,
    )


def generate_report(
    all_results: Dict[str, BenchmarkRunResult],
    output_dir: str,
) -> str:
    """Generate the benchmark report markdown."""
    lines = [
        "# Decision Orchestration Policy Benchmark Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}Z",
        "",
        "---",
        "",
        "## Baseline Definitions",
        "",
        "| Mode | Description |",
        "|---|---|",
    ]

    for mode, result in all_results.items():
        lines.append(f"| {mode} | {result.get('description', '')} |")

    lines.extend([
        "",
        "---",
        "",
        "## Overall Comparison",
        "",
        "| Mode | Conformance | Safety-Adj | Exact | Safe | Unsafe | Under-block | Over-block |",
        "|---|---|---|---|---|---|---|---|",
    ])

    for mode, result in all_results.items():
        lines.append(
            f"| {mode} | {result['conformance_pct']}% | "
            f"{result['safety_adjusted_pct']}% | "
            f"{result['exact_matches']} | {result['safe_mismatches']} | "
            f"{result['unsafe_mismatches']} | {result['under_blocking']} | "
            f"{result['over_blocking']} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Decision Distribution and Rates",
        "",
        "| Mode | ALLOW | REVIEW | DENY | Allow Rate | Review Rate | Deny Rate |",
        "|---|---|---|---|---|---|---|",
    ])

    for mode, result in all_results.items():
        dd = result.get("decision_distribution", {})
        lines.append(
            f"| {mode} | {dd.get('ALLOW', 0)} | {dd.get('REVIEW', 0)} | "
            f"{dd.get('DENY', 0)} | {result['allow_rate']}% | "
            f"{result['review_rate']}% | {result['deny_rate']}% |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Risk Distribution",
        "",
        "| Mode | NONE | LOW | MEDIUM | HIGH | CRITICAL |",
        "|---|---|---|---|---|---|",
    ])

    for mode, result in all_results.items():
        rd = result.get("risk_distribution", {})
        lines.append(
            f"| {mode} | {rd.get('NONE', 0)} | {rd.get('LOW', 0)} | "
            f"{rd.get('MEDIUM', 0)} | {rd.get('HIGH', 0)} | {rd.get('CRITICAL', 0)} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Probe-Limited Cases",
        "",
        "Probe-limited cases are mismatches caused by probe-level limitations:",
        "- DNS_FAILURE on an expected VALID_TLS domain (transient DNS resolution issue)",
        "- VALID_TLS on an expected SECURITY_RISK domain (deprecated TLS not detected)",
        "",
    ])

    total_probe_limited = sum(r.get("probe_limited", 0) for r in all_results.values())
    lines.append(f"**Total probe-limited mismatches across all modes:** {total_probe_limited}")
    lines.append("")

    for mode, result in all_results.items():
        mismatches = result.get("mismatches", [])
        pl = [m for m in mismatches if m.get("probe_limited")]
        if pl:
            lines.append(f"### {mode} ({len(pl)} probe-limited)")
            lines.append("")
            lines.append("| Domain | Classification | Expected | Final | Type |")
            lines.append("|---|---|---|---|---|")
            for m in pl:
                lines.append(f"| {m['domain']} | {m['classification']} | {m['expected']} | {m['final_decision']} | {m['mismatch_type']} |")
            lines.append("")

    if total_probe_limited == 0:
        lines.append("No probe-limited cases found.")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Unsafe Mismatches (expected DENY, got ALLOW)",
        "",
    ])

    unsafe_found = False
    for mode, result in all_results.items():
        mismatches = result.get("mismatches", [])
        unsafe_ms = [m for m in mismatches if m.get("mismatch_type") == "unsafe"]
        if unsafe_ms:
            unsafe_found = True
            lines.append(f"### {mode} ({len(unsafe_ms)} unsafe)")
            lines.append("")
            lines.append("| Domain | Classification | Expected | Final | Probe-Limited |")
            lines.append("|---|---|---|---|---|")
            for m in unsafe_ms:
                lines.append(f"| {m['domain']} | {m['classification']} | {m['expected']} | {m['final_decision']} | {'YES' if m.get('probe_limited') else 'no'} |")
            lines.append("")

    if not unsafe_found:
        lines.append("No unsafe mismatches found.")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Under-blocking Cases (expected REVIEW, got ALLOW)",
        "",
    ])

    under_found = False
    for mode, result in all_results.items():
        mismatches = result.get("mismatches", [])
        under_ms = [m for m in mismatches if m.get("mismatch_type") == "under_blocking"]
        if under_ms:
            under_found = True
            lines.append(f"### {mode} ({len(under_ms)} under-blocking)")
            lines.append("")
            lines.append("| Domain | Classification | Expected | Final | Probe-Limited |")
            lines.append("|---|---|---|---|---|")
            for m in under_ms:
                lines.append(f"| {m['domain']} | {m['classification']} | {m['expected']} | {m['final_decision']} | {'YES' if m.get('probe_limited') else 'no'} |")
            lines.append("")

    if not under_found:
        lines.append("No under-blocking cases found.")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Over-blocking Cases (expected ALLOW, got REVIEW/DENY)",
        "",
    ])

    over_found = False
    for mode, result in all_results.items():
        mismatches = result.get("mismatches", [])
        over_ms = [m for m in mismatches if m.get("mismatch_type") == "over_blocking"]
        if over_ms:
            over_found = True
            lines.append(f"### {mode} ({len(over_ms)} over-blocking)")
            lines.append("")
            lines.append("| Domain | Classification | Expected | Final | Probe-Limited |")
            lines.append("|---|---|---|---|---|")
            for m in over_ms[:10]:
                lines.append(f"| {m['domain']} | {m['classification']} | {m['expected']} | {m['final_decision']} | {'YES' if m.get('probe_limited') else 'no'} |")
            if len(over_ms) > 10:
                lines.append(f"| ... and {len(over_ms) - 10} more | | | | |")
            lines.append("")

    if not over_found:
        lines.append("No over-blocking cases found.")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Semantic Audit Summary",
        "",
        "| Metric | What It Measures |",
        "|---|---|",
        "| **Exact conformance** | Final decision matches expected decision exactly. |",
        "| **Safety-adjusted conformance** | Exact + safe mismatches (conservative REVIEW counted as safe). |",
        "| **Safe mismatch rate** | Expected DENY but got REVIEW (risk flagged, not blocked). |",
        "| **Unsafe mismatch rate** | Expected DENY but got ALLOW (risk completely missed). |",
        "| **Under-blocking rate** | Expected REVIEW but got ALLOW (should have been flagged). |",
        "| **Over-blocking rate** | Expected ALLOW but got REVIEW/DENY (false positive). |",
        "| **Probe-limited count** | Mismatches caused by probe-level limitations (not orchestrator errors). |",
        "",
        "---",
        "",
        "## Limitations",
        "",
        "1. **Probe limitations propagate** through all layers.",
        "2. **No ground truth** -- all evaluations use policy expectations.",
        "3. **OFE is observational only** -- does not affect final decisions.",
        "4. **Safe mismatches are acceptable** -- REVIEW instead of DENY is conservative.",
        "5. **Over-blocking is a usability concern** -- ALLOW expected but got REVIEW/DENY.",
        "6. **Under-blocking is a failure** -- ALLOW when REVIEW or DENY was expected.",
        "7. **Safety-adjusted conformance is not production readiness.**",
        "8. **No production readiness is claimed.**",
        "",
        "_This report is for local evidence gathering only. No production claims are made._",
    ])

    return "\n".join(lines)


def save_results(
    all_results: Dict[str, BenchmarkRunResult],
    output_path: str,
) -> None:
    """Save benchmark results to structured JSON."""
    data = {
        "_metadata": {
            "phase": "Phase 7.5",
            "description": "Decision Orchestration Policy benchmark with safety-oriented metrics",
            "generated": datetime.now(timezone.utc).isoformat() + "Z",
            "spl_core_modified": False,
            "ofe_status": "HOLD_PENDING_REAL_DATA",
        },
        "results": {mode: dict(r) for mode, r in all_results.items()},
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
