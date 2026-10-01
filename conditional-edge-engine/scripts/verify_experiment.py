#!/usr/bin/env python
"""Run the EXTERNAL research verifier (pinned commit, strong mode) on every candidate model path: RIDGE, SPLINE and XGB.

  python scripts/verify_experiment.py --verifier-repo ../engine-verification- --experiment EXP_0001 --data /path/NQ.parquet

The verifier only ever receives rows of the stage's partition (IS: before development_end). Exit code 2 from the verifier
is never reported as a pass; missing roll provenance keeps the GLOBAL verdict INCOMPLETE and is reported separately from
research-family status. A model path with a research-family failure is rejected."""
import argparse
import json
import sys

from _common import workspace
from engine.verifier_bridge import run_verification


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verifier-repo", required=True)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--stage", choices=["IS", "OOS"], default="IS")
    ap.add_argument("--timestamp-col", default="timestamp")
    ap.add_argument("--mode", choices=["fast", "standard", "strong"], default="strong")
    ap.add_argument("--models", nargs="*", choices=["RIDGE", "SPLINE", "XGB"], help="default: all three")
    ap.add_argument("--targets", nargs="*", help="default: ALL 4 primary targets (every promotion-capable target); a subset leaves paths unverified")
    ap.add_argument("--skip-verifier-tests", action="store_true")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    s = run_verification(workspace(a.workspace), a.experiment, a.verifier_repo, a.data, stage_name=a.stage, mode=a.mode,
                         models=a.models, timestamp_col=a.timestamp_col, targets=a.targets,
                         skip_verifier_tests=a.skip_verifier_tests)
    print("\n=== SUMMARY ===")
    for r in s["results"]:
        print(f"{r['target']:18s} {r['model']:7s} label={r['label']:45s} global={r['global_verdict']} exit={r['exit_code']} "
              f"research_families={json.dumps(r['research_families'])}")
    print(f"OVERALL: {s['overall']}   (verifier commit {s['verifier_commit']}, mode {s['mode']})")
    sys.exit(0 if s["overall"] == "VERIFIED" else 2 if s["overall"].startswith(("RESEARCH", "INCOMPLETE")) else 1)


if __name__ == "__main__":
    main()
