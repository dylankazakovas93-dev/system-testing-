"""The frozen v1 numbers exactly as specified, plus structural guarantees (no search machinery, no lockbox path)."""
import argparse
import ast
import inspect
from pathlib import Path

import pytest
import yaml

from engine import experiment_runner, oos_stage, partitions, trial_registry as reg
from engine.acceptance import classify_trial, decide_experiment
from engine.common import CODE_ROOT, frozen_files, load_frozen
from engine.feature_engine import feature_names

F = load_frozen()


def test_frozen_feature_bank_matches_the_specification():
    fam = {f["id"]: f["params"] for f in F.feature_bank["families"]}
    assert fam["returns"]["lookbacks"] == [5, 15, 30, 60, 120, 240]
    assert fam["volatility"]["rv_lookbacks"] == [5, 15, 30, 60, 120, 240] and fam["volatility"]["vov_lookbacks"] == [30, 60, 120]
    assert fam["kaufman_er"]["lookbacks"] == [15, 30, 60, 120, 240]
    assert fam["brownian"]["disp_lookbacks"] == [15, 30, 60, 120, 240]
    assert fam["brownian"]["vr_windows"] == [60, 120, 240] and fam["brownian"]["vr_lags"] == [2, 4, 8]
    assert fam["hurst"]["windows"] == [120, 240, 480] and fam["hurst"]["lags"] == [1, 2, 4, 8, 16]
    assert fam["candles"]["lookbacks"] == [15, 30, 60] and fam["volume"]["lookbacks"] == [15, 30, 60]
    assert fam["range"]["lookbacks"] == [15, 30, 60, 120]
    assert F.feature_bank["expected_feature_count"] == 56 == len(feature_names(F))
    assert F.feature_bank["min_history_bars"] == 480
    inst = F.instrument
    assert (inst["timezone"], inst["rth"]["open"], inst["rth"]["close"], inst["eth_session_start"]) == \
           ("America/New_York", "09:30", "16:00", "18:00")


def test_frozen_targets_models_policy_acceptance_values():
    assert [t["name"] for t in F.target_bank["primary_targets"]] == ["DIR_RETURN_15", "DIR_RETURN_30", "DIR_RETURN_60", "DIR_PATH_SKEW_60"]
    assert F.target_bank["session_rule"] == "primary_targets_must_resolve_inside_event_rth_session"
    m = F.model_bank["models"]
    assert list(m) == ["RIDGE", "SPLINE", "XGB"]
    assert m["RIDGE"]["params"] == {"alpha": 10.0, "fit_intercept": True}
    assert m["SPLINE"]["spline"] == {"degree": 3, "n_knots": 4, "knots": "quantile", "include_bias": False}
    assert m["XGB"]["params"] == {"objective": "reg:squarederror", "max_depth": 2, "learning_rate": 0.03, "n_estimators": 300,
                                  "min_child_weight": 20, "subsample": 0.80, "colsample_bytree": 0.80, "reg_lambda": 20.0,
                                  "reg_alpha": 1.0, "random_state": 1729, "tree_method": "hist"}
    p = F.trial_policy
    assert (p["seed"], p["bootstrap_repetitions"], p["permutation_repetitions"]) == (1729, 2000, 2000)
    assert (p["max_experiments_per_campaign"], p["max_selection_trials_per_campaign"], p["expected_trials_per_experiment"]) == (20, 480, 24)
    assert p["states"] == ["UPPER_HALF", "LOWER_HALF"] and p["base_event_frequency_floor_per_week"] == 2.0
    cv = p["development_cv"]
    assert (cv["K"], cv["min_outer_train_events"], cv["inner_blocks"], cv["min_inner_train_events"], cv["min_inner_oof_events"]) == (5, 300, 5, 50, 30)
    assert cv["label"] == "DEVELOPMENT_CV" and "walkforward" not in p
    assert p["oos"]["max_target_side_groups"] == 2 and p["oos"]["models_per_group"] == 3 and p["oos"]["one_shot"] is True
    assert (p["cpcv"]["n_groups"], p["cpcv"]["n_test_groups"], p["cpcv"]["n_splits"]) == (6, 2, 15) and 15 == len(list(__import__("itertools").combinations(range(6), 2)))
    assert p["single_direction_events_only"] is True and p["shortlist"]["top_groups_reported"] == 5
    a = F.acceptance
    assert a["min_selected_frequency_per_week"] == 1.0 and a["min_standardized_uplift"] == 0.10 and a["selected_effect_must_exceed"] == 0.0
    assert (a["max_experiment_q"], a["max_campaign_q"]) == (0.05, 0.05) and p["ci_level"] == 0.95
    assert a["bonferroni"] == {"max_experiment_p": 0.05, "max_campaign_p": 0.05}
    assert a["year_consistency"] == {"min_selected_events_for_eligible_year": 20, "min_positive_effect_year_fraction": 0.70,
                                     "min_positive_uplift_year_fraction": 0.70, "concentration_warning_share": 0.35}
    assert a["fold_consistency"] == {"required_folds": 5, "min_folds_positive_uplift": 4, "min_folds_positive_effect": 4}
    assert a["model_agreement"]["min_models_passing"] == 2
    assert a["oos_confirmation"]["min_models_passing"] == 2 and a["oos_confirmation"]["max_oos_bonferroni_p"] == 0.05
    assert (a["cpcv"]["n_splits"], a["cpcv"]["min_splits_positive_effect"], a["cpcv"]["min_splits_positive_uplift"]) == (15, 12, 12)
    assert a["verification"]["required_mode"] == "strong"
    assert 4 * 3 * 2 == 24 == len(reg.trial_specs(F))


def test_required_repository_files_exist():
    need = ["README.md", "RESEARCH_RULES.md", "ENGINE_VERSION", "frozen/v1/FEATURE_BANK.yaml", "frozen/v1/TARGET_BANK.yaml",
            "frozen/v1/MODEL_BANK.yaml", "frozen/v1/TRIAL_POLICY.yaml", "frozen/v1/ACCEPTANCE_RULES.yaml",
            "frozen/v1/instruments/NQ_1m.yaml", "experiments/.gitkeep", "registry/experiments.csv",
            "registry/selection_trials.csv", "registry/observations.csv", "registry/oos_access.csv", "AGENTS.md",
            "approvals/README.md", "templates/approval/OOS_APPROVAL.template.yaml", "frozen/v1/VERIFIER_PIN.yaml", "docs/CPCV_PBO.md", "templates/experiment/HYPOTHESIS.md",
            "templates/experiment/EVENT_SPEC.yaml", "templates/experiment/event.py", "templates/experiment/reference.pine"]
    for e in ["feature_engine", "target_engine", "model_engine", "walkforward", "score_calibration", "statistics",
              "multiplicity", "sensitivity", "trial_registry", "experiment_runner", "is_report", "partitions", "oos_stage",
              "cpcv", "ladder", "acceptance"]:
        need.append(f"engine/{e}.py")
    for f in ["returns", "volatility", "kaufman_er", "brownian", "hurst", "candles", "range", "volume", "session"]:
        need.append(f"features/{f}.py")
    for s in ["new_experiment", "freeze_experiment", "run_experiment", "verify_experiment", "campaign_status", "run_oos",
              "run_cpcv", "make_report", "show_approval_hashes", "log_observation", "confirm_lockbox"]:
        need.append(f"scripts/{s}.py")
    missing = [n for n in need if not (CODE_ROOT / n).exists()]
    assert not missing, missing


BANNED = {"optuna", "hyperopt", "skopt", "tpot", "autosklearn", "flaml", "deap", "nevergrad", "ray", "bayes_opt", "pygad",
          "torch", "tensorflow", "keras", "transformers", "lightgbm", "catboost"}
BANNED_NAMES = {"GridSearchCV", "RandomizedSearchCV", "HalvingGridSearchCV", "cross_val_score", "cross_val_predict",
                "KFold", "StratifiedKFold", "ShuffleSplit", "train_test_split", "RFE", "SelectKBest", "SequentialFeatureSelector"}


def _sources():
    for sub in ("engine", "features", "scripts"):
        for p in (CODE_ROOT / sub).glob("*.py"):
            yield p, ast.parse(p.read_text())


def test_no_search_automl_random_cv_or_feature_selection_machinery():
    for p, tree in _sources():
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    assert a.name.split(".")[0] not in BANNED, (p, a.name)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in BANNED, (p, node.module)
                for a in node.names:
                    assert a.name not in BANNED_NAMES, (p, a.name)
            if isinstance(node, ast.Name):
                assert node.id not in BANNED_NAMES, (p, node.id)


def test_no_threshold_mining_constants_in_engine():
    text = "\n".join(p.read_text() for p, _ in _sources() if p.parent.name == "engine")
    for needle in ("ER > 0.2", "ER > .3", "percentile(score", "top_40", "top_quintile", "top_decile", "q=0.8", "q=0.9", "0.75, 0.25"):
        assert needle not in text, needle
    # the only thresholds an engine state may use are the train-only median
    assert "median" in (CODE_ROOT / "engine/score_calibration.py").read_text()
    assert [t for t in F.trial_policy["states"]] == ["UPPER_HALF", "LOWER_HALF"]


def test_acceptance_api_cannot_see_deciles_or_diagnostics():
    for fn in (classify_trial, decide_experiment):
        assert not any(w in " ".join(inspect.signature(fn).parameters) for w in ("decile", "diagnostic", "importance"))
    assert "decile" not in inspect.getsource(reg.recompute_campaign).lower()


def test_no_lockbox_evaluation_path():
    ap_src = (CODE_ROOT / "scripts/run_experiment.py").read_text()
    tree = ast.parse(ap_src)
    opts = [a.args[0].value for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "add_argument"
            for a in [n] if a.args]
    assert not any("lockbox" in o.lower() for o in opts), opts
    sig = inspect.signature(experiment_runner.run_experiment)
    assert not any("lockbox" in k for k in sig.parameters)
    assert "def confirm" not in (CODE_ROOT / "engine/experiment_runner.py").read_text()
    assert "not implemented" in (CODE_ROOT / "scripts/confirm_lockbox.py").read_text()


def test_final_lockbox_is_inaccessible_to_every_code_path():
    """oos_view (the widest view any stage gets) never contains a lockbox row; there is no lockbox view at all."""
    import pandas as pd
    idx = pd.date_range("2019-12-30", "2021-02-03", freq="1D", tz="UTC")
    bars = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}, index=idx)
    p = partitions.parse_partitions({"development_end": "2020-06-01", "oos_end": "2020-12-01", "lockbox_start": "2020-12-15"})
    assert not (partitions.oos_view(bars, p).index >= p.oos_end).any()
    assert not (partitions.development_view(bars, p).index >= p.development_end).any()
    assert "lockbox_view" not in dir(partitions) and not [n for n in dir(partitions) if "lockbox" in n.lower() and callable(getattr(partitions, n))]
    assert "not implemented" in (CODE_ROOT / "scripts/confirm_lockbox.py").read_text()


def test_scripts_and_engine_never_write_approval_files():
    """AGENTS.md rule 1: no code path creates anything in approvals/ (only reads it)."""
    for sub in ("engine", "scripts"):
        for pth in (CODE_ROOT / sub).glob("*.py"):
            src = pth.read_text()
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = getattr(node.func, "attr", getattr(node.func, "id", ""))
                    if name in ("write_text", "write_bytes", "open", "safe_dump", "dump", "copy", "copy2", "copyfile", "move"):
                        seg = ast.get_source_segment(src, node) or ""
                        assert "approval" not in seg.lower(), (pth.name, seg[:120])
    src = (CODE_ROOT / "engine/oos_stage.py").read_text()
    assert "approval_path(ws, experiment_id).write" not in src and "def write_approval" not in src and "def create_approval" not in src


def test_oos_requires_a_human_approval_gate_before_any_data_is_read():
    src = (CODE_ROOT / "scripts/run_oos.py").read_text()
    assert src.index("validate_approval") < src.index("load_bars_before")
    import inspect
    assert inspect.signature(oos_stage.run_oos).parameters.keys() == {"ws", "experiment_id", "bars", "verbose"}      # no skip-approval flag


def test_seeds_are_fixed_everywhere_no_unseeded_randomness():
    for p, tree in _sources():
        src = p.read_text()
        assert "np.random.seed" not in src and "random.random()" not in src, p
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "default_rng":
                assert node.args or node.keywords, (p, "default_rng() without a seed")
