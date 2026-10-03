"""Nested score calibration: the classification threshold must be deployable from history alone.

For one outer training set this produces CHRONOLOGICAL INNER OUT-OF-FOLD predictions:
  the training events (time-ordered) are cut into ``inner_blocks`` consecutive blocks; block j
  is predicted by a model fitted on blocks < j, purged so that every used training event's
  target window ended BEFORE block j starts. The score threshold is the MEDIAN of those inner
  OOF predictions. Outer-validation scores/labels never participate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

UPPER, LOWER = "UPPER_HALF", "LOWER_HALF"


@dataclass(frozen=True)
class WFConfig:
    min_outer_train_events: int
    inner_blocks: int
    min_inner_train_events: int
    min_inner_oof_events: int

    @staticmethod
    def from_policy(policy: dict) -> "WFConfig":
        w = policy["development_cv"]
        return WFConfig(w["min_outer_train_events"], w["inner_blocks"], w["min_inner_train_events"],
                        w["min_inner_oof_events"])


def inner_oof_predictions(model_factory: Callable, X: pd.DataFrame, y: np.ndarray, event_ns: np.ndarray,
                          target_end_ns: np.ndarray, train_idx: np.ndarray, cfg: WFConfig):
    """Returns (oof_positions, oof_predictions) using ONLY ``train_idx`` rows (positions into X/y)."""
    order = train_idx[np.argsort(event_ns[train_idx], kind="stable")]
    segments = np.array_split(order, cfg.inner_blocks)
    oof_pos, oof_pred = [], []
    for j in range(1, cfg.inner_blocks):
        seg = segments[j]
        if len(seg) == 0:
            continue
        block_start = event_ns[seg[0]]
        prior = np.concatenate(segments[:j])
        prior = prior[target_end_ns[prior] < block_start]          # purge overlapping target windows
        if len(prior) < cfg.min_inner_train_events:
            continue
        model = model_factory().fit(X.iloc[prior], y[prior])
        oof_pos.append(seg)
        oof_pred.append(model.predict(X.iloc[seg]))
    if not oof_pos:
        return np.array([], dtype=int), np.array([], dtype=float)
    return np.concatenate(oof_pos), np.concatenate(oof_pred)


def calibrate_threshold(model_factory, X, y, event_ns, target_end_ns, train_idx, cfg: WFConfig):
    """(threshold, oof_positions, oof_predictions); threshold=None if calibration is impossible."""
    pos, pred = inner_oof_predictions(model_factory, X, y, event_ns, target_end_ns, train_idx, cfg)
    if len(pred) < cfg.min_inner_oof_events:
        return None, pos, pred
    return float(np.median(pred)), pos, pred


def assign_state(score: np.ndarray, threshold: float) -> np.ndarray:
    """'UPPER_HALF' if score > threshold, 'LOWER_HALF' if score < threshold, 'TIE' otherwise."""
    return np.where(score > threshold, UPPER, np.where(score < threshold, LOWER, "TIE"))
