#!/usr/bin/env python
"""Log an exploratory observation. Allowed ONLY as --diagnostic-only: it is technically unable to alter any trial row,
decision or status of the current experiment. If the analysis can influence what configuration is selected, it is a
SELECTION OPPORTUNITY and requires a NEW pre-registered experiment instead."""
import argparse

from _common import workspace
from engine import trial_registry as reg


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--description", required=True)
    ap.add_argument("--diagnostic-only", action="store_true", help="required")
    ap.add_argument("--category", default="exploratory")
    ap.add_argument("--workspace")
    a = ap.parse_args()
    oid = reg.log_exploratory_observation(workspace(a.workspace), a.experiment, a.description,
                                          diagnostic_only=bool(a.diagnostic_only), category=a.category)
    print(f"logged {oid} (DIAGNOSTIC ONLY — NOT A SELECTION TRIAL)")


if __name__ == "__main__":
    main()
