# Confidence Collapse Detection — Frontier Explorer v1

## Algorithm

The collapse detector finds a single significant confidence drop in a sequence of challenge results.

### Pseudocode

```
function detect_collapse(confidences[], drop_threshold = 0.20):
    if length(confidences) < 3:
        return None

    best = max(confidences)
    best_idx = index_of_first(best, confidences)
    best_remaining = confidences[best_idx + 1:]

    if best_remaining is empty:
        return None

    min_after = min(best_remaining)
    drop = best - min_after

    if drop < drop_threshold:
        return None

    collapse_start = best_idx + 1
    collapse_end = best_idx + 1 + index_of_first(min_after, best_remaining)

    return {
        detected: true,
        drop_magnitude: round(drop, 4),
        drop_threshold: drop_threshold,
        peak_confidence: round(best, 4),
        peak_step: best_idx,
        nadir_confidence: round(min_after, 4),
        nadir_step: collapse_end,
        collapse_start_step: collapse_start,
        collapse_end_step: collapse_end,
        collapsed: drop >= drop_threshold
    }
```

## Parameters

| Parameter | Default | Range | Description |
|---|---|---|---|
| `drop_threshold` | 0.20 | (0, 1) | Minimum absolute confidence drop to qualify as a collapse |
| `confidences` | — | [0, 1] per element | Sequential list of predicted probabilities from challenge results, ordered by step |

## Heuristics

1. **Peak-first anchoring.** The detector anchors on the highest confidence value in the sequence, then scans forward for the lowest subsequent value. This avoids false positives from early low-confidence readings that later improve.

2. **Single collapse per session.** Only the most significant collapse (peak → subsequent nadir) is reported. Multiple collapse zones are not tracked independently.

3. **Minimum sequence length.** Sequences of fewer than 3 values are rejected — no meaningful collapse can be detected in 1–2 steps.

4. **No recovery detection.** The detector does not check whether confidence recovers after the nadir. A collapse is reported if the drop exceeds threshold, regardless of later behavior.

## Examples

### No Collapse

```
Confidences:  [0.90, 0.88, 0.85, 0.87]
Threshold:    0.20

Peak:         0.90
Nadir after:  0.85
Drop:         0.05
Collapse:     None (drop < 0.20)

Interpretation: Normal variance, no degradation.
```

### Gradual Degradation (Detected)

```
Confidences:  [0.95, 0.89, 0.82, 0.74, 0.65]
Threshold:    0.20

Peak:         0.95 (step 0)
Nadir after:  0.65 (step 4)
Drop:         0.30
Collapse:     {
                detected: true,
                drop_magnitude: 0.30,
                peak_step: 0,
                nadir_step: 4,
                collapse_start: 1,
                collapse_end: 4
              }

Interpretation: System confidence steadily degraded over 5 challenges.
                The entire post-peak range is the collapse zone.
```

### Sharp Collapse

```
Confidences:  [0.95, 0.92, 0.87, 0.48, 0.52]
Threshold:    0.20

Peak:         0.95 (step 0)
Nadir after:  0.48 (step 3)
Drop:         0.47
Collapse:     {
                detected: true,
                drop_magnitude: 0.47,
                peak_step: 0,
                nadir_step: 3,
                collapse_start: 1,
                collapse_end: 3
              }

Interpretation: Confidence held steady for 3 challenges (0.95→0.87),
                then collapsed sharply at step 4 (0.87→0.48). The
                collapse zone is steps 1–3 (post-peak through nadir).
```

### Gradual + Sharp (Composite)

```
Confidences:  [0.94, 0.91, 0.88, 0.78, 0.52, 0.55, 0.50]
Threshold:    0.20

Peak:         0.94 (step 0)
Nadir after:  0.50 (step 6)
Drop:         0.44
Collapse:     detected

Interpretation: Gradual decline to step 3 (0.78), then sharper drop
                through step 6. The algorithm finds one collapse zone
                spanning steps 1–6, but does not distinguish the
                two phases.
```

### Recovery After Drop

```
Confidences:  [0.92, 0.88, 0.55, 0.58, 0.85]
Threshold:    0.20

Peak:         0.92 (step 0)
Nadir after:  0.55 (step 2)
Drop:         0.37
Collapse:     detected (drop = 0.37 >= 0.20)

Note: Recovery to 0.85 at step 4 is NOT detected by the algorithm.
      The collapse is still reported because the peak→nadir drop
      exceeded threshold, even though the system later recovered.
```

## Failure Modes

| Mode | Description | Impact |
|---|---|---|
| **Late peak** | If the highest confidence occurs mid-sequence (e.g., after training updates), the detector ignores the earlier low-confidence values and only finds the drop from the mid-sequence peak forward. | The reported collapse zone may start mid-session, missing the initial low-confidence warmup. |
| **Multiple peaks** | Only the highest peak is considered. If there are multiple local maxima with separate collapses, only the most extreme one is reported. | Multi-phase degradation is collapsed into a single zone. |
| **Recovery blindness** | The algorithm does not distinguish between temporary drops with recovery and permanent degradation. | A system that recovers from a temporary challenge is still flagged as collapsed. |
| **Threshold sensitivity** | The 0.20 default is arbitrary. Different systems may need 0.10 (sensitive) or 0.30 (conservative). | False positives with low thresholds, false negatives with high thresholds. |
| **Equal confidence values** | If the peak confidence appears at two equal values, `index()` picks the first occurrence. | Minor — the earliest peak is used, which is the conservative choice. |

## Recommended Usage

```python
from frontier.session import CollapseDetector

confidences = [0.95, 0.92, 0.87, 0.73, 0.48]
result = CollapseDetector.detect(confidences, drop_threshold=0.20)

if result and result["detected"]:
    print(f"Collapse: {result['drop_magnitude']:.2f} drop "
          f"from step {result['peak_step']} to {result['nadir_step']}")
```
