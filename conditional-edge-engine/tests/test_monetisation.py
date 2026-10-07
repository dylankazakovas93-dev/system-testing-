"""Monetisation (bracket) study mechanics on hand-built and synthetic bars (v2.3.0). Development-style data only."""
import copy

import numpy as np
import pandas as pd
import pytest

from engine import monetisation as M
from engine.common import load_frozen
from engine.synthetic import make_bars

F = load_frozen()
SPEC = M.load_spec()
COST = SPEC["costs"]["round_trip_ticks"] * F.tick_size                      # 3 ticks x 0.25 = 0.75 points


def flat_bars(days=3, start="2021-03-01"):
    """RTH 1-minute bars, price 100, true range exactly 1.0 (high 100.5 / low 99.5) -> ATR(14) = 1.0 after warm-up."""
    b = make_bars(days, start=start, seed=1, vol=0.0)
    b["open"] = b["close"] = 100.0
    b["high"], b["low"] = 100.5, 99.5
    return b


def event_at(bars, day_pos, minute_pos, direction=1):
    t = bars.index[day_pos * 390 + minute_pos]
    return pd.DataFrame({"event_time": [t], "direction": [direction]}), day_pos * 390 + minute_pos


def sim_one(bars, ev, k_stop, k_target, expiry):
    et = pd.DatetimeIndex(ev["event_time"])
    atr = M.atr_at_events(bars, et, "1m", 14, F)
    w = M.Windows(bars, et, ev["direction"].to_numpy(), 120, F)
    return M.simulate(w, atr, k_stop, k_target, expiry, COST), atr


def test_wilder_atr_constant_range_and_warmup():
    b = flat_bars(1)
    a = M.wilder_atr(b["high"].to_numpy(), b["low"].to_numpy(), b["close"].to_numpy(), 14)
    assert np.isnan(a[:14]).all() and np.allclose(a[14:], 1.0)


def test_atr_uses_only_completed_bars():
    b = flat_bars(1)
    ev, pos = event_at(b, 0, 60)
    base = M.atr_at_events(b, ev["event_time"], "1m", 14, F)[0]
    b2 = b.copy()
    b2.iloc[pos, b2.columns.get_loc("high")] = 150.0                     # the bar OPENING at event_time is not complete yet
    assert M.atr_at_events(b2, ev["event_time"], "1m", 14, F)[0] == base
    b3 = b.copy()
    b3.iloc[pos - 1, b3.columns.get_loc("high")] = 150.0                 # the previous bar is complete -> it may move the ATR
    assert M.atr_at_events(b3, ev["event_time"], "1m", 14, F)[0] > base
    assert np.isnan(M.atr_at_events(b, ev["event_time"], "5m", 14, F)[0])             # 12 completed 5-minute bars < warm-up of 14
    ev2, _ = event_at(b, 0, 200)
    assert M.atr_at_events(b, ev2["event_time"], "5m", 14, F)[0] == pytest.approx(1.0)


def set_bar(b, pos, high=None, low=None, close=None):
    for k, v in (("high", high), ("low", low), ("close", close)):
        if v is not None:
            b.iloc[pos, b.columns.get_loc(k)] = v


def test_target_stop_ambiguous_and_expiry_outcomes():
    b = flat_bars()
    ev, pos = event_at(b, 1, 60)
    # entry at the open of bar pos (100). target 2 ATR = +2 -> bar pos+3 reaches 102.1
    b2 = b.copy(); set_bar(b2, pos + 3, high=102.1)
    s, _ = sim_one(b2, ev, 1.0, 2.0, 60)
    assert s["target_hit"][0] and s["net"][0] == pytest.approx(2.0 - COST)
    # stop 1 ATR = -1 -> bar pos+2 reaches 98.9 first
    b3 = b.copy(); set_bar(b3, pos + 2, low=98.9); set_bar(b3, pos + 5, high=103.0)
    s, _ = sim_one(b3, ev, 1.0, 2.0, 60)
    assert s["stopped"][0] and not s["target_hit"][0] and s["net"][0] == pytest.approx(-1.0 - COST)
    # same bar touches both -> counted as a stop
    b4 = b.copy(); set_bar(b4, pos + 4, high=102.5, low=98.5)
    s, _ = sim_one(b4, ev, 1.0, 2.0, 60)
    assert s["stopped"][0] and s["net"][0] == pytest.approx(-1.0 - COST)
    # neither: expires at the close of the last allowed bar (15 bars -> bar pos+14), marked to market
    b5 = b.copy(); set_bar(b5, pos + 14, close=100.4); set_bar(b5, pos + 15, close=120.0)
    s, _ = sim_one(b5, ev, 3.0, 3.0, 15)
    assert not s["target_hit"][0] and not s["stopped"][0] and s["net"][0] == pytest.approx(0.4 - COST)
    # short: mirror image
    evs, _ = event_at(b, 1, 60, direction=-1)
    b6 = b.copy(); set_bar(b6, pos + 3, low=97.9)
    s, _ = sim_one(b6, evs, 1.0, 2.0, 60)
    assert s["target_hit"][0] and s["net"][0] == pytest.approx(2.0 - COST)


def test_window_is_truncated_at_the_rth_close_and_no_overnight_hold():
    b = flat_bars()
    ev, pos = event_at(b, 0, 388)                                         # 2 bars before the close
    et = pd.DatetimeIndex(ev["event_time"])
    w = M.Windows(b, et, ev["direction"].to_numpy(), 120, F)
    assert w.n_eff[0] == 2
    b2 = b.copy(); set_bar(b2, 390 + 3, high=150.0)                        # next session must never be reached
    s, _ = sim_one(b2, ev, 3.0, 1.0, 120)
    assert not s["target_hit"][0]


def test_events_without_atr_or_forward_bars_are_dropped():
    b = flat_bars(1)
    ev, _ = event_at(b, 0, 5)                                              # ATR warm-up
    s, _ = sim_one(b, ev, 1.0, 1.0, 30)
    assert len(s["net"]) == 0


def planted_events(bars, seed=3, every=40):
    rng = np.random.default_rng(seed)
    n_days = len(bars) // 390
    rows = []
    for d in range(n_days):
        for m in range(120, 330, every):
            rows.append((bars.index[d * 390 + m], 1))
    return pd.DataFrame(rows, columns=["event_time", "direction"])


def drift_bars(days, seed, drift):
    """Random-walk bars; after every planted event the next 50 minutes drift up by ``drift`` per minute."""
    b = make_bars(days, start="2018-01-02", seed=seed, vol=0.0004)
    ev = planted_events(b)
    c = b["close"].to_numpy().copy()
    log_inc = np.diff(np.log(c), prepend=np.log(c[0]))
    pos = b.index.get_indexer(ev["event_time"])
    for p in pos:
        log_inc[p:p + 50] += drift
    new_c = np.exp(np.log(c[0]) + np.cumsum(log_inc))
    o = np.r_[new_c[0], new_c[:-1]]
    hi = np.maximum(o, new_c) * (1 + 0.0002)
    lo = np.minimum(o, new_c) * (1 - 0.0002)
    return pd.DataFrame({"open": o, "high": hi, "low": lo, "close": new_c, "volume": 100.0}, index=b.index), ev


FAST = copy.deepcopy(SPEC)
FAST["pick"]["min_trades"] = 50
FAST["grid"]["expiry_bars"] = [30, 60]


def test_pure_noise_gives_no_stable_bracket():
    b, ev = drift_bars(160, seed=11, drift=0.0)
    out = M.run_study(b, ev, F, FAST)
    assert out["decision"] == M.NO_STABLE and out["chosen"] is None and out["n_stable"] == 0
    assert out["n_cells"] == 2 * 3 * 3 * 2                                  # atr bases x stops x targets x expiries


def test_planted_edge_finds_a_bracket_with_stable_neighbours_and_is_deterministic():
    b, ev = drift_bars(160, seed=11, drift=0.0006)
    a = M.run_study(b, ev, F, FAST)
    again = M.run_study(b, ev, F, FAST)
    assert a["decision"] == "BRACKET_FOUND" and a["chosen"] == again["chosen"] and a["n_stable"] >= 1
    c = a["chosen"]
    assert c["stable"] and c["net_expectancy"] > 0 and c["min_neighbour_expectancy"] > 0
    assert c["min_neighbour_expectancy"] >= SPEC["neighbours"]["min_retained_expectancy_fraction"] * c["net_expectancy"]
    best = max(x["neighbourhood_score"] for x in a["cells"] if x["stable"])
    assert c["neighbourhood_score"] == pytest.approx(best)                   # the pick is the stable cell with the best whole neighbourhood
    assert a["cost_points_round_trip"] == pytest.approx(COST) and a["label"].startswith("MONETISATION STUDY")
    assert not any(p in str(a) for p in SPEC["forbidden_output_phrases"])


def test_a_lone_spike_cell_is_not_picked():
    # an unstable cell can have the highest centre expectancy but must never be chosen over a stable neighbourhood
    b, ev = drift_bars(160, seed=11, drift=0.0006)
    out = M.run_study(b, ev, F, FAST)
    assert all(not c["stable"] for c in out["cells"] if c["reasons"])
    assert out["chosen"]["stable"]


def test_spec_is_frozen_and_study_never_marked_promotable():
    assert SPEC["promotion_eligible"] is False and SPEC["selection_trials_affected"] == 0
    assert SPEC["atr"]["period"] == 14 and SPEC["atr"]["bases"] == ["1m", "5m"]
    assert SPEC["grid"]["stop_atr"] == [1.0, 2.0, 3.0] and SPEC["grid"]["target_atr"] == [1.0, 2.0, 3.0]
    assert SPEC["neighbours"]["multipliers"] == [0.75, 1.25] and SPEC["neighbours"]["min_retained_expectancy_fraction"] == 0.5
    assert SPEC["costs"]["round_trip_ticks"] == 3 and SPEC["fills"]["stop_and_target_same_bar"] == "stop"
    assert len(M.spec_sha256()) == 64
