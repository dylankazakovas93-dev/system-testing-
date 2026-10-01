import numpy as np
import pandas as pd
import pytest

from engine.common import load_frozen
from engine.feature_engine import feature_names
from engine.model_engine import FrozenModel, make_model_factory
from engine.score_calibration import UPPER, LOWER, WFConfig, assign_state, calibrate_threshold, inner_oof_predictions
from tests import helpers as H
from engine.walkforward import development_folds, run_walkforward

F = load_frozen()
NAMES = feature_names(F)


def synth(n_per_year=400, years=(2016, 2017, 2018, 2019, 2020), seed=0, slope=0.0, horizon_min=60):
    rng = np.random.default_rng(seed)
    times = []
    for y in years:
        start = pd.Timestamp(f"{y}-01-05", tz="UTC").value
        end = pd.Timestamp(f"{y}-12-20", tz="UTC").value
        times.append(np.sort(rng.integers(start, end, n_per_year)))
    t = pd.DatetimeIndex(np.concatenate(times), tz="UTC")
    n = len(t)
    X = pd.DataFrame(rng.normal(size=(n, len(NAMES))), columns=NAMES)
    X["day_of_week"] = rng.integers(0, 5, n).astype(float)
    y = slope * X["ER_60"].to_numpy() + rng.normal(size=n)
    te = t + pd.Timedelta(minutes=horizon_min)
    return X, y, t, te


CFG = WFConfig(min_outer_train_events=300, inner_blocks=5, min_inner_train_events=50, min_inner_oof_events=30)


class LinearProbe:
    """Deterministic fake: prediction = OLS slope on ER_60 only (fast, transparent)."""

    def __init__(self):
        self.fit_labels = None

    def fit(self, X, y):
        x = X["ER_60"].to_numpy()
        self.b = float(np.dot(x - x.mean(), y - y.mean()) / np.dot(x - x.mean(), x - x.mean()))
        self.m = float(y.mean())
        self.fit_labels = np.asarray(y).copy()
        return self

    def predict(self, X):
        return self.m + self.b * X["ER_60"].to_numpy()


class SpyFactory:
    """Records the exact training rows (their y values) every fit sees."""

    def __init__(self):
        self.fits = []

    def __call__(self):
        outer = self

        class M(LinearProbe):
            def fit(self, X, y):
                outer.fits.append(np.asarray(y).copy())
                return super().fit(X, y)
        return M()


def folds_for(t):
    return development_folds(t, 5, "America/New_York")


def test_three_frozen_models_fit_and_predict_deterministically():
    X, y, t, te = synth(200, (2018, 2019), seed=1, slope=0.5)
    for name in ("RIDGE", "SPLINE", "XGB"):
        a = FrozenModel(name, F).fit(X, y).predict(X)
        b = FrozenModel(name, F).fit(X, y).predict(X)
        assert np.array_equal(a, b) and np.isfinite(a).all()
        assert np.corrcoef(a, y)[0, 1] > 0.3        # detects the planted linear signal in-sample


def test_frozen_hyperparameters_come_from_yaml():
    m = FrozenModel("XGB", F).fit(*synth(120, (2018,), seed=2)[:2])
    p = m.est.get_params()
    for k, v in dict(max_depth=2, learning_rate=0.03, n_estimators=300, min_child_weight=20, subsample=0.8,
                     colsample_bytree=0.8, reg_lambda=20.0, reg_alpha=1.0, random_state=1729,
                     tree_method="hist", objective="reg:squarederror").items():
        assert p[k] == v, k
    r = FrozenModel("RIDGE", F).fit(*synth(120, (2018,), seed=2)[:2])
    assert r.est.alpha == 10.0 and r.est.fit_intercept
    s = FrozenModel("SPLINE", F).fit(*synth(120, (2018,), seed=2)[:2])
    assert (s.spl.degree, s.spl.n_knots, s.spl.knots, s.spl.include_bias) == (3, 4, "quantile", False)
    assert s.est.alpha == 10.0
    with pytest.raises(Exception):
        FrozenModel("LASSO", F)


def test_ridge_standardization_is_train_only():
    X, y, t, te = synth(200, (2018, 2019), seed=3)
    m = FrozenModel("RIDGE", F).fit(X.iloc[:150], y[:150])
    assert np.allclose(m.scaler.mean_, X.iloc[:150][m.cont].mean().to_numpy())


def test_spline_knots_fit_on_train_only_and_dow_not_splined():
    X, y, t, te = synth(200, (2018, 2019), seed=4)
    m = FrozenModel("SPLINE", F).fit(X.iloc[:150], y[:150])
    q = np.quantile(X.iloc[:150]["ER_60"], [0, 1 / 3, 2 / 3, 1])      # 4 quantile knots incl. boundaries
    knots = m.spl.bsplines_[m.cont.index("ER_60")].t
    Xm = X.copy(); Xm.iloc[150:, :] = 1e6                      # mutate everything outside the training rows
    m2 = FrozenModel("SPLINE", F).fit(Xm.iloc[:150].assign(day_of_week=X.iloc[:150]["day_of_week"]), y[:150])
    assert np.array_equal(m2.spl.bsplines_[m.cont.index("ER_60")].t, knots)
    assert set(np.round(q, 8)).issubset(set(np.round(knots, 8)))
    assert "day_of_week" not in m.cont
    assert m.spl.n_features_in_ == 55


def test_xgb_predictions_do_not_depend_on_pandas_row_order_of_index():
    X, y, t, te = synth(150, (2018,), seed=5, slope=1.0)
    m = FrozenModel("XGB", F).fit(X, y)
    p1 = m.predict(X)
    p2 = m.predict(X.set_index(pd.RangeIndex(1000, 1000 + len(X))))
    assert np.array_equal(p1, p2)


def test_score_median_comes_from_inner_oof_training_scores_only():
    X, y, t, te = synth(400, (2016, 2017, 2018), seed=6, slope=1.0)
    ev = t.asi8; tend = te.asi8
    train = np.flatnonzero(t < pd.Timestamp("2018-01-01", tz="UTC"))
    thr, pos, pred = calibrate_threshold(LinearProbe, X, y, ev, tend, train, CFG)
    order = train[np.argsort(ev[train], kind="stable")]
    segs = np.array_split(order, 5)
    manual = []
    for j in range(1, 5):
        prior = np.concatenate(segs[:j]); prior = prior[tend[prior] < ev[segs[j][0]]]
        mdl = LinearProbe().fit(X.iloc[prior], y[prior])
        manual.append(mdl.predict(X.iloc[segs[j]]))
    assert thr == pytest.approx(float(np.median(np.concatenate(manual))))
    assert len(pred) == sum(len(s) for s in segs[1:])            # first block is never predicted
    val = np.flatnonzero(t >= pd.Timestamp("2018-01-01", tz="UTC"))
    full = LinearProbe().fit(X.iloc[train], y[train])
    assert thr != pytest.approx(float(np.median(full.predict(X.iloc[val]))), abs=1e-12)


# ------------------------------- DEVELOPMENT_CV: exactly K=5 purged chronological expanding folds -------------------------
def test_development_cv_is_exactly_five_chronological_expanding_folds():
    X, y, t, te = synth(400, slope=0.0, seed=9)
    folds = folds_for(t)
    assert len(folds) == 5 == F.trial_policy["development_cv"]["K"]
    starts = [f.val_start_ns for f in folds]
    assert starts == sorted(starts) and len(set(starts)) == 5
    for a, b in zip(folds[:-1], folds[1:]):
        assert a.val_end_ns == b.val_start_ns                     # consecutive blocks, no gap, no overlap
    res = run_walkforward(LinearProbe, X, y, t, te, CFG, folds)
    assert [f["status"] for f in res.folds] == ["OK"] * 5
    ntr = [f["n_train"] for f in res.folds]
    assert ntr == sorted(ntr) and len(set(ntr)) == 5              # expanding
    ev = t.asi8
    for f, fd in zip(res.folds, folds):                           # validation rows only from their own block (no shuffling)
        pos = res.validation[res.validation["fold"] == f["fold"]]["pos"].to_numpy()
        assert ((ev[pos] >= fd.val_start_ns) & (ev[pos] < fd.val_end_ns)).all()
    assert set(res.validation["fold"]) == {1, 2, 3, 4, 5}
    assert not any(res.validation["fold"].diff().dropna() < 0)    # chronological


def test_fold_boundaries_use_timestamps_only_and_snap_to_local_trading_day_start():
    X, y, t, te = synth(300, slope=0.0, seed=10)
    f1 = folds_for(t)
    f2 = folds_for(t)
    assert [f.val_start_ns for f in f1] == [f.val_start_ns for f in f2]
    for f in f1:
        local = pd.Timestamp(f.val_start_ns, tz="UTC").tz_convert("America/New_York")
        assert (local.hour, local.minute, local.second) == (0, 0, 0)       # whole trading days stay together
    other = folds_for(t)                                                     # labels never enter the boundaries
    assert [f.val_start_ns for f in other] == [f.val_start_ns for f in f1]


def test_training_events_are_purged_by_effective_target_end():
    X, y, t, te = synth(400, slope=0.0, seed=11, horizon_min=60 * 24 * 30)      # 30-day label windows
    spy = SpyFactory()
    folds = folds_for(t)
    res = run_walkforward(spy, X, y, t, te, CFG, folds)
    ev, tend = t.asi8, te.asi8
    for f, fd in zip(res.folds, folds):
        legal = (ev < fd.val_start_ns) & (tend < fd.val_start_ns)
        crossing = (ev < fd.val_start_ns) & (tend >= fd.val_start_ns)
        assert f["n_train"] == int(legal.sum())                                 # exactly the legal set
        assert crossing.sum() > 0                                               # overlapping events existed and were removed
    # the final fit of every fold used ONLY legal rows: poison y of the overlapping/validation/future rows
    y2 = y.copy()
    fd = folds[2]
    bad = ~((ev < fd.val_start_ns) & (tend < fd.val_start_ns))
    y2[bad] = 9999.0
    a = run_walkforward(LinearProbe, X, y, t, te, CFG, folds).validation
    b = run_walkforward(LinearProbe, X, y2, t, te, CFG, folds).validation
    pd.testing.assert_frame_equal(a[a.fold == 3].reset_index(drop=True), b[b.fold == 3].reset_index(drop=True))


def test_effective_target_end_is_max_of_claimed_and_declared():
    """A candidate that UNDERSTATES its target_end cannot shorten the purge: the effective end is max(claimed, declared)."""
    from engine.target_engine import compute_primary_targets, declared_resolution_times
    bars = H.random_bars(300, seed=2)
    ev = H.events_at(bars, [50, 100])
    tg = compute_primary_targets(bars, ev, F)["DIR_RETURN_30"]
    declared = declared_resolution_times(bars.index, ev["event_time"], 30, pd.Timedelta("1min"))
    assert (pd.DatetimeIndex(tg["effective_target_end"]) >= pd.DatetimeIndex(tg["target_end"])).all()
    assert (pd.DatetimeIndex(tg["effective_target_end"]) == declared).all()
    understated = pd.DatetimeIndex(tg["target_end"]) - pd.Timedelta("20min")                       # a lying claim
    eff = pd.DatetimeIndex(np.maximum(understated.asi8, declared.asi8)).tz_localize("UTC")
    assert (eff == declared).all() and (eff > understated).all()


def test_folds_below_frozen_minimums_are_skipped_never_relaxed():
    X, y, t, te = synth(60, (2016, 2017, 2018, 2019, 2020), seed=12)             # 300 events -> blocks of 50: fold 1 trains on 50
    res = run_walkforward(LinearProbe, X, y, t, te, CFG, folds_for(t))
    assert res.folds[0]["status"].startswith("SKIPPED_INSUFFICIENT_DATA")
    assert all(f["status"].startswith("SKIPPED_INSUFFICIENT_DATA") for f in res.folds)      # none reaches 300 training events
    assert CFG.min_outer_train_events == 300 == F.trial_policy["development_cv"]["min_outer_train_events"]
    assert (F.trial_policy["development_cv"]["inner_blocks"], F.trial_policy["development_cv"]["min_inner_train_events"],
            F.trial_policy["development_cv"]["min_inner_oof_events"]) == (5, 50, 30)
    assert len(res.validation) == 0


def test_changing_validation_labels_cannot_alter_thresholds_or_models():
    X, y, t, te = synth(400, slope=0.8, seed=7)
    folds = folds_for(t)
    base = run_walkforward(LinearProbe, X, y, t, te, CFG, folds)
    fd = folds[1]                                                       # alter fold 2's VALIDATION block labels
    idx = np.flatnonzero((t.asi8 >= fd.val_start_ns) & (t.asi8 < fd.val_end_ns))
    y2 = y.copy()
    y2[idx] = np.random.default_rng(99).normal(size=len(idx)) * 50 + 1000
    alt = run_walkforward(LinearProbe, X, y2, t, te, CFG, folds)
    for k in (1, 2):                                                    # folds whose training never contains those labels
        a = base.validation[base.validation.fold == k].reset_index(drop=True)
        b = alt.validation[alt.validation.fold == k].reset_index(drop=True)
        pd.testing.assert_frame_equal(a, b)
    assert [f.get("threshold") for f in base.folds[:2]] == [f.get("threshold") for f in alt.folds[:2]]


def test_states_are_halves_with_ties_excluded():
    s = np.array([-2.0, -1.0, 0.0, 0.0, 1.0, 2.0])
    st = assign_state(s, 0.0)
    assert st.tolist() == [LOWER, LOWER, "TIE", "TIE", UPPER, UPPER]


def test_validation_state_share_is_roughly_half_when_model_has_signal():
    X, y, t, te = synth(400, slope=1.0, seed=10)
    res = run_walkforward(make_model_factory("RIDGE", F), X, y, t, te, CFG, folds_for(t))
    share = (res.validation["state"] == UPPER).mean()
    assert 0.35 < share < 0.65
    assert len(res.importances) == 5 and len(res.coefficients) == 5            # Ridge diagnostics per fold


def test_target_transform_makes_xgb_scale_invariant_and_leaves_linear_models_unchanged():
    """Regression for the spec issue: literal XGB regularization is absolute, so on return-scale targets it is constant."""
    import copy
    import dataclasses
    X, y, t, te = synth(300, (2018, 2019), seed=21, slope=1.0)
    ys = y * 1e-3                                                          # realistic log-return scale
    literal_bank = copy.deepcopy(F.model_bank)
    literal_bank["target_transform"] = "none"
    F_literal = dataclasses.replace(F, model_bank=literal_bank)
    dead = FrozenModel("XGB", F_literal).fit(X, ys).predict(X)
    assert len(np.unique(dead)) == 1                                        # literal spec: constant model
    live = FrozenModel("XGB", F).fit(X, ys).predict(X)
    assert len(np.unique(live)) > 100 and np.corrcoef(live, y)[0, 1] > 0.3
    big = FrozenModel("XGB", F).fit(X, y).predict(X)                        # invariant: same ranking at any unit
    assert np.allclose(live * 1e3, big, rtol=1e-6, atol=1e-9)
    for name in ("RIDGE", "SPLINE"):                                        # exactly equivariant models: no change
        a = FrozenModel(name, F_literal).fit(X, ys).predict(X)
        b = FrozenModel(name, F).fit(X, ys).predict(X)
        assert np.allclose(a, b, rtol=1e-7, atol=1e-12)
    assert FrozenModel("RIDGE", F).fit(X, ys).predict(X).std() > 0 and F.model_bank["target_transform"] == "train_only_standardization"
