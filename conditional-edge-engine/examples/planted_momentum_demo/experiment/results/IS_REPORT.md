# IS REPORT — EXP_0001

**EXPERIMENT SELECTION TRIALS: 24 / 24**

**CAMPAIGN REVEALED SELECTION TRIALS: 24 / 480**

**Number of statistical selection opportunities exposed so far: 24** (campaign C001; this experiment carries selection opportunity numbers 1–24; cumulative count when it was revealed: 24).

**OOS status = NOT ACCESSED**

* IS status (retroactive, as of campaign universe 24): **IS_SHORTLIST_ELIGIBLE**; lifecycle status: **AWAITING_HUMAN_OOS_APPROVAL**
* external verification: **RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE** (a model path counts toward 2-of-3 only if verified in strong mode)
* The campaign-adjusted values below are RETROACTIVE: later experiments in the campaign enlarge the multiplicity universe and may remove eligibility.

## A. Experiment hypothesis

Planted AR(1) momentum makes recent path informative.

## B. Exact event definition

* condition: every n-th bar of the supplied history
* base parameters: `{"every_n_bars": 45, "direction_period": 1, "direction": 1}`; sensitivity parameters: ['every_n_bars']
* eligible session (exchange-local): {'start': '09:31', 'end': '15:00'}; deduplication: keep_first_per_event_time; cooldown: {'bars': 0}
* information time: completion time of the n-th bar
* event.py sha256 `47e3f563c012e50b1a7f8a30d8bf81e106793a1d594ffd5bb2d922660ad10585`; EVENT_SPEC sha256 `9b17cc874e0a2d4b7c58b552bf3df5b87a5978ec80ba401beb10e063a0de22eb`

## C. Direction

All events: **+1** (long only). v1 allows one direction per experiment.

## D. Raw event frequency

| quantity | value |
|---|---|
| events after session/dedup/cooldown/target-session rules | 5,728 |
| model-eligible events (>= 480 completed bars) | 5,718 |
| development trading weeks | 157 |
| raw event frequency | 36.48 / week |
| TARGET_TIMESTAMP_INELIGIBLE events removed (60-bar window would cross the RTH close) | 0 |
| declared parameters never read by event.py | none |

## E. Data period used

* DEVELOPMENT only: bars 2016-01-04 14:30:00+00:00 … 2018-12-31 20:59:00+00:00 (304,590 bars). Partitions (frozen in the manifest): {'development_end': '2019-01-01', 'lockbox_start': '2019-10-01', 'oos_end': '2019-07-01'}
* OOS and lockbox rows removed before research code was called: 0
* training history: 2016-01-04..2016-07-05(exclusive; first fold's training = history before validation); DEVELOPMENT_CV validation: 2016-07-05..2018-12-31 DEVELOPMENT_CV folds [1, 2, 3, 4, 5]

## F. Exact selection trial count

4 targets × 3 models × 2 states = **24** pre-registered selection trials (no threshold, feature, parameter or filter search). Campaign C001: 24 revealed of 480 possible.

## G. All 24 trial results (M–Q: frequency, retention, parent/selected effect, uplift, CI)

All statistics are on pooled DEVELOPMENT_CV validation predictions (5 purged chronological folds). Nothing here is OOS.

| trial | opp # | target | model | state | N sel | parent f/wk | sel f/wk | retention | parent effect | selected effect | uplift | std uplift | 95% block-boot CI (uplift) | raw p | exp q | exp Bonf p | camp q | camp Bonf p | pos-eff yrs | pos-uplift yrs | pos-eff folds | pos-uplift folds | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXP_0001_T01 | 1 | DIR_RETURN_15 | RIDGE | UPPER_HALF | 2357 | 36.39 | 17.99 | 0.49 | +0.00003 | +0.00143 | +0.00140 | +0.212 | [+0.00119, +0.00160] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T02 | 2 | DIR_RETURN_15 | RIDGE | LOWER_HALF | 2410 | 36.39 | 18.40 | 0.51 | -0.00003 | +0.00134 | +0.00137 | +0.207 | [+0.00116, +0.00157] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T03 | 3 | DIR_RETURN_15 | SPLINE | UPPER_HALF | 2452 | 36.39 | 18.72 | 0.51 | +0.00003 | +0.00143 | +0.00140 | +0.211 | [+0.00121, +0.00157] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T04 | 4 | DIR_RETURN_15 | SPLINE | LOWER_HALF | 2315 | 36.39 | 17.67 | 0.49 | -0.00003 | +0.00145 | +0.00148 | +0.224 | [+0.00126, +0.00168] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T05 | 5 | DIR_RETURN_15 | XGB | UPPER_HALF | 2524 | 36.39 | 19.27 | 0.53 | +0.00003 | +0.00143 | +0.00140 | +0.212 | [+0.00121, +0.00158] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T06 | 6 | DIR_RETURN_15 | XGB | LOWER_HALF | 2243 | 36.39 | 17.12 | 0.47 | -0.00003 | +0.00155 | +0.00158 | +0.239 | [+0.00137, +0.00179] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T07 | 7 | DIR_RETURN_30 | RIDGE | UPPER_HALF | 2168 | 36.39 | 16.55 | 0.45 | -0.00001 | +0.00145 | +0.00145 | +0.142 | [+0.00112, +0.00179] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T08 | 8 | DIR_RETURN_30 | RIDGE | LOWER_HALF | 2599 | 36.39 | 19.84 | 0.55 | +0.00001 | +0.00122 | +0.00121 | +0.118 | [+0.00092, +0.00151] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 2/3 | 3/3 | 4/5 | 5/5 | REJECTED_INSTABILITY ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T09 | 9 | DIR_RETURN_30 | SPLINE | UPPER_HALF | 2257 | 36.39 | 17.23 | 0.47 | -0.00001 | +0.00157 | +0.00158 | +0.154 | [+0.00129, +0.00185] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T10 | 10 | DIR_RETURN_30 | SPLINE | LOWER_HALF | 2510 | 36.39 | 19.16 | 0.53 | +0.00001 | +0.00143 | +0.00142 | +0.138 | [+0.00115, +0.00169] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T11 | 11 | DIR_RETURN_30 | XGB | UPPER_HALF | 2512 | 36.39 | 19.18 | 0.53 | -0.00001 | +0.00131 | +0.00132 | +0.128 | [+0.00102, +0.00158] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T12 | 12 | DIR_RETURN_30 | XGB | LOWER_HALF | 2255 | 36.39 | 17.21 | 0.47 | +0.00001 | +0.00148 | +0.00147 | +0.143 | [+0.00113, +0.00179] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T13 | 13 | DIR_RETURN_60 | RIDGE | UPPER_HALF | 2046 | 36.39 | 15.62 | 0.43 | +0.00016 | +0.00161 | +0.00145 | +0.095 | [+0.00095, +0.00198] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | REJECTED_INSUFFICIENT_UPLIFT ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T14 | 14 | DIR_RETURN_60 | RIDGE | LOWER_HALF | 2721 | 36.39 | 20.77 | 0.57 | -0.00016 | +0.00092 | +0.00109 | +0.072 | [+0.00070, +0.00149] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 2/3 | 3/3 | 4/5 | 5/5 | REJECTED_INSUFFICIENT_UPLIFT ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T15 | 15 | DIR_RETURN_60 | SPLINE | UPPER_HALF | 2253 | 36.39 | 17.20 | 0.47 | +0.00016 | +0.00112 | +0.00095 | +0.063 | [+0.00051, +0.00140] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 2/3 | 5/5 | 4/5 | REJECTED_INSUFFICIENT_UPLIFT ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T16 | 16 | DIR_RETURN_60 | SPLINE | LOWER_HALF | 2514 | 36.39 | 19.19 | 0.53 | -0.00016 | +0.00069 | +0.00085 | +0.056 | [+0.00045, +0.00128] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 2/3 | 2/3 | 4/5 | 4/5 | REJECTED_INSUFFICIENT_UPLIFT ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T17 | 17 | DIR_RETURN_60 | XGB | UPPER_HALF | 2389 | 36.39 | 18.24 | 0.50 | +0.00016 | +0.00132 | +0.00116 | +0.076 | [+0.00068, +0.00160] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 2/3 | 2/3 | 4/5 | 4/5 | REJECTED_INSUFFICIENT_UPLIFT ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T18 | 18 | DIR_RETURN_60 | XGB | LOWER_HALF | 2378 | 36.39 | 18.15 | 0.50 | -0.00016 | +0.00100 | +0.00116 | +0.077 | [+0.00068, +0.00164] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 2/3 | 2/3 | 4/5 | 4/5 | REJECTED_INSUFFICIENT_UPLIFT ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T19 | 19 | DIR_PATH_SKEW_60 | RIDGE | UPPER_HALF | 2168 | 36.39 | 16.55 | 0.45 | +0.00012 | +0.00256 | +0.00244 | +0.151 | [+0.00192, +0.00296] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T20 | 20 | DIR_PATH_SKEW_60 | RIDGE | LOWER_HALF | 2599 | 36.39 | 19.84 | 0.55 | -0.00012 | +0.00191 | +0.00204 | +0.126 | [+0.00159, +0.00251] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T21 | 21 | DIR_PATH_SKEW_60 | SPLINE | UPPER_HALF | 2294 | 36.39 | 17.51 | 0.48 | +0.00012 | +0.00215 | +0.00203 | +0.125 | [+0.00157, +0.00247] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T22 | 22 | DIR_PATH_SKEW_60 | SPLINE | LOWER_HALF | 2473 | 36.39 | 18.88 | 0.52 | -0.00012 | +0.00176 | +0.00188 | +0.116 | [+0.00142, +0.00234] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T23 | 23 | DIR_PATH_SKEW_60 | XGB | UPPER_HALF | 2498 | 36.39 | 19.07 | 0.52 | +0.00012 | +0.00206 | +0.00193 | +0.120 | [+0.00148, +0.00236] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T24 | 24 | DIR_PATH_SKEW_60 | XGB | LOWER_HALF | 2269 | 36.39 | 17.32 | 0.48 | -0.00012 | +0.00201 | +0.00213 | +0.132 | [+0.00159, +0.00267] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 2/3 | 3/3 | 5/5 | 5/5 | REJECTED_INSTABILITY ⚠YEAR_CONCENTRATION_WARNING |

## H. Multiplicity adjustments

* `experiment_bonferroni_p = min(raw_p × 24, 1)`; `experiment_q` = BH over all 24 trials.
* `campaign_bonferroni_p = min(raw_p × 24, 1)` (universe = 24 × 1 experiments); `campaign_q` = BH over all 24 revealed trials, including rejected experiments, rejected models and the opposite score side. Recomputed after every new reveal.

## I. Top configurations (deterministic ranking, no subjective choice)

Eligibility is the full hard IS gate set; ranking = standardized uplift DESC, campaign_bonferroni_p ASC, selected frequency DESC, trial_id ASC.

| trial | opp # | target | model | state | N sel | parent f/wk | sel f/wk | retention | parent effect | selected effect | uplift | std uplift | 95% block-boot CI (uplift) | raw p | exp q | exp Bonf p | camp q | camp Bonf p | pos-eff yrs | pos-uplift yrs | pos-eff folds | pos-uplift folds | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXP_0001_T06 | 6 | DIR_RETURN_15 | XGB | LOWER_HALF | 2243 | 36.39 | 17.12 | 0.47 | -0.00003 | +0.00155 | +0.00158 | +0.239 | [+0.00137, +0.00179] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T04 | 4 | DIR_RETURN_15 | SPLINE | LOWER_HALF | 2315 | 36.39 | 17.67 | 0.49 | -0.00003 | +0.00145 | +0.00148 | +0.224 | [+0.00126, +0.00168] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T05 | 5 | DIR_RETURN_15 | XGB | UPPER_HALF | 2524 | 36.39 | 19.27 | 0.53 | +0.00003 | +0.00143 | +0.00140 | +0.212 | [+0.00121, +0.00158] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T01 | 1 | DIR_RETURN_15 | RIDGE | UPPER_HALF | 2357 | 36.39 | 17.99 | 0.49 | +0.00003 | +0.00143 | +0.00140 | +0.212 | [+0.00119, +0.00160] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T03 | 3 | DIR_RETURN_15 | SPLINE | UPPER_HALF | 2452 | 36.39 | 18.72 | 0.51 | +0.00003 | +0.00143 | +0.00140 | +0.211 | [+0.00121, +0.00157] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T02 | 2 | DIR_RETURN_15 | RIDGE | LOWER_HALF | 2410 | 36.39 | 18.40 | 0.51 | -0.00003 | +0.00134 | +0.00137 | +0.207 | [+0.00116, +0.00157] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T09 | 9 | DIR_RETURN_30 | SPLINE | UPPER_HALF | 2257 | 36.39 | 17.23 | 0.47 | -0.00001 | +0.00157 | +0.00158 | +0.154 | [+0.00129, +0.00185] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T19 | 19 | DIR_PATH_SKEW_60 | RIDGE | UPPER_HALF | 2168 | 36.39 | 16.55 | 0.45 | +0.00012 | +0.00256 | +0.00244 | +0.151 | [+0.00192, +0.00296] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T12 | 12 | DIR_RETURN_30 | XGB | LOWER_HALF | 2255 | 36.39 | 17.21 | 0.47 | +0.00001 | +0.00148 | +0.00147 | +0.143 | [+0.00113, +0.00179] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T07 | 7 | DIR_RETURN_30 | RIDGE | UPPER_HALF | 2168 | 36.39 | 16.55 | 0.45 | -0.00001 | +0.00145 | +0.00145 | +0.142 | [+0.00112, +0.00179] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T10 | 10 | DIR_RETURN_30 | SPLINE | LOWER_HALF | 2510 | 36.39 | 19.16 | 0.53 | +0.00001 | +0.00143 | +0.00142 | +0.138 | [+0.00115, +0.00169] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T11 | 11 | DIR_RETURN_30 | XGB | UPPER_HALF | 2512 | 36.39 | 19.18 | 0.53 | -0.00001 | +0.00131 | +0.00132 | +0.128 | [+0.00102, +0.00158] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T20 | 20 | DIR_PATH_SKEW_60 | RIDGE | LOWER_HALF | 2599 | 36.39 | 19.84 | 0.55 | -0.00012 | +0.00191 | +0.00204 | +0.126 | [+0.00159, +0.00251] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T21 | 21 | DIR_PATH_SKEW_60 | SPLINE | UPPER_HALF | 2294 | 36.39 | 17.51 | 0.48 | +0.00012 | +0.00215 | +0.00203 | +0.125 | [+0.00157, +0.00247] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T23 | 23 | DIR_PATH_SKEW_60 | XGB | UPPER_HALF | 2498 | 36.39 | 19.07 | 0.52 | +0.00012 | +0.00206 | +0.00193 | +0.120 | [+0.00148, +0.00236] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |
| EXP_0001_T22 | 22 | DIR_PATH_SKEW_60 | SPLINE | LOWER_HALF | 2473 | 36.39 | 18.88 | 0.52 | -0.00012 | +0.00176 | +0.00188 | +0.116 | [+0.00142, +0.00234] | 0.0005 | 0.0005 | 0.0120 | 0.0005 | 0.0120 | 3/3 | 3/3 | 5/5 | 5/5 | IS_SHORTLIST_ELIGIBLE ⚠YEAR_CONCENTRATION_WARNING |

### TOP 5 IS GROUPS (the human may unlock at most 2 for OOS; each approved group runs all 3 models)

| rank | group (TARGET|SIDE) | models eligible | median std uplift | median campaign Bonf p | median sel f/wk |
|---|---|---|---|---|---|
| 1 | DIR_RETURN_15|LOWER_HALF | RIDGE, SPLINE, XGB | +0.224 | 0.0120 | 17.67 |
| 2 | DIR_RETURN_15|UPPER_HALF | RIDGE, SPLINE, XGB | +0.212 | 0.0120 | 18.72 |
| 3 | DIR_RETURN_30|UPPER_HALF | RIDGE, SPLINE, XGB | +0.142 | 0.0120 | 17.23 |
| 4 | DIR_RETURN_30|LOWER_HALF | SPLINE, XGB | +0.141 | 0.0120 | 18.19 |
| 5 | DIR_PATH_SKEW_60|UPPER_HALF | RIDGE, SPLINE, XGB | +0.125 | 0.0120 | 17.51 |

## J. Model agreement (>= 2 of 3 models required)

| group | eligible models | provisional models |
|---|---|---|
| DIR_PATH_SKEW_60|UPPER_HALF | RIDGE, SPLINE, XGB | - |
| DIR_PATH_SKEW_60|LOWER_HALF | RIDGE, SPLINE | - |
| DIR_RETURN_15|UPPER_HALF | RIDGE, SPLINE, XGB | - |
| DIR_RETURN_15|LOWER_HALF | RIDGE, SPLINE, XGB | - |
| DIR_RETURN_30|UPPER_HALF | RIDGE, SPLINE, XGB | - |
| DIR_RETURN_30|LOWER_HALF | SPLINE, XGB | - |
| DIR_RETURN_60|UPPER_HALF | - | - |
| DIR_RETURN_60|LOWER_HALF | - | - |

## K. All IS calendar years (every trial; eligible = >= 20 selected events)

**EXP_0001_T01 DIR_RETURN_15/RIDGE/UPPER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.43 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 464 | 17.85 | +0.00006 | +0.00111 | +0.00105 |
| 2017 | yes | 1907 | 911 | 17.52 | +0.00002 | +0.00153 | +0.00151 |
| 2018 | yes | 1914 | 982 | 18.53 | +0.00002 | +0.00148 | +0.00146 |

**EXP_0001_T02 DIR_RETURN_15/RIDGE/LOWER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.43 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 482 | 18.54 | -0.00006 | +0.00095 | +0.00101 |
| 2017 | yes | 1907 | 996 | 19.15 | -0.00002 | +0.00136 | +0.00138 |
| 2018 | yes | 1914 | 932 | 17.58 | -0.00002 | +0.00151 | +0.00154 |

**EXP_0001_T03 DIR_RETURN_15/SPLINE/UPPER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.46 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 464 | 17.85 | +0.00006 | +0.00109 | +0.00103 |
| 2017 | yes | 1907 | 955 | 18.37 | +0.00002 | +0.00145 | +0.00143 |
| 2018 | yes | 1914 | 1033 | 19.49 | +0.00002 | +0.00155 | +0.00153 |

**EXP_0001_T04 DIR_RETURN_15/SPLINE/LOWER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.46 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 482 | 18.54 | -0.00006 | +0.00093 | +0.00099 |
| 2017 | yes | 1907 | 952 | 18.31 | -0.00002 | +0.00141 | +0.00143 |
| 2018 | yes | 1914 | 881 | 16.62 | -0.00002 | +0.00177 | +0.00180 |

**EXP_0001_T05 DIR_RETURN_15/XGB/UPPER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.44 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 468 | 18.00 | +0.00006 | +0.00127 | +0.00121 |
| 2017 | yes | 1907 | 997 | 19.17 | +0.00002 | +0.00144 | +0.00142 |
| 2018 | yes | 1914 | 1059 | 19.98 | +0.00002 | +0.00150 | +0.00147 |

**EXP_0001_T06 DIR_RETURN_15/XGB/LOWER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.44 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 478 | 18.38 | -0.00006 | +0.00112 | +0.00118 |
| 2017 | yes | 1907 | 910 | 17.50 | -0.00002 | +0.00153 | +0.00156 |
| 2018 | yes | 1914 | 855 | 16.13 | -0.00002 | +0.00180 | +0.00182 |

**EXP_0001_T07 DIR_RETURN_30/RIDGE/UPPER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.50 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 349 | 13.42 | +0.00027 | +0.00055 | +0.00028 |
| 2017 | yes | 1907 | 798 | 15.35 | -0.00002 | +0.00200 | +0.00202 |
| 2018 | yes | 1914 | 1021 | 19.26 | -0.00013 | +0.00132 | +0.00146 |

**EXP_0001_T08 DIR_RETURN_30/RIDGE/LOWER_HALF** — positive selected-effect years 2/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.50 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 597 | 22.96 | -0.00027 | -0.00011 | +0.00016 |
| 2017 | yes | 1907 | 1109 | 21.33 | +0.00002 | +0.00147 | +0.00145 |
| 2018 | yes | 1914 | 893 | 16.85 | +0.00013 | +0.00180 | +0.00166 |

**EXP_0001_T09 DIR_RETURN_30/SPLINE/UPPER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.48 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 379 | 14.58 | +0.00027 | +0.00088 | +0.00061 |
| 2017 | yes | 1907 | 848 | 16.31 | -0.00002 | +0.00190 | +0.00192 |
| 2018 | yes | 1914 | 1030 | 19.43 | -0.00013 | +0.00155 | +0.00169 |

**EXP_0001_T10 DIR_RETURN_30/SPLINE/LOWER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.48 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 567 | 21.81 | -0.00027 | +0.00014 | +0.00041 |
| 2017 | yes | 1907 | 1059 | 20.37 | +0.00002 | +0.00156 | +0.00154 |
| 2018 | yes | 1914 | 884 | 16.68 | +0.00013 | +0.00210 | +0.00196 |

**EXP_0001_T11 DIR_RETURN_30/XGB/UPPER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.50 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 420 | 16.15 | +0.00027 | +0.00090 | +0.00063 |
| 2017 | yes | 1907 | 993 | 19.10 | -0.00002 | +0.00167 | +0.00169 |
| 2018 | yes | 1914 | 1099 | 20.74 | -0.00013 | +0.00114 | +0.00127 |

**EXP_0001_T12 DIR_RETURN_30/XGB/LOWER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.50 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 526 | 20.23 | -0.00027 | +0.00023 | +0.00050 |
| 2017 | yes | 1907 | 914 | 17.58 | +0.00002 | +0.00186 | +0.00184 |
| 2018 | yes | 1914 | 815 | 15.38 | +0.00013 | +0.00185 | +0.00172 |

**EXP_0001_T13 DIR_RETURN_60/RIDGE/UPPER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.50 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 256 | 9.85 | +0.00032 | +0.00110 | +0.00078 |
| 2017 | yes | 1907 | 704 | 13.54 | +0.00040 | +0.00231 | +0.00191 |
| 2018 | yes | 1914 | 1086 | 20.49 | -0.00015 | +0.00128 | +0.00143 |

**EXP_0001_T14 DIR_RETURN_60/RIDGE/LOWER_HALF** — positive selected-effect years 2/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.50 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 690 | 26.54 | -0.00032 | -0.00004 | +0.00029 |
| 2017 | yes | 1907 | 1203 | 23.13 | -0.00040 | +0.00072 | +0.00112 |
| 2018 | yes | 1914 | 828 | 15.62 | +0.00015 | +0.00203 | +0.00188 |

**EXP_0001_T15 DIR_RETURN_60/SPLINE/UPPER_HALF** — positive selected-effect years 3/3, positive-uplift years 2/3, largest-year share of total absolute uplift 0.51 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 290 | 11.15 | +0.00032 | +0.00029 | -0.00003 |
| 2017 | yes | 1907 | 879 | 16.90 | +0.00040 | +0.00164 | +0.00124 |
| 2018 | yes | 1914 | 1084 | 20.45 | -0.00015 | +0.00092 | +0.00107 |

**EXP_0001_T16 DIR_RETURN_60/SPLINE/LOWER_HALF** — positive selected-effect years 2/3, positive-uplift years 2/3, largest-year share of total absolute uplift 0.51 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 656 | 25.23 | -0.00032 | -0.00034 | -0.00001 |
| 2017 | yes | 1907 | 1028 | 19.77 | -0.00040 | +0.00066 | +0.00106 |
| 2018 | yes | 1914 | 830 | 15.66 | +0.00015 | +0.00155 | +0.00139 |

**EXP_0001_T17 DIR_RETURN_60/XGB/UPPER_HALF** — positive selected-effect years 2/3, positive-uplift years 2/3, largest-year share of total absolute uplift 0.51 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 281 | 10.81 | +0.00032 | -0.00035 | -0.00067 |
| 2017 | yes | 1907 | 973 | 18.71 | +0.00040 | +0.00182 | +0.00142 |
| 2018 | yes | 1914 | 1135 | 21.42 | -0.00015 | +0.00130 | +0.00145 |

**EXP_0001_T18 DIR_RETURN_60/XGB/LOWER_HALF** — positive selected-effect years 2/3, positive-uplift years 2/3, largest-year share of total absolute uplift 0.51 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 665 | 25.58 | -0.00032 | -0.00061 | -0.00028 |
| 2017 | yes | 1907 | 934 | 17.96 | -0.00040 | +0.00108 | +0.00148 |
| 2018 | yes | 1914 | 779 | 14.70 | +0.00015 | +0.00227 | +0.00211 |

**EXP_0001_T19 DIR_PATH_SKEW_60/RIDGE/UPPER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.48 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 319 | 12.27 | +0.00024 | +0.00153 | +0.00129 |
| 2017 | yes | 1907 | 794 | 15.27 | +0.00037 | +0.00340 | +0.00303 |
| 2018 | yes | 1914 | 1055 | 19.91 | -0.00018 | +0.00225 | +0.00242 |

**EXP_0001_T20 DIR_PATH_SKEW_60/RIDGE/LOWER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.48 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 627 | 24.12 | -0.00024 | +0.00042 | +0.00066 |
| 2017 | yes | 1907 | 1113 | 21.40 | -0.00037 | +0.00179 | +0.00216 |
| 2018 | yes | 1914 | 859 | 16.21 | +0.00018 | +0.00315 | +0.00298 |

**EXP_0001_T21 DIR_PATH_SKEW_60/SPLINE/UPPER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.50 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 331 | 12.73 | +0.00024 | +0.00080 | +0.00056 |
| 2017 | yes | 1907 | 897 | 17.25 | +0.00037 | +0.00277 | +0.00240 |
| 2018 | yes | 1914 | 1066 | 20.11 | -0.00018 | +0.00206 | +0.00223 |

**EXP_0001_T22 DIR_PATH_SKEW_60/SPLINE/LOWER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.50 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 615 | 23.65 | -0.00024 | +0.00006 | +0.00030 |
| 2017 | yes | 1907 | 1010 | 19.42 | -0.00037 | +0.00176 | +0.00213 |
| 2018 | yes | 1914 | 848 | 16.00 | +0.00018 | +0.00299 | +0.00281 |

**EXP_0001_T23 DIR_PATH_SKEW_60/XGB/UPPER_HALF** — positive selected-effect years 3/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.49 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 322 | 12.38 | +0.00024 | +0.00066 | +0.00042 |
| 2017 | yes | 1907 | 1043 | 20.06 | +0.00037 | +0.00261 | +0.00224 |
| 2018 | yes | 1914 | 1133 | 21.38 | -0.00018 | +0.00195 | +0.00212 |

**EXP_0001_T24 DIR_PATH_SKEW_60/XGB/LOWER_HALF** — positive selected-effect years 2/3, positive-uplift years 3/3, largest-year share of total absolute uplift 0.49 — **YEAR_CONCENTRATION_WARNING** (> 35%)

| year | eligible | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|---|
| 2016 | yes | 946 | 624 | 24.00 | -0.00024 | -0.00002 | +0.00022 |
| 2017 | yes | 1907 | 864 | 16.62 | -0.00037 | +0.00234 | +0.00271 |
| 2018 | yes | 1914 | 781 | 14.74 | +0.00018 | +0.00326 | +0.00308 |

## L. All 5 purged DEVELOPMENT_CV folds (internal cross-validation — NOT OOS)

**DIR_RETURN_15|RIDGE** fold records: fold 1: OK (train 951, validation 953); fold 2: OK (train 1904, validation 954); fold 3: OK (train 2858, validation 953); fold 4: OK (train 3811, validation 953); fold 5: OK (train 4764, validation 954)

**DIR_RETURN_15|SPLINE** fold records: fold 1: OK (train 951, validation 953); fold 2: OK (train 1904, validation 954); fold 3: OK (train 2858, validation 953); fold 4: OK (train 3811, validation 953); fold 5: OK (train 4764, validation 954)

**DIR_RETURN_15|XGB** fold records: fold 1: OK (train 951, validation 953); fold 2: OK (train 1904, validation 954); fold 3: OK (train 2858, validation 953); fold 4: OK (train 3811, validation 953); fold 5: OK (train 4764, validation 954)

**DIR_RETURN_30|RIDGE** fold records: fold 1: OK (train 951, validation 953); fold 2: OK (train 1904, validation 954); fold 3: OK (train 2858, validation 953); fold 4: OK (train 3811, validation 953); fold 5: OK (train 4764, validation 954)

**DIR_RETURN_30|SPLINE** fold records: fold 1: OK (train 951, validation 953); fold 2: OK (train 1904, validation 954); fold 3: OK (train 2858, validation 953); fold 4: OK (train 3811, validation 953); fold 5: OK (train 4764, validation 954)

**DIR_RETURN_30|XGB** fold records: fold 1: OK (train 951, validation 953); fold 2: OK (train 1904, validation 954); fold 3: OK (train 2858, validation 953); fold 4: OK (train 3811, validation 953); fold 5: OK (train 4764, validation 954)

**DIR_RETURN_60|RIDGE** fold records: fold 1: OK (train 951, validation 953); fold 2: OK (train 1904, validation 954); fold 3: OK (train 2858, validation 953); fold 4: OK (train 3811, validation 953); fold 5: OK (train 4764, validation 954)

**DIR_RETURN_60|SPLINE** fold records: fold 1: OK (train 951, validation 953); fold 2: OK (train 1904, validation 954); fold 3: OK (train 2858, validation 953); fold 4: OK (train 3811, validation 953); fold 5: OK (train 4764, validation 954)

**DIR_RETURN_60|XGB** fold records: fold 1: OK (train 951, validation 953); fold 2: OK (train 1904, validation 954); fold 3: OK (train 2858, validation 953); fold 4: OK (train 3811, validation 953); fold 5: OK (train 4764, validation 954)

**DIR_PATH_SKEW_60|RIDGE** fold records: fold 1: OK (train 951, validation 953); fold 2: OK (train 1904, validation 954); fold 3: OK (train 2858, validation 953); fold 4: OK (train 3811, validation 953); fold 5: OK (train 4764, validation 954)

**DIR_PATH_SKEW_60|SPLINE** fold records: fold 1: OK (train 951, validation 953); fold 2: OK (train 1904, validation 954); fold 3: OK (train 2858, validation 953); fold 4: OK (train 3811, validation 953); fold 5: OK (train 4764, validation 954)

**DIR_PATH_SKEW_60|XGB** fold records: fold 1: OK (train 951, validation 953); fold 2: OK (train 1904, validation 954); fold 3: OK (train 2858, validation 953); fold 4: OK (train 3811, validation 953); fold 5: OK (train 4764, validation 954)

**EXP_0001_T01** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 466 | 17.26 | +0.00006 | +0.00113 | +0.00107 |
| 2 | 954 | 439 | 16.26 | +0.00019 | +0.00172 | +0.00153 |
| 3 | 953 | 477 | 17.67 | -0.00014 | +0.00132 | +0.00146 |
| 4 | 953 | 450 | 16.67 | +0.00022 | +0.00173 | +0.00151 |
| 5 | 954 | 525 | 19.44 | -0.00017 | +0.00129 | +0.00146 |

**EXP_0001_T02** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 487 | 18.04 | -0.00006 | +0.00096 | +0.00102 |
| 2 | 954 | 515 | 19.07 | -0.00019 | +0.00112 | +0.00130 |
| 3 | 953 | 476 | 17.63 | +0.00014 | +0.00161 | +0.00147 |
| 4 | 953 | 503 | 18.63 | -0.00022 | +0.00114 | +0.00135 |
| 5 | 954 | 429 | 15.89 | +0.00017 | +0.00196 | +0.00179 |

**EXP_0001_T03** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 466 | 17.26 | +0.00006 | +0.00111 | +0.00105 |
| 2 | 954 | 427 | 15.81 | +0.00019 | +0.00168 | +0.00149 |
| 3 | 953 | 533 | 19.74 | -0.00014 | +0.00124 | +0.00138 |
| 4 | 953 | 504 | 18.67 | +0.00022 | +0.00196 | +0.00174 |
| 5 | 954 | 522 | 19.33 | -0.00017 | +0.00119 | +0.00136 |

**EXP_0001_T04** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 487 | 18.04 | -0.00006 | +0.00094 | +0.00100 |
| 2 | 954 | 527 | 19.52 | -0.00019 | +0.00102 | +0.00120 |
| 3 | 953 | 420 | 15.56 | +0.00014 | +0.00189 | +0.00175 |
| 4 | 953 | 449 | 16.63 | -0.00022 | +0.00173 | +0.00195 |
| 5 | 954 | 432 | 16.00 | +0.00017 | +0.00181 | +0.00164 |

**EXP_0001_T05** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 471 | 17.44 | +0.00006 | +0.00129 | +0.00123 |
| 2 | 954 | 436 | 16.15 | +0.00019 | +0.00194 | +0.00175 |
| 3 | 953 | 565 | 20.93 | -0.00014 | +0.00103 | +0.00117 |
| 4 | 953 | 524 | 19.41 | +0.00022 | +0.00163 | +0.00142 |
| 5 | 954 | 528 | 19.56 | -0.00017 | +0.00139 | +0.00155 |

**EXP_0001_T06** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 482 | 17.85 | -0.00006 | +0.00114 | +0.00120 |
| 2 | 954 | 518 | 19.19 | -0.00019 | +0.00128 | +0.00147 |
| 3 | 953 | 388 | 14.37 | +0.00014 | +0.00184 | +0.00170 |
| 4 | 953 | 429 | 15.89 | -0.00022 | +0.00151 | +0.00173 |
| 5 | 954 | 426 | 15.78 | +0.00017 | +0.00209 | +0.00193 |

**EXP_0001_T07** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 351 | 13.00 | +0.00027 | +0.00059 | +0.00032 |
| 2 | 954 | 415 | 15.37 | -0.00009 | +0.00157 | +0.00166 |
| 3 | 953 | 385 | 14.26 | +0.00007 | +0.00239 | +0.00233 |
| 4 | 953 | 476 | 17.63 | +0.00007 | +0.00150 | +0.00143 |
| 5 | 954 | 541 | 20.04 | -0.00036 | +0.00119 | +0.00154 |

**EXP_0001_T08** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 602 | 22.30 | -0.00027 | -0.00008 | +0.00019 |
| 2 | 954 | 539 | 19.96 | +0.00009 | +0.00137 | +0.00128 |
| 3 | 953 | 568 | 21.04 | -0.00007 | +0.00151 | +0.00158 |
| 4 | 953 | 477 | 17.67 | -0.00007 | +0.00135 | +0.00142 |
| 5 | 954 | 413 | 15.30 | +0.00036 | +0.00238 | +0.00202 |

**EXP_0001_T09** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 381 | 14.11 | +0.00027 | +0.00091 | +0.00064 |
| 2 | 954 | 449 | 16.63 | -0.00009 | +0.00158 | +0.00167 |
| 3 | 953 | 401 | 14.85 | +0.00007 | +0.00223 | +0.00217 |
| 4 | 953 | 474 | 17.56 | +0.00007 | +0.00201 | +0.00194 |
| 5 | 954 | 552 | 20.44 | -0.00036 | +0.00115 | +0.00151 |

**EXP_0001_T10** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 572 | 21.19 | -0.00027 | +0.00016 | +0.00043 |
| 2 | 954 | 505 | 18.70 | +0.00009 | +0.00158 | +0.00149 |
| 3 | 953 | 552 | 20.44 | -0.00007 | +0.00151 | +0.00158 |
| 4 | 953 | 479 | 17.74 | -0.00007 | +0.00185 | +0.00192 |
| 5 | 954 | 402 | 14.89 | +0.00036 | +0.00243 | +0.00207 |

**EXP_0001_T11** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 424 | 15.70 | +0.00027 | +0.00094 | +0.00067 |
| 2 | 954 | 483 | 17.89 | -0.00009 | +0.00142 | +0.00151 |
| 3 | 953 | 510 | 18.89 | +0.00007 | +0.00188 | +0.00182 |
| 4 | 953 | 546 | 20.22 | +0.00007 | +0.00103 | +0.00096 |
| 5 | 954 | 549 | 20.33 | -0.00036 | +0.00124 | +0.00160 |

**EXP_0001_T12** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 529 | 19.59 | -0.00027 | +0.00027 | +0.00054 |
| 2 | 954 | 471 | 17.44 | +0.00009 | +0.00164 | +0.00155 |
| 3 | 953 | 443 | 16.41 | -0.00007 | +0.00203 | +0.00209 |
| 4 | 953 | 407 | 15.07 | -0.00007 | +0.00122 | +0.00129 |
| 5 | 954 | 405 | 15.00 | +0.00036 | +0.00252 | +0.00217 |

**EXP_0001_T13** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 259 | 9.59 | +0.00032 | +0.00113 | +0.00081 |
| 2 | 954 | 337 | 12.48 | +0.00053 | +0.00218 | +0.00165 |
| 3 | 953 | 370 | 13.70 | +0.00031 | +0.00246 | +0.00215 |
| 4 | 953 | 498 | 18.44 | +0.00020 | +0.00170 | +0.00150 |
| 5 | 954 | 582 | 21.56 | -0.00054 | +0.00088 | +0.00142 |

**EXP_0001_T14** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 694 | 25.70 | -0.00032 | -0.00002 | +0.00030 |
| 2 | 954 | 617 | 22.85 | -0.00053 | +0.00037 | +0.00090 |
| 3 | 953 | 583 | 21.59 | -0.00031 | +0.00105 | +0.00137 |
| 4 | 953 | 455 | 16.85 | -0.00020 | +0.00144 | +0.00164 |
| 5 | 954 | 372 | 13.78 | +0.00054 | +0.00277 | +0.00223 |

**EXP_0001_T15** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 292 | 10.81 | +0.00032 | +0.00018 | -0.00014 |
| 2 | 954 | 393 | 14.56 | +0.00053 | +0.00212 | +0.00159 |
| 3 | 953 | 489 | 18.11 | +0.00031 | +0.00134 | +0.00102 |
| 4 | 953 | 522 | 19.33 | +0.00020 | +0.00111 | +0.00091 |
| 5 | 954 | 557 | 20.63 | -0.00054 | +0.00071 | +0.00125 |

**EXP_0001_T16** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 661 | 24.48 | -0.00032 | -0.00039 | -0.00006 |
| 2 | 954 | 561 | 20.78 | -0.00053 | +0.00059 | +0.00112 |
| 3 | 953 | 464 | 17.19 | -0.00031 | +0.00077 | +0.00108 |
| 4 | 953 | 431 | 15.96 | -0.00020 | +0.00091 | +0.00111 |
| 5 | 954 | 397 | 14.70 | +0.00054 | +0.00230 | +0.00175 |

**EXP_0001_T17** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 283 | 10.48 | +0.00032 | -0.00028 | -0.00061 |
| 2 | 954 | 406 | 15.04 | +0.00053 | +0.00258 | +0.00205 |
| 3 | 953 | 570 | 21.11 | +0.00031 | +0.00128 | +0.00097 |
| 4 | 953 | 580 | 21.48 | +0.00020 | +0.00163 | +0.00143 |
| 5 | 954 | 550 | 20.37 | -0.00054 | +0.00093 | +0.00147 |

**EXP_0001_T18** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 670 | 24.81 | -0.00032 | -0.00058 | -0.00026 |
| 2 | 954 | 548 | 20.30 | -0.00053 | +0.00099 | +0.00152 |
| 3 | 953 | 383 | 14.19 | -0.00031 | +0.00113 | +0.00144 |
| 4 | 953 | 373 | 13.81 | -0.00020 | +0.00203 | +0.00223 |
| 5 | 954 | 404 | 14.96 | +0.00054 | +0.00254 | +0.00200 |

**EXP_0001_T19** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 322 | 11.93 | +0.00025 | +0.00161 | +0.00136 |
| 2 | 954 | 384 | 14.22 | +0.00044 | +0.00340 | +0.00296 |
| 3 | 953 | 413 | 15.30 | +0.00033 | +0.00337 | +0.00304 |
| 4 | 953 | 496 | 18.37 | +0.00022 | +0.00259 | +0.00237 |
| 5 | 954 | 553 | 20.48 | -0.00061 | +0.00191 | +0.00253 |

**EXP_0001_T20** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 631 | 23.37 | -0.00025 | +0.00044 | +0.00069 |
| 2 | 954 | 570 | 21.11 | -0.00044 | +0.00156 | +0.00200 |
| 3 | 953 | 540 | 20.00 | -0.00033 | +0.00199 | +0.00233 |
| 4 | 953 | 457 | 16.93 | -0.00022 | +0.00236 | +0.00258 |
| 5 | 954 | 401 | 14.85 | +0.00061 | +0.00410 | +0.00349 |

**EXP_0001_T21** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 332 | 12.30 | +0.00025 | +0.00082 | +0.00057 |
| 2 | 954 | 427 | 15.81 | +0.00044 | +0.00256 | +0.00212 |
| 3 | 953 | 474 | 17.56 | +0.00033 | +0.00294 | +0.00261 |
| 4 | 953 | 508 | 18.81 | +0.00022 | +0.00240 | +0.00219 |
| 5 | 954 | 553 | 20.48 | -0.00061 | +0.00174 | +0.00235 |

**EXP_0001_T22** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 621 | 23.00 | -0.00025 | +0.00005 | +0.00030 |
| 2 | 954 | 527 | 19.52 | -0.00044 | +0.00128 | +0.00172 |
| 3 | 953 | 479 | 17.74 | -0.00033 | +0.00225 | +0.00258 |
| 4 | 953 | 445 | 16.48 | -0.00022 | +0.00228 | +0.00250 |
| 5 | 954 | 401 | 14.85 | +0.00061 | +0.00385 | +0.00324 |

**EXP_0001_T23** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 325 | 12.04 | +0.00025 | +0.00074 | +0.00049 |
| 2 | 954 | 464 | 17.19 | +0.00044 | +0.00294 | +0.00250 |
| 3 | 953 | 581 | 21.52 | +0.00033 | +0.00231 | +0.00198 |
| 4 | 953 | 580 | 21.48 | +0.00022 | +0.00201 | +0.00179 |
| 5 | 954 | 548 | 20.30 | -0.00061 | +0.00188 | +0.00249 |

**EXP_0001_T24** folds with evidence 5/5

| fold | N parent | N selected | selected f/wk | parent effect | selected effect | uplift |
|---|---|---|---|---|---|---|
| 1 | 953 | 628 | 23.26 | -0.00025 | +0.00001 | +0.00026 |
| 2 | 954 | 490 | 18.15 | -0.00044 | +0.00193 | +0.00237 |
| 3 | 953 | 372 | 13.78 | -0.00033 | +0.00276 | +0.00309 |
| 4 | 953 | 373 | 13.81 | -0.00022 | +0.00257 | +0.00278 |
| 5 | 954 | 406 | 15.04 | +0.00061 | +0.00398 | +0.00336 |

## M–Q. Frequency / retention / parent effect / selected effect / uplift / confidence intervals

See section G (one row per trial: parent and selected frequency, retention, parent and selected effect, uplift, standardized uplift, 95% weekly-block bootstrap CI).

## R. Feature diagnostics — DIAGNOSTIC ONLY — NOT A SELECTION TRIAL

Feature-family importance (share of total importance), score/target decile monotonicity (Spearman), Ridge coefficient sign stability and yearly feature-mean shifts. Feature-family ablation is not implemented in v1.

| panel | family importance |
|---|---|
| DIR_PATH_SKEW_60|RIDGE | brownian:0.18, candles:0.15, hurst:0.06, kaufman_er:0.05, range:0.05 |
| DIR_PATH_SKEW_60|SPLINE | brownian:0.20, candles:0.11, hurst:0.07, kaufman_er:0.06, range:0.09 |
| DIR_PATH_SKEW_60|XGB | brownian:0.23, candles:0.09, hurst:0.05, kaufman_er:0.08, range:0.09 |
| DIR_RETURN_15|RIDGE | brownian:0.19, candles:0.14, hurst:0.04, kaufman_er:0.04, range:0.07 |
| DIR_RETURN_15|SPLINE | brownian:0.20, candles:0.12, hurst:0.05, kaufman_er:0.06, range:0.13 |
| DIR_RETURN_15|XGB | brownian:0.22, candles:0.08, hurst:0.05, kaufman_er:0.07, range:0.11 |
| DIR_RETURN_30|RIDGE | brownian:0.20, candles:0.14, hurst:0.05, kaufman_er:0.04, range:0.06 |
| DIR_RETURN_30|SPLINE | brownian:0.19, candles:0.11, hurst:0.08, kaufman_er:0.07, range:0.10 |
| DIR_RETURN_30|XGB | brownian:0.22, candles:0.09, hurst:0.05, kaufman_er:0.08, range:0.09 |
| DIR_RETURN_60|RIDGE | brownian:0.17, candles:0.16, hurst:0.06, kaufman_er:0.05, range:0.05 |
| DIR_RETURN_60|SPLINE | brownian:0.21, candles:0.09, hurst:0.08, kaufman_er:0.07, range:0.07 |
| DIR_RETURN_60|XGB | brownian:0.23, candles:0.11, hurst:0.05, kaufman_er:0.08, range:0.08 |

| panel | score↔target decile monotonicity (Spearman) |
|---|---|
| DIR_PATH_SKEW_60|RIDGE | +0.99 |
| DIR_PATH_SKEW_60|SPLINE | +0.96 |
| DIR_PATH_SKEW_60|XGB | +0.89 |
| DIR_RETURN_15|RIDGE | +0.99 |
| DIR_RETURN_15|SPLINE | +0.99 |
| DIR_RETURN_15|XGB | +0.99 |
| DIR_RETURN_30|RIDGE | +0.96 |
| DIR_RETURN_30|SPLINE | +0.95 |
| DIR_RETURN_30|XGB | +0.96 |
| DIR_RETURN_60|RIDGE | +0.96 |
| DIR_RETURN_60|SPLINE | +0.85 |
| DIR_RETURN_60|XGB | +0.72 |

Ridge coefficient stability DIR_PATH_SKEW_60: COUNT_BALANCE_15 (-0.187, sign agreement 100%), HURST_240 (-0.113, sign agreement 100%), RET_15 (-0.0961, sign agreement 100%), RET_5 (+0.206, sign agreement 100%), RET_60 (+0.0224, sign agreement 40%), SIGNED_VOLUME_30 (+0.138, sign agreement 100%), VOV_120 (-0.105, sign agreement 100%), day_of_week (+0.223, sign agreement 100%)

Ridge coefficient stability DIR_RETURN_15: BROWNIAN_DISP_60 (+0.164, sign agreement 100%), COUNT_BALANCE_30 (-0.0894, sign agreement 100%), COUNT_BALANCE_60 (-0.163, sign agreement 100%), RANGE_POS_120 (-0.109, sign agreement 100%), RET_15 (-0.113, sign agreement 100%), RET_5 (+0.315, sign agreement 100%), SIGNED_VOLUME_30 (+0.171, sign agreement 100%), day_of_week (+0.251, sign agreement 100%)

Ridge coefficient stability DIR_RETURN_30: BROWNIAN_DISP_60 (+0.121, sign agreement 100%), COUNT_BALANCE_15 (-0.115, sign agreement 100%), HURST_240 (-0.106, sign agreement 100%), RET_15 (-0.0975, sign agreement 100%), RET_5 (+0.213, sign agreement 100%), SIGNED_VOLUME_30 (+0.129, sign agreement 100%), VOV_120 (-0.116, sign agreement 100%), day_of_week (+0.236, sign agreement 100%)

Ridge coefficient stability DIR_RETURN_60: BROWNIAN_DISP_240 (+0.0924, sign agreement 100%), COUNT_BALANCE_15 (-0.22, sign agreement 100%), HURST_240 (-0.118, sign agreement 100%), RET_5 (+0.147, sign agreement 100%), RET_60 (+0.0305, sign agreement 40%), SIGNED_VOLUME_30 (+0.0903, sign agreement 100%), VOV_120 (-0.114, sign agreement 100%), day_of_week (+0.251, sign agreement 100%)

Largest yearly feature-mean shifts (in SD): VOV_120 1.02, VOV_60 0.97, VOV_30 0.90, RV_240 0.08, HURST_480 0.08, VR_240_2 0.07, VR_240_4 0.06, RET_15 0.06

### Score deciles (pooled DEVELOPMENT_CV)

These bins were not selection trials and cannot promote a candidate.
Using them to construct a rule requires a new registered experiment.

#### DIR_PATH_SKEW_60 / RIDGE — DIAGNOSTIC ONLY — NOT A SELECTION TRIAL

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 477 | 3.641 | -0.005465 |
| 2 | 477 | 3.641 | -0.001961 |
| 3 | 477 | 3.641 | -0.001736 |
| 4 | 476 | 3.634 | -0.001624 |
| 5 | 477 | 3.641 | +0.000470 |
| 6 | 477 | 3.641 | +0.001053 |
| 7 | 476 | 3.634 | +0.000935 |
| 8 | 477 | 3.641 | +0.001478 |
| 9 | 477 | 3.641 | +0.002812 |
| 10 | 476 | 3.634 | +0.005291 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | -0.00352 | -0.00038 | +0.00053 | +0.00103 | +0.00224 | +0.00160 | -0.00374 | +0.00156 | +0.00103 | +0.00232 |
| 2017 | -0.00548 | -0.00094 | -0.00202 | -0.00153 | -0.00012 | +0.00094 | +0.00243 | +0.00179 | +0.00313 | +0.00787 |
| 2018 | -0.00738 | -0.00403 | -0.00238 | -0.00265 | +0.00025 | +0.00092 | +0.00106 | +0.00117 | +0.00341 | +0.00504 |

#### DIR_PATH_SKEW_60 / SPLINE — DIAGNOSTIC ONLY — NOT A SELECTION TRIAL

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 477 | 3.641 | -0.004635 |
| 2 | 477 | 3.641 | -0.003141 |
| 3 | 477 | 3.641 | -0.001956 |
| 4 | 476 | 3.634 | +0.000006 |
| 5 | 477 | 3.641 | -0.000032 |
| 6 | 477 | 3.641 | +0.001524 |
| 7 | 476 | 3.634 | +0.001307 |
| 8 | 477 | 3.641 | +0.002191 |
| 9 | 477 | 3.641 | +0.001893 |
| 10 | 476 | 3.634 | +0.004099 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | -0.00346 | -0.00202 | -0.00097 | +0.00197 | +0.00142 | +0.00293 | +0.00061 | +0.00319 | +0.00052 | -0.00110 |
| 2017 | -0.00385 | -0.00292 | -0.00167 | -0.00014 | +0.00026 | +0.00094 | +0.00171 | +0.00223 | +0.00385 | +0.00532 |
| 2018 | -0.00687 | -0.00414 | -0.00274 | -0.00079 | -0.00097 | +0.00134 | +0.00122 | +0.00167 | +0.00092 | +0.00518 |

#### DIR_PATH_SKEW_60 / XGB — DIAGNOSTIC ONLY — NOT A SELECTION TRIAL

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 477 | 3.641 | -0.005319 |
| 2 | 477 | 3.641 | -0.003270 |
| 3 | 477 | 3.641 | -0.002008 |
| 4 | 476 | 3.634 | -0.000303 |
| 5 | 477 | 3.641 | +0.001650 |
| 6 | 477 | 3.641 | +0.001646 |
| 7 | 476 | 3.634 | +0.000663 |
| 8 | 477 | 3.641 | +0.001377 |
| 9 | 477 | 3.641 | +0.002176 |
| 10 | 476 | 3.634 | +0.004645 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | -0.00298 | +0.00010 | -0.00129 | +0.00138 | +0.00251 | +0.00207 | -0.00074 | +0.00037 | +0.00063 | +0.00205 |
| 2017 | -0.00500 | -0.00401 | -0.00172 | -0.00021 | +0.00154 | +0.00107 | +0.00167 | +0.00295 | +0.00319 | +0.00512 |
| 2018 | -0.00734 | -0.00487 | -0.00294 | -0.00123 | +0.00132 | +0.00200 | +0.00037 | +0.00044 | +0.00180 | +0.00528 |

#### DIR_RETURN_15 / RIDGE — DIAGNOSTIC ONLY — NOT A SELECTION TRIAL

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 477 | 3.641 | -0.003125 |
| 2 | 477 | 3.641 | -0.001926 |
| 3 | 477 | 3.641 | -0.001362 |
| 4 | 476 | 3.634 | -0.000545 |
| 5 | 477 | 3.641 | +0.000389 |
| 6 | 477 | 3.641 | -0.000268 |
| 7 | 476 | 3.634 | +0.000896 |
| 8 | 477 | 3.641 | +0.001251 |
| 9 | 477 | 3.641 | +0.001901 |
| 10 | 476 | 3.634 | +0.003107 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | -0.00254 | -0.00118 | -0.00061 | +0.00036 | +0.00085 | -0.00131 | +0.00121 | +0.00019 | +0.00162 | +0.00201 |
| 2017 | -0.00312 | -0.00206 | -0.00143 | -0.00102 | +0.00039 | -0.00002 | +0.00089 | +0.00138 | +0.00197 | +0.00359 |
| 2018 | -0.00355 | -0.00215 | -0.00163 | -0.00042 | +0.00022 | -0.00011 | +0.00076 | +0.00160 | +0.00199 | +0.00342 |

#### DIR_RETURN_15 / SPLINE — DIAGNOSTIC ONLY — NOT A SELECTION TRIAL

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 477 | 3.641 | -0.003044 |
| 2 | 477 | 3.641 | -0.001809 |
| 3 | 477 | 3.641 | -0.001656 |
| 4 | 476 | 3.634 | -0.000782 |
| 5 | 477 | 3.641 | +0.000338 |
| 6 | 477 | 3.641 | +0.000667 |
| 7 | 476 | 3.634 | +0.000351 |
| 8 | 477 | 3.641 | +0.001669 |
| 9 | 477 | 3.641 | +0.001810 |
| 10 | 476 | 3.634 | +0.002771 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | -0.00224 | -0.00079 | -0.00123 | -0.00106 | +0.00085 | -0.00042 | +0.00030 | +0.00220 | +0.00191 | +0.00142 |
| 2017 | -0.00264 | -0.00237 | -0.00127 | -0.00102 | +0.00042 | +0.00070 | +0.00069 | +0.00155 | +0.00142 | +0.00301 |
| 2018 | -0.00401 | -0.00169 | -0.00226 | -0.00044 | -0.00006 | +0.00107 | +0.00010 | +0.00156 | +0.00211 | +0.00317 |

#### DIR_RETURN_15 / XGB — DIAGNOSTIC ONLY — NOT A SELECTION TRIAL

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 477 | 3.641 | -0.003152 |
| 2 | 477 | 3.641 | -0.002353 |
| 3 | 477 | 3.641 | -0.001250 |
| 4 | 476 | 3.634 | -0.000435 |
| 5 | 477 | 3.641 | +0.000047 |
| 6 | 477 | 3.641 | +0.000782 |
| 7 | 476 | 3.634 | +0.000378 |
| 8 | 477 | 3.641 | +0.001484 |
| 9 | 477 | 3.641 | +0.001744 |
| 10 | 476 | 3.634 | +0.003072 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | -0.00251 | -0.00099 | -0.00068 | -0.00102 | +0.00004 | +0.00112 | +0.00032 | +0.00086 | +0.00130 | +0.00264 |
| 2017 | -0.00327 | -0.00269 | -0.00136 | +0.00003 | +0.00018 | +0.00071 | +0.00108 | +0.00145 | +0.00151 | +0.00289 |
| 2018 | -0.00341 | -0.00273 | -0.00155 | -0.00063 | -0.00008 | +0.00071 | -0.00031 | +0.00180 | +0.00216 | +0.00351 |

#### DIR_RETURN_30 / RIDGE — DIAGNOSTIC ONLY — NOT A SELECTION TRIAL

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 477 | 3.641 | -0.003319 |
| 2 | 477 | 3.641 | -0.001892 |
| 3 | 477 | 3.641 | -0.001465 |
| 4 | 476 | 3.634 | -0.001025 |
| 5 | 477 | 3.641 | +0.000761 |
| 6 | 477 | 3.641 | +0.000294 |
| 7 | 476 | 3.634 | +0.000618 |
| 8 | 477 | 3.641 | +0.001250 |
| 9 | 477 | 3.641 | +0.001524 |
| 10 | 476 | 3.634 | +0.003178 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | -0.00186 | -0.00013 | -0.00163 | -0.00000 | +0.00300 | +0.00111 | -0.00005 | +0.00004 | -0.00026 | +0.00212 |
| 2017 | -0.00318 | -0.00282 | -0.00134 | -0.00062 | -0.00051 | +0.00051 | +0.00103 | +0.00170 | +0.00255 | +0.00367 |
| 2018 | -0.00470 | -0.00185 | -0.00155 | -0.00187 | +0.00097 | -0.00025 | +0.00053 | +0.00137 | +0.00156 | +0.00353 |

#### DIR_RETURN_30 / SPLINE — DIAGNOSTIC ONLY — NOT A SELECTION TRIAL

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 477 | 3.641 | -0.003037 |
| 2 | 477 | 3.641 | -0.001599 |
| 3 | 477 | 3.641 | -0.001922 |
| 4 | 476 | 3.634 | -0.001202 |
| 5 | 477 | 3.641 | +0.000094 |
| 6 | 477 | 3.641 | +0.001237 |
| 7 | 476 | 3.634 | +0.000816 |
| 8 | 477 | 3.641 | +0.001129 |
| 9 | 477 | 3.641 | +0.001353 |
| 10 | 476 | 3.634 | +0.003057 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | -0.00180 | -0.00068 | +0.00049 | +0.00042 | -0.00023 | +0.00133 | +0.00141 | -0.00035 | +0.00140 | +0.00116 |
| 2017 | -0.00305 | -0.00135 | -0.00205 | -0.00159 | +0.00021 | +0.00105 | +0.00086 | +0.00189 | +0.00142 | +0.00356 |
| 2018 | -0.00391 | -0.00238 | -0.00281 | -0.00165 | +0.00014 | +0.00137 | +0.00050 | +0.00117 | +0.00128 | +0.00346 |

#### DIR_RETURN_30 / XGB — DIAGNOSTIC ONLY — NOT A SELECTION TRIAL

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 477 | 3.641 | -0.003319 |
| 2 | 477 | 3.641 | -0.001956 |
| 3 | 477 | 3.641 | -0.002007 |
| 4 | 476 | 3.634 | +0.000381 |
| 5 | 477 | 3.641 | -0.000069 |
| 6 | 477 | 3.641 | +0.000770 |
| 7 | 476 | 3.634 | +0.000734 |
| 8 | 477 | 3.641 | +0.000978 |
| 9 | 477 | 3.641 | +0.001597 |
| 10 | 476 | 3.634 | +0.002819 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | -0.00077 | -0.00069 | +0.00006 | +0.00030 | -0.00036 | +0.00069 | +0.00258 | +0.00029 | +0.00009 | +0.00120 |
| 2017 | -0.00432 | -0.00174 | -0.00196 | -0.00004 | +0.00009 | +0.00147 | +0.00093 | +0.00092 | +0.00170 | +0.00334 |
| 2018 | -0.00364 | -0.00310 | -0.00363 | +0.00096 | -0.00008 | +0.00006 | -0.00003 | +0.00128 | +0.00207 | +0.00327 |

#### DIR_RETURN_60 / RIDGE — DIAGNOSTIC ONLY — NOT A SELECTION TRIAL

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 477 | 3.641 | -0.002927 |
| 2 | 477 | 3.641 | -0.001067 |
| 3 | 477 | 3.641 | -0.001395 |
| 4 | 476 | 3.634 | -0.000613 |
| 5 | 477 | 3.641 | +0.000752 |
| 6 | 477 | 3.641 | +0.000301 |
| 7 | 476 | 3.634 | +0.000898 |
| 8 | 477 | 3.641 | +0.000987 |
| 9 | 477 | 3.641 | +0.002590 |
| 10 | 476 | 3.634 | +0.002119 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | -0.00143 | +0.00053 | -0.00118 | +0.00366 | +0.00101 | -0.00108 | -0.00109 | +0.00064 | +0.00264 | +0.00025 |
| 2017 | -0.00307 | -0.00056 | -0.00208 | +0.00073 | +0.00088 | +0.00053 | +0.00097 | +0.00196 | +0.00408 | +0.00324 |
| 2018 | -0.00444 | -0.00275 | -0.00064 | -0.00370 | +0.00054 | +0.00061 | +0.00142 | +0.00020 | +0.00168 | +0.00282 |

#### DIR_RETURN_60 / SPLINE — DIAGNOSTIC ONLY — NOT A SELECTION TRIAL

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 477 | 3.641 | -0.003008 |
| 2 | 477 | 3.641 | -0.000648 |
| 3 | 477 | 3.641 | -0.000343 |
| 4 | 476 | 3.634 | -0.000682 |
| 5 | 477 | 3.641 | -0.000012 |
| 6 | 477 | 3.641 | +0.001963 |
| 7 | 476 | 3.634 | +0.000248 |
| 8 | 477 | 3.641 | +0.001035 |
| 9 | 477 | 3.641 | +0.000196 |
| 10 | 476 | 3.634 | +0.002895 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | -0.00239 | +0.00085 | -0.00110 | +0.00130 | +0.00188 | +0.00286 | +0.00054 | +0.00034 | +0.00004 | +0.00052 |
| 2017 | -0.00285 | +0.00049 | -0.00025 | -0.00099 | +0.00033 | +0.00009 | +0.00204 | +0.00161 | +0.00125 | +0.00323 |
| 2018 | -0.00418 | -0.00319 | -0.00009 | -0.00119 | -0.00107 | +0.00328 | -0.00136 | +0.00088 | -0.00064 | +0.00387 |

#### DIR_RETURN_60 / XGB — DIAGNOSTIC ONLY — NOT A SELECTION TRIAL

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 477 | 3.641 | -0.003472 |
| 2 | 477 | 3.641 | -0.000990 |
| 3 | 477 | 3.641 | -0.001778 |
| 4 | 476 | 3.634 | +0.000107 |
| 5 | 477 | 3.641 | +0.001262 |
| 6 | 477 | 3.641 | +0.001488 |
| 7 | 476 | 3.634 | +0.000971 |
| 8 | 477 | 3.641 | +0.000034 |
| 9 | 477 | 3.641 | +0.000883 |
| 10 | 476 | 3.634 | +0.003144 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | -0.00180 | -0.00080 | +0.00078 | +0.00030 | +0.00348 | +0.00259 | +0.00153 | -0.00375 | +0.00050 | +0.00124 |
| 2017 | -0.00308 | -0.00087 | -0.00143 | +0.00061 | +0.00061 | +0.00191 | +0.00038 | +0.00090 | +0.00110 | +0.00445 |
| 2018 | -0.00559 | -0.00131 | -0.00421 | -0.00055 | +0.00088 | +0.00073 | +0.00121 | +0.00043 | +0.00084 | +0.00282 |

### Diagnostic targets (means over model-eligible events; report only) — DIAGNOSTIC ONLY — NOT A SELECTION TRIAL

| diagnostic target | mean |
|---|---|
| DIAG_FIRST_PASSAGE_0.5 | -0.011368 |
| DIAG_FIRST_PASSAGE_1.0 | 0.000700 |
| DIAG_FWD_RV_60 | 0.005076 |
| DIAG_MAE_120 | -0.013884 |
| DIAG_MAE_15 | -0.003346 |
| DIAG_MAE_30 | -0.005616 |
| DIAG_MAE_60 | -0.008979 |
| DIAG_MFE_120 | 0.014087 |
| DIAG_MFE_15 | 0.003350 |
| DIAG_MFE_30 | 0.005590 |
| DIAG_MFE_60 | 0.009065 |
| DIAG_PATH_EFFICIENCY_60 | 0.368046 |
| DIAG_PATH_LENGTH_60 | 0.031921 |
| DIAG_RET_120 | 0.000207 |
| DIAG_RET_5 | -0.000008 |
| DIAG_TIME_TO_MAE_120 | 59.738136 |
| DIAG_TIME_TO_MAE_15 | 8.010843 |
| DIAG_TIME_TO_MAE_30 | 15.518538 |
| DIAG_TIME_TO_MAE_60 | 30.241693 |
| DIAG_TIME_TO_MFE_120 | 61.175289 |
| DIAG_TIME_TO_MFE_15 | 7.994928 |
| DIAG_TIME_TO_MFE_30 | 15.617174 |
| DIAG_TIME_TO_MFE_60 | 30.788388 |

## S. Filter / component ladder

No `filter_ladder` declared in EVENT_SPEC.

## T. Sensitivity diagnostics

status RUN; verdicts per candidate group: {'DIR_PATH_SKEW_60|LOWER_HALF': 'PASSED', 'DIR_PATH_SKEW_60|UPPER_HALF': 'PASSED', 'DIR_RETURN_15|LOWER_HALF': 'PASSED', 'DIR_RETURN_15|UPPER_HALF': 'PASSED', 'DIR_RETURN_30|LOWER_HALF': 'PASSED', 'DIR_RETURN_30|UPPER_HALF': 'PASSED'}

* DIR_PATH_SKEW_60|LOWER_HALF: **PASSED**; every_n_bars×0.75→34: models uplift>0 3/3, freq ok 3/3; every_n_bars×1.25→56: models uplift>0 3/3, freq ok 3/3
* DIR_PATH_SKEW_60|UPPER_HALF: **PASSED**; every_n_bars×0.75→34: models uplift>0 3/3, freq ok 3/3; every_n_bars×1.25→56: models uplift>0 3/3, freq ok 3/3
* DIR_RETURN_15|LOWER_HALF: **PASSED**; every_n_bars×0.75→34: models uplift>0 3/3, freq ok 3/3; every_n_bars×1.25→56: models uplift>0 3/3, freq ok 3/3
* DIR_RETURN_15|UPPER_HALF: **PASSED**; every_n_bars×0.75→34: models uplift>0 3/3, freq ok 3/3; every_n_bars×1.25→56: models uplift>0 3/3, freq ok 3/3
* DIR_RETURN_30|LOWER_HALF: **PASSED**; every_n_bars×0.75→34: models uplift>0 3/3, freq ok 3/3; every_n_bars×1.25→56: models uplift>0 3/3, freq ok 3/3
* DIR_RETURN_30|UPPER_HALF: **PASSED**; every_n_bars×0.75→34: models uplift>0 3/3, freq ok 3/3; every_n_bars×1.25→56: models uplift>0 3/3, freq ok 3/3

Probes can only confirm or veto; a better probe never replaces the base parameter.

### External verification (model paths)

| path | label | mode |
|---|---|---|
| DIR_PATH_SKEW_60|RIDGE | RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE | strong |
| DIR_PATH_SKEW_60|SPLINE | RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE | strong |
| DIR_PATH_SKEW_60|XGB | RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE | strong |
| DIR_RETURN_15|RIDGE | RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE | strong |
| DIR_RETURN_15|SPLINE | RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE | strong |
| DIR_RETURN_15|XGB | RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE | strong |
| DIR_RETURN_30|RIDGE | RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE | strong |
| DIR_RETURN_30|SPLINE | RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE | strong |
| DIR_RETURN_30|XGB | RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE | strong |

## U. Why each shortlisted configuration was selected — how it emerged

### Rank 1: DIR_RETURN_15|LOWER_HALF

How this configuration emerged

- Base event frequency: 36.5/week.
- RIDGE, SPLINE, XGB all evaluated the same frozen 56-feature bank.
- No feature threshold was searched; no feature subset, lookback or horizon was searched.
- LOWER_HALF was predeclared before results (frozen score-state definition: train-only median).
- Selected frequency: 17.67/week (retention 0.49).
- Parent effect: -0.000031; selected effect: +0.001447; uplift: +0.001478 (standardized +0.224) — medians over the 3 eligible models.
- RIDGE: positive uplift in 3/3 eligible years; positive selected effect in 3/3 years; positive uplift in 5/5 DEVELOPMENT_CV folds; bootstrap CI lower bound +0.00116.
- SPLINE: positive uplift in 3/3 eligible years; positive selected effect in 3/3 years; positive uplift in 5/5 DEVELOPMENT_CV folds; bootstrap CI lower bound +0.00126.
- XGB: positive uplift in 3/3 eligible years; positive selected effect in 3/3 years; positive uplift in 5/5 DEVELOPMENT_CV folds; bootstrap CI lower bound +0.00137.
- Bonferroni adjusted p (experiment): 0.01199; campaign Bonferroni adjusted p: 0.01199; BH q experiment 0.0004998, campaign 0.0004998.
- Model agreement: 3/3.
- Selection trial count when observed: 24.
- CONCERNS surfaced: YEAR_CONCENTRATION_WARNING: one calendar year carries > 35% of total absolute uplift; external verification: RIDGE=RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE(strong), SPLINE=RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE(strong), XGB=RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE(strong); campaign-adjusted values will keep changing as more experiments are revealed.

### Rank 2: DIR_RETURN_15|UPPER_HALF

How this configuration emerged

- Base event frequency: 36.5/week.
- RIDGE, SPLINE, XGB all evaluated the same frozen 56-feature bank.
- No feature threshold was searched; no feature subset, lookback or horizon was searched.
- UPPER_HALF was predeclared before results (frozen score-state definition: train-only median).
- Selected frequency: 18.72/week (retention 0.51).
- Parent effect: +0.000031; selected effect: +0.001429; uplift: +0.001398 (standardized +0.212) — medians over the 3 eligible models.
- RIDGE: positive uplift in 3/3 eligible years; positive selected effect in 3/3 years; positive uplift in 5/5 DEVELOPMENT_CV folds; bootstrap CI lower bound +0.00119.
- SPLINE: positive uplift in 3/3 eligible years; positive selected effect in 3/3 years; positive uplift in 5/5 DEVELOPMENT_CV folds; bootstrap CI lower bound +0.00121.
- XGB: positive uplift in 3/3 eligible years; positive selected effect in 3/3 years; positive uplift in 5/5 DEVELOPMENT_CV folds; bootstrap CI lower bound +0.00121.
- Bonferroni adjusted p (experiment): 0.01199; campaign Bonferroni adjusted p: 0.01199; BH q experiment 0.0004998, campaign 0.0004998.
- Model agreement: 3/3.
- Selection trial count when observed: 24.
- CONCERNS surfaced: YEAR_CONCENTRATION_WARNING: one calendar year carries > 35% of total absolute uplift; external verification: RIDGE=RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE(strong), SPLINE=RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE(strong), XGB=RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE(strong); campaign-adjusted values will keep changing as more experiments are revealed.

### Rank 3: DIR_RETURN_30|UPPER_HALF

How this configuration emerged

- Base event frequency: 36.5/week.
- RIDGE, SPLINE, XGB all evaluated the same frozen 56-feature bank.
- No feature threshold was searched; no feature subset, lookback or horizon was searched.
- UPPER_HALF was predeclared before results (frozen score-state definition: train-only median).
- Selected frequency: 17.23/week (retention 0.47).
- Parent effect: -0.000008; selected effect: +0.001446; uplift: +0.001454 (standardized +0.142) — medians over the 3 eligible models.
- RIDGE: positive uplift in 3/3 eligible years; positive selected effect in 3/3 years; positive uplift in 5/5 DEVELOPMENT_CV folds; bootstrap CI lower bound +0.00112.
- SPLINE: positive uplift in 3/3 eligible years; positive selected effect in 3/3 years; positive uplift in 5/5 DEVELOPMENT_CV folds; bootstrap CI lower bound +0.00129.
- XGB: positive uplift in 3/3 eligible years; positive selected effect in 3/3 years; positive uplift in 5/5 DEVELOPMENT_CV folds; bootstrap CI lower bound +0.00102.
- Bonferroni adjusted p (experiment): 0.01199; campaign Bonferroni adjusted p: 0.01199; BH q experiment 0.0004998, campaign 0.0004998.
- Model agreement: 3/3.
- Selection trial count when observed: 24.
- CONCERNS surfaced: YEAR_CONCENTRATION_WARNING: one calendar year carries > 35% of total absolute uplift; external verification: RIDGE=RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE(strong), SPLINE=RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE(strong), XGB=RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE(strong); campaign-adjusted values will keep changing as more experiments are revealed.

### Rank 4: DIR_RETURN_30|LOWER_HALF

How this configuration emerged

- Base event frequency: 36.5/week.
- RIDGE, SPLINE, XGB all evaluated the same frozen 56-feature bank.
- No feature threshold was searched; no feature subset, lookback or horizon was searched.
- LOWER_HALF was predeclared before results (frozen score-state definition: train-only median).
- Selected frequency: 18.19/week (retention 0.50).
- Parent effect: +0.000008; selected effect: +0.001452; uplift: +0.001444 (standardized +0.141) — medians over the 2 eligible models.
- SPLINE: positive uplift in 3/3 eligible years; positive selected effect in 3/3 years; positive uplift in 5/5 DEVELOPMENT_CV folds; bootstrap CI lower bound +0.00115.
- XGB: positive uplift in 3/3 eligible years; positive selected effect in 3/3 years; positive uplift in 5/5 DEVELOPMENT_CV folds; bootstrap CI lower bound +0.00113.
- Bonferroni adjusted p (experiment): 0.01199; campaign Bonferroni adjusted p: 0.01199; BH q experiment 0.0004998, campaign 0.0004998.
- Model agreement: 2/3.
- Selection trial count when observed: 24.
- CONCERNS surfaced: YEAR_CONCENTRATION_WARNING: one calendar year carries > 35% of total absolute uplift; not every model is eligible: RIDGE=REJECTED_INSTABILITY; external verification: RIDGE=RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE(strong), SPLINE=RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE(strong), XGB=RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE(strong); campaign-adjusted values will keep changing as more experiments are revealed.

### Rank 5: DIR_PATH_SKEW_60|UPPER_HALF

How this configuration emerged

- Base event frequency: 36.5/week.
- RIDGE, SPLINE, XGB all evaluated the same frozen 56-feature bank.
- No feature threshold was searched; no feature subset, lookback or horizon was searched.
- UPPER_HALF was predeclared before results (frozen score-state definition: train-only median).
- Selected frequency: 17.51/week (retention 0.48).
- Parent effect: +0.000125; selected effect: +0.002153; uplift: +0.002029 (standardized +0.125) — medians over the 3 eligible models.
- RIDGE: positive uplift in 3/3 eligible years; positive selected effect in 3/3 years; positive uplift in 5/5 DEVELOPMENT_CV folds; bootstrap CI lower bound +0.00192.
- SPLINE: positive uplift in 3/3 eligible years; positive selected effect in 3/3 years; positive uplift in 5/5 DEVELOPMENT_CV folds; bootstrap CI lower bound +0.00157.
- XGB: positive uplift in 3/3 eligible years; positive selected effect in 3/3 years; positive uplift in 5/5 DEVELOPMENT_CV folds; bootstrap CI lower bound +0.00148.
- Bonferroni adjusted p (experiment): 0.01199; campaign Bonferroni adjusted p: 0.01199; BH q experiment 0.0004998, campaign 0.0004998.
- Model agreement: 3/3.
- Selection trial count when observed: 24.
- CONCERNS surfaced: YEAR_CONCENTRATION_WARNING: one calendar year carries > 35% of total absolute uplift; external verification: RIDGE=RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE(strong), SPLINE=RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE(strong), XGB=RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE(strong); campaign-adjusted values will keep changing as more experiments are revealed.

## V. Why every other configuration was rejected

| trial | target/model/state | decision | reason |
|---|---|---|---|
| EXP_0001_T08 | DIR_RETURN_30/RIDGE/LOWER_HALF | REJECTED_INSTABILITY | [REJECTED_INSTABILITY] positive selected-effect years 2/3 < 70% |
| EXP_0001_T13 | DIR_RETURN_60/RIDGE/UPPER_HALF | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift 0.095 < 0.1 at retention 0.43 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS) |
| EXP_0001_T14 | DIR_RETURN_60/RIDGE/LOWER_HALF | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift 0.072 < 0.1 at retention 0.57 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_INSTABILITY] positive selected-effect years 2/3 < 70% |
| EXP_0001_T15 | DIR_RETURN_60/SPLINE/UPPER_HALF | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift 0.063 < 0.1 at retention 0.47 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_INSTABILITY] positive-uplift years 2/3 < 70% |
| EXP_0001_T16 | DIR_RETURN_60/SPLINE/LOWER_HALF | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift 0.056 < 0.1 at retention 0.53 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_INSTABILITY] positive selected-effect years 2/3 < 70%, positive-uplift years 2/3 < 70% |
| EXP_0001_T17 | DIR_RETURN_60/XGB/UPPER_HALF | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift 0.076 < 0.1 at retention 0.50 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_INSTABILITY] positive selected-effect years 2/3 < 70%, positive-uplift years 2/3 < 70% |
| EXP_0001_T18 | DIR_RETURN_60/XGB/LOWER_HALF | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift 0.077 < 0.1 at retention 0.50 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_INSTABILITY] positive selected-effect years 2/3 < 70%, positive-uplift years 2/3 < 70% |
| EXP_0001_T20 | DIR_PATH_SKEW_60/RIDGE/LOWER_HALF | IS_SHORTLIST_ELIGIBLE | - |
| EXP_0001_T22 | DIR_PATH_SKEW_60/SPLINE/LOWER_HALF | IS_SHORTLIST_ELIGIBLE | - |
| EXP_0001_T24 | DIR_PATH_SKEW_60/XGB/LOWER_HALF | REJECTED_INSTABILITY | [REJECTED_INSTABILITY] positive selected-effect years 2/3 < 70% |

## W. Non-promotable interesting observations (registry/observations.csv)

**DIAGNOSTIC ONLY — NOT A SELECTION TRIAL.** Anything here can only inspire a NEW registered experiment (which adds 24 selection trials to the campaign universe).

| id | category | description |
|---|---|---|
| OBS_00001 | score_decile_shape | DIR_RETURN_15/RIDGE: mean target top decile +0.00311 vs bottom decile -0.00312 (pooled DEVELOPMENT_CV deciles; not selection trials) |
| OBS_00002 | feature_importance | DIR_RETURN_15/RIDGE: top features RET_5 (0.3155), day_of_week (0.2511), SIGNED_VOLUME_30 (0.1712) (diagnostic importance; models still consume the whole bank) |
| OBS_00003 | score_decile_shape | DIR_RETURN_15/SPLINE: mean target top decile +0.00277 vs bottom decile -0.00304 (pooled DEVELOPMENT_CV deciles; not selection trials) |
| OBS_00004 | feature_importance | DIR_RETURN_15/SPLINE: top features RET_5 (1.939), RANGE_POS_15 (1.192), RANGE_POS_30 (0.7684) (diagnostic importance; models still consume the whole bank) |
| OBS_00005 | score_decile_shape | DIR_RETURN_15/XGB: mean target top decile +0.00307 vs bottom decile -0.00315 (pooled DEVELOPMENT_CV deciles; not selection trials) |
| OBS_00006 | feature_importance | DIR_RETURN_15/XGB: top features RET_5 (0.06643), RANGE_POS_15 (0.05322), day_of_week (0.04875) (diagnostic importance; models still consume the whole bank) |
| OBS_00007 | score_decile_shape | DIR_RETURN_30/RIDGE: mean target top decile +0.00318 vs bottom decile -0.00332 (pooled DEVELOPMENT_CV deciles; not selection trials) |
| OBS_00008 | feature_importance | DIR_RETURN_30/RIDGE: top features day_of_week (0.2358), RET_5 (0.2126), SIGNED_VOLUME_30 (0.1286) (diagnostic importance; models still consume the whole bank) |
| OBS_00009 | score_decile_shape | DIR_RETURN_30/SPLINE: mean target top decile +0.00306 vs bottom decile -0.00304 (pooled DEVELOPMENT_CV deciles; not selection trials) |
| OBS_00010 | feature_importance | DIR_RETURN_30/SPLINE: top features RET_5 (1.287), RANGE_POS_15 (0.7884), COUNT_BALANCE_15 (0.7209) (diagnostic importance; models still consume the whole bank) |
| OBS_00011 | score_decile_shape | DIR_RETURN_30/XGB: mean target top decile +0.00282 vs bottom decile -0.00332 (pooled DEVELOPMENT_CV deciles; not selection trials) |
| OBS_00012 | feature_importance | DIR_RETURN_30/XGB: top features day_of_week (0.05351), RET_5 (0.04554), RANGE_POS_15 (0.03796) (diagnostic importance; models still consume the whole bank) |
| OBS_00013 | score_decile_shape | DIR_RETURN_60/RIDGE: mean target top decile +0.00212 vs bottom decile -0.00293 (pooled DEVELOPMENT_CV deciles; not selection trials) |
| OBS_00014 | feature_importance | DIR_RETURN_60/RIDGE: top features day_of_week (0.2509), COUNT_BALANCE_15 (0.2204), RET_5 (0.1468) (diagnostic importance; models still consume the whole bank) |
| OBS_00015 | score_decile_shape | DIR_RETURN_60/SPLINE: mean target top decile +0.00289 vs bottom decile -0.00301 (pooled DEVELOPMENT_CV deciles; not selection trials) |
| OBS_00016 | feature_importance | DIR_RETURN_60/SPLINE: top features RET_5 (1.043), HURST_240 (0.8424), VR_60_2 (0.708) (diagnostic importance; models still consume the whole bank) |
| OBS_00017 | score_decile_shape | DIR_RETURN_60/XGB: mean target top decile +0.00314 vs bottom decile -0.00347 (pooled DEVELOPMENT_CV deciles; not selection trials) |
| OBS_00018 | feature_importance | DIR_RETURN_60/XGB: top features day_of_week (0.05609), RET_5 (0.03022), RANGE_POS_15 (0.02681) (diagnostic importance; models still consume the whole bank) |
| OBS_00019 | score_decile_shape | DIR_PATH_SKEW_60/RIDGE: mean target top decile +0.00529 vs bottom decile -0.00547 (pooled DEVELOPMENT_CV deciles; not selection trials) |
| OBS_00020 | feature_importance | DIR_PATH_SKEW_60/RIDGE: top features day_of_week (0.2232), RET_5 (0.2061), COUNT_BALANCE_15 (0.1866) (diagnostic importance; models still consume the whole bank) |
| OBS_00021 | score_decile_shape | DIR_PATH_SKEW_60/SPLINE: mean target top decile +0.00410 vs bottom decile -0.00464 (pooled DEVELOPMENT_CV deciles; not selection trials) |
| OBS_00022 | feature_importance | DIR_PATH_SKEW_60/SPLINE: top features RET_5 (1.327), COUNT_BALANCE_15 (0.7284), RANGE_POS_15 (0.7208) (diagnostic importance; models still consume the whole bank) |
| OBS_00023 | score_decile_shape | DIR_PATH_SKEW_60/XGB: mean target top decile +0.00464 vs bottom decile -0.00532 (pooled DEVELOPMENT_CV deciles; not selection trials) |
| OBS_00024 | feature_importance | DIR_PATH_SKEW_60/XGB: top features day_of_week (0.05753), RET_5 (0.04162), RANGE_POS_15 (0.03721) (diagnostic importance; models still consume the whole bank) |
| OBS_00025 | long_short_asymmetry | DIR_RETURN_15: mean uplift UPPER_HALF +0.00140 vs LOWER_HALF +0.00147 across models |
| OBS_00026 | long_short_asymmetry | DIR_RETURN_30: mean uplift UPPER_HALF +0.00145 vs LOWER_HALF +0.00137 across models |
| OBS_00027 | long_short_asymmetry | DIR_RETURN_60: mean uplift UPPER_HALF +0.00118 vs LOWER_HALF +0.00103 across models |
| OBS_00028 | long_short_asymmetry | DIR_PATH_SKEW_60: mean uplift UPPER_HALF +0.00213 vs LOWER_HALF +0.00202 across models |
| OBS_00029 | year_concentration | EXP_0001_T01: YEAR_CONCENTRATION_WARNING (largest year share 0.43 of total absolute uplift) |
| OBS_00030 | year_concentration | EXP_0001_T02: YEAR_CONCENTRATION_WARNING (largest year share 0.43 of total absolute uplift) |
| OBS_00031 | year_concentration | EXP_0001_T03: YEAR_CONCENTRATION_WARNING (largest year share 0.46 of total absolute uplift) |
| OBS_00032 | year_concentration | EXP_0001_T04: YEAR_CONCENTRATION_WARNING (largest year share 0.46 of total absolute uplift) |
| OBS_00033 | year_concentration | EXP_0001_T05: YEAR_CONCENTRATION_WARNING (largest year share 0.44 of total absolute uplift) |
| OBS_00034 | year_concentration | EXP_0001_T06: YEAR_CONCENTRATION_WARNING (largest year share 0.44 of total absolute uplift) |
| OBS_00035 | year_concentration | EXP_0001_T07: YEAR_CONCENTRATION_WARNING (largest year share 0.50 of total absolute uplift) |
| OBS_00036 | year_concentration | EXP_0001_T08: YEAR_CONCENTRATION_WARNING (largest year share 0.50 of total absolute uplift) |
| OBS_00037 | year_concentration | EXP_0001_T09: YEAR_CONCENTRATION_WARNING (largest year share 0.48 of total absolute uplift) |
| OBS_00038 | year_concentration | EXP_0001_T10: YEAR_CONCENTRATION_WARNING (largest year share 0.48 of total absolute uplift) |
| OBS_00039 | year_concentration | EXP_0001_T11: YEAR_CONCENTRATION_WARNING (largest year share 0.50 of total absolute uplift) |
| OBS_00040 | year_concentration | EXP_0001_T12: YEAR_CONCENTRATION_WARNING (largest year share 0.50 of total absolute uplift) |
| OBS_00041 | year_concentration | EXP_0001_T13: YEAR_CONCENTRATION_WARNING (largest year share 0.50 of total absolute uplift) |
| OBS_00042 | year_concentration | EXP_0001_T14: YEAR_CONCENTRATION_WARNING (largest year share 0.50 of total absolute uplift) |
| OBS_00043 | year_concentration | EXP_0001_T15: YEAR_CONCENTRATION_WARNING (largest year share 0.51 of total absolute uplift) |
| OBS_00044 | year_concentration | EXP_0001_T16: YEAR_CONCENTRATION_WARNING (largest year share 0.51 of total absolute uplift) |
| OBS_00045 | year_concentration | EXP_0001_T17: YEAR_CONCENTRATION_WARNING (largest year share 0.51 of total absolute uplift) |
| OBS_00046 | year_concentration | EXP_0001_T18: YEAR_CONCENTRATION_WARNING (largest year share 0.51 of total absolute uplift) |
| OBS_00047 | year_concentration | EXP_0001_T19: YEAR_CONCENTRATION_WARNING (largest year share 0.48 of total absolute uplift) |
| OBS_00048 | year_concentration | EXP_0001_T20: YEAR_CONCENTRATION_WARNING (largest year share 0.48 of total absolute uplift) |
| OBS_00049 | year_concentration | EXP_0001_T21: YEAR_CONCENTRATION_WARNING (largest year share 0.50 of total absolute uplift) |
| OBS_00050 | year_concentration | EXP_0001_T22: YEAR_CONCENTRATION_WARNING (largest year share 0.50 of total absolute uplift) |
| OBS_00051 | year_concentration | EXP_0001_T23: YEAR_CONCENTRATION_WARNING (largest year share 0.49 of total absolute uplift) |
| OBS_00052 | year_concentration | EXP_0001_T24: YEAR_CONCENTRATION_WARNING (largest year share 0.49 of total absolute uplift) |

## X. Exact hashes

| item | sha256 |
|---|---|
| manifest_sha256 | 0dc2d4aae44fe2ceaf261ad282ea739fe844099f7425018ae9f5541f332e4757 |
| manifest_hash | ad26f7d1b5977e883081b567b6c856c513ec95f91695d98b975f4c28dc67aff5 |
| event_hash | dd3dc43384677409442cf430c5708bf8e5f0fafe10f4b6665c2cdd5d0e61e2e4 |
| event_py | 47e3f563c012e50b1a7f8a30d8bf81e106793a1d594ffd5bb2d922660ad10585 |
| event_spec | 9b17cc874e0a2d4b7c58b552bf3df5b87a5978ec80ba401beb10e063a0de22eb |
| partitions_hash | 8e35ba8724b68cc65dde56ecb0259a4e687efe4410d7ae4449d58d79e2abf4fd |
| frozen_bundle_hash | 65d7d0ad47aa1748956b2d5503c3cf532cf130627355cfdbd143bac001adec6d |
| engine_code_hash | c66f17efa976366e426023e1b7da97e3e30bc95e51936cfc61677ee404f57942 |
| engine_version | v1.1.0 |
| trial_ledger_hash | dbe6c2d6e86d29bb8805be8fdb829d930de87c17405a6d64ae93814717a7c0e5 |
| is_data_fingerprint | 99deba244cd2790651042661941d558e73e3f0c42b3f508c0acf26dee9be2371 |
| results_sha256 | 9f044b2747e12236011fd6fadf42566f681010ad3c0ebe304984f4ecbded0ad8 |
| verifier_pin | 624c8b7f0502abf6c5d453d501e96e3172367035 |

## Y. OOS status

**OOS status = NOT ACCESSED**

OOS requires a manual human approval file. Compute the hashes to reference with `python scripts/show_approval_hashes.py --experiment EXP_0001`. The LLM / scripts never create `approvals/EXP_0001_OOS_APPROVAL.yaml`; at most 2 TARGET|SIDE groups from the top-5 list may be approved and every approved group runs all three frozen models.

