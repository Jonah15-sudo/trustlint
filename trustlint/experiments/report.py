from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict


_SIGNIFICANCE_FLOOR = 0.01


def _sig(val: float, label: str = "improvement") -> str:
    if abs(val) < _SIGNIFICANCE_FLOOR:
        return "Insufficient evidence."
    return f"{label} detected (Δ = {val:+.4f})."


class ExperimentReport:
    def __init__(self, result: Dict[str, Any], raw_dir: str = "experiments/raw_runs") -> None:
        self.result = result
        self.raw_dir = raw_dir
        os.makedirs(raw_dir, exist_ok=True)

    def save_json(self, path: str = "experiment_results.json") -> str:
        full = os.path.join(self.raw_dir, path)
        with open(full, "w", encoding="utf-8") as f:
            json.dump(self.result, f, indent=2, ensure_ascii=False)
        return full

    def save_markdown(self, path: str = "comparison_report.md") -> str:
        full = os.path.join(self.raw_dir, path)
        r = self.result
        b = r["baseline"]
        o = r["ofe"]
        c = r["comparison"]
        m = r["metadata"]

        lines: list[str] = []
        lines.append("# OFE Experimental Campaign — Comparison Report")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
        lines.append("")
        lines.append("## Protocol")
        lines.append("")
        lines.append(f"- Condition A: {m['condition_a']}")
        lines.append(f"- Condition B: {m['condition_b']}")
        lines.append(f"- Training items: {m['training_items']}")
        lines.append(f"- OFE signals injected: {m['ofe_signals']}")
        lines.append(f"- Curricula: {', '.join(m['curricula'])}")
        lines.append(f"- Total challenges evaluated: {m['total_challenges']}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 1. What improved?")
        lines.append("")

        improvements: list[str] = []
        unchanged: list[str] = []
        regressions: list[str] = []

        comps = [
            ("Accuracy", c["accuracy"]),
            ("Calibration Error", c["calibration_error"]),
            ("Error Rate", c["error_rate"]),
            ("Collapse Rate", c["collapse_rate"]),
            ("Total Weaknesses", c["total_weaknesses"]),
        ]
        for label, comp in comps:
            diff = comp["absolute_difference"]
            dir_label = comp["direction"]
            if dir_label == "improvement":
                improvements.append(f"- **{label}**: Δ = {diff:+.4f} (A: {comp['A']}, B: {comp['B']})")
            elif dir_label == "regression":
                regressions.append(f"- **{label}**: Δ = {diff:+.4f} (A: {comp['A']}, B: {comp['B']})")
            else:
                unchanged.append(f"- **{label}**: Δ = {diff:+.4f} (A: {comp['A']}, B: {comp['B']})")

        for line in improvements:
            lines.append(line)
        if not improvements:
            lines.append("- No improvements detected.")

        lines.append("")
        lines.append("## 2. What did not improve?")
        lines.append("")
        for line in unchanged:
            lines.append(line)
        if not unchanged:
            lines.append("- All metrics either improved or regressed.")
        lines.append("")
        lines.append("## 3. What regressed?")
        lines.append("")
        for line in regressions:
            lines.append(line)
        if not regressions:
            lines.append("- No regressions detected.")
        lines.append("")
        lines.append("## 4. Which weaknesses changed?")
        lines.append("")
        lines.append("| Weakness | A Freq | B Freq | A %total | B %total | Δ Freq | Δ %pct | Interpretation |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for wc in c["weakness_level"]:
            lines.append(
                f"| {wc['weakness']} | {wc['a_frequency']} | {wc['b_frequency']} "
                f"| {wc['a_percent']}% | {wc['b_percent']}% "
                f"| {wc['absolute_difference']:+d} | {wc['percentage_point_difference']:+.1f}% "
                f"| {wc['interpretation']} |"
            )

        lines.append("")
        lines.append("### Statistical Notes")
        lines.append("")
        for wc in c["weakness_level"]:
            lines.append(f"- **{wc['weakness']}**: "
                         f"A count = {wc['a_frequency']} / {b['total_weaknesses']} total weaknesses; "
                         f"B count = {wc['b_frequency']} / {o['total_weaknesses']} total weaknesses. "
                         + _sig(wc['absolute_difference'], "reduction" if wc['interpretation'] == "improvement" else "increase"))

        lines.append("")
        lines.append("## 5. Which capability boundaries changed?")
        lines.append("")
        cb = c["capability_boundary"]
        ba = b["capability_boundary"]
        bo = o["capability_boundary"]
        lines.append(f"- **A fraction below confidence threshold ({ba['confidence_threshold']})**: {ba['fraction_below']:.4f}")
        lines.append(f"- **B fraction below threshold**: {bo['fraction_below']:.4f}")
        lines.append(f"- **Delta**: {cb['delta_fraction_below']:+.4f}")
        lines.append("- A boundary crossings: " + (", ".join(
            f"difficulty={x['difficulty']} ({x['direction']})" for x in ba["crossings"]
        ) if ba["crossings"] else "none"))
        lines.append("- B boundary crossings: " + (", ".join(
            f"difficulty={x['difficulty']} ({x['direction']})" for x in bo["crossings"]
        ) if bo["crossings"] else "none"))

        lines.append("")
        lines.append("### Difficulty Distribution")
        lines.append("")
        lines.append("| Bucket | Range | A Accuracy | B Accuracy | Δ |")
        lines.append("|---|---|---|---|---|")
        for bucket in sorted(c["difficulty_distribution"].keys()):
            dc = c["difficulty_distribution"][bucket]
            da = b["difficulty_distribution"][bucket]
            lines.append(
                f"| {bucket} | {da['range']} "
                f"| {dc['A_accuracy']:.4f} | {dc['B_accuracy']:.4f} "
                f"| {dc['absolute_difference']:+.4f} |"
            )

        lines.append("")
        lines.append("## 6. What evidence supports the conclusions?")
        lines.append("")
        lines.append(f"**Sample sizes:**")
        lines.append(f"- Training: {m['training_items']} TLS items + {m['ofe_signals']} OFE signals")
        lines.append(f"- Evaluation: {m['total_challenges']} challenge predictions per condition")
        lines.append(f"- Weaknesses: {b['total_weaknesses']} (A), {o['total_weaknesses']} (B)")
        lines.append(f"- Collapse sequences: {b['collapse']['total_sequences']} per condition")
        lines.append(f"- Calibration samples: {b['calibration']['sample_size']} (A), {o['calibration']['sample_size']} (B)")
        lines.append("")
        lines.append(f"**Absolute differences (B - A):**")
        lines.append(f"- Accuracy: {c['accuracy']['absolute_difference']:+.4f} ({c['accuracy']['percentage_difference']:+.2f}%)")
        lines.append(f"- Calibration error: {c['calibration_error']['absolute_difference']:+.4f} ({c['calibration_error']['percentage_difference']:+.2f}%)")
        lines.append(f"- Error rate: {c['error_rate']['absolute_difference']:+.4f}")
        lines.append(f"- Collapse rate: {c['collapse_rate']['absolute_difference']:+.4f}")
        lines.append(f"- Weakness count: {c['total_weaknesses']['absolute_difference']:+.4f}")
        lines.append("")
        lines.append("## 7. What uncertainty remains?")
        lines.append("")
        lines.append("1. **Sample size uncertainty.** The experiment uses a single training run per condition. "
                     "Results may vary with different random seeds or dataset splits.")
        lines.append("2. **OFE signal design.** Structural signals were generated synthetically. "
                     "Real OFE signals from production data may produce different outcomes.")
        lines.append("3. **DSL coupling.** The experiment DSL includes OFE-aware features. "
                     "A different DSL design could change the comparison.")
        lines.append("4. **Binary metrics.** Accuracy and collapse are binary-sampled. "
                     "Continuous metrics (calibration, confidence) may show different patterns at higher resolution.")
        lines.append("5. **Single run.** No confidence intervals are computed. "
                     "Repeated runs with varied random seeds are needed for statistical significance testing.")
        lines.append("6. **Label assignment.** All OFE signals received label=False. "
                     "Different label assignments could change the graph update dynamics.")
        lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("## Summary")
        lines.append("")

        improved = any(
            abs(c["accuracy"]["absolute_difference"]) >= _SIGNIFICANCE_FLOOR
            or abs(c["calibration_error"]["absolute_difference"]) >= _SIGNIFICANCE_FLOOR
            for c in [c]
        )
        weak_improved = any(
            wc["interpretation"] == "improvement"
            for wc in c["weakness_level"]
        )

        if improved or weak_improved:
            parts = []
            if improved:
                parts.append("Some aggregate metrics showed measurable differences")
            if weak_improved:
                parts.append("Weakness frequencies shifted between conditions")
            lines.append(f"{' and '.join(parts)} in this campaign. "
                         "However, differences are small and may not generalize. "
                         "Replication with larger datasets is recommended.")
        else:
            lines.append("No compelling evidence of improvement from OFE signals was found in this campaign. "
                         "Results are consistent with OFE providing negligible measurable value "
                         "under the tested conditions.")

        text = "\n".join(lines)
        with open(full, "w", encoding="utf-8") as f:
            f.write(text)
        return full
