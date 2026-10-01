#!/usr/bin/env python
"""Selection opportunities used by a campaign, lifecycle statuses, OOS ledger; runs the registry integrity check."""
import argparse
import json

from _common import workspace
from engine import trial_registry as reg
from engine.oos_stage import mark_contamination_if_mutated


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--campaign")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    for e in reg.read_experiments(ws)["experiment_id"]:
        mark_contamination_if_mutated(ws, e)
    print("registry integrity:", json.dumps(reg.integrity_check(ws)))
    camps = [a.campaign] if a.campaign else list(reg.read_campaigns(ws)["campaign_id"])
    for c in camps:
        s = reg.campaign_summary(ws, c)
        print(f"\ncampaign {c}  partitions {s['partitions']}")
        print(f"  experiments used                      : {s['experiments_used']} / {s['experiments_max']}")
        print(f"  CAMPAIGN REVEALED SELECTION TRIALS    : {s['selection_trials_revealed']} / {s['selection_trials_max']}"
              f"   (registered: {s['selection_trials_registered']})")
        print(f"  statistical selection opportunities exposed so far: {s['statistical_selection_opportunities_exposed']}")
        print(f"  campaign OOS status: {s['campaign_status']}  (spent: {s['campaign_oos_spent']})")
        print(f"  IS shortlist-eligible trials: {s['shortlist_eligible_trials']}; provisional: {s['provisional_trials']}; OOS unlocks: {s['oos_unlocks']}")
        for e in s["experiments"]:
            print(f"    {e['experiment_id']}  {e['status']:28s} is_status={e['is_status'] or '-':26s} lineage_of={e['lineage_parent'] or '-':9s} verification={e['research_verification']}")


if __name__ == "__main__":
    main()
