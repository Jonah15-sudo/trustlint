# Difficulty Model — Frontier Explorer v1

## Formula

```
difficulty = clamp(
    0.30 × contradiction_complexity
  + 0.20 × evidence_density
  + 0.15 × ambiguity
  + 0.20 × step_progression
  + 0.15 × frontier_pressure
)
```

## Inputs

| Input | Source | Range | Description |
|---|---|---|---|
| `contradiction_complexity` | `mutation_summary.mutations[].kind == "flipped_bool"` | [0, 1] | Proportion of mutations that flipped a boolean value, creating direct signal conflict |
| `evidence_density` | `mutation_summary.mutation_count / total_mutations` | [0, 1] | Ratio of mutated data paths to total examined leaves |
| `ambiguity` | `mutation_summary.mutations[].kind == "normalized_toward_midpoint"` | [0, 1] | Proportion of mutations that pushed numeric values toward the 0.5 midpoint (increases uncertainty) |
| `step_progression` | `step / max_steps` | [0, 1] | How far into the curriculum the challenge sits |
| `frontier_pressure` | `FrontierExplorer.analyze_frontier()` | [0, 1] | Composite measure of system weakness from weakest features and lowest edge confidences |

## Derivation

Each factor is computed independently, then weighted and summed:

```
contradiction_complexity = count("flipped_bool" in mutations) / total_mutations
evidence_density        = mutation_count / max(total_mutations, 1)
ambiguity               = count("normalized_toward_midpoint" in mutations) / total_mutations
step_progression        = step / max_steps
frontier_pressure       = clamp(frontier_pressure_input)
```

All five factors are clamped to [0, 1] before the weighted sum. The final result is clamped to [0, 1].

## Score Range

| Score | Label | Meaning |
|---|---|---|
| 0.00 – 0.20 | Trivial | No contradiction, single mutation, early step |
| 0.20 – 0.40 | Easy | Minor mutations, low ambiguity |
| 0.40 – 0.60 | Moderate | Mixed mutations, mid-curriculum |
| 0.60 – 0.80 | Hard | Multiple contradictions, high ambiguity, late steps |
| 0.80 – 1.00 | Extreme | Maximum signal conflict + high frontier pressure |

## Edge Cases

| Condition | Result | Rationale |
|---|---|---|
| Zero mutations | `step / max_steps` | Only step progression matters when nothing was mutated |
| All bool flips | `0.30 + 0.20 + 0.20*step_ratio + 0.15*fp` | Max contradiction, moderate evidence density |
| All midpoint pushes | `0.15 + 0.20 + 0.20*step_ratio + 0.15*fp` | Ambiguity without direct contradiction |
| `step=0, max_steps=0` | 0.0 | Division by zero → clamped to 0 |
| Any input > 1.0 | Clamped to 1.0 | `clamp()` ensures valid range |

## Assumptions

1. **Bool flips are always contradictory.** A flipped boolean in evidence data represents direct signal conflict between the original and the challenge.
2. **Midpoint normalization creates ambiguity.** Pushing a normalized value toward 0.5 increases decision uncertainty proportionally.
3. **Mutations are independent.** Each mutated path contributes independently to difficulty.
4. **Later steps are harder.** The step progression factor encodes the assumption that cumulative mutations compound difficulty.
5. **Frontier pressure reflects system state.** Higher frontier pressure means the system is already operating near its capability boundary, making any additional challenge harder.

## Known Weaknesses

1. **No interaction detection.** Mutations that interact non-linearly (e.g., flipping two correlated booleans) are scored the same as independent flips.
2. **No semantic understanding.** The model has no knowledge of what the data fields mean. A flipped `valid` flag scores the same as a flipped `hsts` flag.
3. **Linear weighting is naive.** The 30/20/15/20/15 split is a first-guess heuristic, not empirically optimized.
4. **Frontier pressure lag.** The frontier pressure snapshot is taken at curriculum start and reused for all steps — it does not update as the system learns during the session.
5. **No label difficulty.** The model does not consider whether the label becomes harder to predict — only the evidence mutations are scored.

## Example Cases

| # | Mutations | Step | Max | FP | Contradiction | Density | Ambiguity | Step | Pressure | Score |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1x preserved_bool | 1 | 5 | 0.0 | 0.00 | 1.00 | 0.00 | 0.20 | 0.00 | **0.26** |
| 2 | 1x flipped_bool | 1 | 5 | 0.0 | 1.00 | 1.00 | 0.00 | 0.20 | 0.00 | **0.56** |
| 3 | 1x flipped_bool | 5 | 5 | 0.0 | 1.00 | 1.00 | 0.00 | 1.00 | 0.00 | **0.76** |
| 4 | 1x normalized, 1x flipped | 3 | 5 | 0.3 | 0.50 | 1.00 | 0.50 | 0.60 | 0.30 | **0.66** |
| 5 | 2x flipped | 3 | 5 | 0.5 | 1.00 | 1.00 | 0.00 | 0.60 | 0.50 | **0.83** |
| 6 | 1x int_adjusted, 1x preserved | 2 | 5 | 0.0 | 0.00 | 1.00 | 0.00 | 0.40 | 0.00 | **0.28** |
| 7 | 1x normalized, 1x normalized | 4 | 5 | 0.7 | 0.00 | 1.00 | 1.00 | 0.80 | 0.70 | **0.68** |
| 8 | 3x flipped | 5 | 5 | 0.0 | 1.00 | 1.00 | 0.00 | 1.00 | 0.00 | **0.76** |
| 9 | No mutations | 3 | 5 | 0.0 | 0.00 | 0.00 | 0.00 | 0.60 | 0.00 | **0.20** |
| 10 | 2x flipped, 1x normalized | 5 | 5 | 0.9 | 0.67 | 1.00 | 0.33 | 1.00 | 0.90 | **0.90** |

### Calculation Walkthrough (Example #4)

- Mutations: 1x normalized_toward_midpoint, 1x flipped_bool
- Step: 3, Max steps: 5, Frontier pressure: 0.3
- contradiction_complexity = 1/2 = 0.50 (1 flip out of 2 mutations)
- evidence_density = 2/2 = 1.00 (2 mutations, count matches)
- ambiguity = 1/2 = 0.50 (1 midpoint push out of 2)
- step_progression = 3/5 = 0.60
- frontier_pressure = 0.30

```
difficulty = 0.30(0.50) + 0.20(1.00) + 0.15(0.50) + 0.20(0.60) + 0.15(0.30)
           = 0.150 + 0.200 + 0.075 + 0.120 + 0.045
           = 0.590
```
