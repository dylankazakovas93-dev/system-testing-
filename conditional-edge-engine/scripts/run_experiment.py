#!/usr/bin/env python
"""Run a frozen experiment on development data. There is NO option to evaluate or print lockbox performance:
bars at/after the campaign lockbox boundary are discarded before any computation."""
import argparse

from _common import workspace
from engine.common import load_bars
from engine.experiment_runner import run_experiment


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--data", required=True, help="CSV/Parquet 1-minute OHLCV, open-stamped")
    ap.add_argument("--timestamp-col", default="timestamp")
    ap.add_argument("--workspace")
    ap.add_argument("--skip-sensitivity", action="store_true",
                    help="leave a candidate in PROMOTABLE_PENDING_SENSITIVITY (robustness stage not run)")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    bars = load_bars(a.data, a.timestamp_col)
    out = run_experiment(ws, a.experiment, bars, data_label=a.data, run_sensitivity_stage=not a.skip_sensitivity)
    print(out["trials"][["trial_id", "target", "model", "state", "selected_frequency", "standardized_uplift",
                         "raw_p", "experiment_q", "campaign_q", "decision"]].to_string(index=False))
    print(f"report: {out['report_path']}")


if __name__ == "__main__":
    main()
