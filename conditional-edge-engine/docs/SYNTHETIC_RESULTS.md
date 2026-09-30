# Synthetic scenario results (reproduce with `python scripts/synthetic_summary.py`)

Event-level tables with KNOWN structure run through the real freeze -> nested walk-forward -> 24 trials -> statistics ->
acceptance -> registry pipeline. No frozen rule is adjusted per scenario; the scenario parameters in the table are the only thing
that varies (they were chosen to illustrate the scenario, not the engine). Seeds are fixed.

| scenario | planted structure | events (base /wk) | decisions over the 24 trials | max std uplift | min experiment_q | min selected /wk | promoted by model |
|---|---|---|---|---|---|---|---|
| 1_no_signal | `y = N(0,1)`; 10 events/week, 2015-2022 (7 OOS years) | 4165 (9.96) | REJECTED_INSUFFICIENT_UPLIFT: 24 | 0.018 | 0.9825 | 4.36 | - |
| 2_linear_edge | `y = 0.35*ER_60 + N(0,1)` | 4165 (9.96) | PROMOTABLE_PENDING_SENSITIVITY: 24 | 0.292 | 0.0005 | 4.53 | {'RIDGE': 8, 'SPLINE': 8, 'XGB': 8} |
| 3_nonlinear_edge | `y = 0.35*(ER_60^2 - 1) + N(0,1)` (U-shape; zero linear correlation) | 4165 (9.96) | PROMOTABLE_PENDING_SENSITIVITY: 16; REJECTED_INSUFFICIENT_UPLIFT: 8 | 0.309 | 0.0007 | 4.34 | {'SPLINE': 8, 'XGB': 8} |
| 4a_low_frequency_strong_edge | `y = 0.6*ER_60 + N(0,1)`, 1.6 events/week, 2011-2022 | 969 (1.55) **BASE_FREQUENCY_TOO_LOW_FOR_FIXED_HALF_SELECTION** | REJECTED_LOW_FREQUENCY: 24 | 0.395 | 0.0005 | 0.67 | - |
| 4b_spurious_tail | `y = N(0,1) + 1.5` only when `ER_60 > 1.9` (~3% of events) | 4165 (9.96) | REJECTED_INSUFFICIENT_UPLIFT: 24 | 0.05 | 0.024 | 4.42 | - |
| 5_frequency_destroying_weak_filter | `y = 0.041 + 0.006*ER_60 + N(0,1)`, 4.3 events/week | 1831 (4.38) | REJECTED_INSUFFICIENT_UPLIFT: 24 | 0.066 | 0.1199 | 1.97 | - |
| 6_unstable_regime | slope +1.0 in 2015-2018, -0.25 in 2019-2022 | 4165 (9.96) | REJECTED_INSTABILITY: 24 | 0.202 | 0.0005 | 4.85 | - |

`PROMOTABLE_PENDING_SENSITIVITY` = development candidate (>= 2 of 3 models pass at a TARGET x SIDE); sensitivity is a bar-level stage
and is exercised in `tests/test_end_to_end_bars.py`.

Reading guide: scenario 3 shows Ridge failing (`REJECTED_INSUFFICIENT_UPLIFT`) while Spline and XGB pass; 4a is a real, strong effect
that is **not promotable** because the selected half occurs < 1/week; 4b has a statistically detectable tail (`min experiment_q` 0.024)
that stays below the 0.10 uplift floor and is preserved as a diagnostic; 6 passes every gate except year stability.
