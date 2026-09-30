"""Orchestration of one frozen experiment.

EVENT -> FROZEN MARKET STATE -> FROZEN FUTURE PATH TARGETS -> STRICT OOS MODELS
      -> 24 CONTROLLED SELECTION TRIALS -> ROBUSTNESS -> AUDITABLE REPORT

``run_panels`` / ``assemble_trial_results`` operate on tables (used directly by the synthetic tests);
``run_experiment`` adds manifest verification, lockbox truncation, event generation and registry reveal.
There is deliberately no lockbox-evaluation path anywhere in this module.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from engine import trial_registry as reg
from engine.common import (EngineError, Frozen, load_frozen, model_names, now_utc_iso, primary_target_names,
                           utc_ns, validate_bars)
from engine.event_contract import (check_event_causality, generate_events, load_event_module, load_spec)
from engine.experiment_lifecycle import experiment_dir, verify_manifest
from engine.feature_engine import (assert_feature_quality, compute_features, feature_names, model_eligibility)
from engine.model_engine import make_model_factory
from engine.score_calibration import LOWER, UPPER, WFConfig
from engine.statistics import decile_diagnostics, eligible_weeks, evaluate_panel, week_key
from engine.target_engine import (compute_diagnostic_targets, compute_primary_targets, window_span_violations)
from engine.walkforward import run_walkforward


@dataclass
class PanelOutput:
    target: str
    model: str
    stats: dict                      # {state: stats dict}
    folds: list
    importances: dict                # mean |importance| per feature (diagnostic only)
    deciles: dict
    oos: pd.DataFrame                # event_id, event_time, year, score, threshold, state, y
    oos_years: list = field(default_factory=list)


def bars_fingerprint(bars: pd.DataFrame) -> str:
    h = hashlib.sha256()
    h.update(utc_ns(bars.index).tobytes())
    h.update(np.ascontiguousarray(bars[["open", "high", "low", "close", "volume"]].to_numpy("float64")).tobytes())
    return h.hexdigest()


def run_panels(events: pd.DataFrame, features: pd.DataFrame, targets: dict[str, pd.DataFrame],
               eligible: np.ndarray, calendar_index: pd.DatetimeIndex, frozen: Frozen, *,
               target_names: list[str] | None = None, models: list[str] | None = None,
               point_only: bool = False) -> dict[tuple[str, str], PanelOutput]:
    """Walk-forward + statistics for every requested (target, model). Nothing here selects or tunes."""
    pol = frozen.trial_policy
    cfg = WFConfig.from_policy(pol)
    names = feature_names(frozen)
    target_names = target_names or primary_target_names(frozen)
    models = models or model_names(frozen)
    ev = events.assign(_eligible=np.asarray(eligible, dtype=bool))
    ev = ev[ev["_eligible"]].sort_values(["event_time", "event_id"], kind="stable").reset_index(drop=True)
    feat = features.set_index("event_id")
    out: dict[tuple[str, str], PanelOutput] = {}
    boot = 1 if point_only else pol["bootstrap_repetitions"]
    perm = 1 if point_only else pol["permutation_repetitions"]
    for tname in target_names:
        tdf = targets[tname].set_index("event_id")
        ids = [i for i in ev["event_id"] if i in tdf.index]                   # resolved targets only
        sub = ev.set_index("event_id").loc[ids]
        X = feat.loc[ids, names].reset_index(drop=True)
        y = tdf.loc[ids, "value"].to_numpy("float64")
        t_end = pd.DatetimeIndex(tdf.loc[ids, "target_end"])
        etime = pd.DatetimeIndex(sub["event_time"])
        if not np.isfinite(y).all():
            raise EngineError(f"non-finite values in target {tname}")
        for mname in models:
            res = run_walkforward(make_model_factory(mname, frozen), X, y, etime, t_end, cfg)
            oos = res.oos
            pos = oos["pos"].to_numpy(dtype=int)
            years = sorted(int(v) for v in oos["year"].unique()) if len(oos) else []
            n_weeks = eligible_weeks(calendar_index, years, frozen.tz)
            wk = week_key(etime[pos], frozen.tz) if len(pos) else np.array([])
            stats = evaluate_panel(
                y[pos], oos["state"].to_numpy(), oos["year"].to_numpy(), wk, utc_ns(etime[pos]) if len(pos) else np.array([]),
                n_weeks, bootstrap_reps=boot, permutation_reps=perm, seed=pol["seed"], ci_level=pol["ci_level"],
                min_events_year=frozen.acceptance["stability"]["min_selected_events_for_eligible_year"])
            deciles = decile_diagnostics(oos["score"].to_numpy(), y[pos], oos["year"].to_numpy(), n_weeks) if len(pos) else {}
            imp = {}
            if res.importances:
                imp = pd.DataFrame(res.importances).mean().sort_values(ascending=False).to_dict()
            panel = pd.DataFrame({"event_id": np.asarray(ids)[pos], "event_time": etime[pos], "year": oos["year"].to_numpy(),
                                  "score": oos["score"].to_numpy(), "threshold": oos["threshold"].to_numpy(),
                                  "state": oos["state"].to_numpy(), "y": y[pos]})
            out[(tname, mname)] = PanelOutput(tname, mname, stats, res.folds, imp, deciles, panel, years)
    return out


def assemble_trial_results(panels: dict, experiment_id: str, frozen: Frozen) -> dict[str, dict]:
    """Map panel statistics onto the 24 pre-registered trial ids (frozen order)."""
    results = {}
    for i, spec in enumerate(reg.trial_specs(frozen)):
        p = panels[(spec["target"], spec["model"])]
        results[reg.trial_id(experiment_id, i)] = p.stats[spec["state"]]
    return results


def period_strings(panels: dict, events: pd.DataFrame) -> tuple[str, str]:
    years = sorted({y for p in panels.values() for y in p.oos_years})
    if not years:
        return "n/a", "n/a"
    first_event = pd.DatetimeIndex(events["event_time"]).min()
    return (f"{first_event:%Y-%m-%d}..{years[0] - 1}-12-31", f"{years[0]}-01-01..{years[-1]}-12-31")


def derive_observations(panels: dict, trials: pd.DataFrame, frozen: Frozen) -> list[tuple[str, str, str, float | str]]:
    """Descriptive diagnostics only (fixed recipes, no searching). They can never promote anything."""
    obs = []
    for (t, m), p in panels.items():
        d = p.deciles.get("deciles") if p.deciles else None
        if d:
            obs.append(("score_decile_shape",
                        f"{t}/{m}: mean target top decile {d[-1]['mean_target']:+.5f} vs bottom decile "
                        f"{d[0]['mean_target']:+.5f} (pooled-OOS deciles; not selection trials)",
                        "decile10_minus_decile1", d[-1]["mean_target"] - d[0]["mean_target"]))
        if p.importances:
            top = list(p.importances.items())[:3]
            obs.append(("feature_importance",
                        f"{t}/{m}: top features {', '.join(f'{k} ({v:.4g})' for k, v in top)} (diagnostic importance; "
                        f"models still consume the whole bank)", "top_feature_importance", top[0][1]))
    for tname in primary_target_names(frozen):
        rows = trials[trials["target"] == tname]
        up = rows[rows["state"] == UPPER]["uplift"].mean()
        lo = rows[rows["state"] == LOWER]["uplift"].mean()
        if np.isfinite(up) and np.isfinite(lo):
            obs.append(("long_short_asymmetry",
                        f"{tname}: mean standardized-free uplift UPPER_HALF {up:+.5f} vs LOWER_HALF {lo:+.5f} across models",
                        "upper_minus_lower_uplift", up - lo))
    for _, r in trials.iterrows():
        if r["decision"] == "REJECTED_LOW_FREQUENCY" and r["standardized_uplift"] >= frozen.acceptance["min_standardized_uplift"]:
            obs.append(("low_frequency_state",
                        f"{r['trial_id']} ({r['target']}/{r['model']}/{r['state']}): standardized uplift "
                        f"{r['standardized_uplift']:.3f} but selected frequency {r['selected_frequency']:.3f}/week",
                        "standardized_uplift", r["standardized_uplift"]))
    return obs


def _save_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=lambda o: None if (isinstance(o, float) and np.isnan(o)) else str(o)))


def _clean(obj):
    """NaN -> None recursively (strict JSON)."""
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        return None if not np.isfinite(obj) else float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    return obj


def dev_bars(bars: pd.DataFrame, lockbox_start: str) -> tuple[pd.DataFrame, int]:
    """Development bars = bars opening strictly before the lockbox boundary (UTC midnight). Lockbox bars are dropped."""
    lb = pd.Timestamp(lockbox_start, tz="UTC")
    dev = bars[bars.index.tz_convert("UTC") < lb]
    return dev, int(len(bars) - len(dev))


BASE_FREQ_FLAG = "BASE_FREQUENCY_TOO_LOW_FOR_FIXED_HALF_SELECTION"


def base_frequency_flag(n_events: int, trading_weeks: int, frozen: Frozen) -> str:
    """Flag when the BASE event itself occurs < 2.0 times/week. The experiment still runs; the 50% state is never changed."""
    if trading_weeks <= 0:
        return BASE_FREQ_FLAG
    return BASE_FREQ_FLAG if n_events / trading_weeks < frozen.trial_policy["base_event_frequency_floor_per_week"] else ""


def build_event_tables(module, spec: dict, bars: pd.DataFrame, frozen: Frozen, params: dict | None = None):
    """events -> features -> eligibility -> targets on the given (development) bars."""
    events, sp = generate_events(module, bars, spec, frozen, params)
    features = compute_features(bars, events, frozen)
    eligible = model_eligibility(features, frozen)
    assert_feature_quality(features, eligible, frozen)
    targets = compute_primary_targets(bars, events, frozen) if len(events) else {}
    return events, features, eligible, targets, sp


def run_experiment(ws: reg.Workspace, experiment_id: str, bars: pd.DataFrame, *, data_label: str = "in-memory",
                   run_sensitivity_stage: bool = True, verbose: bool = True) -> dict:
    """Run the base experiment end to end and reveal its 24 trials. Returns a results dict."""
    from engine import report as report_mod
    from engine import sensitivity as sens_mod
    frozen = load_frozen()
    log = (lambda *a: print(*a, flush=True)) if verbose else (lambda *a: None)
    exp = reg.experiment_row(ws, experiment_id)
    if exp["status"] == "REVEALED":
        raise EngineError(f"{experiment_id} results are already revealed; a changed event is a NEW experiment")
    if exp["status"] != "FROZEN":
        raise EngineError(f"{experiment_id} is {exp['status']}; freeze it first")
    verified = verify_manifest(ws, experiment_id)              # raises MutationDetected
    d = experiment_dir(ws, experiment_id)
    spec = load_spec(d / "EVENT_SPEC.yaml")
    module = load_event_module(d / "event.py")
    camp = reg.campaign_row(ws, exp["campaign_id"])
    validate_bars(bars)
    bars_dev, n_lockbox = dev_bars(bars, camp["lockbox_start"])
    if len(bars_dev) == 0:
        raise EngineError("no development bars before the lockbox boundary")
    log(f"[{experiment_id}] development bars: {len(bars_dev):,} (lockbox-withheld bars: {n_lockbox:,})")
    causality = check_event_causality(module, bars_dev, spec, frozen)
    log(f"[{experiment_id}] event causality pre-check passed at {causality['cutoffs']} cutoffs")
    events, features, eligible, targets, sp = build_event_tables(module, spec, bars_dev, frozen)
    all_weeks = eligible_weeks(bars_dev.index, sorted(set(bars_dev.index.tz_convert("UTC").year)), frozen.tz)
    base_freq = len(events) / all_weeks if all_weeks else float("nan")
    base = {"n_events": int(len(events)), "n_model_eligible": int(eligible.sum()), "trading_weeks": int(all_weeks),
            "raw_event_frequency_per_week": base_freq, "long_events": int((events["direction"] == 1).sum()),
            "short_events": int((events["direction"] == -1).sum()),
            "flag": base_frequency_flag(len(events), all_weeks, frozen),
            "unused_parameters": sp.unused(), "lockbox_withheld_bars": n_lockbox,
            "forward_windows_crossing_gaps": {t: window_span_violations(bars_dev, events, h, frozen.interval)
                                              for t, h in (("60bar", 60),)} if len(events) else {}}
    log(f"[{experiment_id}] base events: {base['n_events']:,} ({base_freq:.2f}/week){' -> ' + base['flag'] if base['flag'] else ''}")
    if not eligible.any():
        raise EngineError("no model-eligible events (need >= 480 completed bars before an event)")
    panels = run_panels(events, features, targets, eligible, bars_dev.index, frozen)
    results = assemble_trial_results(panels, experiment_id, frozen)
    train_p, oos_p = period_strings(panels, events)
    trials = reg.reveal_experiment(ws, experiment_id, results, train_period=train_p, oos_period=oos_p, frozen=frozen)
    log(f"[{experiment_id}] revealed 24 trials; decisions: {trials['decision'].value_counts().to_dict()}")
    # diagnostic observations (separate registry, cannot promote)
    trials_full = reg.experiment_trials(ws, experiment_id)
    for cat, desc, mname, val in derive_observations(panels, trials_full, frozen):
        reg.add_observation(ws, experiment_id, cat, desc, mname, val)
    # robustness stage: only if a development candidate exists; never creates candidates
    sensitivity = {"status": "NOT_APPLICABLE", "groups": {}}
    pending = trials_full[trials_full["decision"] == "PROMOTABLE_PENDING_SENSITIVITY"]
    if pending.empty:
        sensitivity["status"] = "NO_DEVELOPMENT_CANDIDATE"
    elif run_sensitivity_stage:
        sensitivity = sens_mod.run_sensitivity(module, spec, bars_dev, frozen, pending)
        reg.set_sensitivity(ws, experiment_id, {k: v["verdict"] for k, v in sensitivity["groups"].items()}, frozen)
    final = reg.experiment_trials(ws, experiment_id)
    # persist
    rdir = d / "results"
    rdir.mkdir(exist_ok=True)
    for (t, m), p in panels.items():
        p.oos.to_csv(rdir / f"oos_{t}_{m}.csv", index=False)
    bundle = {"experiment_id": experiment_id, "revealed_at": now_utc_iso(), "data": data_label,
              "data_fingerprint": bars_fingerprint(bars_dev), "lockbox_start": camp["lockbox_start"],
              "manifest_check": verified, "event_causality": causality, "base_event": base,
              "train_period": train_p, "oos_period": oos_p, "sensitivity": sensitivity,
              "panels": {f"{t}|{m}": {"stats": p.stats, "folds": p.folds, "importances": p.importances,
                                      "deciles": p.deciles} for (t, m), p in panels.items()},
              "diagnostic_targets": _diagnostic_summary(bars_dev, events, features, eligible, frozen)}
    (rdir / "results.json").write_text(json.dumps(_clean(bundle), indent=2, sort_keys=True))
    text = report_mod.build_report(ws, experiment_id, bundle, final, reg.read_observations(ws), frozen)
    (rdir / "REPORT.md").write_text(text)
    bundle["report_path"] = str(rdir / "REPORT.md")
    bundle["trials"] = final
    return bundle


def _diagnostic_summary(bars, events, features, eligible, frozen) -> dict:
    """Mean of report-only diagnostic targets over model-eligible parent events (never used for selection)."""
    if not eligible.any():
        return {}
    ev = events[eligible].reset_index(drop=True)
    sigma = features.loc[eligible, "RV_60"].to_numpy()
    d = compute_diagnostic_targets(bars, ev, frozen, sigma)
    return {c: float(np.nanmean(d[c])) for c in d.columns if c != "event_id" and d[c].notna().any()}
