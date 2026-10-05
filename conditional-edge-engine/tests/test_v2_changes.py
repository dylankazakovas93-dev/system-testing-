"""v2.0.0: uplift floor 0.01 (null-based gates carry the burden), targets 15/60/180 with session-end truncation, descriptive where-it-works map."""
import json

import numpy as np
import pandas as pd
import pytest

from engine import where_map
from engine.acceptance import LOW_UPLIFT, classify_trial
from engine.common import load_frozen, primary_target_names
from engine.selection_holdout_stage import selection_holdout_evaluations
from tests.test_statistics import good_row

F = load_frozen()
ACC = F.acceptance


def test_the_uplift_floor_is_001_and_nothing_larger_remains():
    assert ACC["min_standardized_uplift"] == 0.01 and ACC["selection_holdout_evidence"]["min_standardized_uplift"] == 0.01
    assert classify_trial(good_row(standardized_uplift=0.01), ACC)[0]
    assert classify_trial(good_row(standardized_uplift=0.012), ACC)[0]                          # 0.012 passes: no hidden 0.10
    ok, dec, why = classify_trial(good_row(standardized_uplift=0.0099), ACC)
    assert not ok and dec == LOW_UPLIFT and "< 0.01" in why
    # the other gates are untouched
    assert ACC["min_selected_frequency_per_week"] == 1.0 and ACC["bootstrap_ci_lower_bound_must_exceed"] == 0.0 and ACC["max_experiment_q"] == 0.05
    assert ACC["year_consistency"]["min_positive_effect_year_fraction"] == 0.70 and "fold_consistency" not in ACC
    row = dict(group_id="G|U", model="RIDGE", n_selected=300, selected_frequency=2.0, standardized_uplift=0.012, selected_effect=0.1, bootstrap_ci_low=0.01, raw_p=0.001)
    assert selection_holdout_evaluations([row], ACC["selection_holdout_evidence"])[0]["gates_pass"] is True


def test_primary_targets_are_15_60_180_and_path_skew_with_24_trials():
    assert primary_target_names(F) == ["DIR_RETURN_15", "DIR_RETURN_60", "DIR_RETURN_180", "DIR_PATH_SKEW_60"]
    assert len(__import__("engine.trial_registry", fromlist=["x"]).trial_specs(F)) == 24
    assert F.target_bank["session_rule"] == "primary_targets_truncate_at_event_rth_session_close"
    assert not any(t["name"] in ("DIR_RETURN_30", "DIR_RETURN_120") for t in F.target_bank["primary_targets"])


def _cv(path, rows):
    pd.DataFrame(rows, columns=["event_id", "event_time", "fold", "year", "score", "threshold", "state", "y", "truncated"]).to_csv(path, index=False)


def test_where_map_reports_buckets_by_year_hour_and_truncation_and_flags_failures(tmp_path):
    from engine import trial_registry as reg
    from engine.experiment_lifecycle import experiment_dir
    ws = reg.Workspace(tmp_path).init()
    d = experiment_dir(ws, "EXP_0001") / "results"
    d.mkdir(parents=True)
    rng = np.random.default_rng(0)
    rows = []
    for i in range(4000):
        year = 2018 + (i % 2)
        hour = 10 + (i // 2) % 4                                                      # 10..13 NY
        trunc = hour == 13
        t = pd.Timestamp(f"{year}-03-0{1 + i % 5} {hour + 5}:00:00", tz="UTC") + pd.Timedelta(seconds=i)
        sel = i % 2 == 0
        edge = 0.5 if (year == 2018 and not trunc) else -0.5 if trunc else 0.0        # works in 2018 full-horizon, fails when truncated
        y = rng.normal() + (edge if sel else 0.0)
        rows.append((f"E{i}", t, 0, year, 0.0, 0.0, "UPPER_HALF" if sel else "LOWER_HALF", y, trunc))
    for m in ("RIDGE", "SPLINE"):
        _cv(d / f"cv_DIR_RETURN_60_{m}.csv", rows)
    g = {"group_id": "DIR_RETURN_60|UPPER_HALF", "target": "DIR_RETURN_60", "state": "UPPER_HALF", "models": ["RIDGE", "SPLINE"]}
    wm = where_map.build(ws, "EXP_0001", [g], F)
    assert wm["available"] and wm["label"] == "DESCRIPTIVE — NOT A SELECTION TRIAL"
    m = wm["groups"]["DIR_RETURN_60|UPPER_HALF"]
    by = {k: {r["bucket"]: r for r in m[k]} for k in ("year", "hour", "horizon")}
    assert set(by["year"]) == {"2018", "2019"} and set(by["horizon"]) == {"full_horizon", "truncated_at_session_close"}
    assert by["horizon"]["full_horizon"]["median_uplift"] > 0 and by["horizon"]["truncated_at_session_close"]["median_uplift"] < 0
    assert by["horizon"]["full_horizon"]["verdict"].startswith("works") and by["horizon"]["truncated_at_session_close"]["verdict"].startswith("does NOT work")
    assert by["hour"]["13:00"]["verdict"].startswith("does NOT work") and by["hour"]["10:00"]["median_uplift"] > -0.3
    assert json.dumps(wm, sort_keys=True) == json.dumps(where_map.build(ws, "EXP_0001", [g], F), sort_keys=True)     # deterministic
    md = "\n".join(where_map.render(wm, lambda x: f"{x:+.4f}"))
    assert "DESCRIPTIVE" in md and "does NOT work" in md and "truncated_at_session_close" in md


def test_where_map_never_enters_the_selection_path():
    import inspect

    from engine import acceptance, near_tie, trial_registry
    for mod in (acceptance, near_tie, trial_registry):
        assert "where_map" not in inspect.getsource(mod)
    src = inspect.getsource(where_map)
    assert "set_status" not in src and "append_" not in src and "update_experiment" not in src


def test_table_level_is_report_has_the_where_it_works_section_and_it_is_deterministic(tmp_path_factory):
    from engine import trial_registry as reg
    from engine.experiment_lifecycle import experiment_dir
    from engine.is_report import write_is_report
    from tests.scenario_helpers import CLEAR_WINNER, lifecycle_workspace
    ws, exp, _ = lifecycle_workspace(tmp_path_factory.mktemp("wm"), **CLEAR_WINNER)
    r = experiment_dir(ws, exp) / "results"
    md = (r / "IS_REPORT.md").read_text()
    j = json.loads((r / "IS_REPORT.json").read_text())
    assert "## WM. WHERE IT WORKS / WHERE IT DOES NOT" in md and "DESCRIPTIVE — NOT A SELECTION TRIAL" in md
    wm = j["WM_where_it_works"]
    assert wm["available"] and set(wm["groups"]) == {g["group_id"] for g in j["I_top_configurations"]["top_groups"]}
    assert len(reg.read_trials(ws)) == 24                                              # the map created no trial
    before = json.dumps(wm, sort_keys=True)
    write_is_report(ws, exp)
    assert json.dumps(json.loads((r / "IS_REPORT.json").read_text())["WM_where_it_works"], sort_keys=True) == before
