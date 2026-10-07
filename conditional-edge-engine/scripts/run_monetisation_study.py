#!/usr/bin/env python
"""Monetisation (bracket) study for the ONE final configuration of an experiment that passed CPCV (frozen/v1/MONETISATION_SPEC.yaml).
DEVELOPMENT rows only: the selection holdout and the final lockbox are never loaded. Not a selection trial; changes no status or registry row.
Picks an ATR bracket whose whole +-25% neighbourhood is net-positive after costs, or reports NO_STABLE_BRACKET."""
import argparse

from _common import workspace
from engine.monetisation import run_for_experiment


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--timestamp-col", default="timestamp")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    r = run_for_experiment(workspace(a.workspace), a.experiment, a.data, a.timestamp_col)
    c = r["chosen"]
    print(f"{r['label']}\n{r['experiment_id']} {r['final_config_id']}: {r['decision']} ({r['n_stable']} of {r['n_cells']} cells stable)")
    if c:
        print(f"ATR {c['atr_base']}, stop {c['stop_atr']}x, target {c['target_atr']}x, limit {c['expiry']} bars: {c['n_trades']} trades, "
              f"net {c['net_expectancy']:+.3f} pts/trade, worst neighbour {c['min_neighbour_expectancy']:+.3f}")
    print(f"results/MONETISATION_STUDY.md written under the experiment folder (development data only, not confirmation)")


if __name__ == "__main__":
    main()
