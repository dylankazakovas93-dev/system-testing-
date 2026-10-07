"""Monetisation (bracket) study  (frozen/v1/MONETISATION_SPEC.yaml, added in v2.3.0).

*** DEVELOPMENT DATA ONLY - NOT A SELECTION TRIAL - NOT CONFIRMATION ***

Given the events a final configuration selected in DEVELOPMENT (event time and direction), simulate a grid of ATR brackets
(stop = k_s x ATR, target = k_t x ATR, optional time limit, ATR(14) of 1-minute or 5-minute bars), net of the frozen round-trip cost, and
pick ONE bracket by a pre-written rule: the cell whose whole +-25% neighbourhood is good. If no cell is stable the answer is NO_STABLE_BRACKET;
there is no fallback to the best single cell.

Conventions (all causal): entry = open of the first bar whose open >= event_time; ATR = latest COMPLETED bar at event_time; a bar that touches
both stop and target counts as a stop; every window is truncated at the RTH close of the event's session; touched levels fill at the level.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from engine.common import Frozen, frozen_dir, load_yaml, utc_ns
from engine.target_engine import effective_horizon_bars, forward_start

SPEC_FILE = "MONETISATION_SPEC.yaml"
NO_STABLE = "NO_STABLE_BRACKET"
SESSION = "SESSION"                         # expiry label used when the spec lists no time limit


def load_spec(version: str = "v1") -> dict:
    return load_yaml(frozen_dir(version) / SPEC_FILE)


def spec_sha256(version: str = "v1") -> str:
    return hashlib.sha256((frozen_dir(version) / SPEC_FILE).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------ ATR
def wilder_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
    """Wilder RMA of the true range (alpha = 1/period). The first ``period`` values are NaN (warm-up)."""
    prev = np.r_[close[0], close[:-1]]
    tr = np.maximum.reduce([high - low, np.abs(high - prev), np.abs(low - prev)])
    atr = pd.Series(tr).ewm(alpha=1.0 / period, adjust=False).mean().to_numpy().copy()
    atr[:period] = np.nan
    return atr


def _resample(bars: pd.DataFrame, minutes: int) -> pd.DataFrame:
    g = bars.resample(f"{minutes}min", label="left", closed="left")
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last()})
    return out.dropna()


def atr_at_events(bars: pd.DataFrame, event_time, base: str, period: int, frozen: Frozen) -> np.ndarray:
    """ATR of the latest COMPLETED bar (1m or 5m) at each event time (a bar stamped s is complete at s + its length)."""
    minutes = {"1m": 1, "5m": 5}[base]
    b = bars if minutes == 1 else _resample(bars, minutes)
    atr = wilder_atr(b["high"].to_numpy("float64"), b["low"].to_numpy("float64"), b["close"].to_numpy("float64"), period)
    known_ns = utc_ns(b.index) + minutes * int(frozen.interval.value)
    pos = np.searchsorted(known_ns, utc_ns(pd.DatetimeIndex(event_time)), side="right") - 1
    out = np.full(len(pos), np.nan)
    ok = pos >= 0
    out[ok] = atr[pos[ok]]
    return out


# ------------------------------------------------------------------------------------------------ forward windows
class Windows:
    """Forward 1-minute windows of every event: arrays (n_events, n_max), NaN past each event's allowed length."""

    def __init__(self, bars: pd.DataFrame, event_time, direction, n_max: int, frozen: Frozen):
        et = pd.DatetimeIndex(event_time)
        first = forward_start(bars, et)
        n_close = effective_horizon_bars(et, n_max, frozen)                       # truncated at the RTH close
        ns = utc_ns(bars.index)
        step = int(frozen.interval.value)
        n_eff = np.zeros(len(et), dtype="int64")
        for i in range(len(et)):                                                  # truncate at the first time gap / the end of the data
            f, n = int(first[i]), int(n_close[i])
            n = min(n, len(ns) - f)
            if n <= 0:
                continue
            seg = ns[f:f + n]
            gap = np.flatnonzero(np.diff(seg) != step)
            n_eff[i] = gap[0] + 1 if len(gap) else n
        self.n_eff = n_eff
        self.n_max = n_max
        idx = np.clip(first[:, None] + np.arange(n_max)[None, :], 0, len(ns) - 1)
        valid = np.arange(n_max)[None, :] < n_eff[:, None]
        h, l, c, o = (bars[k].to_numpy("float64") for k in ("high", "low", "close", "open"))
        self.p0 = np.where(first < len(ns), o[np.clip(first, 0, len(ns) - 1)], np.nan)
        d = np.asarray(direction, dtype="float64")
        self.d = d
        H = np.where(valid, h[idx], np.nan)
        L = np.where(valid, l[idx], np.nan)
        self.close = np.where(valid, c[idx], np.nan)
        self.fav = np.where(d[:, None] > 0, H - self.p0[:, None], self.p0[:, None] - L)    # favourable excursion from the entry, points
        self.adv = np.where(d[:, None] > 0, self.p0[:, None] - L, H - self.p0[:, None])    # adverse excursion, points


def simulate(w: Windows, atr: np.ndarray, k_stop: float, k_target: float, expiry, cost_points: float) -> dict:
    """Net P&L (points) per event for one bracket. ``expiry`` = bars or SESSION. Events without ATR or without a forward bar are excluded."""
    n_e = w.n_eff if expiry == SESSION else np.minimum(int(expiry), w.n_eff)
    ok = np.isfinite(atr) & (atr > 0) & (n_e > 0) & np.isfinite(w.p0)
    stop, tgt = k_stop * atr, k_target * atr
    inwin = np.arange(w.n_max)[None, :] < n_e[:, None]
    with np.errstate(invalid="ignore"):
        hit_t = (w.fav >= tgt[:, None]) & inwin
        hit_s = (w.adv >= stop[:, None]) & inwin
    big = w.n_max + 1
    it = np.where(hit_t.any(1), hit_t.argmax(1), big)
    is_ = np.where(hit_s.any(1), hit_s.argmax(1), big)
    target = it < is_                                                              # same-bar touch (it == is_) is a stop
    stopped = (is_ <= it) & (is_ < big)
    last = np.clip(n_e - 1, 0, w.n_max - 1)
    exp_pnl = w.d * (w.close[np.arange(len(last)), last] - w.p0)
    gross = np.where(target, tgt, np.where(stopped, -stop, exp_pnl))
    net = gross - cost_points
    return {"ok": ok, "net": net[ok], "gross": gross[ok], "stop": stop[ok], "target_hit": target[ok], "stopped": stopped[ok],
            "idx": np.flatnonzero(ok)}


# ------------------------------------------------------------------------------------------------ study
def _cell_stats(sim: dict, years: np.ndarray, min_events_year: int) -> dict:
    net = sim["net"]
    n = len(net)
    yr = years[sim["idx"]]
    per_year = {}
    for y in np.unique(yr):
        m = yr == y
        if int(m.sum()) >= min_events_year:
            per_year[int(y)] = float(net[m].mean())
    return {"n_trades": int(n), "net_expectancy": float(net.mean()) if n else float("nan"),
            "net_expectancy_R": float((net / sim["stop"]).mean()) if n else float("nan"),
            "hit_target": float(sim["target_hit"].mean()) if n else float("nan"),
            "hit_stop": float(sim["stopped"].mean()) if n else float("nan"),
            "eligible_years": len(per_year), "positive_years": int(sum(v > 0 for v in per_year.values())), "by_year": per_year}


def run_study(bars: pd.DataFrame, events: pd.DataFrame, frozen: Frozen, spec: dict | None = None, *, n_weeks: float | None = None) -> dict:
    """``events``: columns ``event_time`` (tz-aware) and ``direction`` (+1/-1) = the events the final configuration selected in DEVELOPMENT."""
    spec = spec or load_spec(frozen.version)
    g, nb, pk = spec["grid"], spec["neighbours"], spec["pick"]
    cost = float(spec["costs"]["round_trip_ticks"]) * frozen.tick_size
    expiries = list(g["expiry_bars"]) or [SESSION]
    n_max = int(max([e for e in expiries if e != SESSION], default=0)) or int(frozen.instrument["rth"]["minutes"])
    if SESSION in expiries:
        n_max = int(frozen.instrument["rth"]["minutes"])
    ev = events.sort_values("event_time").reset_index(drop=True)
    et = pd.DatetimeIndex(ev["event_time"])
    years = np.asarray(et.tz_convert("UTC").year)
    w = Windows(bars, et, ev["direction"].to_numpy(), n_max, frozen)
    mults = [1.0] + list(nb["multipliers"])
    cells, cache = [], {}

    def stats(base, atr, ks, kt, ex):
        key = (base, round(ks, 6), round(kt, 6), ex)
        if key not in cache:
            cache[key] = _cell_stats(simulate(w, atr, ks, kt, ex, cost), years, pk["min_events_for_eligible_year"])
        return cache[key]

    for base in spec["atr"]["bases"]:
        atr = atr_at_events(bars, et, base, int(spec["atr"]["period"]), frozen)
        for ex in expiries:
            for ks in g["stop_atr"]:
                for kt in g["target_atr"]:
                    c = stats(base, atr, ks, kt, ex)
                    neigh = [stats(base, atr, ks * ms, kt * mt, ex) for ms in mults for mt in mults if not (ms == 1.0 and mt == 1.0)]
                    ne = [x["net_expectancy"] for x in neigh]
                    cen = c["net_expectancy"]
                    why = []
                    if c["n_trades"] < pk["min_trades"]:
                        why.append(f"only {c['n_trades']} trades (< {pk['min_trades']})")
                    if not cen > 0:
                        why.append("centre net expectancy not positive")
                    if c["eligible_years"] == 0 or c["positive_years"] / c["eligible_years"] < pk["min_positive_year_fraction"]:
                        why.append(f"positive years {c['positive_years']}/{c['eligible_years']} < {pk['min_positive_year_fraction']:.0%}")
                    if nb["neighbours_must_stay_positive"] and not all(np.isfinite(x) and x > 0 for x in ne):
                        why.append("a neighbour is not positive")
                    if cen > 0 and not all(np.isfinite(x) and x >= nb["min_retained_expectancy_fraction"] * cen for x in ne):
                        why.append(f"a neighbour keeps < {nb['min_retained_expectancy_fraction']:.0%} of the centre expectancy")
                    cells.append({"atr_base": base, "stop_atr": ks, "target_atr": kt, "expiry": ex, "reward_risk": kt / ks,
                                  **{k: c[k] for k in ("n_trades", "net_expectancy", "net_expectancy_R", "hit_target", "hit_stop",
                                                      "eligible_years", "positive_years")},
                                  "min_neighbour_expectancy": float(np.nanmin(ne)) if ne else float("nan"),
                                  "neighbourhood_score": float(min([cen] + ne)) if all(np.isfinite(ne)) else float("nan"),
                                  "stable": not why, "reasons": why})
    stable = [c for c in cells if c["stable"]]
    order_atr = {b: i for i, b in enumerate(spec["atr"]["bases"])}
    exp_key = lambda c: (10 ** 9 if c["expiry"] == SESSION else c["expiry"])
    chosen = None
    if stable:
        chosen = sorted(stable, key=lambda c: (-c["neighbourhood_score"], -c["net_expectancy"], order_atr[c["atr_base"]],
                                               c["stop_atr"], c["target_atr"], exp_key(c)))[0]
    n_trades_week = (chosen["n_trades"] / n_weeks) if (chosen and n_weeks) else None
    return {"label": spec["label"], "spec_sha256": spec_sha256(frozen.version), "n_events_in": int(len(ev)),
            "cost_points_round_trip": cost, "n_cells": len(cells), "n_stable": len(stable),
            "decision": "BRACKET_FOUND" if chosen else NO_STABLE,
            "chosen": chosen, "chosen_trades_per_week": n_trades_week,
            "chosen_by_year": (cache[(chosen["atr_base"], round(chosen["stop_atr"], 6), round(chosen["target_atr"], 6), chosen["expiry"])]["by_year"]
                               if chosen else None),
            "cells": cells,
            "notes": ["Development data only; never confirmation. The chosen bracket must still be evaluated on data it has not seen.",
                      "Touched levels fill at the level (no gap slippage); same-bar stop/target touches count as stops."]}


# ------------------------------------------------------------------------------------------------ experiment-level runner
ALLOWED_STATUSES = ("CPCV_CONFIRMED", "AWAITING_FINAL_LOCKBOX_APPROVAL")


def _report_md(r: dict, experiment_id: str, config_id: str) -> str:
    L = [f"# {r['label']}", "", f"Experiment `{experiment_id}`, final configuration `{config_id}`. Events = those selected by at least 2 of the 3 models in the out-of-fold "
         f"DEVELOPMENT_CV predictions ({r['n_events_in']} events). Costs: {r['cost_points_round_trip']} points round trip. "
         f"{r['n_cells']} grid cells, {r['n_stable']} stable.", "", f"**Decision: {r['decision']}**", ""]
    c = r["chosen"]
    if c:
        L += [f"* ATR base {c['atr_base']}, stop {c['stop_atr']} x ATR, target {c['target_atr']} x ATR (reward:risk {c['reward_risk']:.2f}), time limit {c['expiry']} bars.",
              f"* {c['n_trades']} trades"
              + (f" ({r['chosen_trades_per_week']:.2f}/week)" if r.get("chosen_trades_per_week") else "")
              + f", net expectancy {c['net_expectancy']:+.3f} points per trade ({c['net_expectancy_R']:+.3f} R), target hit {c['hit_target']:.0%}, stop {c['hit_stop']:.0%}.",
              f"* Worst of its 8 neighbours (stop/target x0.75 / x1.25): {c['min_neighbour_expectancy']:+.3f} points. Positive years {c['positive_years']}/{c['eligible_years']}.", ""]
    else:
        L += ["No cell passed every stability condition, so no bracket is proposed. There is no fallback to the best single cell.", ""]
    L += ["## All cells (canonical order)", "", "| ATR | stop | target | RR | limit | trades | net exp (pts) | worst neighbour | stable | why not |", "|---|---|---|---|---|---|---|---|---|---|"]
    for x in r["cells"]:
        L.append(f"| {x['atr_base']} | {x['stop_atr']} | {x['target_atr']} | {x['reward_risk']:.2f} | {x['expiry']} | {x['n_trades']} | {x['net_expectancy']:+.3f} | "
                 f"{x['min_neighbour_expectancy']:+.3f} | {'yes' if x['stable'] else 'no'} | {'; '.join(x['reasons'])} |")
    L += ["", *[f"* {n}" for n in r["notes"]], ""]
    return "\n".join(L)


def run_for_experiment(ws, experiment_id: str, data_path, timestamp_col: str = "timestamp", *, frozen: Frozen | None = None) -> dict:
    """Run the study for the ONE final configuration of an experiment. DEVELOPMENT rows only; writes results/MONETISATION_STUDY.{json,md}; no registry write."""
    import json
    from engine import trial_registry as reg
    from engine.common import EngineError, load_frozen
    from engine.event_contract import load_spec as load_event_spec
    from engine.experiment_lifecycle import experiment_dir
    from engine.partitions import load_bars_before, parse_partitions
    frozen = frozen or load_frozen()
    exp = reg.experiment_row(ws, experiment_id)
    if exp["status"] not in ALLOWED_STATUSES:
        raise EngineError(f"the monetisation study runs only after the final configuration passed CPCV (status is {exp['status']}); "
                          "it can never rescue a rejected lineage")
    fc = reg.final_config_of(ws, experiment_id)
    if fc is None:
        raise EngineError(f"{experiment_id} has no FINAL_CONFIG_FROZEN row")
    _, target, state = fc["selected_config_id"].split("|")
    d = experiment_dir(ws, experiment_id)
    spec = load_event_spec(d / "EVENT_SPEC.yaml")
    parts = parse_partitions(spec["partitions"])
    values = spec["direction_definition"]["values"]
    if len(values) != 1:
        raise EngineError("one direction per experiment")
    action = int(values[0]) * (1 if state == "UPPER_HALF" else -1)
    votes, parent = {}, None
    for m in ("RIDGE", "SPLINE", "XGB"):
        cv = pd.read_csv(d / "results" / f"cv_{target}_{m}.csv")
        parent = cv if parent is None else parent
        for t in cv.loc[cv["state"] == state, "event_time"]:
            votes[t] = votes.get(t, 0) + 1
    chosen_times = sorted(t for t, v in votes.items() if v >= 2)
    events = pd.DataFrame({"event_time": pd.to_datetime(chosen_times, utc=True), "direction": action})
    weeks = pd.DatetimeIndex(pd.to_datetime(parent["event_time"], utc=True)).tz_convert(frozen.tz)
    n_weeks = float(len({(t.isocalendar().year, t.isocalendar().week) for t in weeks}))
    bars = load_bars_before(data_path, parts.development_end, timestamp_col)
    result = run_study(bars, events, frozen, n_weeks=n_weeks)
    result.update({"experiment_id": experiment_id, "final_config_id": fc["selected_config_id"], "data_used": "DEVELOPMENT only",
                   "selection_holdout_accessed": False, "final_lockbox_accessed": False})
    (d / "results" / "MONETISATION_STUDY.json").write_text(json.dumps(result, indent=2, sort_keys=True, default=str))
    (d / "results" / "MONETISATION_STUDY.md").write_text(_report_md(result, experiment_id, fc["selected_config_id"]))
    return result
