#!/usr/bin/env python
"""How many selection opportunities has this campaign used? Also runs the registry integrity check."""
import argparse
import json

from _common import workspace
from engine import trial_registry as reg


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--campaign")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    print("registry integrity:", json.dumps(reg.integrity_check(ws)))
    camps = [a.campaign] if a.campaign else list(reg.read_campaigns(ws)["campaign_id"])
    for c in camps:
        s = reg.campaign_summary(ws, c)
        print(f"\ncampaign {c} (lockbox starts {s['lockbox_start']})")
        print(f"  experiments used      : {s['experiments_used']} / {s['experiments_max']}")
        print(f"  selection trials      : {s['selection_trials_registered']} registered / {s['selection_trials_max']} max; "
              f"{s['selection_trials_revealed']} revealed")
        print(f"  promotable trials     : {s['promotable_trials']} (pending sensitivity: {s['pending_sensitivity']})")
        for e in s["experiments"]:
            print(f"    {e['experiment_id']}  {e['status']:9s} lineage_of={e['lineage_parent'] or '-':9s} verification={e['research_verification']}")


if __name__ == "__main__":
    main()
