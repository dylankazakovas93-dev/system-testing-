#!/usr/bin/env python
"""Open the campaign's SHARED confirmation OOS exactly once. Refuses unless the campaign is frozen and the human campaign-open
approval (and every per-experiment approval) is valid. BH and Bonferroni run across ALL 3 x approved_group confirmations of the
whole campaign. Validation happens BEFORE any data is read; bars at/after oos_end (final lockbox) are never read."""
import argparse

from _common import workspace
from engine import trial_registry as reg
from engine.oos_stage import run_campaign_oos, validate_campaign_open
from engine.partitions import load_bars_before, parse_partitions


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--timestamp-col", default="timestamp")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    validate_campaign_open(ws, a.campaign)                 # fail BEFORE any data is read
    parts = parse_partitions(reg.campaign_partitions(ws, a.campaign))
    bars = load_bars_before(a.data, parts.oos_end, a.timestamp_col)
    r = run_campaign_oos(ws, a.campaign, bars)
    print(f"campaign {a.campaign} OOS is now SPENT (family of {r['family_size']} confirmations): {r['experiments']}")


if __name__ == "__main__":
    main()
