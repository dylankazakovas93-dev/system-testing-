"""TradingView translation test: compare Python event timestamps with an exported TradingView list.

TradingView exports/alerts reference the BAR where a signal is plotted. For a pivot confirmed by R
right-hand bars the plotted bar is the PIVOT bar; the event is only knowable after the R-th following
bar closes. ``kind``:
  pivot_bar_open        exported time = open of the plotted pivot bar  -> event = open of bar(pos+R) + interval
  confirmation_bar_open exported time = open of the bar whose close fired the alert -> event = that open + interval
Positions are counted in BARS of the supplied data (gap-safe), never in wall-clock minutes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.common import EngineError, utc_ns


def expected_event_times(exported_times, bars: pd.DataFrame, interval: pd.Timedelta, *, delay_bars: int,
                         kind: str = "pivot_bar_open") -> pd.DatetimeIndex:
    opens = utc_ns(bars.index)
    ex = utc_ns(pd.DatetimeIndex(pd.to_datetime(exported_times, utc=True)))
    pos = np.searchsorted(opens, ex)
    if not (pos < len(opens)).all() or not (opens[np.minimum(pos, len(opens) - 1)] == ex).all():
        raise EngineError("exported timestamps must be exact bar open times present in the data")
    if kind == "pivot_bar_open":
        pos = pos + int(delay_bars)
    elif kind != "confirmation_bar_open":
        raise EngineError(f"unknown exported timestamp kind {kind!r}")
    pos = pos[pos < len(opens)]
    return bars.index[pos].tz_convert("UTC") + interval


def compare_event_times(python_events: pd.DataFrame, exported_times, bars: pd.DataFrame, interval: pd.Timedelta, *,
                        delay_bars: int, kind: str = "pivot_bar_open") -> dict:
    exp = set(expected_event_times(exported_times, bars, interval, delay_bars=delay_bars, kind=kind))
    got = set(pd.DatetimeIndex(python_events["event_time"]).tz_convert("UTC"))
    both = exp & got
    return {"n_reference": len(exp), "n_python": len(got), "matched": len(both),
            "missing_in_python": sorted(exp - got), "extra_in_python": sorted(got - exp),
            "exact_match": exp == got,
            "naive_plot_time_matches": None}


def load_tradingview_export(path, column: str = "time") -> list:
    df = pd.read_csv(path)
    if column not in df.columns:
        raise EngineError(f"export needs a {column!r} column")
    return list(pd.to_datetime(df[column], utc=True))
