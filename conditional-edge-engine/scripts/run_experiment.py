#!/usr/bin/env python
"""Run the IS (development) stage of a frozen experiment, then STOP.

Only DEVELOPMENT rows are ever loaded (bars at/after development_end are discarded as the file is read). There is no OOS or
lockbox option here: confirmation OOS needs a manual human approval file and scripts/run_oos.py."""
import argparse

from _common import workspace
from engine import trial_registry as reg
from engine.event_contract import load_spec
from engine.experiment_lifecycle import experiment_dir
from engine.experiment_runner import run_experiment
from engine.partitions import load_bars_before, parse_partitions


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--data", required=True, help="CSV/Parquet 1-minute OHLCV, open-stamped")
    ap.add_argument("--timestamp-col", default="timestamp")
    ap.add_argument("--workspace")
    ap.add_argument("--skip-sensitivity", action="store_true", help="skip the event-parameter sensitivity veto stage")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    spec = load_spec(experiment_dir(ws, a.experiment) / "EVENT_SPEC.yaml")
    parts = parse_partitions(spec["partitions"])
    bars = load_bars_before(a.data, parts.development_end, a.timestamp_col)      # OOS / lockbox rows are never read into memory
    out = run_experiment(ws, a.experiment, bars, data_label=a.data, run_sensitivity_stage=not a.skip_sensitivity)
    t = out["trials"]
    print(t[["trial_id", "target", "model", "state", "selected_frequency", "standardized_uplift", "selected_effect", "raw_p",
             "experiment_bonferroni_p", "campaign_bonferroni_p", "decision"]].to_string(index=False))
    s = reg.campaign_summary(ws, reg.experiment_row(ws, a.experiment)["campaign_id"])
    print(f"\nEXPERIMENT SELECTION TRIALS: 24 / 24    CAMPAIGN REVEALED SELECTION TRIALS: {s['selection_trials_revealed']} / {s['selection_trials_max']}")
    print(f"IS report: {out['report_path']}\nstatus: {reg.experiment_row(ws, a.experiment)['status']}  (OOS NOT ACCESSED; stopped for human review)")


if __name__ == "__main__":
    main()
