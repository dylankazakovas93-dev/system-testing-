"""Fixed CPCV mechanics (6 chronological groups, 2 held out, 15 splits, purge, embargo, train-only fits) and the informational selection-holdout
evidence gates. Frozen mechanics: none of these were changed by the v1.2 lifecycle patch."""
import numpy as np
import pandas as pd
import pytest

from engine import cpcv as C
from engine import trial_registry as reg
from engine.common import load_frozen
from engine.selection_holdout_stage import group_verdicts, selection_holdout_evaluations

F = load_frozen()


def test_cpcv_generates_exactly_15_splits_with_no_search_over_n_or_k():
    splits = C.cpcv_split_ids(6, 2)
    assert len(splits) == 15 == F.trial_policy["cpcv"]["n_splits"] and len(set(splits)) == 15
    assert all(len(s) == 2 and s == tuple(sorted(s)) for s in splits)
    assert splits[0] == (0, 1) and splits[-1] == (4, 5)                                            # deterministic order, no shuffling
    from collections import Counter
    assert set(Counter(g for s in splits for g in s).values()) == {5}                              # every group is held out in exactly 5 splits
    assert (F.trial_policy["cpcv"]["n_groups"], F.trial_policy["cpcv"]["n_test_groups"]) == (6, 2)


def test_cpcv_groups_are_chronological_equal_count_and_whole_trading_days():
    t = pd.date_range("2018-01-02 15:00", periods=1200, freq="45min", tz="UTC")
    t = t[(t.tz_convert("America/New_York").hour >= 9) & (t.tz_convert("America/New_York").hour < 16)]
    regions = C.cpcv_groups(t, 6, "America/New_York")
    assert len(regions) == 6
    ns = t.as_unit("ns").asi8
    sizes = [int(((ns >= lo) & (ns < hi)).sum()) for lo, hi in regions]
    assert sum(sizes) == len(t) and max(sizes) - min(sizes) <= len(t) // 6 * 0.35 + 8              # ~equal event counts
    for (a, b), (c, d) in zip(regions[:-1], regions[1:]):
        assert b == c and a < b                                                                      # contiguous, chronological
    for lo, _ in regions[1:]:
        loc = pd.Timestamp(lo, tz="UTC").tz_convert("America/New_York")
        assert (loc.hour, loc.minute) == (0, 0)                                                      # boundaries are trading-day starts


def _day(n):
    return int(pd.Timestamp("2019-01-01", tz="UTC").value) + n * 24 * 3600 * 10**9


def test_cpcv_purges_training_events_whose_label_windows_overlap_a_held_out_region():
    hour = 3600 * 10**9
    regions = [(_day(10), _day(20)), (_day(40), _day(50))]                      # two held-out groups
    ev = np.array([_day(9), _day(9) + 23 * hour, _day(5), _day(21), _day(30), _day(39), _day(60)], dtype=np.int64)
    eff = ev + np.array([2 * hour, 2 * hour, 2 * hour, 1 * hour, 1 * hour, 2 * 24 * hour, 1 * hour], dtype=np.int64)
    # event[0]: day 9 00:00, label ends day 9 02:00 (before region) -> kept ; event[1]: day 9 23:00 label ends day 10 01:00 -> OVERLAP -> purged
    # event[5]: day 39 label ends day 41 -> overlaps region 2 -> purged
    train, test = C.split_masks(ev, eff, regions, embargo_ns=0)
    assert train.tolist() == [True, False, True, True, True, False, True] and not test.any()
    ev2 = np.array([_day(12), _day(45)], dtype=np.int64)
    tr2, te2 = C.split_masks(np.r_[ev, ev2], np.r_[eff, ev2 + hour], regions, embargo_ns=0)
    assert te2[-2:].all() and not tr2[-2:].any()                                  # events inside a held-out region are TEST, never train


def test_cpcv_embargo_is_applied_at_every_held_out_boundary_on_both_sides():
    emb = 180 * 60 * 10**9                                                        # 180 bars of information time (max primary horizon)
    from engine.target_engine import max_primary_horizon_bars
    assert emb == max_primary_horizon_bars(F) * int(F.interval.value)
    regions = [(_day(10), _day(20)), (_day(40), _day(50))]
    minute = 60 * 10**9
    probes = {"before_r1_inside_embargo": _day(10) - 90 * minute, "before_r1_outside": _day(10) - 181 * minute,
              "after_r1_inside_embargo": _day(20) + 90 * minute, "after_r1_outside": _day(20) + 181 * minute,
              "before_r2_inside_embargo": _day(40) - 179 * minute, "before_r2_outside": _day(40) - 181 * minute,
              "after_r2_inside_embargo": _day(50) + 179 * minute, "after_r2_outside": _day(50) + 181 * minute,
              "far": _day(30)}
    ev = np.array(list(probes.values()), dtype=np.int64)
    eff = ev + 1                                                                   # tiny labels: only the embargo can remove them
    train, _ = C.split_masks(ev, eff, regions, embargo_ns=emb)
    kept = dict(zip(probes, train.tolist()))
    for k in ("before_r1_inside_embargo", "after_r1_inside_embargo", "before_r2_inside_embargo", "after_r2_inside_embargo"):
        assert kept[k] is False, k                                                 # embargoed at EVERY boundary (4 boundaries)
    for k in ("before_r1_outside", "after_r1_outside", "before_r2_outside", "after_r2_outside", "far"):
        assert kept[k] is True, k


def test_cpcv_pass_rule_thresholds_are_exactly_12_of_15_and_positive_medians():
    rule = F.acceptance["cpcv"]
    def recs(n_pos_eff, n_pos_up, eff_pos=0.2, eff_neg=-0.05, n=15):
        return [{"split": i, "valid": True, "selected_effect": eff_pos if i < n_pos_eff else eff_neg,
                 "uplift": 0.1 if i < n_pos_up else -0.02} for i in range(n)]
    assert C.pass_rule(recs(15, 15), rule)["cpcv_pass"]
    assert C.pass_rule(recs(12, 12), rule)["cpcv_pass"]                              # 12/15 is the floor
    assert not C.pass_rule(recs(11, 15), rule)["cpcv_pass"] and not C.pass_rule(recs(15, 11), rule)["cpcv_pass"]
    bad_median = [{"split": i, "valid": True, "selected_effect": 5.0 if i < 12 else -50.0, "uplift": 0.1} for i in range(15)]
    assert C.pass_rule(bad_median, rule)["n_effect_positive"] == 12
    neg_med = [{"split": i, "valid": True, "selected_effect": -0.01 if i < 8 else 0.2, "uplift": 0.1} for i in range(15)]
    assert not C.pass_rule(neg_med, rule)["cpcv_pass"]
    few = recs(15, 15)[:14] + [{"split": 14, "valid": False, "selected_effect": float("nan"), "uplift": float("nan")}]
    assert not C.pass_rule(few, rule)["cpcv_pass"]                                   # an invalid split can never be waived
    s = C.pass_rule(recs(13, 14), rule)
    assert s["fraction_effect_positive"] == pytest.approx(13 / 15) and s["fraction_uplift_positive"] == pytest.approx(14 / 15)
    assert {"median_effect", "median_uplift", "p10_uplift", "p90_uplift", "worst_split", "best_split"} <= set(s)


def test_pbo_not_applicable_for_one_candidate_and_computed_from_rank_reversals():
    one = C.pbo_diagnostic({"a": np.array([0.1] * 6)}, C.cpcv_split_ids(6, 2), 6)
    assert one["pbo"] is None and one["status"] == "NOT APPLICABLE"
    splits = C.cpcv_split_ids(6, 2)
    # config A is uniformly better than B in every group -> the best IS config is always the best holdout config -> PBO = 0
    stable = C.pbo_diagnostic({"A": np.full(6, 0.3), "B": np.full(6, 0.1), "C": np.full(6, -0.1)}, splits, 6)
    assert stable["status"] == "COMPUTED" and stable["pbo"] == 0.0
    # anti-persistent configs: whichever is best in training groups is WORST in the held-out groups -> PBO high
    rng = np.random.default_rng(0)
    base = rng.normal(size=6)
    anti = C.pbo_diagnostic({"A": base, "B": -base}, splits, 6)
    assert anti["pbo"] >= 0.5 and len(anti["logits"]) == 15
    assert "not an independent p-value" in anti["note"]


def test_pbo_diagnostic_cannot_influence_verdicts_or_ranking(monkeypatch):
    import inspect
    from engine import acceptance
    src_reg = inspect.getsource(reg)
    assert "pbo" not in inspect.getsource(acceptance).lower() and "pbo" not in src_reg.replace("pbo_diagnostic", "").lower().replace("cpcv_cols", "")
    # computed AFTER and apart from every verdict: swapping it for garbage cannot change a verdict
    from engine.synthetic import make_event_tables
    tables = make_event_tables(years=range(2015, 2021), events_per_week=6, signal="linear", slope=0.4, seed=3)
    events, features, eligible, targets, calendar = tables
    groups = ["DIR_RETURN_180|UPPER_HALF"]
    a = C.run_cpcv_tables(events, features, targets, eligible, calendar, groups, F, models=["RIDGE"])
    monkeypatch.setattr(C, "pbo_diagnostic", lambda *x, **k: {"pbo": 0.999, "status": "COMPUTED", "n_configs": 99})
    b = C.run_cpcv_tables(events, features, targets, eligible, calendar, groups, F, models=["RIDGE"])
    assert a["group_verdicts"] == b["group_verdicts"] and a["summary"] == b["summary"] and a["pbo"]["pbo"] != b["pbo"]["pbo"]


class _Probe:
    """Fast deterministic stand-in model that records exactly which rows it was fitted on."""
    log: list = []

    def __init__(self):
        pass

    def fit(self, X, y):
        _Probe.log.append(("fit", X.index.to_numpy().copy(), np.asarray(y).copy()))
        x = X["ER_60"].to_numpy()
        self.b = float(np.dot(x - x.mean(), y - y.mean()) / np.dot(x - x.mean(), x - x.mean()))
        self.mx, self.my = float(x.mean()), float(y.mean())
        return self

    def predict(self, X):
        return self.my + self.b * (X["ER_60"].to_numpy() - self.mx)


def test_cpcv_fits_are_train_only_purged_embargoed_and_use_no_global_statistics():
    from engine.synthetic import make_event_tables
    events, features, eligible, targets, calendar = make_event_tables(years=range(2015, 2021), events_per_week=8, signal="linear", slope=0.4, seed=5)
    _Probe.log = []
    res = C.run_cpcv_tables(events, features, targets, eligible, calendar, ["DIR_RETURN_60|UPPER_HALF"], F, models=["RIDGE"],
                            factory=lambda m: _Probe)
    ev = events.sort_values(["event_time", "event_id"]).reset_index(drop=True)
    ev_ns = ev["event_time"].astype("int64").to_numpy() if ev["event_time"].dt.unit == "ns" else ev["event_time"].dt.as_unit("ns").astype("int64").to_numpy()
    tdf = targets["DIR_RETURN_60"].set_index("event_id").loc[ev["event_id"]]
    eff = pd.DatetimeIndex(tdf["effective_target_end"]).as_unit("ns").asi8
    recs = res["records"][("DIR_RETURN_60", "UPPER_HALF", "RIDGE")]
    assert len(recs) == 15 and all(r["valid"] for r in recs)
    from engine.target_engine import max_primary_horizon_bars
    emb = max_primary_horizon_bars(F) * int(F.interval.value)
    # every FINAL fit of a split used exactly the legal training rows of that split (the other fits are inner OOF fits)
    finals = [l for l in _Probe.log if len(l[1]) in {r["n_train"] for r in recs}]
    for r in recs:
        tr, te = C.split_masks(ev_ns, eff, [res["regions"][k] for k in r["test_groups"]], emb)
        assert r["n_train"] == int(tr.sum()) and r["n_test"] == int(te.sum())
        assert not (tr & te).any()
        assert any(np.array_equal(l[1], np.flatnonzero(tr)) for l in finals), r["split"]       # fitted on exactly these rows
    # nothing is carried between splits: mutating ONLY test-region labels/features leaves every split's training threshold unchanged
    f2, t2 = features.copy(), {k: v.copy() for k, v in targets.items()}
    r0 = res["regions"][recs[0]["test_groups"][0]]
    in_test = ((events["event_time"].dt.as_unit("ns").astype("int64") >= r0[0]) & (events["event_time"].dt.as_unit("ns").astype("int64") < r0[1])).to_numpy()
    t2["DIR_RETURN_60"].loc[in_test, "value"] = 1e6
    f2.loc[in_test, "ER_60"] = 1e6
    res2 = C.run_cpcv_tables(events, f2, t2, eligible, calendar, ["DIR_RETURN_60|UPPER_HALF"], F, models=["RIDGE"])
    res1 = C.run_cpcv_tables(events, features, targets, eligible, calendar, ["DIR_RETURN_60|UPPER_HALF"], F, models=["RIDGE"])
    k = ("DIR_RETURN_60", "UPPER_HALF", "RIDGE")
    g0 = recs[0]["test_groups"][0]
    held_out_thr, trained_on_thr = [], []
    for a, b, sp in zip(res1["records"][k], res2["records"][k], res["splits"]):
        (held_out_thr if g0 in sp else trained_on_thr).append((a["threshold"], b["threshold"]))
    assert len(held_out_thr) == 5 and len(trained_on_thr) == 10                       # each group is held out in exactly 5 of 15 splits
    # splits that HOLD OUT the mutated group never saw those rows in training: identical thresholds
    assert all(x == y for x, y in held_out_thr), held_out_thr
    # control: splits that TRAIN on the mutated rows must react (otherwise the mutation proves nothing)
    assert any(x != y for x, y in trained_on_thr)


def test_selection_holdout_evidence_gates_and_group_rule_unit():
    rule = F.acceptance["selection_holdout_evidence"]
    def row(model, group="G|U", **kw):
        r = dict(group_id=group, model=model, n_selected=300, selected_frequency=2.0, standardized_uplift=0.2, selected_effect=0.1,
                 bootstrap_ci_low=0.01, raw_p=0.001)
        r.update(kw)
        return r
    rows = selection_holdout_evaluations([row("RIDGE"), row("SPLINE"), row("XGB", selected_effect=-0.01)], rule)
    assert [r["gates_pass"] for r in rows] == [True, True, False]                    # negative selected effect fails the SELECTION HOLDOUT gate too
    assert rows[0]["selection_holdout_trials_in_family"] == 3 and rows[0]["selection_holdout_bonferroni_p"] == pytest.approx(0.003)
    assert group_verdicts(rows, rule)["G|U"] == {"models_passing": 2, "models": ["RIDGE", "SPLINE"], "evidence_gates_met": True}
    one = selection_holdout_evaluations([row("RIDGE"), row("SPLINE", standardized_uplift=0.005), row("XGB", selected_frequency=0.5)], rule)
    assert group_verdicts(one, rule)["G|U"]["evidence_gates_met"] is False                      # 1 of 3 is not a confirmation
    big_family = selection_holdout_evaluations([row(m, group=f"G{g}|U", raw_p=0.01) for g in range(2) for m in ("RIDGE", "SPLINE", "XGB")], rule)
    assert big_family[0]["selection_holdout_bonferroni_p"] == pytest.approx(0.06) and not big_family[0]["gates_pass"]    # 0.01 * 6 > 0.05
