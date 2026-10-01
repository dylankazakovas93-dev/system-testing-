#!/usr/bin/env python
"""READ-ONLY helper for the HUMAN: print the exact hashes and allowed groups an OOS approval file must reference.
It does NOT create or modify any approval file (see AGENTS.md)."""
import argparse
import json

from _common import workspace
from engine.oos_stage import approval_hashes, approval_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--workspace")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    print(json.dumps(approval_hashes(ws, a.experiment), indent=2))
    print(f"\nThe HUMAN writes: {approval_path(ws, a.experiment)}  (template: templates/approval/OOS_APPROVAL.template.yaml)")


if __name__ == "__main__":
    main()
