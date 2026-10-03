"""Forward-path and monetisation DIAGNOSTICS (frozen/v1/PATH_DIAGNOSTICS.yaml).  *** DIAGNOSTIC ONLY — NOT A SELECTION TRIAL ***

This module only READS events/panels and WRITES a report structure. It is never imported by the selection, acceptance, registry or
multiplicity code, adds no row to selection_trials.csv and cannot change any decision, ranking or status. Summaries use the exact
percentile convention of the YAML (linear interpolation) and only the declared percentiles. No bracket is ever selected or ranked:
the bracket surface is emitted in the canonical order (expiry, stop, target).
"""
from __future__ import annotations

import hashlib
import json
from itertools import product

import numpy as np
import pandas as pd

from engine.common import Frozen, utc_ns
from engine.path_engine import (AMBIG, EXPIRED, STOP, TARGET, PathArrays, barrier_outcome, bracket_pnl, compute_paths, mfe_mae_log,
                                rv_ref, sigma_ref)
from engine.target_engine import forward_start, session_close_utc

FORBIDDEN_PHRASES = ("BEST BRACKET", "OPTIMAL STOP", "OPTIMAL TARGET", "RECOMMENDED BRACKET")


# ---------------------------------------------------------------------------------------------------- summaries
def _f(x):
    return None if x is None or not np.isfinite(x) else float(x)


def pct(x: np.ndarray, q: float):
    x = np.asarray(x, dtype="float64")
    x = x[np.isfinite(x)]
    return _f(np.percentile(x, q, method="linear")) if len(x) else None


def summ_endpoint(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype="float64")
    x = x[np.isfinite(x)]
    return {"n": int(len(x)), "mean": _f(x.mean()) if len(x) else None, "median": pct(x, 50), "p25": pct(x, 25), "p75": pct(x, 75),
            "p5": pct(x, 5), "p95": pct(x, 95), "std": _f(x.std(ddof=1)) if len(x) > 1 else None}


def summ_exc(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype="float64")
    x = x[np.isfinite(x)]
    return {"n": int(len(x)), "mean": _f(x.mean()) if len(x) else None, "median": pct(x, 50), "p75": pct(x, 75), "p95": pct(x, 95)}


def summ_dom(x: np.ndarray) -> dict:
    x = np.asarray(x, dtype="float64")
    x = x[np.isfinite(x)]
    return {"n": int(len(x)), "mean": _f(x.mean()) if len(x) else None, "median": pct(x, 50), "p25": pct(x, 25), "p75": pct(x, 75),
            "fraction_gt_0": _f((x > 0).mean()) if len(x) else None, "fraction_lt_0": _f((x < 0).mean()) if len(x) else None,
            "n_gt_0": int((x > 0).sum()), "n_lt_0": int((x < 0).sum())}


def _rate(k: int, n: int):
    return {"n": int(k), "denominator": int(n), "rate": (k / n) if n else None}


# ---------------------------------------------------------------------------------------------------- context sections
def core_sections(T: PathArrays, m: np.ndarray, tick: float) -> dict:
    """Endpoint returns, continuation/reversal, MFE/MAE excursions, dominance and time-to-extrema for the events in ``m``."""
    out = {"endpoint": {}, "continuation": {}, "excursions": {}, "dominance": {}, "time_to_extrema": {}}
    sig_all = T.sigma_log
    for h in T.horizons:
        em = m & T.elig[h]
        n = int(em.sum())
        p0, d = T.p0[em], T.d[em]
        ch = T.close_h[h][em]
        raw_pts = ch - p0
        with np.errstate(divide="ignore", invalid="ignore"):
            raw_log = np.log(ch / p0)
        dir_log = d * raw_log
        out["endpoint"][h] = {"n": n, "n_path_ineligible": int(m.sum() - n), "raw_return_points": summ_endpoint(raw_pts),
                              "raw_log_return": summ_endpoint(raw_log), "directional_log_return": summ_endpoint(dir_log)}
        out["continuation"][h] = {"continuation": _rate(int((dir_log > 0).sum()), n), "reversal": _rate(int((dir_log < 0).sum()), n),
                                  "flat": _rate(int((dir_log == 0).sum()), n)}
        mfe, mae = T.mfe_pts[h][em], T.mae_pts[h][em]
        adv = -mae
        mfe_l, mae_l = mfe_mae_log(p0, d, mfe, mae)
        sg = sig_all[em]
        okS = np.isfinite(sg) & (sg > 0)
        out["excursions"][h] = {
            "MFE": {"points": summ_exc(mfe), "ticks": summ_exc(mfe / tick), "sigma": summ_exc((mfe_l / sg)[okS])},
            "ADVERSE_ABS_MAE": {"points": summ_exc(adv), "ticks": summ_exc(adv / tick), "sigma": summ_exc((-mae_l / sg)[okS])}}
        out["dominance"][h] = summ_dom(mfe + mae)
        tm, ta = T.t_mfe[h][em], T.t_mae[h][em]
        out["time_to_extrema"][h] = {
            "bars_to_MFE": summ_exc(tm.astype(float)), "bars_to_MAE": summ_exc(ta.astype(float)),
            "p_mfe_before_mae": _rate(int((tm < ta).sum()), n), "p_mae_before_mfe": _rate(int((ta < tm).sum()), n),
            "p_same_bar": _rate(int((tm == ta).sum()), n)}
    return out


def first_passage_sections(T: PathArrays, m: np.ndarray, spec: dict) -> dict:
    fp = spec["first_passage"]
    res = {"symmetric": {}, "asymmetric": {}, "outcomes": fp["outcomes"], "same_bar_rule": fp["same_bar_rule"]}

    def one(tgt, stp, h):
        em = m & T.elig[h] & np.isfinite(T.sigma_log)
        n = int(em.sum())
        code = barrier_outcome(T.t_fav[tgt][em], T.t_adv[stp][em], h)
        return {"n": n, "confirmed_target_first": _rate(int((code == TARGET).sum()), n),
                "confirmed_stop_first": _rate(int((code == STOP).sum()), n),
                "ambiguous_same_bar": _rate(int((code == AMBIG).sum()), n), "neither": _rate(int((code == EXPIRED).sum()), n)}
    for k in fp["levels_sigma"]:
        res["symmetric"][f"+{k}sigma_before_-{k}sigma"] = {h: one(k, k, h) for h in fp["horizons_bars"]}
    for t, s in fp["asymmetric_target_stop_sigma"]:
        res["asymmetric"][f"+{t}sigma_target/-{s}sigma_stop"] = {h: one(t, s, h) for h in fp["horizons_bars"]}
    return res


def bracket_cell_defs(spec: dict) -> list[dict]:
    b = spec["bracket_surface"]
    cells = [{"expiry_bars": e, "stop_sigma": s, "target_sigma": t} for e, s, t in product(b["expiries_bars"], b["stops_sigma"], b["targets_sigma"])]
    assert len(cells) == b["n_cells"] == 64
    return cells                                           # canonical order: expiry, stop, target (NOT performance order)


def _cell_stats(code, pc, pr, sd, sel, weeks) -> dict:
    ok = sel & (code >= 0)
    n = int(ok.sum())
    if n == 0:
        return {"n": 0}
    c, p, rr = code[ok], pc[ok], pr[ok]
    r = p / sd[ok]
    win, lose = p[p > 0], p[p < 0]
    unamb = np.isfinite(rr)
    return {
        "n": n, "frequency_per_week": (n / weeks) if weeks else None,
        "target_hit_rate": _rate(int((c == TARGET).sum()), n), "stop_hit_rate_conservative": _rate(int(((c == STOP) | (c == AMBIG)).sum()), n),
        "expiry_rate": _rate(int((c == EXPIRED).sum()), n), "same_bar_ambiguous_rate": _rate(int((c == AMBIG).sum()), n),
        "confirmed_stop_first_rate": _rate(int((c == STOP).sum()), n),
        "mean_gross_points": _f(p.mean()), "median_gross_points": pct(p, 50), "mean_R": _f(r.mean()), "median_R": pct(r, 50),
        "profit_factor_gross": _f(win.sum() / abs(lose.sum())) if len(lose) and lose.sum() != 0 else None,
        "win_rate": _rate(int((p > 0).sum()), n), "mean_winner_points": _f(win.mean()) if len(win) else None,
        "mean_loser_points": _f(lose.mean()) if len(lose) else None,
        "p5": pct(p, 5), "p25": pct(p, 25), "p50": pct(p, 50), "p75": pct(p, 75), "p95": pct(p, 95),
        "raw_path_result": {"n_unambiguous": int(unamb.sum()), "ambiguous_excluded": int((~unamb).sum()),
                            "mean_gross_points": _f(rr[unamb].mean()) if unamb.any() else None,
                            "median_gross_points": pct(rr[unamb], 50) if unamb.any() else None}}


def bracket_surface(T: PathArrays, ctx: dict[str, dict], years: np.ndarray, folds: np.ndarray, spec: dict) -> dict[str, list]:
    """The 64-cell surface for every context. ``ctx[name] = {mask, weeks_total, weeks_by_year}``. Canonical order, cell by cell."""
    out = {name: [] for name in ctx}
    min_ev = spec["stability"]["min_events_for_eligible_year"]
    for cell in bracket_cell_defs(spec):
        code, pc, pr, sd = bracket_pnl(T, cell["target_sigma"], cell["stop_sigma"], cell["expiry_bars"])
        for name, c in ctx.items():
            m = c["mask"]
            rec = {**cell, "variant_primary": "CONSERVATIVE_RESULT (AMBIGUOUS_SAME_BAR counted as STOP)", **_cell_stats(code, pc, pr, sd, m, c["weeks_total"])}
            if rec["n"]:
                yearly, inel = {}, []
                for y in sorted(set(years[m & (code >= 0)].tolist())):
                    my = m & (years == y) & (code >= 0)
                    ny = int(my.sum())
                    if ny < min_ev:
                        inel.append({"year": int(y), "n": ny})
                        continue
                    cy, py = code[my], pc[my]
                    yearly[int(y)] = {"n": ny, "mean_gross_points": _f(py.mean()), "median_gross_points": pct(py, 50),
                                      "target_hit_rate": _rate(int((cy == TARGET).sum()), ny),
                                      "stop_hit_rate_conservative": _rate(int(((cy == STOP) | (cy == AMBIG)).sum()), ny),
                                      "expiry_rate": _rate(int((cy == EXPIRED).sum()), ny)}
                means = [v["mean_gross_points"] for v in yearly.values()]
                fold_means = []
                for f in sorted(set(folds[m & (code >= 0)].tolist())):
                    if f <= 0:
                        continue
                    mf = m & (folds == f) & (code >= 0)
                    if mf.any():
                        fold_means.append(float(pc[mf].mean()))
                rec["yearly"] = yearly
                rec["ineligible_years"] = inel
                rec["year_stability"] = {"positive_years": int(sum(1 for v in means if v > 0)), "eligible_years": len(means),
                                         "worst_year": _f(min(means)) if means else None, "best_year": _f(max(means)) if means else None,
                                         "median_yearly_result": _f(np.median(means)) if means else None}
                rec["fold_stability"] = {"folds_with_events": len(fold_means),
                                         "positive_fold_fraction": (sum(1 for v in fold_means if v > 0) / len(fold_means)) if fold_means else None,
                                         "mean_per_fold": _f(np.mean(fold_means)) if fold_means else None}
            out[name].append(rec)
    return out


def yearly_table(T: PathArrays, m: np.ndarray, years: np.ndarray, weeks_by_year: dict, tick: float, min_ev: int) -> dict:
    """Compact long-run yearly table (spec item 20): every eligible year, negative years included."""
    rows, inel = [], []
    for y in sorted(set(years[m].tolist())):
        my = m & (years == y)
        n = int(my.sum())
        if n < min_ev:
            inel.append({"year": int(y), "n": n})
            continue
        row = {"year": int(y), "n": n, "events_per_week": (n / weeks_by_year[y]) if weeks_by_year.get(y) else None}
        for h in (15, 30, 60, 120):
            e = my & T.elig[h]
            with np.errstate(divide="ignore", invalid="ignore"):
                dl = T.d[e] * np.log(T.close_h[h][e] / T.p0[e])
            row[f"CONT_{h}"] = _rate(int((dl > 0).sum()), int(e.sum()))
        e = my & T.elig[60]
        with np.errstate(divide="ignore", invalid="ignore"):
            dl60 = T.d[e] * np.log(T.close_h[60][e] / T.p0[e])
        row.update({"median_MFE_60": pct(T.mfe_pts[60][e], 50), "median_absMAE_60": pct(-T.mae_pts[60][e], 50),
                    "P75_MFE_60": pct(T.mfe_pts[60][e], 75), "P75_absMAE_60": pct(-T.mae_pts[60][e], 75),
                    "mean_return_60": _f(dl60.mean()) if len(dl60) else None, "median_return_60": pct(dl60, 50), "n_60": int(e.sum()),
                    "units": "excursions in points; returns are directional log returns"})
        rows.append(row)
    return {"rows": rows, "ineligible_years": inel}


# ---------------------------------------------------------------------------------------------------- orchestration
def _identity(mask: np.ndarray) -> str:
    return hashlib.sha256(np.packbits(mask).tobytes() + str(len(mask)).encode()).hexdigest()


def make_paths(bars: pd.DataFrame, events: pd.DataFrame, sigma_log: np.ndarray, frozen: Frozen) -> PathArrays:
    spec = frozen.path_diagnostics
    o, h, l, c = (bars[k].to_numpy("float64") for k in ("open", "high", "low", "close"))
    first = forward_start(bars, events["event_time"])
    close_ns = utc_ns(session_close_utc(pd.DatetimeIndex(events["event_time"]).tz_convert("UTC"), frozen))
    levels = sorted({*spec["first_passage"]["levels_sigma"], *spec["bracket_surface"]["stops_sigma"], *spec["bracket_surface"]["targets_sigma"]})
    return compute_paths(o, h, l, c, utc_ns(bars.index), first, events["direction"].to_numpy(), sigma_log, close_ns,
                         int(frozen.interval.value), list(spec["horizons_bars"]), levels)


def _ctx_payload(T, m, years, folds, weeks_total, weeks_by_year, weeks_by_fold, frozen, spec) -> dict:
    tick = frozen.tick_size
    core = core_sections(T, m, tick)
    by_year, by_fold, inel = {}, {}, []
    for y in sorted(set(years[m].tolist())):
        my = m & (years == y)
        if int(my.sum()) < spec["stability"]["min_events_for_eligible_year"]:
            inel.append({"year": int(y), "n": int(my.sum())})
            continue
        by_year[int(y)] = core_sections(T, my, tick)
    for f in sorted(set(folds[m].tolist())):
        if f > 0:
            by_fold[int(f)] = core_sections(T, m & (folds == f), tick)
    return {"n_events": int(m.sum()), "weeks": weeks_total, **core, "first_passage": first_passage_sections(T, m, spec),
            "by_year": by_year, "ineligible_years": inel, "by_fold": by_fold,
            "yearly_table": yearly_table(T, m, years, weeks_by_year, tick, spec["stability"]["min_events_for_eligible_year"])}


def build_path_diagnostics(*, bars_dev: pd.DataFrame, events: pd.DataFrame, features: pd.DataFrame, eligible: np.ndarray, panels: dict,
                           folds, weeks_all: dict, weeks_cv: dict[str, dict], frozen: Frozen, ladder_steps: dict | None = None) -> dict:
    """Assemble the whole diagnostic report from DEVELOPMENT rows only.

    ``folds`` = DEVELOPMENT_CV Fold objects; ``weeks_all`` = weeks_in_intervals over all development bars;
    ``weeks_cv[f'{target}|{model}']`` = weeks info of that panel's validation folds."""
    spec = frozen.path_diagnostics
    ev = events.assign(_el=np.asarray(eligible, dtype=bool), _sigma=sigma_ref(features["RV_60"].to_numpy()))
    ev = ev[ev["_el"]].sort_values(["event_time", "event_id"], kind="stable").reset_index(drop=True)
    T = make_paths(bars_dev, ev, ev["_sigma"].to_numpy(), frozen)
    etime = pd.DatetimeIndex(ev["event_time"]).tz_convert("UTC")
    years = etime.year.to_numpy()
    ens = utc_ns(etime)
    fold_of = np.zeros(len(ev), dtype=int)
    for f in folds:
        fold_of[(ens >= f.val_start_ns) & (ens < f.val_end_ns)] = f.fold
    all_mask = np.ones(len(ev), dtype=bool)
    ctx_def = {"ALL": {"mask": all_mask, "weeks_total": weeks_all["total"], "weeks_by_year": weeks_all["by_year"],
                       "weeks_by_fold": {}}}
    id_of = {ev["event_id"].iloc[i]: i for i in range(len(ev))}
    for (t, m), p in sorted(panels.items()):
        cv = p.cv
        for state in ("UPPER_HALF", "LOWER_HALF"):
            mk = np.zeros(len(ev), dtype=bool)
            for eid in cv.loc[cv["state"] == state, "event_id"]:
                mk[id_of[eid]] = True
            w = weeks_cv.get(f"{t}|{m}", {"total": 0, "by_year": {}})
            ctx_def[f"{t}|{m}|{state}"] = {"mask": mk, "weeks_total": w["total"], "weeks_by_year": w["by_year"], "weeks_by_fold": {}}
    surfaces = bracket_surface(T, ctx_def, years, fold_of, spec)
    contexts, seen = {}, {}
    for name, c in ctx_def.items():
        ident = _identity(c["mask"])
        if name != "ALL" and ident in seen:
            contexts[name] = {"same_events_as": seen[ident]}
            continue
        seen[ident] = name
        payload = _ctx_payload(T, c["mask"], years, fold_of, c["weeks_total"], c["weeks_by_year"], {}, frozen, spec)
        payload["bracket_surface"] = surfaces[name]
        contexts[name] = payload
    inel = {int(h): int((~T.elig[h]).sum()) for h in T.horizons}
    rep = {"version": spec["version"], "label": spec["label"], "promotion_eligible": False, "selection_trials_affected": 0,
           "diagnostic_statement": " ".join(spec["diagnostic_statement"].split()),
           "non_promotable_rule": spec["non_promotable_rule"], "human_interpretation_rule": " ".join(spec["human_interpretation_rule"].split()),
           "sigma_ref_formula": spec["sigma_ref"]["formula"],
           "cost_banner": spec["bracket_surface"]["cost_banner"], "selection_banner": spec["bracket_surface"]["selection_banner"],
           "horizons_bars": list(T.horizons), "tick_size_points": frozen.tick_size, "sigma_ref": spec["sigma_ref"]["definition"],
           "percentile_method": spec["percentiles"]["method"], "n_bracket_cells": len(bracket_cell_defs(spec)),
           "bracket_canonical_order": spec["bracket_surface"]["canonical_order"],
           "counts": {"events_total": int(len(events)), "model_eligible_events": int(len(ev)), "path_ineligible_by_horizon": inel},
           "n_contexts": len(contexts), "contexts": contexts, "ladder": ladder_steps or {}}
    return rep


# ---------------------------------------------------------------------------------------------------- filter-ladder path effects
def ladder_path_diagnostics(sets: dict, order: list[str], bars_dev: pd.DataFrame, frozen: Frozen) -> dict:
    """Path summaries for every frozen ladder step (sets = ladder_event_sets output). Never changes or removes a step."""
    from engine.feature_engine import last_completed_position
    spec = frozen.path_diagnostics
    tick = frozen.tick_size
    weeks = pd.Series(bars_dev.index.tz_convert(frozen.tz)).dt.strftime("%G-%V").nunique()
    steps = []
    close = bars_dev["close"].to_numpy("float64")
    prev = None
    for name in order:
        ev = sets[name].reset_index(drop=True)
        rec = {"step": name, "n_events": int(len(ev))}
        if len(ev):
            pos = last_completed_position(bars_dev.index, ev["event_time"], frozen.interval)
            sig = sigma_ref(rv_ref(close, pos))
            ok = np.isfinite(sig)
            ev, sig = ev[ok].reset_index(drop=True), sig[ok]
        rec["n_events_with_sigma"] = int(len(ev))
        rec["frequency_per_week"] = len(ev) / weeks if weeks else None
        if len(ev):
            T = make_paths(bars_dev, ev, sig, frozen)
            yrs = pd.DatetimeIndex(ev["event_time"]).tz_convert("UTC").year.to_numpy()
            core = core_sections(T, np.ones(len(ev), dtype=bool), tick)
            rec["core"] = {h: {"continuation": core["continuation"][h], "median_MFE_points": core["excursions"][h]["MFE"]["points"]["median"],
                               "p75_MFE_points": core["excursions"][h]["MFE"]["points"]["p75"], "p95_MFE_points": core["excursions"][h]["MFE"]["points"]["p95"],
                               "median_adverse_points": core["excursions"][h]["ADVERSE_ABS_MAE"]["points"]["median"],
                               "p75_adverse_points": core["excursions"][h]["ADVERSE_ABS_MAE"]["points"]["p75"],
                               "p95_adverse_points": core["excursions"][h]["ADVERSE_ABS_MAE"]["points"]["p95"]} for h in T.horizons}
            rec["by_year"] = {}
            for y in sorted(set(yrs.tolist())):
                my = yrs == y
                if int(my.sum()) < spec["stability"]["min_events_for_eligible_year"]:
                    continue
                cy = core_sections(T, my, tick)
                rec["by_year"][int(y)] = {"n": int(my.sum()), **{f"cont_{h}": cy["continuation"][h]["continuation"] for h in T.horizons},
                                          "median_MFE_60": cy["excursions"][60]["MFE"]["points"]["median"],
                                          "median_adverse_60": cy["excursions"][60]["ADVERSE_ABS_MAE"]["points"]["median"]}
        rec["delta_vs_previous_step"] = None
        if prev is not None and "core" in rec and "core" in prev:
            rec["delta_vs_previous_step"] = {
                "frequency_per_week": (rec["frequency_per_week"] - prev["frequency_per_week"]) if rec["frequency_per_week"] is not None else None,
                "per_horizon": {h: {"continuation_rate": _sub(rec["core"][h]["continuation"]["continuation"]["rate"], prev["core"][h]["continuation"]["continuation"]["rate"]),
                                    "median_MFE_points": _sub(rec["core"][h]["median_MFE_points"], prev["core"][h]["median_MFE_points"]),
                                    "median_adverse_points": _sub(rec["core"][h]["median_adverse_points"], prev["core"][h]["median_adverse_points"])}
                                for h in rec["core"]}}
        steps.append(rec)
        prev = rec
    return {"label": spec["label"], "order_frozen": list(order), "steps": steps,
            "note": "A poor-looking step is NOT removed or altered; changing the ladder is a new experiment."}


def _sub(a, b):
    return None if a is None or b is None else a - b


def assert_no_forbidden_phrases(obj) -> None:
    txt = json.dumps(obj)
    bad = [p for p in FORBIDDEN_PHRASES if p in txt.upper()]
    if bad:
        raise AssertionError(f"forbidden bracket-selection phrases in path diagnostics: {bad}")
