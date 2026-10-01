#!/usr/bin/env python
"""Final CPCV robustness (veto only) for an OOS_CONFIRMED experiment. The final lockbox stays sealed."""
import argparse

from _common import workspace
from engine.cpcv import run_cpcv
from engine.event_contract import load_spec
from engine.experiment_lifecycle import experiment_dir
from engine.partitions import load_bars_before, parse_partitions


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--timestamp-col", default="timestamp")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    parts = parse_partitions(load_spec(experiment_dir(ws, a.experiment) / "EVENT_SPEC.yaml")["partitions"])
    bars = load_bars_before(a.data, parts.oos_end, a.timestamp_col)
    r = run_cpcv(ws, a.experiment, bars)
    print(f"CPCV confirmed groups: {r['cpcv_confirmed_groups'] or 'none'}; PBO diagnostic: {r['pbo_diagnostic']['pbo'] if r['pbo_diagnostic']['pbo'] is not None else 'NOT APPLICABLE'}")


if __name__ == "__main__":
    main()
