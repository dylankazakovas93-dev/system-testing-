# AGENTS.md — rules for any LLM / agent working in this repository

**The engine may search only inside the predefined development (IS) research space. It stops and presents the human with the
entire in-sample selection history before it is technically permitted to touch OOS. OOS is a manual human unlock. The final
lockbox stays sealed.**

## You MAY
* Edit ONLY `experiments/EXP_xxxx/{HYPOTHESIS.md, EVENT_SPEC.yaml, event.py, reference.pine}` of a DRAFT experiment (before `freeze`).
* Run `new_experiment`, `freeze_experiment`, `run_experiment` (IS only), `verify_experiment`, `make_report`, `campaign_status`.
* Report concerns, diagnostics and observations (logged via `scripts/log_observation.py --diagnostic-only`).

## You MUST NOT
1. **Never create, edit or delete any file in `approvals/`.** The OOS approval is written by the HUMAN. Not "on the user's
   behalf", not as a convenience, not as a test fixture in production code. `show_approval_hashes.py` is read-only for a reason.
2. Never run `freeze_campaign_oos.py`, `run_campaign_oos.py` or `run_cpcv.py` unless the human explicitly asks AND the human approval files exist (per experiment, and the campaign-open approval). Never create `approvals/CAMPAIGN_*_OOS_OPEN_APPROVAL.yaml` either. Never open the final
   lockbox (`confirm_lockbox.py` is a deliberate stub).
3. Never modify `frozen/`, `engine/`, `features/` during an experiment, and never change `event.py` / `EVENT_SPEC.yaml` /
   partitions after `freeze`. Changing them after results were revealed = a NEW lineage (new experiment, 24 new trials).
4. Never move partition dates or infer them from results. Never load, print, plot or summarise OOS/lockbox rows during IS.
5. **No hidden selection.** If a result can influence which configuration is selected (another threshold, feature subset,
   lookback, model, horizon, filter, session, parameter), it is a SELECTION OPPORTUNITY and must be a pre-registered trial of a
   NEW experiment. You may run an unexpected exploratory analysis ONLY if `diagnostic_only = true` and it is technically unable
   to alter any trial row, decision or status; log it in `registry/observations.csv`. Do not run side scripts that inspect
   alternatives outside the frozen runner. If you notice "ER_120 looks important", log it; testing `ER_120 > x` needs a new experiment.
6. Never choose "the best-looking trial". The deterministic ranking in the IS report is the only ranking; the human picks at most
   2 TARGET|SIDE groups for OOS.
7. Mixed-direction indicators: create two experiments (`_LONG`, `_SHORT`) BEFORE results; never split inside one experiment.
8. Never weaken a gate to make a test pass (see RESEARCH_RULES.md §0). If synthetic data fails a gate, change the planted effect.
9. Report faithfully: say when a step was skipped, when verification is pending, when a candidate lost eligibility.

10. The forward-path / bracket diagnostics (IS report section Z) are DIAGNOSTIC ONLY. Never present a bracket, stop, target, horizon or percentile from them as best, optimal or recommended; any rule inspired by them is a NEW experiment or a separate registered monetisation study.

## Lifecycle you must respect
`DRAFT -> FROZEN -> IS run (stops) -> [IS_REJECTED | IS_PROVISIONAL_CANDIDATE | AWAITING_HUMAN_OOS_APPROVAL]
 -> human approvals -> campaign OOS freeze (all IS experiments complete; campaign closed) -> human campaign-open approval -> ONE campaign-wide OOS opening -> [OOS_REJECTED | OOS_CONFIRMED] -> CPCV -> [CPCV_REJECTED | CPCV_CONFIRMED -> AWAITING_FINAL_LOCKBOX]`
(`OOS_NOT_APPROVED`, `OOS_CONTAMINATED` are terminal.) Internal cross-validation is called `DEVELOPMENT_CV`, never OOS.
