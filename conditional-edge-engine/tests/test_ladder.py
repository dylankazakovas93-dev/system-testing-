import textwrap

import numpy as np
import pandas as pd
import pytest

from engine import trial_registry as reg
from engine.common import load_frozen
from engine.event_contract import load_event_module
from engine.ladder import evaluate_ladder
from engine.synthetic import make_bars
from tests.test_event_contract import LADDER_EVENT, module_from, spec

F = load_frozen()


def ladder_spec(order=("BASE_TRIGGER", "CONDITION_1", "FINAL_EVENT")):
    return spec(base_parameters={"step": 41}, filter_ladder=list(order))


def test_ladder_steps_report_frequency_retention_effect_uplift_and_yearly_tables(tmp_path):
    bars = make_bars(n_days=520, seed=4, phi=0.8)                                    # planted momentum: 'up' bars improve the outcome
    mod = module_from(tmp_path, LADDER_EVENT)
    lad = evaluate_ladder(mod, ladder_spec(), bars, F)
    assert lad["label"] == "DIAGNOSTIC ONLY — NOT A SELECTION TRIAL" and lad["order_frozen"] == ["BASE_TRIGGER", "CONDITION_1", "FINAL_EVENT"]
    steps = lad["steps"]
    assert [s["step"] for s in steps] == lad["order_frozen"]
    base, c1, fin = steps
    assert base["n_events"] > c1["n_events"] == fin["n_events"] > 0
    r = c1["targets"]["DIR_RETURN_15"]
    assert r["retention_vs_parent"] == pytest.approx(c1["n_events"] / base["n_events"])
    assert r["retention_vs_previous"] == pytest.approx(c1["n_events"] / base["n_events"])
    assert fin["targets"]["DIR_RETURN_15"]["retention_vs_previous"] == pytest.approx(1.0)
    b = base["targets"]["DIR_RETURN_15"]
    assert r["uplift_vs_parent"] == pytest.approx(r["effect"] - b["effect"]) and r["uplift_vs_previous"] == pytest.approx(r["effect"] - b["effect"])
    assert r["uplift_vs_parent"] > 0                                                 # momentum makes the 'up' filter genuinely better
    assert r["yearly"] and all({"year", "n", "effect", "uplift_vs_parent", "uplift_vs_previous", "eligible"} <= set(y) for y in r["yearly"])
    assert r["steady_improvement_vs_previous"] is True and r["flags"] == []          # >= 70% of eligible years improve: no flag
    assert r["positive_uplift_years_vs_previous"] == r["eligible_years"] >= 2


def test_bad_filter_is_flagged_but_never_removed_reordered_or_changed(tmp_path):
    bad = LADDER_EVENT.replace("up[1:] = c[1:] > c[:-1]", "up[1:] = c[1:] < c[:-1]")           # CONDITION_1 now selects the WORSE half
    bars = make_bars(n_days=520, seed=4, phi=0.8)
    lad = evaluate_ladder(module_from(tmp_path, bad), ladder_spec(), bars, F)
    names = [s["step"] for s in lad["steps"]]
    assert names == ["BASE_TRIGGER", "CONDITION_1", "FINAL_EVENT"]                    # the engine kept the bad filter in place
    r = lad["steps"][1]["targets"]["DIR_RETURN_15"]
    assert r["uplift_vs_previous"] < 0 and r["steady_improvement_vs_previous"] is False
    assert r["flags"] == ["FREQUENCY_DESTRUCTION", "NO_CONSISTENT_IMPROVEMENT"]       # fewer events AND no steady improvement
    assert lad["steps"][2]["targets"]["DIR_RETURN_15"]["flags"] == []                  # FINAL_EVENT == CONDITION_1: nothing further to flag
    assert lad["steps"][2]["targets"]["DIR_RETURN_15"]["identical_to_previous_step"] is True
    assert lad["steps"][2]["targets"]["DIR_RETURN_15"]["retention_vs_previous"] == pytest.approx(1.0)


def test_ladder_never_changes_automatically_between_runs_and_is_deterministic(tmp_path):
    bars = make_bars(n_days=300, seed=5, phi=0.5)
    mod = module_from(tmp_path, LADDER_EVENT)
    a = evaluate_ladder(mod, ladder_spec(), bars, F)
    b = evaluate_ladder(mod, ladder_spec(), bars, F)
    assert a == b
    # no engine API reorders/removes/adds/re-thresholds steps: the only inputs are the frozen order and the module output
    import inspect
    import engine.ladder as L
    src = inspect.getsource(L).split('"""', 2)[2]                                   # code only, not the docstring
    for forbidden in ("reorder", "drop_step", "remove(", "threshold", "optimi", "argmax", "best"):
        assert forbidden not in src.replace("DIAGNOSTIC", ""), forbidden


def test_no_ladder_means_nothing_is_evaluated(tmp_path):
    mod = module_from(tmp_path, LADDER_EVENT)
    assert evaluate_ladder(mod, spec(base_parameters={"step": 41}), make_bars(n_days=30), F) == {}
