"""Frozen target engine v1: FROZEN FUTURE PATH TARGETS.

Forward bars = the first bars whose OPEN timestamp is >= event_time (the signal bar is complete
before event_time, so its movement can never enter a target). P0 = open of the first forward bar.

Explicit sign conventions, direction d in {-1,+1}, N forward bars, P0 as above:

  DIR_RETURN_N = d * log(close_N / P0)

  long  (d=+1):  fav_i = log(high_i / P0)      adv_i = log(low_i  / P0)
  short (d=-1):  fav_i = -log(low_i / P0)      adv_i = -log(high_i / P0)
  MFE60 = max_i fav_i ;  MAE60 = min_i adv_i  (<= 0 because the first bar's low <= open <= high)
  DIR_PATH_SKEW_60 = MFE60 + MAE60           (>0: favorable excursion dominates)

Only the four PRIMARY targets can take part in selection. Diagnostic targets are report-only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.common import EngineError, Frozen, utc_ns, validate_bars
from features._base import gather


def _directions(events: pd.DataFrame) -> np.ndarray:
    d = events["direction"].to_numpy()
    if not np.isin(d, (-1, 1)).all():
        raise EngineError("event direction must be -1 or +1 for target computation")
    return d.astype("float64")


def forward_start(bars: pd.DataFrame, event_time) -> np.ndarray:
    """Position of the first bar whose OPEN >= event_time (== len(bars) if none)."""
    return np.searchsorted(utc_ns(bars.index), utc_ns(pd.DatetimeIndex(event_time)), side="left")


def directional_return(close_n: np.ndarray, p0: np.ndarray, d: np.ndarray) -> np.ndarray:
    return d * np.log(close_n / p0)


def excursions(high: np.ndarray, low: np.ndarray, p0: np.ndarray, d: np.ndarray):
    """(fav, adv) arrays of shape (E, N) in directional log space."""
    lh = np.log(high / p0[:, None])
    ll = np.log(low / p0[:, None])
    long_ = (d > 0)[:, None]
    fav = np.where(long_, lh, -ll)
    adv = np.where(long_, ll, -lh)
    return fav, adv


def compute_primary_targets(bars: pd.DataFrame, events: pd.DataFrame, frozen: Frozen) -> dict[str, pd.DataFrame]:
    """name -> DataFrame[event_id, target_start, target_end, value]; unresolved (data end) events omitted.

    Omission is by timestamps only (window not yet complete), never by outcome.
    """
    validate_bars(bars)
    interval = frozen.interval
    d_all = _directions(events)
    first = forward_start(bars, events["event_time"])
    n = len(bars)
    o, h, l, c = (bars[k].to_numpy("float64") for k in ("open", "high", "low", "close"))
    out: dict[str, pd.DataFrame] = {}
    for spec in frozen.target_bank["primary_targets"]:
        N = int(spec["horizon_bars"])
        ok = (first + N - 1) < n
        f, d = first[ok], d_all[ok]
        p0 = o[f]
        if spec["kind"] == "directional_return":
            val = directional_return(c[f + N - 1], p0, d)
        elif spec["kind"] == "path_skew":
            fav, adv = excursions(gather(h, f + N - 1, N), gather(l, f + N - 1, N), p0, d)
            val = fav.max(axis=1) + adv.min(axis=1)
        else:
            raise EngineError(f"unknown target kind {spec['kind']}")
        out[spec["name"]] = pd.DataFrame({
            "event_id": events["event_id"].to_numpy()[ok],
            "target_start": bars.index[f].tz_convert("UTC"),
            "target_end": bars.index[f + N - 1].tz_convert("UTC") + interval,
            "value": val,
        }).reset_index(drop=True)
    return out


def to_long(targets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Long format expected by the external verifier: event_id, target_name, target_start, target_end, target_value."""
    parts = []
    for name, df in targets.items():
        parts.append(df.assign(target_name=name).rename(columns={"value": "target_value"}))
    cols = ["event_id", "target_name", "target_start", "target_end", "target_value"]
    return pd.concat(parts, ignore_index=True)[cols]


def compute_diagnostic_targets(bars: pd.DataFrame, events: pd.DataFrame, frozen: Frozen,
                               sigma: np.ndarray | None = None) -> pd.DataFrame:
    """Report-only diagnostics. ``sigma`` = RV_60 at each event (known at event time) for first passage.

    Returns one row per event; NaN when the required forward window is not yet complete.
    These columns can NEVER promote a candidate.
    """
    cfg = frozen.target_bank["diagnostic_targets"]
    d_all = _directions(events)
    first = forward_start(bars, events["event_time"])
    n = len(bars)
    o, h, l, c = (bars[k].to_numpy("float64") for k in ("open", "high", "low", "close"))
    E = len(events)
    res = {"event_id": events["event_id"].to_numpy()}

    def win_ok(N):
        return (first + N - 1) < n

    for N in cfg["return_horizons_bars"]:
        ok = win_ok(N)
        v = np.full(E, np.nan)
        v[ok] = directional_return(c[first[ok] + N - 1], o[first[ok]], d_all[ok])
        res[f"DIAG_RET_{N}"] = v
    for N in cfg["excursion_horizons_bars"]:
        ok = win_ok(N)
        mfe, mae, tmfe, tmae = (np.full(E, np.nan) for _ in range(4))
        if ok.any():
            f = first[ok]
            fav, adv = excursions(gather(h, f + N - 1, N), gather(l, f + N - 1, N), o[f], d_all[ok])
            mfe[ok], mae[ok] = fav.max(axis=1), adv.min(axis=1)
            tmfe[ok], tmae[ok] = fav.argmax(axis=1) + 1, adv.argmin(axis=1) + 1
        res[f"DIAG_MFE_{N}"], res[f"DIAG_MAE_{N}"] = mfe, mae
        res[f"DIAG_TIME_TO_MFE_{N}"], res[f"DIAG_TIME_TO_MAE_{N}"] = tmfe, tmae
    fp = cfg["first_passage"]
    Nfp = int(fp["horizon_bars"])
    ok = win_ok(Nfp)
    for mult in fp["multiples"]:
        code = np.full(E, np.nan)
        if ok.any() and sigma is not None:
            f = first[ok]
            fav, adv = excursions(gather(h, f + Nfp - 1, Nfp), gather(l, f + Nfp - 1, Nfp), o[f], d_all[ok])
            thr = (mult * sigma[ok])[:, None]
            up = fav >= thr
            dn = adv <= -thr
            both = up & dn
            t_up = np.where(up.any(axis=1), up.argmax(axis=1), 10**9)
            t_dn = np.where(dn.any(axis=1), dn.argmax(axis=1), 10**9)
            r = np.zeros(len(f))
            r[t_up < t_dn] = 1.0
            r[t_dn < t_up] = -1.0          # same-bar double touch (t_up == t_dn) or no touch -> 0
            code[ok] = r
        res[f"DIAG_FIRST_PASSAGE_{mult}"] = code
    N = int(cfg["path_horizon_bars"])
    ok = win_ok(N)
    plen, peff, frv = (np.full(E, np.nan) for _ in range(3))
    if ok.any():
        f = first[ok]
        closes = gather(c, f + N - 1, N)
        path = np.concatenate([o[f][:, None], closes], axis=1)
        steps = np.log(path[:, 1:] / path[:, :-1])
        length = np.abs(steps).sum(axis=1)
        net = np.abs(steps.sum(axis=1))
        plen[ok] = length
        with np.errstate(divide="ignore", invalid="ignore"):
            peff[ok] = np.where(length > 0, net / length, np.nan)
        frv[ok] = np.sqrt((steps ** 2).sum(axis=1))
    res["DIAG_PATH_LENGTH_60"], res["DIAG_PATH_EFFICIENCY_60"], res["DIAG_FWD_RV_60"] = plen, peff, frv
    return pd.DataFrame(res)


def window_span_violations(bars: pd.DataFrame, events: pd.DataFrame, horizon: int, interval: pd.Timedelta) -> int:
    """Data-quality info: forward windows whose wall-clock span exceeds horizon*interval (session gaps)."""
    first = forward_start(bars, events["event_time"])
    ok = (first + horizon - 1) < len(bars)
    ns = utc_ns(bars.index)
    span = ns[first[ok] + horizon - 1] - ns[first[ok]]
    return int((span > (horizon - 1) * interval.value).sum())
