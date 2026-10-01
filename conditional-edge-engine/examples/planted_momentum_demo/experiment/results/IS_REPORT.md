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
| DIAG_FIRST_PASSAGE_0.5 | -0.006121 |
| DIAG_FIRST_PASSAGE_1.0 | -0.011892 |
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
| DIR_RETURN_60|RIDGE | RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE | strong |
| DIR_RETURN_60|SPLINE | RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE | strong |
| DIR_RETURN_60|XGB | RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE | strong |

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
| OBS_00053 | path_continuation | raw base event: continuation at 60 bars 2898/5718 (DIAGNOSTIC ONLY — NOT A SELECTION TRIAL; GROSS — COSTS NOT APPLIED) |
| OBS_00054 | path_dominance | raw base event: median path dominance (MFE+MAE) at 60 bars 1.8510916339164396 points (DIAGNOSTIC ONLY — NOT A SELECTION TRIAL; GROSS — COSTS NOT APPLIED) |
| OBS_00055 | bracket_surface_description | 24 of 64 fixed bracket cells have positive conservative mean gross points for the raw base event (descriptive count only; DIAGNOSTIC ONLY — NO BRACKET WAS SELECTED; GROSS — COSTS NOT APPLIED) |


---
# NON-PROMOTABLE PATH DIAGNOSTICS

Sections F–L and U–V above are the **PROMOTION EVIDENCE** (the 24 selection trials). Everything below is **NON-PROMOTABLE PATH DIAGNOSTICS**: it is not part of the 24-trial BH / Bonferroni family and cannot create, promote, rescue or rank any candidate.

## Z. FORWARD PATH DIAGNOSTICS

**DIAGNOSTIC ONLY — NOT A SELECTION TRIAL** — **GROSS — COSTS NOT APPLIED** — **DIAGNOSTIC ONLY — NO BRACKET WAS SELECTED**

> These statistics were viewed post-event-definition as diagnostics. They are not eligible to create or promote a candidate in this experiment. Any trading rule, threshold, bracket, horizon, percentile, or filter inspired by these diagnostics requires a NEW registered experiment or a separate monetisation study.

**PATH DIAGNOSTICS ARE NON-PROMOTABLE: they never change candidate status, trial rank, group rank, the top-5 IS list, campaign BH/Bonferroni, human-approval eligibility or OOS group ordering.**

**Human interpretation rule.** A human may approve, decline, or approve fewer than the eligible maximum from the deterministic eligible list. A human may NOT use a visually attractive path or bracket diagnostic to substitute a non-eligible or lower-ranked configuration that the engine did not place in the approval-eligible set. If diagnostics inspire a different rule, bracket, horizon, threshold or filter, a NEW experiment or a SEPARATE MONETISATION STUDY is required; there is no current-experiment promotion.

Horizons [5, 15, 30, 60, 120] bars; tick size 0.25 points (instrument config); sigma_ref = RV_60 / sqrt(60) (sigma_ref = RV_60 / sqrt(60), where RV_60 = sqrt(sum_{i=1..60} r_i^2) over the 60 one-minute log returns ending at the last bar completed by event_time (the frozen feature-engine RV_60); sigma_ref is the corresponding one-bar RMS log-return scale); percentiles: linear_interpolation. Events: 5,718 model-eligible of 5,728; PATH_TIMESTAMP_INELIGIBLE per horizon: {'120': 1040, '15': 0, '30': 0, '5': 0, '60': 0}. Contexts: ALL events and UPPER/LOWER_HALF of every target × model (DEVELOPMENT_CV pooled validation events; identical event sets are grouped). Full detail: `results/PATH_DIAGNOSTICS.json`. No OOS or lockbox row entered any number below.

### Z.1 Endpoint returns (ALL events; directional log return)

| h | N | mean | median | P25 | P75 | P5 | P95 | std | mean raw pts | median raw pts |
|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 5718 | -0.000008 | -0.000043 | -0.001903 | 0.001877 | -0.004598 | 0.004712 | 0.002825 | -0.079 | -0.196 |
| 15 | 5718 | 0.000015 | -0.000036 | -0.004373 | 0.004435 | -0.011044 | 0.010955 | 0.006593 | 0.076 | -0.157 |
| 30 | 5718 | -0.000002 | -0.000003 | -0.006982 | 0.007050 | -0.016868 | 0.016797 | 0.010271 | -0.100 | -0.027 |
| 60 | 5718 | 0.000113 | 0.000187 | -0.010106 | 0.010419 | -0.025022 | 0.024946 | 0.015192 | 0.410 | 0.849 |
| 120 | 4678 | 0.000207 | 0.000187 | -0.014425 | 0.014971 | -0.034811 | 0.035576 | 0.021658 | 0.801 | 0.909 |

### Z.2 Continuation / reversal (ALL events; numerator/denominator)

| h | continuation | reversal | flat |
|---|---|---|---|
| 5 | 2829/5718 = 0.495 | 2889/5718 = 0.505 | 0/5718 = 0.000 |
| 15 | 2850/5718 = 0.498 | 2868/5718 = 0.502 | 0/5718 = 0.000 |
| 30 | 2858/5718 = 0.500 | 2860/5718 = 0.500 | 0/5718 = 0.000 |
| 60 | 2898/5718 = 0.507 | 2820/5718 = 0.493 | 0/5718 = 0.000 |
| 120 | 2360/4678 = 0.504 | 2318/4678 = 0.496 | 0/4678 = 0.000 |

### Z.3 MFE / MAE (ALL events; MAE ≤ 0 shown as |MAE|; path dominance = MFE + MAE)

| h | MFE mean pts | MFE median pts | MFE median ticks | MFE median σ | |MAE| mean pts | |MAE| median pts | |MAE| median ticks | |MAE| median σ | dominance median | frac > 0 | frac < 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 7.64 | 3.41 | 13.7 | 0.996 | 7.71 | 3.63 | 14.5 | 1.099 | -0.21 | 0.495 | 0.505 |
| 15 | 18.38 | 9.57 | 38.3 | 2.870 | 18.34 | 9.66 | 38.6 | 2.900 | -0.59 | 0.494 | 0.506 |
| 30 | 30.71 | 18.43 | 73.7 | 5.584 | 30.80 | 18.94 | 75.7 | 5.831 | -0.44 | 0.497 | 0.503 |
| 60 | 49.79 | 33.37 | 133.5 | 10.180 | 49.19 | 31.96 | 127.9 | 9.655 | 1.85 | 0.509 | 0.491 |
| 120 | 77.70 | 55.55 | 222.2 | 16.937 | 75.93 | 51.83 | 207.3 | 16.174 | 3.82 | 0.510 | 0.490 |

### Z.4 Excursion percentiles (ALL events; P75 / P95, points and σ units)

| h | MFE P75 pts | MFE P95 pts | MFE P75 σ | MFE P95 σ | |MAE| P75 pts | |MAE| P95 pts | |MAE| P75 σ | |MAE| P95 σ |
|---|---|---|---|---|---|---|---|---|
| 5 | 10.93 | 28.19 | 3.293 | 7.617 | 11.28 | 27.54 | 3.377 | 7.530 |
| 15 | 27.64 | 65.18 | 8.222 | 17.830 | 27.46 | 64.61 | 8.156 | 17.953 |
| 30 | 46.02 | 102.78 | 13.719 | 28.243 | 45.86 | 103.18 | 13.670 | 28.429 |
| 60 | 74.54 | 156.45 | 21.992 | 43.186 | 73.07 | 159.78 | 21.468 | 43.389 |
| 120 | 117.02 | 228.81 | 33.655 | 62.131 | 110.61 | 232.72 | 33.415 | 61.708 |

### Z.5 Time to extrema (ALL events; 1-based bar of the first occurrence)

| h | bars→MFE mean/median/P75/P95 | bars→MAE mean/median/P75/P95 | P(MFE first) | P(MAE first) | P(same bar) |
|---|---|---|---|---|---|
| 5 | 3.0 / 3.0 / 5.0 / 5.0 | 3.0 / 3.0 / 5.0 / 5.0 | 2832/5718 = 0.495 | 2761/5718 = 0.483 | 125/5718 = 0.022 |
| 15 | 8.0 / 8.0 / 15.0 / 15.0 | 8.0 / 8.0 / 15.0 / 15.0 | 2864/5718 = 0.501 | 2852/5718 = 0.499 | 2/5718 = 0.000 |
| 30 | 15.6 / 16.0 / 29.0 / 30.0 | 15.5 / 15.0 / 29.0 / 30.0 | 2848/5718 = 0.498 | 2870/5718 = 0.502 | 0/5718 = 0.000 |
| 60 | 30.8 / 32.0 / 55.0 / 60.0 | 30.2 / 30.0 / 54.0 / 60.0 | 2827/5718 = 0.494 | 2891/5718 = 0.506 | 0/5718 = 0.000 |
| 120 | 61.2 / 62.0 / 106.0 / 120.0 | 59.7 / 59.0 / 105.0 / 120.0 | 2308/4678 = 0.493 | 2370/4678 = 0.507 | 0/4678 = 0.000 |

### Z.6 First passage (ALL events; AMBIGUOUS_SAME_BAR is never assigned a winner)

| case | h | N | confirmed target first | confirmed stop first | ambiguous same bar | neither |
|---|---|---|---|---|---|---|
| +0.5sigma_before_-0.5sigma | 120 | 4678 | 2012/4678 = 0.430 | 2013/4678 = 0.430 | 653/4678 = 0.140 | 0/4678 = 0.000 |
| +0.5sigma_before_-0.5sigma | 15 | 5718 | 2443/5718 = 0.427 | 2478/5718 = 0.433 | 797/5718 = 0.139 | 0/5718 = 0.000 |
| +0.5sigma_before_-0.5sigma | 30 | 5718 | 2443/5718 = 0.427 | 2478/5718 = 0.433 | 797/5718 = 0.139 | 0/5718 = 0.000 |
| +0.5sigma_before_-0.5sigma | 60 | 5718 | 2443/5718 = 0.427 | 2478/5718 = 0.433 | 797/5718 = 0.139 | 0/5718 = 0.000 |
| +1.0sigma_before_-1.0sigma | 120 | 4678 | 2301/4678 = 0.492 | 2348/4678 = 0.502 | 29/4678 = 0.006 | 0/4678 = 0.000 |
| +1.0sigma_before_-1.0sigma | 15 | 5718 | 2805/5718 = 0.491 | 2873/5718 = 0.502 | 40/5718 = 0.007 | 0/5718 = 0.000 |
| +1.0sigma_before_-1.0sigma | 30 | 5718 | 2805/5718 = 0.491 | 2873/5718 = 0.502 | 40/5718 = 0.007 | 0/5718 = 0.000 |
| +1.0sigma_before_-1.0sigma | 60 | 5718 | 2805/5718 = 0.491 | 2873/5718 = 0.502 | 40/5718 = 0.007 | 0/5718 = 0.000 |
| +1.5sigma_before_-1.5sigma | 120 | 4678 | 2326/4678 = 0.497 | 2348/4678 = 0.502 | 4/4678 = 0.001 | 0/4678 = 0.000 |
| +1.5sigma_before_-1.5sigma | 15 | 5718 | 2831/5718 = 0.495 | 2869/5718 = 0.502 | 5/5718 = 0.001 | 13/5718 = 0.002 |
| +1.5sigma_before_-1.5sigma | 30 | 5718 | 2838/5718 = 0.496 | 2875/5718 = 0.503 | 5/5718 = 0.001 | 0/5718 = 0.000 |
| +1.5sigma_before_-1.5sigma | 60 | 5718 | 2838/5718 = 0.496 | 2875/5718 = 0.503 | 5/5718 = 0.001 | 0/5718 = 0.000 |
| +2.0sigma_before_-2.0sigma | 120 | 4678 | 2334/4678 = 0.499 | 2343/4678 = 0.501 | 1/4678 = 0.000 | 0/4678 = 0.000 |
| +2.0sigma_before_-2.0sigma | 15 | 5718 | 2816/5718 = 0.492 | 2823/5718 = 0.494 | 1/5718 = 0.000 | 78/5718 = 0.014 |
| +2.0sigma_before_-2.0sigma | 30 | 5718 | 2854/5718 = 0.499 | 2861/5718 = 0.500 | 1/5718 = 0.000 | 2/5718 = 0.000 |
| +2.0sigma_before_-2.0sigma | 60 | 5718 | 2856/5718 = 0.499 | 2861/5718 = 0.500 | 1/5718 = 0.000 | 0/5718 = 0.000 |
| +0.5sigma_target/-1.0sigma_stop | 120 | 4678 | 2609/4678 = 0.558 | 1794/4678 = 0.383 | 275/4678 = 0.059 | 0/4678 = 0.000 |
| +0.5sigma_target/-1.0sigma_stop | 15 | 5718 | 3183/5718 = 0.557 | 2207/5718 = 0.386 | 328/5718 = 0.057 | 0/5718 = 0.000 |
| +0.5sigma_target/-1.0sigma_stop | 30 | 5718 | 3183/5718 = 0.557 | 2207/5718 = 0.386 | 328/5718 = 0.057 | 0/5718 = 0.000 |
| +0.5sigma_target/-1.0sigma_stop | 60 | 5718 | 3183/5718 = 0.557 | 2207/5718 = 0.386 | 328/5718 = 0.057 | 0/5718 = 0.000 |
| +1.0sigma_target/-0.5sigma_stop | 120 | 4678 | 1794/4678 = 0.383 | 2654/4678 = 0.567 | 230/4678 = 0.049 | 0/4678 = 0.000 |
| +1.0sigma_target/-0.5sigma_stop | 15 | 5718 | 2174/5718 = 0.380 | 3260/5718 = 0.570 | 284/5718 = 0.050 | 0/5718 = 0.000 |
| +1.0sigma_target/-0.5sigma_stop | 30 | 5718 | 2174/5718 = 0.380 | 3260/5718 = 0.570 | 284/5718 = 0.050 | 0/5718 = 0.000 |
| +1.0sigma_target/-0.5sigma_stop | 60 | 5718 | 2174/5718 = 0.380 | 3260/5718 = 0.570 | 284/5718 = 0.050 | 0/5718 = 0.000 |
| +1.0sigma_target/-2.0sigma_stop | 120 | 4678 | 2649/4678 = 0.566 | 2021/4678 = 0.432 | 8/4678 = 0.002 | 0/4678 = 0.000 |
| +1.0sigma_target/-2.0sigma_stop | 15 | 5718 | 3215/5718 = 0.562 | 2474/5718 = 0.433 | 9/5718 = 0.002 | 20/5718 = 0.003 |
| +1.0sigma_target/-2.0sigma_stop | 30 | 5718 | 3224/5718 = 0.564 | 2485/5718 = 0.435 | 9/5718 = 0.002 | 0/5718 = 0.000 |
| +1.0sigma_target/-2.0sigma_stop | 60 | 5718 | 3224/5718 = 0.564 | 2485/5718 = 0.435 | 9/5718 = 0.002 | 0/5718 = 0.000 |
| +2.0sigma_target/-1.0sigma_stop | 120 | 4678 | 1996/4678 = 0.427 | 2673/4678 = 0.571 | 9/4678 = 0.002 | 0/4678 = 0.000 |
| +2.0sigma_target/-1.0sigma_stop | 15 | 5718 | 2433/5718 = 0.425 | 3253/5718 = 0.569 | 13/5718 = 0.002 | 19/5718 = 0.003 |
| +2.0sigma_target/-1.0sigma_stop | 30 | 5718 | 2441/5718 = 0.427 | 3264/5718 = 0.571 | 13/5718 = 0.002 | 0/5718 = 0.000 |
| +2.0sigma_target/-1.0sigma_stop | 60 | 5718 | 2441/5718 = 0.427 | 3264/5718 = 0.571 | 13/5718 = 0.002 | 0/5718 = 0.000 |

### Z.7 Fixed bracket surface (ALL events) — GROSS — COSTS NOT APPLIED

**DIAGNOSTIC ONLY — NO BRACKET WAS SELECTED.** 64 fixed cells in the canonical order ['expiry', 'stop', 'target'] (NOT sorted by performance). Primary variant = CONSERVATIVE_RESULT (AMBIGUOUS_SAME_BAR counted as STOP); the raw-path variant and per-year/per-fold detail are in the JSON. No bracket is recommended, ranked or selected; a bracket needs its own registered monetisation study with its own multiplicity accounting.

| expiry | stop σ | target σ | N | f/wk | target | stop(cons) | expiry | ambig | mean pts | median pts | mean R | PF gross | win | pos yrs | pos folds |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15 | 0.5 | 0.5 | 5718 | 36.42 | 0.427 | 0.573 | 0.000 | 0.139 | -0.24 | -1.04 | -0.145 | 0.77 | 0.427 | 0/3 | 0.00 |
| 15 | 0.5 | 1.0 | 5718 | 36.42 | 0.380 | 0.620 | 0.000 | 0.050 | 0.28 | -1.16 | 0.141 | 1.25 | 0.380 | 3/3 | 1.00 |
| 15 | 0.5 | 1.5 | 5718 | 36.42 | 0.350 | 0.650 | 0.000 | 0.025 | 0.75 | -1.23 | 0.400 | 1.64 | 0.350 | 3/3 | 1.00 |
| 15 | 0.5 | 2.0 | 5718 | 36.42 | 0.327 | 0.672 | 0.001 | 0.012 | 1.19 | -1.26 | 0.638 | 1.99 | 0.328 | 3/3 | 1.00 |
| 15 | 1.0 | 0.5 | 5718 | 36.42 | 0.557 | 0.443 | 0.000 | 0.057 | -0.58 | 1.03 | -0.165 | 0.64 | 0.557 | 0/3 | 0.00 |
| 15 | 1.0 | 1.0 | 5718 | 36.42 | 0.491 | 0.509 | 0.000 | 0.007 | -0.06 | -1.57 | -0.019 | 0.97 | 0.491 | 1/3 | 0.20 |
| 15 | 1.0 | 1.5 | 5718 | 36.42 | 0.453 | 0.546 | 0.001 | 0.004 | 0.49 | -1.93 | 0.134 | 1.25 | 0.454 | 3/3 | 1.00 |
| 15 | 1.0 | 2.0 | 5718 | 36.42 | 0.425 | 0.571 | 0.003 | 0.002 | 1.03 | -2.10 | 0.281 | 1.50 | 0.427 | 3/3 | 1.00 |
| 15 | 1.5 | 0.5 | 5718 | 36.42 | 0.613 | 0.387 | 0.000 | 0.031 | -0.99 | 1.16 | -0.182 | 0.53 | 0.613 | 0/3 | 0.00 |
| 15 | 1.5 | 1.0 | 5718 | 36.42 | 0.533 | 0.467 | 0.001 | 0.003 | -0.61 | 1.85 | -0.112 | 0.76 | 0.533 | 0/3 | 0.00 |
| 15 | 1.5 | 1.5 | 5718 | 36.42 | 0.495 | 0.503 | 0.002 | 0.001 | -0.05 | -2.10 | -0.007 | 0.98 | 0.497 | 1/3 | 0.40 |
| 15 | 1.5 | 2.0 | 5718 | 36.42 | 0.465 | 0.529 | 0.006 | 0.000 | 0.49 | -2.71 | 0.093 | 1.17 | 0.469 | 3/3 | 1.00 |
| 15 | 2.0 | 0.5 | 5718 | 36.42 | 0.654 | 0.345 | 0.001 | 0.016 | -1.31 | 1.25 | -0.181 | 0.47 | 0.654 | 0/3 | 0.00 |
| 15 | 2.0 | 1.0 | 5718 | 36.42 | 0.562 | 0.434 | 0.003 | 0.002 | -1.11 | 2.09 | -0.154 | 0.65 | 0.563 | 0/3 | 0.00 |
| 15 | 2.0 | 1.5 | 5718 | 36.42 | 0.524 | 0.469 | 0.007 | 0.000 | -0.56 | 2.66 | -0.076 | 0.83 | 0.527 | 0/3 | 0.00 |
| 15 | 2.0 | 2.0 | 5718 | 36.42 | 0.492 | 0.494 | 0.014 | 0.000 | -0.02 | -0.83 | -0.001 | 1.00 | 0.499 | 1/3 | 0.40 |
| 30 | 0.5 | 0.5 | 5718 | 36.42 | 0.427 | 0.573 | 0.000 | 0.139 | -0.24 | -1.04 | -0.145 | 0.77 | 0.427 | 0/3 | 0.00 |
| 30 | 0.5 | 1.0 | 5718 | 36.42 | 0.380 | 0.620 | 0.000 | 0.050 | 0.28 | -1.16 | 0.141 | 1.25 | 0.380 | 3/3 | 1.00 |
| 30 | 0.5 | 1.5 | 5718 | 36.42 | 0.350 | 0.650 | 0.000 | 0.025 | 0.75 | -1.23 | 0.400 | 1.64 | 0.350 | 3/3 | 1.00 |
| 30 | 0.5 | 2.0 | 5718 | 36.42 | 0.327 | 0.673 | 0.000 | 0.012 | 1.18 | -1.27 | 0.637 | 1.98 | 0.327 | 3/3 | 1.00 |
| 30 | 1.0 | 0.5 | 5718 | 36.42 | 0.557 | 0.443 | 0.000 | 0.057 | -0.58 | 1.03 | -0.165 | 0.64 | 0.557 | 0/3 | 0.00 |
| 30 | 1.0 | 1.0 | 5718 | 36.42 | 0.491 | 0.509 | 0.000 | 0.007 | -0.06 | -1.57 | -0.019 | 0.97 | 0.491 | 1/3 | 0.20 |
| 30 | 1.0 | 1.5 | 5718 | 36.42 | 0.454 | 0.546 | 0.000 | 0.004 | 0.50 | -1.93 | 0.135 | 1.25 | 0.454 | 3/3 | 1.00 |
| 30 | 1.0 | 2.0 | 5718 | 36.42 | 0.427 | 0.573 | 0.000 | 0.002 | 1.03 | -2.11 | 0.282 | 1.50 | 0.427 | 3/3 | 1.00 |
| 30 | 1.5 | 0.5 | 5718 | 36.42 | 0.613 | 0.387 | 0.000 | 0.031 | -0.99 | 1.16 | -0.182 | 0.53 | 0.613 | 0/3 | 0.00 |
| 30 | 1.5 | 1.0 | 5718 | 36.42 | 0.533 | 0.467 | 0.000 | 0.003 | -0.61 | 1.85 | -0.112 | 0.76 | 0.533 | 0/3 | 0.00 |
| 30 | 1.5 | 1.5 | 5718 | 36.42 | 0.496 | 0.504 | 0.000 | 0.001 | -0.05 | -2.15 | -0.007 | 0.98 | 0.496 | 1/3 | 0.60 |
| 30 | 1.5 | 2.0 | 5718 | 36.42 | 0.468 | 0.532 | 0.000 | 0.000 | 0.49 | -2.75 | 0.093 | 1.17 | 0.468 | 3/3 | 1.00 |
| 30 | 2.0 | 0.5 | 5718 | 36.42 | 0.655 | 0.345 | 0.000 | 0.016 | -1.31 | 1.25 | -0.181 | 0.47 | 0.655 | 0/3 | 0.00 |
| 30 | 2.0 | 1.0 | 5718 | 36.42 | 0.564 | 0.436 | 0.000 | 0.002 | -1.12 | 2.10 | -0.154 | 0.64 | 0.564 | 0/3 | 0.00 |
| 30 | 2.0 | 1.5 | 5718 | 36.42 | 0.527 | 0.473 | 0.000 | 0.000 | -0.57 | 2.72 | -0.077 | 0.83 | 0.527 | 0/3 | 0.00 |
| 30 | 2.0 | 2.0 | 5718 | 36.42 | 0.499 | 0.501 | 0.000 | 0.000 | -0.02 | -2.45 | -0.001 | 0.99 | 0.499 | 1/3 | 0.40 |
| 60 | 0.5 | 0.5 | 5718 | 36.42 | 0.427 | 0.573 | 0.000 | 0.139 | -0.24 | -1.04 | -0.145 | 0.77 | 0.427 | 0/3 | 0.00 |
| 60 | 0.5 | 1.0 | 5718 | 36.42 | 0.380 | 0.620 | 0.000 | 0.050 | 0.28 | -1.16 | 0.141 | 1.25 | 0.380 | 3/3 | 1.00 |
| 60 | 0.5 | 1.5 | 5718 | 36.42 | 0.350 | 0.650 | 0.000 | 0.025 | 0.75 | -1.23 | 0.400 | 1.64 | 0.350 | 3/3 | 1.00 |
| 60 | 0.5 | 2.0 | 5718 | 36.42 | 0.327 | 0.673 | 0.000 | 0.012 | 1.18 | -1.27 | 0.637 | 1.98 | 0.327 | 3/3 | 1.00 |
| 60 | 1.0 | 0.5 | 5718 | 36.42 | 0.557 | 0.443 | 0.000 | 0.057 | -0.58 | 1.03 | -0.165 | 0.64 | 0.557 | 0/3 | 0.00 |
| 60 | 1.0 | 1.0 | 5718 | 36.42 | 0.491 | 0.509 | 0.000 | 0.007 | -0.06 | -1.57 | -0.019 | 0.97 | 0.491 | 1/3 | 0.20 |
| 60 | 1.0 | 1.5 | 5718 | 36.42 | 0.454 | 0.546 | 0.000 | 0.004 | 0.50 | -1.93 | 0.135 | 1.25 | 0.454 | 3/3 | 1.00 |
| 60 | 1.0 | 2.0 | 5718 | 36.42 | 0.427 | 0.573 | 0.000 | 0.002 | 1.03 | -2.11 | 0.282 | 1.50 | 0.427 | 3/3 | 1.00 |
| 60 | 1.5 | 0.5 | 5718 | 36.42 | 0.613 | 0.387 | 0.000 | 0.031 | -0.99 | 1.16 | -0.182 | 0.53 | 0.613 | 0/3 | 0.00 |
| 60 | 1.5 | 1.0 | 5718 | 36.42 | 0.533 | 0.467 | 0.000 | 0.003 | -0.61 | 1.85 | -0.112 | 0.76 | 0.533 | 0/3 | 0.00 |
| 60 | 1.5 | 1.5 | 5718 | 36.42 | 0.496 | 0.504 | 0.000 | 0.001 | -0.05 | -2.15 | -0.007 | 0.98 | 0.496 | 1/3 | 0.60 |
| 60 | 1.5 | 2.0 | 5718 | 36.42 | 0.468 | 0.532 | 0.000 | 0.000 | 0.49 | -2.75 | 0.093 | 1.17 | 0.468 | 3/3 | 1.00 |
| 60 | 2.0 | 0.5 | 5718 | 36.42 | 0.655 | 0.345 | 0.000 | 0.016 | -1.31 | 1.25 | -0.181 | 0.47 | 0.655 | 0/3 | 0.00 |
| 60 | 2.0 | 1.0 | 5718 | 36.42 | 0.564 | 0.436 | 0.000 | 0.002 | -1.12 | 2.10 | -0.154 | 0.64 | 0.564 | 0/3 | 0.00 |
| 60 | 2.0 | 1.5 | 5718 | 36.42 | 0.527 | 0.473 | 0.000 | 0.000 | -0.57 | 2.72 | -0.077 | 0.83 | 0.527 | 0/3 | 0.00 |
| 60 | 2.0 | 2.0 | 5718 | 36.42 | 0.499 | 0.501 | 0.000 | 0.000 | -0.02 | -2.45 | -0.000 | 1.00 | 0.499 | 1/3 | 0.40 |
| 120 | 0.5 | 0.5 | 4678 | 29.80 | 0.430 | 0.570 | 0.000 | 0.140 | -0.23 | -1.04 | -0.140 | 0.78 | 0.430 | 0/3 | 0.00 |
| 120 | 0.5 | 1.0 | 4678 | 29.80 | 0.383 | 0.617 | 0.000 | 0.049 | 0.30 | -1.16 | 0.151 | 1.27 | 0.383 | 3/3 | 1.00 |
| 120 | 0.5 | 1.5 | 4678 | 29.80 | 0.352 | 0.648 | 0.000 | 0.025 | 0.76 | -1.24 | 0.408 | 1.65 | 0.352 | 3/3 | 1.00 |
| 120 | 0.5 | 2.0 | 4678 | 29.80 | 0.328 | 0.672 | 0.000 | 0.012 | 1.19 | -1.28 | 0.643 | 1.99 | 0.328 | 3/3 | 1.00 |
| 120 | 1.0 | 0.5 | 4678 | 29.80 | 0.558 | 0.442 | 0.000 | 0.059 | -0.57 | 1.03 | -0.163 | 0.64 | 0.558 | 0/3 | 0.00 |
| 120 | 1.0 | 1.0 | 4678 | 29.80 | 0.492 | 0.508 | 0.000 | 0.006 | -0.04 | -1.54 | -0.016 | 0.98 | 0.492 | 1/3 | 0.40 |
| 120 | 1.0 | 1.5 | 4678 | 29.80 | 0.455 | 0.545 | 0.000 | 0.004 | 0.51 | -1.91 | 0.137 | 1.26 | 0.455 | 3/3 | 1.00 |
| 120 | 1.0 | 2.0 | 4678 | 29.80 | 0.427 | 0.573 | 0.000 | 0.002 | 1.04 | -2.12 | 0.281 | 1.50 | 0.427 | 3/3 | 1.00 |
| 120 | 1.5 | 0.5 | 4678 | 29.80 | 0.615 | 0.385 | 0.000 | 0.031 | -0.97 | 1.17 | -0.179 | 0.53 | 0.615 | 0/3 | 0.00 |
| 120 | 1.5 | 1.0 | 4678 | 29.80 | 0.534 | 0.466 | 0.000 | 0.003 | -0.59 | 1.86 | -0.109 | 0.77 | 0.534 | 0/3 | 0.00 |
| 120 | 1.5 | 1.5 | 4678 | 29.80 | 0.497 | 0.503 | 0.000 | 0.001 | -0.03 | -2.12 | -0.005 | 0.99 | 0.497 | 1/3 | 0.40 |
| 120 | 1.5 | 2.0 | 4678 | 29.80 | 0.468 | 0.532 | 0.000 | 0.000 | 0.49 | -2.75 | 0.092 | 1.17 | 0.468 | 3/3 | 1.00 |
| 120 | 2.0 | 0.5 | 4678 | 29.80 | 0.659 | 0.341 | 0.000 | 0.016 | -1.28 | 1.26 | -0.176 | 0.48 | 0.659 | 0/3 | 0.00 |
| 120 | 2.0 | 1.0 | 4678 | 29.80 | 0.566 | 0.434 | 0.000 | 0.002 | -1.08 | 2.12 | -0.150 | 0.65 | 0.566 | 0/3 | 0.00 |
| 120 | 2.0 | 1.5 | 4678 | 29.80 | 0.529 | 0.471 | 0.000 | 0.000 | -0.54 | 2.72 | -0.074 | 0.84 | 0.529 | 0/3 | 0.20 |
| 120 | 2.0 | 2.0 | 4678 | 29.80 | 0.499 | 0.501 | 0.000 | 0.000 | -0.02 | -2.66 | -0.001 | 1.00 | 0.499 | 1/3 | 0.40 |

### Z.8 Year-by-year path stability (every eligible year; negative years are shown)

**raw base event**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 1897 | 36.48 | 942/1897 = 0.497 | 955/1897 = 0.503 | 964/1897 = 0.508 | 754/1552 = 0.486 | 24.08 | 22.82 | 50.91 | 51.64 | 0.000091 | 0.000273 |
| 2017 | 1907 | 36.67 | 936/1907 = 0.491 | 966/1907 = 0.507 | 970/1907 = 0.509 | 806/1560 = 0.517 | 34.46 | 30.84 | 74.70 | 70.41 | 0.000401 | 0.000206 |
| 2018 | 1914 | 36.11 | 972/1914 = 0.508 | 937/1914 = 0.490 | 964/1914 = 0.504 | 800/1566 = 0.511 | 48.19 | 48.11 | 102.04 | 103.33 | -0.000151 | 0.000088 |

**EXP_0001_T01 DIR_RETURN_15/RIDGE/UPPER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 464 | 17.85 | 256/464 = 0.552 | 248/464 = 0.534 | 254/464 = 0.547 | 200/398 = 0.503 | 29.74 | 20.76 | 58.60 | 49.02 | 0.001284 | 0.001398 |
| 2017 | 911 | 17.52 | 532/911 = 0.584 | 532/911 = 0.584 | 512/911 = 0.562 | 422/773 = 0.546 | 43.99 | 23.89 | 83.75 | 62.34 | 0.002368 | 0.002259 |
| 2018 | 982 | 18.53 | 595/982 = 0.606 | 540/982 = 0.550 | 536/982 = 0.546 | 434/812 = 0.534 | 59.03 | 37.67 | 112.78 | 93.45 | 0.001472 | 0.002028 |

**EXP_0001_T02 DIR_RETURN_15/RIDGE/LOWER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 482 | 18.54 | 225/482 = 0.467 | 225/482 = 0.467 | 231/482 = 0.479 | 179/376 = 0.476 | 22.88 | 28.96 | 50.46 | 54.80 | -0.000599 | -0.000928 |
| 2017 | 996 | 19.15 | 404/996 = 0.406 | 434/996 = 0.436 | 458/996 = 0.460 | 384/787 = 0.488 | 25.97 | 39.65 | 62.74 | 77.42 | -0.001399 | -0.001569 |
| 2018 | 932 | 17.58 | 377/932 = 0.405 | 397/932 = 0.426 | 428/932 = 0.459 | 366/754 = 0.485 | 34.90 | 59.10 | 89.56 | 114.24 | -0.001861 | -0.001412 |

**EXP_0001_T03 DIR_RETURN_15/SPLINE/UPPER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 464 | 17.85 | 255/464 = 0.550 | 250/464 = 0.539 | 255/464 = 0.550 | 194/397 = 0.489 | 29.74 | 20.97 | 59.15 | 49.23 | 0.001372 | 0.001383 |
| 2017 | 955 | 18.37 | 551/955 = 0.577 | 552/955 = 0.578 | 527/955 = 0.552 | 450/810 = 0.556 | 44.06 | 25.66 | 83.34 | 63.07 | 0.001966 | 0.001738 |
| 2018 | 1033 | 19.49 | 619/1033 = 0.599 | 576/1033 = 0.558 | 556/1033 = 0.538 | 459/846 = 0.543 | 59.29 | 38.12 | 112.86 | 93.71 | 0.001300 | 0.001734 |

**EXP_0001_T04 DIR_RETURN_15/SPLINE/LOWER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 482 | 18.54 | 226/482 = 0.469 | 223/482 = 0.463 | 230/482 = 0.477 | 185/377 = 0.491 | 22.96 | 28.61 | 50.85 | 54.32 | -0.000683 | -0.000977 |
| 2017 | 952 | 18.31 | 385/952 = 0.404 | 414/952 = 0.435 | 443/952 = 0.465 | 356/750 = 0.475 | 26.19 | 37.54 | 62.01 | 79.19 | -0.001169 | -0.001529 |
| 2018 | 881 | 16.62 | 353/881 = 0.401 | 361/881 = 0.410 | 408/881 = 0.463 | 341/720 = 0.474 | 34.11 | 58.09 | 87.76 | 114.26 | -0.001853 | -0.001258 |

**EXP_0001_T05 DIR_RETURN_15/XGB/UPPER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 468 | 18.00 | 261/468 = 0.558 | 256/468 = 0.547 | 263/468 = 0.562 | 200/394 = 0.508 | 30.06 | 20.87 | 61.07 | 48.34 | 0.001553 | 0.001588 |
| 2017 | 997 | 19.17 | 575/997 = 0.577 | 572/997 = 0.574 | 557/997 = 0.559 | 457/838 = 0.545 | 43.42 | 24.04 | 82.90 | 63.07 | 0.002110 | 0.001892 |
| 2018 | 1059 | 19.98 | 633/1059 = 0.598 | 582/1059 = 0.550 | 564/1059 = 0.533 | 452/860 = 0.526 | 58.25 | 38.64 | 112.25 | 93.96 | 0.001282 | 0.001553 |

**EXP_0001_T06 DIR_RETURN_15/XGB/LOWER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 478 | 18.38 | 220/478 = 0.460 | 217/478 = 0.454 | 222/478 = 0.464 | 179/380 = 0.471 | 21.90 | 29.51 | 50.30 | 54.79 | -0.000878 | -0.001215 |
| 2017 | 910 | 17.50 | 361/910 = 0.397 | 394/910 = 0.433 | 413/910 = 0.454 | 349/722 = 0.483 | 25.48 | 41.35 | 63.11 | 77.52 | -0.001472 | -0.001828 |
| 2018 | 855 | 16.13 | 339/855 = 0.396 | 355/855 = 0.415 | 400/855 = 0.468 | 348/706 = 0.493 | 34.04 | 59.10 | 88.11 | 114.53 | -0.001927 | -0.001271 |

**EXP_0001_T07 DIR_RETURN_30/RIDGE/UPPER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 349 | 13.42 | 186/349 = 0.533 | 177/349 = 0.507 | 182/349 = 0.521 | 137/297 = 0.461 | 25.89 | 22.33 | 53.00 | 49.01 | 0.000272 | 0.000577 |
| 2017 | 798 | 15.35 | 478/798 = 0.599 | 471/798 = 0.590 | 443/798 = 0.555 | 373/677 = 0.551 | 43.48 | 22.83 | 84.26 | 61.16 | 0.002478 | 0.001862 |
| 2018 | 1021 | 19.26 | 614/1021 = 0.601 | 560/1021 = 0.548 | 560/1021 = 0.548 | 441/834 = 0.529 | 59.36 | 37.99 | 112.86 | 94.05 | 0.001517 | 0.002003 |

**EXP_0001_T09 DIR_RETURN_30/SPLINE/UPPER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 379 | 14.58 | 207/379 = 0.546 | 194/379 = 0.512 | 211/379 = 0.557 | 156/316 = 0.494 | 27.32 | 21.77 | 56.15 | 52.11 | 0.001229 | 0.001434 |
| 2017 | 848 | 16.31 | 498/848 = 0.587 | 485/848 = 0.572 | 478/848 = 0.564 | 383/707 = 0.542 | 42.68 | 23.60 | 80.79 | 60.97 | 0.002345 | 0.002202 |
| 2018 | 1030 | 19.43 | 619/1030 = 0.601 | 571/1030 = 0.554 | 561/1030 = 0.545 | 453/835 = 0.543 | 58.01 | 37.67 | 112.81 | 92.72 | 0.001518 | 0.001975 |

**EXP_0001_T10 DIR_RETURN_30/SPLINE/LOWER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 567 | 21.81 | 274/567 = 0.483 | 279/567 = 0.492 | 274/567 = 0.483 | 223/458 = 0.487 | 24.86 | 26.21 | 55.20 | 52.06 | -0.000280 | -0.000682 |
| 2017 | 1059 | 20.37 | 438/1059 = 0.414 | 481/1059 = 0.454 | 492/1059 = 0.465 | 423/853 = 0.496 | 27.84 | 37.77 | 67.69 | 79.66 | -0.001156 | -0.001551 |
| 2018 | 884 | 16.68 | 353/884 = 0.399 | 366/884 = 0.414 | 403/884 = 0.456 | 347/731 = 0.475 | 34.90 | 59.79 | 88.33 | 116.93 | -0.002096 | -0.001661 |

**EXP_0001_T11 DIR_RETURN_30/XGB/UPPER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 420 | 16.15 | 218/420 = 0.519 | 220/420 = 0.524 | 227/420 = 0.540 | 169/340 = 0.497 | 28.46 | 21.26 | 58.35 | 52.24 | 0.001488 | 0.001310 |
| 2017 | 993 | 19.10 | 568/993 = 0.572 | 562/993 = 0.566 | 557/993 = 0.561 | 445/816 = 0.545 | 42.70 | 24.64 | 82.90 | 62.62 | 0.002096 | 0.001856 |
| 2018 | 1099 | 20.74 | 643/1099 = 0.585 | 593/1099 = 0.540 | 586/1099 = 0.533 | 464/886 = 0.524 | 57.01 | 40.08 | 110.05 | 95.33 | 0.001169 | 0.001553 |

**EXP_0001_T12 DIR_RETURN_30/XGB/LOWER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 526 | 20.23 | 263/526 = 0.500 | 253/526 = 0.481 | 258/526 = 0.490 | 210/434 = 0.484 | 23.78 | 26.88 | 51.26 | 51.96 | -0.000604 | -0.000487 |
| 2017 | 914 | 17.58 | 368/914 = 0.403 | 404/914 = 0.442 | 413/914 = 0.452 | 361/744 = 0.485 | 25.82 | 40.38 | 64.67 | 79.76 | -0.001441 | -0.001719 |
| 2018 | 815 | 15.38 | 329/815 = 0.404 | 344/815 = 0.422 | 378/815 = 0.464 | 336/680 = 0.494 | 34.11 | 60.35 | 91.49 | 115.47 | -0.001932 | -0.001427 |

**EXP_0001_T19 DIR_PATH_SKEW_60/RIDGE/UPPER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 319 | 12.27 | 177/319 = 0.555 | 172/319 = 0.539 | 177/319 = 0.555 | 128/268 = 0.478 | 30.79 | 20.29 | 56.28 | 45.27 | 0.001081 | 0.001603 |
| 2017 | 794 | 15.27 | 480/794 = 0.605 | 466/794 = 0.587 | 445/794 = 0.560 | 360/658 = 0.547 | 43.42 | 23.03 | 82.62 | 61.12 | 0.002387 | 0.001976 |
| 2018 | 1055 | 19.91 | 623/1055 = 0.591 | 579/1055 = 0.549 | 579/1055 = 0.549 | 452/859 = 0.526 | 59.35 | 37.98 | 114.20 | 95.20 | 0.001499 | 0.002052 |

**EXP_0001_T20 DIR_PATH_SKEW_60/RIDGE/LOWER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 627 | 24.12 | 304/627 = 0.485 | 301/627 = 0.480 | 308/627 = 0.491 | 251/506 = 0.496 | 23.89 | 27.65 | 53.42 | 54.63 | -0.000060 | -0.000513 |
| 2017 | 1113 | 21.40 | 456/1113 = 0.410 | 500/1113 = 0.449 | 525/1113 = 0.472 | 446/902 = 0.494 | 27.21 | 37.63 | 67.20 | 77.69 | -0.001016 | -0.001073 |
| 2018 | 859 | 16.21 | 349/859 = 0.406 | 358/859 = 0.417 | 385/859 = 0.448 | 348/707 = 0.492 | 33.16 | 60.45 | 87.48 | 113.98 | -0.002178 | -0.001712 |

**EXP_0001_T21 DIR_PATH_SKEW_60/SPLINE/UPPER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 331 | 12.73 | 174/331 = 0.526 | 168/331 = 0.508 | 179/331 = 0.541 | 123/265 = 0.464 | 27.31 | 21.77 | 57.20 | 53.17 | 0.000715 | 0.001249 |
| 2017 | 897 | 17.25 | 519/897 = 0.579 | 503/897 = 0.561 | 496/897 = 0.553 | 405/737 = 0.550 | 41.74 | 24.37 | 80.56 | 62.58 | 0.001907 | 0.001831 |
| 2018 | 1066 | 20.11 | 630/1066 = 0.591 | 584/1066 = 0.548 | 571/1066 = 0.536 | 470/872 = 0.539 | 57.67 | 39.28 | 110.18 | 93.71 | 0.001261 | 0.001703 |

**EXP_0001_T22 DIR_PATH_SKEW_60/SPLINE/LOWER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 615 | 23.65 | 307/615 = 0.499 | 305/615 = 0.496 | 306/615 = 0.498 | 256/509 = 0.503 | 24.86 | 25.82 | 53.89 | 51.71 | 0.000115 | -0.000206 |
| 2017 | 1010 | 19.42 | 417/1010 = 0.413 | 463/1010 = 0.458 | 474/1010 = 0.469 | 401/823 = 0.487 | 26.72 | 37.16 | 67.71 | 79.33 | -0.000937 | -0.001453 |
| 2018 | 848 | 16.00 | 342/848 = 0.403 | 353/848 = 0.416 | 393/848 = 0.463 | 330/694 = 0.476 | 34.56 | 59.46 | 89.96 | 115.78 | -0.001927 | -0.001405 |

**EXP_0001_T23 DIR_PATH_SKEW_60/XGB/UPPER_HALF**

| YEAR | N | events/wk | CONT_15 | CONT_30 | CONT_60 | CONT_120 | med MFE60 | med |MAE|60 | P75 MFE60 | P75 |MAE|60 | mean ret60 | median ret60 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2016 | 322 | 12.38 | 167/322 = 0.519 | 163/322 = 0.506 | 171/322 = 0.531 | 127/263 = 0.483 | 25.64 | 21.57 | 53.15 | 48.98 | 0.000464 | 0.001215 |
| 2017 | 1043 | 20.06 | 585/1043 = 0.561 | 584/1043 = 0.560 | 583/1043 = 0.559 | 467/860 = 0.543 | 41.74 | 25.25 | 82.21 | 63.59 | 0.001927 | 0.001817 |
| 2018 | 1133 | 21.38 | 663/1133 = 0.585 | 611/1133 = 0.539 | 603/1133 = 0.532 | 486/919 = 0.529 | 57.31 | 39.53 | 110.65 | 93.98 | 0.001255 | 0.001509 |

### Z.9 Development-fold path stability (ALL events, 60-bar horizon)

| fold | N | continuation | median dir. log return | MFE median pts | |MAE| median pts |
|---|---|---|---|---|---|
| 1 | 953 | 489/953 = 0.513 | 0.000351 | 25.40 | 24.64 |
| 2 | 954 | 491/954 = 0.515 | 0.000598 | 30.00 | 26.03 |
| 3 | 953 | 480/953 = 0.504 | 0.000100 | 39.80 | 36.36 |
| 4 | 953 | 479/953 = 0.503 | 0.000082 | 51.30 | 48.46 |
| 5 | 954 | 480/954 = 0.503 | 0.000079 | 44.46 | 48.13 |

### Z.10 Filter-ladder path effects

_no filter_ladder declared_

### Z.11 Diagnostic observations (registry/observations.csv; DIAGNOSTIC_ONLY = true)

| id | category | description |
|---|---|---|
| OBS_00053 | path_continuation | raw base event: continuation at 60 bars 2898/5718 (DIAGNOSTIC ONLY — NOT A SELECTION TRIAL; GROSS — COSTS NOT APPLIED) |
| OBS_00054 | path_dominance | raw base event: median path dominance (MFE+MAE) at 60 bars 1.8510916339164396 points (DIAGNOSTIC ONLY — NOT A SELECTION TRIAL; GROSS — COSTS NOT APPLIED) |
| OBS_00055 | bracket_surface_description | 24 of 64 fixed bracket cells have positive conservative mean gross points for the raw base event (descriptive count only; DIAGNOSTIC ONLY — NO BRACKET WAS SELECTED; GROSS — COSTS NOT APPLIED) |


## X. Exact hashes

| item | sha256 |
|---|---|
| manifest_sha256 | 337046e5e067eb800a71d2741e6da0a58654b9e78d4c1945dc49edd2e0d6f5c7 |
| manifest_hash | 9d3c9129cba40603b8548efb35520c22fc7caac53fe2c9ef178bbabdf30d5cfc |
| event_hash | dd3dc43384677409442cf430c5708bf8e5f0fafe10f4b6665c2cdd5d0e61e2e4 |
| event_py | 47e3f563c012e50b1a7f8a30d8bf81e106793a1d594ffd5bb2d922660ad10585 |
| event_spec | 9b17cc874e0a2d4b7c58b552bf3df5b87a5978ec80ba401beb10e063a0de22eb |
| partitions_hash | 8e35ba8724b68cc65dde56ecb0259a4e687efe4410d7ae4449d58d79e2abf4fd |
| frozen_bundle_hash | 5b21a32341919b1c5f75a2afbb6da87e5a60f335c064fdea6fcb377116d162b0 |
| engine_code_hash | b090f4dbb655e71a173bd25452d39e7fde06e1363893bb2e3c9feccf26ebea04 |
| engine_version | v1.1.1 |
| trial_ledger_hash | 6270253d32c835672c0d46b5b5040ad915ed2c15ab92d556b8ae4d396b6237d7 |
| is_data_fingerprint | 99deba244cd2790651042661941d558e73e3f0c42b3f508c0acf26dee9be2371 |
| results_sha256 | 32b0dab716c651b1cdf809e0c14ef0955ce7bd14907a849cb7f5feca1ea389d5 |
| path_diagnostics_sha256 | 522420626a819ccebc2ff4033b9526ca31b6e8a1b75c5783971b749ee49938e0 |
| verifier_pin | 624c8b7f0502abf6c5d453d501e96e3172367035 |

## Y. OOS status

**OOS status = NOT ACCESSED**

The campaign-level OOS requires manual human approval files (per experiment, then the campaign-open approval after `freeze_campaign_oos.py`). Compute the hashes to reference with `python scripts/show_approval_hashes.py --experiment EXP_0001`. The LLM / scripts never create `approvals/EXP_0001_OOS_APPROVAL.yaml`; at most 2 TARGET|SIDE groups from the top-5 list may be approved and every approved group runs all three frozen models.

