"""The ONLY research-creative surface: event definition.

event.py contract:   detect_events(bars, params) -> DataFrame[event_time, direction]
  * bars: open-stamped 1-minute OHLCV, tz-aware index, ``bars.attrs['bar_interval']`` set.
  * params: a StrictParams mapping of EVENT_SPEC.base_parameters (unregistered keys raise).
  * event_time: information time (a bar COMPLETION time, open + interval). For a Pine pivot that
    needs R right-hand bars it is the completion time of the R-th right-hand bar, NOT the plotted
    pivot location.
  * direction: +1 / -1.
The engine (not event.py) applies session eligibility, de-duplication and cooldown from the YAML.
"""
from __future__ import annotations

import ast
import importlib.util
import re
from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from engine.common import EngineError, Frozen, utc_ns, validate_bars

REQUIRED_SPEC_KEYS = ["experiment_id", "campaign_id", "hypothesis", "instrument", "data_interval",
                      "eligible_session", "direction_definition", "event_condition", "deduplication_rule",
                      "cooldown", "base_parameters", "sensitivity_parameters", "expected_information_time"]
DEDUP_RULES = ("keep_first_per_event_time", "drop_conflicting_same_time")
ALLOWED_LITERALS = {0, 1}            # structural only; every other number must come from the YAML
FORBIDDEN_IMPORTS = {"os", "sys", "subprocess", "socket", "requests", "urllib", "http", "pathlib", "shutil",
                     "pickle", "ctypes", "importlib", "builtins"}
_HHMM = re.compile(r"^\d{2}:\d{2}$")


class EventSpecError(EngineError):
    pass


class EventContractError(EngineError):
    pass


class EventCausalityError(EngineError):
    pass


# ---------------------------------------------------------------------------- spec
def load_spec(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
    if not isinstance(spec, dict):
        raise EventSpecError("EVENT_SPEC.yaml must be a mapping")
    return spec


def _hhmm(text) -> int:
    h, m = str(text).split(":")
    return int(h) * 60 + int(m)


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and np.isfinite(v)


def validate_spec(spec: dict, frozen: Frozen, *, experiment_id: str | None = None,
                  campaign_id: str | None = None) -> list[str]:
    """Return a list of human-readable errors (empty list = valid)."""
    errs: list[str] = []
    missing = [k for k in REQUIRED_SPEC_KEYS if k not in spec]
    if missing:
        return [f"missing required keys: {missing}"]
    if experiment_id and spec["experiment_id"] != experiment_id:
        errs.append(f"experiment_id {spec['experiment_id']!r} != {experiment_id!r}")
    if campaign_id and spec["campaign_id"] != campaign_id:
        errs.append(f"campaign_id {spec['campaign_id']!r} != {campaign_id!r}")
    hyp = spec["hypothesis"]
    if not isinstance(hyp, str) or len(hyp.strip()) < 20 or "TODO" in hyp:
        errs.append("hypothesis must be a real sentence (>= 20 chars, no TODO)")
    if spec["instrument"] != frozen.instrument["instrument"]:
        errs.append(f"instrument must be {frozen.instrument['instrument']!r}")
    if str(spec["data_interval"]) != frozen.instrument["bar_interval"]:
        errs.append(f"data_interval must be {frozen.instrument['bar_interval']!r}")
    sess = spec["eligible_session"]
    if not (isinstance(sess, dict) and _HHMM.match(str(sess.get("start", ""))) and _HHMM.match(str(sess.get("end", "")))):
        errs.append("eligible_session needs {start: 'HH:MM', end: 'HH:MM'} in exchange-local time")
    else:
        lo = _hhmm(frozen.instrument["rth"]["open"]) + int(frozen.interval.total_seconds() // 60)
        hi = _hhmm(frozen.instrument["rth"]["close"])
        if not (lo <= _hhmm(sess["start"]) < _hhmm(sess["end"]) <= hi):
            errs.append(f"eligible_session must satisfy {lo // 60:02d}:{lo % 60:02d} <= start < end <= "
                        f"{frozen.instrument['rth']['close']} (v1 session features are defined inside RTH, and need "
                        f"at least one completed RTH bar)")
    dd = spec["direction_definition"]
    if not (isinstance(dd, dict) and isinstance(dd.get("rule"), str) and dd["rule"].strip()
            and isinstance(dd.get("values"), list) and dd["values"] and set(dd["values"]) <= {-1, 1}):
        errs.append("direction_definition needs {rule: <non-empty text>, values: subset of [-1, 1]}")
    ec = spec["event_condition"]
    params = spec["base_parameters"]
    if not (isinstance(ec, dict) and isinstance(ec.get("description"), str) and ec["description"].strip()
            and isinstance(ec.get("parameters_used"), list)):
        errs.append("event_condition needs {description: text, parameters_used: [parameter names]}")
    elif isinstance(params, dict) and not set(ec["parameters_used"]) <= set(params):
        errs.append(f"event_condition.parameters_used not in base_parameters: {sorted(set(ec['parameters_used']) - set(params))}")
    if spec["deduplication_rule"] not in DEDUP_RULES:
        errs.append(f"deduplication_rule must be one of {DEDUP_RULES}")
    cd = spec["cooldown"]
    if not (isinstance(cd, dict) and isinstance(cd.get("bars"), int) and not isinstance(cd["bars"], bool) and cd["bars"] >= 0):
        errs.append("cooldown needs {bars: integer >= 0}")
    if not isinstance(params, dict) or not all(_is_num(v) for v in params.values()):
        errs.append("base_parameters must be a mapping of name -> finite number")
        params = {}
    sens = spec["sensitivity_parameters"]
    if not isinstance(sens, list) or len(sens) > frozen.trial_policy["sensitivity"]["max_parameters"]:
        errs.append(f"sensitivity_parameters must be a list of at most "
                    f"{frozen.trial_policy['sensitivity']['max_parameters']} names")
    else:
        for name in sens:
            if name not in params:
                errs.append(f"sensitivity parameter {name!r} is not in base_parameters")
            elif isinstance(params[name], int) and params[name] < 3:
                errs.append(f"integer sensitivity parameter {name!r} must be >= 3 so that x0.75 and x1.25 differ")
    eit = spec["expected_information_time"]
    if not (isinstance(eit, dict) and isinstance(eit.get("rule"), str) and eit["rule"].strip()
            and "confirmation_delay_bars" in eit):
        errs.append("expected_information_time needs {rule: text, confirmation_delay_bars: int | parameter name}")
    else:
        cdb = eit["confirmation_delay_bars"]
        if not ((isinstance(cdb, int) and not isinstance(cdb, bool) and cdb >= 0) or (isinstance(cdb, str) and cdb in params)):
            errs.append("confirmation_delay_bars must be an integer >= 0 or the name of a base parameter")
    tv = spec.get("tradingview", {}) or {}
    if tv.get("reference_pine"):
        ind = spec.get("indicator")
        need = ["inputs", "signal_direction_rule", "bar_close_confirmation", "repainting_pivot_delay_bars"]
        if not isinstance(ind, dict) or any(k not in ind for k in need):
            errs.append(f"tradingview.reference_pine is set: indicator block needs {need}")
        else:
            if not (isinstance(ind["inputs"], dict) and ind["inputs"]):
                errs.append("indicator.inputs must list the indicator inputs with their frozen values")
            else:
                for k, v in ind["inputs"].items():
                    if _is_num(v) and (k not in params or params[k] != v):
                        errs.append(f"numeric indicator input {k}={v} is not registered (equal) in base_parameters")
            for k in ("signal_direction_rule", "bar_close_confirmation"):
                if not (isinstance(ind[k], str) and ind[k].strip()):
                    errs.append(f"indicator.{k} must be non-empty text")
            d = ind["repainting_pivot_delay_bars"]
            if not ((isinstance(d, int) and not isinstance(d, bool) and d >= 0) or (isinstance(d, str) and d in params)):
                errs.append("indicator.repainting_pivot_delay_bars must be an integer >= 0 or a base parameter name")
    return errs


# ---------------------------------------------------------------------------- static scan of event.py
def static_scan_event_source(source: str) -> list[str]:
    """Flag unregistered magic numbers and obviously unsafe / non-causal constructs. Heuristic."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [f"event.py does not parse: {e}"]
    issues: list[str] = []
    has_detect = False
    docstring_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant):
                docstring_ids.add(id(body[0].value))
        if isinstance(node, ast.FunctionDef) and node.name == "detect_events":
            has_detect = True
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            if node.value not in ALLOWED_LITERALS:
                issues.append(f"line {node.lineno}: unregistered numeric literal {node.value!r} "
                              f"(every numeric threshold must come from EVENT_SPEC base_parameters via params[...])")
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in FORBIDDEN_IMPORTS:
                    issues.append(f"line {node.lineno}: forbidden import {a.name}")
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in FORBIDDEN_IMPORTS:
            issues.append(f"line {node.lineno}: forbidden import {node.module}")
        if isinstance(node, ast.Call):
            fn = node.func
            name = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else ""
            if name in ("open", "eval", "exec", "compile", "__import__"):
                issues.append(f"line {node.lineno}: forbidden call {name}()")
            if name in ("bfill", "backfill"):
                issues.append(f"line {node.lineno}: backward fill uses future data")
            if name == "shift" and node.args:
                a0 = node.args[0]
                if (isinstance(a0, ast.UnaryOp) and isinstance(a0.op, ast.USub)) or \
                        (isinstance(a0, ast.Constant) and isinstance(a0.value, (int, float)) and a0.value < 0):
                    issues.append(f"line {node.lineno}: negative shift reads future bars")
            for kw in node.keywords:
                if kw.arg == "center" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    issues.append(f"line {node.lineno}: centered window reads future bars")
    if not has_detect:
        issues.append("event.py must define detect_events(bars, params)")
    return issues


# ---------------------------------------------------------------------------- params / module loading
class StrictParams(Mapping):
    """Read-only parameter mapping; unregistered keys raise and usage is tracked."""

    def __init__(self, values: dict):
        self._v = dict(values)
        self.accessed: set[str] = set()

    def __getitem__(self, key):
        if key not in self._v:
            raise KeyError(f"parameter {key!r} is not registered in EVENT_SPEC base_parameters")
        self.accessed.add(key)
        return self._v[key]

    def __iter__(self):
        return iter(self._v)

    def __len__(self):
        return len(self._v)

    def unused(self) -> list[str]:
        return sorted(set(self._v) - self.accessed)


def load_event_module(path: Path):
    path = Path(path)
    spec = importlib.util.spec_from_file_location(f"_event_{abs(hash(str(path.resolve())))}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not callable(getattr(mod, "detect_events", None)):
        raise EventContractError(f"{path} does not define detect_events(bars, params)")
    return mod


# ---------------------------------------------------------------------------- event generation
def _prepared(bars: pd.DataFrame, frozen: Frozen) -> pd.DataFrame:
    out = bars.copy()
    out.attrs["bar_interval"] = frozen.interval
    return out


def raw_events(module, bars: pd.DataFrame, params: dict, frozen: Frozen) -> tuple[pd.DataFrame, StrictParams]:
    validate_bars(bars)
    sp = StrictParams(params)
    ev = module.detect_events(_prepared(bars, frozen), sp)
    if not isinstance(ev, pd.DataFrame) or not {"event_time", "direction"} <= set(ev.columns):
        raise EventContractError("detect_events must return a DataFrame with columns event_time, direction")
    ev = ev[["event_time", "direction"]].reset_index(drop=True)
    if len(ev) == 0:
        return pd.DataFrame({"event_time": pd.Series(dtype="datetime64[ns, UTC]"),
                             "direction": pd.Series(dtype="int64")}), sp
    t = pd.to_datetime(ev["event_time"])
    if getattr(t.dt, "tz", None) is None:
        raise EventContractError("event_time must be timezone-aware")
    if not np.isin(ev["direction"].to_numpy(), (-1, 1)).all():
        raise EventContractError("direction must be +1 or -1")
    complete = utc_ns(bars.index) + int(frozen.interval.value)
    ens = utc_ns(pd.DatetimeIndex(t))
    known = np.isin(ens, complete)
    if not known.all():
        bad = pd.DatetimeIndex(t[~known]).tolist()[:5]
        raise EventContractError(
            f"event_time must be a bar COMPLETION time (open + {frozen.interval}); "
            f"{int((~known).sum())} events violate this, e.g. {bad}")
    return pd.DataFrame({"event_time": pd.DatetimeIndex(t).tz_convert("UTC"),
                         "direction": ev["direction"].astype("int64").to_numpy()}), sp


def apply_event_rules(raw: pd.DataFrame, spec: dict, frozen: Frozen) -> pd.DataFrame:
    """Session eligibility -> de-duplication -> cooldown (all from the YAML); assigns event ids."""
    ev = raw.sort_values("event_time", kind="stable").reset_index(drop=True)
    if len(ev):
        local = ev["event_time"].dt.tz_convert(frozen.tz)
        minute = (local.dt.hour * 60 + local.dt.minute).to_numpy()
        sess = spec["eligible_session"]
        ev = ev[(minute >= _hhmm(sess["start"])) & (minute < _hhmm(sess["end"]))].reset_index(drop=True)
    rule = spec["deduplication_rule"]
    if len(ev):
        if rule == "keep_first_per_event_time":
            ev = ev.drop_duplicates("event_time", keep="first")
        else:   # drop_conflicting_same_time: identical duplicates collapse, opposite signals cancel
            g = ev.groupby("event_time")["direction"].nunique()
            conflict = set(g[g > 1].index)
            ev = ev[~ev["event_time"].isin(conflict)].drop_duplicates("event_time", keep="first")
        ev = ev.reset_index(drop=True)
    cool = int(spec["cooldown"]["bars"]) * frozen.interval
    if len(ev) and cool > pd.Timedelta(0):
        keep, last = [], None
        for t in ev["event_time"]:
            ok = last is None or t >= last + cool
            keep.append(ok)
            if ok:
                last = t
        ev = ev[np.array(keep)].reset_index(drop=True)
    ev = ev.copy()
    ev["event_id"] = [f"{spec['experiment_id']}_E{t:%Y%m%dT%H%M%S}" for t in ev["event_time"]]
    return ev[["event_id", "event_time", "direction"]]


def generate_events(module, bars: pd.DataFrame, spec: dict, frozen: Frozen,
                    params: dict | None = None) -> tuple[pd.DataFrame, StrictParams]:
    params = dict(spec["base_parameters"] if params is None else params)
    raw, sp = raw_events(module, bars, params, frozen)
    return apply_event_rules(raw, spec, frozen), sp


def check_event_causality(module, bars: pd.DataFrame, spec: dict, frozen: Frozen, *, n_cutoffs: int = 8,
                          seed: int = 1729) -> dict:
    """Truncation + future-mutation invariance at the tightest cutoffs (event completion times).

    Raises EventCausalityError on the first violation. Heuristic evidence, not proof.
    """
    full, _ = generate_events(module, bars, spec, frozen)
    full_raw, _ = raw_events(module, bars, spec["base_parameters"], frozen)
    if len(full_raw) == 0:
        return {"cutoffs": 0, "note": "no events"}
    times = pd.DatetimeIndex(np.sort(full_raw["event_time"].unique()))
    rng = np.random.default_rng(seed)
    picks = set(np.linspace(0, len(times) - 1, min(n_cutoffs // 2, len(times))).astype(int).tolist())
    picks |= set(rng.choice(len(times), size=min(n_cutoffs - len(picks), len(times)), replace=False).tolist())
    interval = frozen.interval
    checked = 0
    for k in sorted(picks):
        T = times[k]
        known = bars[(bars.index + interval) <= T]
        future = bars[(bars.index + interval) > T]
        want = full_raw[full_raw["event_time"] <= T].sort_values(["event_time", "direction"]).reset_index(drop=True)
        trunc, _ = raw_events(module, known, spec["base_parameters"], frozen)
        mutated = bars.copy()
        scale = rng.uniform(0.2, 5.0, size=(len(future), 1))
        mutated.loc[future.index, ["open", "high", "low", "close"]] = future[["open", "high", "low", "close"]].to_numpy() * scale
        mutated.loc[future.index, "volume"] = rng.uniform(0, 1e6, len(future))
        mut, _ = raw_events(module, mutated, spec["base_parameters"], frozen)
        for label, got in (("truncated", trunc), ("future-mutated", mut)):
            got = got[got["event_time"] <= T].sort_values(["event_time", "direction"]).reset_index(drop=True)
            if len(got) != len(want) or not (got["event_time"].to_numpy() == want["event_time"].to_numpy()).all() \
                    or not (got["direction"].to_numpy() == want["direction"].to_numpy()).all():
                raise EventCausalityError(
                    f"event.py is not causal: events known at {T} differ between the full run and the {label} run "
                    f"({len(want)} vs {len(got)} events)")
        checked += 1
    return {"cutoffs": checked}
