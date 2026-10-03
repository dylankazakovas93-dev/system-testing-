"""C. Kaufman Efficiency Ratio (exact, unsmoothed).

ER_L = |close_t - close_(t-L)| / sum_{i=t-L+1..t} |close_i - close_(i-1)| ; zero denominator -> NaN.
"""
from __future__ import annotations

import numpy as np

from features._base import BarContext, gather, safe_div


def compute(ctx: BarContext, pos: np.ndarray, params: dict) -> dict[str, np.ndarray]:
    out = {}
    for L in params["lookbacks"]:
        c = gather(ctx.close, pos, L + 1)
        num = np.abs(c[:, -1] - c[:, 0])
        den = np.sum(np.abs(np.diff(c, axis=1)), axis=1)
        out[f"ER_{L}"] = safe_div(num, den)
    return out
