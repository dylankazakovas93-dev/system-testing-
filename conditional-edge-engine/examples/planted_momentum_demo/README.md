# SYNTHETIC DATA — NOT REAL NQ

Canonical snapshot of one IS run through the real CLIs with **engine v1.1.0** on **synthetic** 1-minute bars with a planted AR(1) momentum
(`make_bars(1100, seed=7, phi=0.8)`, 2016-01-04 … 2020-03). It shows that the pipeline runs end to end. It says nothing about real NQ.

* **Engine**: `FROZEN_MANIFEST.json` records `engine_version v1.1.0`, the engine code hash and `frozen/v1/PATH_DIAGNOSTICS.yaml` (checked equal to the final code when built).
* **Partitions** (frozen in the manifest): development < 2019-01-01 · confirmation OOS 2019-01-01 … 2019-07-01 · final lockbox from 2019-10-01. The IS run read **only** development rows.
* **Campaign-level OOS state** (`registry/campaigns.csv`): `C001` is `OPEN`; no freeze hash; `registry/oos_access.csv` (one row per *campaign*) is header-only; the IS report says `OOS status = NOT ACCESSED`; the lockbox was never read.
* **Lifecycle**: `EXP_0001` stopped at `AWAITING_HUMAN_OOS_APPROVAL` (IS_SHORTLIST_ELIGIBLE after strong-mode verification). No human approval, no campaign freeze, no OOS opening were performed.
  A campaign may freeze at most 6 approved groups (2 per experiment) = at most 18 OOS confirmations.
* **Selection**: 24 selection trials (`registry/selection_trials.csv`): 16 `IS_SHORTLIST_ELIGIBLE`, 6 `REJECTED_INSUFFICIENT_UPLIFT` (`DIR_RETURN_60`), 2 `REJECTED_INSTABILITY` (2 of 3 eligible years positive, 66.7% < 70%).
  These are identical with and without the path-diagnostics layer (tested).
* **Forward-path diagnostics (DIAGNOSTIC ONLY)**: `experiment/results/IS_REPORT.md` section **Z** (non-promotable): endpoint returns, continuation/reversal, MFE/MAE, time to extrema, first passage and the fixed **64-cell gross bracket surface**
  (`GROSS — COSTS NOT APPLIED`, `DIAGNOSTIC ONLY — NO BRACKET WAS SELECTED`) for the raw event; the full detail (25 contexts incl. every target × model × state, by year and fold) is
  `results/PATH_DIAGNOSTICS.json` (6.7 MB, **not included here**; sha256 `2d2614732b4527dd34dd1eb3121df0581a7ae8df2b8a1662ee65e7a00d427528` is recorded in `IS_REPORT.json`). None of it enters the selection trials, BH or Bonferroni.
* **External verification**: `verify_experiment.py` at the pinned commit `624c8b7f…`, **strong** mode, RIDGE/SPLINE/XGB × 3 candidate targets = 9 runs. Every path: all research families `PASS`, label `RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE`
  (exit code 2: no roll provenance in synthetic data). Never `VERIFIED`. See `verify_experiment_*.log`. Local paths in the logs were replaced by `WS` / `DATA`.
* Large intermediates (CV panels, path-diagnostics file, staged verifier copy, data) are intentionally not included.

Reproduce (the manifest pins the engine hash, so it only reproduces against the same engine code):

```bash
python scripts/new_experiment.py --new-campaign C001 --development-end 2019-01-01 --oos-end 2019-07-01 --lockbox-start 2019-10-01 --workspace WS
#   event.py / EVENT_SPEC.yaml as in experiment/ ; then
python scripts/freeze_experiment.py --experiment EXP_0001 --workspace WS
python scripts/run_experiment.py    --experiment EXP_0001 --data NQ_planted.parquet --workspace WS
python scripts/verify_experiment.py --verifier-repo ../engine-verification- --experiment EXP_0001 --data NQ_planted.parquet --workspace WS
```
