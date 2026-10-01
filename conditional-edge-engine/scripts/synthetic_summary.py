#!/usr/bin/env python
"""Reproduce the synthetic-scenario results (known structure, real IS pipeline) and print/write a summary.

Scenarios are fully determined by their arguments and seeds and mirror tests/test_synthetic_scenarios.py; none of the frozen
rules is adjusted per scenario. Each scenario is run through freeze -> DEVELOPMENT_CV (5 purged folds) -> 24 trials -> statistics
-> acceptance -> registry -> IS report on DEVELOPMENT-only tables. Two views are reported:
  * 'before injection': what the IS stage alone concludes (no strong-mode verification, no sensitivity verdict yet);
  * 'after injection' : the same trials once the verification of all 12 model paths and the sensitivity verdict are recorded
                        (TEST-ONLY injection through the registry; the real verifier and the bar-level probes are separate stages).
"""
import argparse
import json
import tempfile
from multiprocessing import Pool

from _common import ROOT  # noqa: F401

from engine import trial_registry as reg
from engine.synthetic import make_event_tables
from tests.scenario_helpers import pass_all_paths, pass_sensitivity, run_is_tables

SCENARIOS = {
    "1_no_signal": dict(signal="none"),
    "2_linear_edge": dict(signal="linear", slope=0.35),
    "3_nonlinear_edge": dict(signal="nonlinear", slope=0.35),
    "4a_low_frequency_strong_edge": dict(signal="linear", slope=0.6, events_per_week=1.6, years=range(2011, 2023)),
    "4b_spurious_tail": dict(signal="tail", tail_threshold=1.9, tail_shift=1.5),
    "5_frequency_destroying_weak_filter": dict(signal="linear", slope=0.006, drift=0.041, events_per_week=4.3),
    "6_unstable_regime": dict(signal="linear", slope=0.0, slope_by_year={2015: 1.0, 2016: 1.0, 2017: 1.0, 2018: 1.0,
                                                                          2019: -0.25, 2020: -0.25, 2021: -0.25, 2022: -0.25}),
    "7_conditional_improvement_only": dict(signal="linear", slope=0.35, drift=-0.45),
}


def run(item):
    name, kw = item
    ws = reg.Workspace(tempfile.mkdtemp()).init()
    tables = make_event_tables(**kw)
    events, calendar = tables[0], tables[4]
    exp, trials, _ = run_is_tables(ws, tables)
    before = trials["decision"].value_counts().to_dict()
    status_before = reg.experiment_row(ws, exp)["status"]
    pass_all_paths(ws, exp)
    pass_sensitivity(ws, exp)
    t = reg.experiment_trials(ws, exp)
    weeks = len(set(calendar.strftime("%G-%V")))
    row = reg.experiment_row(ws, exp)
    return name, {
        "events": int(len(events)), "base_freq_per_week": round(len(events) / weeks, 2),
        "decisions_before_injection": before, "status_before_injection": status_before,
        "decisions_after_injection": t["decision"].value_counts().to_dict(), "status_after_injection": row["status"],
        "max_std_uplift": round(float(t["standardized_uplift"].max()), 3),
        "min_experiment_q": round(float(t["experiment_q"].min()), 4),
        "min_campaign_bonferroni_p": round(float(t["campaign_bonferroni_p"].min()), 4),
        "min_selected_freq": round(float(t["selected_frequency"].min()), 2),
        "eligible_by_model": t[t["decision"] == "IS_SHORTLIST_ELIGIBLE"].groupby("model").size().to_dict(),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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
