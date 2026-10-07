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


def probe(ok=3, eff=None, keep=None, freq=None, mult=1.25, param="pivot_left"):
    """Counts of models (out of 3) that are OK / keep a positive effect / keep >= 50% of the base uplift / keep >= 1 trade a week."""
    return {"parameter": param, "multiplier": mult, "base": 30, "value": 38, "n_events": 1000, "models": [],
            "models_ok": ok, "models_positive_effect": ok if eff is None else eff,
            "models_retained_uplift": ok if keep is None else keep, "models_frequency_ok": ok if freq is None else freq}


def test_probe_values_and_grid_size():
    assert probe_value(30, 0.75) == 23 and probe_value(30, 1.25) == 38          # integers rounded half-up
    assert probe_value(15, 0.75) == 11 and probe_value(15, 1.25) == 19
    assert probe_value(0.5, 0.75) == pytest.approx(0.375) and isinstance(probe_value(0.5, 1.25), float)
    g = probe_grid(spec(), F)
    assert len(g) == 4 and F.trial_policy["sensitivity"]["max_probes"] == 24
    assert [(p["parameter"], p["multiplier"]) for p in g] == [("pivot_left", 0.75), ("pivot_left", 1.25),
                                                             ("pivot_right", 0.75), ("pivot_right", 1.25)]
    assert len(probe_grid(spec(sensitivity_parameters=["pivot_left"]), F)) == 2
    assert probe_grid(spec(sensitivity_parameters=[]), F) == []
    assert len(probe_grid(spec(sensitivity_parameters=list("abcd"), base_parameters={k: 4 for k in "abcd"}), F)) == 8   # no longer capped at 2
    with pytest.raises(Exception):                                                                        # the policy cap is 12 parameters
        names = [f"p{i}" for i in range(13)]
        probe_grid(spec(sensitivity_parameters=names, base_parameters={n: 4 for n in names}), F)


def test_every_probeable_parameter_must_be_listed():
    from engine.event_contract import validate_spec
    ok = spec(base_parameters={"pivot_left": 30, "pivot_right": 15, "buffer": 0.25, "direction": 1},
              sensitivity_parameters=["pivot_left", "pivot_right", "buffer"])
    assert not [e for e in validate_spec(ok, F) if "sensitivity" in e]                              # direction = 1 is not probeable
    bad = spec(base_parameters={"pivot_left": 30, "pivot_right": 15, "buffer": 0.25, "direction": 1},
               sensitivity_parameters=["pivot_left", "pivot_right"])
    errs = [e for e in validate_spec(bad, F) if "sensitivity" in e]
    assert errs and "buffer" in errs[0] and "every probeable" in errs[0]


def test_probes_are_one_at_a_time():
    base = spec()["base_parameters"]
    for p in probe_grid(spec(), F):
        changed = {k for k in base if k == p["parameter"]}
        assert changed == {p["parameter"]}


def test_verdict_rule_any_failing_probe_fails():
    ok = lambda: probe(3)
    bad = lambda: probe(ok=1)                       # fewer than 2 of 3 models are OK at this probe
    assert judge_group([ok(), ok(), ok(), ok()], ACC)["verdict"] == "PASSED"
    assert judge_group([probe(2), ok()], ACC)["verdict"] == "PASSED"                  # 2 of 3 models OK is enough (mirrors model agreement)
    v = judge_group([bad(), ok(), ok(), ok()], ACC)
    assert v["verdict"] == "FAILED" and v["n_failing_probes"] == 1                    # v2.3.0: ONE failing probe vetoes (max_failing_probes = 0)


def test_probe_fails_on_each_condition_separately():
    # effect not positive, uplift below 50% of base, frequency below 1/week: each counted and each fails the group
    for kw, key in ((dict(ok=1, eff=1), "n_effect_not_positive"), (dict(ok=1, keep=1), "n_uplift_below_retention"),
                    (dict(ok=1, freq=1), "n_frequency_failures")):
        v = judge_group([probe(3), probe(**kw)], ACC)
        assert v["verdict"] == "FAILED" and v[key] == 1, kw


def test_better_probe_performance_cannot_replace_or_improve_the_base():
    # a probe with far stronger uplift changes nothing: the verdict only looks at the OK counts
    strong = probe(3); strong["models"] = [{"model": "RIDGE", "standardized_uplift": 5.0}]
    weak = probe(3)
    assert judge_group([strong], ACC) == {**judge_group([weak], ACC), "probes": [strong]}
    out = judge_group([strong], ACC)
    assert set(out) == {"verdict", "n_failing_probes", "n_effect_not_positive", "n_uplift_below_retention", "n_frequency_failures", "probes"}
    sig = inspect.signature(run_sensitivity)
    assert "base_parameters" not in sig.parameters and "params" not in sig.parameters


from tests.test_statistics import VER_ALL, good_row


def rows_for(pass_models):
    return [good_row(model=m, state="UPPER_HALF", trial_id=m, standardized_uplift=0.2 if m in pass_models else 0.0)
            for m in ("RIDGE", "SPLINE", "XGB")]


def test_sensitivity_cannot_rescue_a_failed_base_candidate():
    sens = {"DIR_RETURN_180|UPPER_HALF": "PASSED"}
    none = decide_experiment(rows_for(set()), ACC, sens, VER_ALL)
    assert {r["decision"] for r in none} == {acceptance.LOW_UPLIFT}                       # nothing passes -> nothing promoted
    one = decide_experiment(rows_for({"RIDGE"}), ACC, sens, VER_ALL)
    assert next(r for r in one if r["model"] == "RIDGE")["decision"] == acceptance.AGREE    # 1 of 3 is not a candidate
    two = decide_experiment(rows_for({"RIDGE", "XGB"}), ACC, sens, VER_ALL)
    assert {r["decision"] for r in two if r["model"] != "SPLINE"} == {acceptance.SHORTLIST}
    # and a PASSED sensitivity verdict has no effect on trials that did not pass their own gates
    assert next(r for r in two if r["model"] == "SPLINE")["decision"] == acceptance.LOW_UPLIFT


def test_zero_designated_parameters_skips_the_stage():
    pending = pd.DataFrame([{"target": "DIR_RETURN_180", "state": "UPPER_HALF"}])
    out = run_sensitivity(None, spec(sensitivity_parameters=[]), None, F, pending)
    assert out["status"] == "SKIPPED_NO_PARAMETERS"
    assert out["groups"]["DIR_RETURN_180|UPPER_HALF"]["verdict"] == "SKIPPED_NO_PARAMETERS"
    done = decide_experiment(rows_for({"RIDGE", "XGB"}), ACC, {"DIR_RETURN_180|UPPER_HALF": "SKIPPED_NO_PARAMETERS"}, VER_ALL)
    assert {r["decision"] for r in done if r["model"] != "SPLINE"} == {acceptance.SHORTLIST}


def test_frozen_sensitivity_policy_values():
    s = F.trial_policy["sensitivity"]
    assert (s["max_parameters"], s["multipliers"], s["max_probes"]) == (12, [0.75, 1.25], 24)
    a = ACC["sensitivity"]
    assert (a["max_failing_probes"], a["min_retained_uplift_fraction"], a["selected_effect_must_exceed"], a["min_probe_frequency_per_week"]) == (0, 0.5, 0.0, 1.0)
