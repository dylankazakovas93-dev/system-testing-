# Synthetic scenario results (reproduce with `python scripts/synthetic_summary.py`)

Event-level tables with KNOWN structure run through the real freeze → DEVELOPMENT_CV (5 purged chronological folds) → 24 selection trials →
statistics → acceptance → registry → IS report pipeline, on DEVELOPMENT-only tables. No frozen rule is adjusted per scenario; the scenario
parameters in the table are the only thing that varies. Seeds are fixed. Everything below is IS-stage output (nothing here is SELECTION HOLDOUT).

Two views per scenario:

* **before injection** — what the IS stage alone concludes. Without strong-mode verification of all 12 model paths and the event-parameter
  sensitivity verdict, a trial that passes every statistical gate is only `IS_PROVISIONAL_CANDIDATE` and the experiment stays `IS_PROVISIONAL_CANDIDATE`.
* **after injection** — the same trials after the verification of all 12 paths and the sensitivity verdict are recorded through the registry.
  **This injection is test-only**: the real verifier (`tests/test_verifier_bridge.py`, `scripts/verify_experiment.py`) and the real bar-level
  sensitivity probes (`tests/test_end_to_end_bars.py`) are exercised separately.

Numbers from the run of `scripts/synthetic_summary.py` (events are per DEVELOPMENT table; `min_campaign_bonferroni_p` is `min(raw_p × 24, 1)` with one experiment in the campaign):

| scenario | planted structure | events (base /wk) | decisions before injection | decisions after injection → status | max std uplift | min exp q | min campaign Bonf. p | min selected /wk |
|---|---|---|---|---|---|---|---|---|
| 1_no_signal | `y = N(0,1)`; 10 events/week, 2015-2022 | 4165 (9.96) | REJECTED_INSUFFICIENT_UPLIFT ×24 | same → `IS_REJECTED` | 0.018 | 0.7301 | 1.0 | 4.48 |
| 2_linear_edge | `y = 0.35·ER_60 + N(0,1)` | 4165 (9.96) | IS_PROVISIONAL_CANDIDATE ×24 | IS_SHORTLIST_ELIGIBLE ×24 (8 per model) → `AWAITING_HUMAN_FINAL_CONFIG_SELECTION` | 0.259 | 0.0005 | 0.012 | 4.72 |
| 3_nonlinear_edge | `y = 0.35·(ER_60² − 1) + N(0,1)` (U-shape, no linear correlation) | 4165 (9.96) | PROVISIONAL ×16, REJECTED_INSUFFICIENT_UPLIFT ×8 | SHORTLIST_ELIGIBLE ×16 (SPLINE 8, XGB 8) + REJECTED_INSUFFICIENT_UPLIFT ×8 (Ridge) → `AWAITING_HUMAN_FINAL_CONFIG_SELECTION` | 0.300 | 0.0007 | 0.012 | 4.43 |
| 4a_low_frequency_strong_edge | `y = 0.6·ER_60 + N(0,1)`, 1.6 events/week, 2011-2022 | 969 (1.55) | REJECTED_LOW_FREQUENCY ×24 | same → `IS_REJECTED` | 0.446 | 0.0005 | 0.012 | 0.71 |
| 4b_spurious_tail | `y = N(0,1) + 1.5` only when `ER_60 > 1.9` (~3% of events) | 4165 (9.96) | REJECTED_INSUFFICIENT_UPLIFT ×24 | same → `IS_REJECTED` | 0.052 | 0.009 | 0.036 | 4.49 |
| 5_frequency_destroying_weak_filter | `y = 0.041 + 0.006·ER_60 + N(0,1)`, 4.3 events/week | 1831 (4.38) | REJECTED_INSUFFICIENT_UPLIFT ×24 | same → `IS_REJECTED` | 0.008 | 0.903 | 1.0 | 2.09 |
| 6_unstable_regime | slope +1.0 in 2015-2018, −0.25 in 2019-2022 | 4165 (9.96) | REJECTED_INSTABILITY ×24 | same → `IS_REJECTED` | 0.166 | 0.0005 | 0.012 | 4.82 |
| 7_conditional_improvement_only | `y = 0.35·ER_60 − 0.45 + N(0,1)` (parent effect strongly negative) | 4165 (9.96) | DIAGNOSTIC_CONDITIONAL_IMPROVEMENT ×12 (UPPER), PROVISIONAL ×12 (LOWER) | DIAGNOSTIC… ×12 + SHORTLIST_ELIGIBLE ×12 (4 per model) → `AWAITING_HUMAN_FINAL_CONFIG_SELECTION` | 0.259 | 0.0005 | 0.012 | 4.72 |

Reading guide

* Scenario 3: Ridge fails (`REJECTED_INSUFFICIENT_UPLIFT`), Spline and XGB pass; eligibility is judged per TARGET|SIDE group with ≥ 2 of 3 models.
* Scenario 4a: a real, strong effect that is **not eligible** because the selected half occurs < 1/week; `BASE_FREQUENCY_TOO_LOW_FOR_FIXED_HALF_SELECTION` and `INSUFFICIENT_DEVELOPMENT_FOLD_EVIDENCE` are reported; no threshold is changed.
* Scenario 4b: a statistically detectable tail (`min experiment_q` 0.009) that stays below the 0.10 uplift floor.
* Scenario 5 (**honest note**): with the K=5 DEVELOPMENT_CV pooling this planted effect is not statistically detectable at all (`min experiment_q` 0.903), so it behaves like a second null scenario rather than a "weak but significant" one; the "detectable but below the uplift floor" role is played by 4b.
* Scenario 6: every statistical gate passes in the pooled data but the sign flips in the later years; rejected for instability (year/fold consistency).
* Scenario 7: only the UPPER state has an uplift over a strongly negative parent effect while its absolute selected effect is not positive → `DIAGNOSTIC_CONDITIONAL_IMPROVEMENT`, never a candidate; the LOWER (fade) state has a positive absolute effect and is eligible.

## Lifecycle scenarios A–E (IS → near-tie → human decision → [selection holdout] → final config → automatic CPCV), `tests/test_selection_lifecycle.py`

Table-level synthetic data, real engine code; the human's files are written by test code. Fixtures: `target_scale` plants the relation only on the named targets.

| scenario | planted structure | IS / near-tie | selection holdout | final config | CPCV | final status |
|---|---|---|---|---|---|---|
| A — clear winner | only `DIR_RETURN_180` carries the effect | 2 eligible configs, opposite sides, no near-tie | **skipped** (stays unread) | human picks the top IS config directly (`SELECTION_HOLDOUT_SKIPPED`) | automatic, DEVELOPMENT only, passes | `AWAITING_FINAL_LOCKBOX_APPROVAL` |
| B — genuine near tie | `DIR_RETURN_15` and `DIR_RETURN_60` carry the same effect; 60 loses half of it in the holdout year | near-tie cluster per side (|Δ| ≤ 0.03, paired CI ∋ 0) | both configs frozen together, one opening, family of 6 | `HOLDOUT_PREFERRED_CONFIG` = 15 (the IS rank-1 config 60 is not preferred); the human selects it | automatic, DEVELOPMENT + holdout, passes | `AWAITING_FINAL_LOCKBOX_APPROVAL` |
| C — unresolved | as B but 15 loses 45% in the holdout year | near-tie | both evaluated | `HOLDOUT_UNRESOLVED` (|Δ| ≤ 0.03, CI ∋ 0): no winner is fabricated; the human may choose one or decline | — | `FINAL_CONFIG_FROZEN` (human choice) or `HUMAN_DECLINED` |
| D — CPCV failure | slope +1.0 in every year except 2019 (−1.6) | near-tie | both pass the informational evidence gates | the human selects A | A fails (10/15 splits < 12) → **no fallback to B** | `CPCV_REJECTED` (lineage ends) |
| E — curve fit | slope +0.6 in development, −0.3 in the holdout year | strong IS, near-tie | collapses (selected effect < 0, `NO_QUALIFYING_CONFIG`) | the human declines | not run | `HUMAN_DECLINED` (no CPCV, no lockbox) |

Real-verifier, bar-level holdout and bar-level CPCV runs are in `tests/test_end_to_end_bars.py`.
