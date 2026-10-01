# Planted-momentum demo (SYNTHETIC data, IS stage only)

A snapshot of one full IS run through the real CLIs on **synthetic** 1-minute bars with a planted AR(1) momentum (`make_bars(1100, seed=7, phi=0.8)`,
2016-01-04 … 2020-03). It is evidence that the pipeline runs end to end; it says nothing about real NQ data.

* Partitions (frozen in the manifest): development < 2019-01-01 · confirmation OOS 2019-01-01 … 2019-07-01 · final lockbox from 2019-10-01.
  The IS run read **only** development rows. `registry/oos_access.csv` is empty and the IS report states `OOS status = NOT ACCESSED`.
* Event: every 45th bar, single direction (+1) — `experiment/event.py`, `experiment/EVENT_SPEC.yaml`.
* Result: 24 selection trials (`registry/selection_trials.csv`), 16 `IS_SHORTLIST_ELIGIBLE` after strong-mode verification; `DIR_RETURN_60` is
  `REJECTED_INSUFFICIENT_UPLIFT`; two trials are `REJECTED_INSTABILITY` (only 2 of 3 eligible years positive, 66.7% < 70%).
* External verification: `verify_experiment.py` at the pinned commit `624c8b7f…` (`frozen/v1/VERIFIER_PIN.yaml`), **strong** mode, all 3 model paths
  (RIDGE, SPLINE, XGB) × the 3 candidate targets = 9 runs. Every path: all research families `PASS`, label `RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE`
  (exit code 2, because the synthetic data has no continuous-contract roll provenance). **Never `VERIFIED`.** See `verify_experiment_*.log`.
* The approval step (`approvals/EXP_0001_OOS_APPROVAL.yaml`) was **not** performed: that file is written by a human only.

Reproduce (a snapshot is not re-runnable against later engine edits: the manifest pins the engine code hash of that moment):

```bash
python scripts/new_experiment.py --new-campaign C001 --development-end 2019-01-01 --oos-end 2019-07-01 --lockbox-start 2019-10-01 --workspace WS
#   event.py / EVENT_SPEC.yaml as in experiment/ ; then
python scripts/freeze_experiment.py --experiment EXP_0001 --workspace WS
python scripts/run_experiment.py    --experiment EXP_0001 --data NQ_planted.parquet --workspace WS
python scripts/verify_experiment.py --verifier-repo ../engine-verification- --experiment EXP_0001 --data NQ_planted.parquet --workspace WS
```
