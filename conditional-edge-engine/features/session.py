"""L. Session state (instrument-configured; NQ v1: America/New_York, RTH 09:30-16:00, ETH from 18:00).

Needs event_time: ctx.cache['event_ns'] is supplied by the feature engine for the chunk.
All per-bar session arrays are cumulative/forward-filled within a session, hence causal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from features._base import BarContext, gather


def _hhmm(text: str) -> int:
    h, m = text.split(":")
    return int(h) * 60 + int(m)


def _session_arrays(ctx: BarContext) -> dict[str, np.ndarray]:
    if "session" in ctx.cache:
        return ctx.cache["session"]
    local = ctx.index.tz_convert(ctx.tz)
    minute_of_day = (local.hour * 60 + local.minute).to_numpy()
    local_date = pd.Series(local.normalize().tz_localize(None).values)
    eth_start = _hhmm(ctx.eth_start)
    # ETH trading session key: bars at/after 18:00 local belong to the NEXT calendar date's session.
    sess_date = local_date + pd.to_timedelta((minute_of_day >= eth_start).astype(int), unit="D")
    tp = (ctx.high + ctx.low + ctx.close) / 3.0
    df = pd.DataFrame({"sess": sess_date.values, "pv": tp * ctx.volume, "v": ctx.volume})
    g = df.groupby("sess", sort=False)
    cum_pv = g["pv"].cumsum().to_numpy()
    cum_v = g["v"].cumsum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        vwap = np.where(cum_v > 0, cum_pv / cum_v, np.nan)
    # open of the first RTH bar (stamped >= rth open, < rth close) of each local calendar date, ffilled
    rth = (minute_of_day >= _hhmm(ctx.rth_open)) & (minute_of_day < _hhmm(ctx.rth_close))
    frame = pd.DataFrame({"date": local_date.values, "rth": rth})
    first_rth = frame[frame["rth"]].groupby("date", sort=False).head(1).index.to_numpy()
    seeded = np.full(len(ctx.open), np.nan)
    seeded[first_rth] = ctx.open[first_rth]          # ONLY the first RTH bar of each local date
    rth_open_px = pd.Series(seeded).groupby(local_date.values, sort=False).ffill().to_numpy()
    ctx.cache["session"] = {"vwap": vwap, "rth_open_px": rth_open_px}
    return ctx.cache["session"]


def compute(ctx: BarContext, pos: np.ndarray, params: dict) -> dict[str, np.ndarray]:
    sa = _session_arrays(ctx)
    event_ns = ctx.cache["event_ns"]
    ev_local = pd.DatetimeIndex(pd.to_datetime(event_ns, utc=True)).tz_convert(ctx.tz)
    ev_minute = (ev_local.hour * 60 + ev_local.minute).to_numpy() + ev_local.second.to_numpy() / 60.0
    mins = ev_minute - _hhmm(ctx.rth_open)
    ang = 2.0 * np.pi * mins / float(ctx.rth_minutes)
    ok = pos >= 0
    safe = np.clip(pos, 0, len(ctx.close) - 1)
    close_t = gather(ctx.close, pos, 1)[:, 0]
    rth_px = np.where(ok, sa["rth_open_px"][safe], np.nan)
    vwap = np.where(ok, sa["vwap"][safe], np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        rth_ret = np.log(close_t / rth_px)
        dist = close_t / vwap - 1.0
    return {
        "minutes_since_RTH_open": mins,
        "sin_RTH_phase": np.sin(ang),
        "cos_RTH_phase": np.cos(ang),
        "RTH_return_from_open": rth_ret,
        "distance_from_causal_session_VWAP": dist,
        "day_of_week": ev_local.dayofweek.to_numpy().astype("float64"),
    }
