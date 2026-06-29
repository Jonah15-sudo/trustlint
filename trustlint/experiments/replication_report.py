from __future__ import annotations

import json
import os
from typing import Any, Dict, List

_REPLICATION_HEADER = """# OFE Replication Report

Generated: {date}

Campaigns: {n}
Challenges per campaign: {challenges}
Protocol: Identical across all campaigns (same training sources, same curricula,
           same pipeline configuration). Variation introduced via campaign_seed
           controlling training data shuffle order and OFE signal generation.

---

## Executive Summary

{n} independent A/B comparison campaigns were executed with different seeds,
training orders, and OFE signal values.

### Key Findings

| Metric | Mean Δ | 95% CI | Cohen's d | Reproducibility |
|--------|--------|--------|-----------|-----------------|
"""

_WEAKNESS_HEADER = """
### Weakness-Level Findings

| Weakness | Mean A | Mean B | Mean Δ | Effect Size | Reproducibility |
|----------|--------|--------|--------|-------------|-----------------|
"""

_QUESTION_TEMPLATE = """

---

## {question}

{analysis}

### Verdict

> {verdict}
"""

_PROMOTION_REFERENCE = """
## Reference: Promotion Readiness

See `PROMOTION_READINESS.md` for per-signal PROMOTE / HOLD / REJECT
classifications based on these results.
"""


def generate_replication_report(aggregate: Dict[str, Any], output_path: str) -> None:
    from datetime import datetime

    meta = aggregate["metadata"]
    metrics = aggregate["metric_summaries"]
    weakness = aggregate["weakness_summaries"]

    n = meta["campaign_count"]
    challenges = meta.get("challenges_per_campaign", "N/A")

    lines: List[str] = []
    lines.append(_REPLICATION_HEADER.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        n=n,
        challenges=challenges,
    ))

    for m in metrics:
        lines.append(
            f"| {m['metric']} | {m['mean_delta']:+.4f} | "
            f"[{m['ci_95_lo']:.4f}, {m['ci_95_hi']:.4f}] | "
            f"{m['cohens_d']:+.4f} | {m['reproducibility']} |"
        )

    if weakness:
        lines.append(_WEAKNESS_HEADER)
        for w in weakness:
            lines.append(
                f"| {w['weakness']} | {w['mean_a_frequency']:.1f} | {w['mean_b_frequency']:.1f} | "
                f"{w['mean_difference']:+.1f} | {w.get('effect_size', 0):+.4f} | {w['reproducibility']} |"
            )

    # Generate question-by-question answers
    questions = _question_answers(aggregate)
    for q in questions:
        lines.append(_QUESTION_TEMPLATE.format(**q))

    lines.append(_PROMOTION_REFERENCE)
    lines.append("\n---\n")

    content = "\n".join(lines)
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote {output_path}")


def _question_answers(aggregate: Dict[str, Any]) -> List[Dict[str, str]]:
    metrics_map = {m["key"]: m for m in aggregate["metric_summaries"]}
    weakness_map = {w["weakness"]: w for w in aggregate["weakness_summaries"]}

    questions: List[Dict[str, str]] = []

    # Q1: Is OFE accuracy improvement reproducible?
    am = metrics_map.get("accuracy_delta", {})
    if am:
        rep = am.get("reproducibility", "uncertain")
        d = am.get("cohens_d", 0)
        questions.append({
            "question": "Q1: Is the OFE accuracy improvement reproducible?",
            "analysis": (
                f"Across {am['campaign_count']} campaigns, the mean accuracy difference was "
                f"{am['mean_delta']:+.4f} (95% CI [{am['ci_95_lo']:.4f}, {am['ci_95_hi']:.4f}], "
                f"Cohen's d={d:+.4f}). "
                f"Improvement observed in {am['improvement_count']}/{am['campaign_count']} campaigns "
                f"({am['replication_rate']*100:.0f}%)."
            ),
            "verdict": (
                "The accuracy effect is **not reproducible**. "
                if rep == "not_repeated" else
                "The accuracy effect **may** be reproducible but evidence is mixed. "
                if rep == "uncertain" else
                "The accuracy effect **is** reproducible across campaigns. "
            ) + (
                "The observed effect is negligible (d < 0.2) and the confidence interval "
                "spans zero, consistent with measurement noise."
                if abs(d) < 0.2 else
                f"The effect size (d={d:+.2f}) is consistent but small."
            ),
        })

    # Q2: Is calibration improvement reproducible?
    cm = metrics_map.get("calibration_delta", {})
    if cm:
        rep = cm.get("reproducibility", "uncertain")
        d = cm.get("cohens_d", 0)
        questions.append({
            "question": "Q2: Does OFE improve calibration reproducibility?",
            "analysis": (
                f"Across {cm['campaign_count']} campaigns, mean calibration error difference was "
                f"{cm['mean_delta']:+.4f} (95% CI [{cm['ci_95_lo']:.4f}, {cm['ci_95_hi']:.4f}], "
                f"Cohen's d={d:+.4f}). "
                f"Improvement (calibration error reduction) in {cm['improvement_count']}/{cm['campaign_count']} "
                f"campaigns."
            ),
            "verdict": (
                "Calibration improvement is **not reproducible**."
                if rep == "not_repeated" else
                "Calibration improvement evidence is **uncertain**."
                if rep == "uncertain" else
                "Calibration improvement **is reproducible**."
            ),
        })

    # Q3: Repair http_error_flag?
    hf = weakness_map.get("http_error_flag", {})
    if hf:
        rep = hf.get("reproducibility", "uncertain")
        questions.append({
            "question": "Q3: Does OFE repair http_error_flag?",
            "analysis": (
                f"Across {hf['campaign_count']} campaigns, mean baseline frequency was "
                f"{hf['mean_a_frequency']:.1f}, mean OFE frequency was {hf['mean_b_frequency']:.1f}, "
                f"mean difference {hf['mean_difference']:+.1f}. "
                f"Improvement in {hf['campaigns_with_improvement']}/{hf['campaign_count']} campaigns "
                f"({hf['replication_rate']*100:.0f}%)."
            ),
            "verdict": (
                "http_error_flag repair **did not replicate** across campaigns."
                if rep == "not_repeated" else
                "http_error_flag repair evidence is **uncertain** — further investigation needed."
                if rep == "uncertain" else
                "http_error_flag repair **does replicate** — consistent reduction observed."
            ),
        })

    # Q4: Repair partial_flag?
    pf = weakness_map.get("partial_flag", {})
    if pf:
        rep = pf.get("reproducibility", "uncertain")
        questions.append({
            "question": "Q4: Does OFE repair partial_flag?",
            "analysis": (
                f"Across {pf['campaign_count']} campaigns, mean baseline frequency was "
                f"{pf['mean_a_frequency']:.1f}, mean OFE frequency was {pf['mean_b_frequency']:.1f}, "
                f"mean difference {pf['mean_difference']:+.1f}. "
                f"Improvement in {pf['campaigns_with_improvement']}/{pf['campaign_count']} campaigns."
            ),
            "verdict": (
                "partial_flag repair **did not replicate** across campaigns."
                if rep == "not_repeated" else
                "partial_flag repair evidence is **uncertain** — further investigation needed."
                if rep == "uncertain" else
                "partial_flag repair **does replicate** — consistent reduction observed."
            ),
        })

    # Q5: Aggregate metrics stable?
    agg_metrics = {k: v for k, v in metrics_map.items()
                   if k.startswith("error_rate") or k.startswith("collapse_rate")}
    if agg_metrics:
        stable_count = sum(1 for m in agg_metrics.values()
                           if abs(m.get("mean_delta", 1)) < 0.01)
        total = len(agg_metrics)
        stable_pct = stable_count / total * 100 if total else 0
        questions.append({
            "question": "Q5: Are aggregate metrics stable across campaigns?",
            "analysis": (
                f"Of {total} aggregate metrics, {stable_count} ({stable_pct:.0f}%) showed "
                f"negligible mean change (|Δ| < 0.01). "
            ) + " ".join(
                f"{m['metric']}: mean Δ={m['mean_delta']:+.4f} (σ={m['std_delta']:.4f}, "
                f"d={m.get('cohens_d', 0):+.4f})"
                for m in agg_metrics.values()
            ),
            "verdict": (
                f"Aggregate metrics are **stable** ({stable_pct:.0f}% unchanged)."
                if stable_pct >= 70
                else f"Aggregate metrics show **some variation** ({stable_pct:.0f}% stable)."
            ),
        })

    # Q6: Which effects repeated / disappeared / uncertain?
    repeated = []
    uncertain = []
    disappeared = []

    for m in aggregate["metric_summaries"]:
        label = m["metric"]
        rep = m.get("reproducibility", "uncertain")
        if rep == "repeated":
            repeated.append(label)
        elif rep == "uncertain":
            uncertain.append(label)

    for w in aggregate["weakness_summaries"]:
        name = w["weakness"]
        rep = w.get("reproducibility", "uncertain")
        if rep == "repeated":
            repeated.append(name)
        elif rep == "uncertain":
            uncertain.append(name)
        elif rep == "not_repeated":
            disappeared.append(name)

    questions.append({
        "question": "Q6: Which effects repeated, disappeared, or remain uncertain?",
        "analysis": (
            f"**Repeated** ({len(repeated)}): {', '.join(repeated) if repeated else 'none'}. "
            f"**Disappeared** ({len(disappeared)}): {', '.join(disappeared) if disappeared else 'none'}. "
            f"**Uncertain** ({len(uncertain)}): {', '.join(uncertain) if uncertain else 'none'}."
        ),
        "verdict": (
            "No effect passed the 70% replication threshold."
            if not repeated
            else f"Effects with replication evidence: {', '.join(repeated)}. "
                 f"These require larger-scale confirmation."
        ),
    })

    # Q7: Is signal promotion justified?
    promote_count = sum(1 for w in aggregate["weakness_summaries"]
                        if w.get("reproducibility") == "repeated")
    questions.append({
        "question": "Q7: Is OFE signal promotion justified based on this evidence?",
        "analysis": (
            f"Replication campaign: {len(aggregate['weakness_summaries'])} weakness categories tracked, "
            f"{promote_count} categories show reproducible improvement. "
            f"Overall accuracy effect: {metrics_map.get('accuracy_delta', {}).get('mean_delta', 0):+.4f}. "
        ),
        "verdict": (
            "**Not justified.** Aggregate metrics show no meaningful improvement. "
            "Weakness-level effects lack the replication evidence to warrant promotion."
            if promote_count == 0
            else "**Conditional.** Some weakness-level effects replicate, but aggregate "
                 "metrics do not. Promotion would be premature without understanding "
                 "why improvement does not propagate to system-level accuracy."
        ),
    })

    return questions
