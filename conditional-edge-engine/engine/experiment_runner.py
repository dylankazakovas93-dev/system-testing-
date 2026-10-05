"""IS (development) stage of one frozen experiment.

EVENT -> FROZEN MARKET STATE -> FROZEN FUTURE PATH TARGETS -> DEVELOPMENT_CV (5 purged folds) -> 24 SELECTION TRIALS
      -> (sensitivity veto) -> IS_REPORT -> STOP at AWAITING_HUMAN_FINAL_CONFIG_SELECTION (or IS_REJECTED / IS_PROVISIONAL_CANDIDATE).

The runner receives full bars only to immediately cut them to the DEVELOPMENT partition (``development_view``); SELECTION HOLDOUT and
lockbox rows never reach event, feature, target, model, CV, statistics, plot, report or diagnostic code. It contains no
SELECTION HOLDOUT code path: the selection holdout lives in selection_holdout_stage.py behind human approval files.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from engine import trial_registry as reg
from engine.common import (EngineError, Frozen, load_frozen, model_names, now_utc_iso, primary_target_names, utc_ns,
                           validate_bars)
from engine.event_contract import check_event_causality, generate_events, load_event_module, load_spec
from engine.experiment_lifecycle import experiment_dir, verify_manifest
from engine.feature_engine import assert_feature_quality, compute_features, feature_names, model_eligibility
from engine.model_engine import make_model_factory
from engine.partitions import development_view, parse_partitions
from engine.score_calibration import LOWER, UPPER, WFConfig
from engine.statistics import decile_diagnostics, evaluate_panel, week_key, weeks_in_intervals
from engine.target_engine import compute_diagnostic_targets, compute_primary_targets, window_span_violations
from engine.walkforward import INT64_MAX, development_folds, run_walkforward

BASE_FREQ_FLAG = "BASE_FREQUENCY_TOO_LOW_FOR_FIXED_HALF_SELECTION"
FAMILY_OF = {}  # filled lazily from the frozen feature bank (feature name -> family id)


@dataclass
class PanelOutput:
    target: str
    model: str
    stats: dict                      # {state: stats dict}
    folds: list                      # DEVELOPMENT_CV fold records
    importances: dict                # mean |importance| per feature (diagnostic only)
    coefficients: list               # per-fold signed Ridge coefficients (diagnostic only)
    deciles: dict
    cv: pd.DataFrame                 # event_id, event_time, fold, year, score, threshold, state, y, truncated  (DEVELOPMENT_CV validation)
    cv_years: list = field(default_factory=list)


def bars_fingerprint(bars: pd.DataFrame) -> str:
    h = hashlib.sha256()
    h.update(utc_ns(bars.index).tobytes())
    h.update(np.ascontiguousarray(bars[["open", "high", "low", "close", "volume"]].to_numpy("float64")).tobytes())
    return h.hexdigest()


def base_frequency_flag(n_events: int, trading_weeks: int, frozen: Frozen) -> str:
    """Flag when the BASE event itself occurs < 2.0 times/week. The experiment still runs; the 50% state is never changed."""
    if trading_weeks <= 0:
        return BASE_FREQ_FLAG
    return BASE_FREQ_FLAG if n_events / trading_weeks < frozen.trial_policy["base_event_frequency_floor_per_week"] else ""


def feature_family_map(frozen: Frozen) -> dict[str, str]:
    if not FAMILY_OF:
        import importlib

        from engine.feature_engine import _dummy_ctx
        ctx = _dummy_ctx(frozen)
        ctx.cache["event_ns"] = np.array([ctx.index_ns[-1] + ctx.interval_ns], dtype=np.int64)
        pos = np.array([len(ctx.close) - 1])
        for fam in frozen.feature_bank["families"]:
            for name in importlib.import_module(fam["module"]).compute(ctx, pos, fam["params"]):
                FAMILY_OF[name] = fam["id"]
    return dict(FAMILY_OF)


def run_panels(events: pd.DataFrame, features: pd.DataFrame, targets: dict[str, pd.DataFrame], eligible: np.ndarray,
               calendar_index: pd.DatetimeIndex, frozen: Frozen, *, target_names: list[str] | None = None,
               models: list[str] | None = None, point_only: bool = False) -> dict[tuple[str, str], PanelOutput]:
    """DEVELOPMENT_CV (K=5 purged walk-forward) + statistics for every requested (target, model). No selection/tuning."""
    pol = frozen.trial_policy
    cv = pol["development_cv"]
    cfg = WFConfig.from_policy(pol)
    names = feature_names(frozen)
    target_names = target_names or primary_target_names(frozen)
    models = models or model_names(frozen)
    ev = events.assign(_eligible=np.asarray(eligible, dtype=bool))
    ev = ev[ev["_eligible"]].sort_values(["event_time", "event_id"], kind="stable").reset_index(drop=True)
    folds = development_folds(pd.DatetimeIndex(ev["event_time"]), cv["K"], frozen.tz)     # timestamps only
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
        eff_col = "effective_target_end" if "effective_target_end" in tdf.columns else "target_end"
        eff_end = pd.DatetimeIndex(tdf.loc[ids, eff_col])
        etime = pd.DatetimeIndex(sub["event_time"])
        if not np.isfinite(y).all():
            raise EngineError(f"non-finite values in target {tname}")
        for mname in models:
            res = run_walkforward(make_model_factory(mname, frozen), X, y, etime, eff_end, cfg, folds)
            v = res.validation
            pos = v["pos"].to_numpy(dtype=int)
            ok_folds = sorted(int(f) for f in v["fold"].unique()) if len(v) else []
            intervals = [(f.val_start_ns, f.val_end_ns) for f in folds if f.fold in ok_folds]
            wk = weeks_in_intervals(calendar_index, intervals, frozen.tz) if intervals else {"total": 0, "by_year": {}, "by_interval": []}
            weeks_by_fold = {f: n for f, n in zip(ok_folds, wk["by_interval"])}
            wkeys = week_key(etime[pos], frozen.tz) if len(pos) else np.array([])
            stats = evaluate_panel(
                y[pos], v["state"].to_numpy(), v["year"].to_numpy(), wkeys, utc_ns(etime[pos]) if len(pos) else np.array([]),
                wk["total"], bootstrap_reps=boot, permutation_reps=perm, seed=pol["seed"], ci_level=pol["ci_level"],
                min_events_year=frozen.acceptance["year_consistency"]["min_selected_events_for_eligible_year"],
                fold=v["fold"].to_numpy() if len(v) else None, weeks_by_year=wk["by_year"], weeks_by_fold=weeks_by_fold,
                concentration_share=frozen.acceptance["year_consistency"]["concentration_warning_share"],
                n_batches=frozen.acceptance["concentration"]["n_batches"])
            deciles = decile_diagnostics(v["score"].to_numpy(), y[pos], v["year"].to_numpy(), wk["total"]) if len(pos) else {}
            imp = pd.DataFrame(res.importances).mean().sort_values(ascending=False).to_dict() if res.importances else {}
            panel = pd.DataFrame({"event_id": np.asarray(ids)[pos], "event_time": etime[pos], "fold": v["fold"].to_numpy(),
                                  "year": v["year"].to_numpy(), "score": v["score"].to_numpy(),
                                  "threshold": v["threshold"].to_numpy(), "state": v["state"].to_numpy(), "y": y[pos],
                                  "truncated": (tdf.loc[ids, "truncated"].to_numpy(dtype=bool)[pos] if "truncated" in tdf.columns
                                                else np.zeros(len(pos), dtype=bool))})
            out[(tname, mname)] = PanelOutput(tname, mname, stats, res.folds, imp, res.coefficients, deciles, panel,
                                              sorted(int(x) for x in v["year"].unique()) if len(v) else [])
    return out


def assemble_trial_results(panels: dict, experiment_id: str, frozen: Frozen) -> dict[str, dict]:
    """Map panel statistics onto the 24 pre-registered trial ids (frozen order)."""
    results = {}
    for i, spec in enumerate(reg.trial_specs(frozen)):
        p = panels[(spec["target"], spec["model"])]
        results[reg.trial_id(experiment_id, i)] = p.stats[spec["state"]]
    return results


def period_strings(panels: dict, events: pd.DataFrame) -> tuple[str, str]:
    folds = sorted({f["fold"] for p in panels.values() for f in p.folds if f["status"] == "OK"})
    ev = pd.DatetimeIndex(events["event_time"])
    if not folds:
        return "n/a", "n/a"
    starts = [pd.Timestamp(f["val_start"]) for p in panels.values() for f in p.folds if f["status"] == "OK"]
    first_val = min(starts)
    return (f"{ev.min():%Y-%m-%d}..{first_val:%Y-%m-%d}(exclusive; first fold's training = history before validation)",
            f"{first_val:%Y-%m-%d}..{ev.max():%Y-%m-%d} DEVELOPMENT_CV folds {folds}")


def derive_observations(panels: dict, trials: pd.DataFrame, frozen: Frozen) -> list[tuple[str, str, str, float | str]]:
    """Descriptive diagnostics only (fixed recipes, no searching). They can never promote anything."""
    obs = []
    for (t, m), p in panels.items():
        d = p.deciles.get("deciles") if p.deciles else None
        if d:
            obs.append(("score_decile_shape",
                        f"{t}/{m}: mean target top decile {d[-1]['mean_target']:+.5f} vs bottom decile "
                        f"{d[0]['mean_target']:+.5f} (pooled DEVELOPMENT_CV deciles; not selection trials)",
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
                        f"{tname}: mean uplift UPPER_HALF {up:+.5f} vs LOWER_HALF {lo:+.5f} across models",
                        "upper_minus_lower_uplift", up - lo))
    for _, r in trials.iterrows():
        if r["decision"] == "REJECTED_LOW_FREQUENCY" and r["standardized_uplift"] >= frozen.acceptance["min_standardized_uplift"]:
            obs.append(("low_frequency_state",
                        f"{r['trial_id']} ({r['target']}/{r['model']}/{r['state']}): standardized uplift "
                        f"{r['standardized_uplift']:.3f} but selected frequency {r['selected_frequency']:.3f}/week",
                        "standardized_uplift", r["standardized_uplift"]))
        if r["decision"] == "DIAGNOSTIC_CONDITIONAL_IMPROVEMENT":
            obs.append(("conditional_improvement",
                        f"{r['trial_id']} ({r['target']}/{r['model']}/{r['state']}): uplift {r['standardized_uplift']:.3f} but "
                        f"absolute selected effect {r['selected_effect']:+.5f} <= 0 (less bad than the parent; NOT a candidate)",
                        "selected_effect", r["selected_effect"]))
        if bool(r.get("year_concentration_warning")):
            obs.append(("year_concentration",
                        f"{r['trial_id']}: YEAR_CONCENTRATION_WARNING (largest year share {r['year_concentration_share']:.2f} of total absolute uplift)",
                        "year_concentration_share", r["year_concentration_share"]))
    return obs


def feature_diagnostics(panels: dict, features: pd.DataFrame, eligible: np.ndarray, frozen: Frozen) -> dict:
    """DIAGNOSTIC ONLY — NOT A SELECTION TRIAL: family importance, Ridge coefficient stability, feature distribution shifts,
    decile/score monotonicity. None of this can create a candidate."""
    fam = feature_family_map(frozen)
    fam["day_of_week"] = "session"
    out = {"label": "DIAGNOSTIC ONLY — NOT A SELECTION TRIAL", "family_importance": {}, "ridge_coefficient_stability": {},
           "score_monotonicity": {}, "distribution_shift": []}
    for (t, m), p in panels.items():
        if p.importances:
            tot = sum(p.importances.values()) or 1.0
            agg: dict[str, float] = {}
            for k, v in p.importances.items():
                agg[fam.get(k, "other")] = agg.get(fam.get(k, "other"), 0.0) + v / tot
            out["family_importance"][f"{t}|{m}"] = dict(sorted(agg.items(), key=lambda kv: -kv[1]))
        if m == "RIDGE" and p.coefficients:
            df = pd.DataFrame(p.coefficients)
            same = (np.sign(df).eq(np.sign(df.iloc[0]))).mean()
            top = df.abs().mean().sort_values(ascending=False).head(8).index
            out["ridge_coefficient_stability"][t] = {k: {"mean_coef": float(df[k].mean()),
                                                         "sign_agreement_across_folds": float(same[k])} for k in top}
        d = (p.deciles or {}).get("deciles")
        if d:
            from scipy.stats import spearmanr
            rho = spearmanr([r["decile"] for r in d], [r["mean_target"] for r in d])[0]
            out["score_monotonicity"][f"{t}|{m}"] = float(rho) if np.isfinite(rho) else None
    names = feature_names(frozen)
    f = features.loc[np.asarray(eligible, dtype=bool)]
    if len(f):
        yrs = pd.DatetimeIndex(f["feature_asof_time"]).year
        shifts = []
        for n in names:
            if n == "day_of_week":
                continue
            g = f[n].groupby(yrs)
            mu, sd = g.mean(), f[n].std()
            if sd and np.isfinite(sd) and len(mu) > 1:
                shifts.append({"feature": n, "max_abs_year_mean_shift_in_sd": float((mu - f[n].mean()).abs().max() / sd)})
        out["distribution_shift"] = sorted(shifts, key=lambda r: -r["max_abs_year_mean_shift_in_sd"])[:8]
    return out


def _clean(obj):
    """NaN/inf -> None recursively (strict JSON); numpy -> python."""
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        return None if not np.isfinite(obj) else float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp,)):
        return str(obj)
    return obj


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
    """Run the IS stage end to end and STOP. ``bars`` may contain later partitions: they are removed first."""
    frozen = load_frozen()
    log = (lambda *a: print(*a, flush=True)) if verbose else (lambda *a: None)
    exp = reg.experiment_row(ws, experiment_id)
    if reg.is_revealed(exp):
        raise EngineError(f"{experiment_id} IS results are already revealed (status {exp['status']}); a changed event is a NEW experiment")
    if exp["status"] != "FROZEN":
        raise EngineError(f"{experiment_id} is {exp['status']}; freeze it first")
    verified = verify_manifest(ws, experiment_id)              # raises MutationDetected
    d = experiment_dir(ws, experiment_id)
    spec = load_spec(d / "EVENT_SPEC.yaml")
    module = load_event_module(d / "event.py")
    parts = parse_partitions(spec["partitions"])
    validate_bars(bars)
    n_input = len(bars)
    bars_dev = development_view(bars, parts)                   # HARD PARTITION GUARD: SELECTION HOLDOUT + lockbox rows removed here
    del bars
    if len(bars_dev) == 0:
        raise EngineError("no development bars before development_end")
    log(f"[{experiment_id}] DEVELOPMENT bars only: {len(bars_dev):,} (rows removed before research code: {n_input - len(bars_dev):,})")
    causality = check_event_causality(module, bars_dev, spec, frozen)
    log(f"[{experiment_id}] event causality pre-check passed at {causality['cutoffs']} cutoffs")
    events, features, eligible, targets, sp = build_event_tables(module, spec, bars_dev, frozen)
    dev_weeks = weeks_in_intervals(bars_dev.index, [(-INT64_MAX, INT64_MAX)], frozen.tz)["total"]
    base_freq = len(events) / dev_weeks if dev_weeks else float("nan")
    base = {"n_events": int(len(events)), "n_model_eligible": int(eligible.sum()), "trading_weeks": int(dev_weeks),
            "raw_event_frequency_per_week": base_freq, "direction": int(events["direction"].iloc[0]) if len(events) else None,
            "flag": base_frequency_flag(len(events), dev_weeks, frozen), "unused_parameters": sp.unused(),
            "target_timestamp_ineligible": int(events.attrs.get("target_timestamp_ineligible", 0)),
            "development_bars": int(len(bars_dev)), "first_bar": str(bars_dev.index[0]), "last_bar": str(bars_dev.index[-1]),
            "rows_removed_before_research": int(n_input - len(bars_dev)),
            "forward_windows_crossing_gaps": window_span_violations(bars_dev, events, 60, frozen.interval) if len(events) else 0}
    log(f"[{experiment_id}] base events: {base['n_events']:,} ({base_freq:.2f}/week){' -> ' + base['flag'] if base['flag'] else ''}; "
        f"TARGET_TIMESTAMP_INELIGIBLE removed: {base['target_timestamp_ineligible']}")
    if not eligible.any():
        raise EngineError("no model-eligible events (need >= 480 completed bars before an event)")
    panels = run_panels(events, features, targets, eligible, bars_dev.index, frozen)
    bundle = finish_is(ws, experiment_id, panels, events, features, eligible, frozen, spec=spec, module=module, bars_dev=bars_dev,
                       base=base, causality=causality, verified=verified, data_label=data_label, parts=parts,
                       run_sensitivity_stage=run_sensitivity_stage, log=log)
    log(f"[{experiment_id}] STOP: status {reg.experiment_row(ws, experiment_id)['status']} - SELECTION HOLDOUT NOT ACCESSED; SELECTION HOLDOUT needs a "
        f"manual human approval file (approvals/{experiment_id}_SELECTION_HOLDOUT_APPROVAL.yaml)")
    return bundle


def finish_is(ws: reg.Workspace, experiment_id: str, panels: dict, events: pd.DataFrame, features: pd.DataFrame,
              eligible: np.ndarray, frozen: Frozen, *, spec: dict, module=None, bars_dev: pd.DataFrame | None = None,
              base: dict, causality: dict, verified: dict, data_label: str, parts, run_sensitivity_stage: bool = True,
              log=lambda *a: None, data_hash: str | None = None) -> dict:
    """Reveal the 24 trials, log diagnostics/ladder observations, run the sensitivity veto, persist results and write the
    IS report. (``module``/``bars_dev`` may be None only for table-level synthetic tests: no ladder, no sensitivity run.)"""
    from engine import is_report as is_report_mod
    from engine import ladder as ladder_mod
    from engine import sensitivity as sens_mod
    exp = reg.experiment_row(ws, experiment_id)
    results = assemble_trial_results(panels, experiment_id, frozen)
    train_p, val_p = period_strings(panels, events)
    data_hash = data_hash or (bars_fingerprint(bars_dev) if bars_dev is not None else "table-level")
    reg.reveal_experiment(ws, experiment_id, results, train_period=train_p, validation_period=val_p,
                          is_data_hash=data_hash, frozen=frozen)
    n_rev = int(reg.campaign_summary(ws, exp["campaign_id"], frozen)["selection_trials_revealed"])
    log(f"[{experiment_id}] EXPERIMENT SELECTION TRIALS: 24 / 24 ; CAMPAIGN REVEALED SELECTION TRIALS: "
        f"{n_rev} / {frozen.trial_policy['max_selection_trials_per_campaign']}")
    trials_full = reg.experiment_trials(ws, experiment_id)
    ladder = ladder_mod.evaluate_ladder(module, spec, bars_dev, frozen) if (module is not None and bars_dev is not None) else {}
    for cat, desc, mname, val in derive_observations(panels, trials_full, frozen):
        reg.add_observation(ws, experiment_id, cat, desc, mname, val)
    for st in ladder.get("steps", []):
        for t, rec in st["targets"].items():
            fl = ("; ".join(rec["flags"]).replace("_", " ")) or "ok"
            reg.add_observation(ws, experiment_id, "filter_ladder",
                                f"ladder step {st['step']} / {t}: {st['frequency_per_week']:.2f}/week, effect {rec['effect']:+.6f}, "
                                f"uplift vs parent {rec['uplift_vs_parent']:+.6f}, vs previous {rec['uplift_vs_previous']:+.6f}, "
                                f"positive step-over-step uplift years {rec['positive_uplift_years_vs_previous']}/{rec['eligible_years']}; {fl}",
                                "effect", rec["effect"])
    sensitivity = {"status": "NOT_APPLICABLE", "groups": {}}
    cand = trials_full[trials_full["decision"].isin(["IS_PROVISIONAL_CANDIDATE", "IS_SHORTLIST_ELIGIBLE"])]
    if cand.empty:
        sensitivity["status"] = "NO_DEVELOPMENT_CANDIDATE"
    elif run_sensitivity_stage and module is not None and bars_dev is not None:
        sensitivity = sens_mod.run_sensitivity(module, spec, bars_dev, frozen, cand)
        reg.set_sensitivity(ws, experiment_id, {k: v["verdict"] for k, v in sensitivity["groups"].items()}, frozen)
    else:
        sensitivity["status"] = "NOT_RUN"
    d = experiment_dir(ws, experiment_id)
    rdir = d / "results"
    rdir.mkdir(exist_ok=True)
    for (t, m), p in panels.items():
        p.cv.to_csv(rdir / f"cv_{t}_{m}.csv", index=False)
    path_info = _path_diagnostics_stage(ws, experiment_id, panels, events, features, eligible, frozen, spec, module, bars_dev, rdir)
    bundle = {"experiment_id": experiment_id, "data": data_label, "is_data_fingerprint": data_hash,
              "partitions": parts.as_dict(), "manifest_check": verified, "event_causality": causality,
              "base_event": base, "train_period": train_p, "validation_period": val_p, "sensitivity": sensitivity,
              "development_cv_folds": {f"{t}|{m}": p.folds for (t, m), p in panels.items()},
              "panels": {f"{t}|{m}": {"stats": p.stats, "importances": p.importances, "deciles": p.deciles}
                         for (t, m), p in panels.items()},
              "ladder": ladder, "path_diagnostics": path_info, "feature_diagnostics": feature_diagnostics(panels, features, eligible, frozen),
              "diagnostic_targets": _diagnostic_summary(bars_dev, events, features, eligible, frozen) if bars_dev is not None else {}}
    (rdir / "results.json").write_text(json.dumps(_clean(bundle), indent=2, sort_keys=True))
    paths = is_report_mod.write_is_report(ws, experiment_id)
    bundle.update(report_path=paths["md"], is_report_json=paths["json"], trials=reg.experiment_trials(ws, experiment_id))
    return bundle


def _path_diagnostics_stage(ws, experiment_id, panels, events, features, eligible, frozen, spec, module, bars_dev, rdir) -> dict:
    """DIAGNOSTIC ONLY forward-path layer. Reads development rows and panels; writes results/PATH_DIAGNOSTICS.json; logs fixed-recipe
    observations. It runs AFTER the 24 trials are revealed and cannot alter any trial, decision, ranking or status."""
    from engine import path_diagnostics as pdx
    if bars_dev is None or not eligible.any():
        return {"status": "NOT_COMPUTED_NO_BARS", "label": frozen.path_diagnostics["label"]}
    ev = events.assign(_el=np.asarray(eligible, dtype=bool))
    ev = ev[ev["_el"]].sort_values(["event_time", "event_id"], kind="stable").reset_index(drop=True)
    folds = development_folds(pd.DatetimeIndex(ev["event_time"]), frozen.trial_policy["development_cv"]["K"], frozen.tz)
    weeks_all = weeks_in_intervals(bars_dev.index, [(-INT64_MAX, INT64_MAX)], frozen.tz)
    weeks_cv = {}
    for (t, m), p in panels.items():
        ok = sorted(int(f) for f in p.cv["fold"].unique()) if len(p.cv) else []
        iv = [(f.val_start_ns, f.val_end_ns) for f in folds if f.fold in ok]
        weeks_cv[f"{t}|{m}"] = weeks_in_intervals(bars_dev.index, iv, frozen.tz) if iv else {"total": 0, "by_year": {}}
    ladder_steps = {}
    if module is not None and spec.get("filter_ladder"):
        from engine.event_contract import ladder_event_sets
        ladder_steps = pdx.ladder_path_diagnostics(ladder_event_sets(module, bars_dev, spec, frozen), list(spec["filter_ladder"]), bars_dev, frozen)
    rep = pdx.build_path_diagnostics(bars_dev=bars_dev, events=events, features=features, eligible=eligible, panels=panels, folds=folds,
                                     weeks_all=weeks_all, weeks_cv=weeks_cv, frozen=frozen, ladder_steps=ladder_steps)
    rep = _clean(rep)
    pdx.assert_no_forbidden_phrases(rep)
    txt = json.dumps(rep, separators=(",", ":"), sort_keys=True)
    (rdir / "PATH_DIAGNOSTICS.json").write_text(txt)
    allc = rep["contexts"]["ALL"]
    cells = allc["bracket_surface"]
    npos = sum(1 for c in cells if c.get("mean_gross_points") is not None and c["mean_gross_points"] > 0)
    h60 = allc["continuation"]["60"]["continuation"]
    dom60 = allc["dominance"]["60"]
    banner = f"{frozen.path_diagnostics['label']}; {frozen.path_diagnostics['bracket_surface']['cost_banner']}"
    for cat, desc, name, val in (
            ("path_continuation", f"raw base event: continuation at 60 bars {h60['n']}/{h60['denominator']} ({banner})", "continuation_rate_60", h60["rate"] if h60["rate"] is not None else ""),
            ("path_dominance", f"raw base event: median path dominance (MFE+MAE) at 60 bars {dom60['median']} points ({banner})", "median_dominance_60", dom60["median"] if dom60["median"] is not None else ""),
            ("bracket_surface_description", f"{npos} of {len(cells)} fixed bracket cells have positive conservative mean gross points for the raw base event "
                                            f"(descriptive count only; {frozen.path_diagnostics['bracket_surface']['selection_banner']}; {frozen.path_diagnostics['bracket_surface']['cost_banner']})",
             "cells_positive_mean_gross", npos)):
        reg.add_observation(ws, experiment_id, cat, desc, name, val)
    return {"status": "COMPUTED", "file": "PATH_DIAGNOSTICS.json", "sha256": hashlib.sha256(txt.encode()).hexdigest(),
            "n_bracket_cells": rep["n_bracket_cells"], "n_contexts": rep["n_contexts"], "promotion_eligible": False,
            "selection_trials_affected": 0, "label": rep["label"]}


def _diagnostic_summary(bars, events, features, eligible, frozen) -> dict:
    """Mean of report-only diagnostic targets over model-eligible parent events (never used for selection)."""
    if not eligible.any():
        return {}
    ev = events[eligible].reset_index(drop=True)
    from engine.path_engine import sigma_ref
    sigma = sigma_ref(features.loc[eligible, "RV_60"].to_numpy())          # one-bar RMS scale (same unit as the path diagnostics)
    d = compute_diagnostic_targets(bars, ev, frozen, sigma)
    return {c: float(np.nanmean(d[c])) for c in d.columns if c != "event_id" and d[c].notna().any()}
