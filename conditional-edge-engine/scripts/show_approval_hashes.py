#!/usr/bin/env python
"""READ-ONLY helper for the HUMAN: print the exact hashes and allowed groups an SELECTION HOLDOUT approval file must reference.
It does NOT create or modify any approval file (see AGENTS.md)."""
import argparse
import json

from _common import workspace
from engine.selection_holdout_stage import approval_hashes, approval_path, campaign_approval_path, campaign_open_hashes, final_selection_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--experiment")
    g.add_argument("--campaign", help="print what the campaign-open approval must cite")
    ap.add_argument("--final", action="store_true", help="with --experiment: also print what the FINAL_CONFIG_SELECTION file must cite")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    if a.campaign:
        print(json.dumps(campaign_open_hashes(ws, a.campaign), indent=2))
        print(f"\nThe HUMAN writes: {campaign_approval_path(ws, a.campaign)}  (template: templates/approval/CAMPAIGN_SELECTION_HOLDOUT_OPEN_APPROVAL.template.yaml)")
        return
    h = approval_hashes(ws, a.experiment)
    if a.final:
        print(json.dumps(h, indent=2))
        print(f"\nThe HUMAN writes: {final_selection_path(ws, a.experiment)}  (template: templates/approval/FINAL_CONFIG_SELECTION.template.yaml)")
        return
    print(json.dumps(h, indent=2))
    print(f"\nThe HUMAN writes: {approval_path(ws, a.experiment)}  (template: templates/approval/SELECTION_HOLDOUT_APPROVAL.template.yaml)")


if __name__ == "__main__":
    main()
