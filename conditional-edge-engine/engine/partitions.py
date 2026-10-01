"""Three non-overlapping chronological data stages and the hard data-partition guard.

    DEVELOPMENT / IS      open <  development_end
    CONFIRMATION OOS      development_end <= open < oos_end      (only after a manual human unlock)
    FINAL LOCKBOX         open >= lockbox_start                   (never opened by any code path)

Required ordering: development_end < oos_end <= lockbox_start (UTC midnights). The dates are supplied by the experiment
(EVENT_SPEC.yaml `partitions`), hashed into FROZEN_MANIFEST.json before any result exists, and equal to the campaign's.
No function here moves a boundary. ``development_view`` is the ONLY thing the IS stage receives: OOS and lockbox rows are
physically removed before any research code is called.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from engine.common import EngineError, canonical_json, validate_bars


class PartitionError(EngineError):
    pass


@dataclass(frozen=True)
class Partitions:
    development_end: pd.Timestamp
    oos_end: pd.Timestamp
    lockbox_start: pd.Timestamp

    def as_dict(self) -> dict:
        return {"development_end": f"{self.development_end:%Y-%m-%d}", "oos_end": f"{self.oos_end:%Y-%m-%d}",
                "lockbox_start": f"{self.lockbox_start:%Y-%m-%d}"}

    def hash(self) -> str:
        return hashlib.sha256(canonical_json(self.as_dict()).encode()).hexdigest()


def parse_partitions(d) -> Partitions:
    if not isinstance(d, dict) or set(d) != {"development_end", "oos_end", "lockbox_start"}:
        raise PartitionError("partitions must be exactly {development_end, oos_end, lockbox_start} (YYYY-MM-DD)")
    try:
        dev, oos, lock = (pd.Timestamp(str(d[k]), tz="UTC") for k in ("development_end", "oos_end", "lockbox_start"))
    except Exception as e:  # noqa: BLE001
        raise PartitionError(f"unparseable partition date: {e}") from e
    for k in d:
        if pd.Timestamp(str(d[k]), tz="UTC") != pd.Timestamp(str(d[k]), tz="UTC").normalize():
            raise PartitionError(f"{k} must be a calendar date (UTC midnight)")
    if not (dev < oos <= lock):
        raise PartitionError("partitions must satisfy development_end < oos_end <= lockbox_start (non-overlapping, chronological)")
    return Partitions(dev, oos, lock)


def development_view(bars: pd.DataFrame, p: Partitions) -> pd.DataFrame:
    """The ONLY bars the IS stage may see. OOS and lockbox rows are dropped, not masked."""
    validate_bars(bars)
    return bars[bars.index.tz_convert("UTC") < p.development_end].copy()


def oos_view(bars: pd.DataFrame, p: Partitions) -> pd.DataFrame:
    """Development + confirmation OOS bars (lockbox removed). Only the one-shot OOS stage and post-OOS CPCV call this."""
    validate_bars(bars)
    return bars[bars.index.tz_convert("UTC") < p.oos_end].copy()


def load_bars_before(path: str | Path, cutoff: pd.Timestamp, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """Load CSV/Parquet bars, discarding every row at/after ``cutoff`` immediately after reading (Parquet uses a row filter
    so later rows are never materialised)."""
    from engine.common import BAR_COLUMNS
    path = Path(path)
    if path.suffix.lower() in (".parquet", ".pq"):
        try:
            df = pd.read_parquet(path, filters=[(timestamp_col, "<", cutoff.to_pydatetime())])
        except Exception:  # noqa: BLE001 - index-stored timestamps etc.: fall back to read-then-drop
            df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    if timestamp_col in df.columns:
        df = df.set_index(timestamp_col)
    df.index = pd.DatetimeIndex(pd.to_datetime(df.index, utc=True))
    df.index.name = "timestamp"
    df = df[df.index < cutoff].sort_index()
    for c in BAR_COLUMNS:
        df[c] = df[c].astype("float64")
    validate_bars(df)
    return df[BAR_COLUMNS]
