import numpy as np
import pandas as pd
import pytest

from engine.acceptance import (AGREE, DIAG, INSTAB, LOW_FREQ, LOW_UPLIFT, PENDING_SENS, PROMOTABLE, SENS, STAT,
                               classify_trial, decide_experiment)
from engine.common import load_frozen
from engine.multiplicity import benjamini_hochberg
from engine.score_calibration import LOWER, UPPER
from engine.statistics import decile_diagnostics, eligible_weeks, evaluate_panel, week_key

F = load_frozen()
ACC = F.acceptance


def test_bh_known_values_and_monotonic():
    q = benjamini_hochberg([0.01, 0.04, 0.03, 0.005])
    assert q == pytest.approx([0.02, 0.04, 0.04, 0.02])
    p = np.random.default_rng(0).uniform(size=24)
    qq = benjamini_hochberg(p)
    order = np.argsort(p)
    assert (np.diff(qq[order]) >= -1e-15).all() and (qq >= p - 1e-15).all() and (qq <= 1).all()
    with pytest.raises(ValueError):
        benjamini_hochberg([0.1, float("nan")])


def panel(n_weeks=50, per_week=6, seed=0, slope=0.0, frac_upper=0.5):
    rng = np.random.default_rng(seed)
    weeks, years, ns = [], [], []
    t0 = pd.Timestamp("2019-01-07", tz="UTC")
    for w in range(n_weeks):
        for k in range(per_week):
            ts = t0 + pd.Timedelta(weeks=w, hours=k + 1)
            weeks.append(week_key([ts], "America/New_York")[0]); years.append(ts.year); ns.append(ts.value)
    n = len(weeks)
    score = rng.normal(size=n)
    y = slope * score + rng.normal(size=n)
    state = np.where(score > 0, UPPER, LOWER)
    return dict(y=y, state=state, year=np.array(years), week=np.array(weeks), event_ns=np.array(ns), score=score)


KW = dict(bootstrap_reps=400, permutation_reps=400, seed=1729, ci_level=0.95, min_events_year=20)


def test_panel_hand_numbers_frequency_uplift_retention():
    p = panel(n_weeks=50, per_week=6, seed=1, slope=0.5)
    r = evaluate_panel(p["y"], p["state"], p["year"], p["week"], p["event_ns"], 50, **KW)
    up = r[UPPER]
    y, sel = p["y"], p["state"] == UPPER
    assert up["n_parent"] == 300 and up["n_selected"] == int(sel.sum())
    assert up["parent_frequency"] == pytest.approx(300 / 50) and up["selected_frequency"] == pytest.approx(sel.sum() / 50)
    assert up["retention_ratio"] == pytest.approx(sel.sum() / 300)
    assert up["parent_effect"] == pytest.approx(y.mean())
    assert up["selected_effect"] == pytest.approx(y[sel].mean())
    assert up["uplift"] == pytest.approx(y[sel].mean() - y.mean())
    assert up["target_sd"] == pytest.approx(y.std(ddof=1))
    assert up["standardized_uplift"] == pytest.approx(up["uplift"] / y.std(ddof=1))
    lo = r[LOWER]                                   # fade: evaluation target is -y
    m = ~sel
    assert lo["parent_effect"] == pytest.approx(-y.mean())
    assert lo["selected_effect"] == pytest.approx(-y[m].mean())
    assert lo["uplift"] == pytest.approx(-y[m].mean() + y.mean())
    assert up["bootstrap_ci_low"] < up["uplift"] < up["bootstrap_ci_high"]


def test_frequency_uses_eligible_weeks_not_weeks_with_events():
    p = panel(n_weeks=10, per_week=10, seed=2)
    a = evaluate_panel(p["y"], p["state"], p["year"], p["week"], p["event_ns"], 10, **KW)[UPPER]
    b = evaluate_panel(p["y"], p["state"], p["year"], p["week"], p["event_ns"], 40, **KW)[UPPER]
    assert a["selected_frequency"] == pytest.approx(4 * b["selected_frequency"])


def test_seeded_determinism_and_different_seed_changes_ci():
    p = panel(seed=3, slope=0.4)
    a = evaluate_panel(p["y"], p["state"], p["year"], p["week"], p["event_ns"], 50, **KW)
    b = evaluate_panel(p["y"], p["state"], p["year"], p["week"], p["event_ns"], 50, **KW)
    assert a[UPPER]["bootstrap_ci_low"] == b[UPPER]["bootstrap_ci_low"] and a[UPPER]["raw_p"] == b[UPPER]["raw_p"]
    c = evaluate_panel(p["y"], p["state"], p["year"], p["week"], p["event_ns"], 50, **{**KW, "seed": 5})
    assert c[UPPER]["bootstrap_ci_low"] != a[UPPER]["bootstrap_ci_low"]


def test_strong_signal_small_p_and_null_not_small():
    strong = panel(seed=4, slope=1.0)
    r = evaluate_panel(strong["y"], strong["state"], strong["year"], strong["week"], strong["event_ns"], 50, **KW)
    assert r[UPPER]["raw_p"] < 0.01 and r[LOWER]["raw_p"] < 0.01
    assert r[UPPER]["bootstrap_ci_low"] > 0


def test_blocked_permutation_is_calibrated_under_null():
    rejections, trials = 0, 60
    for s in range(trials):
        p = panel(n_weeks=40, per_week=5, seed=100 + s, slope=0.0)
        r = evaluate_panel(p["y"], p["state"], p["year"], p["week"], p["event_ns"], 40,
                           bootstrap_reps=10, permutation_reps=199, seed=1729, ci_level=0.95, min_events_year=20)
        rejections += r[UPPER]["raw_p"] <= 0.05
    assert rejections / trials <= 0.15          # nominal 5%; generous bound for 60 trials


def test_permutation_permutes_whole_week_blocks_not_events():
    from engine.statistics import permute_week_blocks
    rng = np.random.default_rng(0)
    sizes = rng.integers(2, 9, 30)
    vals = rng.normal(size=30)
    y = np.repeat(vals, sizes)
    wk = np.repeat([f"2019-W{i:02d}" for i in range(1, 31)], sizes)
    blocks = np.split(y, np.flatnonzero(np.r_[True, wk[1:] != wk[:-1]])[1:])
    assert [len(b) for b in blocks] == sizes.tolist()
    yp = permute_week_blocks(blocks, np.random.default_rng(1))
    assert len(yp) == len(y) and sorted(yp.tolist()) == sorted(y.tolist())
    assert not np.array_equal(yp, y)
    # every original week block survives intact and contiguous (an event-level shuffle would not)
    pos, seen = 0, []
    while pos < len(yp):
        v = yp[pos]
        size = int(sizes[list(vals).index(v)])
        assert (yp[pos:pos + size] == v).all()
        seen.append(v); pos += size
    assert sorted(seen) == sorted(vals.tolist())


def test_year_by_year_and_eligibility_20_events():
    p = panel(n_weeks=104, per_week=5, seed=6, slope=0.8)       # 2019 & 2020, ~130 selected/yr
    r = evaluate_panel(p["y"], p["state"], p["year"], p["week"], p["event_ns"], 104, **KW)[UPPER]
    assert [x["year"] for x in r["yearly"]] == [2019, 2020]
    assert r["eligible_years"] >= 2 and r["positive_years"] == r["eligible_years"]
    tiny = panel(n_weeks=10, per_week=4, seed=7, slope=0.8)      # < 20 selected in the year
    rt = evaluate_panel(tiny["y"], tiny["state"], tiny["year"], tiny["week"], tiny["event_ns"], 10, **KW)[UPPER]
    assert rt["eligible_years"] == 0


def test_empty_selection_is_not_evaluable_and_p_is_one():
    p = panel(seed=8)
    st = np.full(len(p["y"]), UPPER)
    r = evaluate_panel(p["y"], st, p["year"], p["week"], p["event_ns"], 50, **KW)[LOWER]
    assert r["n_selected"] == 0 and r["raw_p"] == 1.0 and np.isnan(r["uplift"])


def test_eligible_weeks_from_bars_not_events():
    idx = pd.date_range("2019-12-23", "2020-01-17", freq="1D", tz="UTC")     # ~4 weeks, spans a year boundary
    w2019 = eligible_weeks(idx, [2019], "America/New_York")
    w2020 = eligible_weeks(idx, [2020], "America/New_York")
    wall = eligible_weeks(idx, [2019, 2020], "America/New_York")
    assert wall == len(set(week_key(idx, "America/New_York"))) and wall <= w2019 + w2020 and wall >= max(w2019, w2020)
    assert eligible_weeks(idx, [], "America/New_York") == 0


def test_decile_diagnostics_shapes_and_disclaimer_fields():
    p = panel(n_weeks=100, per_week=6, seed=9, slope=0.7)
    d = decile_diagnostics(p["score"], p["y"], p["year"], 100)
    assert len(d["deciles"]) == 10 and sum(x["n"] for x in d["deciles"]) == len(p["y"])
    assert d["deciles"][-1]["mean_target"] > d["deciles"][0]["mean_target"]
    assert sum(x["frequency_per_week"] for x in d["deciles"]) == pytest.approx(len(p["y"]) / 100)
    assert set(d["by_year"]) >= {2019}


# ---- acceptance gates ----------------------------------------------------------------------
def good_row(**kw):
    row = dict(target="DIR_RETURN_30", model="RIDGE", state=UPPER, n_selected_events=500, selected_frequency=2.0,
               retention_ratio=0.5, standardized_uplift=0.2, bootstrap_ci_low=0.01, experiment_q=0.01,
               campaign_q=0.01, positive_years=4, eligible_years=5)
    row.update(kw)
    return row


def test_each_gate_blocks_promotion_independently():
    assert classify_trial(good_row(), ACC)[0]
    cases = {
        LOW_FREQ: dict(selected_frequency=0.99),
        LOW_UPLIFT: dict(standardized_uplift=0.099),
        STAT: dict(bootstrap_ci_low=0.0),
        INSTAB: dict(positive_years=3, eligible_years=5),
    }
    for decision, kw in cases.items():
        ok, dec, why = classify_trial(good_row(**kw), ACC)
        assert not ok and dec == decision and why
    assert classify_trial(good_row(experiment_q=0.0501), ACC)[1] == STAT
    assert classify_trial(good_row(campaign_q=0.0501), ACC)[1] == STAT
    assert classify_trial(good_row(selected_frequency=1.0), ACC)[0]              # floor is inclusive
    assert classify_trial(good_row(standardized_uplift=0.10), ACC)[0]            # floor is inclusive
    assert classify_trial(good_row(positive_years=7, eligible_years=10), ACC)[0]  # 70% inclusive
    assert classify_trial(good_row(eligible_years=0, positive_years=0), ACC)[1] == INSTAB
    assert classify_trial(good_row(n_selected_events=0), ACC)[1] == DIAG


def test_frequency_destruction_is_labelled_not_hidden():
    ok, dec, why = classify_trial(good_row(standardized_uplift=0.004 / 0.1, retention_ratio=0.49,
                                           selected_frequency=2.1), ACC)
    assert not ok and dec == LOW_UPLIFT and "REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS" in why


def mk_rows(passing):
    rows = []
    for tgt in ("DIR_RETURN_30",):
        for st in (UPPER, LOWER):
            for m in ("RIDGE", "SPLINE", "XGB"):
                ok = (tgt, st, m) in passing
                rows.append(good_row(target=tgt, state=st, model=m) if ok else
                            good_row(target=tgt, state=st, model=m, standardized_uplift=0.0))
    return rows


def test_two_of_three_model_agreement_required():
    one = decide_experiment(mk_rows({("DIR_RETURN_30", UPPER, "RIDGE")}), ACC, {})
    assert {r["decision"] for r in one if r["model"] == "RIDGE" and r["state"] == UPPER} == {AGREE}
    two = decide_experiment(mk_rows({("DIR_RETURN_30", UPPER, "RIDGE"), ("DIR_RETURN_30", UPPER, "XGB")}), ACC,
                            {"DIR_RETURN_30|UPPER_HALF": "PASSED"})
    by = {(r["model"], r["state"]): r["decision"] for r in two}
    assert by[("RIDGE", UPPER)] == by[("XGB", UPPER)] == PROMOTABLE
    assert by[("SPLINE", UPPER)] == LOW_UPLIFT                  # the third model is still shown, rejected
    assert by[("RIDGE", LOWER)] == LOW_UPLIFT


def test_sensitivity_veto_and_pending_states():
    passing = {("DIR_RETURN_30", UPPER, "RIDGE"), ("DIR_RETURN_30", UPPER, "SPLINE")}
    failed = decide_experiment(mk_rows(passing), ACC, {"DIR_RETURN_30|UPPER_HALF": "FAILED"})
    assert {r["decision"] for r in failed if r["state"] == UPPER and r["model"] != "XGB"} == {SENS}
    pend = decide_experiment(mk_rows(passing), ACC, {})
    assert {r["decision"] for r in pend if r["state"] == UPPER and r["model"] != "XGB"} == {PENDING_SENS}
    skipped = decide_experiment(mk_rows(passing), ACC, {"DIR_RETURN_30|UPPER_HALF": "SKIPPED_NO_PARAMETERS"})
    assert {r["decision"] for r in skipped if r["state"] == UPPER and r["model"] != "XGB"} == {PROMOTABLE}


def test_upper_and_lower_trials_of_a_pair_are_algebraically_linked():
    """Structural property (documented in RESEARCH_RULES.md): with no ties, uplift_LOWER = (nU/nL) * uplift_UPPER.
    Both states therefore share sign and raw p-value, and a positive pair uplift can coexist with a NEGATIVE
    absolute selected effect on the fade side when the parent effect is positive."""
    p = panel(n_weeks=80, per_week=6, seed=12, slope=0.4)
    r = evaluate_panel(p["y"], p["state"], p["year"], p["week"], p["event_ns"], 80, **KW)
    u, lo = r[UPPER], r[LOWER]
    assert lo["uplift"] == pytest.approx(u["uplift"] * u["n_selected"] / lo["n_selected"], rel=1e-9)
    assert lo["raw_p"] == u["raw_p"]
    assert np.sign(lo["uplift"]) == np.sign(u["uplift"])
    # positive parent drift: the fade side can show positive uplift while losing money in absolute terms
    q = panel(n_weeks=80, per_week=6, seed=13, slope=0.4)
    q["y"] = q["y"] + 0.5
    r2 = evaluate_panel(q["y"], q["state"], q["year"], q["week"], q["event_ns"], 80, **KW)
    assert r2[LOWER]["uplift"] > 0 and r2[LOWER]["selected_effect"] < 0
