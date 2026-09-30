"""Run a table-level synthetic scenario through the REAL pipeline: freeze -> panels -> 24 trials -> registry."""
from __future__ import annotations

from engine import trial_registry as reg
from engine.common import load_frozen
from engine.experiment_lifecycle import create_experiment, experiment_dir, freeze
from engine.experiment_runner import assemble_trial_results, period_strings, run_panels
from engine.synthetic import make_event_tables

FROZEN = load_frozen()


def new_frozen_experiment(ws, campaign="C001", lockbox="2030-01-01"):
    if campaign not in set(reg.read_campaigns(ws)["campaign_id"]):
        exp = create_experiment(ws, new_campaign=campaign, lockbox_start=lockbox)
    else:
        exp = create_experiment(ws, campaign_id=campaign)
    p = experiment_dir(ws, exp) / "EVENT_SPEC.yaml"
    p.write_text(p.read_text().replace("TODO: one or two sentences.", "A confirmed pivot is followed by a path."))
    freeze(ws, exp)
    return exp


def run_scenario(ws, tables, campaign="C001"):
    """tables = (events, features, eligible, targets, calendar). Returns (exp_id, trials_df, panels)."""
    exp = new_frozen_experiment(ws, campaign)
    events, features, eligible, targets, calendar = tables
    panels = run_panels(events, features, targets, eligible, calendar, FROZEN)
    results = assemble_trial_results(panels, exp, FROZEN)
    train_p, oos_p = period_strings(panels, events)
    reg.reveal_experiment(ws, exp, results, train_period=train_p, oos_period=oos_p, frozen=FROZEN)
    return exp, reg.experiment_trials(ws, exp), panels
