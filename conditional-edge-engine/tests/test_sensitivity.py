import copy
import inspect

import pandas as pd
import pytest
import yaml

from engine import acceptance, sensitivity
from engine.acceptance import decide_experiment
from engine.common import CODE_ROOT, load_frozen
from engine.sensitivity import judge_group, probe_grid, probe_value, run_sensitivity

F = load_frozen()
ACC = F.acceptance


def spec(**kw):
    s = yaml.safe_load((CODE_ROOT / "templates/experiment/EVENT_SPEC.yaml").read_text())
    s.update(kw)
    return s


def probe(pos, freq_ok, mult=1.25, param="pivot_left"):
    return {"parameter": param, "multiplier": mult, "base": 30, "value": 38, "n_events": 1000, "models": [],
            "models_positive_uplift": pos, "models_frequency_ok": freq_ok}


def test_probe_values_and_grid_size():
    assert probe_value(30, 0.75) == 23 and probe_value(30, 1.25) == 38          # integers rounded half-up
    assert probe_value(15, 0.75) == 11 and probe_value(15, 1.25) == 19
    assert probe_value(0.5, 0.75) == pytest.approx(0.375) and isinstance(probe_value(0.5, 1.25), float)
    g = probe_grid(spec(), F)
    assert len(g) == 4 == F.trial_policy["sensitivity"]["max_probes"]
    assert [(p["parameter"], p["multiplier"]) for p in g] == [("pivot_left", 0.75), ("pivot_left", 1.25),
                                                             ("pivot_right", 0.75), ("pivot_right", 1.25)]
    assert len(probe_grid(spec(sensitivity_parameters=["pivot_left"]), F)) == 2
    assert probe_grid(spec(sensitivity_parameters=[]), F) == []
    with pytest.raises(Exception):
        probe_grid(spec(sensitivity_parameters=["a", "b", "c"], base_parameters={"a": 4, "b": 4, "c": 4}), F)


def test_probes_are_one_at_a_time():
    base = spec()["base_parameters"]
    for p in probe_grid(spec(), F):
        changed = {k for k in base if k == p["parameter"]}
        assert changed == {p["parameter"]}


def test_verdict_rule_more_than_one_reversing_probe_fails():
    ok = lambda: probe(3, 3)
    bad = lambda: probe(1, 3)                     # fewer than 2 of 3 models keep a positive uplift -> sign reversed
    assert judge_group([ok(), ok(), ok(), ok()], ACC)["verdict"] == "PASSED"
    assert judge_group([bad(), ok(), ok(), ok()], ACC)["verdict"] == "PASSED"           # exactly one reversal is tolerated
    v = judge_group([bad(), bad(), ok(), ok()], ACC)
    assert v["verdict"] == "FAILED" and v["n_reversing_probes"] == 2


def test_verdict_rule_any_probe_below_one_per_week_fails():
    v = judge_group([probe(3, 3), probe(3, 1), probe(3, 3), probe(3, 3)], ACC)       # <2 of 3 models keep >= 1/week
    assert v["verdict"] == "FAILED" and v["n_frequency_failures"] == 1
    assert judge_group([probe(3, 2), probe(3, 3)], ACC)["verdict"] == "PASSED"


def test_better_probe_performance_cannot_replace_or_improve_the_base():
    # a probe with far stronger uplift changes nothing: the verdict only looks at sign and frequency counts
    strong = probe(3, 3); strong["models"] = [{"model": "RIDGE", "standardized_uplift": 5.0}]
    weak = probe(3, 3)
    assert judge_group([strong], ACC) == {**judge_group([weak], ACC), "probes": [strong]}
    out = judge_group([strong], ACC)
    assert set(out) == {"verdict", "n_reversing_probes", "n_frequency_failures", "probes"}     # no "best"/"chosen_parameter"
    sig = inspect.signature(run_sensitivity)
    assert "base_parameters" not in sig.parameters and "params" not in sig.parameters


from tests.test_statistics import VER_ALL, good_row


def rows_for(pass_models):
    return [good_row(model=m, state="UPPER_HALF", trial_id=m, standardized_uplift=0.2 if m in pass_models else 0.0)
            for m in ("RIDGE", "SPLINE", "XGB")]


def test_sensitivity_cannot_rescue_a_failed_base_candidate():
    sens = {"DIR_RETURN_30|UPPER_HALF": "PASSED"}
    none = decide_experiment(rows_for(set()), ACC, sens, VER_ALL)
    assert {r["decision"] for r in none} == {acceptance.LOW_UPLIFT}                       # nothing passes -> nothing promoted
    one = decide_experiment(rows_for({"RIDGE"}), ACC, sens, VER_ALL)
    assert next(r for r in one if r["model"] == "RIDGE")["decision"] == acceptance.AGREE    # 1 of 3 is not a candidate
    two = decide_experiment(rows_for({"RIDGE", "XGB"}), ACC, sens, VER_ALL)
    assert {r["decision"] for r in two if r["model"] != "SPLINE"} == {acceptance.SHORTLIST}
    # and a PASSED sensitivity verdict has no effect on trials that did not pass their own gates
    assert next(r for r in two if r["model"] == "SPLINE")["decision"] == acceptance.LOW_UPLIFT


def test_zero_designated_parameters_skips_the_stage():
    pending = pd.DataFrame([{"target": "DIR_RETURN_30", "state": "UPPER_HALF"}])
    out = run_sensitivity(None, spec(sensitivity_parameters=[]), None, F, pending)
    assert out["status"] == "SKIPPED_NO_PARAMETERS"
    assert out["groups"]["DIR_RETURN_30|UPPER_HALF"]["verdict"] == "SKIPPED_NO_PARAMETERS"
    done = decide_experiment(rows_for({"RIDGE", "XGB"}), ACC, {"DIR_RETURN_30|UPPER_HALF": "SKIPPED_NO_PARAMETERS"}, VER_ALL)
    assert {r["decision"] for r in done if r["model"] != "SPLINE"} == {acceptance.SHORTLIST}


def test_frozen_sensitivity_policy_values():
    s = F.trial_policy["sensitivity"]
    assert (s["max_parameters"], s["multipliers"], s["max_probes"]) == (2, [0.75, 1.25], 4)
    assert ACC["sensitivity"]["max_reversing_probes"] == 1 and ACC["sensitivity"]["min_probe_frequency_per_week"] == 1.0
