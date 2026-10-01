#!/usr/bin/env python
"""Rebuild IS_REPORT.json/.md of an IS-complete experiment from stored results + registry (e.g. after verification or after
later campaign experiments changed the retroactive adjusted values). A new report has a new hash, which invalidates any
earlier approval. REFUSED once OOS has been unlocked (the IS report is sealed)."""
import argparse

from _common import workspace
from engine.is_report import write_is_report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--workspace")
    a = ap.parse_args()
    p = write_is_report(workspace(a.workspace), a.experiment)
    print(f"rebuilt {p['md']} and {p['json']}")


if __name__ == "__main__":
    main()
