import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine.common import CODE_ROOT, load_frozen
from engine.event_contract import (EventCausalityError, EventContractError, StrictParams, apply_event_rules,
                                   check_event_causality, generate_events, load_event_module, raw_events,
                                   static_scan_event_source)
from engine.pine_translation import compare_event_times, expected_event_times
from engine.synthetic import make_bars
from tests import helpers as H

F = load_frozen()
TEMPLATE_EVENT = CODE_ROOT / "templates/experiment/event.py"


def spec(**kw):
    s = {"experiment_id": "EXP_T", "campaign_id": "C001", "eligible_session": {"start": "09:31", "end": "16:00"},
         "deduplication_rule": "drop_conflicting_same_time", "cooldown": {"bars": 0},
         "base_parameters": {"pivot_left": 3, "pivot_right": 2}}
    s.update(kw)
    return s


def module_from(tmp_path, source, name="ev.py"):
    p = tmp_path / name
    p.write_text(textwrap.dedent(source))
    return load_event_module(p)


# ---- static scan ----------------------------------------------------------------------------
def test_template_passes_static_scan():
    assert static_scan_event_source(TEMPLATE_EVENT.read_text()) == []


def test_unregistered_magic_numbers_are_flagged():
    src = "def detect_events(bars, params):\n    x = bars['close'].rolling(20).mean()\n    y = 0.35 * x\n    return None\n"
    issues = static_scan_event_source(src)
    assert any("20" in i for i in issues) and any("0.35" in i for i in issues)
    ok = "def detect_events(bars, params):\n    n = int(params['lookback'])\n    return bars['close'].rolling(n).mean().iloc[0]\n"
    assert static_scan_event_source(ok) == []


def test_static_scan_flags_future_reading_and_unsafe_constructs():
    cases = {
        "shift(-1)": "def detect_events(b, p):\n    return b['close'].shift(-1)\n",
        "centered": "def detect_events(b, p):\n    return b['close'].rolling(p['n'], center=True).mean()\n",
        "bfill": "def detect_events(b, p):\n    return b['close'].bfill()\n",
        "import os": "import os\ndef detect_events(b, p):\n    return None\n",
        "open(": "def detect_events(b, p):\n    return open('x')\n",
        "missing fn": "def other():\n    return 1\n",
    }
    for label, src in cases.items():
        assert static_scan_event_source(src), label


def test_strict_params_rejects_unregistered_keys_and_tracks_usage():
    sp = StrictParams({"a": 1, "b": 2})
    assert sp["a"] == 1
    with pytest.raises(KeyError, match="not registered"):
        sp["c"]
    assert sp.unused() == ["b"]


# ---- Pine pivot: confirmation time, not plotted time ------------------------------------------
def pivot_bars():
    closes = [100, 99, 98, 97, 96, 95, 94, 93, 94, 95, 96, 97, 98, 99, 100, 101]   # V shape, low at index 7
    lows = [c - 0.5 for c in closes]
    highs = [c + 0.5 for c in closes]
    return H.make_bars(closes, highs=highs, lows=lows)


def test_pivot_event_time_is_confirmation_not_plotted_pivot_time():
    bars = pivot_bars()
    mod = load_event_module(TEMPLATE_EVENT)
    ev, _ = raw_events(mod, bars, {"pivot_left": 3, "pivot_right": 5}, F)
    lows = ev[ev["direction"] == 1]
    assert len(lows) == 1
    pivot_bar = bars.index[7]                                   # where TradingView plots the triangle (offset=-right)
    confirming_bar_open = bars.index[7 + 5]                      # 5th right-hand bar
    expected = confirming_bar_open + pd.Timedelta("1min")        # knowable only when that bar CLOSES
    assert lows["event_time"].iloc[0] == expected
    assert lows["event_time"].iloc[0] != pivot_bar and lows["event_time"].iloc[0] != pivot_bar + pd.Timedelta("1min")
    assert (lows["event_time"].iloc[0] - pivot_bar) == pd.Timedelta("6min")      # right bars + 1 completion minute


def test_pivot_not_visible_before_right_hand_bars_exist():
    bars = pivot_bars()
    mod = load_event_module(TEMPLATE_EVENT)
    for n_avail in (8, 9, 10, 11):                               # bars up to index 7+right-1 or earlier
        ev, _ = raw_events(mod, bars.iloc[:n_avail], {"pivot_left": 3, "pivot_right": 5}, F)
        assert (ev["direction"] == 1).sum() == 0, n_avail
    ev, _ = raw_events(mod, bars.iloc[:13], {"pivot_left": 3, "pivot_right": 5}, F)   # index 12 = 5th right bar
    assert (ev["direction"] == 1).sum() == 1


def test_pivot_direction_high_is_short():
    bars = H.make_bars([100 - abs(i - 7) for i in range(16)])
    ev, _ = raw_events(load_event_module(TEMPLATE_EVENT), bars, {"pivot_left": 3, "pivot_right": 5}, F)
    assert set(ev["direction"]) == {-1}


def test_template_event_passes_truncation_and_future_mutation_check():
    bars = make_bars(n_days=20, seed=3)
    s = spec(base_parameters={"pivot_left": 30, "pivot_right": 15}, cooldown={"bars": 60})
    info = check_event_causality(load_event_module(TEMPLATE_EVENT), bars, s, F)
    assert info["cutoffs"] >= 4


def test_one_bar_lookahead_event_is_caught(tmp_path):
    mod = module_from(tmp_path, '''
        import numpy as np, pandas as pd
        def detect_events(bars, params):
            interval = pd.Timedelta(bars.attrs["bar_interval"])
            c = bars["close"].to_numpy()
            step = int(params["step"])
            idx = np.arange(step, len(bars) - 1, step)
            up = c[idx + 1] > c[idx]                      # peeks ONE bar beyond the stamped information time
            t = bars.index[idx] + interval
            return pd.DataFrame({"event_time": t[up], "direction": np.ones(int(up.sum()), dtype=int)})
    ''')
    bars = make_bars(n_days=10, seed=4)
    with pytest.raises(EventCausalityError):
        check_event_causality(mod, bars, spec(base_parameters={"step": 37}), F)


def test_causal_custom_event_passes_causality_check(tmp_path):
    mod = module_from(tmp_path, '''
        import numpy as np, pandas as pd
        def detect_events(bars, params):
            interval = pd.Timedelta(bars.attrs["bar_interval"])
            c = bars["close"].to_numpy()
            step = int(params["step"])
            idx = np.arange(step, len(bars), step)
            up = c[idx] > c[idx - step]
            t = bars.index[idx] + interval
            return pd.DataFrame({"event_time": t[up], "direction": np.ones(int(up.sum()), dtype=int)})
    ''')
    bars = make_bars(n_days=10, seed=4)
    assert check_event_causality(mod, bars, spec(base_parameters={"step": 37}), F)["cutoffs"] >= 4


def test_event_time_must_be_bar_completion_time(tmp_path):
    mod = module_from(tmp_path, '''
        import pandas as pd
        def detect_events(bars, params):
            return pd.DataFrame({"event_time": [bars.index[100] + pd.Timedelta("30s")], "direction": [1]})   # off the bar grid
    ''')
    with pytest.raises(EventContractError, match="COMPLETION"):
        raw_events(mod, make_bars(n_days=3), {}, F)


def test_bad_direction_and_naive_time_rejected(tmp_path):
    bars = make_bars(n_days=3)
    m1 = module_from(tmp_path, '''
        import pandas as pd
        def detect_events(bars, params):
            return pd.DataFrame({"event_time": [bars.index[100] + pd.Timedelta("1min")], "direction": [0]})
    ''', "a.py")
    with pytest.raises(EventContractError, match="direction"):
        raw_events(m1, bars, {}, F)
    m2 = module_from(tmp_path, '''
        import pandas as pd
        def detect_events(bars, params):
            return pd.DataFrame({"event_time": [pd.Timestamp("2016-01-05 15:00")], "direction": [1]})
    ''', "b.py")
    with pytest.raises(EventContractError, match="timezone"):
        raw_events(m2, bars, {}, F)


# ---- engine-applied rules --------------------------------------------------------------------
def raw(times, dirs):
    return pd.DataFrame({"event_time": pd.DatetimeIndex(times, tz="UTC"), "direction": dirs})


def test_session_eligibility_uses_exchange_local_time():
    # Jan: NY = UTC-5. 14:30 UTC = 09:30 local (excluded by >=09:31), 14:31 local 09:31 included, 20:00 UTC = 15:00 local (end excluded)
    r = raw(["2020-01-08 14:30", "2020-01-08 14:31", "2020-01-08 19:59", "2020-01-08 20:00"], [1, 1, 1, 1])
    out = apply_event_rules(r, spec(eligible_session={"start": "09:31", "end": "15:00"}), F)
    assert [f"{t:%H:%M}" for t in out["event_time"]] == ["14:31", "19:59"]


def test_deduplication_rules():
    r = raw(["2020-01-08 15:00", "2020-01-08 15:00", "2020-01-08 15:10", "2020-01-08 15:10"], [1, 1, 1, -1])
    drop = apply_event_rules(r, spec(), F)
    assert len(drop) == 1 and drop["direction"].iloc[0] == 1 and f"{drop['event_time'].iloc[0]:%H:%M}" == "15:00"
    first = apply_event_rules(r, spec(deduplication_rule="keep_first_per_event_time"), F)
    assert len(first) == 2 and first["direction"].tolist() == [1, 1]


def test_cooldown_is_sequential_and_causal():
    r = raw(["2020-01-08 15:00", "2020-01-08 15:05", "2020-01-08 15:10", "2020-01-08 15:11", "2020-01-08 15:20"], [1] * 5)
    out = apply_event_rules(r, spec(cooldown={"bars": 10}), F)
    assert [f"{t:%H:%M}" for t in out["event_time"]] == ["15:00", "15:10", "15:20"]
    assert out["event_id"].is_unique and out["event_id"].iloc[0].startswith("EXP_T_E2020")


def test_generate_events_applies_rules_to_template_output():
    bars = make_bars(n_days=15, seed=9)
    s = spec(base_parameters={"pivot_left": 30, "pivot_right": 15}, cooldown={"bars": 60},
             eligible_session={"start": "09:31", "end": "15:00"})
    ev, sp = generate_events(load_event_module(TEMPLATE_EVENT), bars, s, F)
    assert len(ev) > 20 and sp.unused() == []
    local = ev["event_time"].dt.tz_convert("America/New_York")
    assert ((local.dt.hour * 60 + local.dt.minute >= 571) & (local.dt.hour * 60 + local.dt.minute < 900)).all()
    gaps = ev["event_time"].diff().dropna()
    assert (gaps >= pd.Timedelta("60min")).all()


# ---- TradingView export translation -----------------------------------------------------------
def test_tradingview_export_translation_applies_confirmation_delay():
    bars = make_bars(n_days=15, seed=9)
    s = spec(base_parameters={"pivot_left": 30, "pivot_right": 15}, cooldown={"bars": 0}, deduplication_rule="keep_first_per_event_time")
    ev, _ = generate_events(load_event_module(TEMPLATE_EVENT), bars, s, F)
    # build a fake "TradingView export": PLOTTED pivot bars (open times) = event bar - right bars
    pos = bars.index.get_indexer(ev["event_time"] - pd.Timedelta("1min")) - 15
    plotted = list(bars.index[pos])
    res = compare_event_times(ev, plotted, bars, pd.Timedelta("1min"), delay_bars=15, kind="pivot_bar_open")
    assert res["exact_match"] and res["matched"] == len(ev) > 10
    # the NAIVE interpretation (event at plotted time + 1 bar) does not match: pivot visual time != event time
    naive = compare_event_times(ev, plotted, bars, pd.Timedelta("1min"), delay_bars=0, kind="pivot_bar_open")
    assert not naive["exact_match"] and naive["matched"] < len(ev) / 2
    confirm_open = list(bars.index[pos + 15])
    res2 = compare_event_times(ev, confirm_open, bars, pd.Timedelta("1min"), delay_bars=15, kind="confirmation_bar_open")
    assert res2["exact_match"]
    # a wrong/missing timestamp is reported, not ignored
    bad = compare_event_times(ev.iloc[1:], plotted, bars, pd.Timedelta("1min"), delay_bars=15)
    assert not bad["exact_match"] and len(bad["missing_in_python"]) == 1
    with pytest.raises(Exception):
        expected_event_times([pd.Timestamp("1999-01-01", tz="UTC")], bars, pd.Timedelta("1min"), delay_bars=15)


def test_template_rolling_implementation_equals_brute_force_definition():
    bars = make_bars(n_days=6, seed=21)
    left, right = 7, 4
    ev, _ = raw_events(load_event_module(TEMPLATE_EVENT), bars, {"pivot_left": left, "pivot_right": right}, F)
    low, high, n = bars["low"].to_numpy(), bars["high"].to_numpy(), len(bars)
    expected = set()
    for i in range(left, n - right):
        t = bars.index[i + right] + pd.Timedelta("1min")
        if low[i] < low[i - left:i].min() and low[i] <= low[i + 1:i + right + 1].min():
            expected.add((t, 1))
        if high[i] > high[i - left:i].max() and high[i] >= high[i + 1:i + right + 1].max():
            expected.add((t, -1))
    assert len(expected) > 100
    assert set(zip(ev["event_time"], ev["direction"])) == expected
