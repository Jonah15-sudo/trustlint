from __future__ import annotations

import json
import os
from typing import Any, Dict, List

_HEADER = """# OFE Signal Promotion Readiness

Generated: {date}

Based on {n}-campaign replication study ({challenges} challenges per campaign).

---

## Classification Criteria

| Classification | Definition |
|---|---|
| **PROMOTE** | Signal shows reproducible improvement across ≥70% of campaigns AND effect size |d| ≥ 0.2 OR improvement in ≥50% of campaigns with |d| ≥ 0.5 |
| **HOLD** | Evidence mixed (30–70% replication rate) OR effect size negligible despite high replication |
| **REJECT** | No evidence of improvement (≤30% replication) OR consistent regression across campaigns |

---

## Signal Classifications
"""

_SIGNAL_TEMPLATE = """
### {signal}

**Classification: {classification}**

| Metric | Baseline | OFE | Δ |
|--------|----------|-----|------|
"""


def _effect_size_label(d: float) -> str:
    if abs(d) < 0.2:
        return "negligible"
    if abs(d) < 0.5:
        return "small"
    if abs(d) < 0.8:
        return "medium"
    return "large"


def _classify(replication_rate: float, effect_size: float, improvement_count: int,
              n: int, lower_is_better: bool) -> str:
    rate = replication_rate
    d = abs(effect_size)

    if lower_is_better:
        d = abs(effect_size)

    if rate >= 0.7 and d >= 0.2:
        return "PROMOTE"
    if rate >= 0.5 and d >= 0.5:
        return "PROMOTE"
    if rate < 0.3:
        return "REJECT"
    return "HOLD"


def _classify_weakness(mean_baseline: float, mean_ofe: float, replication_rate: float,
                       effect_size: float) -> str:
    if mean_ofe < mean_baseline:
        d = abs(effect_size)
        # Zero-variance case: all campaigns show identical improvement, d is undefined but
        # improvement is 100% reproducible — promote
        if replication_rate >= 0.7 and (d >= 0.2 or (d == 0.0 and replication_rate == 1.0)):
            return "PROMOTE"
        if replication_rate >= 0.5 and d >= 0.5:
            return "PROMOTE"
        if replication_rate < 0.3:
            return "REJECT"
        return "HOLD"
    else:
        if replication_rate >= 0.7:
            return "REJECT"
        # No change at all (identical means) — REJECT, not HOLD
        if mean_baseline == mean_ofe:
            return "REJECT"
        return "HOLD"


def generate_promotion_readiness(aggregate: Dict[str, Any], output_path: str) -> None:
    from datetime import datetime

    meta = aggregate["metadata"]
    metrics = aggregate["metric_summaries"]
    weakness = aggregate["weakness_summaries"]
    n = meta["campaign_count"]
    challenges = meta.get("challenges_per_campaign", "N/A")

    lines: List[str] = []
    lines.append(_HEADER.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        n=n,
        challenges=challenges,
    ))

    # Metric-level signals
    for m in metrics:
        rep_rate = m["replication_rate"]
        d = m["cohens_d"]
        improvement = m["improvement_count"]
        lower_better = m["lower_is_better"]

        classification = _classify(rep_rate, d, improvement, n, lower_better)
        es_label = _effect_size_label(d)

        lines.append(_SIGNAL_TEMPLATE.format(
            signal=m["metric"],
            classification=classification,
        ))
        lines.append(f"| Mean Δ | {m['mean_delta']:+.4f} | — | — |")
        lines.append(f"| Replication Rate | {rep_rate*100:.0f}% | — | — |")
        lines.append(f"| Cohen's d | {d:+.4f} ({es_label}) | — | — |")

        lines.append("\n**Justification:** {} campaign(s) showed improvement out of {}. "
                     "Effect size is {}. {}".format(
            improvement, n, es_label,
            "Promotion recommended." if classification == "PROMOTE"
            else "Insufficient evidence — hold for more data."
            if classification == "HOLD"
            else "No evidence of reproducible improvement — reject."
        ))

    # Weakness-level signals
    for w in weakness:
        name = w["weakness"]
        rep_rate = w["replication_rate"]
        effect = w.get("effect_size", 0)
        imp = w["campaigns_with_improvement"]
        mean_a = w["mean_a_frequency"]
        mean_b = w["mean_b_frequency"]

        classification = _classify_weakness(mean_a, mean_b, rep_rate, effect)
        es_label = _effect_size_label(effect)

        lines.append(_SIGNAL_TEMPLATE.format(
            signal=f"Weakness: {name}",
            classification=classification,
        ))
        lines.append(f"| Mean Frequency | {mean_a:.1f} | {mean_b:.1f} | {mean_b-mean_a:+.1f} |")
        lines.append(f"| Replication Rate | {rep_rate*100:.0f}% | — | — |")
        lines.append(f"| Cohen's d | {effect:+.4f} ({es_label}) | — | — |")

        lines.append("\n**Justification:** {} campaign(s) showed improvement out of {}. "
                     "{}".format(
            imp, n,
            "Consistent reduction — candidate for conditional promotion."
            if classification == "PROMOTE"
            else "Insufficient replication evidence — hold."
            if classification == "HOLD"
            else "No evidence of improvement — reject."
        ))

    # Summary
    classifications = []
    for m in metrics:
        classifications.append(_classify(m["replication_rate"], m["cohens_d"],
                                         m["improvement_count"], n, m["lower_is_better"]))
    for w in weakness:
        mean_a = w["mean_a_frequency"]
        mean_b = w["mean_b_frequency"]
        classifications.append(
            _classify_weakness(mean_a, mean_b, w["replication_rate"], w.get("effect_size", 0)))

    promote = classifications.count("PROMOTE")
    hold = classifications.count("HOLD")
    reject = classifications.count("REJECT")

    lines.append(f"""
---

## Summary

| Classification | Count |
|---|---|
| **PROMOTE** | {promote} |
| **HOLD** | {hold} |
| **REJECT** | {reject} |

**Overall verdict:** {
    'No signals meet promotion criteria. Further investigation with larger samples needed.'
    if promote == 0
    else f'{promote} signal(s) qualify for promotion. Review justifications above before promoting.'
}
""")

    content = "\n".join(lines)
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote {output_path}")
