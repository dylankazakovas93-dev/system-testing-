# RESEARCH RULES — conditional-edge-engine v2.3.0 (frozen research rules in `frozen/v1/`; v2 targets and uplift floor; v2.1 batch concentration instead of the fold gate; v2.2 t >= 3 raw-p hurdle replaces the Bonferroni gates, 20000 permutations; v2.3 full ±25% sensitivity and the bracket monetisation study; v1.2 lifecycle)

> The engine may search only inside the predefined development (IS) research space. It stops and presents the human with the
> entire in-sample selection history **and the configuration uncertainty (near-ties)** before it is technically permitted to touch the SELECTION HOLDOUT.
> The SELECTION HOLDOUT is selection data (a manual human unlock); it is **not** confirmation. The final lockbox stays sealed: it is the only untouched confirmation sample.

Lifecycle (v1.2): `DEVELOPMENT / IS → IS SHORTLIST + NEAR-TIE DETECTION → HUMAN DECISION → optional 1–2 year SELECTION HOLDOUT → HUMAN CHOOSES EXACTLY ONE FINAL CONFIG → AUTOMATIC CPCV (post-selection robustness / veto) → AWAITING FINAL LOCKBOX → HUMAN LOCKBOX APPROVAL → FINAL UNTOUCHED CONFIRMATION (not implemented)`.

Creativity is allowed in defining the **event hypothesis**. The research machinery after the event is **frozen**.
This file states what is frozen, how opportunities are counted, and — separately — which parts I **interpreted** and
which problems I found. Nothing below has been run on real NQ data.

## 0. Gates that must never be weakened to make a test pass

1 trade/week floor, 0.01 standardized-uplift floor (v2), exactly 24 selection trials per experiment, 20 experiments per campaign,
2-of-3 model agreement, 70% year consistency, the batch/year concentration gate, the Bonferroni and BH universes (both reported; BH gates, and since v2.2 Bonferroni no longer gates), the raw-p t >= 3 hurdle, single-direction events,
the same-session target rule, the human SELECTION HOLDOUT gate, and the CPCV 6-choose-2 specification. If a synthetic scenario fails one of
them the **planted effect** is changed, never the rule. `tests/test_policy_invariants.py` pins the frozen constants.

## 1. Three non-overlapping chronological partitions

| Partition | What it is | Who may touch it |
|---|---|---|
| **DEVELOPMENT (IS)** | bars opening before `development_end` | the whole IS stage (event, features, targets, models, DEVELOPMENT_CV, statistics, near-tie detection, plots, reports) |
| **SELECTION_HOLDOUT** | `[development_end, selection_holdout_end)`, exactly **1 or 2 calendar years** starting at `development_end` | selection data: only after a human approval, once per campaign; used to choose among configs frozen before it was read. **Not confirmation.** |
| **FINAL_LOCKBOX** | bars from `lockbox_start`, which must equal `selection_holdout_end` (starts immediately after the holdout) | nobody — no code path opens it (`confirm_lockbox.py` is a stub; `selection_holdout_view` cuts at `selection_holdout_end`) |

The holdout length (1 or 2 years — no other duration) is chosen when the campaign is opened, *before any IS result exists*
(`new_experiment.py --new-campaign … --development-end … --selection-holdout-years {1,2}`), copied into every `EVENT_SPEC.yaml`, hashed (`partitions_hash`) and written into `FROZEN_MANIFEST.json`.
Nothing infers or moves it. "SELECTION HOLDOUT" means *only* the human-unlocked selection period; internal cross-validation is called `DEVELOPMENT_CV`; only the final lockbox may ever be called confirmation.

**Data-partition guard.** `run_experiment.py` reads the file through `load_bars_before(..., development_end)`, so SELECTION HOLDOUT/lockbox rows are never
materialised; the library entry point `run_experiment()` additionally applies `development_view()` to whatever bars it is given and records how
many rows it removed. `tests/test_partition_guard.py` poisons SELECTION HOLDOUT and lockbox rows (random prices 1…1e6, negative volume, NaN closes, an extra post-lockbox tail) and asserts
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
`integrity_check()`, the manifest hashes, the trial-ledger hash and the SELECTION HOLDOUT hash chain make such edits detectable; git is the durable audit trail.

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
* **4 primary targets (v2)**: `DIR_RETURN_15`, `DIR_RETURN_60`, `DIR_RETURN_180` and `DIR_PATH_SKEW_60`, all **same-session**. An event whose N-bar window would cross the RTH close is **not dropped**: its window is **truncated at the close** (effective horizon = whole bars left before 16:00, decided from timestamps only, never from outcomes) and the row carries `truncated=True` / `horizon_bars_effective`; the report splits results by full-horizon vs truncated events. Only an event with no complete forward bar before the close is `TARGET_TIMESTAMP_INELIGIBLE`. Diagnostic targets are restricted to in-session windows.
* **3 models** (`MODEL_BANK.yaml`): Ridge, additive cubic spline + Ridge, XGBoost; unchanged since the original build (XGB uses `train_only_standardization`, §7 issue 1).
* **2 states**: `UPPER_HALF` / `LOWER_HALF` around the train-only median of inner out-of-fold scores. No other threshold exists.
* **Single-direction events only.** `direction_definition.values` must be `[1]` or `[-1]`; any event table with both signs, or with a sign other than the spec's, is `FAIL EVENT CONTRACT`.
  A mixed indicator is two experiments (`EXP_xxxx_LONG`, `EXP_xxxx_SHORT`) registered *before* results. Each consumes a campaign slot and 24 trials.
* **DEVELOPMENT_CV** (`TRIAL_POLICY.yaml: development_cv`): development events are cut into K+1 = 6 consecutive blocks of equal model-eligible event count
  (boundaries use event timestamps only, snapped to exchange-local day starts); the 5 folds validate blocks 1…5 with an expanding window. A training event is legal only if
  `event_time < validation_start` **and** `effective_target_end < validation_start`, where `effective_target_end = max(candidate-claimed end, frozen declared resolution)`
  — a candidate cannot shorten its own label horizon. Minimums remain 300 outer / 5 inner blocks / 50 inner-train / 30 inner-OOF; a fold below any minimum is `SKIPPED_INSUFFICIENT_DATA`
  and reported. Each fold has its own nested inner OOF calibration, threshold and final model. Pooled validation predictions are what the statistics use.
* **Inference** (all on DEVELOPMENT_CV predictions during IS): weekly-block bootstrap (2000) and whole-week-block permutation (**20000** since v2.2.0), seed 1729;
  **BH and Bonferroni** (both reported; only BH gates, plus the fixed raw-p hurdle below) at the experiment level (`experiment_bonferroni_p = min(raw_p×24, 1)`, `experiment_q`) and the campaign level
  (`campaign_bonferroni_p = min(raw_p×24E, 1)`, `campaign_q`, universe = every revealed trial of the campaign including rejected experiments, models and sides).
  Campaign values are recomputed over all revealed trials after **every** new reveal, and earlier experiments' statuses are re-evaluated retroactively
  (candidates can be downgraded to `IS_NO_CANDIDATE`; tested).
* **IS shortlist eligibility of one model trial** (`ACCEPTANCE_RULES.yaml`) = all of: selected frequency ≥ 1.0/week (events ÷ eligible weeks **from bars**); standardized uplift ≥ 0.01 (v2: uplift must beat the null by 0.01 sd; the null-based gates — adjusted p, CI > 0, year/fold/model consistency — carry the burden of proof);
  **absolute selected effect > 0** (a trial with positive uplift but non-positive selected effect is `DIAGNOSTIC_CONDITIONAL_IMPROVEMENT`, never eligible); bootstrap CI lower bound > 0;
  **raw permutation p ≤ 0.00135 (t ≥ 3, one-sided; v2.2.0; the same at every experiment and campaign size; replaces the Bonferroni gates)**; `experiment_q` and `campaign_q` ≤ 0.05; year consistency; batch/year concentration (v2.1). A TARGET|SIDE group needs ≥ 2 of 3 eligible models.
  The statuses are `IS_REJECTED`, `IS_PROVISIONAL_CANDIDATE` (gates pass but verification/sensitivity not yet complete), `IS_SHORTLIST_ELIGIBLE`.
* **Year consistency**: among UTC calendar years of the DEVELOPMENT_CV validation events with ≥ 20 selected events, ≥ 70% need positive selected effect **and** ≥ 70% need positive uplift.
  A year whose |selected events × uplift| exceeds 35% of the total raises `YEAR_CONCENTRATION_WARNING` (reported, **not** a rejection).
* **Concentration (v2.1.0, replaces the fold gate)**: the out-of-fold selected trades are cut, in time order, into 10 equal-count batches; the single best batch may carry at most 35% of the total uplift mass, and with ≥ 2 eligible years the uplift mass without the best year must stay positive. This asks "does a small set carry the result?" and needs no minimum number of folds. The 4-of-5-folds gate and the "all 5 folds evaluated" requirement were removed because they acted as a sample-size wall for low-frequency setups; the 5 walk-forward folds still produce the out-of-fold predictions and are reported (informational only).
* **Filter ladder** (optional, frozen order, development only, never alters a trial): `filter_ladder` in the spec + `detect_events_ladder()`; each step reports events, frequency, retention,
  effect / uplift versus the parent and the previous step per target, yearly tables and the flags `NO_CONSISTENT_IMPROVEMENT` / `FREQUENCY_DESTRUCTION`; steps identical to the previous step are unflagged.
  Every row is logged in `observations.csv`.
* **Ranking** (deterministic, `rank_trials` / `rank_groups`): standardized uplift DESC, `campaign_bonferroni_p` ASC, selected frequency DESC, `trial_id` ASC. A group needs ≥ 2/3 eligible models and is ranked
  by the median uplift of its eligible models; the report shows the TOP 5 groups. There is no subjective selection.

## 5. Near-ties, human decisions, selection holdout, final config, automatic CPCV, lockbox

**Human approvals required vs not required**

| ACTION | HUMAN APPROVAL? |
|---|---|
| Define / confirm event premise | YES |
| Run DEVELOPMENT / IS | YES (explicit run) |
| Open selection holdout | YES |
| Choose final config | YES |
| Run fixed CPCV | **NO** (automatic after `FINAL_CONFIG_FROZEN`) |
| Open final lockbox | YES (not implemented) |

Automated diagnostics / verifier / sensitivity do not need separate approval once their stage is legitimately entered. All of the following is in `frozen/v1/SELECTION_PROCESS.yaml` (hashed into every manifest).

1. **Stop + near-tie detection.** `run_experiment.py` ends after writing `IS_REPORT.json/.md` (sections A–Y plus **NT. CONFIGURATION UNCERTAINTY / NEAR-TIES**; `M–Q` share one heading). The unit of a configuration is a TARGET × SIDE group retaining all 3 models.
   Two groups of the same experiment are a **near-tie** iff both are `IS_SHORTLIST_ELIGIBLE` (≥ 2 of 3 eligible models; the existing `rank_groups` set), they are on the same side (UPPER with UPPER, LOWER with LOWER),
   |difference of median standardized uplift| ≤ **0.03**, and the paired weekly-block bootstrap 95% CI (2000 repetitions, seed 1729) of that difference, computed on the *same* DEVELOPMENT_CV validation observations, contains 0. No number is tuned or searched.
   Near-tie edges form **connected components**; members are ranked by the existing frozen IS group ranking (no new metric) and **only the top 2 of a cluster may be proposed** for the holdout (config 3 is not tested merely because 1 and 2 fail later).
   Near-tie analysis creates **no selection trial** (the development count stays exactly 24), can never promote a rejected config and never chooses. The report lists, per cluster: config IDs, target, side, frequency, median standardized uplift, selected effect, campaign BH / Bonferroni, year and fold consistency, pairwise differences, the paired CI and the reason.
2. **Statuses after IS.** `IS_REJECTED`; `AWAITING_HUMAN_FINAL_CONFIG_SELECTION` (eligible, no near-tie cluster); `NEAR_TIE_REVIEW_REQUIRED` (eligible, ≥ 1 cluster; the documented alias `AWAITING_HUMAN_SELECTION_HOLDOUT_APPROVAL` names the same state). The engine stops and never decides for the human:
   **A.** choose ONE IS-eligible config directly and skip the holdout (`SELECTION_HOLDOUT_SKIPPED`); **B.** approve the top 2 near-tied configs of one cluster for the selection holdout; **C.** decline (`HUMAN_DECLINED`).
3. **Human holdout approval** `approvals/EXP_xxxx_SELECTION_HOLDOUT_APPROVAL.yaml` (fields `experiment_id, campaign_id, manifest_sha256, is_report_sha256, near_tie_cluster_id, approved, approved_by, approved_configs, approval_note`; template in `templates/approval/`).
   **Scripts and LLMs never create it** (AGENTS.md; no engine function writes into `approvals/`). ≤ 2 configs per experiment (`MAX_SELECTION_HOLDOUT_CONFIGS_PER_EXPERIMENT`), exactly the proposable pair of one cluster; ≤ 6 per campaign. Invalid if the event, spec, frozen specs, partitions, IS results or IS report change, or if any of the 3 model paths of a config lacks a strong-mode verification.
4. **Campaign freeze, then ONE opening (the accounting unit is the CAMPAIGN).** `freeze_campaign_selection_holdout.py` (human-run) is refused unless every experiment of the campaign finished IS; it closes the campaign and freezes **all** approved configs of all experiments together
   (`registry/selection_holdout_freeze_<campaign>.json`: campaign, partition hash, experiment / IS-report / approval hashes, config IDs, family size) **before any holdout byte is read**; max 6 configs × 3 models = **18** evaluations on the SAME interval; no sequential "test A, look, then decide on B".
   `run_campaign_selection_holdout.py` additionally needs the human file `approvals/CAMPAIGN_<id>_SELECTION_HOLDOUT_OPEN_APPROVAL.yaml` citing the freeze hash; the single ledger row in `registry/selection_holdout_access.csv` (append-only SHA hash chain, one row per campaign; campaign, freeze and approval hashes, partition boundaries, frozen config IDs, timestamp, engine hash, family size)
   is written **before** any holdout computation (`SELECTION_HOLDOUT_SPENT`). No second opening, no added configs, and no overlapping campaign may claim the spent partition as untouched.
5. **Multiplicity.** IS: unchanged (24-trial experiment BH/Bonferroni and campaign-wide revealed-trial BH/Bonferroni). Holdout: `raw_p`, `selection_holdout_q`, `selection_holdout_bonferroni_p = min(raw_p × m, 1)` over **every approved config × 3 models of the whole campaign, losers included**. These are *selection-holdout evidence* values, never confirmation p-values. The lockbox multiplicity is **not** designed (the lockbox is not implemented).
6. **Holdout report** (`SELECTION_HOLDOUT_REPORT.json/.md`): labelled **"SELECTION DATA — USED TO CHOOSE FINAL CONFIGURATION / NOT FINAL CONFIRMATION"**; for every frozen config all 3 models (N, frequency, effect, uplift, standardized uplift, raw p, BH q, Bonferroni), year/month breakdown, path / MFE-MAE / continuation-reversal / bracket diagnostics, the campaign family size and the deterministic advisory preference.
   Because the holdout exists for selection, the human may use these diagnostics — but only to choose among configs frozen before the opening: no new config, threshold, bracket in the final config or model parameter.
7. **Advisory `HOLDOUT_PREFERRED_CONFIG`.** Requires selected effect > 0, frequency ≥ 1/week and ≥ 2 of 3 models with positive uplift; ranks by median standardized uplift DESC, median selected effect DESC, frequency DESC, frozen IS rank ASC, config ID ASC. If the top two are still within the same near-tie rule (|Δ| ≤ 0.03 and paired CI contains 0) the engine reports **`HOLDOUT_UNRESOLVED`** instead of fabricating certainty; `NO_QUALIFYING_CONFIG` if none qualifies. Path diagnostics never enter this rule.
8. **Final config** (after a holdout: minimum viability floor, v1.2.1) `approvals/EXP_xxxx_FINAL_CONFIG_SELECTION.yaml` (human only; `experiment_id, campaign_id, manifest_sha256, is_report_sha256, selection_holdout_report_sha256, selected_config_id, selected_by, selection_note`): exactly ONE config, frozen before the opening and actually evaluated in the holdout; or `DECLINE`.
   **Viability floor, no human override:** after a holdout the human may choose a config only if, in the holdout, its selected effect > 0, its selected frequency ≥ 1.0/week and ≥ 2 of its 3 models have positive uplift (group medians for effect and frequency; the same conditions as the preference requirements). If no frozen config satisfies all three the status is **`NO_FINAL_CONFIG`**: the experiment stops, CPCV never runs and not even a decline re-opens it. `HOLDOUT_UNRESOLVED` may still be reported for close configs, but a config chosen by the human must first be viable. No other gate was added.
   Direct selection without a holdout references the IS report (`selection_holdout_report_sha256: null`), must still be one deterministic IS-eligible config, and marks `SELECTION_HOLDOUT_SKIPPED`; the unused holdout data stay unread. Accepted ⇒ `FINAL_CONFIG_FROZEN` and one append-only row in `registry/final_configs.csv`
   (campaign, experiment, selected config, IS rank, near-tie cluster, holdout used yes/no, holdout rank, human file hash, manifest hash, timestamp, CPCV status; hash-chained and integrity-checked).
9. **Automatic CPCV** (`finalize_final_config.py` validates + freezes and then runs it; `run_cpcv.py` resumes it) needs **no approval**. Data: DEVELOPMENT + SELECTION_HOLDOUT if the holdout was used, DEVELOPMENT only if skipped; the lockbox is never loaded. Mechanics unchanged: 6 chronological groups, 2 held out ⇒ 15 splits; purge + embargo = max primary horizon on both sides of every held-out region; train-only preprocessing, thresholds and nested calibration;
   `CPCV_PASS` per model: median effect > 0, median uplift > 0, ≥ 12/15 splits with positive effect and ≥ 12/15 with positive uplift; ≥ 2 of 3 models. It is labelled **"POST-SELECTION ROBUSTNESS — NOT INDEPENDENT CONFIRMATION"**; it can pass or veto only — never select, rescue, retune or replace.
   The PBO-style diagnostic (see `docs/CPCV_PBO.md`) never influences anything.
10. **No fallback.** `CPCV_REJECTED` ends the lineage: the engine never falls back to the runner-up (that would be another selection after additional evidence). Using the runner-up needs a new, explicitly registered lineage / campaign. `CPCV_CONFIRMED ⇒ AWAITING_FINAL_LOCKBOX_APPROVAL`.
11. **Final lockbox.** Never opened by any code path; it has had no role in event discovery, feature design, model design, IS ranking, near-tie identification, holdout comparison, final-config selection or CPCV, so it is the only dataset that may legitimately be called FINAL UNTOUCHED CONFIRMATION — only after explicit human approval, which is **not implemented in this patch**.
12. **Statuses.** `DRAFT, FROZEN, IS_REJECTED, IS_SHORTLIST_ELIGIBLE, NEAR_TIE_REVIEW_REQUIRED, AWAITING_HUMAN_SELECTION_HOLDOUT_APPROVAL (alias), SELECTION_HOLDOUT_FROZEN, SELECTION_HOLDOUT_SPENT, AWAITING_HUMAN_FINAL_CONFIG_SELECTION, SELECTION_HOLDOUT_SKIPPED, FINAL_CONFIG_FROZEN, CPCV_REJECTED, CPCV_CONFIRMED, AWAITING_FINAL_LOCKBOX_APPROVAL, LOCKBOX_REJECTED, LOCKBOX_CONFIRMED`
    (plus `IS_PROVISIONAL_CANDIDATE`, `HUMAN_DECLINED`, `SELECTION_HOLDOUT_CONTAMINATED`, `NO_FINAL_CONFIG`). The two `LOCKBOX_*` statuses exist but are never entered by the engine.

## 5c. Monetisation (bracket) study (v2.3.0) — separate stage, development data only, not a selection trial

`scripts/run_monetisation_study.py` runs only for the ONE final configuration of an experiment that passed CPCV (`CPCV_CONFIRMED` / `AWAITING_FINAL_LOCKBOX_APPROVAL`; never after `CPCV_REJECTED`). Spec: `frozen/v1/MONETISATION_SPEC.yaml`. Events = those selected by ≥ 2 of the 3 models in the out-of-fold DEVELOPMENT_CV predictions; bars = development rows only (the selection holdout and lockbox are not loaded).
Grid: stop ∈ {1, 2, 3} × ATR, target ∈ {1, 2, 3} × ATR, ATR(14, Wilder) of 1-minute or 5-minute bars (latest completed bar at the event time), optional time limits {15, 30, 60, 120} bars (always also cut at the RTH close). Entry = open of the first forward bar; a bar touching both levels counts as a stop; touched levels fill at the level; cost = 3 ticks round trip.
Pick rule (written before any result): a cell is **stable** if it has ≥ 100 trades, a positive net expectancy, ≥ 70% positive eligible years, and all 8 neighbours (stop/target scaled ×0.75 / ×1.25, together or separately) are positive and keep ≥ 50% of the centre's net expectancy. The chosen cell is the stable one with the best worst-neighbourhood net expectancy. If no cell is stable the result is `NO_STABLE_BRACKET` — never a fallback to the best single cell. The output is development-data evidence only; the chosen bracket must still be tested on data it has not seen. It changes no status, rank or registry row.

## 5b. Forward-path and monetisation diagnostics (v1.1.0) — DIAGNOSTIC ONLY

`frozen/v1/PATH_DIAGNOSTICS.yaml` (hashed into every manifest) freezes horizons (5/15/30/60/120 bars), all formulas, the exact percentiles (linear interpolation; no others), the sigma unit
(`sigma_ref = RV_60 / sqrt(60)`: the one-bar RMS log-return scale derived from the frozen 60-bar `RV_60`; used for MFE/MAE σ units, every barrier and all 64 bracket cells; no other normaliser, no fallback to raw `RV_60`), the 4 symmetric + 4 asymmetric first-passage cases at horizons 15/30/60/120 and the fixed **64-cell bracket surface**
(4 stops × 4 targets × 4 expiries, canonical order expiry/stop/target, never performance order). For every model-eligible event, per horizon: endpoint returns, continuation/reversal/flat counts, MFE/MAE (points, ticks from the instrument config, σ units),
path dominance, time to extrema, first passage and brackets (conservative result = `AMBIGUOUS_SAME_BAR` counted as STOP is primary; raw-path result excludes ambiguous observations). Contexts: all events and UPPER/LOWER_HALF of every target × model (DEVELOPMENT_CV pooled validation events), by year, by
DEVELOPMENT_CV fold, plus the frozen filter-ladder steps. Gross points only: **GROSS — COSTS NOT APPLIED**; **DIAGNOSTIC ONLY — NO BRACKET WAS SELECTED**.

* It runs after the 24 trials are revealed, reads only development rows, writes `results/PATH_DIAGNOSTICS.json` (hash-bound into `results.json` and `IS_REPORT.json`) and an IS-report section Z (separated from the PROMOTION EVIDENCE). Nothing enters `selection_trials.csv`, BH, Bonferroni, ranking or status (tests compare a run with and without the layer).
* `PATH_TIMESTAMP_INELIGIBLE` is decided per event and horizon from timestamps only (non-consecutive bars, data end, completion after the RTH close; non-finite prices also void a window). Exact arithmetic (RTH 09:30–16:00 America/New_York, DST-safe; tested bar by bar): a window of h bars is eligible iff its last bar completes by 16:00, i.e. the first forward bar opens no later than 16:00 − h minutes (latest event times 15:55 / 15:45 / 15:30 / 15:00 / 14:00 for h = 5 / 15 / 30 / 60 / 120). With the template's `eligible_session` ending at 15:00 every event is 60-bar eligible, but events after 14:00 are PATH_TIMESTAMP_INELIGIBLE at 120 bars.
* Memory: streaming over forward-bar steps vectorised over events (O(events) state, no events × horizon matrices).
* **PATH DIAGNOSTICS ARE NON-PROMOTABLE.** They never change `IS_PROVISIONAL_CANDIDATE` / `IS_SHORTLIST_ELIGIBLE`, trial or group ranking, the top-5 IS list, campaign BH/Bonferroni, human-approval eligibility or SELECTION HOLDOUT group order (tested by rewriting the diagnostics file). They are hash-bound: altering the artifact invalidates an approval, which is an integrity rule, not an influence on ranking.
* **Human interpretation rule.** A human may approve, decline, or approve fewer than the eligible maximum from the deterministic eligible list. A human may NOT use an attractive path/bracket diagnostic to substitute a non-eligible or lower-ranked configuration that the engine did not place in the approval-eligible set. A different rule, bracket, horizon, threshold or filter inspired by diagnostics needs a NEW experiment or a SEPARATE MONETISATION STUDY; there is no current-experiment promotion.
* Any trading rule, threshold, bracket, horizon, percentile or filter inspired by these numbers needs a NEW registered experiment or a separate monetisation study. CPCV path diagnostics are not implemented (optional in the specification); CPCV remains a veto only.

## 6. External verification

`verify_experiment.py` stages the candidate on the **development cut** only, runs **all 3** model adapters (strong mode) on **all 4 primary targets (12 paths)** — every primary target is promotion-capable, so a target rejected at IS time is still verified — and checks the verifier checkout is the pinned commit with a clean tree (`VERIFIER_PIN.yaml`).
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
4. **Selection-holdout evidence-gate constants are my definition.** You specified BH + Bonferroni across all approved config × 3 model evaluations and ≥ 2/3 models; the remaining numeric gates (frequency ≥ 1/week, uplift ≥ 0.01, effect > 0, CI low > 0) mirror the IS gates (`selection_holdout_evidence:` in `ACCEPTANCE_RULES.yaml`). They are informational labels on selection data, not a confirmation.
5. **The CPCV group rule (≥ 2 of 3 models) mirrors model agreement;** you specified the per-model pass rule only.
6. **PBO configurations** = the (target, side, model) configs of the one final configuration (3 highly dependent configs); the diagnostic is descriptive only.
7. **Permutation statistic** = uplift, one-sided; `p = (1+#≥)/(B+1)`; bootstrap CI = percentile interval over resampled weeks.
8. **Sensitivity verdict (v2.3.0)** probes EVERY probeable numeric base parameter of the event/filter (floats, integers ≥ 3), one at a time, at ×0.75 and ×1.25 (the event spec must list them all). A model is OK at a probe when its selected effect stays > 0, its standardized uplift keeps ≥ 50% of the base uplift and its selected frequency stays ≥ 1/week; a probe is OK when ≥ 2 of 3 models are OK; the candidate fails if any probe is not OK (`max_failing_probes: 0`). Probes only confirm or veto; a better probe never replaces the base parameter.
9. **Static event scan** rejects numeric literals other than `0`/`1` in `event.py` (heuristic). **Causality pre-check** re-runs the event at 8 cutoffs on truncated and future-mutated bars.
10. **The verifier holdout rule (§6) is an engine staging choice, not a research gate;** the fraction/minimum are in `VERIFIER_PIN.yaml` and are for the human to confirm.
11. **Synthetic lifecycle tests inject verification and sensitivity verdicts at table level** (the real verifier and the bar-level sensitivity stage are exercised separately); the lifecycle itself is the real code.

## 8. Spec issues and limitations (documented; ONLY #1 was acted on as a spec change)

1. **XGBoost is not invariant to the unit of the target — ACTED ON in the original build, reversible.** `reg_alpha`/`reg_lambda` are absolute; on log-return targets (sd ≈ 1e-3) the literal model fits a constant. `MODEL_BANK.yaml: target_transform: train_only_standardization`; set `none` to reproduce the literal spec. **Please confirm.**
2. **Previous issue 2 (uplift vs parent could promote a losing state) is now addressed by the absolute `selected_effect > 0` gate.** The two states are still not independent (`uplift_LOWER = (n_UPPER/n_LOWER)·uplift_UPPER`, tested), so there are ≤ 12 independent p-values; Bonferroni over 24 and BH over 24 are conservative accordingly.
3. **Previous issue 3 (mixed-direction events) is now closed by the single-direction rule;** the cost is that a bidirectional indicator consumes two campaign slots.
4. **Previous issue 5 (windows across session gaps) is now closed by the same-session rule,** superseded in v2: events near the close are kept with a window truncated at the close and flagged (no event is dropped for that reason).
5. **The 0.01 uplift floor is permissive by design (v2):** a statistically real but economically tiny effect can pass the IS gates. The 3-tick round-trip cost is NOT a gate in this engine; it matters for the later bracketing/monetisation study. Truncated (late-session) 180-minute windows are shorter than 180 minutes: read the full-horizon vs truncated split in section WM.
6. **Short development windows make the year gate nearly unanimous:** with 3 eligible years 70% requires 3/3, with 2 it requires 2/2, and `YEAR_CONCENTRATION_WARNING` is structurally likely with ≤ 3 years. Choose a long development window.
7. **SELECTION HOLDOUT multiplicity and access are campaign-wide, with a hard campaign cap:** `MAX_SELECTION_HOLDOUT_CONFIGS_PER_CAMPAIGN = 6` approved configs across ALL experiments (2 per experiment) ⇒ at most 6 × 3 = **18** evaluations in the one family. More than 6 refuses the freeze atomically (nothing is written or changed); the cap is frozen policy and is never relaxed because Bonferroni gets strict (×18 at most). Exactly 6 is accepted; 0 never opens SELECTION HOLDOUT.
8. **The verifier pin** (`624c8b7f…`, on branch `claude/relaxed-lamport-119uli` of `engine-verification-`) is the commit that introduced `scripts/verify_research.py`; there are no tags. **The human must confirm or replace it.**
9. **Float reproducibility.** Batch shape can change reductions by ≤ 1 ulp (invariance tests use `rtol=1e-12`; the verifier compares at `atol=1e-9`).
10. Everything was validated on **synthetic** data with known structure; **no real NQ data has been run.** Real data will exercise gap handling, zero-volume windows and roll provenance.
11. Missing continuous-contract roll provenance keeps the verifier's *global* verdict INCOMPLETE (exit 2); reported separately and never treated as a pass.
12. Static scans and the causality pre-check are heuristic evidence, not proof of causality. Sizing, prop-firm simulation and the final lockbox confirmation are intentionally absent; costs and brackets exist only in the separate development-data monetisation study (section 5c).
