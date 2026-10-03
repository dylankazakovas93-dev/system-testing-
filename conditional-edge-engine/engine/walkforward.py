"""DEVELOPMENT_CV: exactly K=5 purged chronological expanding walk-forward folds (never random CV).

The model-eligible development events are cut (by event count, using timestamps only) into K+1 consecutive blocks. Fold j
(j=1..K) validates block j and trains on history strictly before it:

    legal training event  <=>  event_time < validation_start  AND  effective_target_end < validation_start
    effective_target_end = max(candidate_claimed_target_end, frozen_declared_target_resolution)

Inside each fold the nested calibration of score_calibration.py still applies (chronological inner OOF -> train-only
median). A fold below any frozen minimum is SKIPPED / INSUFFICIENT_DATA (thresholds are never lowered). These folds are
internal cross-validation; they are NEVER called SELECTION HOLDOUT.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from engine.common import utc_ns
from engine.score_calibration import WFConfig, assign_state, calibrate_threshold

INT64_MAX = np.iinfo(np.int64).max


@dataclass
class Fold:
    fold: int
    val_start_ns: int
    val_end_ns: int          # exclusive; INT64_MAX for the last fold


@dataclass
class WFResult:
    validation: pd.DataFrame               # pos, fold, year, score, threshold, state
    folds: list[dict] = field(default_factory=list)
    importances: list[dict] = field(default_factory=list)
    coefficients: list[dict] = field(default_factory=list)


def utc_year(event_time) -> np.ndarray:
    return pd.DatetimeIndex(event_time).tz_convert("UTC").year.to_numpy()


def _snap_to_local_day_start(ts: pd.Timestamp, tz: str) -> int:
    """Start (UTC ns) of the exchange-local calendar day containing ts: folds keep whole trading days together."""
    local = ts.tz_convert(tz)
    start = pd.Timestamp(local.date(), tz=tz)
    return int(start.tz_convert("UTC").as_unit("ns").value)


def make_blocks(event_time, n_blocks: int, tz: str) -> list[tuple[int, int]]:
    """Consecutive [start_ns, end_ns) blocks of ~equal event count. Boundaries depend on event timestamps only."""
    ev = pd.DatetimeIndex(event_time).sort_values()
    if len(ev) < n_blocks:
        return []
    groups = np.array_split(np.arange(len(ev)), n_blocks)
    starts = [None] + [_snap_to_local_day_start(ev[g[0]], tz) for g in groups[1:]]
    blocks = []
    for i in range(n_blocks):
        lo = starts[i] if i else -INT64_MAX
        hi = starts[i + 1] if i + 1 < n_blocks else INT64_MAX
        blocks.append((lo, hi))
    return blocks


def development_folds(event_time, K: int, tz: str) -> list[Fold]:
    """K folds validating blocks 1..K of K+1 blocks (block 0 is training-only history)."""
    blocks = make_blocks(event_time, K + 1, tz)
    if not blocks:
        return []
    return [Fold(j, blocks[j][0], blocks[j][1]) for j in range(1, K + 1)]


def run_walkforward(model_factory, X: pd.DataFrame, y: np.ndarray, event_time, effective_target_end,
                    cfg: WFConfig, folds: list[Fold]) -> WFResult:
    """X/y/event_time/effective_target_end are aligned, model-eligible, resolved-target rows (all DEVELOPMENT)."""
    y = np.asarray(y, dtype="float64")
    ev_ns = utc_ns(pd.DatetimeIndex(event_time))
    te_ns = utc_ns(pd.DatetimeIndex(effective_target_end))
    years = utc_year(event_time)
    rows, out_folds, imps, coefs = [], [], [], []
    for f in folds:
        vs = f.val_start_ns
        train = np.flatnonzero((ev_ns < vs) & (te_ns < vs))
        val = np.flatnonzero((ev_ns >= vs) & (ev_ns < f.val_end_ns))
        rec = {"fold": f.fold, "val_start": str(pd.Timestamp(vs, tz="UTC")), "n_train": int(len(train)),
               "n_validation": int(len(val)), "status": "OK"}
        if f.val_end_ns != INT64_MAX:
            rec["val_end"] = str(pd.Timestamp(f.val_end_ns, tz="UTC"))
        if len(train) < cfg.min_outer_train_events:
            rec["status"] = f"SKIPPED_INSUFFICIENT_DATA(train<{cfg.min_outer_train_events})"
            out_folds.append(rec)
            continue
        if len(val) == 0:
            rec["status"] = "SKIPPED_INSUFFICIENT_DATA(no validation events)"
            out_folds.append(rec)
            continue
        thr, _, oof_pred = calibrate_threshold(model_factory, X, y, ev_ns, te_ns, train, cfg)
        rec["n_inner_oof"] = int(len(oof_pred))
        if thr is None:
            rec["status"] = "SKIPPED_INSUFFICIENT_DATA(inner calibration)"
            out_folds.append(rec)
            continue
        model = model_factory().fit(X.iloc[train], y[train])
        score = model.predict(X.iloc[val])
        rows.append(pd.DataFrame({"pos": val, "fold": f.fold, "year": years[val], "score": score, "threshold": thr,
                                  "state": assign_state(score, thr)}))
        rec["threshold"] = thr
        out_folds.append(rec)
        if hasattr(model, "feature_importance"):
            imps.append(model.feature_importance())
        if hasattr(model, "feature_coefficients"):
            c = model.feature_coefficients()
            if c:
                coefs.append(c)
    val_df = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
        {"pos": [], "fold": [], "year": [], "score": [], "threshold": [], "state": []})
    return WFResult(validation=val_df, folds=out_folds, importances=imps, coefficients=coefs)
