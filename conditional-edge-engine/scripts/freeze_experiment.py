#!/usr/bin/env python
"""Validate, hash and lock an experiment; pre-register its 24 selection trials BEFORE any result exists."""
import argparse

from _common import workspace
from engine.experiment_lifecycle import freeze


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--workspace")
    a = ap.parse_args()
    m = freeze(workspace(a.workspace), a.experiment)
    print(f"frozen {a.experiment}: manifest_hash={m['manifest_hash']}")
    print(f"event_hash={m['event_hash']}")
    print(f"pre-registered {len(m['selection_trials'])} selection trials (no API exists to add a 25th)")


if __name__ == "__main__":
    main()
