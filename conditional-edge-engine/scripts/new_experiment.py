#!/usr/bin/env python
"""Create a new experiment from the template. Consumes one slot of the campaign (max 20).

A NEW campaign needs explicit partition dates (DEVELOPMENT / SELECTION HOLDOUT / FINAL LOCKBOX); nothing infers or moves them.
A mixed-direction indicator must become two experiments (LONG and SHORT): run this script twice."""
import argparse

from _common import workspace
from engine.experiment_lifecycle import create_experiment


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--campaign", help="existing campaign id (e.g. C001)")
    g.add_argument("--new-campaign", help="explicitly open a NEW campaign (one development / SELECTION HOLDOUT / lockbox generation)")
    ap.add_argument("--development-end", help="YYYY-MM-DD: development rows are bars opening BEFORE this date")
    ap.add_argument("--selection-holdout-years", type=int, choices=[1, 2],
                    help="1 or 2: the selection holdout = [development_end, development_end + N calendar years); the final lockbox starts right after it. "
                         "Chosen BEFORE any IS result; there is no duration search")
    ap.add_argument("--lineage-of", default="", help="parent experiment when event.py/spec changed after reveal")
    ap.add_argument("--workspace", help="directory holding registry/, experiments/, approvals/ (default: repo root)")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    parts = None
    if a.new_campaign:
        if not (a.development_end and a.selection_holdout_years):
            ap.error("--new-campaign requires --development-end and --selection-holdout-years (1 or 2)")
        import pandas as pd
        end = f"{pd.Timestamp(a.development_end) + pd.DateOffset(years=a.selection_holdout_years):%Y-%m-%d}"
        parts = {"development_end": a.development_end, "selection_holdout_end": end, "lockbox_start": end}
    exp = create_experiment(ws, a.campaign, new_campaign=a.new_campaign, partitions=parts, lineage_parent=a.lineage_of)
    print(f"created {exp} in {ws.experiments / exp}")
    print("edit ONLY: HYPOTHESIS.md, EVENT_SPEC.yaml, event.py, reference.pine; then run scripts/freeze_experiment.py")


if __name__ == "__main__":
    main()
