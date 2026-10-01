"""Frozen forward-path engine v1 (frozen/v1/PATH_DIAGNOSTICS.yaml).  *** DIAGNOSTIC ONLY — NOT A SELECTION TRIAL ***

Everything here is memory-conscious: the engine iterates over forward-bar steps j = 0 .. max_horizon-1 and is vectorised over
EVENTS, keeping only O(E) running state (running max/min, first-occurrence times, first barrier touches). There is no
E x horizon matrix, no sliding window view, and nothing proportional to the number of bars beyond the OHLC columns themselves.

Conventions (see the YAML for the authoritative statement):
  forward bars = first bars whose OPEN >= event_time; P0 = open of the first forward bar; d in {-1,+1}
  long : fav_pts = high - P0 ; adv_pts = low  - P0        short: fav_pts = P0 - low ; adv_pts = P0 - high
  MFE_pts = max fav_pts (>= 0) ; MAE_pts = min adv_pts (<= 0) ; first occurrence defines bars_to_MFE / bars_to_MAE (1-based)
  directional log excursions: long fav_log = log(high/P0), adv_log = log(low/P0); short fav_log = -log(low/P0), adv_log = -log(high/P0)
  barrier touch (levels in sigma = RV_60 log units): target when fav_log >= t*sigma, stop when adv_log <= -s*sigma;
  same-bar double touch at the first touching bar -> AMBIGUOUS_SAME_BAR (no winner assumed)
Eligibility (PATH_TIMESTAMP_INELIGIBLE) per event and horizon is decided from timestamps only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from engine.common import EngineError

INF_T = np.int32(2**30)
TARGET, STOP, EXPIRED, AMBIG = 1, 2, 0, 3                  # outcome codes (EXPIRED == NEITHER touched inside the horizon)
OUTCOME_NAMES = {TARGET: "TARGET", STOP: "STOP", EXPIRED: "EXPIRED", AMBIG: "AMBIGUOUS_SAME_BAR"}


@dataclass
class PathArrays:
    """Per-event path facts. All arrays have length E (events, in the order given)."""
    horizons: list[int]
    levels: list[float]
    first: np.ndarray
    d: np.ndarray
    p0: np.ndarray
    sigma_log: np.ndarray
    elig: dict[int, np.ndarray] = field(default_factory=dict)          # horizon -> bool (PATH eligible)
    close_h: dict[int, np.ndarray] = field(default_factory=dict)       # close of the h-th forward bar
    mfe_pts: dict[int, np.ndarray] = field(default_factory=dict)
    mae_pts: dict[int, np.ndarray] = field(default_factory=dict)
    t_mfe: dict[int, np.ndarray] = field(default_factory=dict)
    t_mae: dict[int, np.ndarray] = field(default_factory=dict)
    t_fav: dict[float, np.ndarray] = field(default_factory=dict)       # level -> first bar with fav_log >= level*sigma (INF_T if none)
    t_adv: dict[float, np.ndarray] = field(default_factory=dict)       # level -> first bar with adv_log <= -level*sigma


def path_eligibility(ts_ns: np.ndarray, first: np.ndarray, close_ns: np.ndarray, interval_ns: int, h: int) -> np.ndarray:
    """PATH_TIMESTAMP_INELIGIBLE complement: h consecutive forward bars exist, and the h-th completes by the RTH close.
    Uses timestamps only (never prices)."""
    n = len(ts_ns)
    last = first + h - 1
    inside = last < n
    lc = np.minimum(last, n - 1)
    fc = np.minimum(first, n - 1)
    consecutive = (ts_ns[lc] - ts_ns[fc]) == (h - 1) * interval_ns          # no gap inside the window (timestamps strictly increase)
    completes = (ts_ns[lc] + interval_ns) <= close_ns
    return inside & consecutive & completes


def compute_paths(o: np.ndarray, hi: np.ndarray, lo: np.ndarray, cl: np.ndarray, ts_ns: np.ndarray, first: np.ndarray,
                  d: np.ndarray, sigma_log: np.ndarray, close_ns: np.ndarray, interval_ns: int, horizons: list[int],
                  levels: list[float]) -> PathArrays:
    n, E = len(o), len(first)
    if E and not np.isin(d, (-1, 1)).all():
        raise EngineError("event direction must be -1 or +1")
    horizons = sorted(horizons)
    hmax = horizons[-1]
    first = np.asarray(first, dtype=np.int64)
    fc = np.minimum(first, max(n - 1, 0))
    p0 = o[fc].astype("float64")
    long_ = np.asarray(d) > 0
    pa = PathArrays(horizons, list(levels), first, np.asarray(d, dtype="float64"), p0, np.asarray(sigma_log, dtype="float64"))
    for h in horizons:
        pa.elig[h] = path_eligibility(ts_ns, first, close_ns, interval_ns, h)
    mfe = np.full(E, -np.inf)
    mae = np.full(E, np.inf)
    tmfe = np.zeros(E, dtype=np.int32)
    tmae = np.zeros(E, dtype=np.int32)
    t_fav = {k: np.full(E, INF_T, dtype=np.int32) for k in levels}
    t_adv = {k: np.full(E, INF_T, dtype=np.int32) for k in levels}
    bad = np.zeros(E, dtype=bool)                                # a non-finite OHLC value inside the window makes it ineligible
    bad_h: dict[int, np.ndarray] = {}
    sig = pa.sigma_log
    for j in range(hmax):
        idx = np.minimum(first + j, n - 1)
        h_, l_ = hi[idx], lo[idx]
        bad |= ~(np.isfinite(h_) & np.isfinite(l_) & np.isfinite(cl[idx]) & np.isfinite(o[idx]))
        fav = np.where(long_, h_ - p0, p0 - l_)
        adv = np.where(long_, l_ - p0, p0 - h_)
        up = fav > mfe                                           # strict: first occurrence of the extremum wins
        mfe = np.where(up, fav, mfe)
        tmfe = np.where(up, np.int32(j + 1), tmfe)
        dn = adv < mae
        mae = np.where(dn, adv, mae)
        tmae = np.where(dn, np.int32(j + 1), tmae)
        with np.errstate(divide="ignore", invalid="ignore"):
            lh, ll = np.log(h_ / p0), np.log(l_ / p0)
        fav_l = np.where(long_, lh, -ll)
        adv_l = np.where(long_, ll, -lh)
        for k in levels:
            thr = k * sig
            m = (fav_l >= thr) & (t_fav[k] == INF_T)
            t_fav[k] = np.where(m, np.int32(j + 1), t_fav[k])
            m = (adv_l <= -thr) & (t_adv[k] == INF_T)
            t_adv[k] = np.where(m, np.int32(j + 1), t_adv[k])
        if (j + 1) in horizons:
            hh = j + 1
            pa.close_h[hh] = cl[idx].astype("float64")
            pa.mfe_pts[hh], pa.mae_pts[hh] = mfe.copy(), mae.copy()
            pa.t_mfe[hh], pa.t_mae[hh] = tmfe.copy(), tmae.copy()
            bad_h[hh] = bad.copy()
    pa.t_fav, pa.t_adv = t_fav, t_adv
    for h in horizons:
        pa.elig[h] = pa.elig[h] & ~bad_h[h]
    return pa


# ---------------------------------------------------------------------------------------------------- derived quantities
def mfe_mae_log(p0: np.ndarray, d: np.ndarray, mfe_pts: np.ndarray, mae_pts: np.ndarray):
    """MFE_log, MAE_log from the point extrema (long: log((P0+x)/P0); short: -log((P0-x)/P0))."""
    long_ = d > 0
    with np.errstate(divide="ignore", invalid="ignore"):
        mfe = np.where(long_, np.log((p0 + mfe_pts) / p0), -np.log((p0 - mfe_pts) / p0))
        mae = np.where(long_, np.log((p0 + mae_pts) / p0), -np.log((p0 - mae_pts) / p0))
    return mfe, mae


def barrier_outcome(t_target: np.ndarray, t_stop: np.ndarray, expiry: int) -> np.ndarray:
    """First-passage outcome inside ``expiry`` bars from the first-touch bar indices (INF_T = never touched)."""
    tt, ts = t_target <= expiry, t_stop <= expiry
    code = np.full(len(t_target), EXPIRED, dtype=np.int8)
    code[tt & (~ts | (t_target < t_stop))] = TARGET
    code[ts & (~tt | (t_stop < t_target))] = STOP
    code[tt & ts & (t_target == t_stop)] = AMBIG
    return code


def bracket_distances(p0: np.ndarray, d: np.ndarray, sigma_log: np.ndarray, target_sigma: float, stop_sigma: float):
    """Target / stop distances in POINTS (positive numbers) for price levels P0*exp(+-k*sigma) in the event direction."""
    long_ = d > 0
    tdist = np.where(long_, p0 * (np.exp(target_sigma * sigma_log) - 1.0), p0 * (1.0 - np.exp(-target_sigma * sigma_log)))
    sdist = np.where(long_, p0 * (1.0 - np.exp(-stop_sigma * sigma_log)), p0 * (np.exp(stop_sigma * sigma_log) - 1.0))
    return tdist, sdist


def bracket_pnl(pa: PathArrays, target_sigma: float, stop_sigma: float, expiry: int):
    """(code, conservative_pnl_points, raw_pnl_points_or_nan, stop_distance_points) for one bracket cell, all events.

    TARGET -> +target distance; STOP -> -stop distance; EXPIRED -> d*(close_expiry - P0); AMBIGUOUS_SAME_BAR ->
    CONSERVATIVE: counted as STOP; RAW: kept as its own outcome with NaN pnl (excluded from pnl statistics).
    Events not PATH-eligible at ``expiry`` get NaN."""
    code = barrier_outcome(pa.t_fav[target_sigma], pa.t_adv[stop_sigma], expiry)
    tdist, sdist = bracket_distances(pa.p0, pa.d, pa.sigma_log, target_sigma, stop_sigma)
    exp_pnl = pa.d * (pa.close_h[expiry] - pa.p0)
    raw = np.where(code == TARGET, tdist, np.where(code == STOP, -sdist, np.where(code == EXPIRED, exp_pnl, np.nan)))
    cons = np.where(code == AMBIG, -sdist, raw)
    bad = ~pa.elig[expiry] | ~np.isfinite(pa.sigma_log)
    code = np.where(bad, np.int8(-1), code)
    return code, np.where(bad, np.nan, cons), np.where(bad, np.nan, raw), sdist


def rv_ref(close: np.ndarray, pos: np.ndarray, n_returns: int = 60) -> np.ndarray:
    """RV_60 (frozen unit): sqrt(sum of the last 60 squared one-bar log returns) ending at bar ``pos`` (last bar completed at the
    event). Streaming over the 60 steps (O(E) memory). NaN when fewer than 61 closes exist. Equals features.volatility RV_60."""
    pos = np.asarray(pos, dtype=np.int64)
    acc = np.zeros(len(pos))
    for j in range(n_returns):
        a = np.clip(pos - j, 0, len(close) - 1)
        b = np.clip(pos - j - 1, 0, len(close) - 1)
        with np.errstate(divide="ignore", invalid="ignore"):
            r = np.log(close[a] / close[b])
        acc += r * r
    out = np.sqrt(acc)
    out[(pos - n_returns) < 0] = np.nan
    return out
