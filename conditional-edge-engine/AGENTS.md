# AGENTS.md — rules for any LLM / agent working in this repository

**The engine may search only inside the predefined development (IS) research space. It stops and presents the human with the
entire in-sample selection history before it is technically permitted to touch SELECTION HOLDOUT. SELECTION HOLDOUT is a manual human unlock. The final
lockbox stays sealed.**

## You MAY
* Edit ONLY `experiments/EXP_xxxx/{HYPOTHESIS.md, EVENT_SPEC.yaml, event.py, reference.pine}` of a DRAFT experiment (before `freeze`).
* Run `new_experiment`, `freeze_experiment`, `run_experiment` (IS only), `verify_experiment`, `make_report`, `campaign_status`.
* Report concerns, diagnostics and observations (logged via `scripts/log_observation.py --diagnostic-only`).

## You MUST NOT
1. **Never create, edit or delete any file in `approvals/`.** The holdout approval, the campaign-open approval and the final-config selection are written by the HUMAN. Not "on the user's
   behalf", not as a convenience, not as a test fixture in production code. `show_approval_hashes.py` is read-only for a reason.
2. Never run `freeze_campaign_selection_holdout.py`, `run_campaign_selection_holdout.py` or `finalize_final_config.py` unless the human explicitly asks AND the human files exist (per experiment, the campaign-open approval, the final-config selection). CPCV itself needs no approval: it runs automatically inside `finalize_final_config.py` once `FINAL_CONFIG_FROZEN` is valid (`run_cpcv.py` only resumes it). Never create `approvals/CAMPAIGN_*_SELECTION_HOLDOUT_OPEN_APPROVAL.yaml` either. Never open the final
   lockbox (`confirm_lockbox.py` is a deliberate stub).
3. Never modify `frozen/`, `engine/`, `features/` during an experiment, and never change `event.py` / `EVENT_SPEC.yaml` /
   partitions after `freeze`. Changing them after results were revealed = a NEW lineage (new experiment, 24 new trials).
4. Never move partition dates or infer them from results. Never load, print, plot or summarise SELECTION HOLDOUT/lockbox rows during IS.
5. **No hidden selection.** If a result can influence which configuration is selected (another threshold, feature subset,
   lookback, model, horizon, filter, session, parameter), it is a SELECTION OPPORTUNITY and must be a pre-registered trial of a
   NEW experiment. You may run an unexpected exploratory analysis ONLY if `diagnostic_only = true` and it is technically unable
   to alter any trial row, decision or status; log it in `registry/observations.csv`. Do not run side scripts that inspect
   alternatives outside the frozen runner. If you notice "ER_120 looks important", log it; testing `ER_120 > x` needs a new experiment.
6. Never choose "the best-looking trial" or break a near-tie yourself. The deterministic IS ranking, the near-tie clusters and the advisory `HOLDOUT_PREFERRED_CONFIG` are information for the human, who picks exactly ONE final config
   (or declines) and may propose only the top 2 of a near-tie cluster (max 2 per experiment, 6 per campaign) for the selection holdout. Never fall back to a runner-up after a CPCV failure.
7. Mixed-direction indicators: create two experiments (`_LONG`, `_SHORT`) BEFORE results; never split inside one experiment.
8. Never weaken a gate to make a test pass (see RESEARCH_RULES.md §0). If synthetic data fails a gate, change the planted effect.
9. Report faithfully: say when a step was skipped, when verification is pending, when a candidate lost eligibility.

10. The forward-path / bracket diagnostics (IS report section Z) are DIAGNOSTIC ONLY. Never present a bracket, stop, target, horizon or percentile from them as best, optimal or recommended; any rule inspired by them is a NEW experiment or a separate registered monetisation study. You may not substitute a non-eligible or lower-ranked group for the deterministic approval-eligible set because a diagnostic looks attractive (humans may approve, decline or approve fewer from the eligible list only).

## Lifecycle you must respect
`DRAFT -> FROZEN -> IS run (stops) -> [IS_REJECTED | AWAITING_HUMAN_FINAL_CONFIG_SELECTION | NEAR_TIE_REVIEW_REQUIRED (= AWAITING_HUMAN_SELECTION_HOLDOUT_APPROVAL)]
 -> HUMAN: (A) final config directly -> SELECTION_HOLDOUT_SKIPPED | (B) holdout approval -> campaign freeze (SELECTION_HOLDOUT_FROZEN) -> human open approval -> ONE campaign-wide opening (SELECTION_HOLDOUT_SPENT) | (C) HUMAN_DECLINED
 -> HUMAN final-config selection (exactly one, and it must meet the holdout viability floor; none viable -> NO_FINAL_CONFIG, stop) -> FINAL_CONFIG_FROZEN -> AUTOMATIC CPCV -> [CPCV_REJECTED (lineage ends, no fallback) | CPCV_CONFIRMED -> AWAITING_FINAL_LOCKBOX_APPROVAL]`
(`HUMAN_DECLINED`, `SELECTION_HOLDOUT_CONTAMINATED`, `CPCV_REJECTED` are terminal. The engine never enters `LOCKBOX_*`.) Internal cross-validation is called `DEVELOPMENT_CV`, never SELECTION HOLDOUT. Nothing but the final lockbox may be called confirmation.
