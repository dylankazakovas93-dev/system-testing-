# SYNTHETIC DATA — NOT REAL NQ

Canonical snapshot of one IS run through the real CLIs with **engine v1.2.1** on **synthetic** 1-minute bars with a planted AR(1) momentum
(`make_bars(1100, seed=7, phi=0.8)`, 2016-01-04 … 2020-03). It shows that the pipeline runs end to end. It says nothing about real NQ.

* **Engine**: `FROZEN_MANIFEST.json` records `engine_version v1.2.1`, the engine code hash and the frozen specs incl. `frozen/v1/SELECTION_PROCESS.yaml` (checked equal to the final code when built).
* **Partitions** (frozen in the manifest; `new_experiment.py --development-end 2019-01-01 --selection-holdout-years 1`): DEVELOPMENT < 2019-01-01 · SELECTION_HOLDOUT 2019-01-01 … 2020-01-01 (1 calendar year; selection data, not confirmation) · FINAL_LOCKBOX from 2020-01-01. The IS run read **only** development rows.
* **Campaign state** (`registry/campaigns.csv`): `C001` is `OPEN`; no freeze hash; `registry/selection_holdout_access.csv` (one row per *campaign*) and `registry/final_configs.csv` are header-only; the IS report says `SELECTION HOLDOUT status = NOT ACCESSED`; the lockbox was never read.
* **Lifecycle**: `EXP_0001` stopped at `NEAR_TIE_REVIEW_REQUIRED` (`IS_SHORTLIST_ELIGIBLE` after strong-mode verification) because the IS report found one near-tie cluster
  (`NEAR_TIE_CLUSTER_01`: `DIR_RETURN_30|UPPER_HALF` and `DIR_PATH_SKEW_60|UPPER_HALF`; the engine proposes at most these two for a holdout). The IS-rank-1/2 configs (`DIR_RETURN_15` on each side) are on opposite sides and in no cluster.
  No human approval, no campaign freeze, no holdout opening, no final-config selection and no CPCV were performed — those are human decisions (`approvals/` is empty). Limits: ≤ 2 configs per experiment, ≤ 6 per campaign (= ≤ 18 holdout evaluations).
* **Selection**: 24 selection trials (`registry/selection_trials.csv`): 16 `IS_SHORTLIST_ELIGIBLE`, 6 `REJECTED_INSUFFICIENT_UPLIFT` (`DIR_RETURN_60`), 2 `REJECTED_INSTABILITY`.
  **All 24 rows (every numeric column, every decision and rejection reason) are bit-identical to the engine v1.1.1 snapshot of the same data** (compared when this snapshot was built): the v1.2 patch changed lifecycle semantics, not the research.
* **Forward-path diagnostics (DIAGNOSTIC ONLY)**: `experiment/results/IS_REPORT.md` section **Z** (`sigma_ref = RV_60 / sqrt(60)`, 64-cell gross bracket surface, `GROSS — COSTS NOT APPLIED`, `DIAGNOSTIC ONLY — NO BRACKET WAS SELECTED`).
  The full `results/PATH_DIAGNOSTICS.json` (~6 MB) is **not included**; its sha256 `6a071b13…` (in `IS_REPORT.json`) differs from the v1.1.1 snapshot only because the frozen text of `non_promotable_rule` / `lifecycle` embedded in that file was reworded ("OOS" → "SELECTION HOLDOUT"); no formula changed.
* **IS report**: new section **NT. CONFIGURATION UNCERTAINTY / NEAR-TIES** (per cluster: config IDs, side, frequency, median standardized uplift, selected effect, campaign BH / Bonferroni, year and fold consistency, pairwise differences, paired weekly-block CI, reason) and the selection-holdout recommendation.
* **External verification**: `verify_experiment.py` at the pinned commit `624c8b7f…`, **strong** mode, RIDGE/SPLINE/XGB × **all 4 primary targets = 12 runs**. Every path: all research families `PASS`, label `RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE`
  (exit code 2: no roll provenance in synthetic data). Never `VERIFIED`. See `verify_experiment_*.log`. Local paths replaced by `WS` / `DATA` / `VERIFIER`.
* Large intermediates (CV panels, path-diagnostics file, staged verifier copy, data) are intentionally not included.

Reproduce (the manifest pins the engine hash, so it only reproduces against the same engine code):

```bash
python scripts/new_experiment.py --new-campaign C001 --development-end 2019-01-01 --selection-holdout-years 1 --workspace WS
#   event.py / EVENT_SPEC.yaml as in experiment/ ; then
python scripts/freeze_experiment.py --experiment EXP_0001 --workspace WS
python scripts/run_experiment.py    --experiment EXP_0001 --data NQ_planted.parquet --workspace WS
python scripts/verify_experiment.py --verifier-repo ../engine-verification- --experiment EXP_0001 --data NQ_planted.parquet --workspace WS
```
