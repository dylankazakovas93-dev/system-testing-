"""Shared utilities: paths, frozen-spec loading, hashing, bar loading. No research logic."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

CODE_ROOT = Path(__file__).resolve().parents[1]  # the repository holding frozen/, engine/, features/
FROZEN_VERSION = "v1"
BAR_COLUMNS = ["open", "high", "low", "close", "volume"]


class EngineError(Exception):
    """Base class for deliberate engine refusals."""


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def frozen_dir(version: str = FROZEN_VERSION) -> Path:
    return CODE_ROOT / "frozen" / version


def frozen_files(version: str = FROZEN_VERSION) -> list[Path]:
    base = frozen_dir(version)
    return sorted(p for p in base.rglob("*") if p.is_file())


def engine_code_files() -> list[Path]:
    files = sorted((CODE_ROOT / "engine").glob("*.py")) + sorted((CODE_ROOT / "features").glob("*.py"))
    files.append(CODE_ROOT / "ENGINE_VERSION")
    return files


def engine_code_hash() -> str:
    h = hashlib.sha256()
    for p in engine_code_files():
        h.update(str(p.relative_to(CODE_ROOT)).encode())
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


@dataclass(frozen=True)
class Frozen:
    """All frozen v1 specifications, loaded from YAML (the YAML files are the source of truth)."""

    version: str
    feature_bank: dict
    target_bank: dict
    model_bank: dict
    trial_policy: dict
    acceptance: dict
    instrument: dict

    @property
    def interval(self) -> pd.Timedelta:
        return pd.Timedelta(self.instrument["bar_interval"])

    @property
    def tz(self) -> str:
        return self.instrument["timezone"]

    def hashes(self) -> dict[str, str]:
        d = frozen_dir(self.version)
        return {
            "feature_bank_hash": sha256_file(d / "FEATURE_BANK.yaml"),
            "target_bank_hash": sha256_file(d / "TARGET_BANK.yaml"),
            "model_bank_hash": sha256_file(d / "MODEL_BANK.yaml"),
            "trial_policy_hash": sha256_file(d / "TRIAL_POLICY.yaml"),
            "acceptance_rules_hash": sha256_file(d / "ACCEPTANCE_RULES.yaml"),
        }


def load_frozen(version: str = FROZEN_VERSION, instrument: str = "NQ_1m") -> Frozen:
    d = frozen_dir(version)
    return Frozen(
        version=version,
        feature_bank=load_yaml(d / "FEATURE_BANK.yaml"),
        target_bank=load_yaml(d / "TARGET_BANK.yaml"),
        model_bank=load_yaml(d / "MODEL_BANK.yaml"),
        trial_policy=load_yaml(d / "TRIAL_POLICY.yaml"),
        acceptance=load_yaml(d / "ACCEPTANCE_RULES.yaml"),
        instrument=load_yaml(d / "instruments" / f"{instrument}.yaml"),
    )


def primary_target_names(frozen: Frozen) -> list[str]:
    return [t["name"] for t in frozen.target_bank["primary_targets"]]


def model_names(frozen: Frozen) -> list[str]:
    return list(frozen.model_bank["models"].keys())


def validate_bars(bars: pd.DataFrame) -> None:
    """Structural checks only (the external verifier does the deep data audit)."""
    if not isinstance(bars.index, pd.DatetimeIndex) or bars.index.tz is None:
        raise EngineError("bars must have a timezone-aware DatetimeIndex (open-stamped)")
    missing = [c for c in BAR_COLUMNS if c not in bars.columns]
    if missing:
        raise EngineError(f"bars missing columns {missing}")
    if not bars.index.is_monotonic_increasing or bars.index.has_duplicates:
        raise EngineError("bars must be strictly increasing in time with unique timestamps")


def load_bars(path: str | Path, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """Load CSV/Parquet bars into the canonical frame: UTC tz-aware open-stamped index."""
    path = Path(path)
    df = pd.read_parquet(path) if path.suffix.lower() in (".parquet", ".pq") else pd.read_csv(path)
    if timestamp_col in df.columns:
        df = df.set_index(timestamp_col)
    df.index = pd.DatetimeIndex(pd.to_datetime(df.index, utc=True))
    df.index.name = "timestamp"
    df = df.sort_index()
    for c in BAR_COLUMNS:
        df[c] = df[c].astype("float64")
    validate_bars(df)
    return df[BAR_COLUMNS]


def utc_ns(index_or_series) -> np.ndarray:
    """int64 nanoseconds since epoch (UTC) for any tz-aware datetime-like, independent of unit."""
    idx = pd.DatetimeIndex(index_or_series)
    if idx.tz is None:
        raise EngineError("naive timestamps are not allowed")
    return idx.tz_convert("UTC").as_unit("ns").asi8
