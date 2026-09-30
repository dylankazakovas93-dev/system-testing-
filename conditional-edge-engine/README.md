# conditional-edge-engine

A **frozen research factory**: take one precisely specified causal market event (optionally translated from a
TradingView/Pine indicator) and test whether the market state at that event holds robust conditional information about
the next 15–60 minutes — while making it impossible to fish for a result.

```
EVENT -> FROZEN MARKET STATE (56 features) -> FROZEN FUTURE-PATH TARGETS (4) -> STRICT OOS MODELS (3)
      -> 24 CONTROLLED SELECTION TRIALS -> ROBUSTNESS (<=4 probes) -> AUDITABLE REPORT
```

This is the **research engine** (untrusted). It is separate from the frozen verification repo
`engine-verification-`, which is never copied or modified here; `scripts/verify_experiment.py` calls it.
Read `RESEARCH_RULES.md` first — it lists every frozen rule, my interpretation choices, and the spec issues I found.

## Install / test

```bash
python -m pip install numpy pandas scikit-learn xgboost pyyaml pyarrow scipy pytest pytest-xdist
python -m pytest            # add `-n 4 --dist loadscope` to parallelise the slow synthetic scenarios
```

## Workflow (one experiment)

```bash
python scripts/new_experiment.py --new-campaign C001 --lockbox-start 2025-01-01      # opens a campaign (once)
python scripts/new_experiment.py --campaign C001                                      # -> experiments/EXP_0001 from the template
#   edit ONLY HYPOTHESIS.md, EVENT_SPEC.yaml, event.py, reference.pine
python scripts/freeze_experiment.py --experiment EXP_0001                             # hash + lock + pre-register 24 trials
python scripts/run_experiment.py    --experiment EXP_0001 --data /path/NQ_1m.parquet  # no lockbox option exists
python scripts/verify_experiment.py --verifier-repo ../engine-verification- --experiment EXP_0001 --data /path/NQ_1m.parquet
python scripts/campaign_status.py                                                     # opportunities used / integrity
```

`--data` = CSV/Parquet with `timestamp, open, high, low, close, volume` (1-minute, **open-stamped**).
Outputs land in `experiments/EXP_xxxx/results/` (`REPORT.md`, `results.json`, per-panel OOS CSVs) and the `registry/`.

If `event.py` or the spec must change after results were revealed: `new_experiment.py --campaign C001 --lineage-of EXP_0001`.

## Layout

| Path | Purpose |
|---|---|
| `frozen/v1/*.yaml`, `instruments/NQ_1m.yaml` | the frozen specification (hashed at freeze) |
| `features/*.py` | the 56 feature formulas (one module per family) |
| `engine/` | feature/target/model engines, walk-forward + nested calibration, statistics, BH, acceptance, registry, runner, sensitivity, report, verifier bridge |
| `experiments/EXP_xxxx/` | per-experiment: the four editable files, `FROZEN_MANIFEST.json`, `results/`, `verification/` |
| `registry/` | `campaigns.csv`, `experiments.csv`, `selection_trials.csv` (24/experiment), `observations.csv` |
| `templates/experiment/` | HYPOTHESIS, EVENT_SPEC, `event.py` (confirmed-pivot example), `reference.pine` |
| `scripts/` | CLI (`new_experiment`, `freeze_experiment`, `run_experiment`, `verify_experiment`, `campaign_status`; `confirm_lockbox` is an intentional stub) |
| `tests/` | deterministic unit, synthetic-scenario, end-to-end and verifier-integration tests |

## Reading a result

Every report lists all 24 trials with parent/selected frequency, retention, parent/selected effect, uplift, standardized
uplift, block-bootstrap CI, raw p, `experiment_q`, `campaign_q`, year-by-year effects and the decision. Rejected and
low-frequency results are never hidden. Score-decile plots are labelled *not selection trials*; they and all other
diagnostics go to `observations.csv` and can only inspire a **new** experiment.
