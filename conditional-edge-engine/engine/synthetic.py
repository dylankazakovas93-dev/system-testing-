"""Synthetic data with KNOWN structure, used only by tests and demos (never by research runs).

* ``make_event_tables``: event-level tables (events, 56 features, 4 targets) with a planted relation;
  every scenario is fully determined by its arguments and seed.
* ``make_bars``: RTH-only 1-minute NQ-like bars (America/New_York 09:30-16:00), optional AR(1) momentum.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.common import Frozen, load_frozen, primary_target_names
from engine.feature_engine import feature_names

HORIZON_MIN = {"DIR_RETURN_15": 15, "DIR_RETURN_60": 60, "DIR_RETURN_180": 180, "DIR_PATH_SKEW_60": 60}


def make_bars(n_days: int = 260, start: str = "2016-01-04", seed: int = 7, vol: float = 0.0004,
              phi: float = 0.0, base: float = 5000.0) -> pd.DataFrame:
    """RTH-only open-stamped 1-minute bars (390/day), weekdays only. ``phi`` = AR(1) momentum of 1-min returns."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range(start, periods=n_days)
    minutes = np.arange(390)
    local = (days.values[:, None].astype("datetime64[ns]") + np.timedelta64(9 * 60 + 30, "m")
             + (minutes * np.timedelta64(1, "m"))[None, :]).ravel()
    idx = pd.DatetimeIndex(local).tz_localize("America/New_York").tz_convert("UTC")
    n = len(idx)
    eps = rng.normal(0.0, vol, n)
    if phi != 0.0:
        r = np.empty(n)
        r[0] = eps[0]
        for i in range(1, n):
            r[i] = phi * r[i - 1] + eps[i]
    else:
        r = eps
    close = base * np.exp(np.cumsum(r))
    open_ = np.concatenate([[base], close[:-1]])
    spread = np.abs(rng.normal(0, vol / 2, n))
    high = np.maximum(open_, close) * (1 + spread)
    low = np.minimum(open_, close) * (1 - spread)
    volume = rng.integers(50, 600, n).astype("float64")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx)


def make_event_tables(*, years=range(2015, 2023), events_per_week: float = 10.0, seed: int = 11,
                      signal: str = "none", slope: float = 0.0, slope_by_year: dict | None = None,
                      tail_threshold: float = 1.9, tail_shift: float = 1.5, drift: float = 0.0,
                      signal_feature: str = "ER_60", target_scale: dict | None = None, tie: dict | None = None, frozen: Frozen | None = None):
    """Returns (events, features, eligible, targets, calendar_index).

    signal: none | linear | nonlinear (U-shape in the feature) | tail (rare extreme shift).
    Every primary target shares the planted relation (path-skew is scaled); noise is independent per target.
    ``tie`` ({dst: src}) gives target ``dst`` exactly the noisy values of target ``src`` (a near-tied pair by construction).
    ``target_scale`` ({target: factor}) overrides the per-target scaling of the planted relation (default scale 1.0, path-skew 0.8).
    """
    frozen = frozen or load_frozen()
    rng = np.random.default_rng(seed)
    names = feature_names(frozen)
    weeks = pd.date_range(f"{min(years)}-01-05", f"{max(years)}-12-28", freq="W-MON", tz="UTC")
    times = []
    for w in weeks:
        k = rng.poisson(events_per_week)
        if k:
            day = rng.integers(0, 5, k)
            minute = rng.integers(60, 330, k)          # inside RTH (UTC offset irrelevant for tables)
            times.extend((w + pd.to_timedelta(day, unit="D") + pd.Timedelta(hours=15) + pd.to_timedelta(minute, unit="m")).tolist())
    t = pd.DatetimeIndex(sorted(times)).tz_convert("UTC")
    n = len(t)
    X = pd.DataFrame(rng.normal(size=(n, len(names))), columns=names)
    X["day_of_week"] = t.tz_convert("America/New_York").dayofweek.astype("float64")
    x = X[signal_feature].to_numpy()
    year = t.year.to_numpy()
    if signal == "none":
        core = np.zeros(n)
    elif signal == "linear":
        b = np.full(n, slope, dtype=float)
        if slope_by_year:
            for y, s in slope_by_year.items():
                b[year == y] = s
        core = b * x
    elif signal == "nonlinear":
        core = slope * (x ** 2 - 1.0)
    elif signal == "tail":
        core = np.where(x > tail_threshold, tail_shift, 0.0)
    else:
        raise ValueError(signal)
    direction = np.ones(n, dtype=int)                 # v1: single-direction experiments only
    events = pd.DataFrame({"event_id": [f"S{i:06d}" for i in range(n)], "event_time": t, "direction": direction})
    targets = {}
    scale = {"DIR_RETURN_15": 1.0, "DIR_RETURN_60": 1.0, "DIR_RETURN_180": 1.0, "DIR_PATH_SKEW_60": 0.8, **(target_scale or {})}
    for name in primary_target_names(frozen):
        y = drift + scale[name] * core + rng.normal(size=n)
        targets[name] = pd.DataFrame({
            "event_id": events["event_id"], "target_start": t,
            "target_end": t + pd.Timedelta(minutes=HORIZON_MIN[name]),
            "effective_target_end": t + pd.Timedelta(minutes=HORIZON_MIN[name]), "value": y})
    for dst, src in (tie or {}).items():
        targets[dst]["value"] = targets[src]["value"].to_numpy().copy()
    eligible = np.ones(n, dtype=bool)
    calendar = pd.date_range(f"{min(years)}-01-01", f"{max(years)}-12-31", freq="B", tz="UTC")
    return events, X.assign(event_id=events["event_id"].to_numpy(), feature_asof_time=t)[["event_id", "feature_asof_time"] + names], \
        eligible, targets, calendar
