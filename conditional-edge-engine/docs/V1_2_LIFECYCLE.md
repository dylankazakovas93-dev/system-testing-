# v1.2.0 — lifecycle terminology and selection process

v1.2.0 changes **only** the lifecycle semantics and the selection process on top of the frozen v1.1.1 research rules (commit `2b3ee90f…`).
It does **not** change the 56-feature bank, the 4 primary targets, the 3 models, the 2 score states, the 24-trial discovery space, the acceptance thresholds,
the path-diagnostic layer (64 bracket cells), CPCV 6-choose-2 or the external-verifier logic and pin. Nothing was run on real NQ data.

```
DEVELOPMENT / IS -> IS SHORTLIST + NEAR-TIE DETECTION -> HUMAN DECISION -> optional 1-2 year SELECTION HOLDOUT
  -> HUMAN CHOOSES EXACTLY ONE FINAL CONFIG -> AUTOMATIC CPCV (robustness / veto) -> AWAITING FINAL LOCKBOX -> HUMAN LOCKBOX APPROVAL -> FINAL UNTOUCHED CONFIRMATION
```

## Why the old "OOS" was renamed

The previous OOS partition was *used to choose* among configurations. Data that influences a choice is selection data, not confirmation. It is now `SELECTION_HOLDOUT`
everywhere (registry, statuses, reports, scripts, approval files, CLI help, variable names). Nothing but the untouched `FINAL_LOCKBOX` may be called confirmation.

| v1.1.1 | v1.2.0 |
|---|---|
| `oos_end`, `--oos-end`, `--lockbox-start` | `selection_holdout_end`; `--selection-holdout-years {1,2}` (lockbox starts right after) |
| `OOS` partition | `SELECTION_HOLDOUT` (exactly 1 or 2 calendar years starting at `development_end`) |
| `AWAITING_HUMAN_OOS_APPROVAL` | `AWAITING_HUMAN_FINAL_CONFIG_SELECTION` (no near-tie) / `NEAR_TIE_REVIEW_REQUIRED` (alias `AWAITING_HUMAN_SELECTION_HOLDOUT_APPROVAL`) |
| `OOS_NOT_APPROVED` | `HUMAN_DECLINED` |
| `OOS_REJECTED` / `OOS_CONFIRMED` | both replaced by the single status `SELECTION_HOLDOUT_SPENT` (the evidence is in the report; nothing is "confirmed" by a selection holdout) |
| (campaign frozen, new) | `SELECTION_HOLDOUT_FROZEN` |
| `OOS_CONTAMINATED` | `SELECTION_HOLDOUT_CONTAMINATED` |
| `AWAITING_FINAL_LOCKBOX` | `AWAITING_FINAL_LOCKBOX_APPROVAL` |
| `registry/oos_access.csv`, `registry/oos_trials.csv` | `registry/selection_holdout_access.csv`, `registry/selection_holdout_trials.csv` (+ new `registry/final_configs.csv`) |
| `freeze_campaign_oos.py`, `run_campaign_oos.py` | `freeze_campaign_selection_holdout.py`, `run_campaign_selection_holdout.py` (+ new `finalize_final_config.py`) |
| `oos_q`, `oos_bonferroni_p` | `selection_holdout_q`, `selection_holdout_bonferroni_p` ("selection-holdout evidence", never confirmation p-values) |
| human approves 1-2 TARGET\|SIDE groups | human approves the **top-2 near-tied configs of one cluster**; later chooses exactly one final config |
| CPCV needed a separate command after the holdout | CPCV runs **automatically** after `FINAL_CONFIG_FROZEN`; a failure ends the lineage (no runner-up fallback) |

## Interpretation choices made in this patch (please review)

1. **Near-tie statistic.** "median standardized uplift" of a config = the median, over its IS-eligible models, of the standardized uplift of the *pooled DEVELOPMENT_CV validation* predictions
   (identical to the number the IS ranking uses). The paired bootstrap resamples whole trading weeks, *the same weeks for both configs*, and recomputes each model's standardized uplift
   (selected-event mean − parent mean, divided by the fixed target sd of the trial) before taking the median across the config's eligible models. 2000 repetitions, seed 1729, percentile 95% CI.
2. **Cluster naming / order.** Clusters are connected components of near-tie edges among IS-eligible same-side configs of one experiment, numbered `NEAR_TIE_CLUSTER_01…` by the best member's frozen IS group rank;
   members are listed in the frozen IS group ranking; only the first two are proposable.
3. **The approval must name exactly the proposable pair of one cluster** (a single config out of a pair is refused: the holdout exists to compare the near-tied pair; a clearly preferred config is chosen directly).
4. **Status for an experiment without a holdout approval at the campaign freeze** is simply unchanged (it may still be chosen directly); an explicit `approved: false` becomes `HUMAN_DECLINED`.
5. **`HOLDOUT_UNRESOLVED`** reuses the same frozen near-tie rule (|Δ median std uplift| ≤ 0.03 and a paired weekly-block CI containing 0) on the *holdout* panels of the top two qualifying configs.
   `NO_QUALIFYING_CONFIG` is reported when no config meets the preference requirements. The preference never uses path / bracket diagnostics.
6. **Selection-holdout "evidence gates"** (the old OOS gate constants) are kept as *informational* labels on selection data; they gate nothing. The human may choose a config whose gates were not met (the engine does not forbid a human decision among frozen configs).
7. **Selection-holdout training data** = events with `event_time` and `effective_target_end` before `development_end` only (what was knowable before the holdout), exactly as the previous OOS stage.
8. **CPCV after a holdout** uses DEVELOPMENT + SELECTION_HOLDOUT rows and is labelled *POST-SELECTION ROBUSTNESS — NOT INDEPENDENT CONFIRMATION*; its PBO diagnostic is computed over the 3 model configs of the single final configuration.
9. `LOCKBOX_REJECTED` / `LOCKBOX_CONFIRMED` exist in the status vocabulary and are never entered by any code path (no lockbox code exists). **Lockbox multiplicity is not designed.**

## Limitations that remain

* Near-tie classification depends on the DEVELOPMENT_CV pooled panels (5 folds); with few events or a short development window the paired CI is wide and more pairs are "ties"; with a long window fewer are.
* The 2-config / 6-config holdout caps and the 0.03 / 2000 / 1729 constants are frozen policy, not optimised.
* The holdout is 1 or 2 calendar years: with a low event frequency (< ~1/week selected) the holdout evidence is thin. The engine reports that (frequency, N, `HOLDOUT_UNRESOLVED`); it does not extend the window.
* Everything is validated on **synthetic** data. No real NQ data has been run.
