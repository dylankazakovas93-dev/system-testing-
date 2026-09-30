"""Shared helpers for the frozen feature modules.

All features are pure functions of completed bars up to and including position ``pos``
(the last completed bar at event_time). Modules gather explicit trailing windows
(``gather``), so every formula is literally the written definition.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class BarContext:
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray
    index_ns: np.ndarray          # UTC ns of bar OPEN
    interval_ns: int
    index: pd.DatetimeIndex       # tz-aware, UTC
    tz: str
    rth_open: str = "09:30"
    rth_close: str = "16:00"
    eth_start: str = "18:00"
    rth_minutes: int = 390
    cache: dict = field(default_factory=dict)


def gather(arr: np.ndarray, pos: np.ndarray, length: int) -> np.ndarray:
    """Windows arr[pos-length+1 .. pos] (inclusive), shape (E, length).

    Rows whose window starts before index 0 are all-NaN (history too short); negative pos
    (no completed bar) also yields NaN.
    """
    pos = np.asarray(pos, dtype=np.int64)
    start = pos - (length - 1)
    idx = start[:, None] + np.arange(length)[None, :]
    ok = (start >= 0) & (pos >= 0)
    out = arr[np.clip(idx, 0, len(arr) - 1)].astype("float64")
    out[~ok] = np.nan
    return out


def log_returns_window(ctx: BarContext, pos: np.ndarray, n_returns: int) -> np.ndarray:
    """(E, n_returns): r_i = log(close_i / close_(i-1)) for i = t-n+1 .. t."""
    closes = gather(ctx.close, pos, n_returns + 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.log(closes[:, 1:] / closes[:, :-1])


def safe_div(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    """num/den with NaN when den == 0 (or either is NaN)."""
    out = np.full(np.broadcast(num, den).shape, np.nan)
    ok = (den != 0) & np.isfinite(den) & np.isfinite(num)
    out[ok] = (num / np.where(ok, den, 1.0))[ok]
    return out
