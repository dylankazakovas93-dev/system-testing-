#!/usr/bin/env python
"""HUMAN-run: CLOSE a campaign and freeze every human-approved near-tied config of every experiment together (<= 2 per experiment, <= 6 per campaign).

Refuses unless every experiment of the campaign has completed its IS stage. After this the campaign accepts no new experiment,
verification or IS report. Opening the SELECTION HOLDOUT is a separate step (run_campaign_selection_holdout.py) that needs a second human file
approvals/CAMPAIGN_<id>_SELECTION_HOLDOUT_OPEN_APPROVAL.yaml citing the freeze hash printed here. An agent must not run this unless asked."""
import argparse
import json

from _common import workspace
from engine.selection_holdout_stage import campaign_approval_path, freeze_campaign_selection_holdout


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--workspace")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    r = freeze_campaign_selection_holdout(ws, a.campaign)
    print(json.dumps({k: r[k] for k in ("campaign_id", "experiments", "experiments_not_included", "n_approved_configs", "approved_config_ids", "n_holdout_evaluations", "freeze_sha256", "path")}, indent=2))
    print(f"\nCampaign {a.campaign} is now SELECTION_HOLDOUT_FROZEN. The HUMAN writes {campaign_approval_path(ws, a.campaign)}")
    print("(template: templates/approval/CAMPAIGN_SELECTION_HOLDOUT_OPEN_APPROVAL.template.yaml) citing selection_holdout_freeze_sha256 above.")


if __name__ == "__main__":
    main()
