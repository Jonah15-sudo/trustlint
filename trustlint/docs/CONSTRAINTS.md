# SPL v7.1 Constraint Gates

## Constraint #1: Stability v2

The original weighted stability was useful but too simple. v7.1 keeps weighted support/variance, then adds a rolling temporal check:

- recent-vs-baseline weighted correlation
- drift score
- sign-flip detection
- prediction-loss volatility
- per-feature `stability_report`

Each edge exposes:

- `weighted_stability`
- `stability_report`

The full report appears in `snapshot()["constraint_tests"]["stability"]`.

## Constraint #1b: Independence v2

The learner still detects duplicated or highly redundant feature pairs, but v7.1 adds a conditional-independence approximation using partial correlation against potential confounder features.

This means a pair is not blindly punished just because both are explained by a third driver feature. Exact duplicated channels remain penalized.

Each independence pair exposes:

- `raw_redundancy`
- `redundancy`
- `partial_correlation`
- `best_conditioner`
- `conditional_independent`

The full report appears in `snapshot()["constraint_tests"]["independence"]`.

## Constraint #2: Cross-source corroboration

The learner tracks feature statistics per `source_id`. A signal from one collector does not receive full production trust. Multiple qualified sources with consistent direction and balanced support increase edge trust.

Each edge exposes:

- `cross_source_corroboration`

The full report appears in `snapshot()["constraint_tests"]["cross_source_corroboration"]`.

## Constraint #2b: Multi-source verification / provenance

v7.1 adds `verification.py`:

- `SourceRegistry`
- `SourceProfile`
- `EvidenceProvenanceVerifier`
- stable artifact digest validation
- optional HMAC signature validation
- source trust weighting
- transport sanity checking
- anti-collusion visibility for shared provenance hashes

Pipeline training weight is attenuated by the verification score:

```text
final_sample_weight = label_weight * verification_score
```

The full report appears in `snapshot()["constraint_tests"]["source_verification"]`.

## Constraint #3: Intervention approximation production hack

This is not a randomized trial. It is a practical counterfactual approximation:

1. Build a baseline vector from learned feature means.
2. Clamp one feature to its observed low value.
3. Clamp the same feature to its observed high value.
4. Measure the probability shift.

Each edge exposes:

- `intervention_effect`

The full report appears in `snapshot()["constraint_tests"]["intervention_approximation"]`.

## Explicit causal graph report

v7.1 adds `causal_graph_report()` with:

- schema version: `spl.causal_graph.v7.1`
- nodes
- edges
- adjacency
- mechanisms
- all constraint reports

## Final edge confidence

Edge confidence is gated by:

```text
weight magnitude
+ weighted support
+ stability v2
+ independence v2
+ cross-source corroboration
+ source verification
+ intervention effect
```

The topology dashboard also multiplies the surface contribution by the edge gates, so duplicated, unstable, single-source, or non-interventional signals cannot dominate the surface.
