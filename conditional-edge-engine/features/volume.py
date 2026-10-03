"""K. Signed-volume imbalance proxy: sum(sign(close-open)*volume) / sum(volume); zero volume -> NaN."""
from __future__ import annotations

import numpy as np

from features._base import BarContext, gather, safe_div


def compute(ctx: BarContext, pos: np.ndarray, params: dict) -> dict[str, np.ndarray]:
    out = {}
    for L in params["lookbacks"]:
        o = gather(ctx.open, pos, L)
        c = gather(ctx.close, pos, L)
        v = gather(ctx.volume, pos, L)
        out[f"SIGNED_VOLUME_{L}"] = safe_div(np.sum(np.sign(c - o) * v, axis=1), np.sum(v, axis=1))
    return out
