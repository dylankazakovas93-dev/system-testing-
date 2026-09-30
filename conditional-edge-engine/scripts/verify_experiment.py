#!/usr/bin/env python
"""Run the EXTERNAL research verifier against a frozen experiment (the engine is untrusted).

  python scripts/verify_experiment.py --verifier-repo ../engine-verification- --experiment EXP_0001 --data /path/NQ.parquet

Exit code 2 from the verifier (INCOMPLETE/UNVERIFIED) is never reported as a pass. Missing continuous-contract
roll provenance keeps the GLOBAL verdict INCOMPLETE; that is reported separately from research-family status.
"""
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
    ap.add_argument("--timestamp-col", default="timestamp")
    ap.add_argument("--mode", choices=["fast", "standard", "strong"], default="strong")
    ap.add_argument("--model", choices=["RIDGE", "SPLINE", "XGB"], default="RIDGE",
                    help="which frozen model's fit_predict path the verifier exercises (default RIDGE)")
    ap.add_argument("--targets", nargs="*", help="subset of the 4 primary targets (default: all four)")
    ap.add_argument("--skip-verifier-tests", action="store_true", help="pass --skip-tests to the verifier (repository_health stays UNVERIFIED)")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    s = run_verification(workspace(a.workspace), a.experiment, a.verifier_repo, a.data, mode=a.mode, model=a.model,
                         timestamp_col=a.timestamp_col, targets=a.targets, skip_verifier_tests=a.skip_verifier_tests)
    print("\n=== SUMMARY ===")
    for r in s["results"]:
        print(f"{r['target']:18s} label={r['label']:45s} global={r['global_verdict']} exit={r['exit_code']} "
              f"research_families={json.dumps(r['research_families'])}")
        if r["other_families"]:
            print(f"{'':18s} other families: {json.dumps(r['other_families'])}")
    print(f"OVERALL: {s['overall']}")
    sys.exit(0 if s["overall"] == "VERIFIED" else 2 if s["overall"].startswith(("RESEARCH", "INCOMPLETE")) else 1)


if __name__ == "__main__":
    main()
