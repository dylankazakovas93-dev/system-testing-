"""Three non-overlapping chronological data stages and the hard data-partition guard.

    DEVELOPMENT / IS        open <  development_end
    SELECTION_HOLDOUT       development_end <= open < selection_holdout_end   (exactly 1 or 2 calendar years; opened only by the
                            human campaign process; NOT independent confirmation: it may be used to choose the final configuration)
    FINAL_LOCKBOX           open >= lockbox_start                            (the true untouched confirmation; never opened by any code path)

Required: selection_holdout_start = development_end; selection_holdout_end = development_end + 1 or 2 calendar years EXACTLY (no duration
search); lockbox_start = selection_holdout_end (the lockbox begins immediately after the holdout). The dates are chosen BEFORE any IS result
(EVENT_SPEC.yaml `partitions`, hashed into FROZEN_MANIFEST.json, equal to the campaign's). No function here moves a boundary.
``development_view`` is the ONLY thing the IS stage receives: holdout and lockbox rows are physically removed before any research code is called.
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
    selection_holdout_end: pd.Timestamp
    lockbox_start: pd.Timestamp

    @property
    def selection_holdout_start(self) -> pd.Timestamp:
        return self.development_end

    @property
    def selection_holdout_years(self) -> int:
        return int(self.selection_holdout_end.year - self.development_end.year)

    def as_dict(self) -> dict:
        return {"development_end": f"{self.development_end:%Y-%m-%d}", "selection_holdout_end": f"{self.selection_holdout_end:%Y-%m-%d}",
                "lockbox_start": f"{self.lockbox_start:%Y-%m-%d}"}

    def hash(self) -> str:
        return hashlib.sha256(canonical_json(self.as_dict()).encode()).hexdigest()


def parse_partitions(d) -> Partitions:
    if not isinstance(d, dict) or set(d) != {"development_end", "selection_holdout_end", "lockbox_start"}:
        raise PartitionError("partitions must be exactly {development_end, selection_holdout_end, lockbox_start} (YYYY-MM-DD; holdout = 1 or 2 calendar years)")
    try:
        dev, selection_holdout, lock = (pd.Timestamp(str(d[k]), tz="UTC") for k in ("development_end", "selection_holdout_end", "lockbox_start"))
    except Exception as e:  # noqa: BLE001
        raise PartitionError(f"unparseable partition date: {e}") from e
    for k in d:
        if pd.Timestamp(str(d[k]), tz="UTC") != pd.Timestamp(str(d[k]), tz="UTC").normalize():
            raise PartitionError(f"{k} must be a calendar date (UTC midnight)")
    years = [y for y in (1, 2) if dev + pd.DateOffset(years=y) == selection_holdout]
    if not years:
        raise PartitionError("selection_holdout_end must be development_end + exactly 1 or 2 calendar years (no other duration)")
    if lock != selection_holdout:
        raise PartitionError("lockbox_start must equal selection_holdout_end (the final lockbox begins immediately after the selection holdout)")
    return Partitions(dev, selection_holdout, lock)


def development_view(bars: pd.DataFrame, p: Partitions) -> pd.DataFrame:
    """The ONLY bars the IS stage may see. SELECTION HOLDOUT and lockbox rows are dropped, not masked."""
    validate_bars(bars)
    return bars[bars.index.tz_convert("UTC") < p.development_end].copy()


def selection_holdout_view(bars: pd.DataFrame, p: Partitions) -> pd.DataFrame:
    """Development + selection holdout bars (lockbox removed). Only the one-shot SELECTION HOLDOUT stage and post-SELECTION HOLDOUT CPCV call this."""
    validate_bars(bars)
    return bars[bars.index.tz_convert("UTC") < p.selection_holdout_end].copy()


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
