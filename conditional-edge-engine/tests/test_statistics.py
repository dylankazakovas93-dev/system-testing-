import numpy as np
import pandas as pd
import pytest

from engine import acceptance as A
from engine.acceptance import (AGREE, COND_IMPROVE, DIAG, INSTAB, LOW_FREQ, LOW_UPLIFT, PROVISIONAL, SENS, SHORTLIST, STAT, VERIF,
                               classify_trial, decide_experiment, rank_groups, rank_trials)
from engine.common import load_frozen
from engine.multiplicity import benjamini_hochberg
from engine.score_calibration import LOWER, UPPER
from engine.statistics import decile_diagnostics, evaluate_panel, week_key, weeks_in_intervals

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


def test_eligible_weeks_come_from_bars_in_intervals_not_from_events():
    idx = pd.date_range("2019-12-23", "2020-01-17", freq="1D", tz="UTC")     # ~4 weeks, spans a year boundary
    ns = idx.asi8 if idx.unit == "ns" else idx.as_unit("ns").asi8
    whole = weeks_in_intervals(idx, [(-2**62, 2**62)], "America/New_York")
    assert whole["total"] == len(set(week_key(idx, "America/New_York")))
    half = weeks_in_intervals(idx, [(int(pd.Timestamp("2020-01-01", tz="UTC").value), 2**62)], "America/New_York")
    assert 0 < half["total"] < whole["total"] and set(half["by_year"]) == {2020}
    two = weeks_in_intervals(idx, [(-2**62, int(pd.Timestamp("2019-12-30", tz="UTC").value)), (int(pd.Timestamp("2020-01-06", tz="UTC").value), 2**62)], "America/New_York")
    assert len(two["by_interval"]) == 2 and two["total"] >= max(two["by_interval"])
    assert weeks_in_intervals(idx, [], "America/New_York")["total"] == 0


def test_decile_diagnostics_shapes_and_disclaimer_fields():
    p = panel(n_weeks=100, per_week=6, seed=9, slope=0.7)
    d = decile_diagnostics(p["score"], p["y"], p["year"], 100)
    assert len(d["deciles"]) == 10 and sum(x["n"] for x in d["deciles"]) == len(p["y"])
    assert d["deciles"][-1]["mean_target"] > d["deciles"][0]["mean_target"]
    assert sum(x["frequency_per_week"] for x in d["deciles"]) == pytest.approx(len(p["y"]) / 100)
    assert set(d["by_year"]) >= {2019}


# ---- acceptance gates ----------------------------------------------------------------------
def good_row(**kw):
    row = dict(target="DIR_RETURN_30", model="RIDGE", state=UPPER, trial_id="T", n_selected_events=500, selected_frequency=2.0,
               retention_ratio=0.5, standardized_uplift=0.2, selected_effect=0.2, bootstrap_ci_low=0.01, experiment_q=0.01,
               campaign_q=0.01, experiment_bonferroni_p=0.01, campaign_bonferroni_p=0.01, positive_years=4, positive_uplift_years=4,
               eligible_years=5, folds_evaluated=5, positive_effect_folds=5, positive_uplift_folds=5)
    row.update(kw)
    return row


def test_each_gate_blocks_eligibility_independently():
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
    for k in ("experiment_q", "campaign_q", "experiment_bonferroni_p", "campaign_bonferroni_p"):
        ok, dec, why = classify_trial(good_row(**{k: 0.0501}), ACC)
        assert not ok and dec == STAT and k in why, k
    assert classify_trial(good_row(selected_frequency=1.0), ACC)[0]              # floors are inclusive
    assert classify_trial(good_row(standardized_uplift=0.10), ACC)[0]
    assert classify_trial(good_row(positive_years=7, positive_uplift_years=7, eligible_years=10), ACC)[0]   # 70% inclusive
    assert classify_trial(good_row(eligible_years=0, positive_years=0, positive_uplift_years=0), ACC)[1] == INSTAB
    assert classify_trial(good_row(n_selected_events=0), ACC)[1] == DIAG


def test_negative_absolute_selected_effect_cannot_promote():
    # parent -0.30, selected -0.05 -> uplift +0.25 is interesting but NOT a candidate
    ok, dec, why = classify_trial(good_row(selected_effect=-0.05, standardized_uplift=0.25), ACC)
    assert not ok and dec == COND_IMPROVE == "DIAGNOSTIC_CONDITIONAL_IMPROVEMENT" and "less bad than the parent" in why
    assert not classify_trial(good_row(selected_effect=0.0), ACC)[0]              # must be strictly positive
    rows = decide_experiment([good_row(selected_effect=-0.05, model=m, trial_id=m) for m in ("RIDGE", "SPLINE", "XGB")], ACC,
                             {"DIR_RETURN_30|UPPER_HALF": "PASSED"}, VER_ALL)
    assert {r["decision"] for r in rows} == {COND_IMPROVE}


def test_year_consistency_needs_both_positive_effect_and_positive_uplift_fractions():
    assert not classify_trial(good_row(positive_years=5, positive_uplift_years=3, eligible_years=5), ACC)[0]    # effect ok, uplift 60%
    assert not classify_trial(good_row(positive_years=3, positive_uplift_years=5, eligible_years=5), ACC)[0]    # uplift ok, effect 60%
    ok, dec, why = classify_trial(good_row(positive_years=3, positive_uplift_years=3, eligible_years=5), ACC)
    assert dec == INSTAB and "positive selected-effect years 3/5" in why and "positive-uplift years 3/5" in why


def test_five_fold_consistency_gate_never_relaxed():
    assert not classify_trial(good_row(positive_uplift_folds=3), ACC)[0]
    assert not classify_trial(good_row(positive_effect_folds=3), ACC)[0]
    assert classify_trial(good_row(positive_uplift_folds=4, positive_effect_folds=4), ACC)[0]
    ok, dec, why = classify_trial(good_row(folds_evaluated=4, positive_uplift_folds=4, positive_effect_folds=4), ACC)
    assert not ok and dec == INSTAB and "INSUFFICIENT_DEVELOPMENT_FOLD_EVIDENCE" in why     # 4 of 4 is NOT relaxed to 3/4


def test_frequency_destruction_is_labelled_not_hidden():
    ok, dec, why = classify_trial(good_row(standardized_uplift=0.04, retention_ratio=0.49, selected_frequency=2.1), ACC)
    assert not ok and dec == LOW_UPLIFT and "REJECTED_INSUFFICIENT_UPLIFT_FOR_FREQUENCY_LOSS" in why


VER_ALL = {f"DIR_RETURN_30|{m}": {"label": "RESEARCH_FAMILIES_PASS_GLOBAL_INCOMPLETE", "mode": "strong"} for m in ("RIDGE", "SPLINE", "XGB")}


def mk_rows(passing, **extra):
    rows = []
    for st in (UPPER, "LOWER_HALF"):
        for m in ("RIDGE", "SPLINE", "XGB"):
            ok = ("DIR_RETURN_30", st, m) in passing
            rows.append(good_row(state=st, model=m, trial_id=f"{st}-{m}", **extra) if ok else
                        good_row(state=st, model=m, trial_id=f"{st}-{m}", standardized_uplift=0.0, **extra))
    return rows


def test_two_of_three_model_agreement_required():
    one = decide_experiment(mk_rows({("DIR_RETURN_30", UPPER, "RIDGE")}), ACC, {"DIR_RETURN_30|UPPER_HALF": "PASSED"}, VER_ALL)
    assert {r["decision"] for r in one if r["model"] == "RIDGE" and r["state"] == UPPER} == {AGREE}
    two = decide_experiment(mk_rows({("DIR_RETURN_30", UPPER, "RIDGE"), ("DIR_RETURN_30", UPPER, "XGB")}), ACC,
                            {"DIR_RETURN_30|UPPER_HALF": "PASSED"}, VER_ALL)
    by = {(r["model"], r["state"]): r["decision"] for r in two}
    assert by[("RIDGE", UPPER)] == by[("XGB", UPPER)] == SHORTLIST
    assert by[("SPLINE", UPPER)] == LOW_UPLIFT                  # the third model is still shown, rejected
    assert by[("RIDGE", "LOWER_HALF")] == LOW_UPLIFT


def test_campaign_level_gates_make_a_group_provisional_not_eligible():
    rows = mk_rows({("DIR_RETURN_30", UPPER, m) for m in ("RIDGE", "SPLINE", "XGB")}, campaign_bonferroni_p=0.2)
    out = decide_experiment(rows, ACC, {"DIR_RETURN_30|UPPER_HALF": "PASSED"}, VER_ALL)
    up = [r for r in out if r["state"] == UPPER]
    assert {r["decision"] for r in up} == {PROVISIONAL} and "campaign-level gates" in up[0]["rejection_reason"]
    assert A.is_status_of(r["decision"] for r in out) == PROVISIONAL
    assert A.lifecycle_from_is_status(PROVISIONAL) == "IS_PROVISIONAL_CANDIDATE"


def test_path_verification_gates_model_agreement():
    passing = {("DIR_RETURN_30", UPPER, m) for m in ("RIDGE", "SPLINE", "XGB")}
    sens = {"DIR_RETURN_30|UPPER_HALF": "PASSED"}
    none = decide_experiment(mk_rows(passing), ACC, sens, {})                                    # nothing verified yet
    assert {r["decision"] for r in none if r["state"] == UPPER} == {PROVISIONAL}
    assert A.is_status_of(r["decision"] for r in none) == PROVISIONAL                           # cannot be shortlist-eligible
    fast = {k: {**v, "mode": "fast"} for k, v in VER_ALL.items()}
    assert {r["decision"] for r in decide_experiment(mk_rows(passing), ACC, sens, fast) if r["state"] == UPPER} == {PROVISIONAL}
    two = {k: v for k, v in VER_ALL.items() if not k.endswith("XGB")}
    assert {r["decision"] for r in decide_experiment(mk_rows(passing), ACC, sens, two) if r["state"] == UPPER and r["model"] != "XGB"} == {SHORTLIST}
    failed = dict(VER_ALL); failed["DIR_RETURN_30|XGB"] = {"label": "FAILED", "mode": "strong"}
    out = decide_experiment(mk_rows(passing), ACC, sens, failed)
    assert next(r for r in out if r["model"] == "XGB" and r["state"] == UPPER)["decision"] == VERIF       # failed path rejected
    assert {r["decision"] for r in out if r["model"] != "XGB" and r["state"] == UPPER} == {SHORTLIST}     # other 2 still agree
    failed2 = dict(failed); failed2["DIR_RETURN_30|SPLINE"] = {"label": "FAILED", "mode": "strong"}
    out2 = decide_experiment(mk_rows(passing), ACC, sens, failed2)
    assert next(r for r in out2 if r["model"] == "RIDGE" and r["state"] == UPPER)["decision"] == AGREE    # only 1 trustworthy model


def test_sensitivity_veto_and_pending_states():
    passing = {("DIR_RETURN_30", UPPER, m) for m in ("RIDGE", "SPLINE", "XGB")}
    failed = decide_experiment(mk_rows(passing), ACC, {"DIR_RETURN_30|UPPER_HALF": "FAILED"}, VER_ALL)
    assert {r["decision"] for r in failed if r["state"] == UPPER} == {SENS}
    pend = decide_experiment(mk_rows(passing), ACC, {}, VER_ALL)
    assert {r["decision"] for r in pend if r["state"] == UPPER} == {PROVISIONAL}
    skipped = decide_experiment(mk_rows(passing), ACC, {"DIR_RETURN_30|UPPER_HALF": "SKIPPED_NO_PARAMETERS"}, VER_ALL)
    assert {r["decision"] for r in skipped if r["state"] == UPPER} == {SHORTLIST}


def test_deterministic_ranking_rule_and_top5_cap():
    base = [good_row(trial_id=f"T{i:02d}", decision=SHORTLIST) for i in range(1, 5)]
    base[0].update(standardized_uplift=0.30)
    base[1].update(standardized_uplift=0.40)
    base[2].update(standardized_uplift=0.40, campaign_bonferroni_p=0.001)
    base[3].update(standardized_uplift=0.40, campaign_bonferroni_p=0.001, selected_frequency=3.0)
    order = [r["trial_id"] for r in rank_trials(base)]
    # std uplift DESC, then campaign Bonferroni p ASC, then selected frequency DESC, then trial id ASC
    assert order == ["T04", "T03", "T02", "T01"]
    tie = [good_row(trial_id=t, decision=SHORTLIST) for t in ("T09", "T03", "T05")]
    assert [r["trial_id"] for r in rank_trials(tie)] == ["T03", "T05", "T09"]            # final tie-break: trial_id ASC
    assert rank_trials([good_row(decision=PROVISIONAL), good_row(decision=STAT)]) == []  # only eligible trials are ranked
    rows = []
    targets = ["DIR_RETURN_15", "DIR_RETURN_30", "DIR_RETURN_60", "DIR_PATH_SKEW_60"]
    for gi, (t, st) in enumerate([(t, s) for t in targets for s in (UPPER, "LOWER_HALF")]):
        for m in ("RIDGE", "SPLINE", "XGB"):
            rows.append(good_row(target=t, state=st, model=m, trial_id=f"{t}-{st}-{m}", decision=SHORTLIST,
                                 standardized_uplift=0.11 + 0.01 * gi))
    g = rank_groups(rows, ACC)
    assert len(g) == 5 and [x["rank"] for x in g] == [1, 2, 3, 4, 5]                     # at most TOP 5
    assert g[0]["median_standardized_uplift"] > g[1]["median_standardized_uplift"] > g[4]["median_standardized_uplift"]
    two_models = [r for r in rows if not (r["target"] == "DIR_PATH_SKEW_60" and r["state"] == "LOWER_HALF" and r["model"] != "RIDGE")]
    assert "DIR_PATH_SKEW_60|LOWER_HALF" not in {x["group_id"] for x in rank_groups(two_models, ACC, 10)}   # 1 of 3 is not a group


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


def test_year_and_fold_tables_concentration_warning_and_weeks():
    """Per-year / per-fold tables, positive-year counts, and the YEAR_CONCENTRATION_WARNING (> 35% of total absolute uplift).
    Note: with only 3 eligible years the largest share is >= 33% by construction, so the warning is only informative with
    several years; the uniform case therefore uses 6 years."""
    rng = np.random.default_rng(5)
    rows = []
    t0 = pd.Timestamp("2019-01-07", tz="UTC")
    for w in range(312):                                  # 2019 .. 2024
        for k in range(6):
            ts = t0 + pd.Timedelta(weeks=w, hours=k + 1)
            rows.append((ts.value, ts.year, week_key([ts], "America/New_York")[0]))
    ns = np.array([r[0] for r in rows]); yr = np.array([r[1] for r in rows]); wk = np.array([r[2] for r in rows])
    years = sorted(set(yr))
    score = rng.normal(size=len(ns))

    def run(slope_of_year):
        slope = np.array([slope_of_year(a) for a in yr])
        y = slope * score + rng.normal(size=len(ns)) * 0.3
        st = np.where(score > 0, UPPER, LOWER)
        fold = np.searchsorted(years, yr) + 1
        wby = {int(a): 52 for a in years}
        wbf = {int(f): 52 for f in np.unique(fold)}
        return evaluate_panel(y, st, yr, wk, ns, 52 * len(years), fold=fold, weeks_by_year=wby, weeks_by_fold=wbf, **KW)[UPPER]

    r = run(lambda a: 3.0 if a == 2021 else 0.1)                      # one year carries almost all the uplift
    yl = {x["year"]: x for x in r["yearly"]}
    assert set(yl) == set(years) and all(x["eligible"] for x in yl.values())
    assert yl[2021]["n_parent"] == int((yr == 2021).sum()) and yl[2021]["selected_frequency"] == pytest.approx(yl[2021]["n_selected"] / 52)
    contrib = {k: abs(v["n_selected"] * v["uplift"]) for k, v in yl.items()}
    assert r["year_concentration_share"] == pytest.approx(max(contrib.values()) / sum(contrib.values()))
    assert r["year_concentration_warning"] is True and r["year_concentration_share"] > 0.35
    assert r["positive_years"] == 6 and r["positive_uplift_years"] == 6
    assert r["folds_evaluated"] == 6 and len(r["folds"]) == 6
    f2 = [f for f in r["folds"] if f["fold"] == 2][0]
    assert f2["selected_frequency"] == pytest.approx(f2["n_selected"] / 52)
    r2 = run(lambda a: 1.0)
    assert r2["year_concentration_warning"] is False and r2["year_concentration_share"] < 0.35
    r3 = run(lambda a: 0.0)
    assert r3["positive_years"] < 6 or r3["positive_uplift_years"] < 6              # no structure: not consistently positive
