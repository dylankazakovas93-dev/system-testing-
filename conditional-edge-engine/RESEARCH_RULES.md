# RESEARCH RULES — conditional-edge-engine v1.0.0 (frozen v1)

> The engine may search only inside the predefined development (IS) research space. It stops and presents the human with the
> entire in-sample selection history before it is technically permitted to touch OOS. OOS is a manual human unlock.
> The final lockbox stays sealed.

Creativity is allowed in defining the **event hypothesis**. The research machinery after the event is **frozen**.
This file states what is frozen, how opportunities are counted, and — separately — which parts I **interpreted** and
which problems I found. Nothing below has been run on real NQ data.

## 0. Gates that must never be weakened to make a test pass

1 trade/week floor, 0.10 standardized-uplift floor, exactly 24 selection trials per experiment, 20 experiments per campaign,
2-of-3 model agreement, 70% year consistency, 4/5 fold consistency, the Bonferroni **and** BH universes, single-direction events,
the same-session target rule, the human OOS gate, and the CPCV 6-choose-2 specification. If a synthetic scenario fails one of
them the **planted effect** is changed, never the rule. `tests/test_policy_invariants.py` pins the frozen constants.

## 1. Three non-overlapping chronological partitions

| Partition | What it is | Who may touch it |
|---|---|---|
| **DEVELOPMENT (IS)** | bars opening before `development_end` | the whole IS stage (event, features, targets, models, DEVELOPMENT_CV, statistics, plots, reports) |
| **CONFIRMATION OOS** | `[development_end, oos_end)` | one-shot, only after a human approval file |
| **FINAL LOCKBOX** | bars from `lockbox_start` (`oos_end <= lockbox_start`) | nobody — no code path opens it (`confirm_lockbox.py` is a stub; `oos_view` cuts at `oos_end`) |

The three dates are chosen when the campaign is opened (`new_experiment.py --new-campaign … --development-end … --oos-end … --lockbox-start …`),
copied into every `EVENT_SPEC.yaml`, hashed (`partitions_hash`) and written into `FROZEN_MANIFEST.json` **before** any IS result exists.
Nothing infers or moves them. "OOS" means *only* the human-unlocked confirmation period; internal cross-validation is called `DEVELOPMENT_CV`.

**Data-partition guard.** `run_experiment.py` reads the file through `load_bars_before(..., development_end)`, so OOS/lockbox rows are never
materialised; the library entry point `run_experiment()` additionally applies `development_view()` to whatever bars it is given and records how
many rows it removed. `tests/test_partition_guard.py` poisons OOS and lockbox rows (random prices 1…1e6, negative volume, NaN closes, an extra post-lockbox tail) and asserts
that the IS results and artifacts are identical to a run on clean bars (see the test for the exact comparison).

## 2. Immutable boundary

| Who | May modify | Must NOT modify |
|---|---|---|
| Event-writing LLM/user (per experiment) | `experiments/EXP_xxxx/{HYPOTHESIS.md, EVENT_SPEC.yaml, event.py, reference.pine}` | `frozen/`, `engine/`, `features/`, `approvals/` |

`freeze_experiment.py` validates the spec, hashes `event.py`, `EVENT_SPEC.yaml`, the partitions, **every** `frozen/v1` file and the
engine/feature code, pre-registers the complete 24-trial set, writes `FROZEN_MANIFEST.json`, and makes the editable files read-only.
Every later stage re-verifies the manifest and raises `MutationDetected` on any difference. A changed `event.py`/spec after results were
revealed is a **new lineage** (`new_experiment.py --lineage-of EXP_xxxx`) that consumes a new campaign slot and 24 new trials.

*Enforcement is detection, not prevention:* read-only modes are advisory (root ignores them) and the CSV registry can be hand-edited.
`integrity_check()`, the manifest hashes, the trial-ledger hash and the OOS hash chain make such edits detectable; git is the durable audit trail.

## 3. Opportunity accounting

* Exactly **4 primary targets × 3 models × 2 states = 24 selection trials** per experiment, pre-registered at freeze (`status=PREREGISTERED`).
  There is no function that creates a 25th trial; `integrity_check()` flags missing, duplicate, 25th, changed-spec and edited-result rows.
* The 24 result rows are hash-sealed at reveal (`trial_ledger_hash` over the sealed fields; campaign-adjusted p/q values and decisions are retroactive by design and not sealed).
* Counters printed by `run_experiment.py`, the IS report and `campaign_status.py`:
  `EXPERIMENT SELECTION TRIALS: 24 / 24`, `CAMPAIGN REVEALED SELECTION TRIALS: N / 480`, and
  *statistical selection opportunities exposed so far* (`selection_opportunity_number = 24·(experiment_seq−1) + trial_index`, a 1-based running count).
* `MAX_EXPERIMENTS_PER_CAMPAIGN = 20` ⇒ ≤ 480 selection trials. Experiment 21 raises `CampaignLimitExceeded`.
* Anything else is a **diagnostic observation** (`registry/observations.csv`, `diagnostic_only=true`, label *DIAGNOSTIC ONLY — NOT A SELECTION TRIAL*)
  or a **new experiment**. AGENTS.md forbids hidden selection.

## 4. What is frozen (v1)

* **56 features** (`FEATURE_BANK.yaml`), open-stamped bars, information-time features; NaN after warm-up is a hard `FeatureQualityFailure`. Unchanged from the original build.
* **4 primary targets** — all **same-session**. An event whose longest (60-bar) forward window would cross the RTH close is `TARGET_TIMESTAMP_INELIGIBLE`,
  decided from timestamps only (never from returns or outcomes), dropped before modelling and counted in the report. Diagnostic targets are restricted to in-session windows.
* **3 models** (`MODEL_BANK.yaml`): Ridge, additive cubic spline + Ridge, XGBoost; unchanged since the original build (XGB uses `train_only_standardization`, §7 issue 1).
* **2 states**: `UPPER_HALF` / `LOWER_HALF` around the train-only median of inner out-of-fold scores. No other threshold exists.
* **Single-direction events only.** `direction_definition.values` must be `[1]` or `[-1]`; any event table with both signs, or with a sign other than the spec's, is `FAIL EVENT CONTRACT`.
  A mixed indicator is two experiments (`EXP_xxxx_LONG`, `EXP_xxxx_SHORT`) registered *before* results. Each consumes a campaign slot and 24 trials.
* **DEVELOPMENT_CV** (`TRIAL_POLICY.yaml: development_cv`): development events are cut into K+1 = 6 consecutive blocks of equal model-eligible event count
  (boundaries use event timestamps only, snapped to exchange-local day starts); the 5 folds validate blocks 1…5 with an expanding window. A training event is legal only if
  `event_time < validation_start` **and** `effective_target_end < validation_start`, where `effective_target_end = max(candidate-claimed end, frozen declared resolution)`
  — a candidate cannot shorten its own label horizon. Minimums remain 300 outer / 5 inner blocks / 50 inner-train / 30 inner-OOF; a fold below any minimum is `SKIPPED_INSUFFICIENT_DATA`
  and reported. Each fold has its own nested inner OOF calibration, threshold and final model. Pooled validation predictions are what the statistics use.
* **Inference** (all on DEVELOPMENT_CV predictions during IS): weekly-block bootstrap (2000) and whole-week-block permutation (2000), seed 1729;
  **BH and Bonferroni** at the experiment level (`experiment_bonferroni_p = min(raw_p×24, 1)`, `experiment_q`) and the campaign level
  (`campaign_bonferroni_p = min(raw_p×24E, 1)`, `campaign_q`, universe = every revealed trial of the campaign including rejected experiments, models and sides).
  Campaign values are recomputed over all revealed trials after **every** new reveal, and earlier experiments' statuses are re-evaluated retroactively
  (candidates can be downgraded to `IS_NO_CANDIDATE`; tested).
* **IS shortlist eligibility of one model trial** (`ACCEPTANCE_RULES.yaml`) = all of: selected frequency ≥ 1.0/week (events ÷ eligible weeks **from bars**); standardized uplift ≥ 0.10;
  **absolute selected effect > 0** (a trial with positive uplift but non-positive selected effect is `DIAGNOSTIC_CONDITIONAL_IMPROVEMENT`, never eligible); bootstrap CI lower bound > 0;
  `experiment_q`, `campaign_q`, `experiment_bonferroni_p`, `campaign_bonferroni_p` all ≤ 0.05; year consistency; fold consistency. A TARGET|SIDE group needs ≥ 2 of 3 eligible models.
  The statuses are `IS_REJECTED`, `IS_PROVISIONAL_CANDIDATE` (gates pass but verification/sensitivity not yet complete), `IS_SHORTLIST_ELIGIBLE`.
* **Year consistency**: among UTC calendar years of the DEVELOPMENT_CV validation events with ≥ 20 selected events, ≥ 70% need positive selected effect **and** ≥ 70% need positive uplift.
  A year whose |selected events × uplift| exceeds 35% of the total raises `YEAR_CONCENTRATION_WARNING` (reported, **not** a rejection).
* **Fold consistency**: ≥ 4 of 5 folds with positive uplift **and** ≥ 4 of 5 with positive selected effect. Fewer than 5 evaluated folds ⇒ `INSUFFICIENT_DEVELOPMENT_FOLD_EVIDENCE` (not eligible).
* **Filter ladder** (optional, frozen order, development only, never alters a trial): `filter_ladder` in the spec + `detect_events_ladder()`; each step reports events, frequency, retention,
  effect / uplift versus the parent and the previous step per target, yearly tables and the flags `NO_CONSISTENT_IMPROVEMENT` / `FREQUENCY_DESTRUCTION`; steps identical to the previous step are unflagged.
  Every row is logged in `observations.csv`.
* **Ranking** (deterministic, `rank_trials` / `rank_groups`): standardized uplift DESC, `campaign_bonferroni_p` ASC, selected frequency DESC, `trial_id` ASC. A group needs ≥ 2/3 eligible models and is ranked
  by the median uplift of its eligible models; the report shows the TOP 5 groups. There is no subjective selection.

## 5. Human gate, one-shot OOS, CPCV, lockbox

1. **Stop.** `run_experiment.py` ends at `AWAITING_HUMAN_OOS_APPROVAL` (or `IS_REJECTED` / `IS_PROVISIONAL_CANDIDATE`) after writing `IS_REPORT.json/.md` (sections A–Y; `M–Q` share one heading) with the entire selection history.
2. **Per-experiment approval.** The human writes `approvals/EXP_xxxx_OOS_APPROVAL.yaml` (template in `templates/approval/`) for each experiment he wants confirmed. **Scripts and LLMs never create it** (AGENTS.md; no engine function writes into `approvals/`;
   `show_approval_hashes.py` is read-only). It must reference the current `manifest_sha256` and `is_report_sha256`, name ≤ 2 groups from the top-5 list (`MAX_OOS_GROUPS_PER_EXPERIMENT = 2`), and every named group is run with all 3 models.
   It is invalid if the event, spec, frozen specs, partitions or IS results change, if the status is not `AWAITING_HUMAN_OOS_APPROVAL` when re-derived under the campaign universe, or if any of the 3 model paths lacks a strong-mode verification.
3. **Campaign OOS freeze, then ONE opening (the OOS accounting unit is the CAMPAIGN).**
   * **Freeze** (`freeze_campaign_oos.py`, human-run): refused unless **every** experiment of the campaign has completed its IS stage (no DRAFT / FROZEN experiment). It closes the campaign (no new experiment, verification record or IS report), re-validates every approval and writes
     `registry/oos_freeze_<campaign>.json` with all approved experiment/group pairs, their manifest / IS-report / approval hashes and `n_oos_confirmations = 3 × Σ approved groups`. Experiments awaiting approval without a positive approval file become `OOS_NOT_APPROVED`; an invalid approval aborts the freeze.
   * **Open** (`run_campaign_oos.py`): needs a second human file `approvals/CAMPAIGN_<id>_OOS_OPEN_APPROVAL.yaml` citing the exact freeze hash; all per-experiment approvals are re-checked against the freeze. The single ledger row in `registry/oos_access.csv` (append-only SHA hash chain, **one row per campaign**) is written
     **before** any OOS computation — "CAMPAIGN OOS HAS BEEN SPENT" — and the campaign becomes `OOS_SPENT`.
   * **Group caps:** ≤ 2 groups per experiment and ≤ 6 positively approved groups across the campaign, summed over all experiments and checked before any state change (and again when the freeze document is validated at opening, so an edited/re-hashed freeze cannot add a 7th group).
   * **Multiplicity is campaign-wide:** BH `oos_q` and `oos_bonferroni_p = min(raw_p × m, 1)` use **m = every 3 × approved_group model confirmation of every experiment in the campaign** (losing experiments and models included). Per-experiment reports, group verdicts (≥ 2 of 3 models), statuses and `oos_trials.csv` rows are preserved; each report states the campaign family size.
   * **Confirmation gate** per model: `selected_effect>0`, frequency ≥ 1/week, uplift ≥ 0.10, CI low > 0, BH q ≤ 0.05 **and** Bonferroni ≤ 0.05 (campaign-wide). Failure ⇒ `OOS_REJECTED`; IS reports of the campaign are sealed (`ReportSealedError`; `OOS status = NOT ACCESSED` can no longer be printed).
   * **Spent enforcement:** once frozen the campaign is closed; once spent, no experiment (including lineage children) can be registered in it, every approval for any of its experiments is refused, a mutated experiment becomes `OOS_CONTAMINATED`, and **no new campaign whose confirmation OOS interval `[development_end, oos_end)` overlaps a spent OOS interval can be created, frozen or opened** (`OOS CONTAMINATED`). A later, disjoint OOS needs a new campaign.
4. **CPCV** (`run_cpcv.py`, only for `OOS_CONFIRMED`, veto only): 6 groups, 2 held out ⇒ 15 splits; purge + embargo = max primary horizon on both sides of every held-out region; preprocessing, thresholds and nested calibration are train-only per split.
   `CPCV_PASS` per model: median effect > 0, median uplift > 0, ≥ 12/15 splits with positive effect and ≥ 12/15 with positive uplift. A group needs ≥ 2/3 passing models. See `docs/CPCV_PBO.md`.
   The PBO-style diagnostic (`NOT APPLICABLE` for one candidate configuration) never influences selection.
5. **Lifecycle**: `IS_REJECTED → IS_PROVISIONAL_CANDIDATE → AWAITING_HUMAN_OOS_APPROVAL → OOS_NOT_APPROVED | OOS_REJECTED | OOS_CONFIRMED → CPCV_REJECTED | CPCV_CONFIRMED → AWAITING_FINAL_LOCKBOX`.
   The lockbox stays sealed.

## 6. External verification

`verify_experiment.py` stages the candidate on the **development cut** only, runs **all 3** model adapters (strong mode) on the candidate targets, and checks the verifier checkout is the pinned commit with a clean tree (`VERIFIER_PIN.yaml`).
Exit code 2 from missing roll provenance is recorded as `RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE` — never `VERIFIED`. Fast-mode runs do not count.

**Verifier holdout (found by running the real verifier).** The verifier is never handed rows beyond the stage partition, but its `lockbox` audit is `UNVERIFIED` when it has no events to withhold.
The bridge therefore passes `--lockbox-start` = the start of a frozen holdout inside the staged development data (`stage_holdout_fraction: 0.10` of the staged span, ≥ 14 days, floored to a UTC date;
`VERIFIER_PIN.yaml`), so the verifier covers the first ~90% of the development span. **The verifier's folds are UTC calendar years:** with fewer than 3 calendar years of staged data before the holdout no audited fold has later
rows and its `future_label_poisoning` / `future_feature_poisoning` checks are "not applicable" (`ml_leakage` UNVERIFIED ⇒ `INCOMPLETE`, never a pass). Observed: a 2-year development window ended
`INCOMPLETE` for every path; a 3-year window gave all research families `PASS` for all 9 (3 targets × 3 models) strong-mode paths. The bridge prints and records a warning when fewer than 3 years are available. Use ≥ 3 calendar years of development data.

## 7. Interpretation choices I made (not spelled out in the requirements)

1. Window conventions, VR/Hurst windows, session VWAP, `eligible_session` ⊂ `[09:31, 16:00)`, ties belong to neither state — as in the original build (see `features/` docstrings and `frozen/v1/FEATURE_BANK.yaml`).
2. **Blocks are cut by event count, not by calendar,** and snapped to exchange-local day starts so no trading day is split. The block cut uses timestamps only.
3. **The `years` in the year-consistency rule are UTC calendar years** of `event_time` (matches the external verifier's fold construction); the trading week is the ISO week of the exchange-local date.
4. **OOS confirmation gate constants are my definition.** You specified BH + Bonferroni across 3×G confirmations and ≥ 2/3 models; the remaining numeric gates (frequency ≥ 1/week, uplift ≥ 0.10, effect > 0, CI low > 0) mirror the IS gates (`oos_confirmation:` in `ACCEPTANCE_RULES.yaml`).
5. **The CPCV group rule (≥ 2 of 3 models) mirrors model agreement;** you specified the per-model pass rule only.
6. **PBO configurations** = the (target, side, model) configs of OOS-confirmed groups. With one approved group that is ≤ 3 highly dependent configs; the diagnostic is descriptive only.
7. **Permutation statistic** = uplift, one-sided; `p = (1+#≥)/(B+1)`; bootstrap CI = percentile interval over resampled weeks.
8. **Sensitivity verdict** mirrors model agreement (a probe reverses the sign if < 2 of 3 models keep positive uplift; fails frequency if < 2 of 3 keep ≥ 1/week; fail if > 1 probe reverses or any fails frequency).
9. **Static event scan** rejects numeric literals other than `0`/`1` in `event.py` (heuristic). **Causality pre-check** re-runs the event at 8 cutoffs on truncated and future-mutated bars.
10. **The verifier holdout rule (§6) is an engine staging choice, not a research gate;** the fraction/minimum are in `VERIFIER_PIN.yaml` and are for the human to confirm.
11. **Synthetic lifecycle tests inject verification and sensitivity verdicts at table level** (the real verifier and the bar-level sensitivity stage are exercised separately); the lifecycle itself is the real code.

## 8. Spec issues and limitations (documented; ONLY #1 was acted on as a spec change)

1. **XGBoost is not invariant to the unit of the target — ACTED ON in the original build, reversible.** `reg_alpha`/`reg_lambda` are absolute; on log-return targets (sd ≈ 1e-3) the literal model fits a constant. `MODEL_BANK.yaml: target_transform: train_only_standardization`; set `none` to reproduce the literal spec. **Please confirm.**
2. **Previous issue 2 (uplift vs parent could promote a losing state) is now addressed by the absolute `selected_effect > 0` gate.** The two states are still not independent (`uplift_LOWER = (n_UPPER/n_LOWER)·uplift_UPPER`, tested), so there are ≤ 12 independent p-values; Bonferroni over 24 and BH over 24 are conservative accordingly.
3. **Previous issue 3 (mixed-direction events) is now closed by the single-direction rule;** the cost is that a bidirectional indicator consumes two campaign slots.
4. **Previous issue 5 (windows across session gaps) is now closed by the same-session rule,** at the price of dropping events near the close (counted and reported).
5. **The 0.10 standardized-uplift floor is demanding at 15–60 minute horizons;** most real signals are expected to be `REJECTED_INSUFFICIENT_UPLIFT`.
6. **Short development windows make the year gate nearly unanimous:** with 3 eligible years 70% requires 3/3, with 2 it requires 2/2, and `YEAR_CONCENTRATION_WARNING` is structurally likely with ≤ 3 years. Choose a long development window.
7. **OOS multiplicity and access are campaign-wide, with a hard campaign cap:** `MAX_OOS_GROUPS_PER_CAMPAIGN = 6` approved groups across ALL experiments (2 per experiment) ⇒ at most 6 × 3 = **18** confirmations in the one family. More than 6 refuses the freeze atomically (nothing is written or changed); the cap is frozen policy and is never relaxed because Bonferroni gets strict (×18 at most). Exactly 6 is accepted; 0 never opens OOS.
8. **The verifier pin** (`624c8b7f…`, on branch `claude/relaxed-lamport-119uli` of `engine-verification-`) is the commit that introduced `scripts/verify_research.py`; there are no tags. **The human must confirm or replace it.**
9. **Float reproducibility.** Batch shape can change reductions by ≤ 1 ulp (invariance tests use `rtol=1e-12`; the verifier compares at `atol=1e-9`).
10. Everything was validated on **synthetic** data with known structure; **no real NQ data has been run.** Real data will exercise gap handling, zero-volume windows and roll provenance.
11. Missing continuous-contract roll provenance keeps the verifier's *global* verdict INCOMPLETE (exit 2); reported separately and never treated as a pass.
12. Static scans and the causality pre-check are heuristic evidence, not proof of causality. Costs, sizing, brackets, prop-firm simulation and the final lockbox confirmation are intentionally absent.
