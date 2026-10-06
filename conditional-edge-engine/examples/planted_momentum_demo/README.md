# SYNTHETIC DATA — NOT REAL NQ

Canonical snapshot of one IS run through the real CLIs with **engine v2.2.0** on **synthetic** 1-minute bars with a planted AR(1) momentum
(`make_bars(1100, seed=7, phi=0.8)`, 2016-01-04 … 2020-03). It shows that the pipeline runs end to end. It says nothing about real NQ.

* **Engine**: `FROZEN_MANIFEST.json` records `engine_version v2.2.0` and the engine code hash (checked equal to the committed code when built).
* **Partitions** (`--development-end 2019-01-01 --selection-holdout-years 1`): DEVELOPMENT < 2019-01-01 · SELECTION_HOLDOUT 2019-01-01 … 2020-01-01 · FINAL_LOCKBOX from 2020-01-01. The IS run read **only** development rows.
* **State**: `C001` is `OPEN`; the holdout access ledger and `final_configs.csv` are header-only; no approvals exist; the lockbox was never read.
* **Targets (v2)**: 15-, 60-, 180-minute directional returns (windows truncated at the 16:00 close and flagged, never dropped) and the 60-bar path skew. Uplift floor 0.01; the fold gate is replaced by a batch/year concentration gate (the eligible trials have their best batch of 10 carrying 12–17% of the uplift, gate 35%).
  Significance (v2.2.0): raw permutation p ≤ 0.00135 (t ≥ 3) plus BH q ≤ 0.05, with 20000 permutations. The eligible trials sit at the permutation floor (raw p = 0.00005); the Bonferroni columns are reported but gate nothing.
* **Selection**: 24 trials. `DIR_RETURN_15`: 6 `IS_SHORTLIST_ELIGIBLE`; `DIR_PATH_SKEW_60`: 5 eligible + 1 `REJECTED_INSTABILITY`; `DIR_RETURN_60`: all rejected (5 on year consistency, only 2 of 3 development years positive; 1 on model agreement);
  `DIR_RETURN_180`: all rejected — raw p 0.0015 / 0.017 / 0.023 for XGB / Ridge / spline, all above the 0.00135 hurdle, plus year instability and (for Ridge and spline) a CI that includes 0. The planted AR(1) memory has decayed by 3 hours. No near-tie cluster was found (the eligible groups' uplifts differ by more than 0.03), so the experiment stops at `AWAITING_HUMAN_FINAL_CONFIG_SELECTION`: the human may pick one config directly.
* **IS report**: sections NT (configuration uncertainty) and WM (where it works / where it does not, by year, hour and full vs truncated horizon, descriptive only) are included.
* **External verification**: `verify_experiment.py` at the pinned commit `624c8b7f…`, **strong** mode, all 4 primary targets × 3 models = **12 paths, every research family PASS**, label `RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE` (exit 2: no roll provenance in synthetic data). Never `VERIFIED`.
  The truncated 180-minute targets verify cleanly. Local paths replaced by `WS` / `DATA` / `VERIFIER`.
* Large intermediates (CV panels, path-diagnostics file, staged verifier copy, data) are not included.

Reproduce (the manifest pins the engine hash, so it only reproduces against the same engine code):

```bash
python scripts/new_experiment.py --new-campaign C001 --development-end 2019-01-01 --selection-holdout-years 1 --workspace WS
#   event.py / EVENT_SPEC.yaml as in experiment/ ; then
python scripts/freeze_experiment.py --experiment EXP_0001 --workspace WS
python scripts/run_experiment.py    --experiment EXP_0001 --data NQ_planted.parquet --workspace WS
python scripts/verify_experiment.py --verifier-repo ../engine-verification- --experiment EXP_0001 --data NQ_planted.parquet --workspace WS
```
