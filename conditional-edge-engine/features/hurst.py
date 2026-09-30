"""F. Hurst / diffusion exponent via the multi-lag variance scaling law.

x = log close over the W most recent completed bars.
V(k) = mean((x_i - x_(i-k))^2) over all valid pairs inside the window.
OLS: log V(k) = a + b log k over the frozen lags; H = b / 2.
NaN if fewer than ``min_valid_lags`` lags have V(k) > 0. No R/S, no DFA.
"""
from __future__ import annotations

import numpy as np

from features._base import BarContext, gather


def hurst_from_windows(x: np.ndarray, lags: list[int], min_valid: int) -> np.ndarray:
    """x: (E, W) log-close windows (NaN rows allowed). Returns H of shape (E,)."""
    E = x.shape[0]
    lnV = np.full((E, len(lags)), np.nan)
    for j, k in enumerate(lags):
        d = x[:, k:] - x[:, :-k]
        v = np.mean(d * d, axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            lnV[:, j] = np.where(v > 0, np.log(v), np.nan)
    lk = np.log(np.asarray(lags, dtype=float))[None, :]
    valid = np.isfinite(lnV)
    n = valid.sum(axis=1)
    w = valid.astype(float)
    with np.errstate(divide="ignore", invalid="ignore"):
        xm = (w * lk).sum(axis=1) / n
        ym = (w * np.where(valid, lnV, 0.0)).sum(axis=1) / n
        dx = np.where(valid, lk - xm[:, None], 0.0)
        dy = np.where(valid, lnV - ym[:, None], 0.0)
        slope = (dx * dy).sum(axis=1) / (dx * dx).sum(axis=1)
    h = slope / 2.0
    h[n < min_valid] = np.nan
    return h


def compute(ctx: BarContext, pos: np.ndarray, params: dict) -> dict[str, np.ndarray]:
    out = {}
    for W in params["windows"]:
        with np.errstate(divide="ignore", invalid="ignore"):
            x = np.log(gather(ctx.close, pos, W))
        out[f"HURST_{W}"] = hurst_from_windows(x, params["lags"], params["min_valid_lags"])
    return out
