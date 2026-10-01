#!/usr/bin/env python
"""HUMAN-run: CLOSE a campaign and freeze every human-approved experiment/target-side group together.

Refuses unless every experiment of the campaign has completed its IS stage. After this the campaign accepts no new experiment,
verification or IS report. Opening the OOS is a separate step (run_campaign_oos.py) that needs a second human file
approvals/CAMPAIGN_<id>_OOS_OPEN_APPROVAL.yaml citing the freeze hash printed here. An agent must not run this unless asked."""
import argparse
import json

from _common import workspace
from engine.oos_stage import campaign_approval_path, freeze_campaign_oos


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--workspace")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    r = freeze_campaign_oos(ws, a.campaign)
    print(json.dumps({k: r[k] for k in ("campaign_id", "experiments", "experiments_not_included", "n_approved_groups", "n_oos_confirmations", "freeze_sha256", "path")}, indent=2))
    print(f"\nCampaign {a.campaign} is now OOS_FROZEN. The HUMAN writes {campaign_approval_path(ws, a.campaign)}")
    print("(template: templates/approval/CAMPAIGN_OOS_OPEN_APPROVAL.template.yaml) citing oos_freeze_sha256 above.")


if __name__ == "__main__":
    main()
