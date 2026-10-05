"""Table-level synthetic scenarios with KNOWN structure through the real freeze -> DEVELOPMENT_CV (5 purged folds) ->
24 trials -> statistics -> acceptance -> registry -> IS report pipeline. Nothing in the frozen rules is adjusted per
scenario; if a gate failed, the planted effect (not the rule) is what a scenario changes.

Shortlist eligibility additionally needs externally verified model paths and the sensitivity verdict; those are injected
via the registry (see scenario_helpers) in the tests that demonstrate eligibility."""
import numpy as np
import pandas as pd
import pytest

from engine import trial_registry as reg
from engine.acceptance import (COND_IMPROVE, INSTAB, LOW_FREQ, LOW_UPLIFT, NO_CANDIDATE, PROVISIONAL, SHORTLIST)
from engine.common import load_frozen
from engine.synthetic import make_event_tables
from tests.scenario_helpers import pass_all_paths, pass_sensitivity, run_is_tables

F = load_frozen()
TARGETS = ["DIR_RETURN_15", "DIR_RETURN_180", "DIR_RETURN_60", "DIR_PATH_SKEW_60"]
CANDIDATE = {SHORTLIST, PROVISIONAL}


def run(tmp_path_factory, inject=False, **kw):
    ws = reg.Workspace(tmp_path_factory.mktemp("ws")).init()
    tables = make_event_tables(**kw)
    exp, trials, panels = run_is_tables(ws, tables)
    if inject:
        pass_all_paths(ws, exp)
        pass_sensitivity(ws, exp)
        trials = reg.experiment_trials(ws, exp)
    return ws, exp, trials, panels, tables


def q(trials, **cond):
    m = pd.Series(True, index=trials.index)
    for k, v in cond.items():
        m &= trials[k] == v
    return trials[m]


class TestNoSignal:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        return run(tmp_path_factory, inject=True, signal="none")

    def test_24_trials_no_candidate(self, res):
        ws, exp, t, panels, _ = res
        assert len(t) == 24 and not t["decision"].isin(CANDIDATE).any()
        assert (t["experiment_q"] > 0.05).all() and (t["campaign_q"] > 0.05).all() and (t["experiment_bonferroni_p"] > 0.05).all()
        assert (t["standardized_uplift"].abs() < 0.10).all()
        row = reg.experiment_row(ws, exp)
        assert row["is_status"] == NO_CANDIDATE and row["status"] == "IS_REJECTED"
        assert reg.integrity_check(ws)["selection_trials"] == 24

    def test_every_trial_is_shown_with_its_numbers(self, res):
        _, _, t, _, _ = res
        for c in ("parent_frequency", "selected_frequency", "retention_ratio", "parent_effect", "selected_effect", "uplift",
                  "standardized_uplift", "bootstrap_ci_low", "bootstrap_ci_high", "raw_p", "experiment_bonferroni_p",
                  "campaign_bonferroni_p", "selection_opportunity_number"):
            assert t[c].notna().all(), c
        assert (t["decision"] != "PENDING").all() and (t["folds_evaluated"] == 5).all()


class TestLinearEdge:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        return run(tmp_path_factory, signal="linear", slope=0.35)

    def test_before_verification_the_groups_are_only_provisional_never_eligible(self, res):
        ws, exp, *_ = res
        t = reg.experiment_trials(ws, exp)                                # fixture ran WITHOUT verification / sensitivity verdicts
        assert not t["decision"].eq(SHORTLIST).any() and t["decision"].eq(PROVISIONAL).all()
        assert "verification" in t["rejection_reason"].iloc[0] and "sensitivity" in t["rejection_reason"].iloc[0]
        assert reg.experiment_row(ws, exp)["is_status"] == PROVISIONAL and reg.experiment_row(ws, exp)["status"] == "IS_PROVISIONAL_CANDIDATE"

    def test_all_models_eligible_on_every_target_once_paths_are_verified(self, res):
        ws, exp, *_ = res
        pass_all_paths(ws, exp); pass_sensitivity(ws, exp)
        t = reg.experiment_trials(ws, exp)
        for target in TARGETS:
            for state in ("UPPER_HALF", "LOWER_HALF"):
                g = q(t, target=target, state=state)
                assert len(g) == 3 and (g["decision"] == SHORTLIST).all(), (target, state, g["decision"].tolist())
                assert (g["standardized_uplift"] >= 0.10).all() and (g["selected_frequency"] >= 1.0).all()
                assert (g["selected_effect"] > 0).all() and (g["bootstrap_ci_low"] > 0).all()
                assert (g["positive_years"] >= 0.7 * g["eligible_years"]).all() and (g["positive_uplift_years"] >= 0.7 * g["eligible_years"]).all()
                assert (g["positive_effect_folds"] >= 4).all() and (g["positive_uplift_folds"] >= 4).all() and (g["folds_evaluated"] == 5).all()
        assert reg.experiment_row(ws, exp)["is_status"] == SHORTLIST
        assert reg.experiment_row(ws, exp)["status"] == "AWAITING_HUMAN_FINAL_CONFIG_SELECTION"

    def test_effect_size_matches_planted_truth(self, res):
        # planted: y = 0.35*z + N(0,1). Upper half of a good score has E[y|upper] ~ 0.35*0.8 = 0.28; sd ~ 1.06
        _, _, t, _, _ = res
        r = q(t, target="DIR_RETURN_180", model="RIDGE", state="UPPER_HALF").iloc[0]
        assert 0.15 < r["standardized_uplift"] < 0.32 and 0.15 < r["selected_effect"] < 0.40


class TestNonlinearEdge:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        return run(tmp_path_factory, inject=True, signal="nonlinear", slope=0.35)

    def test_nonlinear_models_detect_a_u_shape_ridge_cannot(self, res):
        _, _, t, _, _ = res
        for target in TARGETS:
            for state in ("UPPER_HALF", "LOWER_HALF"):
                for model in ("SPLINE", "XGB"):
                    r = q(t, target=target, state=state, model=model).iloc[0]
                    assert r["decision"] == SHORTLIST, (target, state, model)
                    assert r["standardized_uplift"] > 0.10
                ridge = q(t, target=target, state=state, model="RIDGE").iloc[0]
                assert ridge["standardized_uplift"] < 0.10 and ridge["decision"] == LOW_UPLIFT

    def test_promotion_is_at_target_side_level_with_all_models_still_shown(self, res):
        _, _, t, _, _ = res
        g = q(t, target="DIR_RETURN_180", state="UPPER_HALF")
        assert sorted(g["model"]) == ["RIDGE", "SPLINE", "XGB"] and (g["decision"] != "PENDING").all()
        assert (g["decision"] == SHORTLIST).sum() == 2                 # exactly the 2-of-3 that pass


class TestLowFrequencyNonPromotable:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        return run(tmp_path_factory, inject=True, signal="linear", slope=0.6, events_per_week=1.6, years=range(2011, 2023))

    def test_strong_but_low_frequency_is_documented_not_promoted(self, res):
        ws, exp, t, panels, _ = res
        assert not t["decision"].isin(CANDIDATE).any() and (t["decision"] == LOW_FREQ).all()
        assert (t["selected_frequency"] < 1.0).all() and (t["parent_frequency"] < 2.0).all()
        assert (t["standardized_uplift"] > 0.15).all() and (t["experiment_q"] < 0.05).all()   # the effect is real but unusable
        assert t["rejection_reason"].str.contains("selected frequency").all()
        assert (t["folds_evaluated"] < 5).all()                                                # 969 events: early folds lack 300 training events (reported, no longer a gate)
        assert not t["rejection_reason"].str.contains("FOLD_EVIDENCE").any()                    # v2.1: the fold gate is gone; the frequency floor alone rejects these

    def test_low_frequency_leads_are_preserved_as_observations(self, res):
        ws, *_ = res
        obs = reg.read_observations(ws)
        assert (obs["category"] == "low_frequency_state").sum() == 24 and (obs["eligible_for_promotion"] == "False").all()

    def test_base_frequency_flag_logic(self):
        from engine.experiment_runner import BASE_FREQ_FLAG, base_frequency_flag
        assert base_frequency_flag(199, 100, F) == BASE_FREQ_FLAG            # 1.99/week -> flagged (still reported/run)
        assert base_frequency_flag(200, 100, F) == ""                        # 2.00/week -> not flagged
        assert base_frequency_flag(10, 0, F) == BASE_FREQ_FLAG
        assert F.trial_policy["states"] == ["UPPER_HALF", "LOWER_HALF"]      # the 50% state is never changed to rescue it


class TestSpuriousTail:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        return run(tmp_path_factory, inject=True, signal="tail", tail_threshold=1.9, tail_shift=1.5)

    def test_tail_effect_visible_in_deciles_but_cannot_promote(self, res):
        ws, exp, t, panels, _ = res
        assert not t["decision"].isin(CANDIDATE).any()
        dec = panels[("DIR_RETURN_180", "XGB")].deciles["deciles"]
        assert len(dec) == 10 and dec[-1]["mean_target"] > dec[0]["mean_target"] + 0.05      # visible as a diagnostic...
        assert len(t) == 24 and (t["standardized_uplift"] < 0.10).all()                       # ...but adds no selection trial

    def test_tail_observation_is_registered_as_non_promotable(self, res):
        ws, exp, t, panels, _ = res
        obs = reg.read_observations(ws)
        assert len(obs) > 0 and (obs["experiment_id"] == exp).all() and (obs["eligible_for_promotion"] == "False").all()
        assert "score_decile_shape" in set(obs["category"])
        assert (obs["diagnostic_label"] == "DIAGNOSTIC ONLY — NOT A SELECTION TRIAL").all()
        assert not reg.experiment_trials(ws, exp)["decision"].isin(CANDIDATE).any()


class TestFrequencyDestroyingWeakFilter:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        return run(tmp_path_factory, inject=True, signal="linear", slope=0.006, drift=0.041, events_per_week=4.3)

    def test_trivial_uplift_is_rejected_even_above_one_per_week(self, res):
        _, _, t, _, _ = res
        assert not t["decision"].isin(CANDIDATE).any() and (t["decision"] == LOW_UPLIFT).all()
        assert (t["selected_frequency"] >= 1.0).all() and (t["selected_frequency"] < t["parent_frequency"]).all()
        assert ((t["retention_ratio"] > 0.35) & (t["retention_ratio"] < 0.65)).all()
        assert (t["standardized_uplift"].abs() < 0.10).all()
        assert t["rejection_reason"].str.contains("REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS").all()

    def test_parent_effect_reflects_the_planted_drift(self, res):
        _, _, t, _, _ = res
        u = q(t, state="UPPER_HALF")
        assert abs(u["parent_effect"].mean() - 0.041) < 0.04            # 4 independent noise draws


class TestUnstableSignal:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        slopes = {2015: 1.0, 2016: 1.0, 2017: 1.0, 2018: 1.0, 2019: -0.25, 2020: -0.25, 2021: -0.25, 2022: -0.25}
        return run(tmp_path_factory, inject=True, signal="linear", slope=0.0, slope_by_year=slopes)

    def test_strong_pooled_effect_is_rejected_for_instability_only(self, res):
        _, _, t, _, _ = res
        assert not t["decision"].isin(CANDIDATE).any() and (t["decision"] == INSTAB).all()
        # every OTHER gate passes, so consistency alone blocks eligibility
        assert (t["selected_frequency"] >= 1).all() and (t["standardized_uplift"] >= 0.10).all() and (t["selected_effect"] > 0).all()
        assert (t["bootstrap_ci_low"] > 0).all() and (t["experiment_q"] <= 0.05).all() and (t["campaign_q"] <= 0.05).all()
        assert (t["experiment_bonferroni_p"] <= 0.05).all() and (t["campaign_bonferroni_p"] <= 0.05).all()
        weak_years = (t["positive_years"] / t["eligible_years"] < 0.70) | (t["positive_uplift_years"] / t["eligible_years"] < 0.70)
        weak_folds = (t["positive_uplift_folds"] < 4) | (t["positive_effect_folds"] < 4)
        assert (weak_years | weak_folds).all()


class TestConditionalImprovementIsNotACandidate:
    """Parent effect strongly negative: the UPPER state is 'less bad' (big uplift, negative absolute effect) and must not be a
    candidate; the opposite (fade) side genuinely earns a positive absolute effect."""

    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        return run(tmp_path_factory, inject=True, signal="linear", slope=0.35, drift=-0.45)

    def test_less_bad_than_parent_is_diagnostic_only(self, res):
        ws, exp, t, panels, _ = res
        up = q(t, state="UPPER_HALF")
        assert (up["decision"] == COND_IMPROVE).all()
        assert (up["standardized_uplift"] >= 0.10).all() and (up["selected_effect"] < 0).all() and (up["parent_effect"] < up["selected_effect"]).all()
        assert up["rejection_reason"].str.contains("less bad than the parent").all()
        lo = q(t, state="LOWER_HALF")
        assert (lo["decision"] == SHORTLIST).all() and (lo["selected_effect"] > 0).all()        # the genuine candidate is the fade side

    def test_conditional_improvement_is_reported_not_discarded(self, res):
        ws, exp, t, *_ = res
        obs = reg.read_observations(ws)
        assert (obs["category"] == "conditional_improvement").sum() == 12
