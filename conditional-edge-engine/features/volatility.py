"""B. Realized volatility RV_L = sqrt(sum r_i^2); J. Volatility-of-volatility VOV_L = std(TR, ddof=0)."""
from __future__ import annotations

import numpy as np

from features._base import BarContext, gather, log_returns_window


def true_range(ctx: BarContext) -> np.ndarray:
    """TR_t = max(high-low, |high-prev_close|, |low-prev_close|); TR_0 is NaN (no prev close)."""
    if "tr" not in ctx.cache:
        prev = np.concatenate([[np.nan], ctx.close[:-1]])
        tr = np.maximum.reduce([ctx.high - ctx.low, np.abs(ctx.high - prev), np.abs(ctx.low - prev)])
        ctx.cache["tr"] = tr  # NaN propagates at index 0 through np.abs(nan)
    return ctx.cache["tr"]


def compute(ctx: BarContext, pos: np.ndarray, params: dict) -> dict[str, np.ndarray]:
    out = {}
    for L in params["rv_lookbacks"]:
        r = log_returns_window(ctx, pos, L)
        out[f"RV_{L}"] = np.sqrt(np.sum(r * r, axis=1))
    tr = true_range(ctx)
    for L in params["vov_lookbacks"]:
        out[f"VOV_{L}"] = np.std(gather(tr, pos, L), axis=1, ddof=0)
    return out
