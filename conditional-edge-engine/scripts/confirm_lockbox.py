#!/usr/bin/env python
"""Lockbox confirmation is a SEPARATE, explicit, single-use step that is intentionally NOT implemented in v1.

It must only ever be opened after a campaign has produced frozen, confirmation-eligible candidates, and never
repeatedly. run_experiment.py cannot reach lockbox data. Implementing this command is a deliberate future decision.
"""
import sys

if __name__ == "__main__":
    sys.exit("confirm_lockbox.py: not implemented in v1 (no automatic or repeated lockbox checking).")
