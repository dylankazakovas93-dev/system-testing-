# Synthetic scenario results (reproduce with `python scripts/synthetic_summary.py`)

Event-level tables with KNOWN structure run through the real freeze → DEVELOPMENT_CV (5 purged chronological folds) → 24 selection trials →
statistics → acceptance → registry → IS report pipeline, on DEVELOPMENT-only tables. No frozen rule is adjusted per scenario; the scenario
parameters in the table are the only thing that varies. Seeds are fixed. Everything below is IS-stage output (nothing here is OOS).

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
| 2_linear_edge | `y = 0.35·ER_60 + N(0,1)` | 4165 (9.96) | IS_PROVISIONAL_CANDIDATE ×24 | IS_SHORTLIST_ELIGIBLE ×24 (8 per model) → `AWAITING_HUMAN_OOS_APPROVAL` | 0.259 | 0.0005 | 0.012 | 4.72 |
| 3_nonlinear_edge | `y = 0.35·(ER_60² − 1) + N(0,1)` (U-shape, no linear correlation) | 4165 (9.96) | PROVISIONAL ×16, REJECTED_INSUFFICIENT_UPLIFT ×8 | SHORTLIST_ELIGIBLE ×16 (SPLINE 8, XGB 8) + REJECTED_INSUFFICIENT_UPLIFT ×8 (Ridge) → `AWAITING_HUMAN_OOS_APPROVAL` | 0.300 | 0.0007 | 0.012 | 4.43 |
| 4a_low_frequency_strong_edge | `y = 0.6·ER_60 + N(0,1)`, 1.6 events/week, 2011-2022 | 969 (1.55) | REJECTED_LOW_FREQUENCY ×24 | same → `IS_REJECTED` | 0.446 | 0.0005 | 0.012 | 0.71 |
| 4b_spurious_tail | `y = N(0,1) + 1.5` only when `ER_60 > 1.9` (~3% of events) | 4165 (9.96) | REJECTED_INSUFFICIENT_UPLIFT ×24 | same → `IS_REJECTED` | 0.052 | 0.009 | 0.036 | 4.49 |
| 5_frequency_destroying_weak_filter | `y = 0.041 + 0.006·ER_60 + N(0,1)`, 4.3 events/week | 1831 (4.38) | REJECTED_INSUFFICIENT_UPLIFT ×24 | same → `IS_REJECTED` | 0.008 | 0.903 | 1.0 | 2.09 |
| 6_unstable_regime | slope +1.0 in 2015-2018, −0.25 in 2019-2022 | 4165 (9.96) | REJECTED_INSTABILITY ×24 | same → `IS_REJECTED` | 0.166 | 0.0005 | 0.012 | 4.82 |
| 7_conditional_improvement_only | `y = 0.35·ER_60 − 0.45 + N(0,1)` (parent effect strongly negative) | 4165 (9.96) | DIAGNOSTIC_CONDITIONAL_IMPROVEMENT ×12 (UPPER), PROVISIONAL ×12 (LOWER) | DIAGNOSTIC… ×12 + SHORTLIST_ELIGIBLE ×12 (4 per model) → `AWAITING_HUMAN_OOS_APPROVAL` | 0.259 | 0.0005 | 0.012 | 4.72 |

Reading guide

* Scenario 3: Ridge fails (`REJECTED_INSUFFICIENT_UPLIFT`), Spline and XGB pass; eligibility is judged per TARGET|SIDE group with ≥ 2 of 3 models.
* Scenario 4a: a real, strong effect that is **not eligible** because the selected half occurs < 1/week; `BASE_FREQUENCY_TOO_LOW_FOR_FIXED_HALF_SELECTION` and `INSUFFICIENT_DEVELOPMENT_FOLD_EVIDENCE` are reported; no threshold is changed.
* Scenario 4b: a statistically detectable tail (`min experiment_q` 0.009) that stays below the 0.10 uplift floor.
* Scenario 5 (**honest note**): with the K=5 DEVELOPMENT_CV pooling this planted effect is not statistically detectable at all (`min experiment_q` 0.903), so it behaves like a second null scenario rather than a "weak but significant" one; the "detectable but below the uplift floor" role is played by 4b.
* Scenario 6: every statistical gate passes in the pooled data but the sign flips in the later years; rejected for instability (year/fold consistency).
* Scenario 7: only the UPPER state has an uplift over a strongly negative parent effect while its absolute selected effect is not positive → `DIAGNOSTIC_CONDITIONAL_IMPROVEMENT`, never a candidate; the LOWER (fade) state has a positive absolute effect and is eligible.

## Lifecycle scenarios (IS → human approval → one-shot OOS → CPCV), `tests/test_lifecycle_oos_cpcv.py`

| scenario | planted structure | IS | OOS | CPCV | final status |
|---|---|---|---|---|---|
| stable effect | `y = 0.35·ER_60 + N(0,1)` | eligible | `OOS_CONFIRMED` (3/3 models) | 15/15 splits with positive effect and positive uplift for all 3 models (≥ 12 required), `CPCV_CONFIRMED` | `AWAITING_FINAL_LOCKBOX` |
| curve-fit | slope +0.6 in 2015-2019 (development), −0.3 in 2020 (the OOS year) | eligible (std uplift ≈ 0.41) | `OOS_REJECTED` | not run (CPCV never rescues) | `OOS_REJECTED` |
| OOS-ok, CPCV-unstable | slope +1.0 in every development year except 2019 (−1.6) | eligible | `OOS_CONFIRMED` (3/3) | 10/15 splits positive (< 12) for every model, `CPCV_REJECTED` | `CPCV_REJECTED` |

IS tolerates the single bad development year (positive effect in 4 of 5 eligible years and 4 of 5 folds are required, ≥ 70% of years), OOS confirms, and CPCV rejects because
only 10 of 15 splits have a positive selected effect and positive uplift (`n_effect_positive = n_uplift_positive = 10` for RIDGE, SPLINE and XGB, < 12 required). The medians are
positive (≈ 0.49-0.55), so the veto comes from the ≥ 12/15 split rule alone. Real-verifier, bar-level OOS and bar-level CPCV runs are in `tests/test_end_to_end_bars.py`.
