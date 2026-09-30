#!/usr/bin/env python
"""Create a new experiment from the template. Consumes one slot of the campaign (max 20)."""
import argparse

from _common import workspace
from engine.experiment_lifecycle import create_experiment


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--campaign", help="existing campaign id (e.g. C001)")
    g.add_argument("--new-campaign", help="explicitly open a NEW campaign (one development/lockbox generation)")
    ap.add_argument("--lockbox-start", help="YYYY-MM-DD; required with --new-campaign")
    ap.add_argument("--lineage-of", default="", help="parent experiment when event.py/spec changed after reveal")
    ap.add_argument("--workspace", help="directory holding registry/ and experiments/ (default: repo root)")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    exp = create_experiment(ws, a.campaign, new_campaign=a.new_campaign, lockbox_start=a.lockbox_start,
                            lineage_parent=a.lineage_of)
    print(f"created {exp} in {ws.experiments / exp}")
    print("edit ONLY: HYPOTHESIS.md, EVENT_SPEC.yaml, event.py, reference.pine; then run scripts/freeze_experiment.py")


if __name__ == "__main__":
    main()
