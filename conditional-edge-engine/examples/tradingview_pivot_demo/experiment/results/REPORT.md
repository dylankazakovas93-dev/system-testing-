# Experiment report — EXP_0001

* campaign: **C001** (experiment 1 of 20); lockbox starts 2020-01-01 (never evaluated here)
* engine v1.0.0; data: /tmp/final_demo2/NQ_synth.parquet (fingerprint `9b703070ac8833ce…`)
* development / training period: 2016-01-04..2016-12-31; chronological OOS period: 2017-01-01..2019-12-31
* **selection opportunities used by this experiment: 24 of 24. Campaign C001: 24 of 480 registered, 24 revealed.**
* external research verification: **RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE** (research results are not valid unless the research families pass)

## BASE EVENT

| quantity | value |
|---|---|
| events after session/dedup/cooldown rules | 4,448 |
| model-eligible events (>= 480 completed bars) | 4,444 |
| development trading weeks | 209 |
| raw event frequency | 21.28 / week |
| long / short events | 2,196 / 2,252 |
| declared parameters never read by event.py | none |
| 60-bar forward windows spanning a session gap | {'60bar': 0} |
| lockbox-withheld bars (not loaded for modelling) | 22,620 |


Outer walk-forward folds: 2016: SKIPPED_INSUFFICIENT_TRAIN(<300), 2017: OK, 2018: OK, 2019: OK

## PROMOTED DEVELOPMENT CANDIDATES

No development candidate. (No target × side had >= 2 of 3 models pass every gate.)

## REJECTED — LOW FREQUENCY

_none_

## REJECTED — INSUFFICIENT UPLIFT

| trial | target | model | state | N sel | parent f/wk | sel f/wk | retention | parent effect | selected effect | uplift | std uplift | 95% block-boot CI (uplift) | raw p | exp q | camp q | pos/elig years | decision | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXP_0001_T01 | DIR_RETURN_15 | RIDGE | UPPER_HALF | 1624 | 21.25 | 10.34 | 0.49 | +0.00002 | +0.00004 | +0.00002 | +0.010 | [-0.00004, +0.00007] | 0.3013 | 0.9975 | 0.9975 | 3/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift 0.010 < 0.1 at retention 0.49 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0000 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05 |
| EXP_0001_T02 | DIR_RETURN_15 | RIDGE | LOWER_HALF | 1713 | 21.25 | 10.91 | 0.51 | -0.00002 | -0.00001 | +0.00001 | +0.009 | [-0.00003, +0.00007] | 0.3013 | 0.9975 | 0.9975 | 2/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift 0.009 < 0.1 at retention 0.51 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0000 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 2/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T03 | DIR_RETURN_15 | SPLINE | UPPER_HALF | 1643 | 21.25 | 10.46 | 0.49 | +0.00002 | -0.00000 | -0.00002 | -0.014 | [-0.00008, +0.00003] | 0.7901 | 0.9975 | 0.9975 | 2/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.014 < 0.1 at retention 0.49 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0001 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 2/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T04 | DIR_RETURN_15 | SPLINE | LOWER_HALF | 1694 | 21.25 | 10.79 | 0.51 | -0.00002 | -0.00004 | -0.00002 | -0.014 | [-0.00007, +0.00003] | 0.7901 | 0.9975 | 0.9975 | 1/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.014 < 0.1 at retention 0.51 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0001 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 1/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T05 | DIR_RETURN_15 | XGB | UPPER_HALF | 1556 | 21.25 | 9.91 | 0.47 | +0.00002 | -0.00002 | -0.00004 | -0.028 | [-0.00010, +0.00001] | 0.9385 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.028 < 0.1 at retention 0.47 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0001 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 0/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T06 | DIR_RETURN_15 | XGB | LOWER_HALF | 1781 | 21.25 | 11.34 | 0.53 | -0.00002 | -0.00006 | -0.00004 | -0.024 | [-0.00009, +0.00001] | 0.9385 | 0.9975 | 0.9975 | 1/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.024 < 0.1 at retention 0.53 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0001 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 1/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T07 | DIR_RETURN_30 | RIDGE | UPPER_HALF | 1614 | 21.25 | 10.28 | 0.48 | -0.00004 | -0.00006 | -0.00002 | -0.009 | [-0.00010, +0.00006] | 0.6927 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.009 < 0.1 at retention 0.48 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0001 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 0/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T08 | DIR_RETURN_30 | RIDGE | LOWER_HALF | 1723 | 21.25 | 10.97 | 0.52 | +0.00004 | +0.00002 | -0.00002 | -0.008 | [-0.00009, +0.00006] | 0.6927 | 0.9975 | 0.9975 | 3/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.008 < 0.1 at retention 0.52 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0001 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05 |
| EXP_0001_T09 | DIR_RETURN_30 | SPLINE | UPPER_HALF | 1654 | 21.25 | 10.54 | 0.50 | -0.00004 | -0.00009 | -0.00005 | -0.023 | [-0.00013, +0.00002] | 0.9075 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.023 < 0.1 at retention 0.50 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0001 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 0/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T10 | DIR_RETURN_30 | SPLINE | LOWER_HALF | 1683 | 21.25 | 10.72 | 0.50 | +0.00004 | -0.00001 | -0.00005 | -0.023 | [-0.00012, +0.00002] | 0.9075 | 0.9975 | 0.9975 | 1/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.023 < 0.1 at retention 0.50 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0001 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 1/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T11 | DIR_RETURN_30 | XGB | UPPER_HALF | 1603 | 21.25 | 10.21 | 0.48 | -0.00004 | -0.00008 | -0.00004 | -0.019 | [-0.00011, +0.00003] | 0.8501 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.019 < 0.1 at retention 0.48 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0001 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 0/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T12 | DIR_RETURN_30 | XGB | LOWER_HALF | 1734 | 21.25 | 11.04 | 0.52 | +0.00004 | -0.00000 | -0.00004 | -0.017 | [-0.00010, +0.00003] | 0.8501 | 0.9975 | 0.9975 | 1/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.017 < 0.1 at retention 0.52 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0001 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 1/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T13 | DIR_RETURN_60 | RIDGE | UPPER_HALF | 1598 | 21.25 | 10.18 | 0.48 | +0.00001 | +0.00009 | +0.00008 | +0.026 | [-0.00003, +0.00020] | 0.0850 | 0.9975 | 0.9975 | 3/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift 0.026 < 0.1 at retention 0.48 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0000 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05 |
| EXP_0001_T14 | DIR_RETURN_60 | RIDGE | LOWER_HALF | 1739 | 21.25 | 11.08 | 0.52 | -0.00001 | +0.00007 | +0.00008 | +0.024 | [-0.00003, +0.00018] | 0.0850 | 0.9975 | 0.9975 | 3/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift 0.024 < 0.1 at retention 0.52 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0000 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05 |
| EXP_0001_T15 | DIR_RETURN_60 | SPLINE | UPPER_HALF | 1685 | 21.25 | 10.73 | 0.50 | +0.00001 | -0.00005 | -0.00006 | -0.018 | [-0.00017, +0.00005] | 0.8571 | 0.9975 | 0.9975 | 1/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.018 < 0.1 at retention 0.50 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0002 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 1/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T16 | DIR_RETURN_60 | SPLINE | LOWER_HALF | 1652 | 21.25 | 10.52 | 0.50 | -0.00001 | -0.00007 | -0.00006 | -0.019 | [-0.00017, +0.00005] | 0.8571 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.019 < 0.1 at retention 0.50 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0002 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 0/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T17 | DIR_RETURN_60 | XGB | UPPER_HALF | 1610 | 21.25 | 10.25 | 0.48 | +0.00001 | -0.00004 | -0.00005 | -0.014 | [-0.00016, +0.00006] | 0.7736 | 0.9975 | 0.9975 | 2/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.014 < 0.1 at retention 0.48 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0002 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 2/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T18 | DIR_RETURN_60 | XGB | LOWER_HALF | 1727 | 21.25 | 11.00 | 0.52 | -0.00001 | -0.00005 | -0.00004 | -0.013 | [-0.00015, +0.00006] | 0.7736 | 0.9975 | 0.9975 | 1/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.013 < 0.1 at retention 0.52 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0002 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 1/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T19 | DIR_PATH_SKEW_60 | RIDGE | UPPER_HALF | 1570 | 21.25 | 10.00 | 0.47 | -0.00000 | +0.00001 | +0.00001 | +0.004 | [-0.00011, +0.00014] | 0.4398 | 0.9975 | 0.9975 | 2/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift 0.004 < 0.1 at retention 0.47 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0001 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 2/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T20 | DIR_PATH_SKEW_60 | RIDGE | LOWER_HALF | 1767 | 21.25 | 11.25 | 0.53 | +0.00000 | +0.00002 | +0.00001 | +0.003 | [-0.00010, +0.00013] | 0.4398 | 0.9975 | 0.9975 | 2/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift 0.003 < 0.1 at retention 0.53 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0001 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 2/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T21 | DIR_PATH_SKEW_60 | SPLINE | UPPER_HALF | 1578 | 21.25 | 10.05 | 0.47 | -0.00000 | -0.00012 | -0.00011 | -0.032 | [-0.00024, +0.00001] | 0.9660 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.032 < 0.1 at retention 0.47 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0002 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 0/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T22 | DIR_PATH_SKEW_60 | SPLINE | LOWER_HALF | 1759 | 21.25 | 11.20 | 0.53 | +0.00000 | -0.00010 | -0.00010 | -0.029 | [-0.00021, +0.00001] | 0.9660 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.029 < 0.1 at retention 0.53 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0002 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 0/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T23 | DIR_PATH_SKEW_60 | XGB | UPPER_HALF | 1527 | 21.25 | 9.73 | 0.46 | -0.00000 | -0.00019 | -0.00018 | -0.052 | [-0.00031, -0.00006] | 0.9975 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.052 < 0.1 at retention 0.46 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0003 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 0/3 (need >= 70% of eligible years with >= 20 selected events) |
| EXP_0001_T24 | DIR_PATH_SKEW_60 | XGB | LOWER_HALF | 1810 | 21.25 | 11.53 | 0.54 | +0.00000 | -0.00015 | -0.00016 | -0.044 | [-0.00026, -0.00005] | 0.9975 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT | [REJECTED_INSUFFICIENT_UPLIFT] standardized uplift -0.044 < 0.1 at retention 0.54 (REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS); [REJECTED_STATISTICAL] bootstrap CI lower bound -0.0003 <= 0, experiment_q 0.9975 > 0.05, campaign_q 0.9975 > 0.05; [REJECTED_INSTABILITY] positive years 0/3 (need >= 70% of eligible years with >= 20 selected events) |

Frequency cost versus gain (shown for every such state, never hidden):

```
EXP_0001_T01 DIR_RETURN_15/RIDGE/UPPER_HALF
Parent: 21.25/week
Selected: 10.34/week (retention 0.49)
Parent effect: +0.0128σ
Selected effect: +0.0227σ
Uplift: +0.0100σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T02 DIR_RETURN_15/RIDGE/LOWER_HALF
Parent: 21.25/week
Selected: 10.91/week (retention 0.51)
Parent effect: -0.0128σ
Selected effect: -0.0033σ
Uplift: +0.0095σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T03 DIR_RETURN_15/SPLINE/UPPER_HALF
Parent: 21.25/week
Selected: 10.46/week (retention 0.49)
Parent effect: +0.0128σ
Selected effect: -0.0013σ
Uplift: -0.0141σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T04 DIR_RETURN_15/SPLINE/LOWER_HALF
Parent: 21.25/week
Selected: 10.79/week (retention 0.51)
Parent effect: -0.0128σ
Selected effect: -0.0264σ
Uplift: -0.0137σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T05 DIR_RETURN_15/XGB/UPPER_HALF
Parent: 21.25/week
Selected: 9.91/week (retention 0.47)
Parent effect: +0.0128σ
Selected effect: -0.0149σ
Uplift: -0.0277σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T06 DIR_RETURN_15/XGB/LOWER_HALF
Parent: 21.25/week
Selected: 11.34/week (retention 0.53)
Parent effect: -0.0128σ
Selected effect: -0.0369σ
Uplift: -0.0242σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T07 DIR_RETURN_30/RIDGE/UPPER_HALF
Parent: 21.25/week
Selected: 10.28/week (retention 0.48)
Parent effect: -0.0167σ
Selected effect: -0.0253σ
Uplift: -0.0085σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T08 DIR_RETURN_30/RIDGE/LOWER_HALF
Parent: 21.25/week
Selected: 10.97/week (retention 0.52)
Parent effect: +0.0167σ
Selected effect: +0.0087σ
Uplift: -0.0080σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T09 DIR_RETURN_30/SPLINE/UPPER_HALF
Parent: 21.25/week
Selected: 10.54/week (retention 0.50)
Parent effect: -0.0167σ
Selected effect: -0.0401σ
Uplift: -0.0234σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T10 DIR_RETURN_30/SPLINE/LOWER_HALF
Parent: 21.25/week
Selected: 10.72/week (retention 0.50)
Parent effect: +0.0167σ
Selected effect: -0.0063σ
Uplift: -0.0230σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T11 DIR_RETURN_30/XGB/UPPER_HALF
Parent: 21.25/week
Selected: 10.21/week (retention 0.48)
Parent effect: -0.0167σ
Selected effect: -0.0356σ
Uplift: -0.0189σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T12 DIR_RETURN_30/XGB/LOWER_HALF
Parent: 21.25/week
Selected: 11.04/week (retention 0.52)
Parent effect: +0.0167σ
Selected effect: -0.0007σ
Uplift: -0.0175σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T13 DIR_RETURN_60/RIDGE/UPPER_HALF
Parent: 21.25/week
Selected: 10.18/week (retention 0.48)
Parent effect: +0.0020σ
Selected effect: +0.0277σ
Uplift: +0.0257σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T14 DIR_RETURN_60/RIDGE/LOWER_HALF
Parent: 21.25/week
Selected: 11.08/week (retention 0.52)
Parent effect: -0.0020σ
Selected effect: +0.0215σ
Uplift: +0.0236σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T15 DIR_RETURN_60/SPLINE/UPPER_HALF
Parent: 21.25/week
Selected: 10.73/week (retention 0.50)
Parent effect: +0.0020σ
Selected effect: -0.0163σ
Uplift: -0.0183σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T16 DIR_RETURN_60/SPLINE/LOWER_HALF
Parent: 21.25/week
Selected: 10.52/week (retention 0.50)
Parent effect: -0.0020σ
Selected effect: -0.0207σ
Uplift: -0.0187σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T17 DIR_RETURN_60/XGB/UPPER_HALF
Parent: 21.25/week
Selected: 10.25/week (retention 0.48)
Parent effect: +0.0020σ
Selected effect: -0.0123σ
Uplift: -0.0143σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T18 DIR_RETURN_60/XGB/LOWER_HALF
Parent: 21.25/week
Selected: 11.00/week (retention 0.52)
Parent effect: -0.0020σ
Selected effect: -0.0154σ
Uplift: -0.0133σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T19 DIR_PATH_SKEW_60/RIDGE/UPPER_HALF
Parent: 21.25/week
Selected: 10.00/week (retention 0.47)
Parent effect: -0.0014σ
Selected effect: +0.0022σ
Uplift: +0.0036σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T20 DIR_PATH_SKEW_60/RIDGE/LOWER_HALF
Parent: 21.25/week
Selected: 11.25/week (retention 0.53)
Parent effect: +0.0014σ
Selected effect: +0.0046σ
Uplift: +0.0032σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T21 DIR_PATH_SKEW_60/SPLINE/UPPER_HALF
Parent: 21.25/week
Selected: 10.05/week (retention 0.47)
Parent effect: -0.0014σ
Selected effect: -0.0337σ
Uplift: -0.0323σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T22 DIR_PATH_SKEW_60/SPLINE/LOWER_HALF
Parent: 21.25/week
Selected: 11.20/week (retention 0.53)
Parent effect: +0.0014σ
Selected effect: -0.0276σ
Uplift: -0.0290σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T23 DIR_PATH_SKEW_60/XGB/UPPER_HALF
Parent: 21.25/week
Selected: 9.73/week (retention 0.46)
Parent effect: -0.0014σ
Selected effect: -0.0536σ
Uplift: -0.0522σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

```
EXP_0001_T24 DIR_PATH_SKEW_60/XGB/LOWER_HALF
Parent: 21.25/week
Selected: 11.53/week (retention 0.54)
Parent effect: +0.0014σ
Selected effect: -0.0427σ
Uplift: -0.0441σ
STATUS: REJECTED_INSUFFICIENT_UPLIFT / REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS
```

## REJECTED — STATISTICAL

_none_

## REJECTED — INSTABILITY

_none_

## REJECTED — SENSITIVITY

_none_

### Passed own gates but fewer than 2 of 3 models (not promoted)

_none_

## DIAGNOSTIC / NON-PROMOTABLE OBSERVATIONS

**DIAGNOSTIC — NOT ELIGIBLE FOR PROMOTION.** Anything below may inspire a NEW registered experiment; it cannot modify this one.

### Score deciles (pooled OOS)

These bins were not selection trials and cannot promote a candidate.
Using them to construct a rule requires a new registered experiment.

#### DIR_PATH_SKEW_60 / RIDGE

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 334 | 2.127 | +0.000205 |
| 2 | 334 | 2.127 | +0.000053 |
| 3 | 334 | 2.127 | -0.000091 |
| 4 | 333 | 2.121 | -0.000221 |
| 5 | 334 | 2.127 | -0.000023 |
| 6 | 334 | 2.127 | +0.000097 |
| 7 | 333 | 2.121 | +0.000126 |
| 8 | 334 | 2.127 | -0.000142 |
| 9 | 334 | 2.127 | -0.000153 |
| 10 | 333 | 2.121 | +0.000101 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | -0.00013 | +0.00025 | +0.00030 | +0.00002 | -0.00019 | +0.00000 | -0.00028 | -0.00010 | -0.00008 | +0.00015 |
| 2018 | +0.00033 | +0.00005 | -0.00033 | -0.00040 | +0.00010 | +0.00017 | +0.00016 | -0.00020 | -0.00009 | -0.00006 |
| 2019 | +0.00065 | -0.00009 | -0.00015 | -0.00021 | -0.00004 | +0.00009 | +0.00037 | -0.00012 | -0.00040 | +0.00013 |

Top diagnostic feature importances: BODY_BALANCE_15 (0.03636), BODY_BALANCE_30 (0.09659), BODY_BALANCE_60 (0.07154), BROWNIAN_DISP_120 (0.07426), BROWNIAN_DISP_15 (0.1808) — **DIAGNOSTIC — NOT ELIGIBLE FOR PROMOTION**

#### DIR_PATH_SKEW_60 / SPLINE

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 334 | 2.127 | +0.000205 |
| 2 | 334 | 2.127 | +0.000312 |
| 3 | 334 | 2.127 | -0.000194 |
| 4 | 333 | 2.121 | +0.000008 |
| 5 | 334 | 2.127 | +0.000089 |
| 6 | 334 | 2.127 | +0.000255 |
| 7 | 333 | 2.121 | -0.000200 |
| 8 | 334 | 2.127 | -0.000115 |
| 9 | 334 | 2.127 | -0.000193 |
| 10 | 333 | 2.121 | -0.000217 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | +0.00008 | +0.00006 | -0.00006 | -0.00004 | +0.00046 | +0.00018 | -0.00046 | +0.00038 | -0.00027 | -0.00007 |
| 2018 | +0.00015 | +0.00001 | -0.00001 | +0.00013 | +0.00013 | +0.00026 | -0.00014 | -0.00027 | -0.00012 | -0.00044 |
| 2019 | +0.00056 | +0.00072 | -0.00042 | -0.00006 | -0.00015 | +0.00030 | -0.00007 | -0.00039 | -0.00017 | -0.00081 |

Top diagnostic feature importances: BODY_BALANCE_15 (0.213), BODY_BALANCE_30 (0.2043), BODY_BALANCE_60 (0.2091), BROWNIAN_DISP_120 (0.1793), BROWNIAN_DISP_15 (0.1441) — **DIAGNOSTIC — NOT ELIGIBLE FOR PROMOTION**

#### DIR_PATH_SKEW_60 / XGB

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 334 | 2.127 | +0.000100 |
| 2 | 334 | 2.127 | -0.000014 |
| 3 | 334 | 2.127 | +0.000389 |
| 4 | 333 | 2.121 | +0.000175 |
| 5 | 334 | 2.127 | -0.000010 |
| 6 | 334 | 2.127 | +0.000017 |
| 7 | 333 | 2.121 | -0.000272 |
| 8 | 334 | 2.127 | -0.000340 |
| 9 | 334 | 2.127 | +0.000013 |
| 10 | 333 | 2.121 | -0.000107 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | +0.00019 | -0.00045 | -0.00006 | +0.00050 | +0.00044 | +0.00032 | -0.00017 | -0.00049 | -0.00001 | +0.00000 |
| 2018 | -0.00000 | +0.00011 | +0.00021 | -0.00007 | -0.00012 | +0.00009 | -0.00021 | -0.00017 | +0.00033 | -0.00060 |
| 2019 | +0.00006 | +0.00014 | +0.00071 | +0.00020 | -0.00014 | -0.00020 | -0.00042 | -0.00038 | -0.00047 | +0.00019 |

Top diagnostic feature importances: BODY_BALANCE_15 (0.01529), BODY_BALANCE_30 (0.01973), BODY_BALANCE_60 (0.01856), BROWNIAN_DISP_120 (0.01898), BROWNIAN_DISP_15 (0.01729) — **DIAGNOSTIC — NOT ELIGIBLE FOR PROMOTION**

#### DIR_RETURN_15 / RIDGE

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 334 | 2.127 | +0.000039 |
| 2 | 334 | 2.127 | +0.000050 |
| 3 | 334 | 2.127 | -0.000025 |
| 4 | 333 | 2.121 | -0.000088 |
| 5 | 334 | 2.127 | +0.000112 |
| 6 | 334 | 2.127 | +0.000000 |
| 7 | 333 | 2.121 | -0.000048 |
| 8 | 334 | 2.127 | +0.000111 |
| 9 | 334 | 2.127 | -0.000057 |
| 10 | 333 | 2.121 | +0.000103 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | -0.00002 | +0.00017 | -0.00022 | -0.00023 | +0.00010 | -0.00008 | -0.00023 | -0.00005 | +0.00008 | +0.00011 |
| 2018 | -0.00000 | +0.00011 | -0.00013 | -0.00023 | +0.00015 | -0.00007 | -0.00008 | +0.00023 | -0.00013 | +0.00009 |
| 2019 | +0.00016 | -0.00010 | +0.00019 | +0.00008 | +0.00009 | +0.00009 | +0.00014 | +0.00012 | -0.00024 | +0.00008 |

Top diagnostic feature importances: BODY_BALANCE_15 (0.04831), BODY_BALANCE_30 (0.157), BODY_BALANCE_60 (0.1584), BROWNIAN_DISP_120 (0.09769), BROWNIAN_DISP_15 (0.1662) — **DIAGNOSTIC — NOT ELIGIBLE FOR PROMOTION**

#### DIR_RETURN_15 / SPLINE

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 334 | 2.127 | +0.000096 |
| 2 | 334 | 2.127 | +0.000022 |
| 3 | 334 | 2.127 | +0.000005 |
| 4 | 333 | 2.121 | +0.000142 |
| 5 | 334 | 2.127 | -0.000050 |
| 6 | 334 | 2.127 | -0.000031 |
| 7 | 333 | 2.121 | -0.000012 |
| 8 | 334 | 2.127 | +0.000055 |
| 9 | 334 | 2.127 | +0.000044 |
| 10 | 333 | 2.121 | -0.000074 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | -0.00005 | -0.00004 | -0.00010 | +0.00008 | -0.00014 | -0.00004 | +0.00013 | -0.00002 | +0.00014 | -0.00005 |
| 2018 | +0.00005 | +0.00003 | +0.00020 | +0.00013 | -0.00017 | -0.00010 | -0.00014 | +0.00010 | -0.00001 | -0.00019 |
| 2019 | +0.00033 | +0.00006 | -0.00010 | +0.00019 | +0.00014 | +0.00003 | +0.00001 | +0.00008 | -0.00005 | +0.00003 |

Top diagnostic feature importances: BODY_BALANCE_15 (0.2815), BODY_BALANCE_30 (0.1966), BODY_BALANCE_60 (0.1978), BROWNIAN_DISP_120 (0.1616), BROWNIAN_DISP_15 (0.3052) — **DIAGNOSTIC — NOT ELIGIBLE FOR PROMOTION**

#### DIR_RETURN_15 / XGB

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 334 | 2.127 | -0.000016 |
| 2 | 334 | 2.127 | +0.000179 |
| 3 | 334 | 2.127 | +0.000021 |
| 4 | 333 | 2.121 | -0.000081 |
| 5 | 334 | 2.127 | +0.000179 |
| 6 | 334 | 2.127 | -0.000051 |
| 7 | 333 | 2.121 | -0.000108 |
| 8 | 334 | 2.127 | -0.000011 |
| 9 | 334 | 2.127 | -0.000064 |
| 10 | 333 | 2.121 | +0.000150 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | -0.00007 | +0.00019 | -0.00010 | -0.00026 | +0.00019 | +0.00004 | -0.00002 | -0.00015 | -0.00008 | +0.00013 |
| 2018 | -0.00010 | +0.00011 | +0.00019 | -0.00007 | +0.00011 | -0.00014 | -0.00015 | +0.00001 | -0.00007 | +0.00012 |
| 2019 | +0.00017 | +0.00023 | -0.00003 | +0.00003 | +0.00025 | -0.00003 | -0.00014 | +0.00012 | -0.00003 | +0.00040 |

Top diagnostic feature importances: BODY_BALANCE_15 (0.01494), BODY_BALANCE_30 (0.02008), BODY_BALANCE_60 (0.0199), BROWNIAN_DISP_120 (0.01772), BROWNIAN_DISP_15 (0.017) — **DIAGNOSTIC — NOT ELIGIBLE FOR PROMOTION**

#### DIR_RETURN_30 / RIDGE

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 334 | 2.127 | +0.000133 |
| 2 | 334 | 2.127 | -0.000087 |
| 3 | 334 | 2.127 | -0.000148 |
| 4 | 333 | 2.121 | +0.000005 |
| 5 | 334 | 2.127 | -0.000024 |
| 6 | 334 | 2.127 | -0.000040 |
| 7 | 333 | 2.121 | -0.000057 |
| 8 | 334 | 2.127 | -0.000132 |
| 9 | 334 | 2.127 | -0.000030 |
| 10 | 333 | 2.121 | +0.000009 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | +0.00012 | -0.00021 | -0.00001 | +0.00016 | -0.00036 | -0.00019 | +0.00013 | -0.00022 | -0.00010 | -0.00002 |
| 2018 | +0.00007 | -0.00000 | -0.00010 | -0.00004 | +0.00002 | +0.00026 | -0.00038 | -0.00034 | +0.00022 | +0.00012 |
| 2019 | +0.00022 | -0.00010 | -0.00025 | -0.00005 | +0.00008 | -0.00016 | +0.00011 | +0.00016 | -0.00033 | +0.00002 |

Top diagnostic feature importances: BODY_BALANCE_15 (0.04084), BODY_BALANCE_30 (0.08649), BODY_BALANCE_60 (0.08615), BROWNIAN_DISP_120 (0.08286), BROWNIAN_DISP_15 (0.1241) — **DIAGNOSTIC — NOT ELIGIBLE FOR PROMOTION**

#### DIR_RETURN_30 / SPLINE

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 334 | 2.127 | +0.000208 |
| 2 | 334 | 2.127 | -0.000082 |
| 3 | 334 | 2.127 | -0.000087 |
| 4 | 333 | 2.121 | +0.000067 |
| 5 | 334 | 2.127 | -0.000044 |
| 6 | 334 | 2.127 | -0.000139 |
| 7 | 333 | 2.121 | -0.000089 |
| 8 | 334 | 2.127 | -0.000003 |
| 9 | 334 | 2.127 | +0.000011 |
| 10 | 333 | 2.121 | -0.000215 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | +0.00014 | -0.00018 | +0.00006 | -0.00018 | +0.00023 | -0.00015 | +0.00008 | -0.00002 | -0.00016 | -0.00018 |
| 2018 | +0.00002 | +0.00006 | -0.00021 | +0.00015 | +0.00009 | -0.00013 | -0.00011 | +0.00001 | +0.00008 | -0.00023 |
| 2019 | +0.00049 | -0.00014 | -0.00008 | +0.00017 | -0.00026 | -0.00014 | -0.00028 | +0.00000 | +0.00021 | -0.00042 |

Top diagnostic feature importances: BODY_BALANCE_15 (0.1504), BODY_BALANCE_30 (0.1782), BODY_BALANCE_60 (0.203), BROWNIAN_DISP_120 (0.1838), BROWNIAN_DISP_15 (0.2002) — **DIAGNOSTIC — NOT ELIGIBLE FOR PROMOTION**

#### DIR_RETURN_30 / XGB

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 334 | 2.127 | +0.000069 |
| 2 | 334 | 2.127 | -0.000096 |
| 3 | 334 | 2.127 | +0.000023 |
| 4 | 333 | 2.121 | +0.000005 |
| 5 | 334 | 2.127 | +0.000058 |
| 6 | 334 | 2.127 | -0.000084 |
| 7 | 333 | 2.121 | -0.000215 |
| 8 | 334 | 2.127 | -0.000235 |
| 9 | 334 | 2.127 | +0.000042 |
| 10 | 333 | 2.121 | +0.000062 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | +0.00010 | -0.00010 | -0.00008 | -0.00002 | -0.00014 | -0.00021 | -0.00012 | -0.00018 | +0.00008 | -0.00004 |
| 2018 | -0.00017 | -0.00011 | -0.00001 | +0.00006 | +0.00021 | +0.00007 | -0.00016 | -0.00039 | -0.00000 | +0.00040 |
| 2019 | +0.00037 | -0.00009 | +0.00009 | -0.00002 | +0.00002 | -0.00014 | -0.00037 | -0.00010 | +0.00001 | +0.00010 |

Top diagnostic feature importances: BODY_BALANCE_15 (0.01609), BODY_BALANCE_30 (0.01764), BODY_BALANCE_60 (0.01802), BROWNIAN_DISP_120 (0.01914), BROWNIAN_DISP_15 (0.01641) — **DIAGNOSTIC — NOT ELIGIBLE FOR PROMOTION**

#### DIR_RETURN_60 / RIDGE

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 334 | 2.127 | +0.000189 |
| 2 | 334 | 2.127 | -0.000078 |
| 3 | 334 | 2.127 | -0.000213 |
| 4 | 333 | 2.121 | -0.000117 |
| 5 | 334 | 2.127 | -0.000104 |
| 6 | 334 | 2.127 | +0.000228 |
| 7 | 333 | 2.121 | +0.000215 |
| 8 | 334 | 2.127 | +0.000128 |
| 9 | 334 | 2.127 | -0.000127 |
| 10 | 333 | 2.121 | -0.000056 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | -0.00000 | +0.00016 | +0.00013 | +0.00006 | -0.00030 | -0.00029 | +0.00009 | +0.00018 | +0.00011 | -0.00001 |
| 2018 | +0.00035 | -0.00039 | -0.00027 | -0.00005 | +0.00003 | +0.00026 | +0.00052 | +0.00002 | -0.00037 | -0.00001 |
| 2019 | +0.00036 | +0.00009 | -0.00044 | -0.00028 | -0.00008 | +0.00048 | +0.00002 | +0.00022 | -0.00021 | -0.00035 |

Top diagnostic feature importances: BODY_BALANCE_15 (0.04), BODY_BALANCE_30 (0.06913), BODY_BALANCE_60 (0.04474), BROWNIAN_DISP_120 (0.05583), BROWNIAN_DISP_15 (0.1818) — **DIAGNOSTIC — NOT ELIGIBLE FOR PROMOTION**

#### DIR_RETURN_60 / SPLINE

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 334 | 2.127 | +0.000264 |
| 2 | 334 | 2.127 | +0.000132 |
| 3 | 334 | 2.127 | +0.000122 |
| 4 | 333 | 2.121 | -0.000080 |
| 5 | 334 | 2.127 | -0.000135 |
| 6 | 334 | 2.127 | -0.000124 |
| 7 | 333 | 2.121 | +0.000176 |
| 8 | 334 | 2.127 | -0.000090 |
| 9 | 334 | 2.127 | -0.000201 |
| 10 | 333 | 2.121 | +0.000002 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | +0.00009 | +0.00018 | -0.00046 | +0.00031 | -0.00016 | -0.00041 | +0.00015 | +0.00028 | +0.00005 | -0.00001 |
| 2018 | +0.00021 | +0.00029 | -0.00002 | -0.00002 | -0.00029 | -0.00003 | +0.00017 | -0.00026 | -0.00016 | +0.00002 |
| 2019 | +0.00081 | -0.00009 | +0.00065 | -0.00034 | -0.00001 | -0.00003 | +0.00020 | -0.00028 | -0.00058 | +0.00006 |

Top diagnostic feature importances: BODY_BALANCE_15 (0.3071), BODY_BALANCE_30 (0.1752), BODY_BALANCE_60 (0.163), BROWNIAN_DISP_120 (0.2259), BROWNIAN_DISP_15 (0.1459) — **DIAGNOSTIC — NOT ELIGIBLE FOR PROMOTION**

#### DIR_RETURN_60 / XGB

| decile | N | events / week | mean target (event direction) |
|---|---|---|---|
| 1 | 334 | 2.127 | +0.000108 |
| 2 | 334 | 2.127 | -0.000046 |
| 3 | 334 | 2.127 | +0.000140 |
| 4 | 333 | 2.121 | +0.000286 |
| 5 | 334 | 2.127 | -0.000113 |
| 6 | 334 | 2.127 | -0.000135 |
| 7 | 333 | 2.121 | -0.000014 |
| 8 | 334 | 2.127 | -0.000271 |
| 9 | 334 | 2.127 | +0.000194 |
| 10 | 333 | 2.121 | -0.000082 |

Year-by-year mean target by decile:

| year | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 2017 | +0.00013 | -0.00034 | +0.00007 | +0.00066 | -0.00021 | -0.00036 | +0.00031 | -0.00019 | +0.00012 | +0.00005 |
| 2018 | +0.00022 | +0.00029 | -0.00025 | -0.00015 | -0.00014 | +0.00003 | -0.00018 | -0.00013 | +0.00056 | -0.00020 |
| 2019 | -0.00019 | -0.00012 | +0.00048 | +0.00048 | -0.00004 | -0.00015 | -0.00007 | -0.00048 | -0.00009 | -0.00052 |

Top diagnostic feature importances: BODY_BALANCE_15 (0.01958), BODY_BALANCE_30 (0.01806), BODY_BALANCE_60 (0.01809), BROWNIAN_DISP_120 (0.01903), BROWNIAN_DISP_15 (0.01559) — **DIAGNOSTIC — NOT ELIGIBLE FOR PROMOTION**

### Diagnostic targets (means over model-eligible parent events; report only)

| diagnostic target | mean |
|---|---|
| DIAG_FIRST_PASSAGE_0.5 | 0.006976 |
| DIAG_FIRST_PASSAGE_1.0 | 0.011701 |
| DIAG_FWD_RV_60 | 0.003075 |
| DIAG_MAE_120 | -0.003508 |
| DIAG_MAE_15 | -0.001241 |
| DIAG_MAE_30 | -0.001761 |
| DIAG_MAE_60 | -0.002475 |
| DIAG_MFE_120 | 0.003570 |
| DIAG_MFE_15 | 0.001278 |
| DIAG_MFE_30 | 0.001794 |
| DIAG_MFE_60 | 0.002543 |
| DIAG_PATH_EFFICIENCY_60 | 0.134376 |
| DIAG_PATH_LENGTH_60 | 0.019077 |
| DIAG_RET_120 | 0.000018 |
| DIAG_RET_5 | 0.000015 |
| DIAG_TIME_TO_MAE_120 | 60.497637 |
| DIAG_TIME_TO_MAE_15 | 7.832808 |
| DIAG_TIME_TO_MAE_30 | 15.552655 |
| DIAG_TIME_TO_MAE_60 | 30.182493 |
| DIAG_TIME_TO_MFE_120 | 60.286293 |
| DIAG_TIME_TO_MFE_15 | 8.117462 |
| DIAG_TIME_TO_MFE_30 | 15.589559 |
| DIAG_TIME_TO_MFE_60 | 30.904365 |

### Registered observations (registry/observations.csv)

| id | category | description |
|---|---|---|
| OBS_00001 | score_decile_shape | DIR_RETURN_15/RIDGE: mean target top decile +0.00010 vs bottom decile +0.00004 (pooled-OOS deciles; not selection trials) |
| OBS_00002 | feature_importance | DIR_RETURN_15/RIDGE: top features BROWNIAN_DISP_15 (0.1662), BODY_BALANCE_60 (0.1584), BODY_BALANCE_30 (0.157) (diagnostic importance; models still consume the whole bank) |
| OBS_00003 | score_decile_shape | DIR_RETURN_15/SPLINE: mean target top decile -0.00007 vs bottom decile +0.00010 (pooled-OOS deciles; not selection trials) |
| OBS_00004 | feature_importance | DIR_RETURN_15/SPLINE: top features VOV_30 (0.5832), RV_15 (0.5821), HURST_480 (0.5687) (diagnostic importance; models still consume the whole bank) |
| OBS_00005 | score_decile_shape | DIR_RETURN_15/XGB: mean target top decile +0.00015 vs bottom decile -0.00002 (pooled-OOS deciles; not selection trials) |
| OBS_00006 | feature_importance | DIR_RETURN_15/XGB: top features day_of_week (0.03635), RET_30 (0.02108), HURST_240 (0.02102) (diagnostic importance; models still consume the whole bank) |
| OBS_00007 | score_decile_shape | DIR_RETURN_30/RIDGE: mean target top decile +0.00001 vs bottom decile +0.00013 (pooled-OOS deciles; not selection trials) |
| OBS_00008 | feature_importance | DIR_RETURN_30/RIDGE: top features day_of_week (0.1645), RET_15 (0.1435), BROWNIAN_DISP_30 (0.136) (diagnostic importance; models still consume the whole bank) |
| OBS_00009 | score_decile_shape | DIR_RETURN_30/SPLINE: mean target top decile -0.00021 vs bottom decile +0.00021 (pooled-OOS deciles; not selection trials) |
| OBS_00010 | feature_importance | DIR_RETURN_30/SPLINE: top features VR_60_4 (0.641), VR_60_8 (0.5882), VOV_30 (0.5621) (diagnostic importance; models still consume the whole bank) |
| OBS_00011 | score_decile_shape | DIR_RETURN_30/XGB: mean target top decile +0.00006 vs bottom decile +0.00007 (pooled-OOS deciles; not selection trials) |
| OBS_00012 | feature_importance | DIR_RETURN_30/XGB: top features day_of_week (0.0633), cos_RTH_phase (0.02046), VR_60_2 (0.0198) (diagnostic importance; models still consume the whole bank) |
| OBS_00013 | score_decile_shape | DIR_RETURN_60/RIDGE: mean target top decile -0.00006 vs bottom decile +0.00019 (pooled-OOS deciles; not selection trials) |
| OBS_00014 | feature_importance | DIR_RETURN_60/RIDGE: top features RET_15 (0.2021), BROWNIAN_DISP_15 (0.1818), day_of_week (0.1395) (diagnostic importance; models still consume the whole bank) |
| OBS_00015 | score_decile_shape | DIR_RETURN_60/SPLINE: mean target top decile +0.00000 vs bottom decile +0.00026 (pooled-OOS deciles; not selection trials) |
| OBS_00016 | feature_importance | DIR_RETURN_60/SPLINE: top features sin_RTH_phase (0.663), VR_60_8 (0.6255), RANGE_POS_15 (0.596) (diagnostic importance; models still consume the whole bank) |
| OBS_00017 | score_decile_shape | DIR_RETURN_60/XGB: mean target top decile -0.00008 vs bottom decile +0.00011 (pooled-OOS deciles; not selection trials) |
| OBS_00018 | feature_importance | DIR_RETURN_60/XGB: top features day_of_week (0.04443), RV_5 (0.02095), VR_120_2 (0.02091) (diagnostic importance; models still consume the whole bank) |
| OBS_00019 | score_decile_shape | DIR_PATH_SKEW_60/RIDGE: mean target top decile +0.00010 vs bottom decile +0.00020 (pooled-OOS deciles; not selection trials) |
| OBS_00020 | feature_importance | DIR_PATH_SKEW_60/RIDGE: top features RET_15 (0.1846), BROWNIAN_DISP_15 (0.1808), day_of_week (0.1661) (diagnostic importance; models still consume the whole bank) |
| OBS_00021 | score_decile_shape | DIR_PATH_SKEW_60/SPLINE: mean target top decile -0.00022 vs bottom decile +0.00020 (pooled-OOS deciles; not selection trials) |
| OBS_00022 | feature_importance | DIR_PATH_SKEW_60/SPLINE: top features VOV_30 (0.6697), VR_60_4 (0.5563), VR_60_8 (0.5542) (diagnostic importance; models still consume the whole bank) |
| OBS_00023 | score_decile_shape | DIR_PATH_SKEW_60/XGB: mean target top decile -0.00011 vs bottom decile +0.00010 (pooled-OOS deciles; not selection trials) |
| OBS_00024 | feature_importance | DIR_PATH_SKEW_60/XGB: top features day_of_week (0.0534), VR_60_2 (0.02144), RV_5 (0.02044) (diagnostic importance; models still consume the whole bank) |
| OBS_00025 | long_short_asymmetry | DIR_RETURN_15: mean standardized-free uplift UPPER_HALF -0.00002 vs LOWER_HALF -0.00001 across models |
| OBS_00026 | long_short_asymmetry | DIR_RETURN_30: mean standardized-free uplift UPPER_HALF -0.00004 vs LOWER_HALF -0.00004 across models |
| OBS_00027 | long_short_asymmetry | DIR_RETURN_60: mean standardized-free uplift UPPER_HALF -0.00001 vs LOWER_HALF -0.00001 across models |
| OBS_00028 | long_short_asymmetry | DIR_PATH_SKEW_60: mean standardized-free uplift UPPER_HALF -0.00010 vs LOWER_HALF -0.00008 across models |

## ALL 24 SELECTION TRIALS

| trial | target | model | state | N sel | parent f/wk | sel f/wk | retention | parent effect | selected effect | uplift | std uplift | 95% block-boot CI (uplift) | raw p | exp q | camp q | pos/elig years | decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXP_0001_T01 | DIR_RETURN_15 | RIDGE | UPPER_HALF | 1624 | 21.25 | 10.34 | 0.49 | +0.00002 | +0.00004 | +0.00002 | +0.010 | [-0.00004, +0.00007] | 0.3013 | 0.9975 | 0.9975 | 3/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T02 | DIR_RETURN_15 | RIDGE | LOWER_HALF | 1713 | 21.25 | 10.91 | 0.51 | -0.00002 | -0.00001 | +0.00001 | +0.009 | [-0.00003, +0.00007] | 0.3013 | 0.9975 | 0.9975 | 2/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T03 | DIR_RETURN_15 | SPLINE | UPPER_HALF | 1643 | 21.25 | 10.46 | 0.49 | +0.00002 | -0.00000 | -0.00002 | -0.014 | [-0.00008, +0.00003] | 0.7901 | 0.9975 | 0.9975 | 2/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T04 | DIR_RETURN_15 | SPLINE | LOWER_HALF | 1694 | 21.25 | 10.79 | 0.51 | -0.00002 | -0.00004 | -0.00002 | -0.014 | [-0.00007, +0.00003] | 0.7901 | 0.9975 | 0.9975 | 1/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T05 | DIR_RETURN_15 | XGB | UPPER_HALF | 1556 | 21.25 | 9.91 | 0.47 | +0.00002 | -0.00002 | -0.00004 | -0.028 | [-0.00010, +0.00001] | 0.9385 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T06 | DIR_RETURN_15 | XGB | LOWER_HALF | 1781 | 21.25 | 11.34 | 0.53 | -0.00002 | -0.00006 | -0.00004 | -0.024 | [-0.00009, +0.00001] | 0.9385 | 0.9975 | 0.9975 | 1/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T07 | DIR_RETURN_30 | RIDGE | UPPER_HALF | 1614 | 21.25 | 10.28 | 0.48 | -0.00004 | -0.00006 | -0.00002 | -0.009 | [-0.00010, +0.00006] | 0.6927 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T08 | DIR_RETURN_30 | RIDGE | LOWER_HALF | 1723 | 21.25 | 10.97 | 0.52 | +0.00004 | +0.00002 | -0.00002 | -0.008 | [-0.00009, +0.00006] | 0.6927 | 0.9975 | 0.9975 | 3/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T09 | DIR_RETURN_30 | SPLINE | UPPER_HALF | 1654 | 21.25 | 10.54 | 0.50 | -0.00004 | -0.00009 | -0.00005 | -0.023 | [-0.00013, +0.00002] | 0.9075 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T10 | DIR_RETURN_30 | SPLINE | LOWER_HALF | 1683 | 21.25 | 10.72 | 0.50 | +0.00004 | -0.00001 | -0.00005 | -0.023 | [-0.00012, +0.00002] | 0.9075 | 0.9975 | 0.9975 | 1/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T11 | DIR_RETURN_30 | XGB | UPPER_HALF | 1603 | 21.25 | 10.21 | 0.48 | -0.00004 | -0.00008 | -0.00004 | -0.019 | [-0.00011, +0.00003] | 0.8501 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T12 | DIR_RETURN_30 | XGB | LOWER_HALF | 1734 | 21.25 | 11.04 | 0.52 | +0.00004 | -0.00000 | -0.00004 | -0.017 | [-0.00010, +0.00003] | 0.8501 | 0.9975 | 0.9975 | 1/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T13 | DIR_RETURN_60 | RIDGE | UPPER_HALF | 1598 | 21.25 | 10.18 | 0.48 | +0.00001 | +0.00009 | +0.00008 | +0.026 | [-0.00003, +0.00020] | 0.0850 | 0.9975 | 0.9975 | 3/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T14 | DIR_RETURN_60 | RIDGE | LOWER_HALF | 1739 | 21.25 | 11.08 | 0.52 | -0.00001 | +0.00007 | +0.00008 | +0.024 | [-0.00003, +0.00018] | 0.0850 | 0.9975 | 0.9975 | 3/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T15 | DIR_RETURN_60 | SPLINE | UPPER_HALF | 1685 | 21.25 | 10.73 | 0.50 | +0.00001 | -0.00005 | -0.00006 | -0.018 | [-0.00017, +0.00005] | 0.8571 | 0.9975 | 0.9975 | 1/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T16 | DIR_RETURN_60 | SPLINE | LOWER_HALF | 1652 | 21.25 | 10.52 | 0.50 | -0.00001 | -0.00007 | -0.00006 | -0.019 | [-0.00017, +0.00005] | 0.8571 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T17 | DIR_RETURN_60 | XGB | UPPER_HALF | 1610 | 21.25 | 10.25 | 0.48 | +0.00001 | -0.00004 | -0.00005 | -0.014 | [-0.00016, +0.00006] | 0.7736 | 0.9975 | 0.9975 | 2/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T18 | DIR_RETURN_60 | XGB | LOWER_HALF | 1727 | 21.25 | 11.00 | 0.52 | -0.00001 | -0.00005 | -0.00004 | -0.013 | [-0.00015, +0.00006] | 0.7736 | 0.9975 | 0.9975 | 1/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T19 | DIR_PATH_SKEW_60 | RIDGE | UPPER_HALF | 1570 | 21.25 | 10.00 | 0.47 | -0.00000 | +0.00001 | +0.00001 | +0.004 | [-0.00011, +0.00014] | 0.4398 | 0.9975 | 0.9975 | 2/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T20 | DIR_PATH_SKEW_60 | RIDGE | LOWER_HALF | 1767 | 21.25 | 11.25 | 0.53 | +0.00000 | +0.00002 | +0.00001 | +0.003 | [-0.00010, +0.00013] | 0.4398 | 0.9975 | 0.9975 | 2/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T21 | DIR_PATH_SKEW_60 | SPLINE | UPPER_HALF | 1578 | 21.25 | 10.05 | 0.47 | -0.00000 | -0.00012 | -0.00011 | -0.032 | [-0.00024, +0.00001] | 0.9660 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T22 | DIR_PATH_SKEW_60 | SPLINE | LOWER_HALF | 1759 | 21.25 | 11.20 | 0.53 | +0.00000 | -0.00010 | -0.00010 | -0.029 | [-0.00021, +0.00001] | 0.9660 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T23 | DIR_PATH_SKEW_60 | XGB | UPPER_HALF | 1527 | 21.25 | 9.73 | 0.46 | -0.00000 | -0.00019 | -0.00018 | -0.052 | [-0.00031, -0.00006] | 0.9975 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT |
| EXP_0001_T24 | DIR_PATH_SKEW_60 | XGB | LOWER_HALF | 1810 | 21.25 | 11.53 | 0.54 | +0.00000 | -0.00015 | -0.00016 | -0.044 | [-0.00026, -0.00005] | 0.9975 | 0.9975 | 0.9975 | 0/3 | REJECTED_INSUFFICIENT_UPLIFT |

### Year-by-year selected effect (event-direction-adjusted; years with >= 20 selected events are eligible)

| trial | state | 2017 | 2018 | 2019 |
|---|---|---|---|---|
| EXP_0001_T01 | DIR_RETURN_15/RIDGE/UPPER_HALF | +0.00002 (n=650) | +0.00002 (n=522) | +0.00007 (n=452) |
| EXP_0001_T02 | DIR_RETURN_15/RIDGE/LOWER_HALF | +0.00005 (n=473) | +0.00003 (n=586) | -0.00008 (n=654) |
| EXP_0001_T03 | DIR_RETURN_15/SPLINE/UPPER_HALF | +0.00003 (n=623) | -0.00006 (n=560) | +0.00003 (n=460) |
| EXP_0001_T04 | DIR_RETURN_15/SPLINE/LOWER_HALF | +0.00005 (n=500) | -0.00005 (n=548) | -0.00011 (n=646) |
| EXP_0001_T05 | DIR_RETURN_15/XGB/UPPER_HALF | -0.00001 (n=631) | -0.00005 (n=499) | -0.00002 (n=426) |
| EXP_0001_T06 | DIR_RETURN_15/XGB/LOWER_HALF | +0.00001 (n=492) | -0.00003 (n=609) | -0.00013 (n=680) |
| EXP_0001_T07 | DIR_RETURN_30/RIDGE/UPPER_HALF | -0.00008 (n=637) | -0.00003 (n=513) | -0.00005 (n=464) |
| EXP_0001_T08 | DIR_RETURN_30/RIDGE/LOWER_HALF | +0.00002 (n=486) | +0.00003 (n=595) | +0.00001 (n=642) |
| EXP_0001_T09 | DIR_RETURN_30/SPLINE/UPPER_HALF | -0.00009 (n=626) | -0.00007 (n=566) | -0.00011 (n=462) |
| EXP_0001_T10 | DIR_RETURN_30/SPLINE/LOWER_HALF | +0.00001 (n=497) | -0.00002 (n=542) | -0.00003 (n=644) |
| EXP_0001_T11 | DIR_RETURN_30/XGB/UPPER_HALF | -0.00005 (n=653) | -0.00006 (n=533) | -0.00015 (n=417) |
| EXP_0001_T12 | DIR_RETURN_30/XGB/LOWER_HALF | +0.00006 (n=470) | -0.00000 (n=575) | -0.00004 (n=689) |
| EXP_0001_T13 | DIR_RETURN_60/RIDGE/UPPER_HALF | +0.00006 (n=541) | +0.00008 (n=536) | +0.00013 (n=521) |
| EXP_0001_T14 | DIR_RETURN_60/RIDGE/LOWER_HALF | +0.00002 (n=582) | +0.00007 (n=572) | +0.00011 (n=585) |
| EXP_0001_T15 | DIR_RETURN_60/SPLINE/UPPER_HALF | +0.00001 (n=605) | -0.00005 (n=551) | -0.00013 (n=529) |
| EXP_0001_T16 | DIR_RETURN_60/SPLINE/LOWER_HALF | -0.00002 (n=518) | -0.00005 (n=557) | -0.00013 (n=577) |
| EXP_0001_T17 | DIR_RETURN_60/XGB/UPPER_HALF | +0.00001 (n=619) | +0.00006 (n=518) | -0.00022 (n=473) |
| EXP_0001_T18 | DIR_RETURN_60/XGB/LOWER_HALF | -0.00002 (n=504) | +0.00006 (n=590) | -0.00017 (n=633) |
| EXP_0001_T19 | DIR_PATH_SKEW_60/RIDGE/UPPER_HALF | -0.00001 (n=582) | +0.00001 (n=522) | +0.00002 (n=466) |
| EXP_0001_T20 | DIR_PATH_SKEW_60/RIDGE/LOWER_HALF | -0.00001 (n=541) | +0.00006 (n=586) | +0.00000 (n=640) |
| EXP_0001_T21 | DIR_PATH_SKEW_60/SPLINE/UPPER_HALF | -0.00008 (n=588) | -0.00015 (n=539) | -0.00013 (n=451) |
| EXP_0001_T22 | DIR_PATH_SKEW_60/SPLINE/LOWER_HALF | -0.00009 (n=535) | -0.00010 (n=569) | -0.00010 (n=655) |
| EXP_0001_T23 | DIR_PATH_SKEW_60/XGB/UPPER_HALF | -0.00013 (n=621) | -0.00010 (n=502) | -0.00040 (n=404) |
| EXP_0001_T24 | DIR_PATH_SKEW_60/XGB/LOWER_HALF | -0.00016 (n=502) | -0.00004 (n=606) | -0.00024 (n=702) |

