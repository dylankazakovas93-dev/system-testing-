# conditional-edge-engine

A **frozen research factory**: take one precisely specified, single-direction, causal market event (optionally translated from a
TradingView/Pine indicator) and test whether the market state at that event holds robust conditional information about
the next 15–60 minutes — while making it impossible to fish for a result.

```
EVENT -> FROZEN MARKET STATE (56 features) -> FROZEN SAME-SESSION TARGETS (4) -> 3 MODELS x 2 STATES = 24 SELECTION TRIALS
   -> DEVELOPMENT_CV (5 purged folds) -> IS REPORT  ==== STOP: human reads the entire IS selection history ====
   -> human approval file -> ONE-SHOT CONFIRMATION OOS -> CPCV veto -> AWAITING_FINAL_LOCKBOX (lockbox stays sealed)
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
# once per campaign: three chronological, non-overlapping partitions, frozen into every experiment's manifest
python scripts/new_experiment.py --new-campaign C001 --development-end 2023-01-01 --oos-end 2024-07-01 --lockbox-start 2024-07-01
python scripts/new_experiment.py --campaign C001                 # -> experiments/EXP_0001 from the template (one slot of 20)
#   edit ONLY HYPOTHESIS.md, EVENT_SPEC.yaml, event.py, reference.pine  (ONE direction per experiment: _LONG / _SHORT are two experiments)
python scripts/freeze_experiment.py --experiment EXP_0001        # hash + lock + pre-register exactly 24 selection trials
python scripts/run_experiment.py    --experiment EXP_0001 --data /path/NQ_1m.parquet   # IS only; STOPS; writes IS_REPORT.json/.md
python scripts/verify_experiment.py --verifier-repo ../engine-verification- --experiment EXP_0001 --data /path/NQ_1m.parquet   # all 3 model paths
python scripts/show_approval_hashes.py --experiment EXP_0001     # read-only: the hashes a human approval must cite
#   --- HUMAN reads IS_REPORT.md and, if desired, writes approvals/EXP_0001_OOS_APPROVAL.yaml (never a script / LLM) ---
python scripts/run_oos.py  --experiment EXP_0001 --data /path/NQ_1m.parquet    # refuses without a valid approval; ONE shot
python scripts/run_cpcv.py --experiment EXP_0001 --data /path/NQ_1m.parquet    # only after OOS_CONFIRMED; veto only
python scripts/campaign_status.py                                # counters, lifecycle statuses, OOS ledger, integrity check
```

`--data` = CSV/Parquet with `timestamp, open, high, low, close, volume` (1-minute, **open-stamped**). `run_experiment.py` loads only rows before
`development_end`; `run_oos.py` only rows before `oos_end`; nothing loads the lockbox.

If `event.py` or the spec must change after results were revealed: `new_experiment.py --campaign C001 --lineage-of EXP_0001`.

## Layout

| Path | Purpose |
|---|---|
| `frozen/v1/*.yaml`, `instruments/NQ_1m.yaml` | the frozen specification (hashed at freeze), incl. `VERIFIER_PIN.yaml` |
| `features/*.py` | the 56 feature formulas (one module per family) |
| `engine/` | partitions, feature/target/model engines, DEVELOPMENT_CV walk-forward + nested calibration, statistics, BH + Bonferroni, acceptance + ranking, registry, runner, ladder, sensitivity, IS report, OOS stage, CPCV, verifier bridge |
| `experiments/EXP_xxxx/` | per-experiment: the four editable files, `FROZEN_MANIFEST.json`, `results/`, `verification/` |
| `registry/` | `campaigns`, `experiments`, `selection_trials` (24/experiment), `observations`, `oos_access` (append-only hash chain), `oos_trials`, `cpcv_results` |
| `approvals/` | **human-written** OOS approval files only (`README.md` explains; templates in `templates/approval/`) |
| `templates/experiment/` | HYPOTHESIS, EVENT_SPEC, `event.py` (single-direction confirmed pivot), `reference.pine` |
| `scripts/` | CLI; `confirm_lockbox.py` is an intentional stub |
| `docs/` | `CPCV_PBO.md`, `SYNTHETIC_RESULTS.md` |
| `tests/` | deterministic unit, synthetic-scenario, lifecycle (IS → human gate → OOS → CPCV), partition-guard, end-to-end and verifier-integration tests |

## Reading a result

`IS_REPORT.md` (sections A–Y) lists the hypothesis, exact event definition, raw frequency, data period, the exact trial count
(`EXPERIMENT SELECTION TRIALS: 24 / 24`, `CAMPAIGN REVEALED SELECTION TRIALS: N / 480`), all 24 trials with parent/selected frequency,
retention, effects, uplift, bootstrap CI, raw p, experiment/campaign Bonferroni and BH q, every calendar year, all five
**DEVELOPMENT_CV** folds (labelled as internal CV, never OOS), feature diagnostics (*DIAGNOSTIC ONLY — NOT A SELECTION TRIAL*), the
filter ladder, sensitivity, the deterministic top-5 TARGET|SIDE groups, why each shortlisted configuration emerged and why every
other one was rejected, exact hashes, and the OOS status (`NOT ACCESSED` until the ledger says otherwise).
Rejected and low-frequency results are never hidden.

## Evidence in this repository

* `docs/SYNTHETIC_RESULTS.md` — planted-structure scenarios and the lifecycle outcomes. Reproduce with `python scripts/synthetic_summary.py`.
* `examples/planted_momentum_demo/` — a snapshot of one real CLI run on synthetic planted-momentum bars: IS report, 24-trial registry, and strong-mode verification of all 3 model paths at the pinned commit (synthetic data; the human approval step was not performed).
* `RESEARCH_RULES.md` §7–§8 — interpretation choices, spec issues and known limitations (the XGB target-standardisation choice and the verifier pin need human confirmation).
