"""Minimum viability floor after a SELECTION_HOLDOUT (v1.2.1): the human may choose a final config only if, in the holdout, its
selected effect > 0, its selected frequency >= 1.0/week and at least 2 of its 3 frozen models have positive uplift. If no frozen config
qualifies the status is NO_FINAL_CONFIG: the experiment stops, CPCV never runs, and the human cannot override it. No other gate exists."""
import json
import shutil

import pytest

from engine import cpcv as C
from engine import trial_registry as reg
from engine.common import EngineError, load_frozen
from engine.experiment_lifecycle import experiment_dir
from engine.holdout_preference import holdout_preference
from engine.selection_holdout_stage import ApprovalError, freeze_final_config, holdout_report_path, validate_final_selection
from tests.scenario_helpers import (NEAR_TIE_PAIR, finalize_config, human_approval, human_final_selection, lifecycle_workspace, pair_60_first, proposable,
                                    run_cpcv_stage, spend_selection_holdout, weaken)

F = load_frozen()
Y = [2020]


def clone(ws, tmp_path, name="c"):
    shutil.copytree(ws.root, tmp_path / name)
    return reg.Workspace(tmp_path / name)


@pytest.fixture(scope="module")
def life(tmp_path_factory):
    ws, exp, tables = lifecycle_workspace(tmp_path_factory.mktemp("viab"), **NEAR_TIE_PAIR)
    return ws, exp, tables, pair_60_first(proposable(ws, exp, 0))      # cfgs = [60, 15] (same side)


def spent(life, tmp_path_factory, name, tables):
    ws0, exp, _, cfgs = life
    ws = clone(ws0, tmp_path_factory.mktemp(name), "ws")
    human_approval(ws, exp, cfgs)
    rep = spend_selection_holdout(ws, exp, tables)
    return ws, rep


@pytest.fixture(scope="module")
def both(life, tmp_path_factory):                                         # 60 keeps half its effect: both viable
    return spent(life, tmp_path_factory, "both", weaken(life[2], "DIR_RETURN_60", Y, 0.5))


@pytest.fixture(scope="module")
def only_b(life, tmp_path_factory):                                       # 60's effect reverses in the holdout year: only 15 is viable
    return spent(life, tmp_path_factory, "onlyb", weaken(life[2], "DIR_RETURN_60", Y, 1.6))


@pytest.fixture(scope="module")
def neither(life, tmp_path_factory):                                      # both effects reverse sign in the holdout year
    t = weaken(weaken(life[2], "DIR_RETURN_60", Y, 1.6), "DIR_RETURN_15", Y, 1.6)
    return spent(life, tmp_path_factory, "neither", t)


# 1. both viable -> either may be chosen
@pytest.mark.parametrize("which", [0, 1])
def test_both_viable_the_human_may_choose_either(life, both, tmp_path, which):
    ws0, rep = both
    exp, cfgs = life[1], life[3]
    assert rep["viable_configs"] == cfgs and rep["no_final_config"] is False and reg.experiment_row(ws0, exp)["status"] == "SELECTION_HOLDOUT_SPENT"
    ws = clone(ws0, tmp_path)
    human_final_selection(ws, exp, cfgs[which])
    assert freeze_final_config(ws, exp)["selected_config_id"] == cfgs[which] and reg.experiment_row(ws, exp)["status"] == "FINAL_CONFIG_FROZEN"


# 2. only A viable -> only A may be selected
def test_only_the_viable_config_may_be_selected(life, only_b, tmp_path):
    ws0, rep = only_b
    exp, (weak, good) = life[1], life[3]
    assert rep["viable_configs"] == [good] and rep["no_final_config"] is False and reg.experiment_row(ws0, exp)["status"] == "SELECTION_HOLDOUT_SPENT"
    ws = clone(ws0, tmp_path)
    human_final_selection(ws, exp, weak)
    with pytest.raises(ApprovalError, match="fails the minimum viability floor.*cannot override"):
        freeze_final_config(ws, exp)
    assert reg.read_final_configs(ws).empty and reg.experiment_row(ws, exp)["status"] == "SELECTION_HOLDOUT_SPENT"
    human_final_selection(ws, exp, good)
    assert freeze_final_config(ws, exp)["selected_config_id"] == good


# 3 + 7. neither viable -> NO_FINAL_CONFIG, nothing can be selected, CPCV never runs
def test_neither_viable_is_no_final_config_and_cpcv_never_runs(life, neither, tmp_path):
    ws0, rep = neither
    exp, cfgs, tables = life[1], life[3], life[2]
    assert rep["viable_configs"] == [] and rep["no_final_config"] is True and rep["status"] == "NO_FINAL_CONFIG"
    assert reg.experiment_row(ws0, exp)["status"] == "NO_FINAL_CONFIG" and reg.experiment_row(ws0, exp)["status"] in reg.LIFECYCLE
    assert "NO_FINAL_CONFIG" in (experiment_dir(ws0, exp) / "results/SELECTION_HOLDOUT_REPORT.md").read_text()
    for choice in (cfgs[0], cfgs[1], "DECLINE"):                          # no human choice, not even a decline, re-opens the experiment
        ws = clone(ws0, tmp_path, f"x{abs(hash(choice))}")
        human_final_selection(ws, exp, choice)
        with pytest.raises(ApprovalError, match="NO_FINAL_CONFIG"):
            freeze_final_config(ws, exp)
        with pytest.raises(ApprovalError, match="NO_FINAL_CONFIG"):
            validate_final_selection(ws, exp)
        assert reg.read_final_configs(ws).empty and reg.read_cpcv(ws).empty
        with pytest.raises(EngineError, match="CPCV runs only for FINAL_CONFIG_FROZEN"):
            C.precheck_cpcv(ws, exp)
        with pytest.raises(EngineError, match="no FINAL_CONFIG_FROZEN ledger row"):
            run_cpcv_stage(ws, exp, tables)
        assert reg.experiment_row(ws, exp)["status"] == "NO_FINAL_CONFIG"
    assert not any(h[0] in ("FINAL_CONFIG_FROZEN", "CPCV_CONFIRMED", "CPCV_REJECTED") for h in json.loads(reg.experiment_row(ws0, exp)["status_history"]))


# 4-6. each condition on its own, through the real validator, with the real preference/qualifies logic
def rewrite(ws, exp, cfg, **per_model):
    """Rewrite one config's holdout model rows (test-only) and recompute the report's preference/viability exactly as the engine does."""
    p = holdout_report_path(ws, exp)
    H = json.loads(p.read_text())
    g = cfg.split("|", 1)[1]
    for r in H["evaluations"]:
        if r["group_id"] == g:
            for k, v in per_model.items():
                r[k] = v[r["model"]] if isinstance(v, dict) else v
    configs = [{"config_id": c, "is_rank": next(x["is_rank"] for x in H["preference"]["cards"] if x["config_id"] == c),
                "model_rows": [r for r in H["evaluations"] if r["group_id"] == c.split("|", 1)[1]]} for c in H["approved_configs"]]
    H["preference"] = holdout_preference(configs, F)
    H["viable_configs"] = [c["config_id"] for c in H["preference"]["cards"] if c["qualifies"]]
    p.write_text(json.dumps(H, indent=2, sort_keys=True))
    return H


@pytest.mark.parametrize("name,changes,needle", [
    ("frequency_below_1_per_week", {"selected_frequency": 0.9}, r"selected frequency 0\.900/week < 1\.0"),
    ("effect_zero", {"selected_effect": 0.0}, r"selected effect \+0\.00000 <= 0"),
    ("effect_negative", {"selected_effect": -0.01}, r"selected effect -0\.01000 <= 0"),
    ("one_of_three_positive_uplift", {"uplift": {"RIDGE": 0.05, "SPLINE": -0.02, "XGB": -0.02}}, r"only 1 of 3 models have positive uplift"),
])
def test_each_viability_condition_blocks_selection_on_its_own(both, life, tmp_path, name, changes, needle):
    ws = clone(both[0], tmp_path)
    exp, cfgs = life[1], life[3]
    target, other = cfgs[1], cfgs[0]
    H = rewrite(ws, exp, target, **changes)
    assert target not in H["viable_configs"] and other in H["viable_configs"]                      # only the edited config lost viability
    human_final_selection(ws, exp, target)
    with pytest.raises(ApprovalError, match=needle):
        validate_final_selection(ws, exp)
    assert reg.read_final_configs(ws).empty and reg.experiment_row(ws, exp)["status"] == "SELECTION_HOLDOUT_SPENT"
    human_final_selection(ws, exp, other)                                                          # the untouched viable config is still selectable
    assert validate_final_selection(ws, exp)["selected_config_id"] == other


def test_two_of_three_positive_uplift_is_viable_and_exactly_one_per_week_is_viable(both, life, tmp_path):
    ws = clone(both[0], tmp_path)
    exp, cfgs = life[1], life[3]
    H = rewrite(ws, exp, cfgs[1], selected_frequency=1.0, uplift={"RIDGE": 0.05, "SPLINE": 0.02, "XGB": -0.02})
    assert cfgs[1] in H["viable_configs"]                                                          # boundary values pass: >= 1.0/week and >= 2 of 3
    human_final_selection(ws, exp, cfgs[1])
    assert validate_final_selection(ws, exp)["selected_config_id"] == cfgs[1]


def test_all_configs_non_viable_through_the_rewritten_report_also_stops(both, life, tmp_path):
    ws = clone(both[0], tmp_path)
    exp, cfgs = life[1], life[3]
    for c in cfgs:
        rewrite(ws, exp, c, selected_frequency=0.5)
    human_final_selection(ws, exp, cfgs[0])
    with pytest.raises(ApprovalError, match="fails the minimum viability floor"):
        validate_final_selection(ws, exp)


# the floor is the only new gate; HOLDOUT_UNRESOLVED may still be reported and the frozen rule is recorded
def test_the_floor_is_frozen_policy_and_unresolved_can_coexist_with_viable_configs(life, tmp_path_factory):
    v = F.selection_process["final_config"]["viability_floor_after_holdout"]
    assert v == {"selected_effect_gt": 0, "selected_frequency_per_week_ge": 1.0, "models_with_positive_uplift_ge": 2, "none_viable": "NO_FINAL_CONFIG"}
    ws, rep = spent(life, tmp_path_factory, "unres", life[2])
    exp, cfgs = life[1], life[3]
    assert rep["preference"]["status"] == "HOLDOUT_UNRESOLVED" and rep["viable_configs"] == cfgs   # close, still both viable: the human picks (viable) either
    human_final_selection(ws, exp, cfgs[0])
    assert freeze_final_config(ws, exp)["selected_config_id"] == cfgs[0]


# end to end: a viable choice proceeds to CPCV automatically (the floor does not break the happy path)
def test_a_viable_choice_still_reaches_cpcv(both, life, tmp_path):
    ws = clone(both[0], tmp_path)
    exp, cfgs, tables = life[1], life[3], weaken(life[2], "DIR_RETURN_60", Y, 0.5)
    info, rep = finalize_config(ws, exp, tables, cfgs[1])
    assert info["selected_config_id"] == cfgs[1] and rep is not None and reg.experiment_row(ws, exp)["status"] in ("AWAITING_FINAL_LOCKBOX_APPROVAL", "CPCV_REJECTED")
