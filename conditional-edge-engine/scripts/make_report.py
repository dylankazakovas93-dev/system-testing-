#!/usr/bin/env python
"""Rebuild REPORT.md of a REVEALED experiment from its stored results.json and the registry (e.g. after verification).
Reads results only; it never recomputes or re-reveals anything."""
import argparse
import json

from _common import workspace
from engine import trial_registry as reg
from engine.common import load_frozen
from engine.experiment_lifecycle import experiment_dir
from engine.report import build_report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--workspace")
    a = ap.parse_args()
    ws = workspace(a.workspace)
    d = experiment_dir(ws, a.experiment) / "results"
    bundle = json.loads((d / "results.json").read_text())
    text = build_report(ws, a.experiment, bundle, reg.experiment_trials(ws, a.experiment), reg.read_observations(ws), load_frozen())
    (d / "REPORT.md").write_text(text)
    print(f"rebuilt {d / 'REPORT.md'}")


if __name__ == "__main__":
    main()
