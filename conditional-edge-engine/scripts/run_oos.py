#!/usr/bin/env python
"""One-shot CONFIRMATION OOS. Refuses unless a valid HUMAN approval file exists for the exact frozen manifest and IS report.

This script never creates the approval. Bars at/after oos_end (final lockbox) are never read."""
import argparse

from _common import workspace
from engine.event_contract import load_spec
from engine.experiment_lifecycle import experiment_dir
from engine.oos_stage import run_oos, validate_approval
from engine.partitions import load_bars_before, parse_partitions


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--timestamp-col", default="timestamp")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    validate_approval(ws, a.experiment)                     # fail BEFORE any data is read if the human has not approved
    parts = parse_partitions(load_spec(experiment_dir(ws, a.experiment) / "EVENT_SPEC.yaml")["partitions"])
    bars = load_bars_before(a.data, parts.oos_end, a.timestamp_col)
    r = run_oos(ws, a.experiment, bars)
    print(f"status: {r['status']}; see experiments/{a.experiment}/results/OOS_REPORT.md. OOS is now SPENT.")


if __name__ == "__main__":
    main()
