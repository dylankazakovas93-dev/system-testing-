# AGENTS.md

Read **GUIDE.md** first: it explains the pipeline, what you are encouraged to do (propose events and filters, consult the literature, interpret reports critically,
suggest follow-ups) and the short list of non-negotiables. `RESEARCH_RULES.md` has the exact rules.

Non-negotiables in one place (details in GUIDE.md):
1. Never write anything in `approvals/`; never open the final lockbox.
2. Do not touch holdout/lockbox data outside the approved process.
3. Every variant is a trial: keep the trial tracker, Bonferroni/BH and campaign limits intact; exploratory looks are diagnostic-only and can only inspire a new experiment.
4. Do not edit `engine/`, `features/`, `frozen/` or `ENGINE_VERSION`; do not change an experiment after `freeze`. Propose methodology changes to the human instead.
5. The engine/LLM never makes the human's choices (holdout approval, final config, near-tie resolution); no fallback after a CPCV failure.
6. Report honestly.

Lifecycle: `DRAFT -> FROZEN -> IS run (stops) -> [IS_REJECTED | AWAITING_HUMAN_FINAL_CONFIG_SELECTION | NEAR_TIE_REVIEW_REQUIRED]
-> human: direct final config | holdout approval -> campaign freeze -> one opening | decline -> human final-config selection (must meet the holdout viability floor; none viable -> NO_FINAL_CONFIG)
-> FINAL_CONFIG_FROZEN -> automatic CPCV -> [CPCV_REJECTED (lineage ends) | CPCV_CONFIRMED -> AWAITING_FINAL_LOCKBOX_APPROVAL]`.
`DEVELOPMENT_CV` is internal cross-validation; the SELECTION HOLDOUT is selection data; only the untouched final lockbox may ever be called confirmation.
