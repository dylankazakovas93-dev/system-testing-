import numpy as np
import pandas as pd
import pytest

from engine.common import load_frozen
from engine.feature_engine import feature_names
from engine.model_engine import FrozenModel, make_model_factory
from engine.score_calibration import UPPER, LOWER, WFConfig, assign_state, calibrate_threshold, inner_oof_predictions
from engine.walkforward import run_walkforward

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
    """Deterministic fake: prediction = ridge-free OLS slope on ER_60 only (fast, transparent)."""

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
    # recompute independently: blocks of the ordered training set, purge by target_end
    order = train[np.argsort(ev[train], kind="stable")]
    segs = np.array_split(order, 5)
    manual = []
    for j in range(1, 5):
        prior = np.concatenate(segs[:j]); prior = prior[tend[prior] < ev[segs[j][0]]]
        mdl = LinearProbe().fit(X.iloc[prior], y[prior])
        manual.append(mdl.predict(X.iloc[segs[j]]))
    assert thr == pytest.approx(float(np.median(np.concatenate(manual))))
    assert len(pred) == sum(len(s) for s in segs[1:])            # first block is never predicted
    # validation-year scores have a different median -> threshold is NOT derived from them
    val = np.flatnonzero(t >= pd.Timestamp("2018-01-01", tz="UTC"))
    full = LinearProbe().fit(X.iloc[train], y[train])
    assert thr != pytest.approx(float(np.median(full.predict(X.iloc[val]))), abs=1e-12)


def test_changing_outer_validation_labels_cannot_alter_thresholds_or_models():
    X, y, t, te = synth(400, slope=0.8, seed=7)
    base = run_walkforward(LinearProbe, X, y, t, te, CFG)
    target_year = 2019
    y2 = y.copy()
    idx = np.flatnonzero(t.year == target_year)
    y2[idx] = np.random.default_rng(99).normal(size=len(idx)) * 50 + 1000   # wreck validation-year labels
    alt = run_walkforward(LinearProbe, X, y2, t, te, CFG)
    for yr in (2017, 2018, 2019):       # folds whose training never contains the altered labels
        a = base.oos[base.oos.year == yr].reset_index(drop=True)
        b = alt.oos[alt.oos.year == yr].reset_index(drop=True)
        pd.testing.assert_frame_equal(a, b)
    assert [f.get("threshold") for f in base.folds if f["year"] <= 2019] == \
           [f.get("threshold") for f in alt.folds if f["year"] <= 2019]


def test_purged_events_and_future_labels_never_reach_the_model():
    X, y, t, te = synth(400, slope=0.8, seed=8, horizon_min=60 * 24 * 40)    # 40-day target windows
    base = run_walkforward(LinearProbe, X, y, t, te, CFG)
    vs = pd.Timestamp("2019-01-01", tz="UTC")
    forbidden = (te >= vs)                                                    # purged + validation + future
    y2 = y.copy(); y2[np.asarray(forbidden)] = 9999.0
    alt = run_walkforward(LinearProbe, X, y2, t, te, CFG)
    a = base.oos[base.oos.year == 2019].reset_index(drop=True)
    b = alt.oos[alt.oos.year == 2019].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)
    # and: some training events really were purged (windows crossing the boundary)
    crossing = np.asarray((t < vs) & (te >= vs)).sum()
    assert crossing > 0


def test_walkforward_is_chronological_expanding_and_skips_short_history():
    X, y, t, te = synth(400, slope=0.0, seed=9)
    res = run_walkforward(LinearProbe, X, y, t, te, CFG)
    status = {f["year"]: f["status"] for f in res.folds}
    assert status[2016].startswith("SKIPPED")                  # no history at all
    assert status[2017] == "OK"                                # 400 >= 300
    ntr = [f["n_train"] for f in res.folds]
    assert ntr == sorted(ntr)                                  # expanding
    assert set(res.oos.year.unique()) == {2017, 2018, 2019, 2020}
    for yr, g in res.oos.groupby("year"):
        assert (t[g["pos"].to_numpy()].year == yr).all()       # OOS rows only from their own year


def test_states_are_halves_with_ties_excluded():
    s = np.array([-2.0, -1.0, 0.0, 0.0, 1.0, 2.0])
    st = assign_state(s, 0.0)
    assert st.tolist() == [LOWER, LOWER, "TIE", "TIE", UPPER, UPPER]


def test_oos_state_share_is_roughly_half_when_model_has_signal():
    X, y, t, te = synth(400, slope=1.0, seed=10)
    res = run_walkforward(make_model_factory("RIDGE", F), X, y, t, te, CFG)
    share = (res.oos["state"] == UPPER).mean()
    assert 0.35 < share < 0.65
    assert len(res.importances) == len(res.oos.year.unique())


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
