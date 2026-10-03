#!/usr/bin/env python
"""Resume the AUTOMATIC post-selection CPCV of a FINAL_CONFIG_FROZEN experiment (normally `finalize_final_config.py` runs it). Veto only; the
final lockbox is never loaded and CPCV never needs a human approval."""
import argparse

from _common import workspace
from engine.cpcv import cpcv_cutoff, run_cpcv
from engine.partitions import load_bars_before


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--timestamp-col", default="timestamp")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    cutoff, _ = cpcv_cutoff(ws, a.experiment)
    r = run_cpcv(ws, a.experiment, load_bars_before(a.data, cutoff, a.timestamp_col))
    print(f"{r['final_config_id']}: CPCV {'CONFIRMED' if r['cpcv_passed'] else 'REJECTED (lineage ends, no fallback)'} — {r['label']}")


if __name__ == "__main__":
    main()
