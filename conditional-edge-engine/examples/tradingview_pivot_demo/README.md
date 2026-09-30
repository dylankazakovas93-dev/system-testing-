# TradingView-template end-to-end example (snapshot)

Produced by the exact CLI sequence below on **synthetic random-walk** 1-minute bars
(`engine.synthetic.make_bars(1100, seed=7)`, 2016-01-04 .. 2020-03-20, campaign lockbox 2020-01-01).
The bars contain no planted edge, so the correct outcome is "no candidate" — this example demonstrates the machinery
(freeze -> 24 pre-registered trials -> OOS run -> report -> external verification), not a trading result.

```bash
python scripts/new_experiment.py --new-campaign C001 --lockbox-start 2020-01-01 --workspace WS
#   edit EVENT_SPEC.yaml hypothesis only (template event.py / reference.pine used as-is)
python scripts/freeze_experiment.py --experiment EXP_0001 --workspace WS
python scripts/run_experiment.py    --experiment EXP_0001 --data NQ_synth.parquet --workspace WS
python scripts/verify_experiment.py --verifier-repo ../engine-verification- --experiment EXP_0001 --data NQ_synth.parquet --workspace WS --mode strong
python scripts/make_report.py       --experiment EXP_0001 --workspace WS
```

* `experiment/` — the four editable files, `FROZEN_MANIFEST.json`, `results/REPORT.md`, `results/results.json`, `verification/verification_summary.json`.
* `registry/` — the registry CSVs after the run (24 selection trials, observations, one experiment, one campaign).
* `logs/` — console output of each step, including the verifier's per-family statuses.

Snapshot caveat: `FROZEN_MANIFEST.json` hashes the engine code of the commit that produced it; editing `engine/` or
`frozen/` later makes that manifest (correctly) fail verification. The synthetic data file itself is not stored
(regenerate it with the call above).
