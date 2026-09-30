import math

import numpy as np
import pandas as pd
import pytest

from engine.target_engine import (compute_diagnostic_targets, compute_primary_targets, forward_start, to_long,
                                  window_span_violations)
from tests import helpers as H

F = H.FROZEN


def bars_for_targets(n=200, seed=1):
    return H.random_bars(n, seed=seed)


def test_long_and_short_signs_hand_calculated():
    # 60+ bars: signal bar 0 ; event_time = open(bar1). forward bars start at bar 1.
    n = 70
    closes = [100.0] * n
    opens = [100.0] * n
    highs = [100.0] * n
    lows = [100.0] * n
    # forward bar 1: open 100; make path: bar 1 high 103, low 99 ; bar 5 low 96 ; bar 15 close 101 ; bar 30 close 98 ; bar 60 close 104
    highs[1], lows[1] = 103.0, 99.0
    lows[5] = 96.0
    closes[15], closes[30], closes[60] = 101.0, 98.0, 104.0
    highs[60] = 104.0
    bars = H.make_bars(closes, opens=opens, highs=highs, lows=lows)
    # first forward bar is bar index 1 (open 100). bars 1..15 are forward bars 1..15
    ev_long = H.events_at(bars, [0], direction=1)
    ev_short = H.events_at(bars, [0], direction=-1)
    tl = compute_primary_targets(bars, ev_long, F)
    ts = compute_primary_targets(bars, ev_short, F)
    # 15th forward bar is bar 15 -> close 101 ; 30th -> bar 30 close 98 ; 60th -> bar 60 close 104
    assert tl["DIR_RETURN_15"]["value"].iloc[0] == pytest.approx(math.log(101 / 100))
    assert ts["DIR_RETURN_15"]["value"].iloc[0] == pytest.approx(-math.log(101 / 100))
    assert tl["DIR_RETURN_30"]["value"].iloc[0] == pytest.approx(math.log(98 / 100))
    assert ts["DIR_RETURN_30"]["value"].iloc[0] == pytest.approx(-math.log(98 / 100))
    assert tl["DIR_RETURN_60"]["value"].iloc[0] == pytest.approx(math.log(104 / 100))
    # long: MFE = log(104/100) (bar 60 high 104 > bar1 high 103) ; MAE = log(96/100)
    mfe_l, mae_l = math.log(104 / 100), math.log(96 / 100)
    assert tl["DIR_PATH_SKEW_60"]["value"].iloc[0] == pytest.approx(mfe_l + mae_l)
    # short: fav = -log(low/P0): max at low 96 -> -log(96/100)>0 ; adv = -log(high/P0): min at high 104 -> -log(1.04)
    mfe_s, mae_s = -math.log(96 / 100), -math.log(104 / 100)
    assert mae_s <= 0 <= mfe_s
    assert ts["DIR_PATH_SKEW_60"]["value"].iloc[0] == pytest.approx(mfe_s + mae_s)
    assert mae_l <= 0 <= mfe_l


def test_path_skew_sign_meaning():
    n = 70
    base = dict(opens=[100.0] * n, closes=[100.0] * n)
    up_dominated = H.make_bars(base["closes"], opens=base["opens"], highs=[100.0] * 2 + [110.0] + [100.0] * (n - 3),
                               lows=[100.0] * n)
    ev = H.events_at(up_dominated, [0], 1)
    assert compute_primary_targets(up_dominated, ev, F)["DIR_PATH_SKEW_60"]["value"].iloc[0] > 0
    ev_s = H.events_at(up_dominated, [0], -1)
    assert compute_primary_targets(up_dominated, ev_s, F)["DIR_PATH_SKEW_60"]["value"].iloc[0] < 0


def test_target_bars_start_at_event_time_and_exclude_signal_bar():
    bars = bars_for_targets(200)
    pos = 50                                    # signal bar
    ev = H.events_at(bars, [pos])
    first = forward_start(bars, ev["event_time"])
    assert first[0] == pos + 1                  # first bar with open >= event_time (= signal bar close)
    t = compute_primary_targets(bars, ev, F)
    assert t["DIR_RETURN_15"]["target_start"].iloc[0] == bars.index[pos + 1]
    assert t["DIR_RETURN_15"]["target_start"].iloc[0] >= ev["event_time"].iloc[0]
    p0 = bars["open"].iloc[pos + 1]
    expect = math.log(bars["close"].iloc[pos + 15] / p0)
    assert t["DIR_RETURN_15"]["value"].iloc[0] == pytest.approx(expect)
    assert t["DIR_RETURN_15"]["target_end"].iloc[0] == bars.index[pos + 15] + pd.Timedelta("1min")


def test_signal_bar_movement_never_enters_target():
    bars = bars_for_targets(200, seed=3)
    pos = 60
    ev = H.events_at(bars, [pos])
    a = compute_primary_targets(bars, ev, F)
    mutated = bars.copy()
    mutated.iloc[pos] = mutated.iloc[pos] * 1.5    # wreck the signal bar itself, and all before
    mutated.iloc[:pos] = mutated.iloc[:pos] * 0.3
    b = compute_primary_targets(mutated, ev, F)
    for k in a:
        assert a[k]["value"].iloc[0] == b[k]["value"].iloc[0]


def test_event_at_bar_open_uses_that_bar_as_first_forward_bar():
    bars = bars_for_targets(200, seed=4)
    ev = pd.DataFrame({"event_id": ["E"], "event_time": [bars.index[70]], "direction": [1]})
    assert forward_start(bars, ev["event_time"])[0] == 70


def test_unresolved_tail_events_omitted_by_timestamp_only():
    bars = bars_for_targets(100, seed=5)
    ev = H.events_at(bars, [10, 30, 39, 50])
    t = compute_primary_targets(bars, ev, F)
    # 60-bar windows: signal pos p needs bars p+1..p+60 <= 99 -> p <= 39
    assert set(t["DIR_RETURN_60"]["event_id"]) == {"E0", "E1", "E2"}
    assert set(t["DIR_RETURN_15"]["event_id"]) == {"E0", "E1", "E2", "E3"}   # 50+15=65 <= 99


def test_to_long_shape_and_names():
    bars = bars_for_targets(200, seed=6)
    ev = H.events_at(bars, [10, 20])
    long = to_long(compute_primary_targets(bars, ev, F))
    assert set(long["target_name"]) == {"DIR_RETURN_15", "DIR_RETURN_30", "DIR_RETURN_60", "DIR_PATH_SKEW_60"}
    assert len(long) == 8
    assert (long["target_start"] >= pd.to_datetime(ev["event_time"].iloc[0])).all()


def test_exactly_four_primary_targets():
    from engine.common import primary_target_names
    assert primary_target_names(F) == ["DIR_RETURN_15", "DIR_RETURN_30", "DIR_RETURN_60", "DIR_PATH_SKEW_60"]


def test_diagnostic_targets_computed_but_separate():
    bars = bars_for_targets(400, seed=7)
    ev = H.events_at(bars, [50, 100], direction=1)
    sigma = np.array([0.001, 0.001])
    d = compute_diagnostic_targets(bars, ev, F, sigma)
    for col in ("DIAG_RET_5", "DIAG_RET_120", "DIAG_MFE_15", "DIAG_MAE_120", "DIAG_TIME_TO_MFE_60",
                "DIAG_FIRST_PASSAGE_1.0", "DIAG_FIRST_PASSAGE_0.5", "DIAG_PATH_LENGTH_60",
                "DIAG_PATH_EFFICIENCY_60", "DIAG_FWD_RV_60"):
        assert col in d.columns
    assert (d["DIAG_MAE_60"] <= 0).all() and (d["DIAG_MFE_60"] >= 0).all()
    c = bars["close"].to_numpy(); o = bars["open"].to_numpy()
    assert d["DIAG_RET_5"].iloc[0] == pytest.approx(math.log(c[50 + 5] / o[51]))
    assert ((d["DIAG_PATH_EFFICIENCY_60"] >= 0) & (d["DIAG_PATH_EFFICIENCY_60"] <= 1)).all()


def test_window_span_violation_counter():
    idx = list(pd.date_range("2020-01-07 14:31", periods=30, freq="1min")) + \
          list(pd.date_range("2020-01-08 14:31", periods=60, freq="1min"))
    closes = np.linspace(100, 110, len(idx))
    bars = pd.DataFrame({"open": closes, "high": closes + 1, "low": closes - 1, "close": closes, "volume": 1.0},
                        index=pd.DatetimeIndex(idx, tz="UTC"))
    ev = H.events_at(bars, [10])        # 60-bar window crosses the overnight gap
    assert window_span_violations(bars, ev, 60, pd.Timedelta("1min")) == 1
