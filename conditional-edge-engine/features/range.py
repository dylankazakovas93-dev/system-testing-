"""I. Range location: (close_t - rolling_low_L) / (rolling_high_L - rolling_low_L); zero range -> 0.5."""
from __future__ import annotations

import numpy as np

from features._base import BarContext, gather


def compute(ctx: BarContext, pos: np.ndarray, params: dict) -> dict[str, np.ndarray]:
    out = {}
    for L in params["lookbacks"]:
        hi = np.max(gather(ctx.high, pos, L), axis=1)
        lo = np.min(gather(ctx.low, pos, L), axis=1)
        close_t = gather(ctx.close, pos, 1)[:, 0]
        rng = hi - lo
        val = np.full(len(pos), np.nan)
        known = np.isfinite(rng)
        zero = known & (rng == 0)
        pos_rng = known & (rng != 0)
        val[zero] = 0.5
        val[pos_rng] = (close_t[pos_rng] - lo[pos_rng]) / rng[pos_rng]
        out[f"RANGE_POS_{L}"] = val
    return out
