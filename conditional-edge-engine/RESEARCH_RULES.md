# RESEARCH RULES — conditional-edge-engine v1

> Creativity is allowed in defining the **event hypothesis**. The research machinery after the event is **frozen**.

This file states what is frozen, what is not, how opportunities are counted, and — separately and frankly — which
parts of the specification I **interpreted** and which I found **logically problematic** while building it.

## 1. Immutable boundary

| Who | May modify | Must NOT modify |
|---|---|---|
| Event-writing LLM/user (per experiment) | `experiments/EXP_xxxx/{HYPOTHESIS.md, EVENT_SPEC.yaml, event.py, reference.pine}` | `frozen/`, `engine/`, `features/` |

`scripts/freeze_experiment.py` validates the spec, hashes `event.py`, `EVENT_SPEC.yaml`, **every** `frozen/v1` file and the
engine/feature code, pre-registers the complete 24-trial set, writes `FROZEN_MANIFEST.json`, and makes the four editable
files read-only. `run_experiment.py`, `verify_experiment.py` and the staging step re-verify the manifest and raise
`MutationDetected` on any difference. A changed `event.py`/spec after results were revealed is a **new lineage**
(`new_experiment.py --lineage-of EXP_xxxx`): it consumes a new campaign slot and a fresh 24 trials; the old experiment is never overwritten.

*Enforcement is detection, not prevention:* read-only file modes are advisory (root ignores them) and the CSV registry can be
hand-edited. `integrity_check()` and the manifest hashes make such edits detectable; git history is the durable audit trail.

## 2. Opportunity accounting (what the registry proves)

* Exactly **4 primary targets × 3 models × 2 states = 24 selection trials** per experiment (`TRIAL_POLICY.yaml`). There is no `MAX_TRIALS`.
* `trial_registry.py` exposes **no function that creates a 25th trial**; trials are written once, at freeze, before any result exists (`status=PREREGISTERED`, `decision=PENDING`).
* `MAX_EXPERIMENTS_PER_CAMPAIGN = 20` ⇒ at most **480** selection trials per campaign. Experiment 21 raises `CampaignLimitExceeded`; a new campaign must be created explicitly with its own lockbox date.
* `python scripts/campaign_status.py` prints experiments used, trials registered/revealed, and runs the integrity check.
* Anything else is a **diagnostic observation** (`observations.csv`, `eligible_for_promotion=False`, always tied to the generating experiment) or a **new experiment**.

## 3. What is frozen (v1)

* **56 features** (`FEATURE_BANK.yaml`): RET×6, RV×6, VOV×3, ER×5, BROWNIAN_DISP×5, VR×9, HURST×3, COUNT_BALANCE×3, BODY_BALANCE×3, RANGE_POS×4, SIGNED_VOLUME×3, session×6. Bars are open-stamped; bar `s` is known at `s+1min`; features see only bars complete by `event_time`; rows are never omitted (NaN inside the row during warm-up); model-eligible = ≥480 completed bars; a NaN after warm-up is a **DATA / FEATURE QUALITY FAILURE** (hard stop, no imputation).
* **4 primary targets** (`TARGET_BANK.yaml`); forward bars = first bars with `open >= event_time`; `P0` = open of the first forward bar. Long/short formulas are written out in `engine/target_engine.py` and tested.
* **3 models** (`MODEL_BANK.yaml`): Ridge(α=10), additive cubic spline (4 quantile knots, train-only) + Ridge(α=10), XGBoost (frozen parameters, no early stopping, `n_jobs=1` for determinism). All consume the entire feature bank; `day_of_week` is a fixed one-hot (0–6), never splined.
* **2 states**: `UPPER_HALF` (score > train-only median ⇒ trade event direction, target `y`) and `LOWER_HALF` (score < median ⇒ fade, target `-y`). No quantile/decile/threshold states exist anywhere (decile plots are diagnostic only).
* **Nested calibration**: per outer UTC calendar year, training = earlier events whose target windows ended before the year; chronological inner OOF predictions inside that training set; threshold = median of those inner OOF scores; final model fitted on the whole outer training set; validation events classified with the frozen training median. Validation labels never touch models or thresholds (tested).
* **Inference**: OOS only; weekly-block bootstrap (2000) and whole-week-block outcome permutation (2000), seed 1729; BH across all 24 trials (`experiment_q`) and across every revealed trial in the campaign (`campaign_q`).
* **Acceptance** (`ACCEPTANCE_RULES.yaml`): frequency ≥ 1.0/week (events ÷ eligible OOS trading weeks **from bars**), standardized uplift ≥ 0.10, bootstrap CI lower bound > 0, `experiment_q ≤ 0.05`, `campaign_q ≤ 0.05`, ≥70% of eligible OOS years (≥20 selected events) with selected effect > 0; promotion only when ≥2 of 3 models pass at a TARGET×SIDE; then event-parameter sensitivity may **veto** but never create or replace.
* **Lockbox**: `run_experiment.py` has no lockbox option; bars at/after the campaign `lockbox_start` are dropped before any computation (events whose target window would cross it are unresolved and omitted). `confirm_lockbox.py` is deliberately a non-implemented stub.

## 4. Interpretation choices I made (not spelled out in the task; all recorded in frozen YAML where they affect numbers)

1. **Window conventions.** `L` = number of one-bar returns (needs `L+1` closes). VR/Hurst "window W" = the `W` most recent completed bars (W log-closes, W−1 returns) — consistent with "Hurst 480 needs 480 bars".
2. **VR q-bar returns** are non-overlapping and anchored at the most recent bar (`x_t−x_{t−q}, x_{t−q}−x_{t−2q}, …` inside the window); the one-bar variance uses all W−1 returns.
3. **Session VWAP** uses typical price `(H+L+C)/3` and the ETH trading session that begins 18:00 local on the previous calendar day (this is where the instrument's ETH start is used); distance = `close/VWAP − 1`. `RTH_return_from_open` uses the open of the first bar stamped ≥09:30 local.
4. **`eligible_session`** must lie inside `[09:31, 16:00)` exchange-local because the v1 session features are defined inside RTH and need one completed RTH bar.
5. **Ties** (score == median) belong to neither state (they stay in the parent).
6. **Outer folds are UTC calendar years** (matches the external verifier's fold construction). I added frozen walk-forward constants that the task did not specify: `min_outer_train_events=300`, `inner_blocks=5`, `min_inner_train_events=50`, `min_inner_oof_events=30`. Years below the minimum are skipped and *reported*, not silently dropped. Inner OOF predictions come from models fitted on less data than the final model; that is inherent to the requested design.
7. **Trading week** = ISO week of the event's exchange-local date. Eligible weeks = distinct such weeks that have **bars** in the OOS years (so sparse events cannot inflate frequency).
8. **Decision labels.** Per trial the primary class follows `decision_priority` (low frequency → insufficient uplift → statistical → instability); every failed gate is listed in `rejection_reason`. Extra labels beyond the six requested: `REJECTED_MODEL_AGREEMENT` (passes own gates, <2 of 3 models), `PROMOTABLE_PENDING_SENSITIVITY` (candidate exists, probes not yet run / retroactive upgrade by `campaign_q`), `REJECTED_SENSITIVITY`. `REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS` appears in the reason whenever retention < 1 and uplift < 0.10 (no additional "material loss" threshold was invented).
9. **Permutation statistic** = uplift, one-sided (≥ observed), `p=(1+#≥)/(B+1)`; bootstrap CI = percentile interval over resampled weeks.
10. **Sensitivity verdict** mirrors model agreement: a probe *reverses* the sign if fewer than 2 of 3 models keep positive uplift in the candidate state; a probe fails *frequency* if fewer than 2 of 3 models keep ≥1/week. Fail if >1 probe reverses or any probe fails frequency. Integer parameters are rounded half-up and must be ≥3 at freeze (so ×0.75 and ×1.25 differ).
11. **Campaign decisions are recomputed** for every revealed experiment whenever `campaign_q` changes (earlier candidates can be downgraded — tested — or upgraded to `PROMOTABLE_PENDING_SENSITIVITY`).
12. **Static event scan**: numeric literals other than `0` and `1` in `event.py` are rejected (heuristic; `params[...]` of unregistered keys also raise at run time, and declared-but-unused parameters are reported).
13. **Event causality pre-check**: before modelling, `run_experiment` re-runs the event at 8 cutoffs on truncated and future-mutated bars and aborts on any difference (complements, does not replace, the external verifier).

## 5. Spec issues found during the build (documented; ONLY #1 was acted on)

1. **XGBoost is not invariant to the unit of the target — ACTED ON, reversible.** `reg_alpha=1.0`/`reg_lambda=20.0` are absolute. On realistic log-return targets (sd ≈ 1e-3) the literal model fits a *constant* (1 unique prediction; every score ties, `UPPER_HALF` selects 0 events). I saw this in the first bar-level run. Ridge/Spline are exactly equivariant. I added `target_transform: train_only_standardization` to `MODEL_BANK.yaml` (fit on `(y−mean_train)/sd_train`, predictions mapped back to raw units). No hyperparameter was changed or tuned; Ridge/Spline outputs are unchanged; regression test `test_target_transform_makes_xgb_scale_invariant_and_leaves_linear_models_unchanged` proves both the failure and the fix. Set `target_transform: none` to reproduce the literal spec. **Please confirm this choice.**
2. **Uplift-vs-parent gate can promote a state that loses money, and the two states are not independent — NOT changed.** With `s=±1`, `uplift_LOWER = (n_UPPER/n_LOWER)·uplift_UPPER` (tested), so each (target, model) contributes at most one independent test (≤12 independent p-values; BH over 24 is conservative), and both states always share sign and p-value. If the parent effect is positive, a fade state can pass every gate with a *negative* absolute selected effect (tested). The year-stability gate (selected effect > 0) partially guards this. The report prints parent/selected effect side by side; a v2 gate on absolute selected effect is recommended.
3. **No direction input ⇒ mixed-direction events cannot express direction-relative states — NOT changed.** Targets are `direction × return` but the frozen bank contains only raw (unsigned) features and no direction. If both long and short events occur, a continuation/reversal relation relative to direction is invisible to all three models (characterized by `test_mixed_direction_events_hide_a_planted_state_effect_documented_limitation`: identical planted structure, detected for single-direction events, invisible for alternating ones). Until a v2 adds direction (or direction-signed features), use **single-direction events** for discovery; the bundled pivot template is bidirectional only as a translation example.
4. **The 0.10 standardized-uplift floor is demanding at 15–60 minute horizons.** A planted momentum effect with `experiment_q ≤ 0.03` in every year still had standardized uplift 0.03–0.05 and was rejected (as specified). Not a bug; it means most real signals will be `REJECTED_INSUFFICIENT_UPLIFT`.
5. **Forward windows may span session gaps.** "First 60 bars" is followed literally; the report counts windows that cross a gap. Use `eligible_session.end` ≥60 minutes before the close if in-session targets are wanted.
6. **The external verifier's `scripts/verify_research.py` is not on `engine-verification-` `main`.** It exists on branch `claude/relaxed-lamport-119uli`. This repo targets that contract (events/features/targets/fit_predict_fold) and fails loudly if the script is missing; it never copies or modifies the verifier.
7. **Float reproducibility.** Features are deterministic, but batch shape can change reductions by ≤1 ulp (invariance tests use `rtol=1e-12`; the verifier compares at `atol=1e-9`).

## 6. Known limitations

* Everything here was validated on **synthetic** data with known structure; no real NQ data was run. Real data will exercise gap handling, zero-volume windows (hard `FeatureQualityFailure`) and roll provenance.
* Research-family verification exercises the **RIDGE** `fit_predict_fold` path by default (`--model` selects another); warm-up / non-finite validation rows get prediction 0.0 in the verifier adapter only (they are excluded from all research statistics).
* Missing continuous-contract roll provenance keeps the verifier's *global* verdict INCOMPLETE (exit 2); it is reported separately from research-family status and never treated as a pass.
* Static scans and the event-causality pre-check are heuristic evidence, not proof of causality.
* Lockbox confirmation, costs, sizing, brackets, TP/SL, prop-firm simulation are intentionally absent.
