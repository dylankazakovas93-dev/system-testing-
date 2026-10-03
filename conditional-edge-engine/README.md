# conditional-edge-engine

A **frozen research factory**: take one precisely specified, single-direction, causal market event (optionally translated from a
TradingView/Pine indicator) and test whether the market state at that event holds robust conditional information about
the next 15–60 minutes — while making it impossible to fish for a result.

```
EVENT -> FROZEN MARKET STATE (56 features) -> FROZEN SAME-SESSION TARGETS (4) -> 3 MODELS x 2 STATES = 24 SELECTION TRIALS
   -> DEVELOPMENT_CV (5 purged folds) -> IS REPORT + NEAR-TIE DETECTION   ==== STOP: human reads the IS selection history and the configuration uncertainty ====
   -> HUMAN DECISION:  A choose ONE config directly (holdout skipped) | B approve the top-2 near-tied configs for the SELECTION HOLDOUT | C decline
   -> [campaign freeze of all approved configs -> human open approval -> ONE campaign-wide SELECTION HOLDOUT opening (selection data, NOT confirmation)]
   -> HUMAN CHOOSES EXACTLY ONE FINAL CONFIG -> AUTOMATIC CPCV (post-selection robustness / veto, no approval) -> AWAITING_FINAL_LOCKBOX_APPROVAL
   -> (human approval; NOT implemented) FINAL LOCKBOX = the only untouched confirmation
```

This is the **research engine** (untrusted). It is separate from the frozen verification repo `engine-verification-`, which is never
copied or modified here; `scripts/verify_experiment.py` calls it at a pinned commit (`frozen/v1/VERIFIER_PIN.yaml`).
Read `RESEARCH_RULES.md` first (frozen rules, my interpretation choices, spec issues, limitations) and `AGENTS.md` (rules for any agent).

**Status: validated on synthetic data only. No real NQ data has been run.**

## Install / test

```bash
python -m pip install -r requirements.txt
python -m pytest -n 4 --dist loadscope     # the lifecycle / scenario modules are slow (minutes); -n 4 parallelises per module/class
```

## Workflow (one experiment)

```bash
# once per campaign: DEVELOPMENT / 1-or-2-year SELECTION_HOLDOUT / FINAL_LOCKBOX (lockbox starts right after the holdout); frozen into every experiment's manifest
python scripts/new_experiment.py --new-campaign C001 --development-end 2023-01-01 --selection-holdout-years 1
python scripts/new_experiment.py --campaign C001                 # -> experiments/EXP_0001 from the template (one slot of 20)
#   edit ONLY HYPOTHESIS.md, EVENT_SPEC.yaml, event.py, reference.pine  (ONE direction per experiment: _LONG / _SHORT are two experiments)
python scripts/freeze_experiment.py --experiment EXP_0001        # hash + lock + pre-register exactly 24 selection trials
python scripts/run_experiment.py    --experiment EXP_0001 --data /path/NQ_1m.parquet   # IS only; STOPS; writes IS_REPORT.json/.md (incl. NEAR-TIES)
python scripts/verify_experiment.py --verifier-repo ../engine-verification- --experiment EXP_0001 --data /path/NQ_1m.parquet   # all 12 paths
python scripts/show_approval_hashes.py --experiment EXP_0001     # read-only: the hashes / eligible configs / near-tie clusters a human file must cite
#   --- HUMAN reads IS_REPORT.md and decides (the engine never decides): ---
#   A. direct choice, holdout skipped: write approvals/EXP_0001_FINAL_CONFIG_SELECTION.yaml (selection_holdout_report_sha256: null)
#      -> python scripts/finalize_final_config.py --experiment EXP_0001 --data ...      # freezes the final config, then runs CPCV automatically
#   B. near-tie cluster: write approvals/EXP_0001_SELECTION_HOLDOUT_APPROVAL.yaml (top 2 of ONE cluster), then (all IS stages of the campaign complete):
python scripts/freeze_campaign_selection_holdout.py --campaign C001   # HUMAN-run: closes the campaign, freezes ALL approved configs together (<= 6 configs = <= 18 evaluations)
python scripts/show_approval_hashes.py --campaign C001          # read-only: the freeze hash the campaign-open approval must cite
#   --- HUMAN writes approvals/CAMPAIGN_C001_SELECTION_HOLDOUT_OPEN_APPROVAL.yaml ---
python scripts/run_campaign_selection_holdout.py --campaign C001 --data /path/NQ_1m.parquet   # opens the shared holdout ONCE; SELECTION DATA, not confirmation
python scripts/show_approval_hashes.py --experiment EXP_0001 --final   # hashes for the final-config file
#   --- HUMAN writes approvals/EXP_0001_FINAL_CONFIG_SELECTION.yaml (exactly ONE config evaluated in the holdout, or DECLINE) ---
python scripts/finalize_final_config.py --experiment EXP_0001 --data /path/NQ_1m.parquet   # FINAL_CONFIG_FROZEN, then CPCV runs AUTOMATICALLY (no approval)
python scripts/campaign_status.py                                # counters, lifecycle statuses, ledgers, integrity check
```

`--data` = CSV/Parquet with `timestamp, open, high, low, close, volume` (1-minute, **open-stamped**). `run_experiment.py` loads only rows before
`development_end`; `run_campaign_selection_holdout.py` only rows before `selection_holdout_end`; CPCV loads development (+ the holdout if it was used); nothing loads the final lockbox.
A CPCV failure ends the lineage (no fallback to a runner-up).

| ACTION | HUMAN APPROVAL? |
|---|---|
| Define / confirm event premise | YES |
| Run DEVELOPMENT / IS | YES (explicit run) |
| Open selection holdout | YES |
| Choose final config | YES |
| Run fixed CPCV | NO |
| Open final lockbox | YES (not implemented) |

If `event.py` or the spec must change after results were revealed: `new_experiment.py --campaign C001 --lineage-of EXP_0001`.

## Layout

| Path | Purpose |
|---|---|
| `frozen/v1/*.yaml`, `instruments/NQ_1m.yaml` | the frozen specification (hashed at freeze), incl. `VERIFIER_PIN.yaml` |
| `features/*.py` | the 56 feature formulas (one module per family) |
| `engine/` | partitions, feature/target/model engines, DEVELOPMENT_CV walk-forward + nested calibration, statistics, BH + Bonferroni, acceptance + ranking, registry, runner, ladder, sensitivity, IS report, near-tie detection, SELECTION HOLDOUT stage, holdout preference, final config, automatic CPCV, verifier bridge |
| `experiments/EXP_xxxx/` | per-experiment: the four editable files, `FROZEN_MANIFEST.json`, `results/`, `verification/` |
| `registry/` | `campaigns`, `experiments`, `selection_trials` (24/experiment), `observations`, `selection_holdout_access` (append-only hash chain, one row per campaign), `selection_holdout_trials`, `final_configs` (append-only hash chain), `cpcv_results` |
| `approvals/` | **human-written** files only: holdout approval, campaign-open approval, final-config selection (`README.md` explains; templates in `templates/approval/`) |
| `templates/experiment/` | HYPOTHESIS, EVENT_SPEC, `event.py` (single-direction confirmed pivot), `reference.pine` |
| `scripts/` | CLI; `confirm_lockbox.py` is an intentional stub |
| `docs/` | `CPCV_PBO.md`, `SYNTHETIC_RESULTS.md` |
| `tests/` | deterministic unit, synthetic-scenario, lifecycle (IS → near-tie → human gate → SELECTION HOLDOUT → final config → CPCV), partition-guard, end-to-end and verifier-integration tests |

## Reading a result

`IS_REPORT.md` (sections A–Y plus **NT. CONFIGURATION UNCERTAINTY / NEAR-TIES**) lists the hypothesis, exact event definition, raw frequency, data period, the exact trial count
(`EXPERIMENT SELECTION TRIALS: 24 / 24`, `CAMPAIGN REVEALED SELECTION TRIALS: N / 480`), all 24 trials with parent/selected frequency,
retention, effects, uplift, bootstrap CI, raw p, experiment/campaign Bonferroni and BH q, every calendar year, all five
**DEVELOPMENT_CV** folds (labelled as internal CV, never SELECTION HOLDOUT), feature diagnostics (*DIAGNOSTIC ONLY — NOT A SELECTION TRIAL*), the
filter ladder, sensitivity, the deterministic top-5 TARGET|SIDE groups, why each shortlisted configuration emerged and why every
other one was rejected, exact hashes, and the SELECTION HOLDOUT status (`NOT ACCESSED` until the campaign SELECTION HOLDOUT is opened).
Rejected and low-frequency results are never hidden.

## Forward-path diagnostics (DIAGNOSTIC ONLY)

`IS_REPORT.md` section **Z** (non-promotable) and `results/PATH_DIAGNOSTICS.json` report endpoint returns, continuation/reversal, MFE/MAE, time to extrema, first passage and a fixed 64-cell *gross* bracket surface
(`GROSS — COSTS NOT APPLIED`, `DIAGNOSTIC ONLY — NO BRACKET WAS SELECTED`) for the raw event and every model/state subset. Frozen in `frozen/v1/PATH_DIAGNOSTICS.yaml`; they never enter the 24 trials, multiplicity, ranking, approval eligibility or status (`sigma_ref = RV_60 / sqrt(60)`, one-bar RMS scale). A human may approve, decline or approve fewer from the deterministic eligible list; a diagnostic never justifies a different group, bracket or filter (that is a new experiment or a separate monetisation study).

## Evidence in this repository

* `docs/SYNTHETIC_RESULTS.md` — planted-structure scenarios and the lifecycle outcomes. Reproduce with `python scripts/synthetic_summary.py`.
* `examples/planted_momentum_demo/` — a snapshot of one real CLI run on synthetic planted-momentum bars: IS report, 24-trial registry, and strong-mode verification of all 3 model paths at the pinned commit (synthetic data; the human approval step was not performed).
* `RESEARCH_RULES.md` §7–§8 — interpretation choices, spec issues and known limitations (the XGB target-standardisation choice and the verifier pin need human confirmation).
