"""Benjamini-Hochberg FDR. Always computed over ALL trials of the relevant family, never over winners."""
from __future__ import annotations

import numpy as np


def benjamini_hochberg(p) -> np.ndarray:
    """BH-adjusted q-values (monotone, capped at 1), same order as the input."""
    p = np.asarray(p, dtype="float64")
    m = len(p)
    if m == 0:
        return p.copy()
    if not np.isfinite(p).all():
        raise ValueError("BH requires finite p-values for every trial (use 1.0 for non-evaluable trials)")
    order = np.argsort(p, kind="stable")
    ranked = p[order] * m / (np.arange(m) + 1.0)
    q_sorted = np.minimum.accumulate(ranked[::-1])[::-1]
    q = np.empty(m)
    q[order] = np.minimum(q_sorted, 1.0)
    return q
