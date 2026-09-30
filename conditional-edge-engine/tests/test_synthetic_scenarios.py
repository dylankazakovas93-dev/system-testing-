"""Table-level synthetic scenarios with KNOWN structure, pushed through the real freeze -> walk-forward ->
24-trial -> statistics -> acceptance -> registry pipeline. Nothing in the frozen rules is adjusted per scenario."""
import numpy as np
import pandas as pd
import pytest

from engine import trial_registry as reg
from engine.common import load_frozen
from engine.experiment_runner import derive_observations
from engine.synthetic import make_event_tables
from tests.scenario_helpers import run_scenario

F = load_frozen()
PROMOTED = {"PROMOTABLE", "PROMOTABLE_PENDING_SENSITIVITY"}
TARGETS = ["DIR_RETURN_15", "DIR_RETURN_30", "DIR_RETURN_60", "DIR_PATH_SKEW_60"]


def run(tmp_path_factory, **kw):
    ws = reg.Workspace(tmp_path_factory.mktemp("ws")).init()
    tables = make_event_tables(**kw)
    exp, trials, panels = run_scenario(ws, tables)
    return ws, exp, trials, panels, tables


def q(trials, **cond):
    m = pd.Series(True, index=trials.index)
    for k, v in cond.items():
        m &= trials[k] == v
    return trials[m]


class TestNoSignal:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        return run(tmp_path_factory, signal="none")

    def test_24_trials_no_candidate(self, res):
        ws, exp, t, panels, _ = res
        assert len(t) == 24 and not t["decision"].isin(PROMOTED).any()
        assert (t["experiment_q"] > 0.05).all() and (t["campaign_q"] > 0.05).all()
        assert (t["standardized_uplift"].abs() < 0.10).all()
        assert reg.integrity_check(ws)["selection_trials"] == 24

    def test_every_trial_is_shown_with_its_numbers(self, res):
        _, _, t, _, _ = res
        for c in ("parent_frequency", "selected_frequency", "retention_ratio", "parent_effect", "selected_effect",
                  "uplift", "standardized_uplift", "bootstrap_ci_low", "bootstrap_ci_high", "raw_p"):
            assert t[c].notna().all(), c
        assert (t["decision"] != "PENDING").all()


class TestLinearEdge:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        return run(tmp_path_factory, signal="linear", slope=0.35)

    def test_ridge_and_other_models_detect_it_oos_on_every_target(self, res):
        _, _, t, _, _ = res
        for target in TARGETS:
            for state in ("UPPER_HALF", "LOWER_HALF"):
                g = q(t, target=target, state=state)
                assert len(g) == 3
                assert (g["decision"] == "PROMOTABLE_PENDING_SENSITIVITY").all(), (target, state, g["decision"].tolist())
                assert (g["standardized_uplift"] >= 0.10).all() and (g["selected_frequency"] >= 1.0).all()
                assert (g["bootstrap_ci_low"] > 0).all() and (g["positive_years"] == g["eligible_years"]).all()
        assert q(t, model="RIDGE")["decision"].isin(PROMOTED).all()

    def test_effect_size_matches_planted_truth(self, res):
        # planted: y = 0.35*z + N(0,1). Upper half of a good score has E[y|upper] ~ 0.35*0.8 = 0.28; sd ~ 1.06
        _, _, t, _, _ = res
        r = q(t, target="DIR_RETURN_30", model="RIDGE", state="UPPER_HALF").iloc[0]
        assert 0.18 < r["standardized_uplift"] < 0.32


class TestNonlinearEdge:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        return run(tmp_path_factory, signal="nonlinear", slope=0.35)

    def test_nonlinear_models_detect_a_u_shape_ridge_cannot(self, res):
        _, _, t, _, _ = res
        for target in TARGETS:
            for state in ("UPPER_HALF", "LOWER_HALF"):
                for model in ("SPLINE", "XGB"):
                    r = q(t, target=target, state=state, model=model).iloc[0]
                    assert r["decision"] == "PROMOTABLE_PENDING_SENSITIVITY", (target, state, model)
                    assert r["standardized_uplift"] > 0.10
                ridge = q(t, target=target, state=state, model="RIDGE").iloc[0]
                assert ridge["standardized_uplift"] < 0.10 and ridge["decision"] == "REJECTED_INSUFFICIENT_UPLIFT"

    def test_promotion_is_at_target_side_level_with_all_models_still_shown(self, res):
        _, _, t, _, _ = res
        g = q(t, target="DIR_RETURN_30", state="UPPER_HALF")
        assert sorted(g["model"]) == ["RIDGE", "SPLINE", "XGB"]
        assert (g["decision"] != "PENDING").all()
        assert g["decision"].isin(PROMOTED).sum() == 2                 # exactly the 2-of-3 that pass


class TestLowFrequencyNonPromotable:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        return run(tmp_path_factory, signal="linear", slope=0.6, events_per_week=1.6, years=range(2011, 2023))

    def test_strong_but_low_frequency_is_documented_not_promoted(self, res):
        ws, exp, t, panels, _ = res
        assert not t["decision"].isin(PROMOTED).any()
        assert (t["decision"] == "REJECTED_LOW_FREQUENCY").all()
        assert (t["selected_frequency"] < 1.0).all() and (t["parent_frequency"] < 2.0).all()
        assert (t["standardized_uplift"] > 0.20).all() and (t["experiment_q"] < 0.05).all()   # the effect is real but unusable
        assert t["rejection_reason"].str.contains("selected frequency").all()

    def test_low_frequency_leads_are_preserved_as_observations(self, res):
        ws, exp, t, panels, _ = res
        obs = derive_observations(panels, t, F)
        assert sum(1 for o in obs if o[0] == "low_frequency_state") == 24

    def test_base_frequency_flag_logic(self, res):
        from engine.experiment_runner import BASE_FREQ_FLAG, base_frequency_flag
        assert base_frequency_flag(199, 100, F) == BASE_FREQ_FLAG            # 1.99/week -> flagged (still reported/run)
        assert base_frequency_flag(200, 100, F) == ""                        # 2.00/week -> not flagged
        assert base_frequency_flag(10, 0, F) == BASE_FREQ_FLAG
        ws, exp, t, panels, (events, *_rest) = res                           # this scenario's base event is ~1.6/week
        weeks = 12 * 52
        assert base_frequency_flag(len(events), weeks, F) == BASE_FREQ_FLAG
        assert F.trial_policy["states"] == ["UPPER_HALF", "LOWER_HALF"]      # the 50% state is never changed to rescue it


class TestSpuriousTail:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        return run(tmp_path_factory, signal="tail", tail_threshold=1.9, tail_shift=1.5)

    def test_tail_effect_visible_in_deciles_but_cannot_promote(self, res):
        ws, exp, t, panels, _ = res
        assert not t["decision"].isin(PROMOTED).any()
        dec = panels[("DIR_RETURN_30", "XGB")].deciles["deciles"]
        assert len(dec) == 10
        assert dec[-1]["mean_target"] > dec[0]["mean_target"] + 0.05            # the tail is visible as a diagnostic...
        assert reg.trial_specs(F) and len(t) == 24                              # ...but adds no selection trial
        assert (t["standardized_uplift"] < 0.10).all()

    def test_tail_observation_is_registered_as_non_promotable(self, res):
        ws, exp, t, panels, _ = res
        for cat, desc, name, val in derive_observations(panels, t, F):
            reg.add_observation(ws, exp, cat, desc, name, val)
        obs = reg.read_observations(ws)
        assert (obs["experiment_id"] == exp).all() and len(obs) > 0
        assert (obs["eligible_for_promotion"] == "False").all()
        assert "score_decile_shape" in set(obs["category"])
        assert not reg.experiment_trials(ws, exp)["decision"].isin(PROMOTED).any()     # observations changed nothing


class TestFrequencyDestroyingWeakFilter:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        return run(tmp_path_factory, signal="linear", slope=0.006, drift=0.041, events_per_week=4.3)

    def test_trivial_uplift_is_rejected_even_above_one_per_week(self, res):
        _, _, t, _, _ = res
        assert not t["decision"].isin(PROMOTED).any()
        assert (t["decision"] == "REJECTED_INSUFFICIENT_UPLIFT").all()
        assert (t["selected_frequency"] >= 1.0).all()                            # frequency floor alone would pass
        assert (t["selected_frequency"] < t["parent_frequency"]).all()
        assert ((t["retention_ratio"] > 0.35) & (t["retention_ratio"] < 0.65)).all()
        assert (t["standardized_uplift"].abs() < 0.10).all()
        assert t["rejection_reason"].str.contains("REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS").all()

    def test_parent_effect_reflects_the_planted_drift(self, res):
        _, _, t, _, _ = res
        u = q(t, state="UPPER_HALF")
        assert abs(u["parent_effect"].mean() - 0.041) < 0.04            # 4 independent noise draws, SE ~0.012 each


class TestUnstableSignal:
    @pytest.fixture(scope="class")
    def res(self, tmp_path_factory):
        slopes = {2015: 1.0, 2016: 1.0, 2017: 1.0, 2018: 1.0, 2019: -0.25, 2020: -0.25, 2021: -0.25, 2022: -0.25}
        return run(tmp_path_factory, signal="linear", slope=0.0, slope_by_year=slopes)

    def test_strong_pooled_effect_is_rejected_for_instability_only(self, res):
        _, _, t, _, _ = res
        assert not t["decision"].isin(PROMOTED).any()
        assert (t["decision"] == "REJECTED_INSTABILITY").all()
        # every OTHER gate passes, so stability alone is what blocks promotion
        assert (t["selected_frequency"] >= 1).all() and (t["standardized_uplift"] >= 0.10).all()
        assert (t["bootstrap_ci_low"] > 0).all() and (t["experiment_q"] <= 0.05).all() and (t["campaign_q"] <= 0.05).all()
        assert (t["positive_years"] / t["eligible_years"] < 0.70).all()


# ------------------------- multiplicity through the registry (fast, crafted p-values) -------------------
def fake_results(ws, exp, p_by_pair, default_p=0.9, good=True):
    trials = reg.experiment_trials(ws, exp)
    out = {}
    for _, r in trials.iterrows():
        p = p_by_pair.get((r["target"], r["model"]), default_p)
        out[r["trial_id"]] = dict(n_parent=2000, n_selected=1000, parent_frequency=4.0, selected_frequency=2.0,
                                  retention_ratio=0.5, parent_effect=0.0, selected_effect=0.2, uplift=0.2, target_sd=1.0,
                                  standardized_uplift=0.2 if good else 0.0, bootstrap_ci_low=0.05, bootstrap_ci_high=0.3,
                                  raw_p=p, positive_years=5, eligible_years=5, n_oos_weeks=500.0)
    return out


def test_experiment_bh_spans_all_24_trials_not_just_winners(tmp_path):
    from engine.multiplicity import benjamini_hochberg
    from tests.scenario_helpers import new_frozen_experiment
    ws = reg.Workspace(tmp_path / "w").init()
    exp = new_frozen_experiment(ws)
    p = {("DIR_RETURN_30", "RIDGE"): 0.002, ("DIR_RETURN_30", "XGB"): 0.004}
    res = fake_results(ws, exp, p, default_p=0.5)
    reg.reveal_experiment(ws, exp, res, train_period="a", oos_period="b", frozen=F)
    t = reg.experiment_trials(ws, exp)
    manual = benjamini_hochberg([res[i]["raw_p"] for i in t["trial_id"]])
    assert np.allclose(t["experiment_q"].to_numpy(), manual)
    winners_only = benjamini_hochberg([0.002, 0.002, 0.004, 0.004])            # what a winners-only correction would give
    assert t["experiment_q"].min() > winners_only.min() * 2                    # the honest m=24 correction is harsher
    assert len(manual) == 24


def test_campaign_bh_includes_prior_experiments_and_can_downgrade_them(tmp_path):
    from engine.multiplicity import benjamini_hochberg
    from tests.scenario_helpers import new_frozen_experiment
    ws = reg.Workspace(tmp_path / "w").init()
    e1 = new_frozen_experiment(ws)
    pairs = {("DIR_RETURN_30", "RIDGE"): 0.006, ("DIR_RETURN_30", "XGB"): 0.006}
    r1 = fake_results(ws, e1, pairs, default_p=0.9)
    reg.reveal_experiment(ws, e1, r1, train_period="a", oos_period="b", frozen=F)
    t1 = reg.experiment_trials(ws, e1)
    sel = t1[(t1["target"] == "DIR_RETURN_30") & (t1["model"].isin(["RIDGE", "XGB"]))]
    assert (sel["experiment_q"] <= 0.05).all() and (sel["campaign_q"] <= 0.05).all()
    assert set(sel["decision"]) == {"PROMOTABLE_PENDING_SENSITIVITY"}            # alone in the campaign it passes
    e2 = new_frozen_experiment(ws)                                                 # same campaign, nothing significant
    r2 = fake_results(ws, e2, {}, default_p=0.9, good=False)
    reg.reveal_experiment(ws, e2, r2, train_period="a", oos_period="b", frozen=F)
    t1b = reg.experiment_trials(ws, e1)
    all_p = [r1[i]["raw_p"] for i in t1["trial_id"]] + [r2[i]["raw_p"] for i in reg.experiment_trials(ws, e2)["trial_id"]]
    manual = benjamini_hochberg(all_p)
    assert np.allclose(t1b["campaign_q"].to_numpy(), manual[:24])                  # BH over all 48 revealed trials
    sel_b = t1b[(t1b["target"] == "DIR_RETURN_30") & (t1b["model"].isin(["RIDGE", "XGB"]))]
    assert (sel_b["experiment_q"] <= 0.05).all() and (sel_b["campaign_q"] > 0.05).all()
    assert set(sel_b["decision"]) == {"REJECTED_STATISTICAL"}                      # campaign_q now blocks it
    assert "campaign_q" in sel_b["rejection_reason"].iloc[0]
    assert reg.integrity_check(ws)["revealed_trials"] == 48
