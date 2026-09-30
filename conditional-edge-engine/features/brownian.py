"""D. Brownian standardized displacement; E. Variance ratio relative to Brownian scaling.

BROWNIAN_DISP_L = sum(r_i) / sqrt(sum(r_i^2)) over the last L one-bar log returns.

VR(W,q): window = the W most recent completed bars (W log-closes x, W-1 one-bar returns).
  q-bar returns are NON-overlapping and anchored at t: x_t-x_(t-q), x_(t-q)-x_(t-2q), ...
  while the start index stays inside the window. Population variance (ddof=0).
  VR = Var(q-bar returns) / (q * Var(1-bar returns in window)); zero denominator -> NaN.
"""
from __future__ import annotations

import numpy as np

from features._base import BarContext, gather, log_returns_window, safe_div


def compute(ctx: BarContext, pos: np.ndarray, params: dict) -> dict[str, np.ndarray]:
    out = {}
    for L in params["disp_lookbacks"]:
        r = log_returns_window(ctx, pos, L)
        out[f"BROWNIAN_DISP_{L}"] = safe_div(np.sum(r, axis=1), np.sqrt(np.sum(r * r, axis=1)))
    for W in params["vr_windows"]:
        with np.errstate(divide="ignore", invalid="ignore"):
            x = np.log(gather(ctx.close, pos, W))
        r1 = np.diff(x, axis=1)
        var1 = np.var(r1, axis=1, ddof=0)
        for q in params["vr_lags"]:
            m = (W - 1) // q                       # number of non-overlapping q-bar returns
            cols = (W - 1) - q * np.arange(m + 1)  # x positions t, t-q, ..., t-mq
            d = np.diff(x[:, cols[::-1]], axis=1)  # chronological q-bar returns
            varq = np.var(d, axis=1, ddof=0)
            out[f"VR_{W}_{q}"] = safe_div(varq, q * var1)
    return out
