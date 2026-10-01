# SYNTHETIC DATA — NOT REAL NQ

Canonical snapshot of one IS run through the real CLIs with **engine v1.0.0** on **synthetic** 1-minute bars with a planted AR(1) momentum
(`make_bars(1100, seed=7, phi=0.8)`, 2016-01-04 … 2020-03). It shows that the pipeline runs end to end. It says nothing about real NQ.

* **Engine**: `FROZEN_MANIFEST.json` records `engine_version v1.0.0` and the engine code hash of the final v1 code (checked equal when the example was built).
* **Partitions** (frozen in the manifest): development < 2019-01-01 · confirmation OOS 2019-01-01 … 2019-07-01 · final lockbox from 2019-10-01.
  The IS run read **only** development rows.
* **Campaign-level OOS state** (`registry/campaigns.csv`): campaign `C001` is `OPEN`; `oos_freeze_hash` and `oos_spent_at` are empty;
  `registry/oos_access.csv` (one row per *campaign*) is header-only; the IS report says `OOS status = NOT ACCESSED`.
* **Lifecycle**: `EXP_0001` stopped at `AWAITING_HUMAN_OOS_APPROVAL` (IS_SHORTLIST_ELIGIBLE after strong-mode verification). Nothing beyond that was done:
  no human approval, no campaign freeze (`freeze_campaign_oos.py`), no campaign OOS opening. Those need human-written files in `approvals/`.
  A campaign may freeze at most 6 approved groups (2 per experiment) = at most 18 OOS confirmations.
* **Result**: 24 selection trials (`registry/selection_trials.csv`), 16 `IS_SHORTLIST_ELIGIBLE`; `DIR_RETURN_60` is `REJECTED_INSUFFICIENT_UPLIFT`;
  two trials are `REJECTED_INSTABILITY` (2 of 3 eligible years positive, 66.7% < 70%).
* **External verification**: `verify_experiment.py` at the pinned commit `624c8b7f…`, **strong** mode, RIDGE/SPLINE/XGB × 3 candidate targets = 9 runs.
  Every path: all research families `PASS`, label `RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE` (exit code 2: no roll provenance in synthetic data). Never `VERIFIED`.
  See `verify_experiment_*.log`. Local paths in the logs were replaced by `WS` / `DATA`.
* Large intermediates (CV panels, staged verifier copy, data) are intentionally not included.

Reproduce (the manifest pins the engine hash, so it only reproduces against the same engine code):

```bash
python scripts/new_experiment.py --new-campaign C001 --development-end 2019-01-01 --oos-end 2019-07-01 --lockbox-start 2019-10-01 --workspace WS
#   event.py / EVENT_SPEC.yaml as in experiment/ ; then
python scripts/freeze_experiment.py --experiment EXP_0001 --workspace WS
python scripts/run_experiment.py    --experiment EXP_0001 --data NQ_planted.parquet --workspace WS
python scripts/verify_experiment.py --verifier-repo ../engine-verification- --experiment EXP_0001 --data NQ_planted.parquet --workspace WS
```
