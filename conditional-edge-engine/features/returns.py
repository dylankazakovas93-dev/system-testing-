"""A. Log returns: RET_L = log(close_t / close_(t-L))."""
from __future__ import annotations

import numpy as np

from features._base import BarContext, gather


def compute(ctx: BarContext, pos: np.ndarray, params: dict) -> dict[str, np.ndarray]:
    out = {}
    for L in params["lookbacks"]:
        closes = gather(ctx.close, pos, L + 1)
        with np.errstate(divide="ignore", invalid="ignore"):
            out[f"RET_{L}"] = np.log(closes[:, -1] / closes[:, 0])
    return out
