"""Expanding annual chronological OOS walk-forward (never random CV).

For each outer validation calendar year (UTC) V with start vs:
  1. outer training = events with event_time < vs AND target_end < vs  (overlapping targets purged;
     the purge uses the target's own resolution time, i.e. the trial's longest required horizon);
  2. inner chronological OOF predictions inside that training set -> score median (frozen threshold);
  3. fit on the complete outer training set;
  4. score the validation events; classify with the already-frozen training median.
Validation labels are never used to fit, to calibrate or to rank.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from engine.common import utc_ns
from engine.score_calibration import WFConfig, assign_state, calibrate_threshold


@dataclass
class WFResult:
    oos: pd.DataFrame                      # pos, year, score, threshold, state
    folds: list[dict] = field(default_factory=list)
    importances: list[dict] = field(default_factory=list)


def utc_year(event_time) -> np.ndarray:
    return pd.DatetimeIndex(event_time).tz_convert("UTC").year.to_numpy()


def run_walkforward(model_factory, X: pd.DataFrame, y: np.ndarray, event_time, target_end,
                    cfg: WFConfig) -> WFResult:
    """X/y/event_time/target_end are aligned, model-eligible, resolved-target rows."""
    y = np.asarray(y, dtype="float64")
    ev_ns = utc_ns(pd.DatetimeIndex(event_time))
    te_ns = utc_ns(pd.DatetimeIndex(target_end))
    years = utc_year(event_time)
    rows, folds, imps = [], [], []
    for V in sorted(np.unique(years)):
        vs = int(pd.Timestamp(year=int(V), month=1, day=1, tz="UTC").as_unit("ns").value)
        train = np.flatnonzero((ev_ns < vs) & (te_ns < vs))
        val = np.flatnonzero(years == V)
        fold = {"year": int(V), "n_train": int(len(train)), "n_validation": int(len(val)), "status": "OK"}
        if len(train) < cfg.min_outer_train_events:
            fold["status"] = f"SKIPPED_INSUFFICIENT_TRAIN(<{cfg.min_outer_train_events})"
            folds.append(fold)
            continue
        thr, oof_pos, oof_pred = calibrate_threshold(model_factory, X, y, ev_ns, te_ns, train, cfg)
        fold["n_inner_oof"] = int(len(oof_pred))
        if thr is None:
            fold["status"] = "SKIPPED_INSUFFICIENT_CALIBRATION"
            folds.append(fold)
            continue
        model = model_factory().fit(X.iloc[train], y[train])
        score = model.predict(X.iloc[val])
        rows.append(pd.DataFrame({"pos": val, "year": int(V), "score": score, "threshold": thr,
                                  "state": assign_state(score, thr)}))
        fold["threshold"] = thr
        folds.append(fold)
        if hasattr(model, "feature_importance"):
            imps.append(model.feature_importance())
    oos = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
        {"pos": [], "year": [], "score": [], "threshold": [], "state": []})
    return WFResult(oos=oos, folds=folds, importances=imps)
