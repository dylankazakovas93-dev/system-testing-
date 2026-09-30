#!/usr/bin/env python
"""Reproduce the synthetic-scenario results (known structure, real pipeline) and print/write a summary table.

Scenarios are fully determined by their arguments and seeds; none of the frozen rules is adjusted per scenario.
"""
import argparse
import json
import sys
import tempfile
from multiprocessing import Pool

from _common import ROOT  # noqa: F401
import pandas as pd

from engine import trial_registry as reg
from engine.common import load_frozen
from engine.experiment_lifecycle import create_experiment, experiment_dir, freeze
from engine.experiment_runner import assemble_trial_results, base_frequency_flag, period_strings, run_panels
from engine.synthetic import make_event_tables

SCENARIOS = {
    "1_no_signal": dict(signal="none"),
    "2_linear_edge": dict(signal="linear", slope=0.35),
    "3_nonlinear_edge": dict(signal="nonlinear", slope=0.35),
    "4a_low_frequency_strong_edge": dict(signal="linear", slope=0.6, events_per_week=1.6, years=range(2011, 2023)),
    "4b_spurious_tail": dict(signal="tail", tail_threshold=1.9, tail_shift=1.5),
    "5_frequency_destroying_weak_filter": dict(signal="linear", slope=0.006, drift=0.041, events_per_week=4.3),
    "6_unstable_regime": dict(signal="linear", slope=0.0, slope_by_year={2015: 1.0, 2016: 1.0, 2017: 1.0, 2018: 1.0,
                                                                          2019: -0.25, 2020: -0.25, 2021: -0.25, 2022: -0.25}),
}


def run(item):
    name, kw = item
    frozen = load_frozen()
    ws = reg.Workspace(tempfile.mkdtemp()).init()
    exp = create_experiment(ws, new_campaign="C001", lockbox_start="2030-01-01")
    p = experiment_dir(ws, exp) / "EVENT_SPEC.yaml"
    p.write_text(p.read_text().replace("TODO: one or two sentences.", "A confirmed pivot is followed by a path."))
    freeze(ws, exp)
    events, features, eligible, targets, calendar = make_event_tables(**kw)
    panels = run_panels(events, features, targets, eligible, calendar, frozen)
    train_p, oos_p = period_strings(panels, events)
    reg.reveal_experiment(ws, exp, assemble_trial_results(panels, exp, frozen), train_period=train_p, oos_period=oos_p, frozen=frozen)
    t = reg.experiment_trials(ws, exp)
    weeks = len(set(calendar.strftime("%G-%V")))
    return name, {
        "events": int(len(events)), "base_freq_per_week": round(len(events) / weeks, 2),
        "base_flag": base_frequency_flag(len(events), weeks, frozen),
        "decisions": t["decision"].value_counts().to_dict(),
        "max_std_uplift": round(float(t["standardized_uplift"].max()), 3),
        "min_experiment_q": round(float(t["experiment_q"].min()), 4),
        "min_selected_freq": round(float(t["selected_frequency"].min()), 2),
        "promoted_by_model": t[t["decision"].isin(["PROMOTABLE", "PROMOTABLE_PENDING_SENSITIVITY"])].groupby("model").size().to_dict(),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    with Pool(a.jobs) as pool:
        results = dict(pool.map(run, list(SCENARIOS.items())))
    print(json.dumps(results, indent=2, sort_keys=True))
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(results, fh, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
