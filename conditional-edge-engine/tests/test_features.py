import math

import numpy as np
import pandas as pd
import pytest

from engine.common import load_frozen
from engine.feature_engine import (FeatureQualityFailure, assert_feature_quality, compute_features,
                                   feature_names, model_eligibility)
from tests import helpers as H

F = H.FROZEN


def feats(bars, positions):
    return compute_features(bars, H.events_at(bars, positions), F)


def test_exactly_56_frozen_features_unique_and_ordered():
    names = feature_names(F)
    assert len(names) == 56 == len(set(names))
    assert names[0] == "RET_5" and names[-1] == "day_of_week"
    counts = {"RET": 6, "RV": 6, "ER": 5, "BROWNIAN_DISP": 5, "VR": 9, "HURST": 3, "COUNT_BALANCE": 3,
              "BODY_BALANCE": 3, "RANGE_POS": 4, "VOV": 3, "SIGNED_VOLUME": 3}
    for prefix, n in counts.items():
        got = [x for x in names if x.startswith(prefix + "_")]
        assert len(got) == n, (prefix, got)
    assert sum(1 for x in names if x in ("minutes_since_RTH_open", "sin_RTH_phase", "cos_RTH_phase",
              "RTH_return_from_open", "distance_from_causal_session_VWAP", "day_of_week")) == 6


# ---- hand-calculated examples --------------------------------------------------------------
def test_er_hand_calculated_and_denominator():
    # closes 10,11,10,12,13 ; L=4 at t=4: |13-10| / (1+1+2+1) = 3/5
    closes = [10, 11, 10, 12, 13]
    bars = H.make_bars(closes)
    f = compute_features(bars, H.events_at(bars, [4]), load_frozen())
    # only lookbacks >=15 exist in the bank -> verify formula through the module directly
    from features.kaufman_er import compute
    from engine.feature_engine import _make_ctx
    ctx = _make_ctx(bars, F)
    out = compute(ctx, np.array([4]), {"lookbacks": [4]})
    assert out["ER_4"][0] == pytest.approx(0.6, abs=1e-15)
    flat = H.make_bars([5, 5, 5, 5, 5])
    out = compute(_make_ctx(flat, F), np.array([4]), {"lookbacks": [4]})
    assert math.isnan(out["ER_4"][0])            # zero denominator -> NaN


def test_er_uses_all_path_steps_not_smoothed():
    # path 0 -> +2 -> -2(+... ) closes 100,102,98,100,101 L=4: |101-100| / (2+4+2+1) = 1/9
    from features.kaufman_er import compute
    from engine.feature_engine import _make_ctx
    bars = H.make_bars([100, 102, 98, 100, 101])
    out = compute(_make_ctx(bars, F), np.array([4]), {"lookbacks": [4]})
    assert out["ER_4"][0] == pytest.approx(1 / 9, abs=1e-15)


def test_ret_and_rv_hand_calculated():
    from features.returns import compute as cr
    from features.volatility import compute as cv
    from engine.feature_engine import _make_ctx
    bars = H.make_bars([100, 101, 99, 102])
    ctx = _make_ctx(bars, F)
    pos = np.array([3])
    assert cr(ctx, pos, {"lookbacks": [3]})["RET_3"][0] == pytest.approx(math.log(102 / 100), abs=1e-15)
    rv = cv(ctx, pos, {"rv_lookbacks": [3], "vov_lookbacks": []})["RV_3"][0]
    expect = math.sqrt(math.log(101 / 100) ** 2 + math.log(99 / 101) ** 2 + math.log(102 / 99) ** 2)
    assert rv == pytest.approx(expect, abs=1e-15)


def test_brownian_displacement_hand_calculated():
    from features.brownian import compute
    from engine.feature_engine import _make_ctx
    bars = H.make_bars([100, 101, 99, 102])
    out = compute(_make_ctx(bars, F), np.array([3]), {"disp_lookbacks": [3], "vr_windows": [], "vr_lags": []})
    r = [math.log(101 / 100), math.log(99 / 101), math.log(102 / 99)]
    assert out["BROWNIAN_DISP_3"][0] == pytest.approx(sum(r) / math.sqrt(sum(x * x for x in r)), abs=1e-15)
    # a monotone path with equal steps approaches sqrt(L)
    up = H.make_bars([100 * 1.001 ** i for i in range(6)])
    v = compute(_make_ctx(up, F), np.array([5]), {"disp_lookbacks": [5], "vr_windows": [], "vr_lags": []})
    assert v["BROWNIAN_DISP_5"][0] == pytest.approx(math.sqrt(5), rel=1e-12)


def test_variance_ratio_exact_q_aggregation_hand_example():
    # W=5 closes: 1,2,4,8,16 -> x = log; q=2 blocks anchored at t: (x4-x2),(x2-x0)
    from features.brownian import compute
    from engine.feature_engine import _make_ctx
    flat = H.make_bars([5.0] * 5)
    out = compute(_make_ctx(flat, F), np.array([4]), {"disp_lookbacks": [], "vr_windows": [5], "vr_lags": [2]})
    assert math.isnan(out["VR_5_2"][0])            # zero 1-bar variance -> denominator zero -> NaN
    closes = [1.0, 2.0, 3.0, 7.0, 8.0]
    bars = H.make_bars(closes)
    out = compute(_make_ctx(bars, F), np.array([4]), {"disp_lookbacks": [], "vr_windows": [5], "vr_lags": [2]})
    x = [math.log(v) for v in closes]
    one = [x[i] - x[i - 1] for i in range(1, 5)]
    q2 = [x[4] - x[2], x[2] - x[0]]                       # non-overlapping, anchored at t
    def pv(a):
        m = sum(a) / len(a); return sum((v - m) ** 2 for v in a) / len(a)
    assert out["VR_5_2"][0] == pytest.approx(pv(q2) / (2 * pv(one)), abs=1e-14)
    # the OVERLAPPING alternative would give a different number -> proves non-overlap is used
    overlapping = [x[i] - x[i - 2] for i in range(2, 5)]
    assert pv(overlapping) / (2 * pv(one)) != pytest.approx(out["VR_5_2"][0], rel=1e-6)


def test_variance_ratio_partial_block_dropped_when_not_divisible():
    # W=6 closes, q=4 -> m = (6-1)//4 = 1 block: x5 - x1 (x0 unused by q-bar returns)
    from features.brownian import compute
    from engine.feature_engine import _make_ctx
    closes = [3.0, 4.0, 4.5, 6.0, 5.0, 7.0]
    bars = H.make_bars(closes)
    out = compute(_make_ctx(bars, F), np.array([5]), {"disp_lookbacks": [], "vr_windows": [6], "vr_lags": [4]})
    # one q-bar return -> its population variance is 0 -> VR = 0
    assert out["VR_6_4"][0] == 0.0


def test_hurst_exact_lags_and_random_walk_scaling():
    # deterministic x with V(k) = k^2 (straight line in log price) -> b=2 -> H=1 exactly
    from features.hurst import hurst_from_windows
    W = 40
    x = 0.01 * np.arange(W, dtype=float)[None, :]
    h = hurst_from_windows(x, [1, 2, 4, 8, 16], 4)
    assert h[0] == pytest.approx(1.0, abs=1e-12)
    # V(k) = k (pure diffusion in expectation): build x such that mean sq diffs are not exactly k, so
    # compare the vectorized result to the plain-python OLS reference instead
    bars = H.random_bars(700, seed=11)
    c = bars["close"].to_numpy()
    f = feats(bars, [699, 650])
    for row, t in enumerate([699, 650]):
        for W in (120, 240, 480):
            assert f[f"HURST_{W}"].iloc[row] == pytest.approx(H.ref_hurst(c, t, W), abs=1e-10)


def test_hurst_uses_only_lags_1_2_4_8_16_and_nan_rule():
    from features.hurst import hurst_from_windows
    flat = np.zeros((1, 50))
    assert math.isnan(hurst_from_windows(flat, [1, 2, 4, 8, 16], 4)[0])     # all V=0 -> <4 valid
    w = np.cumsum(np.random.default_rng(0).normal(size=(1, 60)), axis=1) * 0.01
    a = hurst_from_windows(w, [1, 2, 4, 8, 16], 4)[0]
    b = hurst_from_windows(w, [1, 2, 3, 5, 7], 4)[0]
    assert a != b                                                              # lag bank matters


@pytest.mark.parametrize("seed", [1, 2])
def test_all_formula_features_match_independent_reference(seed):
    bars = H.random_bars(1000, seed=seed)
    o, h, l, c, v = (bars[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    positions = [500, 617, 999]
    f = feats(bars, positions)
    for row, t in enumerate(positions):
        g = lambda name: f[name].iloc[row]
        for L in (5, 15, 30, 60, 120, 240):
            assert g(f"RET_{L}") == pytest.approx(H.ref_ret(c, t, L), abs=1e-12)
            assert g(f"RV_{L}") == pytest.approx(H.ref_rv(c, t, L), abs=1e-12)
        for L in (15, 30, 60, 120, 240):
            assert g(f"ER_{L}") == pytest.approx(H.ref_er(c, t, L), abs=1e-12)
            assert g(f"BROWNIAN_DISP_{L}") == pytest.approx(H.ref_disp(c, t, L), abs=1e-12)
        for W in (60, 120, 240):
            for q in (2, 4, 8):
                assert g(f"VR_{W}_{q}") == pytest.approx(H.ref_vr(c, t, W, q), abs=1e-10)
        for W in (120, 240, 480):
            assert g(f"HURST_{W}") == pytest.approx(H.ref_hurst(c, t, W), abs=1e-10)
        for L in (15, 30, 60):
            assert g(f"COUNT_BALANCE_{L}") == pytest.approx(H.ref_count_balance(o, c, t, L), abs=1e-15)
            assert g(f"BODY_BALANCE_{L}") == pytest.approx(H.ref_body_balance(o, c, t, L), abs=1e-12)
            assert g(f"SIGNED_VOLUME_{L}") == pytest.approx(H.ref_signed_volume(o, c, v, t, L), abs=1e-12)
        for L in (15, 30, 60, 120):
            assert g(f"RANGE_POS_{L}") == pytest.approx(H.ref_range_pos(h, l, c, t, L), abs=1e-12)
        for L in (30, 60, 120):
            assert g(f"VOV_{L}") == pytest.approx(H.ref_vov(h, l, c, t, L), abs=1e-10)


def test_candle_and_range_and_volume_hand_calculated():
    from features.candles import compute as cc
    from features.range import compute as cr
    from features.volume import compute as cvol
    from engine.feature_engine import _make_ctx
    o = [10, 10, 10, 10]
    c = [11, 9, 10, 13]          # +1, -1, 0, +1 ; bodies +1, -1, 0, +3
    h = [12, 11, 10.5, 14]
    l = [9.5, 8, 9.5, 9.0]
    v = [100, 200, 300, 400]
    bars = H.make_bars(c, opens=o, highs=h, lows=l, volumes=v)
    ctx = _make_ctx(bars, F)
    pos = np.array([3])
    out = cc(ctx, pos, {"lookbacks": [4]})
    assert out["COUNT_BALANCE_4"][0] == pytest.approx(1 / 4)
    assert out["BODY_BALANCE_4"][0] == pytest.approx(3 / 5)
    rp = cr(ctx, pos, {"lookbacks": [4]})["RANGE_POS_4"][0]
    assert rp == pytest.approx((13 - 8) / (14 - 8))
    sv = cvol(ctx, pos, {"lookbacks": [4]})["SIGNED_VOLUME_4"][0]
    assert sv == pytest.approx((100 - 200 + 0 + 400) / 1000)
    # zero range -> 0.5 ; zero volume -> NaN ; zero body sum -> NaN
    flat = H.make_bars([5, 5, 5], opens=[5, 5, 5], highs=[5, 5, 5], lows=[5, 5, 5], volumes=[0, 0, 0])
    fc = _make_ctx(flat, F)
    assert cr(fc, np.array([2]), {"lookbacks": [3]})["RANGE_POS_3"][0] == 0.5
    assert math.isnan(cvol(fc, np.array([2]), {"lookbacks": [3]})["SIGNED_VOLUME_3"][0])
    assert math.isnan(cc(fc, np.array([2]), {"lookbacks": [3]})["BODY_BALANCE_3"][0])


def test_true_range_uses_previous_close_and_vov_ddof0():
    from features.volatility import true_range, compute
    from engine.feature_engine import _make_ctx
    # gap up: high-low small but |high - prev_close| large
    bars = H.make_bars([100, 110, 111], opens=[100, 110, 110.5], highs=[100.5, 110.5, 111.5], lows=[99.5, 109.5, 110.2])
    ctx = _make_ctx(bars, F)
    tr = true_range(ctx)
    assert math.isnan(tr[0]) and tr[1] == pytest.approx(10.5) and tr[2] == pytest.approx(1.5)
    out = compute(ctx, np.array([2]), {"rv_lookbacks": [], "vov_lookbacks": [2]})
    assert out["VOV_2"][0] == pytest.approx(np.std([10.5, 1.5], ddof=0)) == pytest.approx(4.5)


# ---- session features ----------------------------------------------------------------------
def _session_bars():
    # 2020-01-08 (Wed) RTH: 09:30 NY = 14:30 UTC. Build bars from 09:25 NY.
    start = pd.Timestamp("2020-01-08 14:25:00", tz="UTC")
    n = 20
    idx = pd.date_range(start, periods=n, freq="1min")
    close = 100 + np.arange(n, dtype=float)
    open_ = np.concatenate([[100.0], close[:-1]])
    bars = pd.DataFrame({"open": open_, "high": close + 1, "low": open_ - 1, "close": close,
                         "volume": np.full(n, 10.0)}, index=idx)
    return bars


def test_session_features_hand_calculated():
    bars = _session_bars()
    # signal bar = 09:34 (pos 9): event_time = 09:35 NY ; 5 RTH bars completed (09:30..09:34)
    f = compute_features(bars, H.events_at(bars, [9]), F)
    assert f["minutes_since_RTH_open"].iloc[0] == pytest.approx(5.0)
    assert f["sin_RTH_phase"].iloc[0] == pytest.approx(math.sin(2 * math.pi * 5 / 390))
    assert f["cos_RTH_phase"].iloc[0] == pytest.approx(math.cos(2 * math.pi * 5 / 390))
    # open of first RTH bar (09:30) is bars.open[5] = close[4] = 104 ; close_t = close[9] = 109
    assert f["RTH_return_from_open"].iloc[0] == pytest.approx(math.log(109 / 104))
    assert f["day_of_week"].iloc[0] == 2.0               # Wednesday
    # causal VWAP over ALL completed session bars pos 0..9 (ETH session incl. 09:25-09:29 bars)
    tp = (bars["high"] + bars["low"] + bars["close"]) / 3
    vwap = (tp.iloc[:10] * 10).sum() / 100
    assert f["distance_from_causal_session_VWAP"].iloc[0] == pytest.approx(109 / vwap - 1)


def test_session_vwap_resets_at_eth_start_not_midnight():
    # bars spanning 17:50 - 18:10 NY on Tue 2020-01-07 (22:50-23:10 UTC): 18:00 starts a NEW session
    idx = pd.date_range("2020-01-07 22:50:00", periods=20, freq="1min", tz="UTC")
    close = np.linspace(100, 119, 20)
    bars = pd.DataFrame({"open": close, "high": close + 0.5, "low": close - 0.5, "close": close,
                         "volume": np.full(20, 10.0)}, index=idx)
    f = compute_features(bars, H.events_at(bars, [15]), F)   # bar 23:05 UTC = 18:05 NY
    sub = bars.iloc[10:16]                                    # 18:00..18:05 NY bars only
    tp = (sub["high"] + sub["low"] + sub["close"]) / 3
    vwap = (tp * 10).sum() / 60
    assert f["distance_from_causal_session_VWAP"].iloc[0] == pytest.approx(close[15] / vwap - 1)


# ---- causality / warm-up -------------------------------------------------------------------
def test_features_ignore_bars_after_event_time_even_if_garbage():
    bars = H.random_bars(1200, seed=5)
    pos = [520, 700, 900]
    ev = H.events_at(bars, pos)
    base = compute_features(bars, ev, F)
    for cut in pos:
        mutated = bars.copy()
        mutated.iloc[cut + 1:] = mutated.iloc[cut + 1:] * np.array([7.0, -3.0, 0.01, 5.0, 123.0])
        trunc_events = ev[ev["event_time"] <= bars.index[cut] + pd.Timedelta("1min")]
        m = compute_features(mutated, trunc_events, F)
        names = feature_names(F)
        b = base[base["event_id"].isin(trunc_events["event_id"])]
        pd.testing.assert_frame_equal(b[names].reset_index(drop=True), m[names].reset_index(drop=True), check_exact=False, rtol=1e-12, atol=0)


def test_features_identical_under_truncation():
    bars = H.random_bars(1300, seed=6)
    pos = [500, 800, 1000]
    ev = H.events_at(bars, pos)
    full = compute_features(bars, ev, F)
    names = feature_names(F)
    for k, p in enumerate(pos):
        sub_bars = bars.iloc[: p + 1]
        sub = compute_features(sub_bars, ev.iloc[[k]], F)
        pd.testing.assert_frame_equal(full.iloc[[k]][names].reset_index(drop=True), sub[names].reset_index(drop=True),
                                      check_exact=False, rtol=1e-12, atol=0)


def test_event_stamped_at_bar_open_cannot_see_that_bar():
    # event_time == open of bar p : bar p is NOT complete, so the last completed bar is p-1
    bars = H.random_bars(700, seed=8)
    p = 600
    ev = pd.DataFrame({"event_id": ["E"], "event_time": [bars.index[p]], "direction": [1]})
    f = compute_features(bars, ev, F)
    assert f.attrs["completed_bars"][0] == p
    c = bars["close"].to_numpy()
    assert f["RET_5"].iloc[0] == pytest.approx(math.log(c[p - 1] / c[p - 6]), abs=1e-12)


def test_short_warmup_rows_exist_but_are_nan_and_not_model_eligible():
    bars = H.random_bars(700, seed=9)
    ev = H.events_at(bars, [3, 30, 250, 478, 479, 600])
    f = compute_features(bars, ev, F)
    assert len(f) == 6                                        # rows are NEVER omitted
    assert np.isnan(f.loc[0, "RET_5"]) and np.isnan(f.loc[0, "HURST_480"])
    assert np.isfinite(f.loc[2, "RET_240"]) and np.isnan(f.loc[2, "HURST_480"])   # 251 bars only
    el = model_eligibility(f, F)
    assert el.tolist() == [False, False, False, False, True, True]   # completed bars 4,31,251,479,480,601
    # exactly 480 completed bars -> Hurst-480 finite
    assert np.isnan(f.loc[3, "HURST_480"]) and np.isfinite(f.loc[4, "HURST_480"])   # 479 vs 480 bars


def test_feature_quality_failure_on_unexpected_nan_after_warmup():
    bars = H.random_bars(700, seed=10)
    bars.loc[bars.index[300:601], "volume"] = 0.0           # zero volume windows -> SIGNED_VOLUME NaN
    ev = H.events_at(bars, [600])
    f = compute_features(bars, ev, F)
    el = model_eligibility(f, F)
    assert el[0]
    with pytest.raises(FeatureQualityFailure):
        assert_feature_quality(f, el, F)


def test_clean_data_passes_quality_after_warmup_and_is_not_imputed():
    bars = H.random_bars(900, seed=12)
    ev = H.events_at(bars, [480, 600, 800])
    f = compute_features(bars, ev, F)
    el = model_eligibility(f, F)
    assert el.all()
    assert_feature_quality(f, el, F)
