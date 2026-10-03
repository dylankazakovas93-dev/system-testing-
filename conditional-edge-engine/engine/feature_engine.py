"""Frozen feature engine v1: EVENT -> FROZEN MARKET STATE.

The engine only ever receives bars complete by the LAST event_time
(``open + interval <= max(event_time)``); later bars are dropped before any computation.
For each event the last completed bar is located by timestamp. Every feature module indexes
only positions <= that bar (verified by truncation / future-mutation tests).
"""
from __future__ import annotations

import importlib

import numpy as np
import pandas as pd

from engine.common import EngineError, Frozen, canonical_json, utc_ns, validate_bars
from features._base import BarContext

CHUNK = 2048


class FeatureQualityFailure(EngineError):
    """DATA / FEATURE QUALITY FAILURE: a mandatory feature is NaN after deterministic warm-up."""


_NAMES_CACHE: dict[str, list[str]] = {}


def feature_names(frozen: Frozen) -> list[str]:
    """Names in frozen order, produced by running each family on a tiny dummy context (cached per bank)."""
    key = canonical_json([frozen.feature_bank, frozen.instrument])
    if key not in _NAMES_CACHE:
        _NAMES_CACHE[key] = _checked_names(frozen)
    return list(_NAMES_CACHE[key])


def _checked_names(frozen: Frozen) -> list[str]:
    names = _family_names(frozen)
    expected = frozen.feature_bank["expected_feature_count"]
    if len(names) != expected or len(set(names)) != len(names):
        raise EngineError(f"feature bank produces {len(names)} unique names, expected {expected}")
    return names


def _dummy_ctx(frozen: Frozen) -> BarContext:
    n = 8
    idx = pd.date_range("2020-01-06 15:00", periods=n, freq="1min", tz="UTC")
    a = np.linspace(100, 101, n)
    return _make_ctx(pd.DataFrame({"open": a, "high": a + 1, "low": a - 1, "close": a, "volume": a}, index=idx), frozen)


def _family_names(frozen: Frozen) -> list[str]:
    ctx = _dummy_ctx(frozen)
    ctx.cache["event_ns"] = np.array([ctx.index_ns[-1] + ctx.interval_ns], dtype=np.int64)
    pos = np.array([len(ctx.close) - 1])
    names: list[str] = []
    for fam in frozen.feature_bank["families"]:
        mod = importlib.import_module(fam["module"])
        names.extend(mod.compute(ctx, pos, fam["params"]).keys())
    return names


def _make_ctx(bars: pd.DataFrame, frozen: Frozen) -> BarContext:
    inst = frozen.instrument
    return BarContext(
        open=bars["open"].to_numpy("float64"), high=bars["high"].to_numpy("float64"),
        low=bars["low"].to_numpy("float64"), close=bars["close"].to_numpy("float64"),
        volume=bars["volume"].to_numpy("float64"),
        index_ns=utc_ns(bars.index), interval_ns=int(frozen.interval.value),
        index=bars.index.tz_convert("UTC"), tz=inst["timezone"],
        rth_open=inst["rth"]["open"], rth_close=inst["rth"]["close"],
        eth_start=inst["eth_session_start"], rth_minutes=int(inst["rth"]["minutes"]),
    )


def last_completed_position(bars_index: pd.DatetimeIndex, event_time: pd.Series, interval: pd.Timedelta) -> np.ndarray:
    """Position of the last bar with open + interval <= event_time (-1 if none)."""
    complete_ns = utc_ns(bars_index) + int(interval.value)
    return np.searchsorted(complete_ns, utc_ns(pd.DatetimeIndex(event_time)), side="right") - 1


def compute_features(bars: pd.DataFrame, events: pd.DataFrame, frozen: Frozen) -> pd.DataFrame:
    """One feature row per event (never omitted). Columns: event_id, feature_asof_time, <56 features>."""
    validate_bars(bars)
    names = feature_names(frozen)
    if len(events) == 0:
        out = pd.DataFrame({"event_id": pd.Series(dtype=object),
                            "feature_asof_time": pd.Series(dtype="datetime64[ns, UTC]"),
                            **{n: pd.Series(dtype="float64") for n in names}})
        out.attrs["completed_bars"] = np.array([], dtype="int64")
        return out
    event_time = pd.DatetimeIndex(events["event_time"])
    interval = frozen.interval
    # Hard information boundary: drop every bar not complete by the last event_time.
    avail = bars[(bars.index + interval) <= event_time.max()]
    if len(avail) == 0:
        raise EngineError("no completed bars available before the first event")
    ctx = _make_ctx(avail, frozen)
    pos_all = last_completed_position(avail.index, event_time, interval)
    ev_ns = utc_ns(event_time)
    cols: dict[str, list[np.ndarray]] = {n: [] for n in names}
    for s in range(0, len(pos_all), CHUNK):
        pos = pos_all[s:s + CHUNK]
        ctx.cache["event_ns"] = ev_ns[s:s + CHUNK]
        got: dict[str, np.ndarray] = {}
        for fam in frozen.feature_bank["families"]:
            mod = importlib.import_module(fam["module"])
            got.update(mod.compute(ctx, pos, fam["params"]))
        if list(got.keys()) != names:
            raise EngineError("feature modules disagree with frozen feature order/names")
        for n in names:
            cols[n].append(got[n])
    out = pd.DataFrame({"event_id": events["event_id"].to_numpy(),
                        "feature_asof_time": event_time.tz_convert("UTC")})
    for n in names:
        out[n] = np.concatenate(cols[n])
    out.attrs["completed_bars"] = (pos_all + 1).astype("int64")
    return out


def model_eligibility(features: pd.DataFrame, frozen: Frozen, bars: pd.DataFrame | None = None,
                      events: pd.DataFrame | None = None) -> np.ndarray:
    """Boolean mask: completed-bar count >= min_history_bars (deterministic warm-up rule)."""
    completed = features.attrs.get("completed_bars")
    if completed is None:
        if bars is None or events is None:
            raise EngineError("completed-bar counts unavailable; pass bars and events")
        completed = last_completed_position(bars.index, events["event_time"], frozen.interval) + 1
    return np.asarray(completed) >= int(frozen.feature_bank["min_history_bars"])


def assert_feature_quality(features: pd.DataFrame, eligible: np.ndarray, frozen: Frozen) -> None:
    """Raise FeatureQualityFailure if any model-eligible row has a non-finite mandatory feature.

    No imputation, no silent dropping: the experiment must not proceed on bad data.
    """
    names = feature_names(frozen)
    block = features.loc[eligible, names].to_numpy(dtype="float64")
    bad = ~np.isfinite(block)
    if bad.any():
        rows, cols = np.nonzero(bad)
        worst = pd.Series([names[c] for c in cols]).value_counts().head(8).to_dict()
        ids = features.loc[eligible, "event_id"].to_numpy()[np.unique(rows)][:5].tolist()
        raise FeatureQualityFailure(
            f"DATA / FEATURE QUALITY FAILURE: {int(bad.any(axis=1).sum())} model-eligible events have "
            f"non-finite mandatory features after warm-up. Features: {worst}; e.g. events {ids}")
