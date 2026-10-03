#!/usr/bin/env python
"""HUMAN-run: validate approvals/<EXP>_FINAL_CONFIG_SELECTION.yaml (exactly ONE configuration), freeze it (FINAL_CONFIG_FROZEN), then run the
fixed CPCV AUTOMATICALLY (no further approval). Loads only DEVELOPMENT (+ SELECTION_HOLDOUT if it was used); the final lockbox is never read."""
import argparse

from _common import workspace
from engine.cpcv import freeze_and_run_cpcv


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--timestamp-col", default="timestamp")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    r = freeze_and_run_cpcv(workspace(a.workspace), a.experiment, a.data, a.timestamp_col)
    if r.get("declined"):
        print("Human declined to choose a final configuration: HUMAN_DECLINED (no CPCV, no lockbox).")
        return
    print(f"{r['final_config_id']}: CPCV {'CONFIRMED' if r['cpcv_passed'] else 'REJECTED (lineage ends, no fallback)'} — {r['label']}; PBO diagnostic: "
          f"{r['pbo_diagnostic']['pbo'] if r['pbo_diagnostic']['pbo'] is not None else 'NOT APPLICABLE'}")


if __name__ == "__main__":
    main()
