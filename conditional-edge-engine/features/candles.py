"""G. Bull/bear candle-count balance; H. Candle-body balance."""
from __future__ import annotations

import numpy as np

from features._base import BarContext, gather, safe_div


def compute(ctx: BarContext, pos: np.ndarray, params: dict) -> dict[str, np.ndarray]:
    out = {}
    for L in params["lookbacks"]:
        o = gather(ctx.open, pos, L)
        c = gather(ctx.close, pos, L)
        out[f"COUNT_BALANCE_{L}"] = np.sum(np.sign(c - o), axis=1) / L
        body = c - o
        out[f"BODY_BALANCE_{L}"] = safe_div(np.sum(body, axis=1), np.sum(np.abs(body), axis=1))
    return out
