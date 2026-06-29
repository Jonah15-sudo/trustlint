# Frontier Validation Report — SPL v7.1

**Date:** 2026-05-31  
**Validator:** Frontier Explorer Hardening v1  
**Sessions:** 5  
**Tests:** 33 (17 existing + 16 new)

---

## 1. Are generated challenges actually harder?

### Finding: YES, with caveats.

Difficulty scores increase monotonically across steps within each session (0.59 → 0.63 → 0.67 → 0.71 → 0.75). The progression is deterministic and consistent across all 5 sessions because they share the same base pipeline state.

**Evidence:**

| Session | Diff start | Diff end | Trend |
|---|---|---|---|
| tls_standard | 0.59 | 0.75 | Monotonic increase |
| tls_expired | 0.59 | 0.75 | Monotonic increase |
| tls_clean | 0.59 | 0.75 | Monotonic increase |
| tls_mixed | 0.59 | 0.75 | Monotonic increase |
| tls_timeout_risk | 0.59 | 0.75 | Monotonic increase |

**Caveat:** The difficulty model depends only on the mutation summary and curriculum position. It does not measure whether the challenge is *semantically* harder — only that it has more contradictions, more ambiguity, or comes later in the sequence.

**What's missing:** A true "hardness" measure should incorporate the system's actual performance on each challenge, not just the mutation statistics.

---

## 2. Are generated challenges still valid?

### Finding: YES.

Every challenge artifact produced by `generate_curriculum()` is a valid `EvidenceArtifact` that:
- Passes through `EvidenceProvenanceVerifier` successfully
- Is processed by the pipeline without DLQ routing
- Produces a non-null result with `causal_probability`, `decision`, `features`, and `verification`

All 5 sessions × 5 steps = 25 challenges processed successfully with zero pipeline errors.

---

## 3. Are difficulty scores meaningful?

### Finding: PARTIALLY.

**What works:**
- Scores are deterministic (same input → same output)
- Scores increase with step progression
- Contradictions (bool flips) raise scores more than neutral mutations
- Ambiguity (midpoint normalization) raises scores
- Frontier pressure amplifies difficulty appropriately

**What does not work well:**
- Scores are identical across sessions because they depend only on mutation_summary and step, not on the system's unique response to each challenge
- The model does not incorporate actual prediction confidence as a difficulty signal
- A challenge that the system finds trivially easy may receive the same score as one that causes collapse, as long as their mutation summaries are similar

**Recommendation:** Incorporate post-challenge confidence into the difficulty model for Month 3.

---

## 4. Are collapse detections reasonable?

### Finding: PARTIALLY — the detector finds real drops, but some are false positives caused by active learning oscillation.

**Collapse detections across 5 sessions:**

| Session | Collapse? | Drop | Pattern | Assessment |
|---|---|---|---|---|
| tls_standard | No | 0.03 | Steady improvement | ✅ Correct |
| tls_expired | Yes | 0.58 | Wild oscillation (0.09→0.94→0.22→0.96→0.38) | ⚠️ False positive — oscillation, not capability loss |
| tls_clean | Yes | 0.80 | Extreme oscillation (0.24→0.10→0.89→0.09→0.86) | ⚠️ False positive — learner still converging |
| tls_mixed | No | 0.11 | Stable progression | ✅ Correct |
| tls_timeout_risk | Yes | 0.70 | Wild oscillation (0.09→0.91→0.16→0.93→0.22) | ⚠️ False positive — oscillation, not capability loss |

**Root cause:** The learner updates its weights during the session (each challenge trains the model). The "collapse" is oscillation during convergence, not a degradation of an already-stable capability. The collapse detector is correct mathematically — it found drops > 0.20 — but the drops are training artifacts, not capability collapse.

**Key insight:** The collapse detector should be used in prediction-only mode (learner frozen) or the threshold should be calibrated differently for active training sessions. A drop of 0.20 during early training is normal; a drop of 0.20 after 1,000 samples is concerning.

---

## 5. Discovered Weaknesses

All 5 sessions identified the same 3 weakest features:

| Feature | Weakness | Reliability |
|---|---|---|
| `partial_flag` | 0.337 | 0.663 |
| `http_error_flag` | 0.337 | 0.663 |
| `hsts_missing` | 0.250 | 0.750 |

This consistency is expected — all sessions start from the same trained pipeline state. The frontier pressure is identical (0.333) across all sessions.

**Limitation:** The weakness analysis is session-static. It does not track how weakness changes as the system learns from challenges. Dynamic weakness mapping is needed (Month 3).

---

## 6. Data Quality

| Metric | Value |
|---|---|
| Total sessions | 5 |
| Challenges per session | 5 |
| Total challenges processed | 25 |
| Pipeline errors | 0 |
| DLQ events | 0 |
| Files saved | 11 (5 sessions + 5 reports + 1 summary) |

---

## 7. Known Limitations

1. **Difficulty model is semantically blind.** It scores mutations, not actual hardness to the system.

2. **Collapse detector flags training oscillation.** The 0.20 default threshold is too sensitive for active learning sessions. A prediction-only evaluation mode is needed.

3. **No cross-session comparison.** All sessions currently share the same base pipeline state. Cross-session metrics (comparing different system configurations) are not yet implemented.

4. **Static frontier pressure.** The frontier analysis is performed once at session start and never updated as the learner trains on challenges.

5. **Identical difficulty across sessions.** Because difficulty depends only on mutation_summary (which is consistent) and not on system response, different sessions with different seeds get the same difficulty progression.

---

## 8. Recommendations for Month 3

1. **Add prediction-only evaluation mode.** Freeze learner weights during challenge evaluation to measure true capability, not training dynamics.

2. **Incorporate post-challenge confidence into difficulty.** A challenge that drops confidence from 0.95 to 0.50 is harder than one that drops from 0.95 to 0.90 — the difficulty score should reflect this.

3. **Add dynamic weakness tracking.** Weakness should be measured before and after each challenge, not just once at session start.

4. **Calibrate collapse threshold.** The 0.20 threshold should be configurable per session type (training vs. prediction-only).

---

## 9. Regression Status

```
33 tests passed · 0 failed · compileall clean
17 existing tests unchanged (no regression)
16 new frontier hardening tests passing
```
